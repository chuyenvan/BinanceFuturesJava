#!/usr/bin/env python3
"""short_v2_p0a_statemap.py — Pha 0A PROGRAM_SHORT_V2: STATE MAP per-coin causal (LIQ/BTCF/BLEED/FLAT, BLEED').

Pre-reg: docs/prereg/PREREG_SHORT_V2_P0A.md (07d9e335). DEV 2022-01-01..2025-12-31, forward <= 2026-01-01 00:00 UTC.
Stage `qv`  : Aerospike test.kline_1m_opt -> quoteVol ngay UTC theo symbol (cache ngoai repo, theo thang).
Stage `run` : CLOSES_1H.bin (daily close + duong gia 1h) + qv + /tmp/fund_cache.npz -> state, 4 so, CI, run, transition.
Out: docs/result/RESULT_SHORT_V2_P0A.json ; bang markdown -> CACHE/p0a_tables.md
"""
import argparse, glob, json, logging, math, os, sys, time
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
H = 3600000
DAY = 86400000
DEV_END_MS = 1767225600000            # 2026-01-01 00:00 UTC
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
FUND = "/tmp/fund_cache.npz"
CACHE = "/home/ubuntu/claude_master/1002/p0a_cache"
OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_V2_P0A.json")
QV_START = pd.Timestamp("2021-09-01")
DEV0, DEV1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2025-12-31")
T_LIST = (3, 7, 14)
FEE = 0.00112
SL_X = 0.10
SL_LOSS = 0.102
NREP, SEED = 2000, 20260905
ZK = math.sqrt(2 * math.log(13))
INFL = ZK / 1.959964
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT"}
STN = {0: "NA", 1: "LIQ", 2: "BTCF", 3: "BLEED", 4: "FLAT"}
TIERN = {1: "NHO", 2: "VUA", 3: "LON"}
log = logging.getLogger("p0a")


# ───────────────────────── stage qv (Aerospike 1m -> ngay UTC) ─────────────────────────
def stage_qv():
    import aerospike, cramjam
    from short_state_0sim import parse_all_min
    os.makedirs(os.path.join(CACHE, "qv"), exist_ok=True)
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    months = pd.period_range(QV_START, DEV1, freq="M")
    for mo in months:
        fp = os.path.join(CACHE, "qv", "%s.parquet" % mo.strftime("%Y%m"))
        if os.path.exists(fp):
            continue
        t0 = time.time(); rows = []
        for d in pd.date_range(mo.start_time, mo.end_time.normalize(), freq="D"):
            base = d + pd.Timedelta(hours=7)          # key GMT+7 = open phut; phut 00:00 UTC -> 07:00
            keys = [("test", "kline_1m_opt", (base + pd.Timedelta(minutes=k)).strftime("%Y%m%d-%H%M"))
                    for k in range(1440)]
            qv = {}; nm = {}; lc = {}; nrec = 0
            for rr in cli.batch_read(keys).batch_records:
                if rr.result != 0 or rr.record is None:
                    continue
                b = rr.record[2]
                if not b or "data" not in b:
                    continue
                nrec += 1
                for s, (c, v) in parse_all_min(bytes(dec(b["data"]))).items():
                    qv[s] = qv.get(s, 0.0) + float(v); nm[s] = nm.get(s, 0) + 1; lc[s] = c
            for s in qv:
                rows.append((d, s.decode(), qv[s], nm[s], lc[s], nrec))
        df = pd.DataFrame(rows, columns=["date", "sym", "qv", "nmin", "lastc", "nrec"])
        df.to_parquet(fp, index=False)
        log.info("qv %s rows=%d days=%d %.0fs", mo, len(df), df["date"].nunique(), time.time() - t0)


