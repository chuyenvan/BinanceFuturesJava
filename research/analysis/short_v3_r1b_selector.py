#!/usr/bin/env python3
"""short_v3_r1b_selector.py — PREREG_SHORT_V3_R1B (85a9b1ca): SELECTOR tai phut trigger tren 10 991 lenh R1.

Stage feat : trades_r1.csv (+ cand_*.parquet) -> 13 feature tai t (chi dung <= t), doc Aerospike CHI cac phut can,
             OI 5m (taker_buy) quet 1 luot oi_percoin_full.bin, funding /tmp/fund_cache.npz -> CACHE/r1b_feats.parquet
Stage model: WFO 6 fold nua nam (purge 72h), HistGradientBoostingRegressor tham so CO DINH, cham IC/tercile/CI/perm/
             importance/ablation -> docs/result/RESULT_SHORT_V3_R1B.json + CACHE/r1b_scores.parquet
Chay: python3 short_v3_r1b_selector.py feat ; python3 short_v3_r1b_selector.py model
"""
import argparse, glob, json, logging, os, sys, time
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
CACHE = "/home/ubuntu/claude_master/1002/r1_cache"
TRADES = os.path.join(CACHE, "trades_r1.csv")
FEAT = os.path.join(CACHE, "r1b_feats.parquet")
SCORES = os.path.join(CACHE, "r1b_scores.parquet")
OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R1B.json")
FUND = "/tmp/fund_cache.npz"
QVDIR = "/home/ubuntu/claude_master/1002/p0a_cache/qv"
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
OIBIN = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
SMAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
MIN, H, DAY, SLOT = 60000, 3600000, 86400000, 300000
H72 = 72 * H
DEV_END_MS = 1767225600000          # 2026-01-01 00:00 UTC (khong doc >=)
SEED, NREP, INFL, STRESS = 20260905, 2000, 1.18, 0.001
LOOKBACK = 60
FEATS = ["r60", "r15", "ext24", "volratio", "wick", "fund_now", "fund_sign", "takerLS",
         "tier", "listing_age", "btc_bull", "btc_r60", "n_trig_day"]
ABL = {"A1_bo_crowding_f6_f9": [f for f in FEATS if f not in ("fund_now", "fund_sign", "takerLS")],
       "A2_bo_context_f10_f14": [f for f in FEATS if f not in ("tier", "listing_age", "btc_bull", "btc_r60", "n_trig_day")],
       "A3_chi_gia_vol_f1_f5": ["r60", "r15", "ext24", "volratio", "wick"]}
PARAMS = dict(loss="squared_error", learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=100,
              l2_regularization=0.0, max_features=0.8, early_stopping=False, max_bins=255, random_state=SEED)
FOLDS = [("2023H1", "2023-01-01", "2023-07-01"), ("2023H2", "2023-07-01", "2024-01-01"),
         ("2024H1", "2024-01-01", "2024-07-01"), ("2024H2", "2024-07-01", "2025-01-01"),
         ("2025H1", "2025-01-01", "2025-07-01"), ("2025H2", "2025-07-01", "2026-01-01")]
log = logging.getLogger("r1b")


def setup_log():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def key_of(m):
    """phut UTC m (gio mo) -> key Aerospike TZ+7 (nhu R1)."""
    return time.strftime("%Y%m%d-%H%M", time.gmtime(m * 60 + 7 * 3600))


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10 ** 6)


def load_trades():
    tr = pd.read_csv(TRADES)
    tr = tr.sort_values("t", kind="stable").reset_index(drop=True)
    tr["entry_ms"] = (tr["t"].astype(np.int64) + 2) * MIN - 1
    tr["exit24_ms"] = (tr["S_B24_k"].astype(np.int64) + 1) * MIN - 1
    tr["exit12_ms"] = (tr["S_B12_k"].astype(np.int64) + 1) * MIN - 1
    tr["year"] = pd.to_datetime(tr["entry_ms"], unit="ms", utc=True).dt.year
    return tr


