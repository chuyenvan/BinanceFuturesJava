#!/usr/bin/env python3
"""short_fullchain_merge.py — gop cac manh per-year (raw npz) cua BUOC 3 -> RESULT json.

Chot: docs/prereg/PREREG_SHORT_FULLCHAIN.md (9ac83699). Dung lai agg/ci_mean/by_year cua
short_fullchain_sim.py (khong viet lai thuat toan).
"""
import argparse, json, sys
import numpy as np
import pandas as pd
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import short_fullchain_sim as S  # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", nargs="+", required=True)
    ap.add_argument("--gate-csv", default="/home/ubuntu/src/BinanceFuturesJava/research/parity/data/p15_dev.csv")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ts_l, g_l, p_l, h_l = [], [], [], []
    combos = None
    for f in a.raw:
        z = np.load(f, allow_pickle=True)
        ts_l.append(z["ts"]); g_l.append(z["g"]); p_l.append(z["pnl"]); h_l.append(z["held"])
        combos = [tuple(int(v) for v in s.split("|")) for s in z["combos"]]
        print("load %s n=%d" % (f, len(z["ts"])), flush=True)
    ts = np.concatenate(ts_l); g = np.concatenate(g_l).astype(np.float64)
    P = np.concatenate(p_l, axis=0); Hd = np.concatenate(h_l, axis=0)
    o = np.argsort(ts, kind="stable")
    ts, g, P, Hd = ts[o], g[o], P[o], Hd[o]
    gg = pd.read_csv(a.gate_csv, usecols=["ts", "predRisk4H"])
    gg["min"] = gg["ts"] // 60000
    gmin = gg.groupby("min")["predRisk4H"].first()
    q10 = float(gmin.quantile(0.10)); q90 = float(gmin.quantile(0.90))
    fin = np.isfinite(g)
    keep = {"A_all": np.ones(len(ts), bool), "B_CHAN_q10": ~(g <= q10),
            "C_THUAN_q90": (g >= q90), "D_NGHICH_q10": (g <= q10)}
    res = {"prereg": "PREREG_SHORT_FULLCHAIN", "cost_base": S.COST_BASE, "fund72": S.FUND72,
           "gate": {"q10": q10, "q90": q90}, "n_pick_total": int(len(ts)),
           "nan_gate_frac": round(float((~fin).mean()), 5),
           "picks_ts_range": [int(ts.min()), int(ts.max())], "variants": {}}
    for vn, m in keep.items():
        m = m & fin
        blk = {"n_pick": int(m.sum()), "frac": round(float(m.mean()), 4), "grid": {}}
        for j, c in enumerate(combos):
            key = "T%d_SL%d_TS%dh" % (c[0], c[1], c[2])
            blk["grid"][key] = S.agg(P[m, j], Hd[m, j], ts[m])
        res["variants"][vn] = blk
        print("VARIANT %s n=%d" % (vn, blk["n_pick"]), flush=True)
    go = []
    for vn in keep:
        for k, r in res["variants"][vn]["grid"].items():
            if r["net"] is not None and r["net"] > 0 and r["out_both"] and r["years_pos"] >= 3:
                go.append([vn, k, r["net"], r["years_pos"]])
    res["go_configs"] = go
    # bang gon cho bao cao: voi moi variant, liet ke 18 to hop
    for vn in keep:
        print("\n== %s (n=%d, frac=%.3f) ==" % (vn, res["variants"][vn]["n_pick"],
                                                res["variants"][vn]["frac"]))
        for k, r in res["variants"][vn]["grid"].items():
            lbl = k + (" (SL=100 no-stop)" if "_SL100_" in k else "")
            print("  %-24s net=%+.4f%% CI[%+.4f,%+.4f] out=%s win=%.1f%% held=%.1fh tail=%+.1f%% yr=%s ypos=%d"
                  % (lbl, 100 * r["net"], 100 * r["ci_raw"][0], 100 * r["ci_raw"][1], r["out_both"],
                     100 * r["winrate"], r["mean_held_h"], 100 * r["max_loss"],
                     r["by_year"], r["years_pos"]))
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("\nGO configs:", go, flush=True)
    print("JSON ->", a.out, flush=True)


if __name__ == "__main__":
    main()
