#!/usr/bin/env python3
"""Frontier day du NUP + NUP2 tren 4 seed, A7 dung nup-a7r-s21 cho seed s21.

Out: docs/result/nup2/frontier_all.csv (+ in bang)
Dung lai Z.summarize cua summarize2 de dinh nghia G1-G3/iso y nguyen.
"""
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
WK = "/home/ubuntu/claude_master/nup2_wk"
OUTD = REPO + "/docs/result/nup2"
KS = "/home/ubuntu/kaggle_sim/out/"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/golive_quarterly")
sys.path.insert(0, REPO + "/research/nup2")
import quarterly as Q  # noqa: E402
import score as S  # noqa: E402
import summarize2 as Z  # noqa: E402

P1 = ["a1", "s7", "s21", "s99"]
CELLS = ["xy", "xb1", "yb1", "xyb1"]


def runs():
    return pd.concat([pd.read_csv(REPO + "/docs/result/nup/runs.csv"), pd.read_csv(WK + "/runs.csv")],
                     ignore_index=True).drop_duplicates(["tag", "period"])


def extras():
    ex = []
    for f in (WK + "/extras_nup.csv", WK + "/extras.csv"):
        if os.path.exists(f):
            ex.append(pd.read_csv(f))
    return pd.concat(ex, ignore_index=True).drop_duplicates("tag").set_index("tag")


def arm_rows_for(tagmap, df, X):
    rows = {}
    for s, tag in tagmap.items():
        g = df[(df.tag == tag) & (df.period == "DEV_2022_25")]
        if not len(g):
            continue
        g = g.iloc[0]
        b = S.b0_metrics("DEV", s)
        st = S.stress_sum(tag, "2022-01-01", "2026-01-01")
        yr = {}
        for y in (2022, 2023, 2024, 2025):
            a = df[(df.tag == tag) & (df.period == str(y))].iloc[0]
            yr[y] = dict(n_cl=int(a.n_cl), ratio=float(a.n_cl / b[y]["n_cl"]))
        ex = X.loc[tag].to_dict() if tag in X.index else {}
        rows[s] = dict(seed=s, n_cl=int(g.n_cl), n_leg=int(g.n_leg), n_entry=int(g.n_entry), pnl=float(g.pnl),
                       cagr=float(g.cagr_ann), dd=float(g.dd_cum),
                       calmar=float(g.cagr_ann / abs(g.dd_cum)) if g.dd_cum < 0 else np.nan,
                       exp_mean=float(g.exp_mean), exp_max=float(g.exp_max), npos_max=int(g.npos_max),
                       stress=st, b0=b, yr=yr, ex=ex,
                       r_ncl=float(g.n_cl / b["T"]["n_cl"]), r_pnl=float(g.pnl / b["T"]["pnl"]),
                       r_stress=float(st / b["stress"]))
    return rows if len(rows) == 4 else None


def main():
    fj = __import__("json").load(open(WK + "/factorial.json"))
    df, X = runs(), extras()
    maps = {}
    for a in ("a1", "a2", "a3", "a4", "a5", "a6", "b1", "b2", "b3", "b4", "b5"):
        maps[a.upper()] = {s: "nup-%s-%s" % (a, s) for s in P1}
    maps["A7"] = {"a1": "nup-a7-a1", "s7": "nup-a7-s7", "s21": "nup-a7r-s21", "s99": "nup-a7-s99"}
    for c in CELLS:
        maps["C:" + c] = {s: "nup2-c-%s-%s" % (c, s) for s in P1}
    out = []
    for name, m in maps.items():
        r = arm_rows_for(m, df, X)
        if not r:
            print("THIEU", name)
            continue
        s = Z.summarize(r)
        s["cell"] = name
        out.append(s)
    A = pd.DataFrame(out)
    b = [S.b0_metrics("DEV", s) for s in P1]
    b0 = pd.DataFrame([dict(
        cell="B0", n_seed=4, n_cl_year=float(np.median([x["T"]["n_cl"] / 4 for x in b])),
        n_cl_ratio=1.0, pnl=float(np.median([x["T"]["pnl"] for x in b])), pnl_ratio=1.0,
        stress=float(np.median([x["stress"] for x in b])), stress_ratio=1.0,
        cagr=float(np.median([x["T"]["cagr"] for x in b])),
        dd_median=float(np.median([x["T"]["dd"] for x in b])),
        dd_worst=float(min(x["T"]["dd"] for x in b)), calmar=np.nan,
        G1=pd.NA, G2=pd.NA, G3=pd.NA, PASS=pd.NA)])
    A = pd.concat([b0, A], ignore_index=True)
    cols = ["cell", "n_seed", "n_cl_year", "n_cl_ratio", "pnl", "pnl_ratio", "stress", "stress_ratio",
            "cagr", "dd_median", "dd_worst", "calmar", "exp_max", "npos_max", "neff", "days_new",
            "top10_share", "G1", "G2", "G3", "PASS", "iso_s", "iso_ncl_year", "iso_pnl", "iso_calmar"]
    A = A[[c for c in cols if c in A.columns]]
    A.to_csv(OUTD + "/frontier_all.csv", index=False)
    pd.set_option("display.width", 240)
    print(A.to_string(index=False, float_format=lambda x: "%.2f" % x))
    print("wrote", OUTD + "/frontier_all.csv")


if __name__ == "__main__":
    main()
