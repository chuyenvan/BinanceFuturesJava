#!/usr/bin/env python3
"""short_gateclosed_sim.py — PREREG_SHORT_GATECLOSED: SHORT top-K8 selector (PA_t15_E10_S42) tai tick GATE LONG DONG
(p15 < 0,008), trailing CO ARM, funding EXACT, du lieu sach v2 (lineage v2 + CLOSES_1H_v2 + Aerospike 1m).

Stage picks : bins PA_t15_E10_S42 (toan universe, moi tick 15') x gate p15_dev x lineage v2 x CLOSES_1H_v2
              -> 3 tap: SG (gate dong, top-K8 score), SO (gate mo, top-K8), RG (gate dong, random-K8); cooldown 24h/coin.
Stage sim   : stream Aerospike test.kline_1m_opt theo THANG UTC (chi decode symbol can), exit E1/E2/E3
              (SHORT cho SG/SO/RG, LONG guong cho SG = doi chung b) -> CACHE/tr_YYYYMM.parquet
Stage sanity: thang 202403 — so loop vs vectorized ca 1 ngay, 10 lenh mau doc lai Aerospike doc lap + loop.
Stage report: funding exact, CI block-72h, theo nam, theo ngay, bo top-5 ngay, verdict GO -> RESULT json.
Chay: python3 short_gateclosed_sim.py picks | sim [--months all] | sanity | report
"""
import argparse, glob, json, logging, os, struct, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
CACHE = "/home/ubuntu/claude_master/1003/sgc_cache"
BINS = "/home/ubuntu/sm_pathexit/sm/PA_t15_E10_S42"
GATE = os.path.join(REPO, "research/parity/data/p15_dev.csv")
LIN = os.path.join(REPO, "data/meta/symbol_lineage_v2.csv")
C1H = "/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin"
FUND = "/tmp/fund_cache.npz"
OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_GATECLOSED.json")
MIN = 60000
H = 3600000
H72 = 72 * H
DEV_M0 = 1640995200000 // MIN          # 2022-01-01 00:00 UTC
DEV_END = 1767225600000 // MIN         # 2026-01-01 00:00 UTC (phut nay KHONG doc)
GATE_THR = 0.008
K_SEL = 8
CD_MIN = 1440                          # cooldown 24h/coin (tinh tu tick vao lenh)
OFF_E = 15                             # entry = close phut m0+15 (t+1 sau phut cuoi nen 15' m0+14)
TSMAX = 4320
FEE = 0.00112
NREP, SEED = 2000, 20260905
K_MULT = 3
INFL = float(np.sqrt(2 * np.log(K_MULT)))   # 1,4823
RSEED = 20261003
EXITS = {"E1": (0.05, 0.03, 0.10, 4320), "E2": (0.05, 0.03, np.inf, 4320), "E3": (0.03, 0.02, 0.10, 1440)}
BAD_STATUS = {"index", "stable/fiat-like"}
SANITY_YM = "202403"
SANITY_DAY = "2024-03-05"
_BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
_C1H_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
log = logging.getLogger("sgc")


def setup_log():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(process)d %(levelname)s %(message)s")


def key_of(m):
    """phut UTC m (gio mo) -> key Aerospike TZ+7."""
    return time.strftime("%Y%m%d-%H%M", time.gmtime(m * 60 + 7 * 3600))