# ───────────────────────── load ─────────────────────────
def load_hourly():
    """Ma tran day gio x sym (float32). Hang k <-> ts = T_START + k*H (ts = thoi diem close duoc biet)."""
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64); sid = a["sym"].astype(np.int64); c = a["c"].astype(np.float32)
    t_start = int((QV_START - pd.Timedelta(days=1)).value // 10**6)
    m = (ts >= t_start) & (ts <= DEV_END_MS) & np.isfinite(c) & (c > 0)
    ts, sid, c = ts[m], sid[m], c[m]
    mp = pd.read_csv(MAP)
    id2 = dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))
    ids = np.unique(sid)
    names = [id2[int(i)] for i in ids]
    col = np.searchsorted(ids, sid)
    nh = (DEV_END_MS - t_start) // H + 1
    C = np.full((nh, len(ids)), np.nan, dtype=np.float32)
    C[(ts - t_start) // H, col] = c
    log.info("hourly C %s, sym=%d, t_start=%s", C.shape, len(ids), pd.to_datetime(t_start, unit="ms"))
    return C, names, t_start


def load_qv():
    fs = sorted(glob.glob(os.path.join(CACHE, "qv", "*.parquet")))
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    return df


# ───────────────────────── chi bao + trang thai (causal) ─────────────────────────
def age_of_hi(cl, w=61):
    """cl (ndays, nsym) -> age_hi: so ngay tu dinh GAN NHAT dat max cua cua so [d-60..d]; yeu cau du w gia tri."""
    nd, ns = cl.shape
    out = np.full((nd, ns), np.nan)
    if nd < w:
        return out
    win = np.lib.stride_tricks.sliding_window_view(cl, w, axis=0)      # (nd-w+1, ns, w), win[...,-1] = ngay d
    rev = win[..., ::-1]
    ok = np.isfinite(win).all(axis=2)
    a = np.argmax(np.where(np.isfinite(rev), rev, -np.inf), axis=2).astype(float)   # argmax tra ve chi so DAU tien = gan nhat
    a[~ok] = np.nan
    out[w - 1:] = a
    return out


def compute_states(close, qv, coins, btc="BTCUSDT"):
    """close, qv: DataFrame ngay x sym (lich day du). Chi dung du lieu <= d cho hang d."""
    cl = close[coins]
    hi60 = cl.rolling(61, min_periods=61).max()
    lo60 = cl.rolling(61, min_periods=61).min()
    run_up = hi60 / lo60 - 1
    dd_hi = cl / hi60 - 1
    age_hi = pd.DataFrame(age_of_hi(cl.to_numpy(float)), index=cl.index, columns=coins)
    tot = qv.sum(axis=1, min_count=1)
    tsh = qv[coins].div(tot, axis=0)
    lt = np.log(tsh.where(tsh > 0))
    mu = lt.shift(1).rolling(90, min_periods=60).mean()
    sd = lt.shift(1).rolling(90, min_periods=60).std(ddof=1)
    tsh_z = (lt - mu) / sd.where(sd > 0)
    lr = np.log(close).diff()
    x = lr[coins]; y = lr[btc]
    v = x.notna() & y.notna().to_numpy()[:, None]
    xv = x.where(v, 0.0); yv = pd.DataFrame(np.where(v, y.to_numpy()[:, None], 0.0), index=x.index, columns=coins)
    n = v.astype(float).rolling(60, min_periods=60).sum()
    sx = xv.rolling(60, min_periods=60).sum(); sy = yv.rolling(60, min_periods=60).sum()
    sxy = (xv * yv).rolling(60, min_periods=60).sum(); syy = (yv * yv).rolling(60, min_periods=60).sum()
    var = syy - sy * sy / n
    beta60 = ((sxy - sx * sy / n) / var.where(var > 0)).where(n >= 45)
    mqv = qv[coins].rolling(30, min_periods=20).mean()
    pr = mqv.rank(axis=1, pct=True)
    tier = pd.DataFrame(np.where(pr > 2 / 3, 3, np.where(pr <= 1 / 3, 1, 2)), index=cl.index, columns=coins).where(pr.notna())
    bc = close[btc]
    sma = bc.rolling(50, min_periods=50).mean()
    bull = (bc > sma).astype(float).where(sma.notna() & bc.notna())     # 1.0 bull, 0.0 not bull, NaN
    valid = (cl.notna() & run_up.notna() & age_hi.notna() & dd_hi.notna() & tsh_z.notna()
             & beta60.notna() & tier.notna())
    liq = (tsh_z >= 1.5) | ((run_up >= 0.5) & (age_hi <= 10))
    btcf = (tier == 3) & (beta60 >= 0.8)
    bleed = (run_up >= 0.3) & (age_hi >= 11) & (age_hi <= 60) & (dd_hi <= -0.15) & (tsh_z <= 0)
    st = np.where(liq, 1, np.where(btcf, 2, np.where(bleed, 3, 4)))
    st = np.where(valid.to_numpy(), st, 0).astype(np.int8)
    return dict(state=pd.DataFrame(st, index=cl.index, columns=coins), run_up=run_up, age_hi=age_hi, dd_hi=dd_hi,
                tsh_z=tsh_z, beta60=beta60, tier=tier, bull=bull, tsh_sum=tsh.sum(axis=1) + qv[[c for c in qv.columns if c not in coins]].sum(axis=1).div(tot))


# ───────────────────────── forward (1h closes) + funding exact ─────────────────────────
def funding_cum(names, t_start, nh):
    """cumF[k, j] = Σ rate cua sym j co ts in (T_START, T_START + k*H]. Short NHAN khi rate > 0."""
    z = np.load(FUND, allow_pickle=True)
    fsyms = [str(s) for s in z["syms"]]
    ts = z["ts"].astype(np.int64); rt = z["rt"].astype(np.float64); sid = z["sid"].astype(np.int64)
    n2c = {n: j for j, n in enumerate(names)}
    colmap = np.array([n2c.get(s, -1) for s in fsyms])
    col = colmap[sid]
    k = -((t_start - ts) // H)                    # ceil((ts - t_start)/H): ts in (grid_{k-1}, grid_k] -> k
    m = (col >= 0) & (ts > t_start) & (k < nh)
    F = np.zeros((nh, len(names)), dtype=np.float64)
    np.add.at(F, (k[m], col[m]), rt[m])
    has = np.zeros(len(names), bool); has[np.unique(col[m])] = True
    log.info("funding events used=%d / %d, sym co funding=%d/%d", int(m.sum()), len(ts), int(has.sum()), len(names))
    return np.cumsum(F, axis=0), has


def forward(S, C, names, t_start, cumF, hasF):
    """1 lenh short / coin-ngay hop le (state>0), d in DEV. Tra DataFrame quan sat cho moi T."""
    n2c = {n: j for j, n in enumerate(names)}
    coins = list(S["state"].columns)
    cj = np.array([n2c.get(c, -1) for c in coins])
    st = S["state"]; tier = S["tier"]; bull = S["bull"]
    out = []
    for d in pd.date_range(DEV0, DEV1, freq="D"):
        sv = st.loc[d].to_numpy()
        ok = (sv > 0) & (cj >= 0)
        if not ok.any():
            continue
        t0 = int((d + pd.Timedelta(days=1)).value // 10**6)
        h0 = (t0 - t_start) // H
        cols = cj[ok]
        P0 = C[h0, cols].astype(np.float64)
        for T in T_LIST:
            L = 24 * T
            if t0 + L * H > DEV_END_MS:
                continue
            W = C[h0 + 1:h0 + L + 1, cols].astype(np.float64)
            anyv = np.isfinite(W).any(axis=0) & np.isfinite(P0)
            Wf = pd.DataFrame(W).ffill().to_numpy()
            ret = Wf[-1] / P0 - 1
            trunc = ~np.isfinite(W[-1])
            mf = np.nanmax(np.where(np.isfinite(W), W, -np.inf), axis=0) / P0 - 1
            hit = W >= (1 + SL_X) * P0[None, :]
            sl = hit.any(axis=0)
            kx = np.where(sl, np.argmax(hit, axis=0) + 1, L)
            fund = cumF[h0 + kx, cols] - cumF[h0, cols]
            pnl = np.where(sl, -SL_LOSS, -ret) - FEE + fund
            o = pd.DataFrame(dict(date=d, T=T, sym=np.array(coins)[ok], state=sv[ok], tier=tier.loc[d].to_numpy()[ok],
                                  bull=float(bull.loc[d]), ret=ret, maxfav=mf, sl=sl, fund=fund, pnl=pnl, trunc=trunc,
                                  hasf=hasF[cols]))
            out.append(o[anyv])
    df = pd.concat(out, ignore_index=True)
    df["year"] = df["date"].dt.year
    df["excess"] = df["ret"] - df.groupby(["T", "date"])["ret"].transform("mean")
    return df


# ───────────────────────── thong ke + CI block-7d ─────────────────────────
def ci_block(pnl, dates):
    if len(pnl) == 0:
        return None, None, None, None
    b = ((dates - DEV0).dt.days // 7).to_numpy()
    nb = int((DEV1 - DEV0).days // 7) + 1
    s = np.bincount(b, weights=pnl, minlength=nb); c = np.bincount(b, minlength=nb).astype(float)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, nb, (NREP, nb))
    bs = s[idx].sum(axis=1) / np.maximum(c[idx].sum(axis=1), 1)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    mu = float(pnl.mean())
    return float(lo), float(hi), mu - (mu - lo) * INFL, mu + (hi - mu) * INFL


def stats(g, ci=True):
    if len(g) == 0:
        return dict(n=0)
    r = dict(n=int(len(g)), bleed_mean=float(g.ret.mean()), bleed_med=float(g.ret.median()),
             excess=float(g.excess.mean()), pSQ10=float((g.maxfav >= 0.10).mean()), pSQ20=float((g.maxfav >= 0.20).mean()),
             p_ret_le_m10=float((g.ret <= -0.10).mean()), fund=float(g.fund.mean()), netproxy=float(g.pnl.mean()),
             sl_rate=float(g.sl.mean()), m_neg_ret_noSL=float((-g.ret[~g.sl]).mean()) if (~g.sl).any() else None,
             m_neg_ret_SL_raw=float((-g.ret[g.sl]).mean()) if g.sl.any() else None)
    if ci:
        lo, hi, ilo, ihi = ci_block(g.pnl.to_numpy(float), g.date)
        r.update(ci_raw=[lo, hi], ci_infl=[ilo, ihi])
    return r


def runs(state_df, tier_df, code):
    """Do dai run (ngay lich lien tiep) cua trang thai `code`; run bat dau trong DEV; tier = tier ngay dau."""
    res = []
    A = state_df.to_numpy(); TT = tier_df.to_numpy(); idx = state_df.index
    last = len(idx) - 1
    for j in range(A.shape[1]):
        m = np.concatenate([[False], A[:, j] == code, [False]])
        dm = np.diff(m.astype(np.int8))
        st = np.where(dm == 1)[0]; en = np.where(dm == -1)[0]
        for a, b in zip(st, en):
            if idx[a] < DEV0 or idx[a] > DEV1:
                continue
            res.append((b - a, TT[a, j], (b - 1) >= last))
    return pd.DataFrame(res, columns=["len", "tier", "cens"])


def panels(C, names, t_start):
    q = load_qv()
    dates = pd.date_range(QV_START, DEV1, freq="D")
    qv = q.pivot_table(index="date", columns="sym", values="qv", aggfunc="sum").reindex(dates)
    lastc = q.pivot_table(index="date", columns="sym", values="lastc", aggfunc="last").reindex(dates)
    nrec = q.groupby("date")["nrec"].max().reindex(dates)
    hix = np.array([((d + pd.Timedelta(days=1)).value // 10**6 - t_start) // H for d in dates])
    close = pd.DataFrame(C[hix].astype(np.float64), index=dates, columns=names)
    allc = sorted(set(qv.columns) | set(names))
    qv = qv.reindex(columns=allc); close = close.reindex(columns=allc)
    coins = [c for c in allc if c.endswith("USDT") and "_" not in c and c != "BTCUSDT" and c not in STABLE]
    return close, qv, lastc, nrec, coins


def sanity_causal(close, qv, coins, S):
    rep = {}
    keys = ["state", "run_up", "age_hi", "dd_hi", "tsh_z", "beta60", "tier"]
    for cut in ("2022-06-15", "2023-09-01", "2025-03-10"):
        cut = pd.Timestamp(cut)
        rng = np.random.default_rng(1)
        c2 = close.copy(); q2 = qv.copy()
        m = c2.index > cut
        c2.loc[m] = rng.uniform(0.01, 100, size=c2.loc[m].shape)
        q2.loc[m] = rng.uniform(1e3, 1e9, size=q2.loc[m].shape)
        S2 = compute_states(c2, q2, coins)
        okk = {}
        for k in keys:
            a = S[k].loc[:cut].to_numpy(float); b = S2[k].loc[:cut].to_numpy(float)
            okk[k] = bool(np.array_equal(a, b, equal_nan=True))
        bb = bool(np.array_equal(S["bull"].loc[:cut].to_numpy(float), S2["bull"].loc[:cut].to_numpy(float), equal_nan=True))
        okk["bull"] = bb
        rep[str(cut.date())] = okk
        assert all(okk.values()), "CAUSAL FAIL tai %s: %s" % (cut.date(), okk)
    return rep


def stage_run():
    t00 = time.time()
    C, names, t_start = load_hourly()
    close, qv, lastc, nrec, coins = panels(C, names, t_start)
    log.info("panel ngay %s, coins=%d", close.shape, len(coins))
    S = compute_states(close, qv, coins)
    res = dict(prereg="docs/prereg/PREREG_SHORT_V2_P0A.md@07d9e335", zk=ZK, infl=INFL, sanity={})
    San = res["sanity"]
    # S-d: lastc 1m vs daily close CLOSES_1H ; Σ tsh
    dev = (close.index >= DEV0)
    cm = [c for c in coins if c in lastc.columns]
    a = lastc.reindex(close.index)[cm].to_numpy(float)[dev]; b = close[cm].to_numpy(float)[dev]
    k = np.isfinite(a) & np.isfinite(b)
    rel = np.abs(a[k] / b[k] - 1)
    San["S_d"] = dict(n_pair=int(k.sum()), med_absrel=float(np.median(rel)), p99_absrel=float(np.percentile(rel, 99)),
                      frac_gt_1pct=float((rel > 0.01).mean()), tsh_sum_minmax=[float(S["tsh_sum"][dev].min()), float(S["tsh_sum"][dev].max())],
                      days_nrec_lt1440=int((nrec[dev] < 1440).sum()), days_nrec_lt1000=int((nrec[dev] < 1000).sum()))
    log.info("S-d %s", San["S_d"])
    San["S_b_causal"] = sanity_causal(close, qv, coins, S)
    log.info("S-b causal OK %s", San["S_b_causal"])
    st = S["state"].loc[DEV0:DEV1]
    yr = st.index.year
    sa = {}
    for y in (2022, 2023, 2024, 2025):
        v = st[yr == y].to_numpy().ravel()
        listed = v[v >= 0]
        nval = int((v > 0).sum())
        sa[str(y)] = dict(n_valid=nval, n_NA_listed=int(((v == 0) & np.isfinite(close.loc[st.index[yr == y], coins].to_numpy().ravel())).sum()),
                          **{STN[c]: round(float((v == c).sum() / max(nval, 1)), 4) for c in (1, 2, 3, 4)})
    vall = st.to_numpy().ravel()
    nall = int((vall > 0).sum())
    cover = {STN[c]: float((vall == c).sum() / nall) for c in (1, 2, 3, 4)}
    bl = S["bull"].loc[DEV0:DEV1].to_numpy()
    cover["BLEED'"] = float(((st.to_numpy() == 3) & (bl[:, None] == 0.0)).sum() / nall)
    cover["ALL"] = 1.0
    San["S_a"] = dict(n_valid_dev=nall, by_year=sa)
    res["cover"] = cover
    log.info("S-a %s cover %s", San["S_a"], cover)
    # S-c: CFXUSDT 60 ngay (pre-reg). CFX trong CLOSES_1H chi co tu 2023-02-20 (khong du warm-up) => them TRBUSDT
    # 2023-10-01..11-29 (pump noi tieng, co lich su) CHI de kiem tay — khong anh huong bat ky so nao.
    for cfx, d0, d1 in (("CFXUSDT", "2023-02-01", "2023-04-01"), ("TRBUSDT", "2023-10-01", "2023-11-29")):
        rr = pd.DataFrame({"close": close[cfx], "tsh_z": S["tsh_z"][cfx], "run_up": S["run_up"][cfx], "age_hi": S["age_hi"][cfx],
                           "dd_hi": S["dd_hi"][cfx], "tier": S["tier"][cfx], "beta60": S["beta60"][cfx],
                           "state": S["state"][cfx].map(STN)}).loc[d0:d1]
        San["S_c_" + cfx] = [[str(i.date())] + [None if (isinstance(x, float) and not np.isfinite(x)) else (round(x, 4) if isinstance(x, float) else x)
                             for x in row] for i, row in zip(rr.index, rr.itertuples(index=False))]
        log.info("S-c %s %s..%s:\n%s", cfx, d0, d1, rr.round(3).to_string())
    # forward
    cumF, hasF = funding_cum(names, t_start, C.shape[0])
    df = forward(S, C, names, t_start, cumF, hasF)
    del cumF
    log.info("forward obs=%d (%.0fs)", len(df), time.time() - t00)
    San["S_a"]["obs_by_T"] = {int(T): dict(n=int((df["T"] == T).sum()), n_trunc=int(df.loc[df["T"] == T, "trunc"].sum()),
                                           frac_has_funding=float(df.loc[df["T"] == T, "hasf"].mean()),
                                           n_sl_ne_pSQ10=int(((df.maxfav >= 0.10) != df.sl)[df["T"] == T].sum()),
                                           fund_q=[float(x) for x in np.percentile(df.loc[df["T"] == T, "fund"], [0.1, 1, 50, 99, 99.9])],
                                           n_fund_lt_m5pct=int((df.loc[df["T"] == T, "fund"] < -0.05).sum()))
                              for T in T_LIST}
    log.info("obs %s", San["S_a"]["obs_by_T"])
    return res, df, S, close


GROUPS = ["LIQ", "BTCF", "BLEED", "BLEED'", "FLAT", "ALL"]


def gmask(df, g):
    if g == "ALL":
        return np.ones(len(df), bool)
    if g == "BLEED'":
        return ((df.state == 3) & (df.bull == 0.0)).to_numpy()
    return (df.state == {"LIQ": 1, "BTCF": 2, "BLEED": 3, "FLAT": 4}[g]).to_numpy()


def tables(res, df, S):
    A = {}; B = {}
    for g in GROUPS:
        mg = gmask(df, g)
        for T in T_LIST:
            sub = df[mg & (df["T"] == T).to_numpy()]
            A["%s|%d" % (g, T)] = stats(sub)
            for y in (2022, 2023, 2024, 2025):
                B["%s|%d|%d" % (g, T, y)] = stats(sub[sub.year == y], ci=(T == 7))
        log.info("A %s done", g)
    res["A"] = A; res["B"] = B
    # C: run length
    Cc = {}
    for code in (1, 3):
        r = runs(S["state"], S["tier"], code)
        d = {}
        for tn, tv in (("ALL", None), ("LON", 3), ("VUA", 2), ("NHO", 1)):
            x = r if tv is None else r[r.tier == tv]
            d[tn] = dict(n=int(len(x)), p25=float(np.percentile(x.len, 25)) if len(x) else None,
                         p50=float(np.percentile(x.len, 50)) if len(x) else None,
                         p75=float(np.percentile(x.len, 75)) if len(x) else None,
                         mean=float(x.len.mean()) if len(x) else None, n_cens=int(x.cens.sum()))
        Cc[STN[code]] = d
    res["C_runs"] = Cc
    # D: chuyen trang thai
    st = S["state"].loc[DEV0:DEV1].to_numpy()
    a, b = st[:-1].ravel(), st[1:].ravel()
    k = (a > 0) & (b > 0)
    M = np.zeros((4, 4))
    np.add.at(M, (a[k] - 1, b[k] - 1), 1)
    res["D_trans"] = {STN[i + 1]: {STN[j + 1]: round(float(M[i, j] / M[i].sum()), 4) for j in range(4)} for i in range(4)}
    res["D_trans_n"] = {STN[i + 1]: int(M[i].sum()) for i in range(4)}
    # E: BLEED T=7 theo tier, theo bull
    E = {}
    sub = df[(df.state == 3) & (df["T"] == 7)]
    for tv, tn in ((3, "LON"), (2, "VUA"), (1, "NHO")):
        E["tier_" + tn] = stats(sub[sub.tier == tv])
    E["bull"] = stats(sub[sub.bull == 1.0]); E["notbull(=BLEED')"] = stats(sub[sub.bull == 0.0])
    res["E_bleed7"] = E
    # F: kill-criterion
    F = {}
    for g in ["LIQ", "BTCF", "BLEED", "FLAT", "BLEED'"]:
        a7 = A["%s|7" % g]
        yrs = [B["%s|7|%d" % (g, y)].get("netproxy") for y in (2022, 2023, 2024, 2025)]
        npos = int(sum(1 for v in yrs if v is not None and v > 0.005))
        c1 = res["cover"][g] >= 0.03; c2 = npos >= 3
        c3r = a7.get("ci_raw", [None])[0] is not None and a7["ci_raw"][0] > 0
        c3i = a7.get("ci_infl", [None])[0] is not None and a7["ci_infl"][0] > 0
        F[g] = dict(cover=res["cover"][g], C1=bool(c1), years_gt_0p5=npos, C2=bool(c2), C3_raw=bool(c3r), C3_infl=bool(c3i),
                    pass_raw=bool(c1 and c2 and c3r), pass_infl=bool(c1 and c2 and c3i), netproxy7=a7.get("netproxy"))
    anyi = any(v["pass_infl"] for v in F.values()); anyr = any(v["pass_raw"] for v in F.values())
    res["F_kill"] = F
    res["verdict"] = "PASS" if anyi else ("PASS-raw/FAIL-inflate" if anyr else "FAIL")
    log.info("VERDICT %s", res["verdict"])
    return res


def pc(x, nd=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else ("%+.*f" % (nd, 100 * x))


def ci_s(c):
    return "—" if not c or c[0] is None else "[%s;%s]" % (pc(c[0]), pc(c[1]))


def write_md(res):
    L = ["## A. Trạng thái × T (toàn DEV 2022–2025; % ; maxFav trên 1h closes = cận dưới)", "",
         "| nhóm | T | n | cover | bleed mean | bleed med | excess | pSQ10 | pSQ20 | P(ret≤−10%) | funding | netproxy | CI raw | CI inflate |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in GROUPS:
        for T in T_LIST:
            a = res["A"]["%s|%d" % (g, T)]
            if not a.get("n"):
                continue
            L.append("| %s | %d | %d | %.1f | %s | %s | %s | %.1f | %.1f | %.1f | %s | **%s** | %s | %s |" % (
                g, T, a["n"], 100 * res["cover"][g], pc(a["bleed_mean"]), pc(a["bleed_med"]), pc(a["excess"]),
                100 * a["pSQ10"], 100 * a["pSQ20"], 100 * a["p_ret_le_m10"], pc(a["fund"], 3), pc(a["netproxy"]),
                ci_s(a.get("ci_raw")), ci_s(a.get("ci_infl"))))
    L += ["", "## B. Theo năm (netproxy % ; bleed mean % ; pSQ10 %)", "",
          "| nhóm | T | 2022 | 2023 | 2024 | 2025 |", "|---|---|---|---|---|---|"]
    for g in GROUPS:
        for T in T_LIST:
            cells = []
            for y in (2022, 2023, 2024, 2025):
                b = res["B"]["%s|%d|%d" % (g, T, y)]
                if not b.get("n"):
                    cells.append("—"); continue
                s = "np %s · bl %s · sq %.1f · n %d" % (pc(b["netproxy"]), pc(b["bleed_mean"]), 100 * b["pSQ10"], b["n"])
                if T == 7:
                    s += " · CI %s" % ci_s(b.get("ci_raw"))
                cells.append(s)
            L.append("| %s | %d | %s |" % (g, T, " | ".join(cells)))
    L += ["", "## C. Độ dài run (ngày lịch; run bắt đầu trong DEV)", "", "| trạng thái | tier | n | p25 | p50 | p75 | mean | kiểm duyệt |",
          "|---|---|---|---|---|---|---|---|"]
    for s, d in res["C_runs"].items():
        for tn, v in d.items():
            L.append("| %s | %s | %d | %s | %s | %s | %s | %d |" % (s, tn, v["n"], v["p25"], v["p50"], v["p75"],
                                                                 None if v["mean"] is None else round(v["mean"], 1), v["n_cens"]))
    L += ["", "## D. Chuyển trạng thái P(s_{d+1} | s_d)", "", "| từ \\ sang | LIQ | BTCF | BLEED | FLAT | n |", "|---|---|---|---|---|---|"]
    for s, row in res["D_trans"].items():
        L.append("| %s | %s | %d |" % (s, " | ".join("%.3f" % row[t] for t in ("LIQ", "BTCF", "BLEED", "FLAT")), res["D_trans_n"][s]))
    L += ["", "## E. BLEED T=7 theo tier / regime", "", "| lát | n | bleed mean | excess | pSQ10 | funding | netproxy | CI raw | CI inflate |",
          "|---|---|---|---|---|---|---|---|---|"]
    for k, a in res["E_bleed7"].items():
        if a.get("n"):
            L.append("| %s | %d | %s | %s | %.1f | %s | **%s** | %s | %s |" % (k, a["n"], pc(a["bleed_mean"]), pc(a["excess"]), 100 * a["pSQ10"],
                                                                     pc(a["fund"], 3), pc(a["netproxy"]), ci_s(a.get("ci_raw")), ci_s(a.get("ci_infl"))))
    L += ["", "## F. Kill-criterion 0A (T=7)", "", "| ứng viên | cover | C1 cover≥3% | năm >+0,5% | C2 ≥3/4 | netproxy_7d | C3 raw | C3 inflate | PASS raw | PASS inflate |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for g, f in res["F_kill"].items():
        L.append("| %s | %.1f%% | %s | %d/4 | %s | %s | %s | %s | %s | %s |" % (g, 100 * f["cover"], f["C1"], f["years_gt_0p5"], f["C2"],
                                                                      pc(f["netproxy7"]), f["C3_raw"], f["C3_infl"], f["pass_raw"], f["pass_infl"]))
    L += ["", "**VERDICT: %s**" % res["verdict"]]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["qv", "run"]); a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.stage == "qv":
        stage_qv(); return
    res, df, S, close = stage_run()
    res = tables(res, df, S)
    os.makedirs(CACHE, exist_ok=True)
    md = write_md(res)
    open(os.path.join(CACHE, "p0a_tables.md"), "w").write(md)
    json.dump(res, open(OUT_JSON, "w"), indent=1, ensure_ascii=False, default=float)
    log.info("WROTE %s + %s/p0a_tables.md", OUT_JSON, CACHE)
    print(md)


if __name__ == "__main__":
    main()
