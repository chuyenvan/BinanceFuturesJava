#!/usr/bin/env python3
"""short_v3_r1d_confirm.py — PREREG_SHORT_V3_R1D (c30a72b4): CONFIRMATION ENTRY cua fade R1.

Tap trigger = 10 977 cua R1c (load_trig R1c). Dieu kien tai t+W: khong phut j in [t+1,t+W] co high >= close_t x1,007 (W in {15,30}).
Entry short TAKER close t+W+1; exit nhanh B (5/3/10) 1m first-hit, TS 24h tu entry; phi 0,056+0,056; funding exact.
Doi chung: (a) LONG mirror (low > close_t x0,993) ; (b) tap bi loai short t+W+1 ; (c) tap dieu kien vao t+1 (C_15 = no-fill R1c).
Stage scan  : stream Aerospike test.kline_1m_opt theo THANG cua t -> r1d_cache/r1d_YYYYMM.parquet (+ sanity causal, vec vs loop).
Stage report: funding, CI block 72h (infl 1,18), GO-R1d 7 dieu kien, sanity (i)(ii)(iv) -> docs/result/RESULT_SHORT_V3_R1D.json
Chay: python3 short_v3_r1d_confirm.py scan --months 202403 --procs 1 ; scan --months all --procs 3 ; report
"""
import argparse, glob, json, logging, os, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import short_v3_r1c_exec as R1C  # noqa: E402  (tai dung load_trig, stream_sel, load_fund, fund_sum)

CACHE = "/home/ubuntu/claude_master/1002/r1d_cache"
R1C_TR = "/home/ubuntu/claude_master/1002/r1c_cache/trades_r1c.csv"
OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R1D.json")
MIN = 60000
H72 = 72 * 3600000
DEV_M1 = R1C.DEV_M1                    # 2025-12-31 23:59 UTC
WS = (15, 30)
TS = 1440
A_, G_, S_ = 0.05, 0.03, 0.10
DELTA = 0.007
FEE_IN, FEE_OUT = 0.00056, 0.00056
STRESS = 0.001
NREP, SEED, INFL = 2000, 20260905, 1.18
YRS = (2022, 2023, 2024, 2025)
LEGS = ("SH1", "SH15", "SH30", "LG15", "LG30")   # short t+1 ; short t+W+1 ; long t+W+1
log = logging.getLogger("r1d")


def setup_log():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(process)d %(levelname)s %(message)s")


# ───────────────────────── exit nhanh B (chep logic exit_vec R1c, TS duy nhat 1440) ─────────────────────────
def exit_vec(Hw, Lw, Ow, Cw, P, side):
    """index 0 = phut entry e (trung hoa), index k = phut e+k (k <= TS). Muc stop phut k tu du lieu den k-1 (SL uu tien cung nen).
    -> (pnl, k_rel, reason 0TIME/1SL/2TRAIL)"""
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
    if hit.any():
        k = int(np.argmax(hit))
        o = Ow[k]; lv = float(level[k])
        px = (max(lv, o) if side < 0 else min(lv, o)) if np.isfinite(o) else lv
        rs = 2 if armed[k] else 1
    else:
        k = TS; px = float(Cw[TS]); rs = 0
    return ((1 - px / P) if side < 0 else (px / P - 1)), k, rs


def exit_loop(Hw, Lw, Ow, Cw, P, side):
    """Tham chieu loop thuan (list python), cung quy uoc."""
    a, g, s = A_, G_, S_
    run = P
    for j in range(len(Hw)):
        h, l, o = Hw[j], Lw[j], Ow[j]
        if side < 0:
            armed = run <= P * (1 - a)
            lv = run * (1 + g) if armed else P * (1 + s)
            if h == h and h >= lv:
                px = max(lv, o) if o == o else lv
                return (1 - px / P), j, (2 if armed else 1)
            if l == l and l < run:
                run = l
        else:
            armed = run >= P * (1 + a)
            lv = run * (1 - g) if armed else P * (1 - s)
            if l == l and l <= lv:
                px = min(lv, o) if o == o else lv
                return (px / P - 1), j, (2 if armed else 1)
            if h == h and h > run:
                run = h
    px = Cw[TS]
    return ((1 - px / P) if side < 0 else (px / P - 1)), TS, 0


