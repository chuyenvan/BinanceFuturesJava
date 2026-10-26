#!/usr/bin/env python3
"""Chon X,Y theo PREREG_NUP2 §3, sua theo MASTER_FIX 2026-10-26 muc 2.

- Tap ung vien = lever DON: A1, A2, A3, A5, A7, B1, B2, B3, B4.
  A4/A6 la TO HOP => loai. B5 loai (khong tim duoc key dung ngu nghia).
- Moi so dung 4 seed a1/s7/s21/s99 (ke ca A2, khong dung 8 seed Pha 2).
- Moc DD cua B0 cung tinh tren dung 4 seed do (khong dung -22,833 cua 8 seed).
- A7 khong do duoc (s21 timeout 7200 s) => loai khoi tap ung vien.
Out: nup2_wk/factorial.json + plan_f2b.json
"""
import json
import os

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
WK = "/home/ubuntu/claude_master/nup2_wk"
OUTD = REPO + "/docs/result/nup2"
P1 = ["a1", "s7", "s21", "s99"]

# lever don: key cau hinh thuc su bi doi (dung de kiem "X,Y khac key")
KEY = {
    "a1": {"SIM_GATE_ROLLING_PCT"},
    "a2": {"SIM_GATE_ROLLING_PCT"},
    "a3": {"SELECTOR_RANK_TOPK"},
    "a5": {"SIM_GATE_DYN_SCALE"},
    "a7": {"GATE_TIER2"},
    "b1": {"SIM_F_BASE"},
    "b2": {"DCA_GRID_LEVELS"},
    "b3": {"DCA_GRID_LEVELS", "DCA_GRID_WEIGHTS"},
    "b4": {"SIM_U_MAX"},
}
CAND = ["a1", "a2", "a3", "a5", "a7", "b1", "b2", "b3", "b4"]
OV = {
    "a1": {"SIM_GATE_ROLLING_PCT": 0.99990},
    "a2": {"SIM_GATE_ROLLING_PCT": 0.99985},
    "a3": {"SELECTOR_RANK_TOPK": 32},
    "a5": {"SIM_GATE_DYN_SCALE": 1.30},
    "a7": {"GATE_TIER2_ENABLED": "true", "GATE_TIER2_PCT": 0.99985, "GATE_TIER2_U_MAX": 0.20,
           "GATE_TIER2_CRASH_RET": -0.01, "GATE_TIER2_SIZE_MULT": 0.5},
    "b1": {"SIM_F_BASE": 0.006305},
    "b2": {"DCA_GRID_LEVELS": "-0.335,-0.5025,-0.603"},
    "b3": {"DCA_GRID_LEVELS": "-0.50,-0.60,-0.70,-0.80,-0.90", "DCA_GRID_WEIGHTS": "1,1,1,1,1,1"},
    "b4": {"SIM_U_MAX": 0.75},
}
LABEL = {"a1": "A1 gate 0.99990", "a2": "A2 gate 0.99985", "a3": "A3 TOPK 32",
         "a5": "A5 dyn 1.30", "a7": "A7 TIER2", "b1": "B1 size x0.5",
         "b2": "B2 DCA nhip x0.67", "b3": "B3 DCA 6 bac", "b4": "B4 U_MAX x1.25"}


def b0_4seed():
    bs = pd.read_csv(REPO + "/docs/result/golive_quarterly/quarterly_x14_by_seed.csv")
    out = {}
    for s in P1:
        r = bs[(bs.phase == "DEV") & (bs.seed.astype(str).str.lower() == s)
               & (bs.period == "DEV_2022_25")].iloc[0]
        out[s] = dict(n_cl=float(r.n_cl), pnl=float(r.pnl), dd=float(r.dd_cum))
    return out


def nup_arms():
    """A1-A6 tu runs.csv NUP, chi 4 seed P1."""
    d = pd.read_csv(REPO + "/docs/result/nup/runs.csv")
    d["arm"] = d.tag.str.replace("nup-", "", regex=False).str.rsplit("-", n=1).str[0]
    d["sd"] = d.tag.str.rsplit("-", n=1).str[1].str.lower()
    B = b0_4seed()
    out = {}
    for a in ("a1", "a2", "a3", "a4", "a5", "a6"):
        g = d[(d.arm == a) & (d.period == "DEV_2022_25") & d.sd.isin(P1)]
        if not len(g):
            continue
        rn, rp, dd = [], [], []
        for _, r in g.iterrows():
            b = B[r.sd]
            rn.append(r.n_cl / b["n_cl"])
            rp.append(r.pnl / b["pnl"])
            dd.append(float(r.dd_cum))
        out[a] = dict(n=float(np.median(rn)), p=float(np.median(rp)),
                      dd=float(np.median(dd)), nseed=len(g),
                      pnl=float(g.pnl.median()), n_cl_year=float(g.n_cl.median() / 4))
    return out


