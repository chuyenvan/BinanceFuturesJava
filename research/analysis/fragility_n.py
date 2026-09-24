#!/usr/bin/env python3
"""FRAGILITY-N — do do venh theo n + kiem gia thuyet 1x (docs/PREREG_FRAGILITY_N.md).

THUAN PYTHON OFFLINE tren artifact DA CO. KHONG chay sim, KHONG Java.
  VIEC A: leverage = margin/(qty*entry) tren MOI leg; max concurrent margin (quet start/end);
          max margin/equity theo thoi gian (equity = b + unP tu logs/sim.out);
          proxy 'mat that' (pnl/margin <= -0.90); tran mat-that 1 coin.
  VIEC B: n / meanP / relSE (bootstrap block-72h, 2000 rep, seed 20260905) / MDE95 /
          drop-top-K best-worst / share top 1-5-10% / SD+range ret% nam / N_eff / conc 1 coin.
  Tra loi (a) bo 1%/2% so lenh theo best|worst|random; (b) 1 coin ve 0 => mat bao nhieu % equity.

Usage: python3 fragility_n.py [--main-only] [--json /home/ubuntu/fragility/fragility.json]
"""
import json
import math
import os
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C
import gd92xexit_score as G

OUTDIR = "/home/ubuntu/fragility"
ANCHOR = pd.Timestamp("2021-07-01")
SEED = C.SEED              # 20260905
NREP = C.NREP              # 2000
BLOCK_H = C.BLOCK_H        # 72
CAP0 = 35000.0             # CAPITAL_START
RX_MARGIN = re.compile(
    r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?\tm:\s*(-?\d+).*?\tmax:\s*(-?\d+)\t\s*(-?\d+)"
    r".*?unP:\s*(-?\d+)")

MAIN = ["T170", "T100", "GD92"]
ALL_RUNS = [
    ("T170", "t170-x1-2021"), ("T100", "hn-t100"), ("GD92", "hn-g92"),
    ("tl-l1", "tl-l1"), ("tl-l2", "tl-l2"), ("tl-l3", "tl-l3"),
    ("pc-close", "pc-close"), ("tc-cap", "tc-cap"),
    ("hn-g-hi", "hn-g-hi"), ("hn-g-la", "hn-g-la"), ("hn-g-cp", "hn-g-cp"),
    ("hn-t-hi", "hn-t-hi"), ("hn-t-la", "hn-t-la"), ("hn-t-cp", "hn-t-cp"),
]
NEN = {"T170": "Z", "T100": "T", "GD92": "G"}
KOUT = "/home/ubuntu/kaggle_sim/out"
# tag -> thu muc THAT (T170/T100/GD92 la ten nghiep vu, khong phai ten thu muc)
DIRS = {t: os.path.join(KOUT, d) for t, d in ALL_RUNS}
G.DIRS = dict(DIRS)          # gd92xexit_score doc qua G.base()/G.DIRS


# ---------------------------------------------------------------- helpers
def tsfmt(t):
    """int64 phut -> 'YYYY-MM-DD HH:MM'."""
    return pd.to_datetime(int(t), unit="m").strftime("%Y-%m-%d %H:%M")


def dup_daily(s):
    """Bo trung ngay (giu gia tri cuoi) — y nhu gd92xexit_score.equity."""
    return s[~s.index.duplicated(keep="last")]


def margin_daily(tag):
    """Chuoi NGAY: (equity=b+unP, margin m, margin max trong ngay `max`, margin max thang)."""
    _, sout = G._paths(tag)
    rows = []
    with open(sout, errors="ignore") as fh:
        for line in fh:
            m = RX_MARGIN.search(line)
            if m:
                g = m.groups()
                rows.append((g[0], int(g[1]) + int(g[5]), int(g[5]), int(g[2]), int(g[3]), int(g[4])))
    df = pd.DataFrame(rows, columns=["d", "eq", "unP", "m", "mmax", "mmonth"])
    df = df.drop_duplicates("d", keep="last")
    df["d"] = pd.to_datetime(df.d, format="%Y%m%d")
    return df.set_index("d")