# ───────────────────────── Aerospike: chi doc cac phut can ─────────────────────────
def read_minutes(need):
    """need: dict phut -> set(sym). Tra dict (phut, sym) -> [O,H,L,C,V] (float) cho cap co ban ghi."""
    import aerospike, cramjam
    from short_pathexit_sim import parse_min
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    mins = sorted(need)
    assert max(mins) * MIN < DEV_END_MS, "doc phut >= 2026"
    out = {}; t0 = time.time(); nrec = 0
    for c0 in range(0, len(mins), 1000):
        ch = mins[c0:c0 + 1000]
        keys = [("test", "kline_1m_opt", key_of(m)) for m in ch]
        brs = None
        for _att in range(3):
            try:
                brs = cli.batch_read(keys).batch_records; break
            except Exception as e:
                log.warning("batch_read loi %s, thu lai", e); time.sleep(5)
        if brs is None:
            raise RuntimeError("batch_read that bai")
        for m, rr in zip(ch, brs):
            if rr.result != 0 or rr.record is None or not rr.record[2] or "data" not in rr.record[2]:
                continue
            d = parse_min(bytes(dec(rr.record[2]["data"]))); nrec += 1
            for s in need[m]:
                v = d.get(s)
                if v is not None:
                    out[(m, s)] = [float(x) for x in v]
        if (c0 // 1000) % 10 == 0:
            log.info("aerospike %d/%d phut, nrec=%d, %.0fs", c0 + len(ch), len(mins), nrec, time.time() - t0)
    cli.close()
    return out, nrec


def feats_1m(tr):
    """f2 r15, f3 ext24, f5 wick, f13 btc_r60 + sanity S2 (C[t] vs c_t, Cf[t-60] vs cf60). Cf[x] = close gan nhat <= x trong 60'."""
    T = tr["t"].to_numpy(np.int64); S = tr["sym"].to_numpy()
    base = {}
    for t, s in zip(T, S):
        for x, ss in ((t, (s, "BTCUSDT")), (t - 15, (s,)), (t - 60, (s, "BTCUSDT")), (t - 1440, (s,))):
            for q in ss:
                base.setdefault(int(x), set()).add(q)
    got, nrec1 = read_minutes(base)
    ok = lambda v: v is not None and v[3] > 0 and np.isfinite(v[3])
    miss = [(x, s) for x, ss in base.items() for s in ss if not ok(got.get((x, s)))]
    need2 = {}
    for x, s in miss:
        for k in range(1, LOOKBACK + 1):
            need2.setdefault(x - k, set()).add(s)
    got2, nrec2 = read_minutes(need2) if need2 else ({}, 0)
    log.info("1m: %d phut co ban (%d rec), thieu %d cap -> lui %d phut (%d rec)", len(base), nrec1, len(miss), len(need2), nrec2)

    def cf(x, s):
        """(close, phut_nguon) — phut_nguon <= x."""
        v = got.get((x, s))
        if ok(v):
            return v[3], x
        for k in range(1, LOOKBACK + 1):
            v = got2.get((x - k, s))
            if ok(v):
                return v[3], x - k
        return np.nan, -1

    n = len(tr)
    r15 = np.full(n, np.nan); ext24 = np.full(n, np.nan); wick = np.full(n, np.nan); btc = np.full(n, np.nan)
    ct_chk = np.zeros(n, bool); cf60_chk = np.zeros(n, bool); srcmax = np.full(n, -1, np.int64)
    cct = tr["c_t"].to_numpy(np.float64); ccf60 = tr["cf60"].to_numpy(np.float64)
    for i, (t, s) in enumerate(zip(T, S)):
        v = got.get((int(t), s))
        assert ok(v), "thieu ban ghi phut trigger %s %d" % (s, t)
        o_, h_, l_, c_ = v[0], v[1], v[2], v[3]
        ct_chk[i] = abs(c_ - cct[i]) <= 1e-6 * cct[i]
        c15, m15 = cf(int(t) - 15, s); c1440, m1440 = cf(int(t) - 1440, s); c60, m60 = cf(int(t) - 60, s)
        cf60_chk[i] = np.isfinite(c60) and abs(c60 - ccf60[i]) <= 1e-6 * ccf60[i]
        r15[i] = c_ / c15 - 1 if np.isfinite(c15) else np.nan
        ext24[i] = c_ / c1440 - 1 if np.isfinite(c1440) else np.nan
        if np.isfinite(h_) and np.isfinite(l_) and h_ > l_:
            wick[i] = (h_ - c_) / (h_ - l_)
        b0 = got.get((int(t), "BTCUSDT"))
        b60, mb60 = cf(int(t) - 60, "BTCUSDT")
        if ok(b0) and np.isfinite(b60):
            btc[i] = b0[3] / b60 - 1
        srcmax[i] = max(int(t), m15, m60, m1440, mb60)
    assert (srcmax <= T).all(), "S3: phut nguon 1m > t"
    s2 = dict(c_t_match=float(ct_chk.mean()), cf60_match=float(cf60_chk.mean()), n_miss_base=len(miss),
              nrec_base=nrec1, nrec_back=nrec2, n_minutes_read=len(base) + len(need2))
    log.info("S2 %s", s2)
    return dict(r15=r15, ext24=ext24, wick=wick, btc_r60=btc), s2


def feat_funding(tr):
    """f6 fund_now = PROXY TRE: rate cua su kien settle gan nhat co fundingTime <= T_t = (t+1)*60000-1."""
    z = np.load(FUND, allow_pickle=True)
    syms = [str(x) for x in z["syms"]]
    fts = z["ts"].astype(np.int64); frt = z["rt"].astype(np.float64); fsid = z["sid"].astype(np.int64)
    m = fts > 0
    fts, frt, fsid = fts[m], frt[m], fsid[m]
    o = np.lexsort((fts, fsid)); fts, frt, fsid = fts[o], frt[o], fsid[o]
    b = np.searchsorted(fsid, np.arange(len(syms) + 1))
    n2i = {s: i for i, s in enumerate(syms)}
    Tt = (tr["t"].to_numpy(np.int64) + 1) * MIN - 1
    fn = np.full(len(tr), np.nan); fage = np.full(len(tr), np.nan); used = np.full(len(tr), -1, np.int64)
    for s, g in tr.groupby("sym").groups.items():
        j = n2i.get(s)
        if j is None or b[j + 1] == b[j]:
            continue
        ts = fts[b[j]:b[j + 1]]; rt = frt[b[j]:b[j + 1]]
        gi = np.asarray(g)
        k = np.searchsorted(ts, Tt[gi], "right") - 1
        okk = k >= 0
        fn[gi[okk]] = rt[k[okk]]; used[gi[okk]] = ts[k[okk]]
        fage[gi[okk]] = (Tt[gi[okk]] - ts[k[okk]]) / H
    assert (used[used >= 0] <= Tt[used >= 0]).all(), "S3: fundingTime > T_t"
    sign = np.where(np.isnan(fn), np.nan, (fn < 0).astype(float))
    info = dict(cov=float(np.isfinite(fn).mean()), age_h_p50=float(np.nanmedian(fage)), age_h_p90=float(np.nanpercentile(fage, 90)))
    log.info("funding %s", info)
    return fn, sign, info


def feat_taker(tr):
    """f9: taker_buy (cot 5) cua oi_percoin_full.bin, dong ts <= (t+1)*60000 - 300000 gan nhat (lui toi da 12 slot)."""
    mp = pd.read_csv(SMAP)
    s2id = dict(zip(mp.symbol.astype(str), mp.symId.astype(int)))
    sid = np.array([s2id.get(s, -1) for s in tr["sym"]], np.int64)
    tsmax = (tr["t"].to_numpy(np.int64) + 1) * MIN - SLOT
    s0 = tsmax // SLOT
    cand = (sid[:, None] << 32) + (s0[:, None] - np.arange(12)[None, :])      # (n, 12)
    need = np.unique(cand[sid >= 0].ravel())
    val = np.full(len(need), np.nan, np.float32)
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 5)])
    mm = np.memmap(OIBIN, dtype=DT, mode="r")
    lo_ts = int(s0.min() - 12) * SLOT; hi_ts = int(s0.max()) * SLOT
    t0 = time.time(); nhit = 0; CH = 5_000_000
    for c0 in range(0, len(mm), CH):
        r = np.asarray(mm[c0:c0 + CH])
        ts = r["ts"].astype(np.int64)
        sel = (ts >= lo_ts) & (ts <= hi_ts)
        if not sel.any():
            continue
        key = (r["sym"][sel].astype(np.int64) << 32) + ts[sel] // SLOT
        p = np.searchsorted(need, key); p[p >= len(need)] = 0
        hit = need[p] == key
        val[p[hit]] = r["f"][sel][hit, 4]; nhit += int(hit.sum())
        if (c0 // CH) % 5 == 0:
            log.info("OI quet %d/%d hit=%d %.0fs", c0 + len(r), len(mm), nhit, time.time() - t0)
    del mm
    out = np.full(len(tr), np.nan); used = np.full(len(tr), -1, np.int64)
    for i in np.nonzero(sid >= 0)[0]:
        for k in range(12):
            p = np.searchsorted(need, cand[i, k])
            v = val[p]
            if np.isfinite(v):
                out[i] = float(v); used[i] = (s0[i] - k) * SLOT; break
    assert (used[used >= 0] <= tsmax[used >= 0]).all(), "S3: OI ts > (t+1)*60000-300000"
    yr = tr["year"].to_numpy()
    info = dict(sym_in_map=float((sid >= 0).mean()), cov=float(np.isfinite(out).mean()),
                cov_by_year={str(y): float(np.isfinite(out[yr == y]).mean()) for y in (2022, 2023, 2024, 2025)},
                lag_slot_mean=float(np.mean((s0 * SLOT - used)[used >= 0]) / SLOT))
    log.info("taker %s", info)
    return out, info


def feat_listing(tr):
    """f11: listing_day = min(ngay dau CLOSES_1H.bin (eday nhu R2), ngay dau nmin>0 cache qv); age cap 365."""
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64); sid = a["sym"].astype(np.int64); c = a["c"].astype(np.float32); del a
    m = (ts < DEV_END_MS) & np.isfinite(c) & (c > 0)
    first = pd.Series(ts[m]).groupby(sid[m]).min()
    mp = pd.read_csv(SMAP); id2 = dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))
    fd_cl = {id2[int(k)]: int((v - H) // DAY) for k, v in first.items() if int(k) in id2}
    q = pd.concat([pd.read_parquet(f, columns=["date", "sym", "nmin"]) for f in sorted(glob.glob(QVDIR + "/*.parquet"))], ignore_index=True)
    q = q[q.nmin > 0]
    q["ed"] = pd.to_datetime(q["date"]).values.astype("datetime64[ms]").astype(np.int64) // DAY
    fd_qv = q.groupby("sym")["ed"].min().to_dict()
    ld = np.array([min([x for x in (fd_cl.get(s), fd_qv.get(s)) if x is not None], default=-10 ** 9) for s in tr["sym"]], np.int64)
    tms = tr["t"].to_numpy(np.int64) * MIN
    has = ld > -10 ** 9
    age = np.where(has, np.minimum(365.0, (tms - ld * DAY) / DAY), np.nan)
    assert (age[has] >= 0).all(), "S3: listing_day > ngay(t)"
    src = np.array(["both" if (fd_cl.get(s) is not None and fd_qv.get(s) is not None) else
                    ("closes" if fd_cl.get(s) is not None else ("qv" if fd_qv.get(s) is not None else "none")) for s in tr["sym"]])
    info = dict(cov=float(has.mean()), frac_cap365=float((age >= 365).mean()), src_counts=pd.Series(src).value_counts().to_dict(),
                age_p10=float(np.nanpercentile(age, 10)), age_p50=float(np.nanpercentile(age, 50)))
    log.info("listing %s", info)
    return age, info


def feat_ntrig(tr):
    """f14: so trigger KHAC trong tap co t' in [t-1440, t-1]."""
    t = tr["t"].to_numpy(np.int64)
    assert (np.diff(t) >= 0).all()
    lo = np.searchsorted(t, t - 1440, "left"); hi = np.searchsorted(t, t, "left")
    return (hi - lo).astype(float)


def stage_feat():
    tr = load_trades()
    s1 = dict(n=int(len(tr)), mean_y24=float(tr["S_B24_net"].mean()), mean_y12=float(tr["S_B12_net"].mean()))
    s1["PASS"] = bool(s1["n"] == 10991 and abs(s1["mean_y24"] - 0.00170) <= 0.00005 and abs(s1["mean_y12"] - 0.00101) <= 0.00005)
    log.info("S1 %s", s1)
    assert s1["PASS"], "S1 FAIL"
    cd = pd.concat([pd.read_parquet(f, columns=["sym", "t", "c_t", "cf60"]) for f in sorted(glob.glob(os.path.join(CACHE, "cand_*.parquet")))])
    tr = tr.merge(cd, on=["sym", "t"], how="left", validate="one_to_one")
    assert tr["c_t"].notna().all() and len(tr) == 10991
    F = pd.DataFrame(index=tr.index)
    F["r60"] = tr["r60"].to_numpy(np.float64)
    F["volratio"] = (tr["W0"] / tr["Mnen"]).to_numpy(np.float64)
    f1m, s2 = feats_1m(tr)
    for k, v in f1m.items():
        F[k] = v
    F["fund_now"], F["fund_sign"], finfo = feat_funding(tr)
    F["takerLS"], tinfo = feat_taker(tr)
    F["tier"] = tr["tier"].map({"NHO": 0.0, "VUA": 1.0, "LON": 2.0}).astype(float)
    F["listing_age"], linfo = feat_listing(tr)
    F["btc_bull"] = tr["regime"].map({"BULL": 1.0, "BEAR": 0.0}).astype(float)
    F["n_trig_day"] = feat_ntrig(tr)
    F = F[FEATS]
    s2["PASS"] = bool(s2["c_t_match"] >= 0.995 and s2["cf60_match"] >= 0.995)
    assert s2["PASS"], "S2 FAIL %s" % s2
    out = pd.concat([tr[["sym", "t", "entry_ms", "exit24_ms", "exit12_ms", "year", "S_B24_net", "S_B24_r", "S_B12_net", "S_B12_r"]], F], axis=1)
    out.to_parquet(FEAT, index=False)
    desc = {f: dict(cov=float(F[f].notna().mean()), p10=float(F[f].quantile(0.1)), p50=float(F[f].median()), p90=float(F[f].quantile(0.9)))
            for f in FEATS}
    meta = dict(S1=s1, S2=s2, funding=finfo, taker=tinfo, listing=linfo, feat_desc=desc,
                S3="assert theo dong: phut nguon 1m <= t; fundingTime <= (t+1)*60000-1; OI ts <= (t+1)*60000-300000; listing_day <= t; f14 t' <= t-1")
    json.dump(meta, open(os.path.join(CACHE, "r1b_feat_meta.json"), "w"), indent=1, default=str)
    log.info("FEAT xong -> %s", FEAT)


# ───────────────────────── model / cham ─────────────────────────
def spearman(a, b):
    a = pd.Series(np.asarray(a, np.float64)).rank().to_numpy(); b = pd.Series(np.asarray(b, np.float64)).rank().to_numpy()
    return float(np.corrcoef(a, b)[0, 1])


def ci_block(v, ems):
    v = np.asarray(v, np.float64)
    _, inv = np.unique(np.asarray(ems, np.int64) // H72, return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(np.float64)
    rng = np.random.default_rng(SEED); nb = len(sums); bs = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb); bs[b] = sums[p].sum() / cnts[p].sum()
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)); mu = float(v.mean())
    return dict(raw=[lo, hi], infl=[mu - (mu - lo) * INFL, mu + (hi - mu) * INFL], nblock=int(nb))


