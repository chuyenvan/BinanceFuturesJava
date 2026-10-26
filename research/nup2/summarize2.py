#!/usr/bin/env python3
"""NUP2 summarize: tu runs.csv + extras.csv -> arms/gates/frontier/match.
Dung lai dinh nghia NUP §4 (G1-G4). Usage: python3 summarize2.py p1b|p2b|p3
"""
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/golive_quarterly")
sys.path.insert(0, REPO + "/research/nup")
import quarterly as Q  # noqa: E402
import score as S  # noqa: E402

WK = "/home/ubuntu/claude_master/nup2_wk"
OUTD = REPO + "/docs/result/nup2"
KS = "/home/ubuntu/kaggle_sim/out/"
P1 = ["a1", "s7", "s21", "s99"]
P2 = P1 + ["s13", "s123", "s777", "s2024"]
HO = [42, 7, 13, 21, 99, 123, 777, 2024]
ARMS = ["b1", "b2", "b3", "b4", "b5", "a7"]
CELLS = {}  # arm -> tag prefix, fill from state/plan when factorial exists


def extra():
    f = WK + "/extras.csv"
    return pd.read_csv(f) if os.path.exists(f) else pd.DataFrame(columns=["tag"])


def realized_dd(tag):
    d = Q.load(tag)
    e = S.CAP0 + d.sort_values("te")["pnl"].cumsum().to_numpy()
    pk = np.maximum.accumulate(e)
    return float(100 * (e / pk - 1).min())


def arm_stats(df, arm, seeds, prefix="nup-"):
    g = df[(df.tag.str.startswith(prefix + "%s-" % arm)) & (df.phase == "DEV")]
    if not g.tag.nunique():
        return None
    X = extra().set_index("tag")
    rows = {}
    for s in seeds:
        t = g[(g.seed == s) & (g.period == "DEV_2022_25")]
        if not len(t):
            continue
        t = t.iloc[0]
        b = S.b0_metrics("DEV", s)
        tag = "%s%s-%s" % (prefix, arm, s)
        st = S.stress_sum(tag, "2022-01-01", "2026-01-01")
        yr = {}
        for y in (2022, 2023, 2024, 2025):
            a = g[(g.seed == s) & (g.period == str(y))].iloc[0]
            yr[y] = dict(n_cl=int(a.n_cl), ratio=float(a.n_cl / b[y]["n_cl"]))
        ex = X.loc[tag].to_dict() if tag in X.index else {}
        rows[s] = dict(seed=s, n_cl=int(t.n_cl), n_leg=int(t.n_leg), n_entry=int(t.n_entry), pnl=float(t.pnl),
                       cagr=float(t.cagr_ann), dd=float(t.dd_cum), calmar=float(t.cagr_ann / abs(t.dd_cum)) if t.dd_cum < 0 else np.nan,
                       exp_mean=float(t.exp_mean), exp_max=float(t.exp_max), npos_max=int(t.npos_max),
                       stress=st, b0=b, yr=yr, ex=ex,
                       r_ncl=float(t.n_cl / b["T"]["n_cl"]), r_pnl=float(t.pnl / b["T"]["pnl"]),
                       r_stress=float(st / b["stress"]))
    return rows


