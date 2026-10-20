#!/usr/bin/env python3
"""Suy ra kich thuoc ro (totalValid) live vs offline tu mbs = up/n, pma = above/n, adr = up/down."""
import glob, sys
import numpy as np, pandas as pd
W = "/home/ubuntu/claude_master/parity_1020"
exec(open(W + "/par_a.py").read().split("res = {}")[0])
L = pd.concat([d for d in (read_gz(p) for p in sorted(glob.glob(W + "/raw242/dumps/feat_dump_*.csv.gz"))) if d is not None], ignore_index=True)
L["min"] = (L.ts // 60000) * 60000
L = L.drop_duplicates("min", keep="last"); L = L[L["min"] >= T0]
E = pd.read_csv(W + "/devexport_1016_1020_md.csv.gz"); E["min"] = E.ts.astype("int64")
J = L.merge(E, on="min", suffixes=("_l", "_e"))


def infer_n(mbs, pma, adr, lo=150, hi=700):
    best = None
    for n in range(lo, hi):
        u = mbs * n; a = pma * n
        if abs(u - round(u)) < 2e-3 * max(1, n / 300) and abs(a - round(a)) < 2e-3 * max(1, n / 300):
            up = round(u)
            # adr = up/down -> down = up/adr
            if adr > 0 and adr < 10:
                d = up / adr
                if abs(d - round(d)) > 2e-3 * n:
                    continue
            return n
    return best


rows = []
for _, r in J.iloc[::37].iterrows():
    nl = infer_n(float(r.marketBreadthStrength_l), float(r.percentAboveMA20_l), float(r.advanceDeclineRatio_l))
    ne = infer_n(float(r.marketBreadthStrength_e), float(r.percentAboveMA20_e), float(r.advanceDeclineRatio_e))
    rows.append(dict(t=f7(int(r["min"])), n_live=nl, n_off=ne))
R = pd.DataFrame(rows)
print(R.to_string(index=False, max_rows=200))
print(R.assign(d=R.n_live - R.n_off).d.describe())
