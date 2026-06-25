#!/usr/bin/env python3
"""TASK-109 v2 — So 45 FEATURE Java generate (sel_feat_v2.csv) vs data TRAIN v2 (ff hien tai + oi 226).
Khong con dung ff Kaggle stale. Chung minh generate Java == data train -> validate pass.
"""
import numpy as np, pandas as pd, gzip

FF = "/home/ubuntu/claudedata/train_ff/features_20240101_to_20240401.bin.gz"
OI = "/home/ubuntu/java/simulator/features_oi_percoin_v1/oi_percoin_20210101_to_20260624.bin.gz"
SYMMAP = "/home/ubuntu/claudedata/feat/symbol_map.csv"
JAVA_DUMP = "/home/ubuntu/claudedata/sel_feat_v2.csv"

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
OI_TOL_MS = 2 * 60 * 60 * 1000

sm = pd.read_csv(SYMMAP)
s2id = dict(zip(sm.symbol, sm.symId))

jv = pd.read_csv(JAVA_DUMP, header=None, names=["ts", "symbol"] + FEAT)
jv["symId"] = jv["symbol"].map(s2id).astype("Int64")
jv = jv.dropna(subset=["symId"])
jv["symId"] = jv["symId"].astype(np.int32)
tmin, tmax = int(jv.ts.min()), int(jv.ts.max())
print(f"Java dump: {len(jv)} rows | ts[{tmin}..{tmax}] | {jv.symId.nunique()} symId")

_raw = open(FF, "rb").read()
if FF.endswith(".gz"): _raw = gzip.decompress(_raw)
a = np.frombuffer(_raw, dtype=TOOL1_DT)
t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
F = np.asarray(a["f"], dtype=np.float32)
for j in range(40):
    t[f"f{j}"] = F[:, j]
t = t[(t.ts >= tmin) & (t.ts <= tmax)].sort_values("ts").reset_index(drop=True)
print(f"Python ff train (range): {len(t)} rows")

_oraw = open(OI, "rb").read()
if OI.endswith(".gz"): _oraw = gzip.decompress(_oraw)
o = np.frombuffer(_oraw, dtype=OI_DT)
# loc range ngay test TRUOC (tranh OOM 138M rows): lay tu tmin-3h de phu tolerance
ots = o["ts"].astype(np.int64)
omask = (ots >= tmin - 3 * 3600 * 1000) & (ots <= tmax)
o = o[omask]
oi = pd.DataFrame({"ts": o["ts"].astype(np.int64), "symId": o["sym"].astype(np.int32)})
O = np.asarray(o["oi"], dtype=np.float32)
for j, nm in enumerate(OI_NAMES):
    oi[nm] = O[:, j]
oi = oi.sort_values("ts").reset_index(drop=True)
merged = pd.merge_asof(t, oi, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
print(f"Python merged: {len(merged)} rows")

jv2 = jv[["ts", "symId"] + FEAT].add_suffix("_jv").rename(columns={"ts_jv": "ts", "symId_jv": "symId"})
py2 = merged[["ts", "symId"] + FEAT].add_suffix("_py").rename(columns={"ts_py": "ts", "symId_py": "symId"})
m = pd.merge(jv2, py2, on=["ts", "symId"], how="inner")
print(f"Giao chung: {len(m)} rows\n")

print("=== DIFF tung feature (Java generate vs Python train) ===")
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

print("\n=== TOP 8 lech nhat ===")
for mx, f, mn, nj, npy, flag in sorted(worst, reverse=True)[:8]:
    print(f"{f:16s} max={mx:.6f} mean={mn:.6f} NaN jv={nj} py={npy}")
