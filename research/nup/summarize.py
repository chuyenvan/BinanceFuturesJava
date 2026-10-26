#!/usr/bin/env python3
"""NUP summarize: tu runs.csv -> bang arm, gate G1-G4, frontier, match, tier2.
Usage: python3 summarize.py p1|p2
Out: docs/result/nup/{arms.csv, frontier.csv, match.csv, score.json}
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
import score as S  # noqa: E402

OUTD = REPO + "/docs/result/nup"
KS = "/home/ubuntu/kaggle_sim/out/"
P1 = ["a1", "s7", "s21", "s99"]
P2 = P1 + ["s13", "s123", "s777", "s2024"]
HO = [42, 7, 13, 21, 99, 123, 777, 2024]


def arm_stats(df, arm, seeds):
    g = df[(df.tag.str.startswith("nup-%s-" % arm)) & (df.phase == "DEV")]
    if not g.tag.nunique():
        return None
    rows = {}
    for s in seeds:
        t = g[(g.seed == s) & (g.period == "DEV_2022_25")]
        if not len(t):
            continue
        t = t.iloc[0]
        b = S.b0_metrics("DEV", s)
        st = S.stress_sum("nup-%s-%s" % (arm, s), "2022-01-01", "2026-01-01")
        yr = {}
        for y in (2022, 2023, 2024, 2025):
            a = g[(g.seed == s) & (g.period == str(y))].iloc[0]
            yr[y] = dict(n_cl=int(a.n_cl), ratio=float(a.n_cl / b[y]["n_cl"]))
        rows[s] = dict(seed=s, n_cl=int(t.n_cl), n_leg=int(t.n_leg), n_entry=int(t.n_entry), pnl=float(t.pnl),
                       cagr=float(t.cagr_ann), dd=float(t.dd_cum), calmar=float(t.cagr_ann / abs(t.dd_cum)) if t.dd_cum < 0 else np.nan,
                       exp_mean=float(t.exp_mean), exp_max=float(t.exp_max), npos_max=int(t.npos_max),
                       stress=st, b0=b, yr=yr,
                       r_ncl=float(t.n_cl / b["T"]["n_cl"]), r_pnl=float(t.pnl / b["T"]["pnl"]),
                       r_stress=float(st / b["stress"]))
    return rows


def summarize(arm_rows):
    ncl = np.median([v["n_cl"] / 4 for v in arm_rows.values()])
    b0n = np.median([v["b0"]["T"]["n_cl"] / 4 for v in arm_rows.values()])
    pnl = np.median([v["pnl"] for v in arm_rows.values()])
    b0p = np.median([v["b0"]["T"]["pnl"] for v in arm_rows.values()])
    st = np.median([v["stress"] for v in arm_rows.values()])
    b0s = np.median([v["b0"]["stress"] for v in arm_rows.values()])
    dds = [v["dd"] for v in arm_rows.values()]
    out = dict(
        n_cl_year=float(ncl), n_cl_ratio=float(np.median([v["r_ncl"] for v in arm_rows.values()])),
        pnl=float(pnl), pnl_ratio=float(np.median([v["r_pnl"] for v in arm_rows.values()])),
        stress=float(st), stress_ratio=float(np.median([v["r_stress"] for v in arm_rows.values()])),
        n_seed_pnl85=int(sum(v["r_pnl"] >= 0.85 for v in arm_rows.values())),
        cagr=float(np.median([v["cagr"] for v in arm_rows.values()])),
        dd_median=float(np.median(dds)), dd_worst=float(min(dds)),
        calmar=float(np.median([v["calmar"] for v in arm_rows.values()])),
        exp_max=float(np.median([v["exp_max"] for v in arm_rows.values()])),
        npos_max=int(max(v["npos_max"] for v in arm_rows.values())),
        years={y: float(np.median([v["yr"][y]["ratio"] for v in arm_rows.values()])) for y in (2022, 2023, 2024, 2025)},
    )
    n = len(arm_rows)
    need = 3 if n <= 4 else 6
    out["G1"] = bool(out["n_cl_ratio"] >= 1.30 and all(out["years"][y] >= 1.15 for y in out["years"]))
    out["G2"] = bool(out["pnl_ratio"] >= 0.90 and out["n_seed_pnl85"] >= need and out["stress_ratio"] >= 0.85)
    out["G3"] = bool(out["dd_median"] >= -32 and out["dd_worst"] >= -36)
    out["PASS_P1"] = bool(out["G1"] and out["G2"] and out["G3"])
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "p1"
    df = pd.read_csv(OUTD + "/runs.csv")
    seeds = P1 if mode == "p1" else P2
    arms = []
    for a in S.ARMS:
        r = arm_stats(df, a, seeds)
        if not r:
            continue
        s = summarize(r)
        s["arm"] = a
        arms.append(s)
        print(a, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items() if k != "years"}, s["years"])
    A = pd.DataFrame(arms)
    A.to_csv(OUTD + "/arms.csv", index=False)
    # frontier
    F = A[["arm", "n_cl_year", "n_cl_ratio", "pnl", "pnl_ratio", "stress_ratio", "cagr", "dd_median", "dd_worst", "calmar", "exp_max", "npos_max"]]
    F.to_csv(OUTD + "/frontier.csv", index=False)
    # match + tier2 (DEV, seeds of this phase)
    rows = []
    for a in S.ARMS:
        for s in seeds:
            t = "nup-%s-%s" % (a, s)
            if not os.path.exists(KS + t + "/storage/printDone.csv"):
                continue
            m = S.match_groups(t, "tsx-x14-" + s)
            m.update(arm=a, seed=s)
            if a == "a7":
                m.update(S.tier2_split(t))
            rows.append(m)
    pd.DataFrame(rows).to_csv(OUTD + "/match.csv", index=False)
    json.dump(dict(mode=mode, seeds=seeds, arms=arms), open(OUTD + "/score.json", "w"), indent=1, default=float)
    print("wrote", OUTD)


if __name__ == "__main__":
    main()
