#!/usr/bin/env python3
"""short_v3_r1c_exec.py — PREREG_SHORT_V3_R1C (41760f10): lop EXECUTION cua fade R1.

Tap trigger = R1 (r1_cache/trades_r1.csv, n=10991) cat t+15+2880 <= 2025-12-31 23:59 UTC. Exit nhanh B (5/3/10) 1m first-hit.
Entry TAKER (close t+1, phi 0,056+0,056) vs LIMIT (close_t x1,007, 15', fill H>=Lp tai Lp, phi 0,02+0,056) x TS 24h/48h; LONG mirror.
Stage scan  : stream Aerospike test.kline_1m_opt theo THANG cua t -> r1c_cache/r1c_YYYYMM.parquet (+ sanity S3 nhieu, S4 vec vs loop).
Stage report: funding settle thuc, CI block 72h (infl 1,67), GO-R1c, sanity S1/S2 -> docs/result/RESULT_SHORT_V3_R1C.json
Chay: python3 short_v3_r1c_exec.py scan --months 202403 --procs 1 ; scan --months all --procs 3 ; report
"""
import argparse, glob, json, logging, os, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
C1 = "/home/ubuntu/claude_master/1002/r1_cache"
CACHE = "/home/ubuntu/claude_master/1002/r1c_cache"
OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R1C.json")
FUND = "/tmp/fund_cache.npz"
MIN = 60000
H72 = 72 * 3600000
DEV_M0 = 1640995200000 // MIN          # 2022-01-01 00:00 UTC
DEV_M1 = 1767225600000 // MIN - 1      # 2025-12-31 23:59 UTC = phut cuoi duoc doc
FWIN = 15
TSS = (1440, 2880)
T_MAX = DEV_M1 - FWIN - TSS[-1]        # trigger cuoi: t+15+2880 <= DEV_M1
A_, G_, S_ = 0.05, 0.03, 0.10
DELTA = 0.007
FEE_TK, FEE_MK, FEE_OUT = 0.00056, 0.0002, 0.00056
STRESS = 0.001
NREP, SEED, INFL = 2000, 20260905, 1.67
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT"}
# ten o -> (side, entry, TS)
CFGS = {"%s_%s%d" % (sd, e, ts // 60): (-1 if sd == "S" else 1, e, ts) for e in ("TK", "LM") for sd in ("S", "L") for ts in TSS}
MAIN = ["S_TK24", "S_TK48", "S_LM24", "S_LM48"]
log = logging.getLogger("r1c")


def setup_log():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(process)d %(levelname)s %(message)s")


def key_of(m):
    """phut UTC m (gio mo) -> key Aerospike TZ+7 (nhu R1)."""
    return time.strftime("%Y%m%d-%H%M", time.gmtime(m * 60 + 7 * 3600))


def ym_of(t):
    d = pd.to_datetime(np.asarray(t, np.int64) * MIN, unit="ms")
    return (d.year * 100 + d.month).to_numpy()


def load_trig():
    """Tap trigger R1 + c_t (tu cand R1), cat t <= T_MAX."""
    tr = pd.read_csv(os.path.join(C1, "trades_r1.csv"))
    n_r1 = len(tr)
    cd = pd.concat([pd.read_parquet(f, columns=["sym", "t", "c_t"]) for f in sorted(glob.glob(os.path.join(C1, "cand_*.parquet")))],
                   ignore_index=True)
    tr = tr.merge(cd, on=["sym", "t"], how="left", validate="1:1")
    assert tr["c_t"].notna().all() and len(tr) == n_r1
    drop = tr[tr["t"] > T_MAX]
    tr = tr[tr["t"] <= T_MAX].sort_values("t", kind="stable").reset_index(drop=True)
    tr["ym"] = ym_of(tr["t"])
    info = dict(n_r1=n_r1, n_kept=int(len(tr)), n_dropped=int(len(drop)),
                t_max_utc=str(pd.Timestamp(T_MAX * MIN, unit="ms")),
                dropped=[dict(sym=r.sym, t_utc=str(pd.Timestamp(int(r.t) * MIN, unit="ms"))) for r in drop.itertuples()])
    return tr, info


# ───────────────────────── stream (chi giu symbol can) ─────────────────────────
def stream_sel(b0, b1, syms, tag):
    """Doc phut b0..b1 (UTC) -> arr (4, N, S) float32 [O,H,L,C] cho syms. Gia <= 0 -> NaN (nhu R1)."""
    import aerospike, cramjam
    from short_pathexit_sim import parse_min
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    idx = {s: i for i, s in enumerate(syms)}
    N = b1 - b0 + 1
    arr = np.full((4, N, len(syms)), np.nan, np.float32)
    t0 = time.time(); nrec = 0; nday = (N + 1439) // 1440
    for d0 in range(b0, b1 + 1, 1440):
        ms = list(range(d0, min(d0 + 1440, b1 + 1)))
        keys = [("test", "kline_1m_opt", key_of(m)) for m in ms]
        brs = None
        for _att in range(3):
            try:
                brs = cli.batch_read(keys).batch_records
                break
            except Exception as e:
                log.warning("%s batch_read loi %s, thu lai", tag, e); time.sleep(5)
        if brs is None:
            raise RuntimeError("batch_read that bai")
        for k, rr in enumerate(brs):
            if rr.result != 0 or rr.record is None:
                continue
            bins = rr.record[2]
            if not bins or "data" not in bins:
                continue
            d = parse_min(bytes(dec(bins["data"])))
            rows = []; vals = []
            for nm, i in idx.items():
                v = d.get(nm)
                if v is not None:
                    rows.append(i); vals.append(list(v)[:4])
            if rows:
                arr[:, ms[k] - b0, rows] = np.asarray(vals, np.float32).T
                nrec += 1
        di = (d0 - b0) // 1440 + 1
        if di % 10 == 0 or di == nday:
            log.info("%s ngay %d/%d nrec=%d %.0fs", tag, di, nday, nrec, time.time() - t0)
    cli.close()
    for f in range(4):
        x = arr[f]
        x[~(x > 0)] = np.nan
    return arr, nrec


# ───────────────────────── exit nhanh B ─────────────────────────
def exit_vec(Hw, Lw, Ow, Cw, P, side):
    """Cua so index 0 = phut entry e (da trung hoa theo quy uoc), index k = phut e+k (k <= TSmax).
    Muc stop phut k tinh tu du lieu den k-1; fill gap = max/min(level, open). -> {TS: (pnl, k_rel, reason 0TIME/1SL/2TRAIL)}"""
    a, g, s = A_, G_, S_
    with np.errstate(all="ignore"):
        if side < 0:
            lw = np.where(np.isfinite(Lw), Lw, np.inf)
            run = np.minimum.accumulate(np.concatenate(([P], lw)))[:-1]
            armed = run <= P * (1 - a)
            level = np.where(armed, run * (1 + g), P * (1 + s))
            hit = np.greater_equal(Hw, level)
        else:
            hw = np.where(np.isfinite(Hw), Hw, -np.inf)
            run = np.maximum.accumulate(np.concatenate(([P], hw)))[:-1]
            armed = run >= P * (1 + a)
            level = np.where(armed, run * (1 - g), P * (1 - s))
            hit = np.less_equal(Lw, level)
    k = int(np.argmax(hit)) if hit.any() else len(Hw)
    res = {}
    for TS in TSS:
        if k <= TS:
            o = Ow[k]; lv = float(level[k])
            if np.isfinite(o):
                px = max(lv, o) if side < 0 else min(lv, o)
            else:
                px = lv
            rs = 2 if armed[k] else 1; ke = k
        else:
            px = float(Cw[TS]); rs = 0; ke = TS
        res[TS] = ((1 - px / P) if side < 0 else (px / P - 1), ke, rs)
    return res


def exit_loop(Hw, Lw, Ow, Cw, P, side):
    """Tham chieu loop thuan (list python), cung quy uoc."""
    a, g, s = A_, G_, S_
    run = P; hitk = None
    for j in range(len(Hw)):
        h, l, o = Hw[j], Lw[j], Ow[j]
        if side < 0:
            armed = run <= P * (1 - a)
            lv = run * (1 + g) if armed else P * (1 + s)
            if h == h and h >= lv:
                hitk = (j, (max(lv, o) if o == o else lv), armed); break
            if l == l and l < run:
                run = l
        else:
            armed = run >= P * (1 + a)
            lv = run * (1 - g) if armed else P * (1 - s)
            if l == l and l <= lv:
                hitk = (j, (min(lv, o) if o == o else lv), armed); break
            if h == h and h > run:
                run = h
    res = {}
    for TS in TSS:
        if hitk is not None and hitk[0] <= TS:
            px, ke, rs = hitk[1], hitk[0], (2 if hitk[2] else 1)
        else:
            px, ke, rs = Cw[TS], TS, 0
        res[TS] = ((1 - px / P) if side < 0 else (px / P - 1), ke, rs)
    return res


def window(o, h, l, cf, e, mode):
    """Cot 1-D cua 1 coin; cua so phut e..e+TSmax. mode tk: index0 trung hoa het (duong gia tu e+1 nhu R1);
    lmS: index0 chi giu H (kiem SL phut fill); lmL: index0 chi giu L. O index0 luon NaN (open truoc fill)."""
    sl = slice(e, e + TSS[-1] + 1)
    Hw = h[sl].astype(np.float64); Lw = l[sl].astype(np.float64); Ow = o[sl].astype(np.float64); Cw = cf[sl].astype(np.float64)
    assert len(Hw) == TSS[-1] + 1, "cua so thieu"
    Ow[0] = np.nan
    if mode == "tk":
        Hw[0] = np.nan; Lw[0] = np.nan
    elif mode == "lmS":
        Lw[0] = np.nan
    elif mode == "lmL":
        Hw[0] = np.nan
    else:
        raise ValueError(mode)
    return Hw, Lw, Ow, Cw


def entries(o, h, l, c, t, ct_ref, P_ref, check=True):
    """Chi doc c[t] (Lp), c[t+1] (P taker), h/l[t+1..t+15] (fill LIMIT)."""
    ct = float(c[t])
    P = float(c[t + 1])
    if check:
        assert np.isfinite(ct) and abs(ct - ct_ref) <= 1e-6 * ct_ref, "c_t lech cache R1"
        assert np.isfinite(P) and abs(P - P_ref) <= 1e-9 * P_ref, "P lech R1"
    lpS = ct * (1 + DELTA); lpL = ct * (1 - DELTA)
    hs = h[t + 1:t + 1 + FWIN].astype(np.float64); ls = l[t + 1:t + 1 + FWIN].astype(np.float64)
    assert len(hs) == FWIN and len(ls) == FWIN
    with np.errstate(invalid="ignore"):
        okS = np.isfinite(hs) & (hs >= lpS); okL = np.isfinite(ls) & (ls <= lpL)
    fS = t + 1 + int(np.argmax(okS)) if okS.any() else -1
    fL = t + 1 + int(np.argmax(okL)) if okL.any() else -1
    assert fS < 0 or t + 1 <= fS <= t + FWIN
    assert fL < 0 or t + 1 <= fL <= t + FWIN
    return dict(ct=ct, P=P, lpS=lpS, lpL=lpL, fS=fS, fL=fL, hs=hs, ls=ls)


def legs(en, t):
    """(prefix, side, mode, e, P_entry) — bo chan LIMIT khong fill."""
    out = [("S_TK", -1, "tk", t + 1, en["P"]), ("L_TK", 1, "tk", t + 1, en["P"])]
    if en["fS"] >= 0:
        out.append(("S_LM", -1, "lmS", en["fS"], en["lpS"]))
    if en["fL"] >= 0:
        out.append(("L_LM", 1, "lmL", en["fL"], en["lpL"]))
    return out


def sim_trigger(o, h, l, c, cf, t, ct_ref, P_ref):
    """Chi so phut tuong doi buffer. -> rec (k/e/f tuong doi), en."""
    en = entries(o, h, l, c, t, ct_ref, P_ref)
    fS, fL = en["fS"], en["fL"]
    rec = dict(c_t2=en["ct"], P2=en["P"], Lp_S=en["lpS"], Lp_L=en["lpL"], f_S=fS, f_L=fL,
               o_fS=(float(o[fS]) if fS >= 0 else np.nan), o_fL=(float(o[fL]) if fL >= 0 else np.nan),
               hseq=",".join("%.8g" % x for x in en["hs"]), lseq=",".join("%.8g" % x for x in en["ls"]))
    for pre, side, mode, e, Pe in legs(en, t):
        r = exit_vec(*window(o, h, l, cf, e, mode), Pe, side)
        for TS, (pnl, ke, rs) in r.items():
            nm = "%s%d" % (pre, TS // 60)
            rec[nm + "_p"] = pnl; rec[nm + "_k"] = e + ke; rec[nm + "_r"] = rs; rec[nm + "_e"] = e
    for nm in CFGS:
        if nm + "_p" not in rec:
            rec[nm + "_p"] = np.nan; rec[nm + "_k"] = -1; rec[nm + "_r"] = -1; rec[nm + "_e"] = -1
    return rec, en


def garble(x, cut, ref, rng):
    y = x.copy()
    if cut < len(y):
        y[cut:] = (rng.uniform(0.5, 2.0, len(y) - cut) * ref).astype(np.float32)
    return y


def sanity_trigger(o, h, l, c, cf, t, en, rng, st):
    """S4 vec vs loop (8 cau hinh); S3 nhieu: du lieu > t -> Lp khong doi; > t+15 -> entry/fill khong doi; > e+TS -> exit TS khong doi."""
    c2 = garble(c, t + 1, en["ct"], rng)
    e1 = entries(garble(o, t + 1, en["ct"], rng), garble(h, t + 1, en["ct"], rng), garble(l, t + 1, en["ct"], rng), c2, t, 0, 0, check=False)
    st["lp_noise"] += 1
    st["lp_noise_bad"] += int(not (e1["lpS"] == en["lpS"] and e1["lpL"] == en["lpL"]))
    cut = t + FWIN + 1
    e2 = entries(garble(o, cut, en["ct"], rng), garble(h, cut, en["ct"], rng), garble(l, cut, en["ct"], rng),
                 garble(c, cut, en["ct"], rng), t, 0, 0, check=False)
    st["fill_noise"] += 1
    st["fill_noise_bad"] += int(not (e2["fS"] == en["fS"] and e2["fL"] == en["fL"] and e2["P"] == en["P"]))
    for pre, side, mode, e, Pe in legs(en, t):
        W = window(o, h, l, cf, e, mode)
        rv = exit_vec(*W, Pe, side)
        rl = exit_loop(*[list(x) for x in W], Pe, side)
        for TS in TSS:
            st["cmp"] += 1
            ok = abs(rv[TS][0] - rl[TS][0]) < 1e-9 and rv[TS][1] == rl[TS][1] and rv[TS][2] == rl[TS][2]
            st["cmp_bad"] += int(not ok)
            cut = e + TS + 1
            W2 = window(garble(o, cut, Pe, rng), garble(h, cut, Pe, rng), garble(l, cut, Pe, rng), garble(cf, cut, Pe, rng), e, mode)
            r2 = exit_vec(*W2, Pe, side)
            st["exit_noise"] += 1
            st["exit_noise_bad"] += int(r2[TS] != rv[TS])


def scan_month(args):
    ym, recs = args
    setup_log()
    t0 = time.time()
    tl = [r[1] for r in recs]
    t_lo, t_hi = min(tl), max(tl)
    assert t_lo >= DEV_M0 and t_hi <= T_MAX
    b0 = t_lo - 2
    b1 = min(t_hi + FWIN + TSS[-1] + 1, DEV_M1)
    assert t_hi + FWIN + TSS[-1] <= b1 <= DEV_M1
    syms = sorted({r[0] for r in recs})
    arr, nrec = stream_sel(b0, b1, syms, str(ym))
    O, H, L, C = arr
    Cf = pd.DataFrame(C).ffill().to_numpy(np.float32)
    idx = {s: i for i, s in enumerate(syms)}
    rng = np.random.default_rng(SEED + ym)
    st = dict(lp_noise=0, lp_noise_bad=0, fill_noise=0, fill_noise_bad=0, cmp=0, cmp_bad=0, exit_noise=0, exit_noise_bad=0)
    rows = []
    for sym, t, ct_ref, P_ref in recs:
        s = idx[sym]; tt = t - b0
        o, h, l, c, cf = [np.ascontiguousarray(X[:, s]) for X in (O, H, L, C, Cf)]
        rec, en = sim_trigger(o, h, l, c, cf, tt, ct_ref, P_ref)
        for k_ in list(rec):
            if (k_.endswith("_k") or k_.endswith("_e") or k_ in ("f_S", "f_L")) and rec[k_] >= 0:
                rec[k_] = int(rec[k_]) + b0
        rec["sym"] = sym; rec["t"] = t
        sanity_trigger(o, h, l, c, cf, tt, en, rng, st)
        rows.append(rec)
    df = pd.DataFrame(rows)
    df["ym"] = ym
    os.makedirs(CACHE, exist_ok=True)
    df.to_parquet(os.path.join(CACHE, "r1c_%d.parquet" % ym), index=False)
    meta = dict(ym=ym, n=len(recs), nsym=len(syms), nrec=nrec, nmin=int(b1 - b0 + 1), b0=b0, b1=b1,
                secs=round(time.time() - t0, 1), sanity=st)
    json.dump(meta, open(os.path.join(CACHE, "meta_%d.json" % ym), "w"), indent=1, default=str)
    log.info("%s XONG n=%d fillS=%d fillL=%d sanity=%s %.0fs", ym, len(recs), int((df["f_S"] >= 0).sum()),
             int((df["f_L"] >= 0).sum()), st, time.time() - t0)
    return meta


# ───────────────────────── report ─────────────────────────
def load_fund():
    z = np.load(FUND, allow_pickle=True)
    fsy = [str(x) for x in z["syms"]]
    fts = z["ts"].astype(np.int64); frt = z["rt"].astype(np.float64); fsid = z["sid"].astype(np.int64)
    m = fts > 0
    fts, frt, fsid = fts[m], frt[m], fsid[m]
    o = np.lexsort((fts, fsid)); fts, frt, fsid = fts[o], frt[o], fsid[o]
    bnd = np.searchsorted(fsid, np.arange(len(fsy) + 1))
    fd = {}
    for j, n in enumerate(fsy):
        if bnd[j + 1] > bnd[j]:
            fd[n] = (fts[bnd[j]:bnd[j + 1]], np.concatenate(([0.0], np.cumsum(frt[bnd[j]:bnd[j + 1]]))))
    info = dict(n_events=int(len(fts)), frac_ts_not_minute=float((fts % MIN != 0).mean()),
                frac_ts_not_second=float((fts % 1000 != 0).mean()), max_ts_utc=str(pd.Timestamp(int(fts.max()), unit="ms")))
    return fd, info


def fund_sum(fd, syms, ein, eout):
    """Sum rate su kien fundingTime in (ein, eout]."""
    res = np.zeros(len(syms)); has = np.zeros(len(syms), bool)
    syms = np.asarray(syms)
    for sym in np.unique(syms):
        gi = np.nonzero(syms == sym)[0]
        if sym not in fd:
            continue
        ts, cum = fd[sym]
        has[gi] = True
        res[gi] = cum[np.searchsorted(ts, eout[gi], "right")] - cum[np.searchsorted(ts, ein[gi], "right")]
    return res, has


def ci_block(v, ems):
    v = np.asarray(v, np.float64)
    blk = np.asarray(ems, np.int64) // H72
    _, inv = np.unique(blk, return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(np.float64)
    rng = np.random.default_rng(SEED)
    nb = len(sums)
    bs = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb)
        bs[b] = sums[p].sum() / cnts[p].sum()
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    mu = float(v.mean())
    return dict(raw=[lo, hi], infl=[mu - (mu - lo) * INFL, mu + (hi - mu) * INFL], nblock=int(nb))


def yr_of(ems):
    return pd.to_datetime(np.asarray(ems, np.int64), unit="ms", utc=True).year.to_numpy()


def cell_data(df, name, fd, sub=None):
    """Lenh cua o `name` (chi lenh co entry; sub = mask bo sung). -> dict mang theo lenh."""
    side, E, TS = CFGS[name]
    m = df[name + "_e"].to_numpy() >= 0
    if sub is not None:
        m = m & sub
    d = df[m]
    e = d[name + "_e"].to_numpy(np.int64); k = d[name + "_k"].to_numpy(np.int64)
    assert (k >= e).all() and (k <= e + TS).all() and (k <= DEV_M1).all()
    ein = (e + 1) * MIN - 1 if E == "TK" else e * MIN
    eout = (k + 1) * MIN - 1
    F, has = fund_sum(fd, d["sym"].to_numpy(), ein, eout)
    fund = -side * F                       # short: +sum rate ; long: -sum rate
    gross = d[name + "_p"].to_numpy(np.float64)
    fee = (FEE_TK if E == "TK" else FEE_MK) + FEE_OUT
    net = gross - fee + fund
    return dict(idx=np.nonzero(m)[0], net=net, gross=gross, fund=fund, rsn=d[name + "_r"].to_numpy(), held=k - e,
                ems=ein, has=has, slfill=(d[name + "_r"].to_numpy() == 1) & (k == e))


def cell_stats(cd):
    net = cd["net"]; ems = cd["ems"]
    ci = ci_block(net, ems)
    yr = yr_of(ems)
    by = {str(y): (float(net[yr == y].mean()) if (yr == y).any() else None) for y in (2022, 2023, 2024, 2025)}
    byn = {str(y): int((yr == y).sum()) for y in (2022, 2023, 2024, 2025)}
    bysl = {str(y): (float((cd["rsn"][yr == y] == 1).mean()) if (yr == y).any() else None) for y in (2022, 2023, 2024, 2025)}
    st = net - STRESS
    return dict(n=int(len(net)), mean=float(net.mean()), median=float(np.median(net)), win=float((net > 0).mean()),
                sl_rate=float((cd["rsn"] == 1).mean()), trail_rate=float((cd["rsn"] == 2).mean()),
                time_rate=float((cd["rsn"] == 0).mean()), sl_fillmin_rate=float(cd["slfill"].mean()),
                gross_mean=float(cd["gross"].mean()), fund_mean=float(cd["fund"].mean()), held_mean_h=float(cd["held"].mean() / 60),
                ci_raw=ci["raw"], ci_infl=ci["infl"], nblock=ci["nblock"], by_year=by, n_by_year=byn, sl_by_year=bysl,
                years_pos=int(sum(1 for x in by.values() if x is not None and x > 0)),
                stress_mean=float(st.mean()), stress_years_pos=int(sum(1 for y in (2022, 2023, 2024, 2025)
                                                                       if (yr == y).any() and st[yr == y].mean() > 0)),
                net_min=float(net.min()), net_p1=float(np.percentile(net, 1)), net_p5=float(np.percentile(net, 5)),
                net_p99=float(np.percentile(net, 99)), frac_has_funding=float(cd["has"].mean()))


def pct(x, nd=3):
    return "n/a" if x is None else ("%+.*f" % (nd, 100 * x))


def report(tr, info):
    fs = sorted(glob.glob(os.path.join(CACHE, "r1c_*.parquet")))
    yms = sorted(int(os.path.basename(f)[4:10]) for f in fs)
    assert yms == sorted(set(tr["ym"].tolist())), "thieu thang: %s" % sorted(set(tr["ym"]) - set(yms))
    sc = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    metas = [json.load(open(os.path.join(CACHE, "meta_%d.json" % y))) for y in yms]
    r1cols = ["sym", "t", "tier", "regime", "S_B24_net", "S_B24_r", "S_B24_k", "L_B24_net", "L_B24_r", "L_B24_k", "S_B12_net"]
    df = tr[r1cols].merge(sc, on=["sym", "t"], how="left", validate="1:1", indicator=True)
    assert (df["_merge"] == "both").all() and len(df) == len(tr)
    df = df.drop(columns="_merge").sort_values("t", kind="stable").reset_index(drop=True)
    fd, finfo = load_fund()
    cds = {nm: cell_data(df, nm, fd) for nm in CFGS}
    subS = df["f_S"].to_numpy() >= 0
    for TS in TSS:
        cds["S_TKsub%d" % (TS // 60)] = cell_data(df, "S_TK%d" % (TS // 60), fd, sub=subS)
    cells = {nm: cell_stats(cd) for nm, cd in cds.items()}
    for nm, x in cells.items():
        log.info("%-10s n=%5d mean=%+.4f%% ci=[%+.3f;%+.3f] infl=[%+.3f;%+.3f] yrs=%d sl=%.3f stress=%+.4f%%", nm, x["n"], 100 * x["mean"],
                 100 * x["ci_raw"][0], 100 * x["ci_raw"][1], 100 * x["ci_infl"][0], 100 * x["ci_infl"][1], x["years_pos"], x["sl_rate"],
                 100 * x["stress_mean"])
    go = {}
    for c in MAIN:
        x = cells[c]; xl = cells[c.replace("S_", "L_")]
        g = dict(G1=bool(x["mean"] > 0 and x["ci_raw"][0] > 0 and x["ci_infl"][0] > 0), G2=bool(x["years_pos"] >= 3),
                 G3=bool(x["n"] >= 1500), G4=bool(x["sl_rate"] <= 0.25), G5=bool(x["stress_mean"] > 0), G6=bool(xl["mean"] <= 0))
        g["ALL"] = bool(all(g.values()))
        go[c] = g
    passing = [c for c in MAIN if go[c]["ALL"]]
    verdict = "GO" if passing else "NO-GO"
    best = max(passing, key=lambda c: cells[c]["mean"]) if passing else max(MAIN, key=lambda c: cells[c]["mean"])
    # S1 tai lap R1
    s1 = {}
    for sd, r1 in (("S", "S_B24"), ("L", "L_B24")):
        cd = cds["%s_TK24" % sd]
        assert len(cd["net"]) == len(df)
        dn = cd["net"] - df[r1 + "_net"].to_numpy()
        s1[sd] = dict(mean_new=float(cd["net"].mean()), mean_r1_same_set=float(df[r1 + "_net"].mean()), mean_diff=float(dn.mean()),
                      max_abs_diff=float(np.abs(dn).max()), k_match=float((df["%s_TK24_k" % sd] == df[r1 + "_k"]).mean()),
                      r_match=float((df["%s_TK24_r" % sd] == df[r1 + "_r"]).mean()))
        s1[sd]["PASS"] = bool(abs(s1[sd]["mean_diff"]) <= 5e-5 and s1[sd]["max_abs_diff"] < 1e-6 and s1[sd]["k_match"] == 1 and s1[sd]["r_match"] == 1)
    r1all = pd.read_csv(os.path.join(C1, "trades_r1.csv"), usecols=["S_B24_net", "L_B24_net"])
    s1["r1_full_mean_S_B24"] = float(r1all["S_B24_net"].mean()); s1["r1_full_mean_L_B24"] = float(r1all["L_B24_net"].mean())
    log.info("S1 %s", s1)
    # sanity scan (S3/S4) gop
    sm = {}
    for m in metas:
        for k_, v in m["sanity"].items():
            sm[k_] = sm.get(k_, 0) + v
    sm["PASS"] = bool(sm["lp_noise"] >= 200 and sm["lp_noise_bad"] == 0 and sm["fill_noise_bad"] == 0 and sm["cmp_bad"] == 0
                      and sm["exit_noise_bad"] == 0)
    # S2 mau 10 lenh SHORT-LIMIT
    rng = np.random.default_rng(SEED)
    fi = np.nonzero(subS)[0]
    samples = []
    for i in np.sort(rng.choice(fi, 10, replace=False)):
        r = df.iloc[i]
        samples.append(dict(sym=r["sym"], t_utc=str(pd.Timestamp(int(r["t"]) * MIN, unit="ms")), c_t=float(r["c_t2"]), Lp=float(r["Lp_S"]),
                            highs_t1_t15=r["hseq"], fill_min_after_t=int(r["f_S"] - r["t"]), o_fill=float(r["o_fS"]),
                            S_LM24_gross=float(r["S_LM24_p"]), S_LM24_reason=int(r["S_LM24_r"]),
                            S_LM24_held_min=int(r["S_LM24_k"] - r["f_S"]), S_TK24_gross=float(r["S_TK24_p"])))
    # fill stats
    fill = {}
    yr_t = yr_of(df["t"].to_numpy(np.int64) * MIN)
    for sd, col, ocol, lpc in (("S", "f_S", "o_fS", "Lp_S"), ("L", "f_L", "o_fL", "Lp_L")):
        f = df[col].to_numpy(); ok = f >= 0
        dt = (f - df["t"].to_numpy())[ok]
        of = df[ocol].to_numpy()[ok]; lp = df[lpc].to_numpy()[ok]
        thru = (of >= lp) if sd == "S" else (of <= lp)
        fill[sd] = dict(n_trig=int(len(df)), n_fill=int(ok.sum()), rate=float(ok.mean()),
                        rate_by_year={str(y): float(ok[yr_t == y].mean()) for y in (2022, 2023, 2024, 2025)},
                        fill_min_dist={str(k_): int((dt == k_).sum()) for k_ in range(1, FWIN + 1)},
                        frac_fill_at_tplus1=float((dt == 1).mean()), frac_open_through_limit=float(np.mean(thru)))
    fill["both_S_and_L"] = int(((df["f_S"] >= 0) & (df["f_L"] >= 0)).sum())
    # chon lenh vs gia vao
    dec = {}
    for TS in (24, 48):
        tk, sb, lm = cells["S_TK%d" % TS], cells["S_TKsub%d" % TS], cells["S_LM%d" % TS]
        dec[str(TS)] = dict(LM_minus_TK=lm["mean"] - tk["mean"], selection_TKsub_minus_TK=sb["mean"] - tk["mean"],
                            entry_LM_minus_TKsub=lm["mean"] - sb["mean"], of_which_gross=lm["gross_mean"] - sb["gross_mean"],
                            of_which_fee=(FEE_TK - FEE_MK), of_which_funding=lm["fund_mean"] - sb["fund_mean"],
                            sl_TK=tk["sl_rate"], sl_TKsub=sb["sl_rate"], sl_LM=lm["sl_rate"], sl_LM_fillmin=lm["sl_fillmin_rate"])
    # bang md (nhap, ngoai repo)
    L_ = ["| o | n | mean | median | CI raw | CI infl x1,67 | 2022 / 2023 / 2024 / 2025 | SL | SLfill | TRAIL | TIME | win | gross | fund | held h | min | p1 | stress |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = ["S_TK24", "S_TK48", "S_LM24", "S_LM48", "S_TKsub24", "S_TKsub48", "L_TK24", "L_TK48", "L_LM24", "L_LM48"]
    for nm in order:
        x = cells[nm]
        L_.append("| %s | %d | %s | %s | [%s; %s] | [%s; %s] | %s | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %s | %s | %.1f | %.1f%% | %.1f%% | %s |" % (
            nm, x["n"], pct(x["mean"]), pct(x["median"], 2), pct(x["ci_raw"][0]), pct(x["ci_raw"][1]), pct(x["ci_infl"][0]), pct(x["ci_infl"][1]),
            " / ".join(pct(x["by_year"][y], 2) for y in ("2022", "2023", "2024", "2025")), 100 * x["sl_rate"], 100 * x["sl_fillmin_rate"],
            100 * x["trail_rate"], 100 * x["time_rate"], 100 * x["win"], pct(x["gross_mean"]), pct(x["fund_mean"]), x["held_mean_h"],
            100 * x["net_min"], 100 * x["net_p1"], pct(x["stress_mean"])))
    L_.append("")
    L_.append("| o | G1 | G2 | G3 | G4 | G5 | G6 | ALL |")
    L_.append("|---|---|---|---|---|---|---|---|")
    for c in MAIN:
        L_.append("| %s | %s |" % (c, " | ".join("Y" if go[c][k_] else "N" for k_ in ("G1", "G2", "G3", "G4", "G5", "G6", "ALL"))))
    open(os.path.join(CACHE, "r1c_tables.md"), "w").write("\n".join(L_) + "\n")
    res = dict(prereg="PREREG_SHORT_V3_R1C (41760f10)", program="PROGRAM_SHORT_V3 ADDENDUM 2 985044ba", r1="3fea4f50",
               conv=dict(fee_taker_in=FEE_TK, fee_maker_in=FEE_MK, fee_out=FEE_OUT, stress=STRESS, delta=DELTA, fill_window_min=FWIN,
                         ts_min=TSS, branch_B=dict(a=A_, g=G_, s=S_), nrep=NREP, seed=SEED, infl=INFL, block_h=72,
                         dev_last_minute_utc=str(pd.Timestamp(DEV_M1 * MIN, unit="ms"))),
               trigger_set=info, verdict=verdict, passing=passing, best_cell=best, go_table=go, cells=cells, fill=fill,
               decomposition=dec, sanity=dict(S1=s1, S3_S4=sm, S2_samples=samples), funding_info=finfo,
               months=[{k_: v for k_, v in m.items() if k_ != "sanity"} for m in metas])
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
    for nm, cd in cds.items():
        col = np.full(len(df), np.nan); col[cd["idx"]] = cd["net"]
        df[nm + "_net"] = col
    keep = ["sym", "t", "c_t2", "P2", "Lp_S", "f_S", "Lp_L", "f_L"] + [nm + s for nm in CFGS for s in ("_net", "_r", "_k")] + \
        ["S_TKsub24_net", "S_TKsub48_net"]
    df[keep].to_csv(os.path.join(CACHE, "trades_r1c.csv"), index=False)
    log.info("VERDICT %s passing=%s best=%s -> %s", verdict, passing, best, OUT_JSON)


def main():
    setup_log()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["scan", "report"])
    ap.add_argument("--months", default="all")
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    tr, info = load_trig()
    log.info("tap trigger: R1 %d -> giu %d (loai %d, t > %s)", info["n_r1"], info["n_kept"], info["n_dropped"], info["t_max_utc"])
    if a.stage == "report":
        report(tr, info); return
    allm = sorted(set(tr["ym"].tolist()))
    months = allm if a.months == "all" else [int(x) for x in a.months.split(",")]
    todo = [m for m in months if a.force or not os.path.exists(os.path.join(CACHE, "r1c_%d.parquet" % m))]
    jobs = []
    for m in todo:
        g = tr[tr["ym"] == m]
        jobs.append((m, [(str(r.sym), int(r.t), float(r.c_t), float(r.P)) for r in g.itertuples()]))
    log.info("scan %d thang (bo qua %d), procs=%d", len(todo), len(months) - len(todo), a.procs)
    os.makedirs(CACHE, exist_ok=True)
    if a.procs <= 1:
        for j in jobs:
            scan_month(j)
    else:
        with Pool(a.procs, maxtasksperchild=1) as p:
            for meta in p.imap_unordered(scan_month, jobs):
                log.info("DONE %s n=%s secs=%s", meta["ym"], meta["n"], meta["secs"])


if __name__ == "__main__":
    main()