def legs(tag):
    """Leg da chuan hoa: them ts (start), te (end), lv, pnl, margin, qty, entry."""
    d = G.trades(tag).copy()
    d["te"] = pd.to_datetime(d["end"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["ts", "te", "pnl", "margin"]).copy()
    d["lv"] = d["margin"] / (d["quantity"] * d["entry"])
    d["day"] = d["te"].dt.floor("D")
    return d.reset_index(drop=True)


def maxdd_uw(series):
    """maxDD% va UW (so ngay duoi dinh lien tuc dai nhat) tren chuoi ngay."""
    s = series.astype(float)
    dd = (s / s.cummax() - 1) * 100
    uw = (s < s.cummax()).groupby((s >= s.cummax()).cumsum()).sum()
    return float(dd.min()), (int(uw.max()) if len(uw) else 0)


def proxy_curve(d):
    """Duong equity PROXY = CAPITAL_START + Σpnl tich luy theo `end`, resample NGAY.

    Neo tai 35000 (CAPITAL_START) vi day la von ban dau; neu neo tai 0 thi cac dip som
    (vd 2022-05-12) bi phong dai vo nghia so voi duong equity THAT.
    """
    return CAP0 + realized_curve(d)


def realized_curve(d):
    g = d.sort_values(["te"], kind="mergesort")
    cum = g["pnl"].cumsum()
    cum.index = g["day"].values
    return cum.groupby(level=0).last()


def sweep(d):
    """Quet start/end => max concurrent margin (2 bien) + margin theo coin tai moi moc."""
    st = d["ts"].values.astype("datetime64[m]").astype(np.int64)
    en = d["te"].values.astype("datetime64[m]").astype(np.int64)
    mg = d["margin"].values.astype(float)
    o = np.argsort(st, kind="mergesort")
    st, mg_st = st[o], mg[o]
    o2 = np.argsort(en, kind="mergesort")
    en, mg_en = en[o2], mg[o2]
    times = np.unique(np.concatenate([st, en]))
    cum_st = np.cumsum(mg_st)
    cum_en = np.cumsum(mg_en)
    # starts-first (CAN TREN): count start<=t ; end<t
    i_st = np.searchsorted(st, times, side="right")
    i_en = np.searchsorted(en, times, side="left")
    S_hi = np.where(i_st > 0, cum_st[np.maximum(i_st - 1, 0)], 0.0) \
        - np.where(i_en > 0, cum_en[np.maximum(i_en - 1, 0)], 0.0)
    # ends-first (CAN DUOI): start<=t ; end<=t
    i_en2 = np.searchsorted(en, times, side="right")
    S_lo = np.where(i_st > 0, cum_st[np.maximum(i_st - 1, 0)], 0.0) \
        - np.where(i_en2 > 0, cum_en[np.maximum(i_en2 - 1, 0)], 0.0)
    return times, S_hi, S_lo


def eq_at(eqday, times):
    """Equity NGAY cuoi cung <= moc (asof ffill)."""
    idx = pd.DatetimeIndex(times.astype("datetime64[m]"))
    return eqday.reindex(idx, method="ffill").to_numpy()


def coin_exposure(d, eqday):
    """max_t (margin 1 coin / equity(t)) × 100 — tran MAT THAT neu coin ve 0."""
    best = (0.0, None, None)
    for sym, g in d.groupby("sym"):
        t, hi, _ = sweep(g)
        if len(t) == 0:
            continue
        e = eq_at(eqday, t)
        e = np.where((e > 0) & np.isfinite(e), e, np.nan)
        r = hi / e
        j = int(np.nanargmax(r)) if np.isfinite(r).any() else -1
        if j >= 0 and np.isfinite(r[j]) and r[j] > best[0]:
            best = (float(r[j]), str(sym), tsfmt(t[j]))
    # them: dinh margin TUYET DOI cua 1 coin
    absmax = (0.0, None)
    for sym, g in d.groupby("sym"):
        _, hi, _ = sweep(g)
        if len(hi) and hi.max() > absmax[0]:
            absmax = (float(hi.max()), str(sym))
    return best, absmax


def blocks_of(d):
    return ((d["ts"] - ANCHOR) / pd.Timedelta(hours=BLOCK_H)).astype(np.int64).to_numpy()


def se_boot(d, nrep=NREP, seed=SEED):
    """Bootstrap block-72h tren leg => SE cua mean(pnl); tra (SE, mean_blk, nblk)."""
    v = d["pnl"].to_numpy(float)
    b = blocks_of(d)
    ub, inv = np.unique(b, return_inverse=True)
    nv = np.bincount(inv, weights=v)
    nc = np.bincount(inv)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ub), size=(nrep, len(ub)))
    num = nv[idx].sum(axis=1)
    den = nc[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = num / den
    m = m[np.isfinite(m)]
    return float(m.std(ddof=1)), float(m.mean()), len(ub)


def drop(d, k, side):
    """Bo k leg tot nhat / xau nhat; tra ve (d_con, delta%) va chi tieu proxy."""
    if k <= 0:
        return d, 0.0
    o = d["pnl"].sort_values(ascending=(side == "worst")).index[:k]
    rest = d.drop(index=o)
    tot0, tot1 = d["pnl"].sum(), rest["pnl"].sum()
    return rest, (tot1 - tot0) / tot0 * 100.0


def neff_overlap(d):
    """So cum 'bet doc lap' theo (a) cung coin + cua so giu chong nhau."""
    tot = 0
    for sym, g in d.groupby("sym"):
        g = g.sort_values("ts")
        cur_end, comps = None, 0
        for s, e in zip(g["ts"].values, g["te"].values):
            if cur_end is None or s > cur_end:
                comps += 1
                cur_end = e
            elif e > cur_end:
                cur_end = e
        tot += comps
    return tot


# ---------------------------------------------------------------- VIEC A
def viec_a(tag):
    d = legs(tag)
    md = margin_daily(tag)
    eqday = dup_daily(md["eq"])
    r = {}
    lv = d["lv"]
    r["n_leg"] = int(len(d))
    r["lv_eq1"] = int((np.abs(lv - 1.0) <= 1e-6).sum())
    r["lv_min"] = float(lv.min()); r["lv_max"] = float(lv.max())
    r["lv_gt_1.05"] = int((lv > 1.05).sum())
    r["lv_bad"] = [float(x) for x in lv[np.abs(lv - 1.0) > 1e-6][:10]]

    times, S_hi, S_lo = sweep(d)
    e = eq_at(eqday, times)
    ok = (e > 0) & np.isfinite(e)
    j_hi = int(np.argmax(S_hi))
    j_lo = int(np.argmax(S_lo))
    r["peak_margin_hi"] = float(S_hi.max())
    r["peak_margin_lo"] = float(S_lo.max())
    r["peak_time_hi"] = tsfmt(times[j_hi])
    r["peak_time_lo"] = tsfmt(times[j_lo])
    r["n_events"] = int(len(times))
    r["peak_over_cap0_hi"] = r["peak_margin_hi"] / CAP0 * 100
    r["peak_over_cap0_lo"] = r["peak_margin_lo"] / CAP0 * 100
    if ok.any():
        ratio = np.where(ok, S_hi / np.where(ok, e, 1.0), np.nan)
        jr = int(np.nanargmax(ratio))
        r["max_margin_over_equity_hi"] = float(ratio[jr]) * 100
        r["t_max_ratio_hi"] = tsfmt(times[jr])
        r["eq_at_peak_hi"] = float(e[j_hi]) if np.isfinite(e[j_hi]) else float("nan")
        r["peak_over_equity_at_peak_hi"] = (S_hi[j_hi] / e[j_hi] * 100) if np.isfinite(e[j_hi]) and e[j_hi] > 0 else float("nan")
        r["n_exposure_gt_equity"] = int((np.where(ok, S_hi, 0) > np.where(ok, e, np.inf)).sum())
        # ban 'ends-first' (khong the > ban starts-first)
        ratio2 = np.where(ok, S_lo / np.where(ok, e, 1.0), np.nan)
        r["max_margin_over_equity_lo"] = float(np.nanmax(ratio2)) * 100
    # kiem cheo bang chuoi NGAY cua sim.out
    dcheck = dup_daily(md["mmax"] / md["eq"]) * 100
    r["daily_mmax_over_eq_max"] = float(dcheck.max())
    r["daily_mmax_over_eq_day"] = str(dcheck.idxmax().date())
    r["daily_m_over_eq_max"] = float((md["m"] / md["eq"]).max() * 100)

    # A6 mat that
    pm = (d["pnl"] / d["margin"])
    r["pm_min"] = float(pm.min())
    dead = d[(pm <= -0.90)]
    r["n_deadleg"] = int(len(dead))
    r["dead_pnl"] = float(dead["pnl"].sum())
    r["dead_share_of_total"] = float(dead["pnl"].sum() / d["pnl"].sum() * 100)
    r["n_below_-0.5"] = int((pm <= -0.50).sum())
    r["n_below_-0.3"] = int((pm <= -0.30).sum())
    best, absmax = coin_exposure(d, eqday)
    r["coin_max_exposure_pct"] = best[0] * 100
    r["coin_max_exposure_sym"] = best[1]
    r["coin_max_exposure_time"] = best[2]
    r["coin_max_abs_margin"] = absmax[0]
    r["coin_max_abs_margin_sym"] = absmax[1]
    # top-5 coin tran
    tr = []
    for sym, g in d.groupby("sym"):
        t, hi, _ = sweep(g)
        if not len(t):
            continue
        e2 = eq_at(eqday, t)
        e2 = np.where((e2 > 0) & np.isfinite(e2), e2, np.nan)
        with np.errstate(invalid="ignore"):
            tr.append((float(np.nanmax(hi / e2)) * 100 if np.isfinite(hi / e2).any() else -1, str(sym), float(hi.max())))
    tr.sort(reverse=True)
    r["coin_top5"] = [(round(a, 2), b, int(c)) for a, b, c in tr[:5]]
    r["_d"] = d; r["_eqday"] = eqday
    return r


# ---------------------------------------------------------------- VIEC B
def viec_b(tag):
    d = legs(tag)
    md = margin_daily(tag)
    eqday = dup_daily(md["eq"])
    s_true = eqday
    r = {}
    r["n"] = int(len(d))
    r["meanP"] = float(d["pnl"].mean())
    r["sd"] = float(d["pnl"].std(ddof=1))
    se_b, mean_b, nblk = se_boot(d)
    r["nblk"] = nblk
    r["se_boot"] = se_b
    r["se_naive"] = r["sd"] / math.sqrt(r["n"])
    r["relSE"] = se_b / r["meanP"] if r["meanP"] else float("nan")
    r["relSE_naive"] = r["se_naive"] / r["meanP"] if r["meanP"] else float("nan")
    r["relSE_x_sqrtn"] = r["relSE"] * math.sqrt(r["n"])
    r["MDE95"] = 1.96 * se_b
    r["MDE95_pct_of_mean"] = r["MDE95"] / r["meanP"] * 100 if r["meanP"] else float("nan")
    r["total_pnl"] = float(d["pnl"].sum())

    tot = r["total_pnl"]
    cur0 = proxy_curve(d)
    dd0, uw0 = maxdd_uw(cur0)
    r["proxy_maxDD"] = dd0; r["proxy_UW"] = uw0
    r["proxy_days"] = int(len(cur0))
    st = G.summary(tag)
    r["true_maxDD"] = st["maxDD"]; r["true_UW"] = st["uw"]; r["true_conc"] = st["conc"]
    r["true_end_eq"] = st["end"]; r["cagr"] = st["cagr"]
    dropk = {}
    for k in sorted({1, 5, math.ceil(0.01 * r["n"]), math.ceil(0.05 * r["n"])}):
        for side in ("best", "worst"):
            rest, dpnl = drop(d, k, side)
            c = proxy_curve(rest)
            dd, uw = maxdd_uw(c)
            dropk["K%d_%s" % (k, side)] = dict(
                k=k, side=side, removed_legs=k, removed_pnl=float(d["pnl"].sum() - rest["pnl"].sum()),
                dPnL_pct=float(dpnl), new_total=float(rest["pnl"].sum()),
                maxDD=dd, dmaxDD_pp=float(dd - dd0), UW=uw, dUW=int(uw - uw0))
    r["dropk"] = dropk
    # B4 share
    v = np.sort(d["pnl"].to_numpy(float))[::-1]
    for q in (1, 5, 10):
        k = max(1, math.ceil(q / 100.0 * r["n"]))
        r["share_top%d_pct" % q] = float(v[:k].sum() / tot * 100)
        r["share_bot%d_pct" % q] = float(v[-k:].sum() / tot * 100)
    # B5 ret% nam (equity THAT, b+unP)
    y = G.yearly_detail(tag)
    r["years"] = {int(k): dict(n=v["n"], ret=v["ret"], maxDD=v["maxDD"], uw=v["uw"], pnl=v["pnl_usdt"])
                  for k, v in y.items()}
    rr = [v["ret"] for v in r["years"].values()]
    r["ret_sd_years"] = float(np.std(rr, ddof=1)) if len(rr) > 1 else float("nan")
    r["ret_range_years"] = float(max(rr) - min(rr))
    r["ret_min_year"] = float(min(rr)); r["ret_max_year"] = float(max(rr))
    r["n_years"] = len(rr)
    # B6 N_eff
    ne_a = neff_overlap(d)
    ne_b = int(d["ts"].dt.isocalendar().week.astype(int).astype(str).radd(
        d["ts"].dt.isocalendar().year.astype(int).astype(str) + "-").nunique())
    r["N_eff_overlap"] = ne_a; r["N_eff_overlap_ratio"] = ne_a / r["n"]
    r["N_eff_week"] = ne_b; r["N_eff_week_ratio"] = ne_b / r["n"]
    r["n_days"] = int(d["ts"].dt.date.nunique())
    r["_d"] = d
    return r


def answer_a(tag, d, rules=(1.0, 2.0)):
    """Bo 1%/2% so lenh theo best | worst | random(2000, seed)."""
    n = len(d); tot = d["pnl"].sum()
    pnl = d["pnl"].to_numpy(float)
    order = np.argsort(pnl)
    rng = np.random.default_rng(SEED)
    out = {}
    for p in rules:
        k = max(1, math.ceil(p / 100.0 * n))
        best = (pnl[order[-k:]].sum()) / tot * 100
        worst = (pnl[order[:k]].sum()) / tot * 100
        idx = rng.random((NREP, n)).argpartition(k - 1, axis=1)[:, :k]
        sim = pnl[idx].sum(axis=1)
        out["pct%g" % p] = dict(
            k=k,
            best=float(-best), worst=float(-worst),
            rand_mean=float(-sim.mean() / tot * 100),
            rand_p5=float(-np.percentile(sim, 95) / tot * 100),
            rand_p95=float(-np.percentile(sim, 5) / tot * 100),
            rand_min=float(-sim.max() / tot * 100), rand_max=float(-sim.min() / tot * 100))
    return out


def funding_term(tag):
    """So hang SO HOC per-leg: funding (tu printDone) / tong PnL / n."""
    d = legs(tag)
    f = pd.to_numeric(d["funding"], errors="coerce").fillna(0.0)
    return dict(n=len(d), funding_sum=float(f.sum()), funding_mean=float(f.mean()),
                funding_over_pnl=float(f.sum() / d["pnl"].sum() * 100),
                pnl_sum=float(d["pnl"].sum()))


def dump(A, B, ANS_A, ANS_B, runs):
    """Ghi bang trung gian ra /home/ubuntu/fragility/."""
    rows_a = []
    for t in runs:
        a = A[t]
        rows_a.append(dict(run=t, **{k: v for k, v in a.items() if not isinstance(v, list)}))
    pd.DataFrame(rows_a).to_csv(os.path.join(OUTDIR, "fragility_A_1x.csv"), index=False)

    rows_d = []
    for t in runs:
        for k, v in B[t]["dropk"].items():
            rows_d.append(dict(run=t, rule=k, **v))
    pd.DataFrame(rows_d).to_csv(os.path.join(OUTDIR, "fragility_B_dropK.csv"), index=False)

    rows_b = []
    for t in runs:
        b = {k: v for k, v in B[t].items() if not isinstance(v, (dict, list))}
        rows_b.append(dict(run=t, **b))
    pd.DataFrame(rows_b).to_csv(os.path.join(OUTDIR, "fragility_B_main.csv"), index=False)

    rows_aa = []
    for t in runs:
        for p, v in ANS_A[t].items():
            rows_aa.append(dict(run=t, pct=p, **v))
    pd.DataFrame(rows_aa).to_csv(os.path.join(OUTDIR, "fragility_answer_a.csv"), index=False)

    rows_y = []
    for t in runs:
        for y, v in B[t]["years"].items():
            rows_y.append(dict(run=t, year=y, **v))
    pd.DataFrame(rows_y).to_csv(os.path.join(OUTDIR, "fragility_years.csv"), index=False)

    with open(os.path.join(OUTDIR, "fragility_answer_b.txt"), "w") as f:
        for t in runs:
            b = ANS_B[t]
            f.write("%s: max 1-coin exposure %.2f%% equity (sym=%s @ %s); margin abs max %.0f (%s)\n"
                    % (t, b["coin_pct"], b["sym"], b["time"], b["abs_margin"], b["abs_sym"]))
            f.write("   top5: %s\n" % (b["top5"],))

    rows_f = []
    for t in runs:
        rows_f.append(dict(run=t, **funding_term(t)))
    pd.DataFrame(rows_f).to_csv(os.path.join(OUTDIR, "fragility_funding.csv"), index=False)
    print("[csv] %s/{fragility_A_1x,fragility_B_main,fragility_B_dropK,fragility_answer_a,fragility_years,fragility_funding}.csv" % OUTDIR)


# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUTDIR, exist_ok=True)
    args = sys.argv[1:]
    main_only = "--main-only" in args
    runs = MAIN if main_only else [t for t, _ in ALL_RUNS]
    A, B, ANS_A, ANS_B = {}, {}, {}, {}
    for tag in runs:
        try:
            a = viec_a(tag); b = viec_b(tag)
        except Exception as e:      # thieu du lieu => ghi ro, KHONG bia
            print("!! %s: KHONG DO DUOC (%s)" % (tag, e)); continue
        d = a.pop("_d"); b.pop("_d")
        A[tag] = a; B[tag] = b
        ANS_A[tag] = answer_a(tag, d)
        ANS_B[tag] = dict(coin_pct=a["coin_max_exposure_pct"], sym=a["coin_max_exposure_sym"],
                          time=a["coin_max_exposure_time"], top5=a["coin_top5"],
                          abs_margin=a["coin_max_abs_margin"], abs_sym=a["coin_max_abs_margin_sym"])
        print("done %s" % tag)
    with open(os.path.join(OUTDIR, "fragility.json"), "w") as f:
        json.dump(dict(A=A, B=B, ans_a=ANS_A, ans_b=ANS_B), f, indent=1, default=str)
    print("[json] %s/fragility.json" % OUTDIR)
    dump(A, B, ANS_A, ANS_B, list(A.keys()))
    return A, B, ANS_A, ANS_B


if __name__ == "__main__":
    main()
