#!/usr/bin/env python3
"""Tuong tac factorial NUP2 Pha 2b: Δ(o) so voi ΔX + ΔY (+ ΔB1), median 4 seed.

Doc WK/runs.csv cho cac o nup2-c-* va cac arm don (nup-a2-*, nup-a3-*, nup-b1-*).
Out: docs/result/nup2/interact_p2b.csv + in bang.
"""
import json
import os

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
WK = "/home/ubuntu/claude_master/nup2_wk"
OUTD = REPO + "/docs/result/nup2"
P1 = ["a1", "s7", "s21", "s99"]


def b0():
    bs = pd.read_csv(REPO + "/docs/result/golive_quarterly/quarterly_x14_by_seed.csv")
    out = {}
    for s in P1:
        r = bs[(bs.phase == "DEV") & (bs.seed.astype(str).str.lower() == s)
               & (bs.period == "DEV_2022_25")].iloc[0]
        out[s] = dict(n_cl=float(r.n_cl), pnl=float(r.pnl), dd=float(r.dd_cum))
    return out


def rows(tagmap):
    """tagmap: name -> function(seed)->tag. Tra ve dict name -> per-seed deltas."""
    d = pd.concat([pd.read_csv(REPO + "/docs/result/nup/runs.csv"), pd.read_csv(WK + "/runs.csv")],
                  ignore_index=True).drop_duplicates(["tag", "period"])
    B = b0()
    out = {}
    for name, fn in tagmap.items():
        z = {}
        for s in P1:
            t = fn(s)
            r = d[(d.tag == t) & (d.period == "DEV_2022_25")]
            if not len(r):
                z = None
                break
            r = r.iloc[0]
            b = B[s]
            z[s] = dict(dn=float(r.n_cl - b["n_cl"]), dp=float(r.pnl - b["pnl"]),
                        dd=float(r.dd_cum - b["dd"]), n_cl=float(r.n_cl), pnl=float(r.pnl),
                        dd_abs=float(r.dd_cum))
        out[name] = z
    return out


def med(z, k):
    return float(np.median([v[k] for v in z.values()])) if z else np.nan


def main():
    fj = json.load(open(WK + "/factorial.json"))
    X, Y = fj["X"], fj["Y"]
    T = {X: lambda s, a=X: "nup-%s-%s" % (a, s),
         Y: lambda s, a=Y: "nup-%s-%s" % (a, s),
         "b1": lambda s: "nup-b1-%s" % s}
    for c in ("xy", "xb1", "yb1", "xyb1"):
        T[c] = (lambda cc: (lambda s: "nup2-c-%s-%s" % (cc, s)))(c)
    R = rows(T)
    lines = []
    recs = []

    def add(name, formula):
        z = {}
        for s in P1:
            base = {k: R[k][s] for k in formula}
            z[s] = dict(dn=sum(w * base[k]["dn"] for k, w in formula.items()),
                        dp=sum(w * base[k]["dp"] for k, w in formula.items()),
                        dd=sum(w * base[k]["dd"] for k, w in formula.items()))
        recs.append(dict(name=name, dn=med(z, "dn"), dp=med(z, "dp"), dd=med(z, "dd")))
        return z

    add(X.upper(), {X: 1})
    add(Y.upper(), {Y: 1})
    add("B1", {"b1": 1})
    # single cells measured
    for name, cell, comp in ((X.upper() + "+" + Y.upper(), "xy", {X: 1, Y: 1}),
                             (X.upper() + "+B1", "xb1", {X: 1, "b1": 1}),
                             (Y.upper() + "+B1", "yb1", {Y: 1, "b1": 1}),
                             (X.upper() + "+" + Y.upper() + "+B1", "xyb1", {X: 1, Y: 1, "b1": 1})):
        zc = {s: dict(dn=R[cell][s]["dn"], dp=R[cell][s]["dp"], dd=R[cell][s]["dd"]) for s in P1}
        recs.append(dict(name=name + " (do)", dn=med(zc, "dn"), dp=med(zc, "dp"), dd=med(zc, "dd")))
        za = {}
        for s in P1:
            za[s] = dict(dn=sum(w * R[k][s]["dn"] for k, w in comp.items()),
                         dp=sum(w * R[k][s]["dp"] for k, w in comp.items()),
                         dd=sum(w * R[k][s]["dd"] for k, w in comp.items()))
        recs.append(dict(name=name + " (cong)", dn=med(za, "dn"), dp=med(za, "dp"), dd=med(za, "dd")))
        recs.append(dict(name=name + " TUONG TAC", dn=med(zc, "dn") - med(za, "dn"),
                         dp=med(zc, "dp") - med(za, "dp"), dd=med(zc, "dd") - med(za, "dd")))
    D = pd.DataFrame(recs)
    D.to_csv(OUTD + "/interact_p2b.csv", index=False)
    print(D.to_string(index=False, float_format=lambda x: "%.2f" % x))
    # % tuong tac so voi cong
    print("\n%% tuong tac / (cong):")
    for i in range(0, len(D), 4):
        pass
    return D


if __name__ == "__main__":
    main()
