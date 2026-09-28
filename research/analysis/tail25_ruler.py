#!/usr/bin/env python3
"""tail25_ruler.py — PREREG_TAIL25 (docs/prereg/PREREG_TAIL25.md).

VIEC 1: rao (b') BO TOP-{0,5,10,15,20,25,30}% (toan ky + tung nam) + CI muc 25% (block-72h, 2000 rep,
        seed 20260905, inflate(k=8)) + q* + rao (a) %PnL top-1%.
VIEC 2: bang tong hop PASS/FAIL (a)+(b') 8 bien the. Sanity: TF20/TF30 phai khop '76cc051'.

THUAN PYTHON OFFLINE tren printDone.csv DA CO (dung nguyen artifact 76cc051). KHONG train/sim/Java.
DEV only <= 2025-12-31. Output NHO.

  python3 tail25_ruler.py [--json docs/result/TAIL25_RULER.json]
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
NEED = ("sym", "status", "profit", "pnl", "margin", "start", "end")
LEVELS = [0, 5, 10, 15, 20, 25, 30]
H = 3600000          # 1h (ms)
BLOCK_H = 72         # 72h
NREPS = 2000
SEED = 20260905
K_INFL = 8           # 8 bien the trong vong nay -> inflate(8)
PRIOR_JSON = "docs/result/TAIL50_RULER_REDUNDANCY.json"   # artifact 76cc051

# thu tu theo yeu cau owner
TARGETS = [
    ("KEEPLEG0", "gr-par-kg0"), ("T170", "t170-x1-2021"), ("T100", "hn-t100"), ("GD92", "hn-g92"),
    ("kg0-q995", "gr-kg0-q995"), ("kg0-q998", "gr-kg0-q998"), ("kg0-q999", "gr-kg0-q999"),
    ("kg0-q998-15m", "gr-kg0-q998-15m"),
]
TMP = "/tmp/t25"


def inflate(k):
    k = int(k)
    if k < 1:
        raise ValueError(k)
    return 1.0 if k == 1 else float(math.sqrt(2.0 * math.log(k)))


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
    return d[d.ts <= DEV_END].copy()


def tf_at(P, x):
    """TF(x%): sum after dropping top-k legs (k = max(1, ceil(x*n/100)))."""
    n = len(P)
    if x <= 0:
        return float(P.sum())
    o = np.sort(P)[::-1]
    k = max(1, int(math.ceil(x / 100.0 * n)))
    return float(o[k:].sum())


def levels_block(P):
    out = {}
    for x in LEVELS:
        v = tf_at(P, x)
        out[str(x)] = dict(sum=float(v), sign=int(np.sign(v)))
    return out


def share_top1(P):
    n = len(P)
    if n == 0 or P.sum() == 0:
        return float("nan")
    o = np.sort(P)[::-1]
    k = max(1, int(math.ceil(0.01 * n)))
    return float(o[:k].sum() / P.sum() * 100.0)


def q_star(P):
    o = np.sort(P)[::-1]
    n = len(P)
    for q in np.arange(0.005, 0.9555, 0.005):
        if o[max(1, int(math.ceil(q * n))):].sum() <= 0:
            return float(round(q * 100, 2))
    return None


def ci_tf25(P, ts):
    """CI cho TF(25%) bang bootstrap khoi 72h, 2000 rep, seed 20260905."""
    n = len(P)
    inv = np.unique(ts // (BLOCK_H * H), return_inverse=True)[1]
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(SEED).integers(0, nb, (NREPS, nb))
    point = tf_at(P, 25)
    oidx = np.arange(n)
    reps = np.empty(NREPS)
    for r in range(NREPS):
        cnt = np.bincount(BI[r], minlength=nb)
        vals = P[np.repeat(oidx, cnt[inv])]
        m = len(vals)
        k = max(1, int(math.ceil(0.25 * m)))
        reps[r] = np.sort(vals)[::-1][k:].sum()
    lo, hi = float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))
    infl = inflate(K_INFL)
    ilo, ihi = point - (point - lo) * infl, point + (hi - point) * infl
    out_r = bool(lo > 0 or hi < 0)
    out_i = bool(ilo > 0 or ihi < 0)
    return dict(point=float(point), raw95=[lo, hi], infl=[ilo, ihi], inflate=infl,
                out_raw=out_r, out_infl=out_i, out=bool(out_r and out_i),
                ci_lower_gt0=bool(lo > 0), rep_median=float(np.median(reps)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="docs/result/TAIL25_RULER.json")
    a = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)

    runs = {}
    for root in (KOUT, DEVRUN):
        if not os.path.isdir(root):
            continue
        for tag in sorted(os.listdir(root)):
            p = os.path.join(root, tag)
            if os.path.isdir(p):
                runs[tag] = p

    prior = {}
    if os.path.exists(PRIOR_JSON):
        pj = json.load(open(PRIOR_JSON))
        prior = pj.get("rao", {})

    out = dict(prereg="docs/prereg/PREREG_TAIL25.md", levels=LEVELS, block_h=BLOCK_H,
               nreps=NREPS, seed=SEED, k_infl=K_INFL, inflate=inflate(K_INFL),
               rules=dict(pass_a_le=15.0, pass_b25="TF(25%)>0",
                          ci_out="ngoai raw95 VA ngoai inflate(8)"),
               targets={}, sanity={}, table=[])
    missing = []
    for name, sub in TARGETS:
        path = runs.get(sub)
        d = load(path) if path else None
        if d is None or len(d) < 30:
            missing.append(name)
            out["targets"][name] = dict(missing=True, dir=sub)
            continue
        P = d["pnl"].to_numpy(float)
        ts = d["ts"].to_numpy("int64")
        blk = levels_block(P)
        years = {}
        dd = d.copy()
        dd["yr"] = dd["te"].dt.year
        for yr, g in dd.groupby("yr"):
            Py = g["pnl"].to_numpy(float)
            n = len(Py)
            if n < 5:
                years[int(yr)] = dict(n=int(n), insufficient=True)
                continue
            yb = {}
            for x in LEVELS:
                v = tf_at(Py, x)
                yb[str(x)] = dict(sum=float(v), sign=int(np.sign(v)))
            years[int(yr)] = dict(n=int(n), levels=yb)
        ci = ci_tf25(P, ts)
        sa = share_top1(P)
        qs = q_star(P)
        pass_b25 = bool(blk["25"]["sum"] > 0)
        pass_a = bool(np.isfinite(sa) and sa <= 15.0)
        rec = dict(name=name, dir=sub, n=int(len(P)), sum_pnl=float(P.sum()),
                   levels=blk, years=years, share_top1_pct=round(sa, 2),
                   pass_a=pass_a, ci25=ci, q_star=qs, pass_b25=pass_b25,
                   median_leg=float(np.median(P)))
        out["targets"][name] = rec
        # sanity vs 76cc051
        pr = prior.get({"KEEPLEG0": "KEEPLEG0", "T170": "T170", "T100": "T100", "GD92": "GD92",
                        "kg0-q995": "kg0-q995", "kg0-q998": "kg0-q998", "kg0-q999": "kg0-q999",
                        "kg0-q998-15m": "kg0-q998-15m"}[name], {})
        s = {}
        for lv in ("20", "30"):
            exp = None
            if pr and ("tf%s" % lv) in pr:
                exp = float(pr["tf%s" % lv]["tail_sum"])
            got = blk[lv]["sum"]
            ok = None if exp is None else bool(abs(got - exp) <= 1e-6 * max(1.0, abs(exp)))
            s["tf" + lv] = dict(got=round(got, 4), prior=round(exp, 4) if exp is not None else None,
                                match=ok)
        out["sanity"][name] = s
        out["table"].append(dict(
            name=name, n=int(len(P)),
            a_pct=round(sa, 2), a_pass=pass_a,
            tf25=round(blk["25"]["sum"], 2), tf25_sign=blk["25"]["sign"],
            b25_pass=pass_b25, q_star=qs,
            ci25_raw=[round(v, 2) for v in ci["raw95"]],
            ci25_infl=[round(v, 2) for v in ci["infl"]],
            ci25_out=ci["out"]))
        print("[%s] n=%d sum=%.1f TF25=%.1f a=%.2f%% q*=%.1f%% passA=%s passB25=%s" % (
            name, len(P), P.sum(), blk["25"]["sum"], sa, qs or -1, pass_a, pass_b25), file=sys.stderr)

    out["missing"] = missing
    san_bad = [k for k, v in out["sanity"].items()
               if any(c.get("match") is False for c in v.values())]
    out["sanity_all_match"] = (len(san_bad) == 0)
    out["sanity_mismatch"] = san_bad
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", a.json, os.path.getsize(a.json), "bytes | sanity_match=", out["sanity_all_match"],
          "bad=", san_bad, file=sys.stderr)


if __name__ == "__main__":
    main()
