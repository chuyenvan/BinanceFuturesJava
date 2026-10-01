#!/usr/bin/env python3
"""short_pathexit_sim_pw_drive.py — driver GOI NGUYEN ham cua short_pathexit_sim.py (khong sua file dung chung).

Khac duy nhat ve BO NHO (khong doi logic/so):
  - nhan .pb CHI nap 72h (main() nap ca 12h/24h/72h) -> giam peak RAM.
  - BO sweep_pb (khong can cho vong nay).
Moi cong thuc (pick top-8, entry open15m+14, LABEL/CUT/TRAIL/NOSTOP, cost, funding, CI block-72h,
theo nam) giu NGUYEN y ban goc.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/ml/lib")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import short_pathexit_sim as S  # noqa: E402

FOLDS = ("20220101,20220401,20220701,20221001,20230101,20230401,20230701,20231001,"
         "20240101,20240401,20240701,20241001,20250101,20250401,20250701,20251001").split(",")
BINS = "/home/ubuntu/sm_pwsoft"
LAB = "/home/ubuntu/ds_label15m"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
OUT = "/home/ubuntu/src/BinanceFuturesJava/docs/result/RESULT_SHORT_PATHEXIT_PSOFT.json"
ARMS = [("PW_t15_E10_S42", "sm/PW_t15_E10_S42"), ("PW_t15_E10_S7", "sm/PW_t15_E10_S7"),
        ("PW_t15_E10_S13", "sm/PW_t15_E10_S13")]
THRE = {"PW_t15_E10_S42": (0.015, 0.10), "PW_t15_E10_S7": (0.015, 0.10),
        "PW_t15_E10_S13": (0.015, 0.10)}

t0 = time.time()
lbl = S.load_labels(LAB, MAP, ("72h",))
print("labels %d (%.0fs)" % (len(lbl["key"]), time.time() - t0), flush=True)
smap = pd.read_csv(MAP)
id2name = dict(zip(smap.symId.astype(int), smap.symbol))

res = {"k_sel": S.K_SEL, "cost_base": S.COST_BASE, "fund72": S.FUND72,
       "prereg": "PREREG_SHORT_PATHEXIT_PSOFT", "labels_hs": "72h", "arms": {}}
picks = {}
for tag, dirp in ARMS:
    d = os.path.join(BINS, dirp)
    pk = S.build_picks(tag, d, FOLDS, lbl)
    pk = pk[(pk["ts"] + 72 * S.H) <= S.DEV_END_MS].reset_index(drop=True)
    picks[tag] = pk
    te = THRE[tag]
    res["arms"][tag] = {"n_pick": int(len(pk)), "thr": te[0], "E": te[1]}
    print("arm %s picks %d" % (tag, len(pk)), flush=True)

# pb rules (CUT20/30, LABEL, NOSTOP) + cross-check tren cung pick
for tag, _ in ARMS:
    pk = picks[tag]
    te = THRE[tag]
    d, info = S.pb_rules(pk, lbl, te[0], te[1], "72h")
    ts = pk["ts"].to_numpy()
    res["arms"][tag]["pb72"] = {r: S.agg_rule(v[0], ts, v[1]) for r, v in d.items()}
    res["arms"][tag]["pb72_info"] = info

# sim 1m
need = sorted({int(s) for pk in picks.values() for s in pk["sym"].to_numpy()})
print("sim: %d syms, %d picks" % (len(need), sum(len(p) for p in picks.values())), flush=True)
outp = S.sim_1m(picks, id2name, need, "127.0.0.1:3222", [2022, 2023, 2024, 2025], THRE)
for tag in outp:
    res["arms"][tag]["sim1m"] = {}
    for rule in ("CUT", "LABEL", "TRAIL", "NOSTOP"):
        recs = outp[tag][rule]
        if not recs:
            continue
        m0 = np.array([r[0] for r in recs], np.int64)
        ts = m0 * 60000
        pnl = np.array([r[1] for r in recs], np.float64)
        held = np.array([r[2] for r in recs], np.float64)
        reason = [r[3] for r in recs]
        ag = S.agg_rule(pnl, ts, held, "prorata")
        ag["reason_frac"] = {k: round(reason.count(k) / len(reason), 4) for k in set(reason)}
        sym_a = np.array([r[4] for r in recs], np.int32)
        kk = (m0 - 14) * 60000 * S.RES + sym_a.astype(np.int64)
        ipp = np.clip(np.searchsorted(lbl["key"], kk), 0, len(lbl["key"]) - 1)
        hitm = lbl["key"][ipp] == kk
        if hitm.any():
            ag["pb_ret_same_mean"] = round(float(lbl["retEnd_72h"][ipp[hitm]].astype(np.float64).mean()), 6)
            ag["pb_maxfav_same_mean"] = round(float(lbl["maxFav_72h"][ipp[hitm]].astype(np.float64).mean()), 6)
            ag["pb_cutfrac20_same"] = round(float((lbl["maxFav_72h"][ipp[hitm]] >= 0.20).mean()), 6)
            ag["pb_cut20_same_mean"] = round(float(np.where(
                lbl["maxFav_72h"][ipp[hitm]] >= 0.20, -0.20,
                -lbl["retEnd_72h"][ipp[hitm]].astype(np.float64)).mean()), 6)
        res["arms"][tag]["sim1m"][rule] = ag

json.dump(res, open(OUT, "w"), indent=1, default=str)
print("JSON -> %s (%.0fs)" % (OUT, time.time() - t0), flush=True)