def window(o, h, l, cf, e):
    """Cua so phut e..e+TS; phut e trung hoa (duong gia tu e+1, nhu che do tk R1/R1c)."""
    sl = slice(e, e + TS + 1)
    Hw = h[sl].astype(np.float64); Lw = l[sl].astype(np.float64); Ow = o[sl].astype(np.float64); Cw = cf[sl].astype(np.float64)
    assert len(Hw) == TS + 1, "cua so thieu"
    Hw[0] = np.nan; Lw[0] = np.nan; Ow[0] = np.nan
    return Hw, Lw, Ow, Cw


# ───────────────────────── dieu kien xac nhan & entry ─────────────────────────
def confirm(h, l, t, W, lpS, lpL):
    """Chi doc h/l phut t+1..t+W. okS: khong phut nao high huu han >= lpS ; okL: khong phut nao low huu han <= lpL.
    -> okS, okL, phut dau tien vuot len (-1 neu khong), phut dau tien thung xuong (-1)."""
    hs = h[t + 1:t + 1 + W].astype(np.float64); ls = l[t + 1:t + 1 + W].astype(np.float64)
    assert len(hs) == W and len(ls) == W
    with np.errstate(invalid="ignore"):
        up = np.isfinite(hs) & (hs >= lpS); dn = np.isfinite(ls) & (ls <= lpL)
    fu = t + 1 + int(np.argmax(up)) if up.any() else -1
    fd = t + 1 + int(np.argmax(dn)) if dn.any() else -1
    return (not up.any()), (not dn.any()), fu, fd


def entry_px(c, cf, e):
    """close phut e; NaN -> close ffill gan nhat <= e (co danh dau)."""
    P = float(c[e])
    if np.isfinite(P):
        return P, 0
    P = float(cf[e])
    assert np.isfinite(P), "khong co gia entry"
    return P, 1


def sim_trigger(o, h, l, c, cf, t, ct_ref, P_ref):
    """Chi so phut tuong doi buffer. -> rec (k/e/fu/fd tuong doi), legs."""
    ct = float(c[t])
    assert np.isfinite(ct) and abs(ct - ct_ref) <= 1e-6 * ct_ref, "c_t lech cache R1"
    lpS = ct * (1 + DELTA); lpL = ct * (1 - DELTA)
    P1 = float(c[t + 1])
    assert np.isfinite(P1) and abs(P1 - P_ref) <= 1e-9 * P_ref, "P t+1 lech R1"
    rec = dict(c_t=ct, Lp_S=lpS, Lp_L=lpL, P1=P1)
    legs = [("SH1", -1, t + 1, P1)]
    for W in WS:
        okS, okL, fu, fd = confirm(h, l, t, W, lpS, lpL)
        e = t + W + 1
        P, nanp = entry_px(c, cf, e)
        rec.update({"okS%d" % W: okS, "okL%d" % W: okL, "fu%d" % W: fu, "fd%d" % W: fd, "P%d" % W: P, "nanP%d" % W: nanp})
        legs += [("SH%d" % W, -1, e, P), ("LG%d" % W, 1, e, P)]
    for nm, side, e, P in legs:
        pnl, k, rs = exit_vec(*window(o, h, l, cf, e), P, side)
        rec[nm + "_p"] = pnl; rec[nm + "_k"] = e + k; rec[nm + "_r"] = rs; rec[nm + "_e"] = e
    rec["hseq30"] = ",".join("%.8g" % x for x in h[t + 1:t + 31])
    return rec, legs