def to_min(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10 ** 6 // MIN)


# ───────────────────────── picks ─────────────────────────
def load_lineage():
    lin = pd.read_csv(LIN)
    lin = lin[~lin["status"].isin(BAD_STATUS)].copy()
    lin["f_min"] = lin["first_real_ts"].map(to_min)
    lin["l_min"] = lin["last_real_ts"].map(to_min)
    return lin


def cooldown(ts_min, sym):
    """Theo thu tu dua vao (ts tang, hang trong tick); giu neu coin chua vao trong 24h truoc."""
    keep = np.zeros(len(ts_min), bool); last = {}
    for i in range(len(ts_min)):
        s = int(sym[i]); t = int(ts_min[i]); lt = last.get(s)
        if lt is None or t >= lt + CD_MIN:
            keep[i] = True; last[s] = t
    return keep


def topk(ts, key, k):
    """Chi so cua top-k theo key giam dan trong tung ts (ts da sort tang)."""
    o = np.lexsort((-key, ts))
    tso = ts[o]
    start = np.r_[0, np.flatnonzero(np.diff(tso)) + 1]
    rank = np.arange(len(o)) - np.repeat(start, np.diff(np.r_[start, len(o)]))
    sel = rank < k
    return o[sel], rank[sel]


def stage_picks():
    os.makedirs(CACHE, exist_ok=True)
    fs = sorted(glob.glob(os.path.join(BINS, "predict_wf_*.bin")))
    assert len(fs) == 16, fs
    a = np.concatenate([np.fromfile(f, dtype=_BIN_DT) for f in fs])
    ts = a["ts"].astype(np.int64); sy = a["sym"].astype(np.int64); p = a["p3"].astype(np.float64)
    del a
    info = {"bins_rows": int(len(ts)), "bins_ticks": int(len(np.unique(ts)))}
    m0 = ts // MIN; e = m0 + OFF_E
    ok = np.isfinite(p) & (m0 >= DEV_M0) & (e + TSMAX <= DEV_END - 1) & (ts % (15 * MIN) == 0)
    lin = load_lineage()
    NS = int(max(sy.max(), lin["symId"].max())) + 1
    fmin = np.full(NS, np.iinfo(np.int64).max); lmin = np.full(NS, -1, np.int64)
    fmin[lin["symId"].to_numpy()] = lin["f_min"].to_numpy(); lmin[lin["symId"].to_numpy()] = lin["l_min"].to_numpy()
    ok_lin = (fmin[sy] <= m0) & (e < lmin[sy])
    info["drop_lineage_rows"] = int((ok & ~ok_lin).sum())
    ok &= ok_lin
    c = np.fromfile(C1H, dtype=_C1H_DT)
    cfin = np.isfinite(c["c"].astype(np.float64))
    ck = np.unique(c["ts"].astype(np.int64)[cfin] * 1024 + c["sym"].astype(np.int64)[cfin])
    del c, cfin
    hk = (e * MIN) // H * H                       # gio 1h da DONG gan nhat truoc phut entry (ts = gio dong)
    ok_c = np.isin(hk * 1024 + sy, ck)
    info["drop_c1h_rows"] = int((ok & ~ok_c).sum())
    ok &= ok_c
    ts, sy, p, m0 = ts[ok], sy[ok], p[ok], m0[ok]
    g = pd.read_csv(GATE)
    gts = g["ts"].to_numpy(np.int64); gp = g["predReturn15M"].to_numpy(np.float64)
    j = np.searchsorted(gts, ts)
    jj = np.minimum(j, len(gts) - 1)
    hit = gts[jj] == ts                           # p15 tai phut m0 (= cot p15 cua cand_dev_x1, khop 100%)
    p15 = np.where(hit, gp[jj], np.nan)
    info["drop_nogate_rows"] = int((~np.isfinite(p15)).sum())
    keep = np.isfinite(p15)
    ts, sy, p, m0, p15 = ts[keep], sy[keep], p[keep], m0[keep], p15[keep]
    closed = p15 < GATE_THR
    tk = pd.DataFrame({"ts": ts, "closed": closed}).drop_duplicates("ts")
    tk["yr"] = pd.to_datetime(tk["ts"], unit="ms", utc=True).dt.year
    info["ticks_by_year"] = {str(y): {"closed": int(gr["closed"].sum()), "open": int((~gr["closed"]).sum())}
                             for y, gr in tk.groupby("yr")}
    info["elig_rows_per_tick_median"] = float(pd.Series(ts).value_counts().median())
    id2n = dict(zip(lin["symId"], lin["symbol"]))
    rng = np.random.default_rng(RSEED)
    u = rng.random(len(ts))
    out = []
    for setn, msk, key in (("SG", closed, p), ("SO", ~closed, p), ("RG", closed, u)):
        idx = np.flatnonzero(msk)
        sel, rk = topk(ts[idx], key[idx], K_SEL)
        ii = idx[sel]
        o = np.lexsort((rk, ts[ii])); ii = ii[o]; rk = rk[o]
        kc = cooldown(m0[ii], sy[ii])
        info["n_%s_topk" % setn] = int(len(ii)); info["n_%s_after_cd" % setn] = int(kc.sum())
        ii = ii[kc]; rk = rk[kc]
        out.append(pd.DataFrame({"set": setn, "ts": ts[ii], "m0": m0[ii], "sym": sy[ii], "rank": rk,
                                 "p": p[ii], "u": u[ii], "p15": p15[ii]}))
    pk = pd.concat(out, ignore_index=True)
    pk["symbol"] = pk["sym"].map(id2n)
    pk["e"] = pk["m0"] + OFF_E
    pk["ym"] = pd.to_datetime(pk["e"] * MIN, unit="ms", utc=True).dt.strftime("%Y%m")
    yr = pd.to_datetime(pk["e"] * MIN, unit="ms", utc=True).dt.year
    info["picks_by_set_year"] = {s: {str(y): int(n) for y, n in gr.groupby(yr[gr.index]).size().items()}
                                 for s, gr in pk.groupby("set")}
    info["n_sym_by_set"] = {s: int(gr["sym"].nunique()) for s, gr in pk.groupby("set")}
    pk.to_parquet(os.path.join(CACHE, "picks.parquet"))
    json.dump(info, open(os.path.join(CACHE, "picks_info.json"), "w"), indent=1)
    log.info("picks %s", json.dumps(info))


# ───────────────────────── 1m stream (tai dung parse_min cua short_pathexit_sim / short_v3_r1_fade) ─────────
def stream(b0, b1, need, tag):
    """Doc phut b0..b1 (UTC, b1 < DEV_END) cho cac symbol trong `need` (list ten) -> arr (5, N, S) [O,H,L,C,V].
    Gia <= 0 -> NaN. Phut thieu -> NaN."""
    import aerospike, cramjam
    from short_pathexit_sim import parse_min
    assert b1 < DEV_END
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    N = b1 - b0 + 1; S = len(need); col = {n: i for i, n in enumerate(need)}
    arr = np.full((5, N, S), np.nan, np.float32)
    t0 = time.time(); nrec = 0
    for d0 in range(b0, b1 + 1, 1440):
        ms = list(range(d0, min(d0 + 1440, b1 + 1)))
        keys = [("test", "kline_1m_opt", key_of(m)) for m in ms]
        brs = None
        for _att in range(3):
            try:
                brs = cli.batch_read(keys).batch_records
                break
            except Exception as ex:
                log.warning("%s batch_read loi %s, thu lai", tag, ex); time.sleep(5)
        if brs is None:
            raise RuntimeError("batch_read that bai")
        for k, rr in enumerate(brs):
            if rr.result != 0 or rr.record is None or not rr.record[2] or "data" not in rr.record[2]:
                continue
            d = parse_min(bytes(dec(rr.record[2]["data"])))
            cols = [col[nm] for nm in d if nm in col]
            if cols:
                arr[:, ms[k] - b0, cols] = np.asarray([d[nm] for nm in d if nm in col], np.float32).T
            nrec += 1
    cli.close()
    for f in range(4):
        x = arr[f]; x[~(x > 0)] = np.nan
    log.info("%s stream %d phut nrec=%d S=%d %.0fs", tag, N, nrec, S, time.time() - t0)
    return arr


# ───────────────────────── exit (vectorized + loop tham chieu) ─────────────────────────
def exit_vec(Hw, Lw, Ow, Cw, P, a, g, s, TS, side):
    """Cua so = phut e+1..e+L (float64), Cw da ffill. side -1 SHORT / +1 LONG. Muc stop phut j chi dung du lieu
    den j-1 (run khoi tao = P). Muc hieu luc = stop GAN gia hon trong {trailing (neu da arm), SL cung}.
    Kich: SHORT High_j >= muc / LONG Low_j <= muc; fill = max/min(muc, Open_j) (gap-open -> open).
    -> (pnl, k_exit (chi so trong cua so), reason 0 TIME / 1 SL / 2 TRAIL / 3 DELIST)."""
    L = len(Hw); n = min(TS, L)
    with np.errstate(all="ignore"):
        if side < 0:
            lw = np.where(np.isfinite(Lw[:n]), Lw[:n], np.inf)
            run = np.minimum.accumulate(np.concatenate(([P], lw)))[:-1]
            armed = run <= P * (1 - a)
            level = np.minimum(np.where(armed, run * (1 + g), np.inf), P * (1 + s))
            hit = Hw[:n] >= level
        else:
            hw = np.where(np.isfinite(Hw[:n]), Hw[:n], -np.inf)
            run = np.maximum.accumulate(np.concatenate(([P], hw)))[:-1]
            armed = run >= P * (1 + a)
            level = np.maximum(np.where(armed, run * (1 - g), -np.inf), P * (1 - s))
            hit = Lw[:n] <= level
    if hit.any():
        k = int(np.argmax(hit)); lv = float(level[k]); o = Ow[k]
        if side < 0:
            px = max(lv, o) if np.isfinite(o) else lv
        else:
            px = min(lv, o) if np.isfinite(o) else lv
        if side < 0:
            rs = 2 if (armed[k] and run[k] * (1 + g) <= P * (1 + s)) else 1
        else:
            rs = 2 if (armed[k] and run[k] * (1 - g) >= P * (1 - s)) else 1
    else:
        k = n - 1; px = float(Cw[k]); rs = 0 if n == TS else 3
    return ((1 - px / P) if side < 0 else (px / P - 1)), k, rs


def exit_loop(Hw, Lw, Ow, Cw, P, a, g, s, TS, side):
    """Tham chieu loop thuan (khong numpy accumulate)."""
    L = len(Hw); n = min(TS, L); run = P
    for j in range(n):
        h, l, o = Hw[j], Lw[j], Ow[j]
        if side < 0:
            armed = run <= P * (1 - a)
            trail = run * (1 + g) if armed else float("inf")
            sl = P * (1 + s)
            lv = min(trail, sl)
            if h == h and h >= lv:
                px = max(lv, o) if o == o else lv
                return 1 - px / P, j, (2 if trail <= sl else 1)
            if l == l and l < run:
                run = l
        else:
            armed = run >= P * (1 + a)
            trail = run * (1 - g) if armed else float("-inf")
            sl = P * (1 - s)
            lv = max(trail, sl)
            if l == l and l <= lv:
                px = min(lv, o) if o == o else lv
                return px / P - 1, j, (2 if trail >= sl else 1)
            if h == h and h > run:
                run = h
    px = Cw[n - 1]
    return ((1 - px / P) if side < 0 else (px / P - 1)), n - 1, (0 if n == TS else 3)


# ───────────────────────── sim theo thang ─────────────────────────
def ffill_from(x, P):
    x = x.copy()
    if not np.isfinite(x[0]):
        x[0] = P
    m = np.isfinite(x)
    idx = np.where(m, np.arange(len(x)), 0)
    np.maximum.accumulate(idx, out=idx)
    return x[idx]


def window(arr, c, e, b0, L):
    i0 = e + 1 - b0
    O, Hh, Lo, C = (arr[f, i0:i0 + L, c].astype(np.float64) for f in range(4))
    return Hh, Lo, O, C


def trade_cells(Hw, Lw, Ow, Cw, P, sides, fn=exit_vec):
    out = {}
    for side, pre in sides:
        for nm, (a, g, s, TS) in EXITS.items():
            out[pre + nm] = fn(Hw, Lw, Ow, Cw, P, a, g, s, TS, side)
    return out


def sides_of(setn):
    return ((-1, "S_"), (1, "L_")) if setn == "SG" else ((-1, "S_"),)


def sim_month(ym, pk=None, save=True):
    setup_log()
    fp = os.path.join(CACHE, "tr_%s.parquet" % ym)
    if save and os.path.exists(fp):
        return ym, "skip"
    if pk is None:
        pk = pd.read_parquet(os.path.join(CACHE, "picks.parquet"))
        pk = pk[pk["ym"] == ym].reset_index(drop=True)
    lin = load_lineage(); lmin = dict(zip(lin["symbol"], lin["l_min"]))
    need = sorted(pk["symbol"].unique())
    b0 = int(pk["e"].min()); b1 = min(int(pk["e"].max()) + TSMAX, DEV_END - 1)
    arr = stream(b0, b1, need, ym)
    col = {n: i for i, n in enumerate(need)}
    rows = []
    for r in pk.itertuples(index=False):
        c = col[r.symbol]; e = int(r.e)
        assert e == r.m0 + OFF_E and e > r.m0 + 14 and r.ts == r.m0 * MIN      # causal: entry sau dong nen 15'
        P = float(arr[3, e - b0, c])
        L = int(min(TSMAX, lmin[r.symbol] - e))
        d = {"set": r.set, "ts": int(r.ts), "m0": int(r.m0), "e": e, "sym": int(r.sym), "symbol": r.symbol,
             "rank": int(r.rank), "p": float(r.p), "p15": float(r.p15), "P": P, "L": L}
        if not (np.isfinite(P) and P > 0) or L < 1:
            d["ok"] = False; rows.append(d); continue
        Hw, Lw, Ow, Cw = window(arr, c, e, b0, L)
        assert len(Hw) == L and e + L <= b1
        Cw = ffill_from(Cw, P)
        d["ok"] = True; d["cov"] = float(np.isfinite(Hw).mean()); d["v_e"] = float(arr[4, e - b0, c])
        for nm, (pnl, k, rs) in trade_cells(Hw, Lw, Ow, Cw, P, sides_of(r.set)).items():
            d[nm + "_p"] = pnl; d[nm + "_x"] = e + 1 + k; d[nm + "_r"] = rs
        rows.append(d)
    df = pd.DataFrame(rows)
    if save:
        df.to_parquet(fp)
    log.info("%s xong %d lenh (ok %d)", ym, len(df), int(df["ok"].sum()))
    if save:
        return ym, len(df)
    return df, arr, b0, need


# ───────────────────────── funding EXACT + thong ke ─────────────────────────
class Fund:
    def __init__(self):
        z = np.load(FUND, allow_pickle=True)
        self.syms = [str(x) for x in z["syms"]]
        ts = z["ts"].astype(np.int64) // H * H; rt = z["rt"].astype(np.float64); sid = z["sid"].astype(np.int64)
        m = ts > 0
        ts, rt, sid = ts[m], rt[m], sid[m]
        o = np.lexsort((ts, sid)); self.ts, self.rt, self.sid = ts[o], rt[o], sid[o]
        self.bnd = np.searchsorted(self.sid, np.arange(len(self.syms) + 1))
        self.n2i = {n: i for i, n in enumerate(self.syms)}

    def window(self, symbols, ent_ms, ex_ms):
        """Sum rate cac ky funding co fundingTime (chuan hoa gio tron) trong (ent_ms, ex_ms]. -> (sum, has_sym)."""
        res = np.zeros(len(symbols)); has = np.zeros(len(symbols), bool)
        sr = pd.Series(np.arange(len(symbols))).groupby(np.asarray(symbols)).groups
        for sym, gi in sr.items():
            j = self.n2i.get(sym)
            if j is None or self.bnd[j + 1] == self.bnd[j]:
                continue
            gi = np.asarray(gi); has[gi] = True
            ts = self.ts[self.bnd[j]:self.bnd[j + 1]]
            cum = np.concatenate(([0.0], np.cumsum(self.rt[self.bnd[j]:self.bnd[j + 1]])))
            res[gi] = cum[np.searchsorted(ts, ex_ms[gi], "right")] - cum[np.searchsorted(ts, ent_ms[gi], "right")]
        return res, has


def _blocks(ems):
    return np.asarray(ems, np.int64) // H72


def ci_block(v, ems):
    v = np.asarray(v, np.float64)
    _, inv = np.unique(_blocks(ems), return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(np.float64)
    rng = np.random.default_rng(SEED); nb = len(sums); bs = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb); bs[b] = sums[p].sum() / cnts[p].sum()
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)); mu = float(v.mean())
    return dict(raw=[lo, hi], infl=[mu - (mu - lo) * INFL, mu + (hi - mu) * INFL], nblock=int(nb))


