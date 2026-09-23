"""ALT REGIME WAVES - do hanh vi ALT (MO TA, 0-sim).

Theo docs/PREREG_ALT_REGIME_WAVES.md (commit b0e91fa) - khoa dinh nghia/nguong TRUOC khi do.
DEV = 2021-01-01..2025-12-31 (CLOSES_1H.bin). Post-DEV = 2026-01-01..2026-09-22 (ticker bins +
Aerospike). Khong chay Java, khong sim, khong tune, khong push.

Chay: python3 research/analysis/alt_regime_waves.py
Out:  research/analysis/out/alt_regime_waves.json + .csv
"""
import datetime as dt
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import altdata  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
L = logging.getLogger("altwaves")

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)

MAJORS = altdata.MAJORS
DEV_END = pd.Timestamp("2025-12-31")
HOR = (90, 180, 365, 730)
BR_THR = 70.0
BR_LEN = 5
BR_MIN_DEN = 15
CORR_MIN_N = 25
CORR_MIN_ALT = 15
NREP = 2000
SEED = 20260923
BLOCK = 7
INFLATE = 1.21
T170 = "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv"
SHADOW = "/home/ubuntu/java/fsrun/storage/printDone.csv"


# ---------------------------------------------------------------- helpers
def year_ends(idx):
    out = []
    for y in range(2021, 2026):
        d = pd.Timestamp("%d-12-31" % y)
        if d in idx:
            out.append(d)
    return out


def pct(a):
    return None if a is None else round(float(a) * 100, 4)


def boot_ci(vals, stat, nrep=NREP, seed=SEED, block=BLOCK, inflate=INFLATE, q=90):
    """block bootstrap on a 1-D daily series (skip NaN)."""
    v = np.asarray(vals, dtype=float)
    ok = ~np.isnan(v)
    v = v[ok]
    n = len(v)
    if n < block * 2:
        return None
    nb = int(np.ceil(n / block))
    idx = np.arange(n)
    rng = np.random.default_rng(seed)
    obs = stat(v)
    reps = np.empty(nrep)
    for r in range(nrep):
        starts = rng.integers(0, max(1, n - block + 1), size=nb)
        sel = np.concatenate([idx[s:s + block] for s in starts])[:n]
        reps[r] = stat(v[sel])
    lo, hi = np.percentile(reps, [(100 - q) / 2, 100 - (100 - q) / 2])
    half = (hi - lo) / 2.0 * inflate
    return {"mean": float(obs), "ci_lo": float(obs - half), "ci_hi": float(obs + half),
            "raw_lo": float(lo), "raw_hi": float(hi)}


def _blocks(n, block, rng, nb):
    starts = rng.integers(0, max(1, n - block + 1), size=nb)
    sel = np.concatenate([np.arange(s, s + block) for s in starts])
    return sel[sel < n]


def boot_group_diff(values, group, nrep=NREP, seed=SEED, block=BLOCK,
                    inflate=INFLATE, q=90):
    """block bootstrap (block ngay) cho hieu (mean trong nhom - mean ngoai nhom)."""
    v = np.asarray(values, dtype=float)
    g = np.asarray(group, dtype=bool)
    fin = ~np.isnan(v)
    iv, ov = v[fin & g], v[fin & ~g]
    if len(iv) < 10 or len(ov) < 10:
        return None
    obs = float(iv.mean() - ov.mean())
    n = len(v)
    nb = int(np.ceil(n / block))
    rng = np.random.default_rng(seed)
    reps = np.empty(nrep)
    for r in range(nrep):
        sel = _blocks(n, block, rng, nb)
        vv, gg = v[sel], g[sel]
        f = ~np.isnan(vv)
        a, b = vv[f & gg], vv[f & ~gg]
        reps[r] = (a.mean() - b.mean()) if (len(a) and len(b)) else np.nan
    reps = reps[~np.isnan(reps)]
    lo, hi = np.percentile(reps, [(100 - q) / 2, 100 - (100 - q) / 2])
    half = (hi - lo) / 2.0 * inflate
    return {"mean": obs, "ci_lo": obs - half, "ci_hi": obs + half,
            "raw_lo": float(lo), "raw_hi": float(hi),
            "excl0": bool(obs - half > 0 or obs + half < 0),
            "n_in": int(len(iv)), "n_out": int(len(ov))}


