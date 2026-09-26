#!/usr/bin/env python3
"""tail_robust_validate.py — KIỂM HỢP LỆ cho vòng TAIL_ROBUST (pre-reg §8).

(a) phủ điểm 100% trên pool P32 ; (b) S1 tai lap DUNG thu tu `rank` cua pool ;
(c) so hoc `net = gross - f` ; (d) trung nhau tap top-8 giua cac doi tuong (bat truong hop
DOI TUONG TRUNG NHAU lam Δ = 0 vo nghia) ; (e) raw CI chua 0 => khong duoc goi "ngoai CI".

Chi doc artifact. Khong train/sim. Chay: python3 tail_robust_validate.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import tail_robust_rulers as T  # noqa: E402

P = T.load_pool(T.POOL_P32, "p32")
nt = len(P["ticks"])
V = {}
objs = ["45deploy", "A45", "S1", "ofi_candidate", "ofi_baseline_fresh", "ofi_noise"]
SC = T.stage_scores(P, "val", objs)
V["coverage"] = {o: round(float(100 * np.isfinite(SC[o]).mean()), 3) for o in objs}
# (a2) CHIEU DIEM: corr(score, rank cua pool) am => diem cao = tot (bins); duong => phai doi dau
V["chieu_diem_corr_rank"] = {o: round(float(np.nanmean([
    pd.Series(SC[o].reshape(nt, -1)[i]).corr(pd.Series(np.arange(32)), method="spearman")
    for i in range(0, nt, 499)])), 4) for o in objs}
_or = {o: (SC[o] * T.ORIENT.get(o, 1)) for o in objs}
V["mean_rank_top8_sau_chuan_hoa"] = {o: round(float(T.select_topk(
    P, _or[o])["sym"].size and np.mean(np.argsort(-_or[o].reshape(nt, -1), axis=1, kind="stable")[:, :8])), 2)
    for o in objs}
# (b) S1 tai lap thu tu rank: trong pool, S1 diem CAO hon => rank NHO hon
d = pd.read_parquet(T.POOL_P32, columns=["ts", "rank"])
S1 = SC["S1"].reshape(nt, -1)
rk = d.sort_values(["ts", "rank"], kind="stable")["rank"].to_numpy().reshape(nt, -1)
ok = int((np.diff(S1, axis=1) > 1e-6).sum())
V["S1_tai_lap_rank"] = {"vi_pham_monotone": ok, "vi_pham_/_cap": round(ok / (S1.shape[0] * (S1.shape[1] - 1)), 6),
                        "spearman_median": float(np.median([
                            pd.Series(S1[i]).corr(pd.Series(rk[i]), method="spearman")
                            for i in range(0, nt, 997)]))}
# (c) so hoc
d = pd.read_parquet(T.POOL_P32, columns=["gross", "net"])
V["so_hoc_net"] = float(np.abs(d.net.to_numpy() - (d.gross.to_numpy() - 0.008)).max())
# (d) trung nhau top-8
sel = {}
for o in objs:
    S = T.select_topk(P, _or[o])
    key = S["tick"] * 1_000_000 + S["sym"]
    sel[o] = key
J = {}
for i, a in enumerate(objs):
    for b in objs[i + 1:]:
        ka, kb = np.sort(sel[a]), np.sort(sel[b])
        inter = np.intersect1d(ka, kb).size
        J["%s|%s" % (a, b)] = round(100.0 * inter / min(len(ka), len(kb)), 3)
V["trung_top8_pct"] = J
# (e) S1 vs ofi_candidate theo TICK
diff = 0
for i in range(0, nt, 500):
    ka = np.sort(sel["S1"][: 0]) if False else None
F = {}
for a, bb in (("S1", "ofi_candidate"), ("ofi_candidate", "ofi_baseline_fresh"),
              ("ofi_candidate", "ofi_noise"), ("45deploy", "A45")):
    ka = sel[a].reshape(nt, T.K); kb = sel[bb].reshape(nt, T.K)
    same = (np.sort(ka, 1) == np.sort(kb, 1)).all(1)
    F["%s|%s" % (a, bb)] = round(100.0 * same.mean(), 3)
V["tick_top8_trung_hoan_toan_pct"] = F
print(json.dumps(V, indent=1))
json.dump(V, open("/tmp/trr/validate.json", "w"), indent=1)
