#!/usr/bin/env python3
"""tail50_ruler_redundancy.py — PREREG_TAIL50_RULER_REDUNDANCY (commit deb5b0c).

VIEC 1: rao (b') BO TOP-{5,10,20,30,40,50}% (toan ky + tung nam) + median/leg + duong cong q* + rao (a).
VIEC 2: ma tran Pearson+Spearman giua 15/17 thau tail-robust tren cac RUN DEV (khoi A) va o run x nam
        (khoi B); liet ke cap |rho|>=0,9 / >=0,99; kiem dong nhat thuc affine.

THUAN PYTHON OFFLINE tren printDone.csv DA CO. KHONG train/sim/Java, khong cham 242/ONNX/LIVE, khong push.
DEV only <= 2025-12-31. Output NHO.

  python3 tail50_ruler_redundancy.py [--json docs/result/TAIL50_RULER_REDUNDANCY.json]
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

KOUT = "/home/ubuntu/kaggle_sim/out"
DEVRUN = "/home/ubuntu/java/devrun"
DEV_END = pd.Timestamp("2025-12-31 23:59")
NMIN = 30
NMIN_Y = 30
TMP = "/tmp/t50"
NEED = ("sym", "status", "profit", "pnl", "margin", "start", "end")

TARGETS = [
    ("KEEPLEG0", "gr-par-kg0"), ("T100", "hn-t100"), ("GD92", "hn-g92"),
    ("kg0-q995", "gr-kg0-q995"), ("kg0-q998", "gr-kg0-q998"), ("kg0-q999", "gr-kg0-q999"),
    ("T170", "t170-x1-2021"), ("kg0-q998-15m", "gr-kg0-q998-15m"),
]
OPT = ["sel15", "sel15-q998", "sel15-q999", "all15"]

# 17 thau (prereg goc §5) — 15 tinh duoc tren run, 2 IC loai (khong co diem doi tuong)
RULERS = ["wmean_p1p99", "wmean_p5p95", "tmean_1", "tmean_5", "median", "sign_frac",
          "tf_1", "tf_5", "tf_10", "conc_1", "conc_5", "hhi_gain", "loss_mean",
          "wl_ratio", "max_loss"]
RULERS_NA = ["ic_wmean", "ic_med"]
PRIORITY = ["median", "tf_5", "wmean_p1p99", "sign_frac", "conc_5", "loss_mean"]


def load(path):
    p = os.path.join(path, "storage", "printDone.csv")
    if not os.path.exists(p):
        return None
    try:
        d = pd.read_csv(p, usecols=lambda c: c.strip() in NEED, on_bad_lines="skip")
    except Exception:
        return None
    d.columns = [c.strip() for c in d.columns]
    if any(c not in d.columns for c in NEED):
        return None
    for c in ("profit", "pnl", "margin"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d["start"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    d["te"] = pd.to_datetime(d["end"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["ts", "profit", "pnl", "margin"]).copy()
    d = d[d.ts <= DEV_END].copy()
    return d


# ─────────────────────── VIEC 1: rao (a)/(b') ───────────────────────
def tf_curve(P):
    """P: mang pnl. Tra TF tai cac buoc x% + share top-1% + median + q* + duong cong."""
    n = len(P)
    tot = float(P.sum())
    o = np.sort(P)[::-1]

    def tf(x):
        k = max(1, int(math.ceil(x / 100.0 * n)))
        return dict(k=k, tail_sum=float(o[k:].sum()), dropped=float(o[:k].sum()))

    k1 = max(1, int(math.ceil(0.01 * n)))
    out = dict(n=n, sum_pnl=tot,
               share_top1_pct=float(o[:k1].sum() / tot * 100) if tot else float("nan"),
               median_leg=float(np.median(P)), sign_frac_pos=float((P > 0).mean() * 100))
    for x in (5, 10, 20, 30, 40, 50):
        out["tf%d" % x] = tf(x)
    out["pass_a"] = bool(out["share_top1_pct"] <= 15.0)
    for x in (30, 40, 50):
        out["pass_b%d" % x] = bool(out["tf%d" % x]["tail_sum"] > 0)
    # dong nhat thuc: TF(50%) == tong nua duoi (n - k leg nho nhat)
    kk = max(1, int(math.ceil(0.50 * n)))
    half = float(o[kk:].sum())
    out["bottom_half_sum"] = half
    out["tf50_eq_bottom_half"] = bool(abs(out["tf50"]["tail_sum"] - half) < 1e-6)
    # duong cong PnL(x)
    curve = {}
    for x in (0, 5, 10, 20, 30, 40, 50):
        curve["%d" % x] = float(tf(x)["tail_sum"]) if x > 0 else tot
    out["curve"] = curve
    # q* = buoc 0,5% nho nhat lam TF<=0
    qs = None
    for q in np.arange(0.005, 0.9555, 0.005):
        if o[max(1, int(math.ceil(q * n))):].sum() <= 0:
            qs = float(round(q * 100, 2))
            break
    out["q_breakeven_pct"] = qs
    return out


def rao_block(d):
    r = tf_curve(d["pnl"].to_numpy(float))
    y = {}
    dd = d.copy()
    dd["yr"] = dd["te"].dt.year
    for yr, g in dd.groupby("yr"):
        if len(g) < 5:
            y[int(yr)] = dict(n=len(g), insufficient=True)
            continue
        P = g["pnl"].to_numpy(float)
        n = len(P)
        o = np.sort(P)[::-1]

        def tf(x):
            k = max(1, int(math.ceil(x / 100.0 * n)))
            return float(o[k:].sum())

        y[int(yr)] = dict(n=n, sum_pnl=float(P.sum()), median_leg=float(np.median(P)),
                          tf10=tf(10), tf20=tf(20), tf30=tf(30), tf40=tf(40), tf50=tf(50),
                          pass_b30=bool(tf(30) > 0), pass_b40=bool(tf(40) > 0),
                          pass_b50=bool(tf(50) > 0))
    r["years"] = y
    return r


# ─────────────────────── VIEC 2: 15 thau tren run ───────────────────────
def rulers_of(net):
    """net: mang pnl/leg. 15 thau tail-robust (prereg goc §5)."""
    x = np.asarray(net, np.float64)
    n = len(x)
    if n == 0:
        return {k: float("nan") for k in RULERS}
    o = np.sort(x)[::-1]          # giam dan
    a = np.sort(x)                # tang dan
    q = np.percentile(x, [1, 5, 25, 75, 90, 95, 99])
    r = {}
    r["wmean_p1p99"] = float(np.clip(x, q[0], q[6]).mean())
    r["wmean_p5p95"] = float(np.clip(x, q[1], q[5]).mean())
    # trimmed mean bo 1%/5% moi duoi
    for pct, nm in ((1, "tmean_1"), (5, "tmean_5")):
        k = int(math.ceil(pct / 100.0 * n))
        keep = a[k:n - k] if n - 2 * k > 0 else a
        r[nm] = float(keep.mean())
    r["median"] = float(np.median(x))
    r["sign_frac"] = float((x > 0).mean())
    for pct, nm in ((1, "tf_1"), (5, "tf_5"), (10, "tf_10")):
        k = max(1, int(math.ceil(pct / 100.0 * n)))
        r[nm] = float(o[k:].mean()) if n - k > 0 else float("nan")
    tot = float(x.sum())
    for pct, nm in ((1, "conc_1"), (5, "conc_5")):
        k = max(1, int(math.ceil(pct / 100.0 * n)))
        r[nm] = float(o[:k].sum() / tot) if tot else float("nan")
    g = np.maximum(x, 0.0)
    G = float(g.sum())
    r["hhi_gain"] = float((g * g).sum() / (G * G)) if G else float("nan")
    lo = x[x < 0]
    r["loss_mean"] = float(-lo.mean()) if len(lo) else float("nan")   # do lon TB leg lo (>=0)
    win = x[x > 0]
    r["wl_ratio"] = (float(win.mean()) / float(-lo.mean())) if (len(win) and len(lo)) else float("nan")
    r["max_loss"] = float(-o[-1]) if n else float("nan")              # lo lon nhat (>=0)
    return r


RATES4 = ["tsloss", "mp_sm", "mp_sl", "margin"]
RATE_LBL = {"tsloss": "TSloss%", "mp_sm": "mP|SM", "mp_sl": "mP|SL", "margin": "mMargin",
            "win": "win%", "meanP": "meanP"}


def rates_of_run(d):
    """4 rate bo chuan da chot (vong rate) + win%/meanP de doi chieu."""
    sm = d.status == "STOP_MARKET_DONE"
    sl = d.status == "STOP_LOSS_DONE"
    n = len(d)
    return dict(tsloss=100.0 * sl.mean(),
                mp_sm=float(d.loc[sm, "profit"].mean()) if sm.any() else float("nan"),
                mp_sl=float(d.loc[sl, "profit"].mean()) if sl.any() else float("nan"),
                margin=float(d.margin.mean()),
                win=100.0 * (d.profit > 0).mean(),
                meanP=float(d.profit.mean()))


def cross_family(A, B, tailcols, out):
    """Do trung lap CHEO: rate chuan {TSloss%,mP|SM,mP|SL,mMargin} vs thau tail-robust (2 khoi)."""
    rows = []
    for v in tailcols:
        for r in RATES4 + ["win"]:
            a = A[[r, v]].apply(pd.to_numeric, errors="coerce").dropna()
            b = B[[r, v]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(a) < 6 or len(b) < 6:
                continue
            pa, sa = float(a.corr(method="pearson").iloc[0, 1]), float(a.corr(method="spearman").iloc[0, 1])
            pb, sb = float(b.corr(method="pearson").iloc[0, 1]), float(b.corr(method="spearman").iloc[0, 1])
            rows.append(dict(tail=v, rate=RATE_LBL.get(r, r), P_A=round(pa, 4), S_A=round(sa, 4),
                             P_B=round(pb, 4), S_B=round(sb, 4),
                             both_blocks=bool(abs(pa) >= .9 and abs(sa) >= .9 and abs(pb) >= .9 and abs(sb) >= .9),
                             near=bool(min(abs(sa), abs(sb)) >= .85 and max(abs(pa), abs(pb)) >= .9)))
    out["cross_family"] = rows
    return rows


def corr_block(rows, label, out):
    cols = [c for c in RULERS if rows[c].notna().sum() >= max(6, int(0.5 * len(rows))) and rows[c].std() > 0]
    X = rows[cols]
    pe = X.corr(method="pearson"); sp = X.corr(method="spearman")
    n = len(X)
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            u, v = cols[i], cols[j]
            piv, spv = float(pe.loc[u, v]), float(sp.loc[u, v])
            pairs.append(dict(a=u, b=v, pearson=round(piv, 4), spearman=round(spv, 4), n=n,
                              ge90=bool(abs(piv) >= 0.9 and abs(spv) >= 0.9),
                              ge99=bool(abs(piv) >= 0.99 and abs(spv) >= 0.99)))
    out[label] = dict(n_obs=n, cols=cols, pairs=pairs,
                      pearson=np.round(pe.values, 4).tolist(),
                      spearman=np.round(sp.values, 4).tolist())
    return pe, sp


def affine_pairs(rows, cols):
    """Cap co quan he affine gan tuyet doi: ||u-(a v+b)|| / ||u-mean(u)|| <= 1e-6."""
    res = []
    for i in range(len(cols)):
        for j in range(len(cols)):
            if i == j:
                continue
            u = rows[cols[i]].to_numpy(float); v = rows[cols[j]].to_numpy(float)
            m = np.isfinite(u) & np.isfinite(v)
            if m.sum() < 6:
                continue
            uu, vv = u[m], v[m]
            A = np.vstack([vv, np.ones_like(vv)]).T
            coef, *_ = np.linalg.lstsq(A, uu, rcond=None)
            pred = A @ coef
            den = np.linalg.norm(uu - uu.mean())
            rel = float(np.linalg.norm(uu - pred) / den) if den > 0 else float("inf")
            if rel <= 1e-6:
                res.append(dict(u=cols[i], v=cols[j], a=float(coef[0]), b=float(coef[1]),
                                rel_resid=round(rel, 12)))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/result/TAIL50_RULER_REDUNDANCY.json")
    a = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)

    # ---- gom run DEV
    runs = {}
    skipped = dict(no_csv=0, bad_cols=0, too_small=0)
    for root in (KOUT, DEVRUN):
        if not os.path.isdir(root):
            continue
        for tag in sorted(os.listdir(root)):
            p = os.path.join(root, tag)
            if not os.path.isdir(p):
                continue
            d = load(p)
            if d is None:
                skipped["no_csv"] += 1
                continue
            if len(d) < NMIN:
                skipped["too_small"] += 1
                continue
            runs[tag] = dict(path=p, d=d)
    print("runs eligible:", len(runs), skipped, file=sys.stderr)

    # ---- VIEC 2: khoi A / B
    rowsA = []
    rowsB = []
    for t, v in runs.items():
        d = v["d"]
        nm = d["pnl"].to_numpy(float) / np.where(d["margin"].to_numpy(float) == 0, np.nan,
                                                 d["margin"].to_numpy(float))
        r = rulers_of(nm)
        r.update(rates_of_run(d))
        r["tag"] = t
        rowsA.append(r)
        d2 = d.copy(); d2["yr"] = d2["te"].dt.year
        for yr, g in d2.groupby("yr"):
            if len(g) < NMIN_Y:
                continue
            nmy = g["pnl"].to_numpy(float) / np.where(g["margin"].to_numpy(float) == 0, np.nan,
                                                      g["margin"].to_numpy(float))
            rr = rulers_of(nmy); rr.update(rates_of_run(g))
            rr["tag"] = t; rr["yr"] = int(yr)
            rowsB.append(rr)
    A = pd.DataFrame(rowsA)
    B = pd.DataFrame(rowsB)
    A.to_csv(os.path.join(TMP, "panelA.csv"), index=False)
    B.to_csv(os.path.join(TMP, "panelB.csv"), index=False)
    print("panelA", len(A), "panelB", len(B), file=sys.stderr)

    out = dict(prereg="docs/prereg/PREREG_TAIL50_RULER_REDUNDANCY.md",
               n_runs=len(runs), skipped=skipped, n_panelB=len(B),
               rulers_used=RULERS, rulers_na=RULERS_NA, priority=PRIORITY,
               net_decl="pnl/margin (lai suat tren ky quy/leg)")

    corr = {}
    corr_block(A, "A_runs", corr)
    corr_block(B, "B_run_year", corr)
    out["corr"] = dict(meta={k: dict(n_obs=v["n_obs"], cols=v["cols"]) for k, v in corr.items()},
                       A_pearson=corr["A_runs"]["pearson"], A_spearman=corr["A_runs"]["spearman"],
                       B_pearson=corr["B_run_year"]["pearson"], B_spearman=corr["B_run_year"]["spearman"])
    pm = {p["a"] + "|" + p["b"]: p for p in corr["A_runs"]["pairs"]}
    bm = {(p["a"], p["b"]): p for p in corr["B_run_year"]["pairs"]}
    both90, both99 = [], []
    for key, p in pm.items():
        q = bm.get((p["a"], p["b"]))
        if q is None:
            continue
        if p["ge90"] and q["ge90"]:
            both90.append(dict(a=p["a"], b=p["b"], P_A=p["pearson"], S_A=p["spearman"],
                               P_B=q["pearson"], S_B=q["spearman"]))
        if p["ge99"] and q["ge99"]:
            both99.append(dict(a=p["a"], b=p["b"], P_A=p["pearson"], S_A=p["spearman"],
                               P_B=q["pearson"], S_B=q["spearman"]))
    out["pairs_ge90_both_blocks"] = sorted(both90, key=lambda z: -abs(z["P_A"]))
    out["pairs_ge99_both_blocks"] = sorted(both99, key=lambda z: -abs(z["P_A"]))
    out["pairs_ge90_blockA_only"] = sorted(
        [dict(a=p["a"], b=p["b"], P=p["pearson"], S=p["spearman"]) for p in corr["A_runs"]["pairs"] if p["ge90"]],
        key=lambda z: -abs(z["P"]))
    # top cap tuong quan (theo |P_A|)
    out["top_pairs_blockA"] = sorted(
        [dict(a=p["a"], b=p["b"], P=p["pearson"], S=p["spearman"],
              P_B=bm.get((p["a"], p["b"]), {}).get("pearson"),
              S_B=bm.get((p["a"], p["b"]), {}).get("spearman"))
         for p in corr["A_runs"]["pairs"]], key=lambda z: -abs(z["P"]))[:18]
    out["affine_blockA"] = affine_pairs(A, corr["A_runs"]["cols"])
    # ---- VIEC 2b: TRUNG LAP CHEO voi bo rate da chot {TSloss%, mP|SM, mP|SL, mMargin}
    tailcols_all = [c for c in RULERS if c in A]
    out["cross_family_ge90"] = [p for p in cross_family(A, B, tailcols_all, out)
                                if p["both_blocks"]]
    # ---- VIEC 2c: BO CHUAN TAIL-ROBUST TOI THIEU (luat B1-B4, chot truoc)
    cross_bad = sorted(set(p["tail"] for p in out["cross_family"]
                           if p["both_blocks"] or p["near"]))
    ASPECTS = [
        ("vi_tri", ["median", "tf_5", "wmean_p1p99", "wmean_p5p95", "tmean_1", "tmean_5", "tf_1", "tf_10"]),
        ("tan_suat_thang", ["sign_frac"]),
        ("do_lon_thua", ["loss_mean", "wl_ratio", "max_loss"]),
        ("tap_trung", ["conc_5", "conc_1", "hhi_gain"]),
    ]

    def redundant(c, u):
        a = A[[c, u]].apply(pd.to_numeric, errors="coerce").dropna()
        b = B[[c, u]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(a) < 6 or len(b) < 6:
            return True, None
        pa, sa = (float(a.corr(method="pearson").iloc[0, 1]), float(a.corr(method="spearman").iloc[0, 1]))
        pb, sb = (float(b.corr(method="pearson").iloc[0, 1]), float(b.corr(method="spearman").iloc[0, 1]))
        red = bool(abs(pa) >= .9 and abs(sa) >= .9 and abs(pb) >= .9 and abs(sb) >= .9)
        return red, dict(a=u, P_A=round(pa, 3), S_A=round(sa, 3), P_B=round(pb, 3), S_B=round(sb, 3))

    chosen, skipped, by_aspect = [], {}, {}
    for asp, cands in ASPECTS:
        pick = None
        for c in cands:
            if c not in tailcols_all:
                continue
            if c in cross_bad:
                skipped.setdefault(asp, []).append(dict(ruler=c, ly_do="trung CHEO voi bo rate da chot"))
                continue
            blk = None
            bad = False
            for u in chosen:
                red, info = redundant(c, u)
                if red:
                    bad = True; blk = info; break
            if bad:
                skipped.setdefault(asp, []).append(dict(ruler=c, ly_do="trung TRONG ho tail", blk=blk))
                continue
            pick = c; break
        by_aspect[asp] = pick
        if pick:
            chosen.append(pick)
    out["recommend"] = dict(
        set=chosen, by_aspect=by_aspect, skipped=skipped, cross_bad=cross_bad,
        pairwise={c + "|" + u: dict(P_A=round(float(A[[c, u]].dropna().corr(method="pearson").iloc[0, 1]), 3),
                                   S_A=round(float(A[[c, u]].dropna().corr(method="spearman").iloc[0, 1]), 3),
                                   P_B=round(float(B[[c, u]].dropna().corr(method="pearson").iloc[0, 1]), 3),
                                   S_B=round(float(B[[c, u]].dropna().corr(method="spearman").iloc[0, 1]), 3))
                   for i, c in enumerate(chosen) for u in chosen[i + 1:]},
        alt_extra=["tf_5", "max_loss"])
    summ = {}
    for c in RULERS:
        if c in A:
            summ[c] = dict(mean=round(float(A[c].mean()), 5), std=round(float(A[c].std()), 5),
                           min=round(float(A[c].min()), 5), max=round(float(A[c].max()), 5),
                           nan=int(A[c].isna().sum()))
    out["summary_blockA"] = summ

    # ---- VIEC 1: rao (a)/(b')
    rut = {}
    for name, sub in TARGETS:
        d = None
        for t, v in runs.items():
            if os.path.basename(v["path"]) == sub or t == sub:
                d = v["d"]; break
        if d is None:
            rut[name] = dict(missing=True, dir=sub)
            continue
        rut[name] = rao_block(d)
    opt = {}
    for nm in OPT:
        hit = next(((t, v) for t, v in runs.items() if nm in t), None)
        if hit:
            opt[nm] = dict(tag=hit[0], **rao_block(hit[1]["d"]))
        else:
            opt[nm] = dict(missing=True)
    out["rao"] = rut
    out["rao_optional"] = opt
    out["rao_summary"] = {k: dict(
        n=v.get("n"), pass_a=v.get("pass_a"), share_top1=round(v.get("share_top1_pct", float("nan")), 2),
        tf30=round(v.get("tf30", {}).get("tail_sum", float("nan")), 1),
        tf40=round(v.get("tf40", {}).get("tail_sum", float("nan")), 1),
        tf50=round(v.get("tf50", {}).get("tail_sum", float("nan")), 1),
        pass_b30=v.get("pass_b30"), pass_b40=v.get("pass_b40"), pass_b50=v.get("pass_b50"),
        median=v.get("median_leg"), q_star=v.get("q_breakeven_pct"),
        half_eq=v.get("tf50_eq_bottom_half")) for k, v in rut.items() if not v.get("missing")}
    out["rao_summary"] = {k: v for k, v in out["rao_summary"].items()}
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", a.json, os.path.getsize(a.json), "bytes", file=sys.stderr)


if __name__ == "__main__":
    main()
