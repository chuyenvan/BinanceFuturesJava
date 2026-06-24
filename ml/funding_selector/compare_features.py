#!/usr/bin/env python3
"""TASK-109 — So 45 FEATURE Java (dump) vs Python (ff_202401 + oi merge_asof) tai (ts,symId) chung.
Chi ra CHINH XAC cot feature nao lech -> khoanh vung nguyen nhan P(win) lech.
Chay tren Oracle (co ff+oi). Java dump: ts,symbol,f0..f44 (symbol la string -> map sang symId qua symbol_map).
"""
import numpy as np, pandas as pd, sys

FF = "/home/ubuntu/claudedata/feat/ff_202401.bin"
OI = "/home/ubuntu/claudedata/feat/oi_percoin_full.bin"
SYMMAP = "/home/ubuntu/claudedata/feat/symbol_map.csv"
JAVA_DUMP = "/home/ubuntu/claudedata/sel_feat_java.csv"

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
OI_TOL_MS = 2 * 60 * 60 * 1000

# symbol_map: symbol -> symId
sm = pd.read_csv(SYMMAP)
col = sm.columns.tolist()
print("symbol_map cols:", col)
# doan cot: thuong [symbol, id] hoac [symId, symbol]
if "symbol" in sm.columns and "symId" in sm.columns:
    s2id = dict(zip(sm.symbol, sm.symId))
else:
    s2id = dict(zip(sm.iloc[:, 1], sm.iloc[:, 0])) if sm.iloc[:, 0].dtype.kind in "iu" else dict(zip(sm.iloc[:, 0], sm.iloc[:, 1]))

# 1) Java dump -> df
jv = pd.read_csv(JAVA_DUMP, header=None, names=["ts", "symbol"] + FEAT)
jv["symId"] = jv["symbol"].map(s2id).astype("Int64")
jv = jv.dropna(subset=["symId"])
jv["symId"] = jv["symId"].astype(np.int32)
tmin, tmax = int(jv.ts.min()), int(jv.ts.max())
print(f"Java dump: {len(jv)} rows | ts[{tmin}..{tmax}] | {jv.symId.nunique()} symId")

# 2) Python: ff_202401 (loc range java) + merge oi
a = np.fromfile(FF, dtype=TOOL1_DT)
t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
F = np.asarray(a["f"], dtype=np.float32)
for j in range(40):
    t[f"f{j}"] = F[:, j]
t = t[(t.ts >= tmin) & (t.ts <= tmax)].sort_values("ts").reset_index(drop=True)
print(f"Python ff (range): {len(t)} rows")

o = np.fromfile(OI, dtype=OI_DT)
oi = pd.DataFrame({"ts": o["ts"].astype(np.int64), "symId": o["sym"].astype(np.int32)})
O = np.asarray(o["oi"], dtype=np.float32)
for j, nm in enumerate(OI_NAMES):
    oi[nm] = O[:, j]
oi = oi.sort_values("ts").reset_index(drop=True)
merged = pd.merge_asof(t, oi, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
print(f"Python merged: {len(merged)} rows")

# 3) merge Java vs Python theo (ts,symId)
jv2 = jv[["ts", "symId"] + FEAT].add_suffix("_jv").rename(columns={"ts_jv": "ts", "symId_jv": "symId"})
py2 = merged[["ts", "symId"] + FEAT].add_suffix("_py").rename(columns={"ts_py": "ts", "symId_py": "symId"})
m = pd.merge(jv2, py2, on=["ts", "symId"], how="inner")
print(f"Giao chung: {len(m)} rows\n")

# 4) so tung feature -> cot nao lech
print("=== DIFF tung feature (Java vs Python) ===")
worst = []
for f in FEAT:
    a_, b_ = m[f + "_jv"], m[f + "_py"]
    mask = a_.notna() & b_.notna()
    d = (a_[mask] - b_[mask]).abs()
    nan_jv, nan_py = a_.isna().sum(), b_.isna().sum()
    mx = d.max() if len(d) else 0.0
    mn = d.mean() if len(d) else 0.0
    flag = " <<< LECH" if (mx > 1e-3 or nan_jv != nan_py) else ""
    worst.append((mx, f, mn, nan_jv, nan_py, flag))
    print(f"{f:16s}: max={mx:.6f} mean={mn:.6f} NaN(jv={nan_jv},py={nan_py}){flag}")

print("\n=== TOP 8 feature lech nhat ===")
for mx, f, mn, nj, npy, flag in sorted(worst, reverse=True)[:8]:
    print(f"{f:16s} max={mx:.6f} mean={mn:.6f} NaN jv={nj} py={npy}")
