#!/usr/bin/env python3
"""AUDIT LONG_LEVERS 2026-10-02 — counterfactual tuyen tinh (mo ta) cho pyramiding-tai-arm / partial-TP-tai-arm tren B0.
Gia dinh: leg them (hoac phan chot) co cung notional lenh goc, vao/chot tai gia arm = entry*1.07, thoat cung gia tp cua lenh.
Pyramid: dPnL_i = N_i*((tp/(1.07*entry)) - 1 - COST);  Partial-TP 50% tai arm: dPnL_i = 0.5*N_i*(0.07 - (tp/entry-1)).
Chi lenh TS_armed (STOP_MARKET_DONE). Bo qua: gioi han ngan sach, khop that tai arm (slip), lai kep. CI block-72h.
"""
import json, sys
import numpy as np, pandas as pd
d = pd.read_csv("/home/ubuntu/kaggle_sim/out/de-p1/storage/printDone.csv")
d["t0"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M"); d["N"] = d.quantity * d.entry
d["blk"] = ((d.t0 - pd.Timestamp("2021-07-01")).dt.total_seconds() // (72 * 3600)).astype(int)
COST = 0.000982 + 2 * 0.000067
a = d[d.status == "STOP_MARKET_DONE"].copy()
a["pyr"] = a.N * (a.tp / (1.07 * a.entry) - 1 - COST)
a["ptp"] = 0.5 * a.N * (0.07 - (a.tp / a.entry - 1))
rng = np.random.default_rng(20260905); R = {"n_armed": int(len(a))}
for k in ("pyr", "ptp"):
    s = a.groupby("blk")[k].sum().values
    bs = [s[rng.integers(0, len(s), len(s))].sum() for _ in range(2000)]
    R[k] = [float(a[k].sum()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    R[k + "_frac_pos"] = float((a[k] > 0).mean())
    R[k + "_top27_share"] = float(a[k].nlargest(27).sum() / a[k].sum()) if a[k].sum() != 0 else None
R["armed_profit_quantiles"] = a.profit.quantile([.1, .25, .5, .75, .9, .95, .99]).round(2).to_dict()
R["sum_pnl"] = float(d.pnl.sum())
print(R)
json.dump(R, open(sys.argv[1], "w"), indent=1, default=str)