def ci_diff(v1, e1, v2, e2):
    """CI block-72h cua mean(v1) - mean(v2), resample CHUNG tap block (ghep theo block thoi gian)."""
    b1, b2 = _blocks(e1), _blocks(e2)
    ub = np.unique(np.concatenate([b1, b2])); i1 = np.searchsorted(ub, b1); i2 = np.searchsorted(ub, b2)
    nb = len(ub)
    s1 = np.bincount(i1, weights=v1, minlength=nb); c1 = np.bincount(i1, minlength=nb).astype(float)
    s2 = np.bincount(i2, weights=v2, minlength=nb); c2 = np.bincount(i2, minlength=nb).astype(float)
    rng = np.random.default_rng(SEED); bs = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb)
        bs[b] = s1[p].sum() / max(c1[p].sum(), 1) - s2[p].sum() / max(c2[p].sum(), 1)
    mu = float(np.mean(v1) - np.mean(v2))
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return dict(diff=mu, raw=[lo, hi], infl=[mu - (mu - lo) * INFL, mu + (hi - mu) * INFL])


def cell_stats(net, gross, fund, rsn, held_min, ems):
    net = np.asarray(net, np.float64); n = len(net)
    if n < 2:
        return dict(n=int(n))
    ci = ci_block(net, ems)
    dt = pd.to_datetime(ems, unit="ms", utc=True)
    yr = dt.year.to_numpy(); day = dt.floor("D").to_numpy()
    by_year = {str(y): dict(n=int((yr == y).sum()), mean=float(net[yr == y].mean())) for y in np.unique(yr)}
    ds = pd.Series(net).groupby(day)
    dmean = ds.mean(); dsum = ds.sum()
    top5 = set(dsum.sort_values(ascending=False).index[:5])
    keep = ~pd.Series(day).isin(top5).to_numpy()
    return dict(
        n=int(n), mean=float(net.mean()), median=float(np.median(net)), ci_raw=ci["raw"], ci_infl=ci["infl"],
        nblock=ci["nblock"], out_raw=bool(ci["raw"][0] > 0), out_infl=bool(ci["infl"][0] > 0),
        by_year=by_year, years_pos=int(sum(1 for v in by_year.values() if v["mean"] > 0)),
        n_days=int(len(dmean)), day_weighted=float(dmean.mean()),
        drop_top5_days=float(net[keep].mean()), drop_top5_days_dayw=float(dmean.drop(list(top5)).mean()),
        top5_days=[str(pd.Timestamp(d).date()) for d in sorted(top5)],
        sl_rate=float(np.mean(rsn == 1)), trail_rate=float(np.mean(rsn == 2)), time_rate=float(np.mean(rsn == 0)),
        delist_rate=float(np.mean(rsn == 3)), gross_mean=float(np.mean(gross)), fund_mean=float(np.mean(fund)),
        held_mean_h=float(np.mean(held_min) / 60.0), win_rate=float(np.mean(net > 0)),
        p01=float(np.percentile(net, 1)), p05=float(np.percentile(net, 5)), min=float(net.min()),
        p99=float(np.percentile(net, 99)), max=float(net.max()))


