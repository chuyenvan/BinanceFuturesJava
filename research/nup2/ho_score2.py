#!/usr/bin/env python3
"""NUP2 HO 2026 score: SigmaPnL realized + maxDD realized (MASTER 10-26).
Usage: python3 ho_score2.py <arm=prefix> ...
Out: nup2_wk/ho_<arm>.csv, docs/result/nup2/ho.csv
"""
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/golive_quarterly")
import quarterly as Q  # noqa: E402

OUTD = REPO + "/docs/result/nup2"
WK = "/home/ubuntu/claude_master/nup2_wk"
KS = "/home/ubuntu/kaggle_sim/out/"
BS = pd.read_csv(REPO + "/docs/result/golive_quarterly/quarterly_x14_by_seed.csv")
HO_SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]


def b0(seed):
    r = BS[(BS.phase == "HO") & (BS.seed.astype(str) == str(seed)) & (BS.period == "HO_2026_W9")]
    return r.iloc[0]


def run(tag):
    d = Q.load(tag)
    d = d[(d.te >= pd.Timestamp("2026-01-01")) & (d.te < pd.Timestamp("2026-10-01"))]
    e = 35000.0 + d.sort_values("te")["pnl"].cumsum().to_numpy()
    pk = np.maximum.accumulate(e)
    return dict(pnl=float(d.pnl.sum()), n_cl=int(d.groupby(["sym", "te"]).ngroups), n_leg=int(len(d)),
                dd=float(100 * (e / pk - 1).min()) if len(e) else 0.0)


def main(pairs):
    rows = []
    for arm, prefix in pairs:
        for s in HO_SEEDS:
            tag = "%s-s%d" % (prefix, s)
            if not os.path.exists(KS + tag + "/storage/printDone.csv"):
                continue
            r = run(tag)
            b = b0(s)
            r.update(arm=arm, seed=s, b0_pnl=float(b.pnl), b0_ncl=int(b.n_cl),
                     r_pnl=float(r["pnl"] / b.pnl))
            rows.append(r)
    D = pd.DataFrame(rows)
    D.to_csv(WK + "/ho.csv", index=False)
    if len(D):
        agg = D.groupby("arm").agg(pnl=("pnl", "median"), b0_pnl=("b0_pnl", "median"),
                                   r_pnl=("r_pnl", "median"), dd_med=("dd", "median"),
                                   dd_worst=("dd", "min"), n=("seed", "count")).reset_index()
        agg["G4"] = (agg.r_pnl >= 0.80) & (agg.dd_worst >= -12)
        print(agg.to_string(index=False))
        agg.to_csv(OUTD + "/ho_g4.csv", index=False)
    return D


if __name__ == "__main__":
    ps = [x.split("=") for x in sys.argv[1:]]
    main(ps)