def sanity_trigger(o, h, l, c, cf, t, rec, legs, rng, st):
    """(iii) causal: nhieu >= t+W+1 -> dieu kien khong doi; nhieu >= t+W+2 -> P khong doi; nhieu >= e+TS+1 -> exit khong doi.
    + vec vs loop thuan cho moi chan."""
    gb = R1C.garble
    ref = rec["c_t"]
    for W in WS:
        cut = t + W + 1
        hh, ll = gb(h, cut, ref, rng), gb(l, cut, ref, rng)
        r2 = confirm(hh, ll, t, W, rec["Lp_S"], rec["Lp_L"])
        st["cond_noise"] += 1
        st["cond_noise_bad"] += int(r2 != (rec["okS%d" % W], rec["okL%d" % W], rec["fu%d" % W], rec["fd%d" % W]))
        cut = t + W + 2
        c2 = gb(c, cut, ref, rng); cf2 = gb(cf, cut, ref, rng)
        P2, _ = entry_px(c2, cf2, t + W + 1)
        st["p_noise"] += 1
        st["p_noise_bad"] += int(P2 != rec["P%d" % W])
    for nm, side, e, P in legs:
        Wd = window(o, h, l, cf, e)
        rv = exit_vec(*Wd, P, side)
        rl = exit_loop(*[list(x) for x in Wd], P, side)
        st["cmp"] += 1
        st["cmp_bad"] += int(not (abs(rv[0] - rl[0]) < 1e-9 and rv[1] == rl[1] and rv[2] == rl[2]))
        cut = e + TS + 1
        W2 = window(gb(o, cut, P, rng), gb(h, cut, P, rng), gb(l, cut, P, rng), gb(cf, cut, P, rng), e)
        st["exit_noise"] += 1
        st["exit_noise_bad"] += int(exit_vec(*W2, P, side) != rv)


def scan_month(args):
    ym, recs = args
    setup_log()
    t0 = time.time()
    tl = [r[1] for r in recs]
    t_lo, t_hi = min(tl), max(tl)
    b0 = t_lo - 2
    b1 = t_hi + max(WS) + 1 + TS + 1
    assert t_lo >= R1C.DEV_M0 and b1 <= DEV_M1, "buffer vuot DEV"
    syms = sorted({r[0] for r in recs})
    arr, nrec = R1C.stream_sel(b0, b1, syms, "r1d-%d" % ym)
    O, H, L, C = arr
    Cf = pd.DataFrame(C).ffill().to_numpy(np.float32)
    idx = {s: i for i, s in enumerate(syms)}
    rng = np.random.default_rng(SEED + ym)
    st = dict(cond_noise=0, cond_noise_bad=0, p_noise=0, p_noise_bad=0, cmp=0, cmp_bad=0, exit_noise=0, exit_noise_bad=0)
    rows = []
    for sym, t, ct_ref, P_ref in recs:
        s = idx[sym]; tt = t - b0
        o, h, l, c, cf = [np.ascontiguousarray(X[:, s]) for X in (O, H, L, C, Cf)]
        rec, legs = sim_trigger(o, h, l, c, cf, tt, ct_ref, P_ref)
        sanity_trigger(o, h, l, c, cf, tt, rec, legs, rng, st)
        for k_ in list(rec):
            if (k_.endswith("_k") or k_.endswith("_e") or k_[:2] in ("fu", "fd")) and rec[k_] >= 0:
                rec[k_] = int(rec[k_]) + b0
        rec["sym"] = sym; rec["t"] = t
        rows.append(rec)
    df = pd.DataFrame(rows)
    df["ym"] = ym
    os.makedirs(CACHE, exist_ok=True)
    df.to_parquet(os.path.join(CACHE, "r1d_%d.parquet" % ym), index=False)
    meta = dict(ym=ym, n=len(recs), nsym=len(syms), nrec=nrec, nmin=int(b1 - b0 + 1), b0=b0, b1=b1,
                secs=round(time.time() - t0, 1), sanity=st)
    json.dump(meta, open(os.path.join(CACHE, "meta_%d.json" % ym), "w"), indent=1, default=str)
    log.info("%s XONG n=%d okS15=%d okS30=%d sanity=%s %.0fs", ym, len(recs), int(df["okS15"].sum()), int(df["okS30"].sum()),
             st, time.time() - t0)
    return meta


# ───────────────────────── report ─────────────────────────
# ten o -> (chan, side, cot mask (None = tat ca), phu dinh mask)
CELLS = {
    "S_W15": ("SH15", -1, "okS15", False), "S_W30": ("SH30", -1, "okS30", False),
    "L_W15": ("LG15", 1, "okL15", False), "L_W30": ("LG30", 1, "okL30", False),
    "X_W15": ("SH15", -1, "okS15", True), "X_W30": ("SH30", -1, "okS30", True),
    "C_15": ("SH1", -1, "okS15", False), "C_30": ("SH1", -1, "okS30", False),
    "T_ALL": ("SH1", -1, None, False),
}
MAIN = ["S_W15", "S_W30"]


