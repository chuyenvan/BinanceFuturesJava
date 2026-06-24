#!/usr/bin/env python3
"""TASK-109 validate B: so P(win) Java (set generate) vs Python (predict_202401.bin) tai (ts,symId) chung, ngay 20240115."""
import numpy as np, pandas as pd

OUT_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4", 4)])  # 26B
HOR = ["p4h", "p12h", "p24h", "p72h"]

# 1) Python baseline: doc predict_202401.bin, loc ngay 20240115 (GMT+7: 20240115 00:00 -> 20240116 00:00 UTC+7)
a = np.fromfile("D:/claudedata/sel_validate_b/predict_202401.bin", dtype=OUT_DT)
py = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
for j, h in enumerate(HOR):
    py[h + "_py"] = a["p"][:, j].astype(np.float32)
# range 20240115 07:00 GMT+7 = 20240115 00:00 UTC -> +1 day. Java export dung start+7h GMT+7.
# Java CSV ts la epoch ms. Loc py theo cung range ts cua java.

# 2) Java
jv = pd.read_csv("D:/claudedata/sel_validate_b/sel_java_20240115.csv")
jv = jv.rename(columns={"p4h": "p4h_jv", "p12h": "p12h_jv", "p24h": "p24h_jv", "p72h": "p72h_jv"})
tmin, tmax = jv.ts.min(), jv.ts.max()
print(f"Java: {len(jv)} rows | ts[{tmin}..{tmax}] | {jv.symId.nunique()} symId")

py = py[(py.ts >= tmin) & (py.ts <= tmax)]
print(f"Python (cung range): {len(py)} rows | {py.symId.nunique()} symId")

# 3) merge theo (ts,symId) chung
m = pd.merge(jv, py, on=["ts", "symId"], how="inner")
print(f"Giao (ts,symId) chung: {len(m)} rows")
if len(m) == 0:
    print("KHONG co diem chung — kiem tra ts/symId khop khong"); raise SystemExit

# 4) so tung horizon
print("\n=== DIFF Java vs Python P(win) ===")
allmax = 0.0
for h in HOR:
    d = (m[h + "_jv"] - m[h + "_py"]).abs()
    # bo NaN ca 2 phia
    mask = m[h + "_jv"].notna() & m[h + "_py"].notna()
    dd = d[mask]
    nan_jv = m[h + "_jv"].isna().sum(); nan_py = m[h + "_py"].isna().sum()
    mx = dd.max() if len(dd) else float("nan")
    allmax = max(allmax, mx if not np.isnan(mx) else 0)
    print(f"{h}: n={mask.sum()} | max|diff|={mx:.8f} | mean|diff|={dd.mean():.8f} | NaN jv={nan_jv} py={nan_py}")

print(f"\n>>> MAX DIFF toan bo = {allmax:.8f}")
print(">>> " + ("KHOP ~0 (PASS)" if allmax < 1e-4 else "LECH (FAIL) — can dieu tra"))

# sample vai dong lech nhat
m["maxd"] = m[[h+"_jv" for h in HOR]].sub(m[[h+"_py" for h in HOR]].values).abs().max(axis=1)
print("\nTop 5 dong lech nhat:")
print(m.nlargest(5, "maxd")[["ts", "symId"] + [c for h in HOR for c in (h+"_jv", h+"_py")] + ["maxd"]].to_string())
