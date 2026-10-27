#!/usr/bin/env python3
"""Cham lai A7 voi 4 seed (a1,s7,s21<-nup-a7r-s21,s99) theo PREREG_NUP2 §3.

Doc WK/runs.csv (nup-a7-* + nup-a7r-s21) + arms_p1b.csv cho cac arm khac.
In bang E day du va ket luan: A7 co tro thanh 'huu ich' va E hang 2 (khac key A2) khong.
"""
import json
import os

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
WK = "/home/ubuntu/claude_master/nup2_wk"
OUTD = REPO + "/docs/result/nup2"
sys_path = REPO + "/research/nup2"
import sys
sys.path.insert(0, sys_path)
import pick_factorial as P  # noqa: E402

P1 = ["a1", "s7", "s21", "s99"]
A7MAP = {"a1": "nup-a7-a1", "s7": "nup-a7-s7", "s21": "nup-a7r-s21", "s99": "nup-a7-s99"}


def a7_4seed():
    d = pd.read_csv(WK + "/runs.csv")
    B = P.b0_4seed()
    rn, rp, dd, pnl, ncy = [], [], [], [], []
    rows = {}
    for s, tag in A7MAP.items():
        r = d[(d.tag == tag) & (d.period == "DEV_2022_25")]
        if not len(r):
            return None, {}
        r = r.iloc[0]
        b = B[s]
        rn.append(r.n_cl / b["n_cl"])
        rp.append(r.pnl / b["pnl"])
        dd.append(float(r.dd_cum))
        pnl.append(float(r.pnl))
        ncy.append(float(r.n_cl) / 4)
        rows[s] = dict(tag=tag, n_cl=int(r.n_cl), pnl=float(r.pnl), dd=float(r.dd_cum),
                       r_ncl=float(r.n_cl / b["n_cl"]), r_pnl=float(r.pnl / b["pnl"]))
    return dict(n=float(np.median(rn)), p=float(np.median(rp)), dd=float(np.median(dd)),
                pnl=float(np.median(pnl)), n_cl_year=float(np.median(ncy)), nseed=4), rows


def main():
    R = P.nup_arms()
    R.update(P.nup2_arms())
    a7, per = a7_4seed()
    if a7:
        R["a7"] = a7
    b0dd = float(np.median([v["dd"] for v in P.b0_4seed().values()]))
    print("A7 per-seed:", json.dumps(per, indent=1))
    table = []
    for a in P.CAND:
        if a not in R:
            continue
        v = R[a]
        ddd = v["dd"] - b0dd
        E = (v["n"] - 1) / max(0.5, abs(ddd))
        useful = bool(a == "b1" or (v["n"] >= 1.10 and v["p"] >= 0.80))
        table.append(dict(arm=a, label=P.LABEL[a], n_cl_year=v["n_cl_year"], n=v["n"], pnl=v["pnl"],
                          p=v["p"], dd=v["dd"], ddd=ddd, E=E, useful=useful, nseed=v["nseed"]))
    ranked = sorted([t for t in table if t["nseed"] == 4], key=lambda t: -t["E"])
    rank = {t["arm"]: i + 1 for i, t in enumerate(ranked)}
    print("\n%-4s %-18s %9s %7s %11s %7s %9s %8s %6s %6s %4s" %
          ("arm", "lever", "cl/nam", "xB0", "SumPnL", "xB0", "maxDDmed", "dDDpp", "E", "huuich", "h"))
    for t in table:
        print("%-4s %-18s %9.1f %7.3f %11.0f %7.3f %9.2f %8.2f %6.3f %6s %4s" %
              (t["arm"].upper(), t["label"], t["n_cl_year"], t["n"], t["pnl"], t["p"], t["dd"],
               t["ddd"], t["E"], "YES" if t["useful"] else "no", rank.get(t["arm"], "-")))
    useful = [t for t in ranked if t["useful"] and t["arm"] != "b1"]
    urank = {t["arm"]: i + 1 for i, t in enumerate(useful)}
    a7t = next(t for t in table if t["arm"] == "a7")
    cond = bool(a7t["useful"] and urank.get("a7") == 2 and P.KEY["a7"] != P.KEY["a2"])
    print("\nXep hang E trong cac lever HUU ICH (tru B1): ",
          [(t["arm"], round(t["E"], 3)) for t in useful])
    print("A7 useful=%s rank_all=%s rank_useful=%s -> DIEU KIEN DUNG=%s"
          % (a7t["useful"], rank.get("a7"), urank.get("a7"), cond))
    out = dict(per_seed=per, table=table, rank=rank, b0_dd_4seed=b0dd,
               a7_useful=bool(a7t["useful"]), a7_rank_all=rank.get("a7"),
               a7_rank_useful=urank.get("a7"), useful_rank=[(t["arm"], t["E"]) for t in useful],
               stop_condition=cond)
    json.dump(out, open(WK + "/a7_rescore.json", "w"), indent=1, default=float)
    print("wrote", WK + "/a7_rescore.json")


if __name__ == "__main__":
    main()