def boot_counts_diff(num1, den1, num2, den2, nrep=NREP, seed=SEED, block=BLOCK,
                     inflate=INFLATE, q=90):
    """block bootstrap cho hieu 2 ti le gop (pooled) tren cung truc ngay."""
    n = len(num1)
    nb = int(np.ceil(n / block))
    rng = np.random.default_rng(seed)
    obs = float(num1.sum() / den1.sum() - num2.sum() / den2.sum())
    reps = np.empty(nrep)
    for r in range(nrep):
        sel = _blocks(n, block, rng, nb)
        reps[r] = (num1[sel].sum() / den1[sel].sum() - num2[sel].sum() / den2[sel].sum())
    lo, hi = np.percentile(reps, [(100 - q) / 2, 100 - (100 - q) / 2])
    half = (hi - lo) / 2.0 * inflate
    return {"mean": obs, "ci_lo": obs - half, "ci_hi": obs + half,
            "raw_lo": float(lo), "raw_hi": float(hi),
            "excl0": bool(obs - half > 0 or obs + half < 0)}


def boot_counts(num, den, nrep=NREP, seed=SEED, block=BLOCK, inflate=INFLATE, q=90):
    """block bootstrap of ratio sum(num)/sum(den) with per-day counts."""
    num = np.asarray(num, float)
    den = np.asarray(den, float)
    n = len(num)
    nb = int(np.ceil(n / block))
    rng = np.random.default_rng(seed)
    obs = num.sum() / den.sum()
    reps = np.empty(nrep)
    for r in range(nrep):
        sel = _blocks(n, block, rng, nb)
        if len(sel) == 0:
            reps[r] = np.nan
            continue
        reps[r] = num[sel].sum() / den[sel].sum()
    lo, hi = np.percentile(reps, [(100 - q) / 2, 100 - (100 - q) / 2])
    half = (hi - lo) / 2.0 * inflate
    return {"mean": float(obs), "ci_lo": float(obs - half), "ci_hi": float(obs + half),
            "raw_lo": float(lo), "raw_hi": float(hi)}


def find_windows(b, thr=BR_THR, minlen=BR_LEN):
    """maximal runs of consecutive days with breadth >= thr, length >= minlen."""
    ok = (b >= thr).fillna(False)
    out = []
    run = []
    prev = None
    for d, v in ok.items():
        if v:
            if prev is None or (d - prev).days == 1:
                run.append(d)
            else:
                if len(run) >= minlen:
                    out.append((run[0], run[-1]))
                run = [d]
        else:
            if len(run) >= minlen:
                out.append((run[0], run[-1]))
            run = []
        prev = d
    if len(run) >= minlen:
        out.append((run[0], run[-1]))
    return out