def nup2_arms():
    """B1-B5, A7 tu arms_p1b.csv (summarize2.py p1b, 4 seed; A7 chi 3 seed)."""
    f = OUTD + "/arms_p1b.csv"
    out = {}
    if not os.path.exists(f):
        return out
    p = pd.read_csv(f)
    for _, r in p.iterrows():
        out[r.arm] = dict(n=float(r.n_cl_ratio), p=float(r.pnl_ratio), dd=float(r.dd_median),
                          nseed=int(r.n_seed), pnl=float(r.pnl), n_cl_year=float(r.n_cl_year))
    return out


def main():
    B = b0_4seed()
    b0dd = float(np.median([v["dd"] for v in B.values()]))
    R = nup_arms()
    R.update(nup2_arms())

    table = []
    for a in CAND:
        if a not in R:
            table.append(dict(arm=a, label=LABEL[a], ok=False, why="khong co du lieu"))
            continue
        v = R[a]
        ok = v["nseed"] == 4
        why = "" if ok else "chi %d/4 seed" % v["nseed"]
        if a == "a7" and not ok:
            why = "khong do duoc (s21 timeout 7200 s)"
        ddd = v["dd"] - b0dd
        E = (v["n"] - 1) / max(0.5, abs(ddd))
        useful = ok and (a == "b1" or (v["n"] >= 1.10 and v["p"] >= 0.80))
        table.append(dict(arm=a, label=LABEL[a], ok=ok, why=why, n_cl_year=v["n_cl_year"], n=v["n"],
                          pnl=v["pnl"], p=v["p"], dd=v["dd"], ddd=ddd, E=E, useful=useful))

    ranked = sorted([t for t in table if t.get("ok")], key=lambda t: -t["E"])
    rank = {t["arm"]: i + 1 for i, t in enumerate(ranked)}
    for t in table:
        t["rank"] = rank.get(t["arm"])

    print("\n=== PREREG §3 — bang E, 4 seed a1/s7/s21/s99, B0 DD median = %.3f%% ===" % b0dd)
    print("%-4s %-18s %9s %8s %12s %8s %9s %8s %6s %5s  %s" %
          ("arm", "lever", "cum/nam", "xB0", "SumPnL", "xB0", "maxDDmed", "dDD pp", "huuich", "E", "hang"))
    for t in table:
        if not t.get("ok"):
            print("%-4s %-18s %s" % (t["arm"].upper(), t["label"], "-- " + t["why"]))
            continue
        print("%-4s %-18s %9.2f %8.3f %12.1f %8.3f %9.2f %8.2f %6s %5.3f  %s" %
              (t["arm"].upper(), t["label"], t["n_cl_year"], t["n"], t["pnl"], t["p"],
               t["dd"], t["ddd"], "YES" if t["useful"] else "no", t["E"],
               t["rank"] if t["rank"] else "-"))
    print("B0  : 4-seed median DD = %.3f%% (8-seed -22.833 KHONG dung)" % b0dd)

    useful = {t["arm"]: t for t in table if t.get("useful")}
    picks = []
    for t in ranked:
        a = t["arm"]
        if a not in useful or a == "b1":
            continue
        if any(KEY[a] & KEY[x] for x in picks):
            continue
        picks.append(a)
        if len(picks) == 2:
            break
    if not picks:
        raise SystemExit("khong co lever huu ich ngoai B1 -> bo Pha 2b")
    X = picks[0]
    Y = picks[1] if len(picks) > 1 else None
    print("\nX = %s (%s)" % (X.upper(), LABEL[X]))
    print("Y = %s" % ((Y.upper() + " (" + LABEL[Y] + ")") if Y else "KHONG (chi 1 lever huu ich)"))

    cells = {}
    if Y:
        cells["xy"] = {X: OV[X], Y: OV[Y]}
        cells["xb1"] = {X: OV[X], "b1": OV["b1"]}
        cells["yb1"] = {Y: OV[Y], "b1": OV["b1"]}
        cells["xyb1"] = {X: OV[X], Y: OV[Y], "b1": OV["b1"]}
    else:
        cells["xb1"] = {X: OV[X], "b1": OV["b1"]}

    out = dict(X=X, Y=Y, picks=picks, b0_dd_4seed=b0dd,
               table=[{k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in t.items()}
                      for t in table],
               useful={k: dict(n=v["n"], p=v["p"], dd=v["dd"]) for k, v in useful.items()},
               E={t["arm"]: float(t["E"]) for t in table if t.get("ok")},
               cells=cells,
               overrides={k: {kk: vv for a in c for kk, vv in OV[a].items()} for k, c in cells.items()})
    json.dump(out, open(WK + "/factorial.json", "w"), indent=1)
    plan = []
    for c, ov in out["overrides"].items():
        for s in P1:
            tag = "nup2-c-%s-%s" % (c, s)
            plan.append(dict(tag=tag, arm=c, seed=s, scope="DEV", ov=ov,
                             jar=("sim-jar-nup-tier2" if "a7" in cells.get(c, {}) else "sim-jar-tsx")))
    json.dump(plan, open(WK + "/plan_f2b.json", "w"), indent=1)
    print("wrote", WK + "/factorial.json", WK + "/plan_f2b.json")


if __name__ == "__main__":
    main()