def bstats(net, rsn, ems, yr, ci=True):
    net = np.asarray(net, np.float64)
    d = dict(n=int(len(net)), mean=float(net.mean()), median=float(np.median(net)), win=float((net > 0).mean()),
             sl_rate=float((np.asarray(rsn) == 1).mean()),
             by_year={str(y): (float(net[yr == y].mean()) if (yr == y).any() else None) for y in (2023, 2024, 2025)},
             n_by_year={str(y): int((yr == y).sum()) for y in (2023, 2024, 2025)},
             sl_by_year={str(y): (float((np.asarray(rsn)[yr == y] == 1).mean()) if (yr == y).any() else None) for y in (2023, 2024, 2025)})
    if ci:
        c = ci_block(net, ems); d.update(ci_raw=c["raw"], ci_infl=c["infl"], nblock=c["nblock"])
    return d


def fold_sets(D):
    """-> list (name, train_idx, test_idx); assert khong ro."""
    out = []
    ex = np.maximum(D["exit24_ms"].to_numpy(np.int64), D["exit12_ms"].to_numpy(np.int64))
    em = D["entry_ms"].to_numpy(np.int64)
    seen = np.zeros(len(D), int)
    for nm, a, b in FOLDS:
        st, en = ms(a), ms(b)
        te = np.nonzero((em >= st) & (em < en))[0]
        trn = np.nonzero(ex < st - H72)[0]
        assert len(np.intersect1d(te, trn)) == 0 and ex[trn].max() < st - H72 and em[trn].max() < st
        seen[te] += 1
        out.append((nm, trn, te))
    oos = em >= ms("2023-01-01")
    assert (seen[oos] == 1).all() and (seen[~oos] == 0).all()
    return out


