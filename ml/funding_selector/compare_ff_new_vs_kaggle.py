#!/usr/bin/env python3
"""So ff Java MOI (ExportFeaturesForPythonTool chay lai ngay test) vs ff_202401.bin Kaggle.
Muc dich: xac dinh ff_202401.bin Kaggle co phai chuan hien tai khong (f15 basketRsi14).
Neu KHOP -> pipeline ff on dinh, generate tool lech. Neu KHAC -> ff Kaggle stale.
"""
import numpy as np, pandas as pd, glob, gzip

TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
FEAT = [f"f{j}" for j in range(40)]

def read_ff(path):
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    a = np.frombuffer(raw, dtype=TOOL1_DT)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    return df

# ff Java moi (verify)
new_files = glob.glob("/home/ubuntu/claudedata/ff_verify/*.bin.gz") + glob.glob("/home/ubuntu/claudedata/ff_verify/*.bin")
print("ff verify files:", new_files)
new = read_ff(new_files[0])
# loc ngay test
lo, hi = 1705276800000, 1705363140000
new = new[(new.ts >= lo) & (new.ts <= hi)]
print(f"ff Java MOI: {len(new)} rows | ts[{new.ts.min()}..{new.ts.max()}]")

# ff Kaggle
kag = read_ff("/home/ubuntu/claudedata/feat/ff_202401.bin")
kag = kag[(kag.ts >= lo) & (kag.ts <= hi)]
print(f"ff Kaggle:   {len(kag)} rows")

m = pd.merge(new.add_suffix("_new").rename(columns={"ts_new":"ts","symId_new":"symId"}),
             kag.add_suffix("_kag").rename(columns={"ts_kag":"ts","symId_kag":"symId"}),
             on=["ts","symId"], how="inner")
print(f"Giao chung: {len(m)} rows\n")

print("=== DIFF ff Java MOI vs ff Kaggle (focus basket f12-f16) ===")
for f in FEAT:
    d = (m[f+"_new"] - m[f+"_kag"]).abs()
    mx, mn = d.max(), d.mean()
    flag = " <<<" if mx > 1e-3 else ""
    if f in [f"f{j}" for j in range(12,17)] or mx > 1e-3:
        print(f"{f:5s}: max={mx:.6f} mean={mn:.6f}{flag}")
print("\n>>> Neu f15 KHOP ~0 -> ff Kaggle = chuan, generate tool lech.")
print(">>> Neu f15 KHAC -> ff Kaggle STALE (sinh tu code cu).")
