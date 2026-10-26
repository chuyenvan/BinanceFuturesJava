#!/usr/bin/env python3
"""Hieu chuan SIM_F_BASE cho A6 theo ADDENDUM A (khong dung PnL).
Usage: python3 calib_a6.py a1 s7   -> ~/claude_master/nup_wk/a6_fbase.json
"""
import json
import sys

import numpy as np
import pandas as pd

WK = "/home/ubuntu/claude_master/nup_wk"
KS = "/home/ubuntu/kaggle_sim/out/"
F0 = 0.015
UMAX = 0.60
TARGET = 0.67
DAY0 = pd.Timestamp("2021-07-01")


def us(tag, eq):
    d = pd.read_csv(KS + tag + "/storage/printDone.csv", index_col=False)
    d["sym"] = d["sym"].astype(str)
    d["ts"] = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d["end"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["margin"] = pd.to_numeric(d["margin"], errors="coerce")
    c = d.groupby(["sym", "te"]).agg(t0=("ts", "min")).reset_index()
    out = []
    for _, r in c.iterrows():
        i = int((r.t0 - pd.Timedelta(hours=7) - DAY0) // pd.Timedelta(minutes=1))
        if i < 0 or i >= len(eq):
            continue
        mrun = d[(d.ts < r.t0) & (d.te > r.t0)].margin.sum()
        out.append(float(mrun) / float(eq[i]))
    return np.array(out)


def f(rF, U):
    return rF * (1 - rF * U / UMAX) / (1 - U / UMAX)


def main():
    z = np.load(WK + "/eq_parquet.npz")
    Us = []
    for s in sys.argv[1:]:
        t = "nup-a4-" + s
        assert t in z.files, "thieu eq parquet cho " + t
        Us.append(us(t, z[t]))
        print(t, "n", len(Us[-1]), "U_med", round(float(np.median(Us[-1])), 4))
    U = np.concatenate(Us)
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if np.median(f(mid, U)) < TARGET:
            lo = mid
        else:
            hi = mid
    rF = (lo + hi) / 2
    out = dict(f_base=round(F0 * rF, 6), rF=round(rF, 8), u_med=float(np.median(U)),
               target=TARGET, f_med=float(np.median(f(rF, U))), seeds=sys.argv[1:],
               n=len(U), method="bisection median f(rF,U)=0.67, ADDENDUM A")
    json.dump(out, open(WK + "/a6_fbase.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