def wfo(D, cols, y, folds):
    from sklearn.ensemble import HistGradientBoostingRegressor
    X = D[cols].to_numpy(np.float64)
    score = np.full(len(D), np.nan); fid = np.full(len(D), -1); ics = []; models = []
    for k, (nm, trn, te) in enumerate(folds):
        m = HistGradientBoostingRegressor(**PARAMS).fit(X[trn], y[trn])
        score[te] = m.predict(X[te]); fid[te] = k
        ics.append(spearman(score[te], y[te])); models.append(m)
    return score, fid, ics, models


def buckets(score, fid, nq):
    """Trong moi fold: rank ordinal cua score -> nhom 0..nq-1 (nq-1 = score cao nhat). Khong dung nhan."""
    b = np.full(len(score), -1)
    for k in np.unique(fid[fid >= 0]):
        ix = np.nonzero(fid == k)[0]
        r = pd.Series(score[ix]).rank(method="first").to_numpy() - 1
        b[ix] = np.floor(r * nq / len(ix)).astype(int)
    return b


def evaluate(D, score, fid, ics, ycol, rcol, full=True):
    y = D[ycol].to_numpy(np.float64); r = D[rcol].to_numpy(); em = D["entry_ms"].to_numpy(np.int64); yr = D["year"].to_numpy()
    oos = fid >= 0
    t3 = buckets(score, fid, 3)
    res = dict(ic_fold={FOLDS[k][0]: ics[k] for k in range(len(ics))}, ic_oos_mean=float(np.mean(ics)),
               ic_pos_folds=int(sum(1 for x in ics if x > 0)), ic_pooled=spearman(score[oos], y[oos]))
    names = {2: "TOP", 1: "MID", 0: "BOT"}
    res["tercile"] = {names[q]: bstats(y[t3 == q], r[t3 == q], em[t3 == q], yr[t3 == q], ci=full or q == 2) for q in (2, 1, 0)}
    res["ALL_OOS"] = bstats(y[oos], r[oos], em[oos], yr[oos], ci=full)
    if full:
        t10 = buckets(score, fid, 10)
        res["decile"] = {str(q): dict(n=int((t10 == q).sum()), mean=float(y[t10 == q].mean()), sl_rate=float((r[t10 == q] == 1).mean()))
                         for q in range(10)}
        res["tercile_by_fold"] = {FOLDS[k][0]: {names[q]: float(y[(fid == k) & (t3 == q)].mean()) for q in (2, 1, 0)}
                                  for k in range(len(ics))}
    return res, t3


