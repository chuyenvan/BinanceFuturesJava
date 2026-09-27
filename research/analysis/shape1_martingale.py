"""SHAPE1-EARLY-CUT — 3 chi so martingale (VIEC 3.7 cua PREREG_SHAPE1_EARLY_CUT.md).

  (i)  lo LON NHAT 1 vi the / 1 coin, tung nam  (vi the = cum (sym, end) tong pnl < 0)
  (ii) conc 1 coin co vuot 15 % khong            (summary.conc, tran appetite latest)
  (iii) so coin "chet" = coin co SigmaPnL < 0

Dung: python3 research/analysis/shape1_martingale.py TAG [TAG ...]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import pandas as pd
import gd92xexit_score as G


def report(tag):
    d = G.trades(tag).copy()
    d["yr"] = d["ts"].dt.year
    s = G.summary(tag)
    out = dict(tag=tag, n=int(len(d)), conc_pct=round(float(s["conc"]), 3),
               conc_over15=bool(s["conc"] > 15.0))
    # (i) worst position (cum sym,end) pnl per year; also worst single leg
    pos = d.groupby(["yr", "sym", "end"])["pnl"].sum().reset_index()
    leg = d.groupby("yr")["pnl"].min()
    py = {}
    for y, g in pos.groupby("yr"):
        py[int(y)] = dict(worst_pos=round(float(g["pnl"].min()), 1),
                          worst_leg=round(float(leg.loc[y]), 1),
                          n_pos=int(len(g)), n_pos_loss=int((g["pnl"] < 0).sum()))
    out["by_year"] = py
    out["worst_pos_all"] = round(float(pos["pnl"].min()), 1)
    out["worst_leg_all"] = round(float(leg.min()), 1)
    # (iii) dead coins
    c = d.groupby("sym")["pnl"].sum()
    out["n_coins"] = int(len(c))
    out["n_dead_coins"] = int((c < 0).sum())
    out["dead_pnl_sum"] = round(float(c[c < 0].sum()), 1)
    out["top_dead"] = {k: round(float(v), 1) for k, v in c.nsmallest(3).items()}
    return out


if __name__ == "__main__":
    rows = {}
    for t in sys.argv[1:]:
        try:
            rows[t] = report(t)
        except Exception as e:
            print("%-18s KHONG DOC DUOC: %s" % (t, e))
    print("=" * 100)
    print("%-18s %5s %8s %8s %10s %8s %8s" % ("tag", "n", "conc%", "conc>15", "worstPos", "worstLeg", "deadCoin"))
    for t, r in rows.items():
        print("%-18s %5d %8s %8s %10s %10s %8d / %d" % (
            t, r["n"], r["conc_pct"], r["conc_over15"], r["worst_pos_all"], r["worst_leg_all"],
            r["n_dead_coins"], r["n_coins"]))
    print("\nLo LON NHAT 1 vi the/1 coin theo NAM:")
    for t, r in rows.items():
        print("  %-18s %s" % (t, json.dumps(r["by_year"])))
    out = "docs/result/shape1_martingale.json"
    with open(out, "w") as f:
        json.dump(rows, f, indent=1)
    print("\nJSON: %s" % out)
