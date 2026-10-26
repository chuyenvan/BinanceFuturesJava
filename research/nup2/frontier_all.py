#!/usr/bin/env python3
"""Bang frontier gop NUP + NUP2 (moi o), kem N_eff + iso-DD.
Usage: python3 frontier_all.py  -> docs/result/nup2/frontier_all.csv
"""
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
WK = "/home/ubuntu/claude_master/nup2_wk"
OUTD = REPO + "/docs/result/nup2"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/nup2")
import summarize2 as Z  # noqa: E402
import score as S  # noqa: E402

P1 = ["a1", "s7", "s21", "s99"]
P2 = P1 + ["s13", "s123", "s777", "s2024"]


def main():
    df = pd.concat([pd.read_csv(REPO + "/docs/result/nup/runs.csv"), pd.read_csv(WK + "/runs.csv")],
                   ignore_index=True)
    ex = []
    for f in (WK + "/extras_nup.csv", WK + "/extras.csv"):
        if os.path.exists(f):
            ex.append(pd.read_csv(f))
    E = pd.concat(ex, ignore_index=True).drop_duplicates("tag") if ex else pd.DataFrame(columns=["tag"])
    Z.extra = lambda: E
    arms = ["a1", "a2", "a3", "a4", "a5", "a6", "b1", "b2", "b3", "b4", "b5", "a7"]
    rows = []
    for a in arms:
        for seeds, tag in ((P1, a), (P2, a + "_8")):
            r = Z.arm_stats(df, a, seeds, "nup-")
            if not r or (tag.endswith("_8") and a != "a2"):
                continue
            s = Z.summarize(r)
            s["arm"] = tag
            rows.append(s)
    # cells
    if os.path.exists(WK + "/factorial.json"):
        import json
        fj = json.load(open(WK + "/factorial.json"))
        for c in fj["cells"]:
            r = Z.arm_stats(df, c, P1, "nup2-c-%s-" % c)
            if r:
                s = Z.summarize(r)
                s["arm"] = "C:" + c
                rows.append(s)
    A = pd.DataFrame(rows)
    # B0
    b = [S.b0_metrics("DEV", s) for s in P1]
    A = pd.concat([pd.DataFrame([dict(
        arm="B0", n_cl_year=float(np.median([x["T"]["n_cl"] / 4 for x in b])),
        n_cl_ratio=1.0, pnl=float(np.median([x["T"]["pnl"] for x in b])), pnl_ratio=1.0,
        stress_ratio=1.0, cagr=float(np.median([x["T"]["cagr"] for x in b])),
        dd_median=float(np.median([x["T"]["dd"] for x in b])), dd_worst=float(min(x["T"]["dd"] for x in b)),
        calmar=np.nan, neff=np.nan, iso_s=np.nan, iso_ncl_year=np.nan, iso_pnl=np.nan, iso_calmar=np.nan)]), A],
                 ignore_index=True)
    cols = ["arm", "n_cl_year", "n_cl_ratio", "pnl", "pnl_ratio", "stress_ratio", "cagr", "dd_median",
            "dd_worst", "calmar", "exp_max", "npos_max", "neff", "top10_share", "G1", "G2", "G3", "PASS",
            "iso_s", "iso_ncl_year", "iso_pnl", "iso_calmar"]
    A = A[[c for c in cols if c in A.columns]]
    A.to_csv(OUTD + "/frontier_all.csv", index=False)
    print(A.to_string(index=False))


if __name__ == "__main__":
    main()
