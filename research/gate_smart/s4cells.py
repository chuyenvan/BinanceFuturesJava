#!/usr/bin/env python3
"""GATE_SMART Pha 0b buoc 1 (prereg 6d92cdba §2.3): xuat o near-miss (0,8<=r/q<1, hop le, khong pass) va o pass [1;1,1) DEV, 8 seed.
Output ~/claude_master/gsmart/s4_cells.parquet (ts, sym, kind, n_seed). Khong PnL."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/ubuntu/claude_master/vz_e1_wt/research/analysis')
import gate_offline as GO
SEEDS = {"A1": "nt-x14-s42", "S7": "nt-x14-s7", "S13": "nt-x14-s13", "S21": "nt-x14-s21", "S99": "nt-x14-s99",
         "S123": "nt-x14-s123", "S777": "nt-x14-s777", "S2024": "nt-x14-s2024"}
DEV0, DEV1 = 1640970000000, 1767200400000
B = dict(np.load(GO.CACHE + "/cand_base.npz"))
mp = pd.read_csv(GO.MAPF)
s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
id2s = {v: k + "USDT" for k, v in s2id.items()}
out = []
for arm, tag in SEEDS.items():
    C = GO.build(arm, B, s2id, tag)
    G = GO.run_g2(C, J=1024)
    ts, P, r, qm, valid, SY = C["ts"], G["P"], G["r"], G["qm"], C["valid"], C["SY"]
    rq = r / qm[:, None]
    dev = ((ts >= DEV0) & (ts < DEV1))[:, None]
    for kind, m in (("near", valid & ~P & (rq >= 0.8) & (rq < 1.0) & dev), ("pass_low", P & (rq < 1.1) & dev)):
        i, c = np.nonzero(m)
        out.append(pd.DataFrame(dict(ts=ts[i], sid=SY[i, c].astype(int), kind=kind, seed=arm)))
    print(arm, {k: int((pd.concat(out[-2:]).kind == k).sum()) for k in ("near", "pass_low")}, flush=True)
    del C, G
A = pd.concat(out, ignore_index=True)
A["sym"] = A.sid.map(id2s)
X = A.groupby(["ts", "sym", "kind"]).seed.nunique().rename("n_seed").reset_index()
X.to_parquet("/home/ubuntu/claude_master/gsmart/s4_cells.parquet", index=False)
print(X.kind.value_counts().to_dict(), "unmapped", int(A.sym.isna().sum()))
