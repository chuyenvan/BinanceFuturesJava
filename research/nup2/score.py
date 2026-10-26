#!/usr/bin/env python3
"""NUP score: chấm 7 arm theo §3/§4 PREREG_NUP.md (+ADDENDUM A/B).

Input: ~/kaggle_sim/out/<tag>/ (printDone, result.json), ~/claude_master/nup_wk/eq_parquet.npz
Baseline B0: docs/result/golive_quarterly/quarterly_x14_by_seed.csv + printDone gốc.
MTM DEV: eq_parquet (kline parquet, công thức legacy + PnL 00:00 UTC) -> fix_off=None.
MTM HO : ecm_mtm_h + cache ecm_px (mtm_new.py ho).

Out: docs/result/nup/{runs.csv, arms.csv, frontier.csv, match.csv, score.json}
Usage: python3 score.py [p1|p2|all]
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

WK = "/home/ubuntu/claude_master/nup_wk"
KS = "/home/ubuntu/kaggle_sim/out/"
OUTD = REPO + "/docs/result/nup"
CAP0 = Q.CAP0
H7 = Q.H7
MIN = Q.MIN
DEV_SEEDS = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]
P1_SEEDS = ["a1", "s7", "s21", "s99"]
HO_SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
ARMS = ["a1", "a2", "a3", "a4", "a5", "a6", "a7"]
BS = pd.read_csv(REPO + "/docs/result/golive_quarterly/quarterly_x14_by_seed.csv")
FD = Q.flagset(json.load(open("/home/ubuntu/claude_master/tsx/flags.json"))["ranges"])
FH = Q.flagset(json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))["ranges"])
UB = pd.Timestamp("2021-07-01") - H7
NDEV = int((pd.Timestamp("2026-01-01") - pd.Timestamp("2021-07-01")) // MIN)
OFF = 420


def b0row(phase, seed, period):
    r = BS[(BS.phase == phase) & (BS.seed.astype(str).str.lower() == str(seed).lower()) & (BS.period == period)]
    assert len(r) == 1, (phase, seed, period)
    return r.iloc[0]


def b0_metrics(phase, seed):
    if phase == "DEV":
        out = {}
        for y in (2022, 2023, 2024, 2025):
            g = b0row("DEV", seed, str(y))
            out[y] = dict(n_cl=int(g.n_cl), n_leg=int(g.n_leg), n_entry=int(g.n_entry), pnl=float(g.pnl))
        t = b0row("DEV", seed, "DEV_2022_25")
        out["T"] = dict(n_cl=int(t.n_cl), n_leg=int(t.n_leg), n_entry=int(t.n_entry), pnl=float(t.pnl),
                        cagr=float(t.cagr_ann), dd=float(t.dd_cum))
        out["stress"] = stress_sum("tsx-x14-" + seed, "2022-01-01", "2026-01-01")
    else:
        g = b0row("HO", seed, "HO_2026_W9")
        out = dict(n_cl=int(g.n_cl), n_leg=int(g.n_leg), n_entry=int(g.n_entry), pnl=float(g.pnl),
                   cagr=float(g.cagr_ann), dd=float(g.dd_cum), roi=float(g.roi))
        out["stress"] = stress_sum("tsx-ho-x14-s%d" % seed, "2026-01-01", "2026-10-01")
    return out


def stress_sum(tag, a, b):
    d = Q.load(tag)
    m = (d["te"] >= pd.Timestamp(a)) & (d["te"] < pd.Timestamp(b))
    return float((d.loc[m, "pnl"] - 0.002 * d.loc[m, "notional"]).sum())


def dev_full(e):
    n = min(len(e), NDEV - OFF)
    full = np.empty(NDEV)
    full[:OFF] = CAP0
    full[OFF:OFF + n] = e[:n]
    full[OFF + n:] = e[n - 1]
    return full


def build_r(tags, phase):
    if phase == "DEV":
        z = np.load(WK + "/eq_parquet.npz")
        return {t: Q.build(t, "tsx-x14-" + t.rsplit("-", 1)[-1], dev_full(z[t]), UB, FD, fix_off=None) for t in tags}
    z = np.load(WK + "/eq_ho.npz")
    return {t: Q.build(t, "tsx-ho-x14-s%d" % int(t.split("-s")[-1]), z[t], Q.HO_L0 - H7, FH) for t in tags}


def rows_for(r, phase, seed):
    rows = []
    for name, a, b, k in (Q.DEV_PER if phase == "DEV" else Q.HO_PER):
        rows.append(dict(phase=phase, tag=r["tag"], seed=seed, period=name, kind=k,
                         **Q.metrics(r, a, b, k, Q.ph0_of(name, a), FD if phase == "DEV" else FH)))
    return rows


def arm_periods(df, tag):
    g = df[df.tag == tag]
    return g


def match_groups(arm_tag, b0_tag, a="2022-01-01", b="2026-01-01"):
    A, B = Q.load(arm_tag), Q.load(b0_tag)
    A = A[(A.ts >= pd.Timestamp(a)) & (A.ts < pd.Timestamp(b))]
    B = B[(B.ts >= pd.Timestamp(a)) & (B.ts < pd.Timestamp(b))]
    used = set()
    common = new = 0
    pc = nc = pn = nn = 0.0
    for sym, ga in A.groupby("sym"):
        gb = B[B.sym == sym].sort_values("ts")
        cand = list(zip(gb.index, gb.ts))
        for ia, ta, pnl, notl in zip(ga.index, ga.ts, ga.pnl, ga.notional):
            best, bd = None, 61
            for j, tb in cand:
                if j in used:
                    continue
                dd = abs((tb - ta).total_seconds())
                if dd < bd:
                    bd, best = dd, j
            if best is not None and bd <= 60:
                used.add(best)
                common += 1
                pc += pnl
                nc += notl
            else:
                new += 1
                pn += pnl
                nn += notl
    pl = nl = 0.0
    for j, pnl, notl in zip(B.index, B.pnl, B.notional):
        if j not in used:
            pl += pnl
            nl += notl
    return dict(common=common, new=new, lost=len(B) - common, pnl_common=pc, pnl_new=pn, pnl_lost=pl,
                roi_common=100 * pc / nc if nc else np.nan, roi_new=100 * pn / nn if nn else np.nan,
                roi_lost=100 * pl / nl if nl else np.nan)


def tier2_split(tag):
    d = Q.load(tag)
    f = KS + tag + "/storage/tier2.csv"
    if not os.path.exists(f):
        return dict(n_t2=0, pnl_t2=np.nan, cl_t2=0, pnl_per_cl_t2=np.nan, pnl_other=float(d.pnl.sum()))
    t = pd.read_csv(f, dtype=str)
    t["start"] = t["start"].astype(str).str.strip()
    # printDone luu sym KHONG co hau to USDT; tier2.csv luu symbol day du
    t["sym"] = t["sym"].astype(str).str.strip().str.replace(r"USDT$", "", regex=True)
    d["sym"] = d["sym"].astype(str).str.strip()
    d["start"] = d["start"].astype(str).str.strip()
    m = d.merge(t[["sym", "start"]].drop_duplicates(), on=["sym", "start"], how="inner")
    cl = m.groupby(["sym", "end"]).ngroups
    return dict(n_t2=len(m), pnl_t2=float(m.pnl.sum()), cl_t2=int(cl),
                pnl_per_cl_t2=float(m.pnl.sum() / cl) if cl else np.nan,
                pnl_other=float(d.pnl.sum() - m.pnl.sum()))


def main():
    os.makedirs(OUTD, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    seeds = DEV_SEEDS if mode in ("p2", "all") else P1_SEEDS
    dev_tags = ["nup-%s-%s" % (a, s) for a in ARMS for s in seeds
                if os.path.exists(KS + "nup-%s-%s/storage/printDone.csv" % (a, s))]
    ho_tags = ["nup-ho-%s-s%d" % (a, s) for a in ARMS for s in HO_SEEDS
               if os.path.exists(KS + "nup-ho-%s-s%d/storage/printDone.csv" % (a, s))]
    rows = []
    if dev_tags:
        for t, r in build_r(dev_tags, "DEV").items():
            rows += rows_for(r, "DEV", t.rsplit("-", 1)[-1])
    if ho_tags:
        for t, r in build_r(ho_tags, "HO").items():
            rows += rows_for(r, "HO", int(t.split("-s")[-1]))
    df = pd.DataFrame(rows)
    df.to_csv(OUTD + "/runs.csv", index=False)
    print("rows", len(df), "dev", len(dev_tags), "ho", len(ho_tags))
    return df


if __name__ == "__main__":
    main()
