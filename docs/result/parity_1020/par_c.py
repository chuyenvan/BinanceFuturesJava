#!/usr/bin/env python3
import json, numpy as np, pandas as pd
W = "/home/ubuntu/claude_master/parity_1020"
A = json.load(open(W + "/par_a.json")); B = json.load(open(W + "/par_b.json"))
D1 = json.load(open(W + "/diag1.json")); D4 = json.load(open(W + "/diag4.json")); D5 = json.load(open(W + "/diag5.json"))
F32 = np.float32
DYN_MIN, SB, DM, GS = F32(0.26787), F32(0.15), F32(1.28760), F32(1.55)
extra = {}
for mode in ("T", "E35"):
    R = pd.read_csv(W + "/out_s1_%s.csv.gz" % mode).dropna(subset=["gv_off"])
    fac_l = np.maximum(DYN_MIN, R.gv_live.astype(F32) / SB * DM).astype(F32)
    fac_o = np.maximum(DYN_MIN, R.gv_off.astype(F32) / SB * DM).astype(F32)
    thr_l = (R.q.astype(F32) * fac_l * GS).astype(F32); thr_o = (R.q.astype(F32) * fac_o * GS).astype(F32)
    pl = ~(R.p15.astype(F32) < thr_l); po = ~(R.p15_off.astype(F32) < thr_o)
    rq_o = (R.p15_off / (fac_o * GS)) / R.q
    ml = (R.p15 - thr_l).abs() / thr_l; mo = (R.p15_off - thr_o).abs() / thr_o
    fl = pl != po
    extra[mode] = dict(n=int(len(R)), pass_live=int(pl.sum()), pass_bt=int(po.sum()), flips=int(fl.sum()),
                       flips_heavy=int((fl & ((ml > .01) | (mo > .01))).sum()), max_rq_bt=float(rq_o.max()),
                       thr_rel=dict(med=float(((thr_l - thr_o).abs() / thr_o).median()), p99=float(((thr_l - thr_o).abs() / thr_o).quantile(.99)),
                                    max=float(((thr_l - thr_o).abs() / thr_o).max())))
json.dump(extra, open(W + "/par_c_fullbt_gate.json", "w"), indent=1)
print(json.dumps(extra, indent=1))