def load_set():
    tr, info = R1C.load_trig()
    bad = tr["t"].to_numpy() + max(WS) + 1 + TS > DEV_M1
    info["r1d_dropped_window"] = int(bad.sum())
    tr = tr[~bad].reset_index(drop=True)
    info["r1d_n"] = int(len(tr))
    return tr, info


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


def cell_data(df, name, fd):
    leg, side, mc, neg = CELLS[name]
    m = np.ones(len(df), bool) if mc is None else df[mc].to_numpy(bool)
    if neg:
        m = ~m
    d = df[m]
    e = d[leg + "_e"].to_numpy(np.int64); k = d[leg + "_k"].to_numpy(np.int64)
    assert (k >= e + 1).all() and (k <= e + TS).all() and (k <= DEV_M1).all()
    ein = (e + 1) * MIN - 1
    eout = (k + 1) * MIN - 1
    F, has = R1C.fund_sum(fd, d["sym"].to_numpy(), ein, eout)
    fund = -side * F                       # short: +sum rate ; long: -sum rate
    gross = d[leg + "_p"].to_numpy(np.float64)
    net = gross - FEE_IN - FEE_OUT + fund
    return dict(idx=np.nonzero(m)[0], mask=m, net=net, gross=gross, fund=fund, rsn=d[leg + "_r"].to_numpy(), held=k - e,
                ems=ein, has=has, sym=d["sym"].to_numpy(), e=e, k=k)


def yr_of(ems):
    return pd.to_datetime(np.asarray(ems, np.int64), unit="ms", utc=True).year.to_numpy()


def cell_stats(cd, n_trig):
    net = cd["net"]; ems = cd["ems"]
    ci = ci_block(net, ems)
    yr = yr_of(ems)
    st = net - STRESS
    has = {y: bool((yr == y).any()) for y in YRS}
    by = {str(y): (float(net[yr == y].mean()) if has[y] else None) for y in YRS}
    return dict(n=int(len(net)), entry_rate=float(len(net) / n_trig), mean=float(net.mean()), median=float(np.median(net)),
                win=float((net > 0).mean()), sl_rate=float((cd["rsn"] == 1).mean()), trail_rate=float((cd["rsn"] == 2).mean()),
                time_rate=float((cd["rsn"] == 0).mean()), gross_mean=float(cd["gross"].mean()), fund_mean=float(cd["fund"].mean()),
                held_mean_h=float(cd["held"].mean() / 60), ci_raw=ci["raw"], ci_infl=ci["infl"], nblock=ci["nblock"],
                by_year=by, n_by_year={str(y): int((yr == y).sum()) for y in YRS},
                sl_by_year={str(y): (float((cd["rsn"][yr == y] == 1).mean()) if has[y] else None) for y in YRS},
                years_pos=int(sum(1 for x in by.values() if x is not None and x > 0)),
                stress_mean=float(st.mean()), stress_by_year={str(y): (float(st[yr == y].mean()) if has[y] else None) for y in YRS},
                stress_years_pos=int(sum(1 for y in YRS if has[y] and st[yr == y].mean() > 0)),
                net_min=float(net.min()), net_p1=float(np.percentile(net, 1)), net_p5=float(np.percentile(net, 5)),
                net_p99=float(np.percentile(net, 99)), net_max=float(net.max()), frac_has_funding=float(cd["has"].mean()))


def pct(x, nd=3):
    return "n/a" if x is None else ("%+.*f" % (nd, 100 * x))


def jd(x):
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return str(x)