def stage_model():
    import sklearn
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.inspection import permutation_importance
    D = pd.read_parquet(FEAT)
    assert len(D) == 10991
    folds = fold_sets(D)
    finfo = {nm: dict(n_train=int(len(trn)), n_test=int(len(te)),
                      train_max_exit=str(pd.Timestamp(int(np.maximum(D["exit24_ms"], D["exit12_ms"]).to_numpy()[trn].max()), unit="ms")),
                      purge_cut=str(pd.Timestamp(ms(a) - H72, unit="ms"))) for (nm, trn, te), (_, a, _b) in zip(folds, FOLDS)}
    log.info("folds %s", finfo)
    y24 = D["S_B24_net"].to_numpy(np.float64); y12 = D["S_B12_net"].to_numpy(np.float64)
    X = D[FEATS].to_numpy(np.float64); nm0, trn0, te0 = folds[0]
    p1 = HistGradientBoostingRegressor(**PARAMS).fit(X[trn0], y24[trn0]).predict(X[te0])
    p2 = HistGradientBoostingRegressor(**PARAMS).fit(X[trn0], y24[trn0]).predict(X[te0])
    s5 = dict(max_abs_diff=float(np.abs(p1 - p2).max()), PASS=bool(np.array_equal(p1, p2)))
    log.info("S5 %s", s5)
    s24, fid, ic24, mods = wfo(D, FEATS, y24, folds)
    R24, t3 = evaluate(D, s24, fid, ic24, "S_B24_net", "S_B24_r")
    log.info("M24 IC fold %s mean %.4f TOP %s", np.round(ic24, 4), R24["ic_oos_mean"], R24["tercile"]["TOP"]["mean"])
    s12, fid12, ic12, _m = wfo(D, FEATS, y12, folds)
    R12, _t = evaluate(D, s12, fid12, ic12, "S_B12_net", "S_B12_r")
    perm = np.random.default_rng(SEED).permutation(len(D))
    y24p = y24[perm]
    sp, fidp, icp, _m = wfo(D, FEATS, y24p, folds)
    ic_perm_real = [spearman(sp[fidp == k], y24[fidp == k]) for k in range(len(folds))]
    PERM = dict(ic_fold=icp, ic_mean=float(np.mean(icp)), ic_vs_real_fold=ic_perm_real, ic_vs_real_mean=float(np.mean(ic_perm_real)))
    log.info("PERM %s", PERM)
    scorer = lambda est, Xs, ys: spearman(est.predict(Xs), ys)
    imp = np.zeros((len(folds), len(FEATS)))
    for k, ((nm, trn, te), m) in enumerate(zip(folds, mods)):
        pi = permutation_importance(m, X[te], y24[te], scoring=scorer, n_repeats=5, random_state=SEED)
        imp[k] = pi.importances_mean
    IMP = {f: dict(mean=float(imp[:, j].mean()), by_fold=[float(x) for x in imp[:, j]]) for j, f in enumerate(FEATS)}
    ABLR = {}
    for an, cols in ABL.items():
        sa, fa, ica, _m = wfo(D, cols, y24, folds)
        ra, _t = evaluate(D, sa, fa, ica, "S_B24_net", "S_B24_r", full=False)
        ABLR[an] = dict(cols=cols, ic_fold=ra["ic_fold"], ic_oos_mean=ra["ic_oos_mean"], ic_pos_folds=ra["ic_pos_folds"],
                        top_mean=ra["tercile"]["TOP"]["mean"], top_sl=ra["tercile"]["TOP"]["sl_rate"],
                        top_ci_raw=ra["tercile"]["TOP"]["ci_raw"], top_by_year=ra["tercile"]["TOP"]["by_year"])
        log.info("ABL %s IC %.4f top %.5f", an, ra["ic_oos_mean"], ra["tercile"]["TOP"]["mean"])
    T = R24["tercile"]["TOP"]
    GO = dict(C1=bool(R24["ic_oos_mean"] > 0.05 and R24["ic_pos_folds"] >= 5),
              C2=bool(T["mean"] > 0 and T["ci_raw"][0] > 0 and T["ci_infl"][0] > 0),
              C3=bool(all(v is not None and v > 0 for v in T["by_year"].values())),
              C4=bool(T["sl_rate"] <= 0.25), C5=bool(T["mean"] - STRESS > 0),
              C6=bool(-0.02 <= PERM["ic_mean"] <= 0.02))
    GO["ALL"] = bool(all(GO.values()))
    verdict = "GO" if GO["ALL"] else "NO-GO"
    log.info("GO %s -> %s", GO, verdict)
    sc = D[["sym", "t", "entry_ms", "year", "S_B24_net", "S_B24_r", "S_B12_net"]].copy()
    sc["fold"] = fid; sc["score24"] = s24; sc["tercile24"] = t3; sc["score12"] = s12; sc["score_perm"] = sp
    sc.to_parquet(SCORES, index=False)
    fmeta = json.load(open(os.path.join(CACHE, "r1b_feat_meta.json")))
    res = dict(prereg="PREREG_SHORT_V3_R1B (85a9b1ca)", program="PROGRAM_SHORT_V3 ADDENDUM 1 (df2ce308)", source_r1="3fea4f50",
               conv=dict(params=PARAMS, sklearn=sklearn.__version__, feats=FEATS, dropped={"f8 dOI_60": "khong co OI tho trong DEV"},
                         nrep=NREP, seed=SEED, infl=INFL, stress=STRESS, block_h=72, purge_h=72),
               sanity=dict(S1=fmeta["S1"], S2=fmeta["S2"], S3=fmeta["S3"], S4=finfo, S5=s5),
               feat_sources=dict(funding=fmeta["funding"], taker=fmeta["taker"], listing=fmeta["listing"], desc=fmeta["feat_desc"]),
               verdict=verdict, go=GO, M24=R24, M12_phu=R12, permutation=PERM, importance=IMP, ablation=ABLR)
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
    log.info("VERDICT %s -> %s", verdict, OUT_JSON)


def main():
    setup_log()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["feat", "model"])
    a = ap.parse_args()
    stage_feat() if a.stage == "feat" else stage_model()


if __name__ == "__main__":
    main()