def summarize(arm_rows):
    n = len(arm_rows)
    need = 3 if n <= 4 else 6
    med = lambda k: float(np.median([v[k] for v in arm_rows.values()]))  # noqa: E731
    dds = [v["dd"] for v in arm_rows.values()]
    out = dict(
        n_seed=n,
        n_cl_year=float(np.median([v["n_cl"] / 4 for v in arm_rows.values()])),
        n_cl_ratio=float(np.median([v["r_ncl"] for v in arm_rows.values()])),
        pnl=med("pnl"), pnl_ratio=float(np.median([v["r_pnl"] for v in arm_rows.values()])),
        stress=float(np.median([v["stress"] for v in arm_rows.values()])),
        stress_ratio=float(np.median([v["r_stress"] for v in arm_rows.values()])),
        n_seed_pnl85=int(sum(v["r_pnl"] >= 0.85 for v in arm_rows.values())),
        cagr=med("cagr"), dd_median=float(np.median(dds)), dd_worst=float(min(dds)),
        calmar=float(np.median([v["calmar"] for v in arm_rows.values()])),
        exp_max=med("exp_max"), npos_max=int(max(v["npos_max"] for v in arm_rows.values())),
        years={y: float(np.median([v["yr"][y]["ratio"] for v in arm_rows.values()])) for y in (2022, 2023, 2024, 2025)},
    )
    exs = [v["ex"] for v in arm_rows.values() if v.get("ex")]
    if exs:
        for k in ("neff", "days_new", "top10_share", "pnl_entry", "pnl_dca", "n_dca_leg", "leg_per_cl_med",
                  "dca_per_cl_med", "cluster_notional_max", "leg0_notional_med", "skip_full", "gate_pass", "n_tier2", "pnl_tier2"):
            vals = [float(x[k]) for x in exs if k in x and pd.notna(x[k])]
            out[k] = float(np.median(vals)) if vals else np.nan
    out["G1"] = bool(out["n_cl_ratio"] >= 1.30 and all(out["years"][y] >= 1.15 for y in out["years"]))
    out["G2"] = bool(out["pnl_ratio"] >= 0.90 and out["n_seed_pnl85"] >= need and out["stress_ratio"] >= 0.85)
    out["G3"] = bool(out["dd_median"] >= -32 and out["dd_worst"] >= -36)
    out["PASS"] = bool(out["G1"] and out["G2"] and out["G3"])
    s = 30.0 / abs(out["dd_median"]) if out["dd_median"] < 0 else np.nan
    out["iso_s"] = float(s)
    out["iso_ncl_year"] = float(out["n_cl_year"] * s) if s == s else np.nan
    out["iso_pnl"] = float(out["pnl"] * s) if s == s else np.nan
    out["iso_calmar"] = float(out["calmar"] * s) if s == s else np.nan
    return out


def main():
    os.makedirs(OUTD, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "p1b"
    df = pd.read_csv(WK + "/runs.csv")
    seeds = P1 if mode == "p1b" else P2
    arms = []
    for a in list(ARMS) + list(CELLS):
        prefix = CELLS.get(a, "nup-")
        r = arm_stats(df, a, seeds, prefix)
        if not r:
            continue
        s = summarize(r)
        s["arm"] = a
        arms.append(s)
        print(a, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items() if k != "years"}, s["years"])
    A = pd.DataFrame(arms)
    A.to_csv(OUTD + "/arms_%s.csv" % mode, index=False)
    cols = ["arm", "n_cl_year", "n_cl_ratio", "pnl", "pnl_ratio", "stress_ratio", "cagr",
            "dd_median", "dd_worst", "calmar", "exp_max", "npos_max", "neff", "days_new", "top10_share",
            "G1", "G2", "G3", "PASS", "iso_s", "iso_ncl_year", "iso_pnl", "iso_calmar"]
    A[[c for c in cols if c in A]].to_csv(OUTD + "/frontier_%s.csv" % mode, index=False)
    # match groups
    rows = []
    for a in list(ARMS) + list(CELLS):
        prefix = CELLS.get(a, "nup-")
        for s in seeds:
            t = "%s%s-%s" % (prefix, a, s)
            if not os.path.exists(KS + t + "/storage/printDone.csv"):
                continue
            m = S.match_groups(t, "tsx-x14-" + s)
            m.update(arm=a, seed=s)
            rows.append(m)
    pd.DataFrame(rows).to_csv(OUTD + "/match_%s.csv" % mode, index=False)
    json.dump(dict(mode=mode, seeds=seeds, arms=arms), open(OUTD + "/score_%s.json" % mode, "w"), indent=1, default=float)
    print("wrote", OUTD)


if __name__ == "__main__":
    main()