def report(tr, info):
    fs = sorted(glob.glob(os.path.join(CACHE, "r1d_*.parquet")))
    yms = sorted(int(os.path.basename(f)[4:10]) for f in fs)
    assert yms == sorted(set(tr["ym"].tolist())), "thieu thang: %s" % sorted(set(tr["ym"]) - set(yms))
    sc = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    metas = [json.load(open(os.path.join(CACHE, "meta_%d.json" % y))) for y in yms]
    df = tr[["sym", "t"]].merge(sc, on=["sym", "t"], how="left", validate="1:1", indicator=True)
    assert (df["_merge"] == "both").all() and len(df) == len(tr)
    df = df.drop(columns="_merge").sort_values("t", kind="stable").reset_index(drop=True)
    n_trig = len(df)
    fd, finfo = R1C.load_fund()
    cds = {nm: cell_data(df, nm, fd) for nm in CELLS}
    cells = {nm: cell_stats(cd, n_trig) for nm, cd in cds.items()}
    for nm, x in cells.items():
        log.info("%-6s n=%5d mean=%+.4f%% med=%+.3f%% ci=[%+.3f;%+.3f] infl=[%+.3f;%+.3f] yrs=%d sl=%.3f stress=%+.4f%%", nm, x["n"],
                 100 * x["mean"], 100 * x["median"], 100 * x["ci_raw"][0], 100 * x["ci_raw"][1], 100 * x["ci_infl"][0],
                 100 * x["ci_infl"][1], x["years_pos"], x["sl_rate"], 100 * x["stress_mean"])
    go = {}
    for W in WS:
        c = "S_W%d" % W
        x = cells[c]; xl = cells["L_W%d" % W]; xx = cells["X_W%d" % W]
        g = dict(G1=bool(x["mean"] > 0 and x["ci_raw"][0] > 0 and x["ci_infl"][0] > 0), G2=bool(x["years_pos"] >= 3),
                 G3=bool(x["n"] >= 1500), G4=bool(x["sl_rate"] <= 0.25), G5=bool(x["stress_mean"] > 0), G6=bool(xl["mean"] <= 0),
                 G7=bool(xx["mean"] < x["mean"]))
        g["ALL"] = bool(all(g.values()))
        go[c] = g
    passing = [c for c in MAIN if go[c]["ALL"]]
    verdict = "GO" if passing else "NO-GO"
    best = max(passing or MAIN, key=lambda c: cells[c]["mean"])
    log.info("GO table %s", go)

    # ── sanity (i) tap W15 = no-fill R1c ; (ii) tai lap C_15 / T_ALL vs R1c S_TK24
    r1c = pd.read_csv(R1C_TR, usecols=["sym", "t", "Lp_S", "f_S", "S_TK24_net", "S_TK24_k", "S_TK24_r"])
    dm = df[["sym", "t", "okS15", "Lp_S", "hseq30", "SH1_k", "SH1_r"]].merge(r1c, on=["sym", "t"], how="left", validate="1:1",
                                                                           suffixes=("", "_r1c"))
    assert dm["f_S"].notna().all()
    nofill = dm["f_S"].to_numpy() < 0
    ok15 = dm["okS15"].to_numpy(bool)
    mis = np.nonzero(nofill != ok15)[0]
    s_i = dict(n_nofill_r1c=int(nofill.sum()), n_okS15=int(ok15.sum()), n_mismatch=int(len(mis)),
               lp_maxreldiff=float(np.max(np.abs(dm["Lp_S"] - dm["Lp_S_r1c"]) / dm["Lp_S_r1c"])),
               mismatches=[dict(sym=dm.at[i, "sym"], t=int(dm.at[i, "t"]), okS15=bool(ok15[i]), f_S_r1c=int(dm.at[i, "f_S"]),
                                Lp=float(dm.at[i, "Lp_S"]), highs15=dm.at[i, "hseq30"].split(",")[:15]) for i in mis[:20]])
    s_i["PASS"] = bool(len(mis) == 0)
    s_ii = {}
    for nm, msk in (("C_15", ok15), ("T_ALL", np.ones(len(df), bool))):
        cd = cds[nm]
        assert (cd["idx"] == np.nonzero(msk)[0]).all()
        ref = dm["S_TK24_net"].to_numpy()[msk]
        dn = cd["net"] - ref
        s_ii[nm] = dict(n=int(msk.sum()), mean_new=float(cd["net"].mean()), mean_r1c=float(ref.mean()), max_abs_diff=float(np.abs(dn).max()),
                        k_match=float((dm["SH1_k"].to_numpy()[msk] == dm["S_TK24_k"].to_numpy()[msk]).mean()),
                        r_match=float((dm["SH1_r"].to_numpy()[msk] == dm["S_TK24_r"].to_numpy()[msk]).mean()))
        s_ii[nm]["PASS"] = bool(s_ii[nm]["max_abs_diff"] < 1e-6 and s_ii[nm]["k_match"] == 1 and s_ii[nm]["r_match"] == 1)
    s_ii["r1c_nofill_mean_from_csv"] = float(dm.loc[nofill, "S_TK24_net"].mean())
    # ── sanity (iii) gop tu scan
    sm = {}
    for m in metas:
        for k_, v in m["sanity"].items():
            sm[k_] = sm.get(k_, 0) + v
    sm["PASS"] = bool(sm["cond_noise"] == 2 * n_trig and all(sm[k_] == 0 for k_ in sm if k_.endswith("_bad")))
    log.info("sanity i=%s ii=%s iii=%s", {k_: v for k_, v in s_i.items() if k_ != "mismatches"}, s_ii, sm)

    # ── sanity (iv) 10 mau S_W15 + 5 mau X_W15
    rng = np.random.default_rng(SEED)
    samples = []
    for nm, nsamp in (("S_W15", 10), ("X_W15", 5)):
        for i in np.sort(rng.choice(cds[nm]["idx"], nsamp, replace=False)):
            r = df.iloc[i]
            hs = np.array([float(x) for x in r["hseq30"].split(",")[:15]])
            mx = float(np.nanmax(hs)) if np.isfinite(hs).any() else float("nan")
            samples.append(dict(cell=nm, sym=r["sym"], t_utc=str(pd.Timestamp(int(r["t"]) * MIN, unit="ms")), c_t=float(r["c_t"]),
                                Lp=float(r["Lp_S"]), highs_t1_t15=r["hseq30"].split(",")[:15], max_high15=mx,
                                hand_check_max_lt_Lp=bool(mx < r["Lp_S"]), first_up_after_t=(int(r["fu15"] - r["t"]) if r["fu15"] >= 0 else None),
                                P1=float(r["P1"]), P16=float(r["P15"]), reason=int(r["SH15_r"]), gross=float(r["SH15_p"]),
                                held_min=int(r["SH15_k"] - r["SH15_e"]), gross_t1=float(r["SH1_p"])))
    s_iv = dict(samples=samples, PASS=bool(all(s["hand_check_max_lt_Lp"] == (s["cell"] == "S_W15") for s in samples)))
    # ── ti le vao lenh theo nam trigger, chong lan cung coin, troi gia khi cho, phan ra
    yt = yr_of(df["t"].to_numpy(np.int64) * MIN)
    rates = {}
    for nm in ("S_W15", "S_W30", "L_W15", "L_W30"):
        msk = cds[nm]["mask"]
        rates[nm] = dict(all=float(msk.mean()), by_year={str(y): float(msk[yt == y].mean()) for y in YRS})
    rates["n_trig_by_year"] = {str(y): int((yt == y).sum()) for y in YRS}
    overlap = {}
    for nm in ("S_W15", "S_W30"):
        cd = cds[nm]
        o_ = pd.DataFrame(dict(sym=cd["sym"], e=cd["e"], k=cd["k"])).sort_values(["sym", "e"])
        prev_k = o_.groupby("sym")["k"].shift(1)
        overlap[nm] = int((o_["e"] <= prev_k).sum())
    drift = {}
    for W in WS:
        r_ = df["P%d" % W].to_numpy() / df["P1"].to_numpy() - 1
        okm = df["okS%d" % W].to_numpy(bool)
        drift[str(W)] = dict(S_mean=float(r_[okm].mean()), S_median=float(np.median(r_[okm])), X_mean=float(r_[~okm].mean()),
                             X_median=float(np.median(r_[~okm])), n_nanP=int(df["nanP%d" % W].sum()))
    dec = {}
    for W in WS:
        cS, cC = cells["S_W%d" % W], cells["C_%d" % W]
        dec[str(W)] = dict(C_minus_S=cC["mean"] - cS["mean"], gross_diff=cC["gross_mean"] - cS["gross_mean"],
                           fund_diff=cC["fund_mean"] - cS["fund_mean"], sl_C=cC["sl_rate"], sl_S=cS["sl_rate"],
                           frac_edge_lost=(cC["mean"] - cS["mean"]) / cC["mean"] if cC["mean"] != 0 else None)

    # ── bang md nhap (ngoai repo)
    L_ = ["| o | n | vao% | mean | median | CI raw | CI infl x1,18 | 2022 / 2023 / 2024 / 2025 | SL | TRAIL | TIME | win | gross | fund | held h | min | p1 | p5 | stress | stress yrs+ |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for nm in ("S_W15", "S_W30", "L_W15", "L_W30", "X_W15", "X_W30", "C_15", "C_30", "T_ALL"):
        x = cells[nm]
        L_.append("| %s | %d | %.1f%% | %s | %s | [%s; %s] | [%s; %s] | %s | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %s | %s | %.1f | %.1f%% | %.1f%% | %.1f%% | %s | %d |" % (
            nm, x["n"], 100 * x["entry_rate"], pct(x["mean"]), pct(x["median"], 2), pct(x["ci_raw"][0]), pct(x["ci_raw"][1]),
            pct(x["ci_infl"][0]), pct(x["ci_infl"][1]), " / ".join(pct(x["by_year"][y], 2) for y in ("2022", "2023", "2024", "2025")),
            100 * x["sl_rate"], 100 * x["trail_rate"], 100 * x["time_rate"], 100 * x["win"], pct(x["gross_mean"]), pct(x["fund_mean"]),
            x["held_mean_h"], 100 * x["net_min"], 100 * x["net_p1"], 100 * x["net_p5"], pct(x["stress_mean"]), x["stress_years_pos"]))
    L_ += ["", "| o | G1 | G2 | G3 | G4 | G5 | G6 | G7 | ALL |", "|---|---|---|---|---|---|---|---|---|"]
    for c in MAIN:
        L_.append("| %s | %s |" % (c, " | ".join("Y" if go[c][k_] else "N" for k_ in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "ALL"))))
    open(os.path.join(CACHE, "r1d_tables.md"), "w").write("\n".join(L_) + "\n")
    res = dict(prereg="PREREG_SHORT_V3_R1D (c30a72b4)", program="PROGRAM_SHORT_V3 ADDENDUM 3 75dddd89", r1c="e7c3e09d", r1="3fea4f50",
               conv=dict(fee_in=FEE_IN, fee_out=FEE_OUT, stress=STRESS, delta=DELTA, W=WS, ts_min=TS, branch_B=dict(a=A_, g=G_, s=S_),
                         nrep=NREP, seed=SEED, infl=INFL, block_h=72, dev_last_minute_utc=str(pd.Timestamp(DEV_M1 * MIN, unit="ms"))),
               trigger_set=info, verdict=verdict, passing=passing, best_cell=best, go_table=go, cells=cells, entry_rates=rates,
               decomposition_late_entry=dec, price_drift_wait=drift, same_coin_overlap=overlap,
               sanity=dict(i_set_W15_eq_nofill=s_i, ii_reproduce=s_ii, iii_causal_vecloop=sm, iv_samples=s_iv),
               funding_info=finfo, months=[{k_: v for k_, v in m.items() if k_ != "sanity"} for m in metas])
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=jd)
    for nm, cd in cds.items():
        col = np.full(len(df), np.nan); col[cd["idx"]] = cd["net"]
        df[nm + "_net"] = col
    keep = ["sym", "t", "c_t", "Lp_S", "Lp_L", "P1", "P15", "P30", "okS15", "okS30", "okL15", "okL30", "fu15", "fu30"] + \
        [lg + s for lg in LEGS for s in ("_r", "_e", "_k")] + [nm + "_net" for nm in CELLS]
    df[keep].to_csv(os.path.join(CACHE, "trades_r1d.csv"), index=False)
    log.info("VERDICT %s passing=%s best=%s -> %s", verdict, passing, best, OUT_JSON)



def main():
    setup_log()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["scan", "report"])
    ap.add_argument("--months", default="all")
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    tr, info = load_set()
    log.info("tap trigger: R1 %d -> R1c %d -> R1d %d (loai them cua so W+1+1440: %d)", info["n_r1"], info["n_kept"], info["r1d_n"],
             info["r1d_dropped_window"])
    if a.stage == "report":
        report(tr, info); return
    allm = sorted(set(tr["ym"].tolist()))
    months = allm if a.months == "all" else [int(x) for x in a.months.split(",")]
    todo = [m for m in months if a.force or not os.path.exists(os.path.join(CACHE, "r1d_%d.parquet" % m))]
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