def load_trades():
    fs = sorted(glob.glob(os.path.join(CACHE, "tr_*.parquet")))
    tr = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    return tr, [os.path.basename(f)[3:9] for f in fs]


def report():
    setup_log()
    pk = pd.read_parquet(os.path.join(CACHE, "picks.parquet"))
    tr, months = load_trades()
    assert len(tr) == len(pk), (len(tr), len(pk))
    info = json.load(open(os.path.join(CACHE, "picks_info.json")))
    F = Fund()
    res = {"prereg": "docs/prereg/PREREG_SHORT_GATECLOSED.md", "bins": BINS, "k_mult": K_MULT, "infl": INFL,
           "fee": FEE, "exits": {k: list(v) for k, v in EXITS.items()}, "months": months, "picks_info": info,
           "n_rows": int(len(tr)), "n_not_ok": {s: int((~g["ok"]).sum()) for s, g in tr.groupby("set")}, "cells": {}}
    tr = tr[tr["ok"]].reset_index(drop=True)
    res["cov_lt90"] = {s: float((g["cov"] < 0.9).mean()) for s, g in tr.groupby("set")}
    nets = {}
    for setn, g in tr.groupby("set"):
        ems = (g["e"].to_numpy(np.int64) + 1) * MIN
        for side, pre in sides_of(setn):
            for nm in EXITS:
                c = pre + nm
                x = g[c + "_x"].to_numpy(np.int64)
                fs, has = F.window(g["symbol"].to_numpy(), ems, (x + 1) * MIN)
                fund = -side * fs                          # short nhan +rate, long tra
                gross = g[c + "_p"].to_numpy(np.float64)
                net = gross - FEE + fund
                key = "%s.%s" % (setn, c)
                st = cell_stats(net, gross, fund, g[c + "_r"].to_numpy(), x - g["e"].to_numpy(np.int64), ems)
                st["fund_cov"] = float(has.mean())
                res["cells"][key] = st; nets[key] = (net, ems)
                log.info("%s n=%d mean=%.5f ci=%s", key, st["n"], st["mean"], st["ci_raw"])
    res["diff_SG_minus_RG"] = {}; res["diff_SG_minus_SO"] = {}; res["verdict"] = {}
    any_go = False
    for nm in EXITS:
        sg = res["cells"]["SG.S_" + nm]; rg = res["cells"]["RG.S_" + nm]
        dr = ci_diff(*nets["SG.S_" + nm], *nets["RG.S_" + nm]); res["diff_SG_minus_RG"][nm] = dr
        res["diff_SG_minus_SO"][nm] = ci_diff(*nets["SG.S_" + nm], *nets["SO.S_" + nm])
        has_sl = np.isfinite(EXITS[nm][2])
        cond = {
            "C1_net_gt0_out_ci_raw_infl": bool(sg["mean"] > 0 and sg["out_raw"] and sg["out_infl"]),
            "C2_years_pos_ge3": bool(sg["years_pos"] >= 3),
            "C3_dayw_gt0_and_drop_top5_gt0": bool(sg["day_weighted"] > 0 and sg["drop_top5_days"] > 0),
            "C4_n_ge_1500": bool(sg["n"] >= 1500),
            "C5_sl_rate_le_25pct": bool((not has_sl) or sg["sl_rate"] <= 0.25),
            "C6_alpha_not_beta": bool(rg["mean"] <= 0 or dr["raw"][0] > 0),
        }
        go = all(cond.values()); any_go |= go
        res["verdict"][nm] = dict(cond=cond, go=go)
    res["GO"] = bool(any_go)
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
    log.info("VERDICT GO=%s %s", any_go, json.dumps(res["verdict"]))


