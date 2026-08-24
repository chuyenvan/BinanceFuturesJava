#!/usr/bin/env python3
"""
WFO fold trainer — train XGBoost gate tới CUTOFF (expanding) -> ONNX. Gọi bởi WFOGateRunner (Java).

ĐỒNG BỘ (tránh lệch ngầm): feature đọc theo ĐÚNG thứ tự V3FULL (KHÓA cứng), KHÔNG theo thứ tự cột CSV.
CSV do WFOGateRunner xuất: cột [timestamp, <33 feature theo MarketFeatures.toCSVRow order>, label_oldbasket].
KHÔNG scaler (XGBoost bất biến scale; OnnxInferenceManager chạy raw). Tham số model = bản final đã chốt.

Env: DATA (csv feature store), CUTOFF (yyyymmdd), OUT_DIR (chứa Model_Regressor_Return15M.onnx)
"""
import os
import numpy as np, pandas as pd
from xgboost import XGBRegressor
from skl2onnx.common.data_types import FloatTensorType
from onnxmltools.convert import convert_xgboost
from scipy.stats import spearmanr

DATA = os.environ["DATA"]
CUTOFF = os.environ["CUTOFF"]
OUT_DIR = os.environ["OUT_DIR"]
os.makedirs(OUT_DIR, exist_ok=True)

# Thứ tự V3FULL — COPY CHÍNH XÁC từ OnnxInferenceManager.extractFeaturesV3Full (33 feat). Nguồn sự thật.
V3FULL = [
    "momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
    "trendStrengthETH","trendConsistency",
    "volatility1M","volatility15M","volatility1H","volatility24H","volatilityTermStructure",
    "advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength","btcDominance",
    "rsi14","volumeSpike","distMA20",
    "fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
    "hourOfDay","dayOfWeek","weekOfMonth","monthOfYear",
    "basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike",
]
assert len(V3FULL) == 33
GATE_PURGE_MS = int(os.environ.get("GATE_PURGE_MS", "0"))
LABEL = os.environ.get("GATE_LABEL", "label_oldbasket")

df = pd.read_csv(DATA)
missing = [c for c in V3FULL if c not in df.columns]
assert not missing, f"CSV THIEU feature V3Full: {missing}"
assert LABEL in df.columns, f"CSV THIEU cot label: {LABEL}"

cut = pd.Timestamp(f"{CUTOFF[:4]}-{CUTOFF[4:6]}-{CUTOFF[6:]}").value // 10**6
tr_cut = cut - GATE_PURGE_MS
n_pre = int((df.timestamp < cut).sum())
tr = df[df.timestamp < tr_cut]
print(f"fold cutoff={CUTOFF} label={LABEL} purge_ms={GATE_PURGE_MS} "
      f"train_rows_pre_purge={n_pre} post_purge={len(tr)}")
if len(tr) == 0:
    print(f"SKIP fold cutoff={CUTOFF}: 0 train rows sau purge {GATE_PURGE_MS}ms")
    raise SystemExit(0)
assert tr.timestamp.max() < tr_cut, \
    f"LEAK: tr.timestamp.max()={tr.timestamp.max()} >= tr_cut={tr_cut}"
if len(tr) < 1000:
    raise SystemExit(f"❌ train rows {len(tr)} < 1000 — cutoff {CUTOFF} quá sớm")

Xtr = tr[V3FULL].values.astype(np.float32)
ytr = tr[LABEL].values.astype(np.float32)

model = XGBRegressor(objective="reg:squarederror", max_depth=4, n_estimators=150,
                     learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                     min_child_weight=10, random_state=42, n_jobs=4)
model.fit(Xtr, ytr)

ic_is = spearmanr(model.predict(Xtr), ytr).correlation
print(f"fold cutoff={CUTOFF} train_rows={len(tr)} in-sample IC={ic_is:.4f}")

onx = convert_xgboost(model, initial_types=[("float_input", FloatTensorType([None, 33]))])
out_path = os.path.join(OUT_DIR, "Model_Regressor_Return15M.onnx")
with open(out_path, "wb") as f:
    f.write(onx.SerializeToString())
print(f"Export -> {out_path}")