# ---------------------------------------------------------------- main
def main():
    res = {}
    w = altdata.load_all()
    alt = [c for c in w.columns if c not in MAJORS]
    dev = w.loc[w.index <= DEV_END]
    L.info("matrix: %s  DEV %s..%s  cols=%d (alt=%d)",
           w.shape, w.index.min().date(), w.index.max().date(), w.shape[1], len(alt))
    res["coverage"] = {
        "matrix_shape": list(w.shape),
        "first": str(w.index.min().date()), "last": str(w.index.max().date()),
        "n_alt": len(alt), "n_majors_present": sum(1 for m in MAJORS if m in w.columns),
        "n_2026_days": int((w.index > DEV_END).sum()),
    }

    # ---- 1. drift dai han
    drift = {}
    for d in year_ends(dev.index):
        row = {}
        for h in HOR:
            d0 = d - pd.Timedelta(days=h)
            if d0 not in dev.index:
                continue
            r = (dev.loc[d] / dev.loc[d0] - 1.0)
            ra = r[[c for c in alt if c in r.index]].dropna()
            row["h%d" % h] = {"alt_n": int(ra.size), "alt_median": pct(ra.median()),
                              "alt_mean": pct(ra.mean()),
                              "pct_below_0": pct((ra < 0).mean()) if ra.size else None,
                              "btc": pct(r.get("BTC", np.nan))}
        drift[str(d.date())] = row
    res["drift"] = drift

    # ---- 2. pump/dump ngan han
    r1 = dev / dev.shift(1) - 1
    r7 = dev / dev.shift(7) - 1
    r30 = dev / dev.shift(30) - 1
    fwd30 = dev.shift(-30) / dev - 1
    from scipy import stats as sps
    short = {}
    for nm, rr in (("ret_1d", r1), ("ret_7d", r7), ("ret_30d", r30)):
        a = rr[alt].values.ravel()
        a = a[~np.isnan(a)]
        short[nm] = {"n": int(a.size), "median": pct(np.median(a)), "mean": pct(a.mean()),
                     "sd": pct(a.std(ddof=1)), "skew": round(float(sps.skew(a)), 4),
                     "excess_kurt": round(float(sps.kurtosis(a)), 4),
                     "p01": pct(np.percentile(a, 1)), "p05": pct(np.percentile(a, 5)),
                     "p95": pct(np.percentile(a, 95)), "p99": pct(np.percentile(a, 99))}
    # pump roi dump
    P = (r7[alt] >= 0.30) & fwd30[alt].notna()
    A = fwd30[alt].notna()
    nP = P.sum().sum()
    num = ((fwd30[alt] < 0) & P).sum(axis=1)          # per day
    den = P.sum(axis=1)
    numA = ((fwd30[alt] < 0) & A).sum(axis=1)
    denA = A.sum(axis=1)
    frac_pump = num.sum() / den.sum()
    baseline = numA.sum() / denA.sum()
    pd_ = num.values.astype(float)
    pa = den.values.astype(float)
    na_ = numA.values.astype(float)
    aa = denA.values.astype(float)
    ci = boot_counts_diff(pd_, pa, na_, aa)
    res["pumpdump"] = {"dist": short,
                       "pump_rule": {"n_pump_obs": int(nP), "frac_pump_neg_fwd30": pct(frac_pump),
                                     "baseline_neg_fwd30": pct(baseline),
                                     "diff_pp": pct(frac_pump - baseline),
                                     "diff_ci90_infl": None if ci is None else
                                     {"lo": pct(ci["ci_lo"]), "hi": pct(ci["ci_hi"]),
                                      "raw_lo": pct(ci["raw_lo"]), "raw_hi": pct(ci["raw_hi"]),
                                      "excl0": bool(ci["ci_lo"] > 0 or ci["ci_hi"] < 0)}}}

    # ---- 3/4. breadth + windows
    walt = w[alt]
    up = walt > walt.shift(30)
    mask = walt.notna() & walt.shift(30).notna()
    num = (up & mask).sum(axis=1)
    den = mask.sum(axis=1)
    b30 = (100.0 * num / den.replace(0, np.nan)).where(den >= BR_MIN_DEN)
    up1 = walt > walt.shift(1)
    m1 = walt.notna() & walt.shift(1).notna()
    b1 = (100.0 * (up1 & m1).sum(axis=1) / m1.sum(axis=1).replace(0, np.nan)).where(
        m1.sum(axis=1) >= BR_MIN_DEN)
    b30.to_csv(os.path.join(OUT, "alt_breadth30.csv"), header=["breadth30"])
    res["breadth_month"] = [
        {"month": str(k), "mean_breadth30": round(float(v), 2), "n_days": int(n)}
        for k, v, n in
        [(str(m), g.mean(), g.notna().sum()) for m, g in b30.groupby(b30.index.to_period("M"))]]

    wins = find_windows(b30.loc[b30.index <= DEV_END])
    wins_post = find_windows(b30.loc[b30.index > DEV_END])
    wrows = []
    for s, e in wins + wins_post:
        seg = b30.loc[s:e]
        wrows.append({"start": str(s.date()), "end": str(e.date()), "days": len(seg),
                      "breadth_mean": round(float(seg.mean()), 2),
                      "breadth_peak": round(float(seg.max()), 2),
                      "post_dev": bool(s > DEV_END)})
    pd.DataFrame(wrows).to_csv(os.path.join(OUT, "alt_windows.csv"), index=False)
    per_year = {}
    for y in range(2021, 2027):
        rr = [x for x in wrows if x["start"][:4] == str(y)]
        days = sum(x["days"] for x in rr)
        per_year[str(y)] = {"n_windows": len(rr), "days": days,
                            "pct_days_in_window": round(100.0 * days /
                                                        max(1, int((b30.index.year == y).sum())), 2),
                            "windows": rr}
    res["windows"] = {"def": "breadth30>=%.0f, run>=%d ngay" % (BR_THR, BR_LEN),
                      "per_year": per_year, "list": wrows}
    res["windows_sens"] = {t: {"thr": t, "minlen": ml,
                               "n_2021_2025": len(find_windows(b30.loc[b30.index <= DEV_END], t, ml))}
                           for t, ml in ((65, 5), (70, 3), (75, 5), (70, 5))}

    # ---- 5. dong pha BTC (corr30 / beta30)
    rr1 = r1[alt]
    btc = r1["BTC"]
    btc_np = btc.values
    dates = rr1.index
    corr_s = pd.Series(index=dates, dtype=float)
    beta_s = pd.Series(index=dates, dtype=float)
    X_all = rr1.values
    for i in range(30, len(dates)):
        win = X_all[i - 30:i, :]
        y = btc_np[i - 30:i]
        fin = np.isfinite(win)
        X0 = np.where(fin, win, 0.0)
        n_jk = fin.astype(float).T @ fin.astype(float)
        sxx = X0.T @ X0
        sx = X0.sum(axis=0)
        ok_c = np.diag(n_jk) >= CORR_MIN_N
        if ok_c.sum() >= CORR_MIN_ALT:
            idx = np.where(ok_c)[0]
            n2 = n_jk[np.ix_(idx, idx)]
            m = sxx[np.ix_(idx, idx)] / n2 - np.outer(sx[idx], sx[idx]) / (n2 * n2)
            d = np.sqrt(np.diag(m))
            c = m / np.outer(d, d)
            iu = np.triu_indices(len(idx), 1)
            good = n2[iu] >= CORR_MIN_N
            if good.sum() > 0:
                corr_s.iloc[i] = np.nanmean(c[iu][good])
        # beta
        yv = np.isfinite(y)
        if yv.sum() >= CORR_MIN_N:
            y0 = np.where(yv, y, 0.0)
            nj = (fin & yv[:, None]).sum(axis=0)
            sxy = (X0 * y0[:, None]).sum(axis=0)
            sy = y0.sum()
            syy = (y0 * y0).sum()
            sel = nj >= CORR_MIN_N
            if sel.sum() > 0:
                mx = np.where(nj > 0, sx / nj, np.nan)
                my = sy / yv.sum()
                cov = sxy / np.where(nj > 0, nj, np.nan) - mx * my
                var = syy / yv.sum() - my * my
                b = cov / var
                beta_s.iloc[i] = np.nanmean(b[sel])
    inwin = pd.Series(False, index=dates)
    for s, e in wins:
        inwin.loc[s:e] = True
    devrows = dates <= DEV_END
    ins = inwin & devrows
    outs = (~inwin) & devrows & corr_s.notna()
    c_in, c_out = corr_s[ins].dropna(), corr_s[outs].dropna()
    b_in, b_out = beta_s[ins].dropna(), beta_s[outs].dropna()

    def diff_ci(a, bb):
        return None

    ci_c = boot_group_diff(corr_s.values, (ins & corr_s.notna()).values)
    ci_b = boot_group_diff(beta_s.values, (ins & beta_s.notna()).values)
    res["comove"] = {
        "corr30_in": None if not len(c_in) else round(float(c_in.mean()), 4),
        "corr30_out": None if not len(c_out) else round(float(c_out.mean()), 4),
        "corr30_diff_ci90": None if ci_c is None else
        {"lo": round(ci_c["ci_lo"], 4), "hi": round(ci_c["ci_hi"], 4),
         "n_in": ci_c["n_in"], "n_out": ci_c["n_out"],
         "excl0": bool(ci_c["ci_lo"] > 0 or ci_c["ci_hi"] < 0)},
        "beta30_in": None if not len(b_in) else round(float(b_in.mean()), 4),
        "beta30_out": None if not len(b_out) else round(float(b_out.mean()), 4),
        "beta30_diff_ci90": None if ci_b is None else
        {"lo": round(ci_b["ci_lo"], 4), "hi": round(ci_b["ci_hi"], 4),
         "n_in": ci_b["n_in"], "n_out": ci_b["n_out"],
         "excl0": bool(ci_b["ci_lo"] > 0 or ci_b["ci_hi"] < 0)},
        "n_in": int(len(c_in)), "n_out": int(len(c_out))}
    pd.DataFrame({"corr30": corr_s, "beta30": beta_s, "in_window": inwin}).to_csv(
        os.path.join(OUT, "alt_comove.csv"))

    # ---- 6. vi du cu the
    ex = {}
    for nm, s, e in (("2025-07..08", "2025-07-01", "2025-08-31"),
                     ("2026-08..09", "2026-08-01", "2026-09-22"),
                     ("2026-09", "2026-09-01", "2026-09-22")):
        seg = b30.loc[s:e]
        ov = [(str(a.date()), str(b.date())) for a, b in wins + wins_post
              if not (b < pd.Timestamp(s) or a > pd.Timestamp(e))]
        br = w.loc[s:e, "BTC"]
        ex[nm] = {"mean_breadth30": round(float(seg.mean()), 2),
                  "max_breadth30": round(float(seg.max()), 2),
                  "days_over_70": int((seg >= 70).sum()), "n_days": int(seg.notna().sum()),
                  "windows_overlap": ov,
                  "btc_ret_pct": pct(br.iloc[-1] / br.iloc[0] - 1) if len(br) > 1 else None,
                  "alt_median_ret_pct": pct((w.loc[e, [c for c in alt if c in w.columns]] /
                                             w.loc[s, [c for c in alt if c in w.columns]] - 1
                                             ).median())}
    res["examples"] = ex

    # ---- 7. T170 theo thang (mo ta)
    t170 = {}
    if os.path.exists(T170):
        d = pd.read_csv(T170)
        d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce")
        d = d.dropna(subset=["ts"])
        d["ym"] = d["ts"].dt.to_period("M").astype(str)
        g = d.groupby("ym")["pnl"].agg(["sum", "count"])
        win_months = set()
        for x in wins:
            for m in pd.period_range(x[0], x[1], freq="M"):
                win_months.add(str(m))
        t170 = {"book": T170, "n_trades": int(len(d)),
                "months": [{"ym": k, "pnl": round(float(v["sum"]), 2), "n": int(v["count"]),
                            "in_window": k in win_months} for k, v in g.iterrows()],
                "pnl_in_window_months": round(float(
                    g.loc[[k for k in g.index if k in win_months], "sum"].sum()), 2),
                "pnl_other_months": round(float(
                    g.loc[[k for k in g.index if k not in win_months], "sum"].sum()), 2),
                "n_month_in_window": len([k for k in g.index if k in win_months])}
    res["t170"] = t170

    # ---- verdict
    dr = res["drift"]
    a1 = sum(1 for y in dr if dr[y].get("h365", {}).get("alt_median") is not None
             and dr[y]["h365"]["alt_median"] < 0)
    a1_ok = a1 >= 3
    a2_ok = all(short[h]["excess_kurt"] > 0 for h in ("ret_1d", "ret_7d", "ret_30d"))
    pr = res["pumpdump"]["pump_rule"]
    a3_ok = bool(pr["diff_pp"] is not None and pr["diff_pp"] > 0 and
                 pr["diff_ci90_infl"] and pr["diff_ci90_infl"]["excl0"])
    b1_ok = all(per_year[str(y)]["n_windows"] >= 1 for y in range(2021, 2026))
    yrs = [per_year[str(y)]["n_windows"] for y in range(2021, 2026)]
    b2_ok = 1.0 <= float(np.mean(yrs)) <= 3.0
    b3_ok = bool(res["comove"]["corr30_diff_ci90"] and res["comove"]["corr30_diff_ci90"]["excl0"]
                 and res["comove"]["corr30_in"] > res["comove"]["corr30_out"]
                 and res["comove"]["beta30_diff_ci90"] and res["comove"]["beta30_diff_ci90"]["excl0"]
                 and res["comove"]["beta30_in"] > res["comove"]["beta30_out"])
    A = a1_ok and a2_ok and a3_ok
    B = b1_ok and b2_ok and b3_ok
    verdict = "DUNG" if (A and B) else ("SAI" if (not A and not b1_ok) else "DUNG MOT PHAN")
    res["verdict"] = {"A1_median365_neg_ge3of5": {"pass": a1_ok, "n_years_neg": a1},
                      "A2_fat_tails": {"pass": a2_ok},
                      "A3_pump_then_dump": {"pass": a3_ok, "diff_pp": pr["diff_pp"]},
                      "B1_at_least_1_window_per_year": {"pass": b1_ok},
                      "B2_1_to_3_windows_per_year": {"pass": b2_ok, "mean": float(np.mean(yrs)),
                                                     "per_year": yrs},
                      "B3_comove_higher_in_window": {"pass": b3_ok},
                      "A": A, "B": B, "verdict": verdict}

    with open(os.path.join(OUT, "alt_regime_waves.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    L.info("VERDICT: %s", verdict)
    L.info("A1=%s(%d) A2=%s A3=%s | B1=%s B2=%s B3=%s", a1_ok, a1, a2_ok, a3_ok, b1_ok, b2_ok, b3_ok)
    L.info("windows/year(2021-25)=%s ; corr in/out=%s/%s ; beta in/out=%s/%s",
           yrs, res["comove"]["corr30_in"], res["comove"]["corr30_out"],
           res["comove"]["beta30_in"], res["comove"]["beta30_out"])


if __name__ == "__main__":
    main()
