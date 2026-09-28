#!/usr/bin/env python3
"""BUOC 0 (OFI_MONEY_REORIENT) — XAC NHAN CHIEU DIEM, KHONG tinh ket qua tien.
Tren pool P32 (rank 0 = S1 tot nhat): corr(score, rank_pool) + mean pool-rank cua top-8 theo 2 chieu
(argsort(-score) = chieu CU; argsort(+score) = chieu SUA) cho 3 doi tuong, ensemble 43/44/45 + tung seed.
"""
import json, os, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr
W = "/home/ubuntu/claude_audit_0928/ofirx"
LABEL = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
KMAP = {"candidate": "pred_ofi_candidate_v2.parquet", "baseline_fresh": "pred_baseline_fresh.parquet",
        "noise_ofi_check": "pred_ofi_noise_v2.parquet"}
d = pd.read_parquet(LABEL, columns=["ts", "symId", "rank"]).sort_values(["ts", "rank"], kind="stable").reset_index(drop=True)
nt = d.ts.nunique(); NS = 32
R = d["rank"].to_numpy().reshape(nt, NS)
key = d[["ts", "symId"]]
out = {}
for arm, fn in KMAP.items():
    acc = None
    for s in (42, 43, 44, 45):
        p = pd.read_parquet(os.path.join(W, "kout%d" % s, fn), columns=["ts", "sym", "score"]).rename(columns={"sym": "symId"})
        m = key.merge(p, on=["ts", "symId"], how="left")
        assert m.score.notna().all()
        v = m.score.to_numpy(np.float64).reshape(nt, NS)
        if s != 42:
            acc = v if acc is None else acc + v
        for tag, S in ([("s%d" % s, v)] + ([("ens434445", acc / 3)] if s == 45 else [])):
            rho = np.nanmean([spearmanr(S[i], R[i]).correlation for i in range(0, nt, 10)])
            pear = float(np.corrcoef(S.reshape(-1), R.reshape(-1))[0, 1])
            top_old = np.take_along_axis(R, np.argsort(-S, axis=1, kind="stable")[:, :8], 1).mean()
            top_new = np.take_along_axis(R, np.argsort(S, axis=1, kind="stable")[:, :8], 1).mean()
            out["%s|%s" % (arm, tag)] = {"spearman_tick_mean(score,rank)": round(float(rho), 4),
                                         "pearson(score,rank)": round(pear, 4),
                                         "meanrank_top8_argsort(-score)_OLD": round(float(top_old), 3),
                                         "meanrank_top8_argsort(+score)_NEW": round(float(top_new), 3)}
            print("%-16s %-10s rho=%+.4f pear=%+.4f  top8 OLD=%.3f NEW=%.3f" % (arm, tag, rho, pear, top_old, top_new), flush=True)
json.dump(out, open(os.path.join(W, "step0_orient.json"), "w"), indent=1)