# ───────────────────────── sanity ─────────────────────────
def _read_indep(cli, dec, sym, m_from, m_to):
    """Doc doc lap tung phut (client.get) -> (O,H,L,C) float64, NaN neu thieu."""
    from short_pathexit_sim import parse_min
    out = np.full((4, m_to - m_from + 1), np.nan)
    for i, m in enumerate(range(m_from, m_to + 1)):
        try:
            _, _, b = cli.get(("test", "kline_1m_opt", key_of(m)))
        except Exception:
            continue
        v = parse_min(bytes(dec(b["data"]))).get(sym) if b and "data" in b else None
        if v is not None:
            out[:, i] = [x if x > 0 else np.nan for x in v[:4]]
    return out


def sanity():
    setup_log()
    import aerospike, cramjam
    pk = pd.read_parquet(os.path.join(CACHE, "picks.parquet"))
    assert (pk.loc[pk["set"].isin(["SG", "RG"]), "p15"] < GATE_THR).all()
    assert (pk.loc[pk["set"] == "SO", "p15"] >= GATE_THR).all()
    assert (pk["e"] * MIN >= pk["ts"] + 15 * MIN).all() and (pk["e"] + TSMAX < DEV_END).all()
    df, arr, b0, need = sim_month(SANITY_YM, pk[pk["ym"] == SANITY_YM].reset_index(drop=True), save=False)
    lin = load_lineage(); lmin = dict(zip(lin["symbol"], lin["l_min"]))
    col = {n: i for i, n in enumerate(need)}
    out = {"month": SANITY_YM, "day": SANITY_DAY}
    dd = df[df["ok"] & (pd.to_datetime((df["e"] + 1) * MIN, unit="ms", utc=True).dt.strftime("%Y-%m-%d") == SANITY_DAY)]
    nmis = 0; ncmp = 0; maxd = 0.0
    for r in dd.itertuples(index=False):
        c = col[r.symbol]; L = int(r.L)
        Hw, Lw, Ow, Cw = window(arr, c, r.e, b0, L); Cw = ffill_from(Cw, r.P)
        lp = trade_cells(list(Hw), list(Lw), list(Ow), list(Cw), r.P, sides_of(r.set), fn=exit_loop)
        for nm, (pnl, k, rs) in lp.items():
            ncmp += 1; dv = abs(pnl - getattr(r, nm + "_p")); maxd = max(maxd, dv)
            if dv > 1e-9 or r.e + 1 + k != getattr(r, nm + "_x") or rs != getattr(r, nm + "_r"):
                nmis += 1
    out["day_vec_vs_loop"] = dict(n_trades=int(len(dd)), n_cmp=ncmp, n_mismatch=nmis, max_abs_diff=maxd)
    log.info("day vec vs loop %s", out["day_vec_vs_loop"])
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect(); dec = cramjam.snappy.decompress_raw
    rng = np.random.default_rng(RSEED)
    ok = df[df["ok"]].reset_index(drop=True)
    samp = ok.iloc[np.sort(rng.choice(len(ok), 10, replace=False))]
    rows = []
    for r in samp.itertuples(index=False):
        L = int(r.L)
        ind = _read_indep(cli, dec, r.symbol, r.e, r.e + L)
        P2 = ind[3, 0]
        O, Hh, Lo, C = ind[:, 1:]
        lp = trade_cells(list(Hh), list(Lo), list(O), list(ffill_from(C, P2)), P2, sides_of(r.set), fn=exit_loop)
        d = dict(set=r.set, symbol=r.symbol, tick_utc=str(pd.to_datetime(r.ts, unit="ms", utc=True)), p15=r.p15,
                 rank=int(r.rank), entry_utc_close=str(pd.to_datetime((r.e + 1) * MIN, unit="ms", utc=True)),
                 P=r.P, P_indep=float(P2), L=L, match=True)
        for nm, (pnl, k, rs) in lp.items():
            ex = getattr(r, nm + "_x")
            d[nm] = dict(pnl=round(float(getattr(r, nm + "_p")), 6), pnl_indep=round(float(pnl), 6), reason=int(rs),
                         exit_utc_close=str(pd.to_datetime((ex + 1) * MIN, unit="ms", utc=True)),
                         held_h=round((ex - r.e) / 60, 2))
            if abs(pnl - getattr(r, nm + "_p")) > 1e-9 or r.e + 1 + k != ex or rs != getattr(r, nm + "_r"):
                d["match"] = False
        rows.append(d)
    cli.close()
    out["samples10"] = rows
    out["samples10_all_match"] = bool(all(d["match"] and d["P"] == d["P_indep"] for d in rows))
    json.dump(out, open(os.path.join(CACHE, "sanity.json"), "w"), indent=1, default=float)
    log.info("sanity all_match=%s day=%s", out["samples10_all_match"], out["day_vec_vs_loop"])


def main():
    setup_log()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["picks", "sim", "sanity", "report"])
    ap.add_argument("--months", default="all")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.stage == "picks":
        stage_picks()
    elif a.stage == "sanity":
        sanity()
    elif a.stage == "report":
        report()
    else:
        pk = pd.read_parquet(os.path.join(CACHE, "picks.parquet"), columns=["ym"])
        yms = sorted(pk["ym"].unique()) if a.months == "all" else a.months.split(",")
        with Pool(a.workers, maxtasksperchild=1) as pool:
            for r in pool.imap_unordered(sim_month, yms):
                log.info("done %s", r)


if __name__ == "__main__":
    main()
