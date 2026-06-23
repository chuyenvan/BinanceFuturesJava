#!/usr/bin/env python3
"""
TASK-043 — Train model gate 15m (return15M) ĐỒNG BỘ TUYỆT ĐỐI với OnnxInferenceManager + export ONNX.

ĐỒNG BỘ (tránh sai lệch ngầm — yêu cầu cốt lõi):
  - Feature đọc theo ĐÚNG thứ tự extractFeaturesV3Full của OnnxInferenceManager (33 feat), KHÔNG theo
    thứ tự cột CSV (CSV thứ tự khác -> nếu train theo CSV rồi generate theo V3Full sẽ LỆCH NGẦM).
  - KHÔNG scaler (XGBoost tree bất biến scale; OnnxInferenceManager thiếu file Scaler -> chạy raw, khớp).
  - Export tên file Model_Regressor_Return15M.onnx (đúng tên OnnxInferenceManager.SinglePredictor load).
  - Nhãn = label_oldbasket (thắng bước B). Train tới CUTOFF -> backtest OOS sau cutoff (B1, sạch in-sample).

Env: DATA, OUT_DIR (chua Model_Regressor_Return15M.onnx), CUTOFF=20250601
"""
import os, glob
import numpy as np, pandas as pd, xgboost as xgb
from xgboost import XGBRegressor
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from onnxmltools.convert import convert_xgboost
from scipy.stats import spearmanr

DATA = os.environ.get("DATA", os.path.expanduser("~/claudedata/gate15m_v2_full.csv"))
OUT_DIR = os.environ.get("OUT_DIR", os.path.expanduser("~/claudedata/gate_model_v2"))
CUTOFF = os.environ.get("CUTOFF", "20250601")
os.makedirs(OUT_DIR, exist_ok=True)

# THỨ TỰ V3FULL — COPY CHÍNH XÁC từ OnnxInferenceManager.extractFeaturesV3Full (33 feat).
# KHÓA cứng ở đây = nguồn sự thật duy nhất. Java generate cũng dùng đúng list này.
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
assert len(V3FULL) == 33, len(V3FULL)
LABEL = "label_oldbasket"

df = pd.read_csv(sorted(glob.glob(DATA))[0]).sort_values("timestamp").reset_index(drop=True)
# CSV CÓ fundingRateRaw? kiem (V3Full can no). Neu thieu -> bao loi RO RANG (tranh lech ngam).
missing = [c for c in V3FULL if c not in df.columns]
assert not missing, f"❌ CSV THIEU feature V3Full: {missing} — KHONG train (tranh lech ngam)"
print(f"rows={len(df)} | 33 feature V3Full khop CSV ✓")

cut = pd.Timestamp(f"{CUTOFF[:4]}-{CUTOFF[4:6]}-{CUTOFF[6:]}").value // 10**6
tr = df[df.timestamp < cut]
oos = df[df.timestamp >= cut]
print(f"train < {CUTOFF}: {len(tr)} rows | OOS >= cutoff: {len(oos)} rows")

Xtr = tr[V3FULL].values.astype(np.float32); ytr = tr[LABEL].values.astype(np.float32)
Xoos = oos[V3FULL].values.astype(np.float32); yoos = oos[LABEL].values.astype(np.float32)

# model NHO (right-size cho WFO sau): depth 4, 150 cay
model = XGBRegressor(objective="reg:squarederror", max_depth=4, n_estimators=150,
                     learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                     min_child_weight=10, random_state=42, n_jobs=4)
model.fit(Xtr, ytr)

# danh gia OOS (sanity: model co suc phan biet tren OOS?)
pred_oos = model.predict(Xoos)
ic_oos = spearmanr(pred_oos, yoos).correlation
print(f"\n=== OOS IC (sau cutoff, model CHUA thay) = {ic_oos:.4f} ===")
# in-sample de doi chieu
ic_is = spearmanr(model.predict(Xtr), ytr).correlation
print(f"   (in-sample IC = {ic_is:.4f} — chenh lech IS vs OOS cho biet overfit)")

# === EXPORT ONNX dong bo OnnxInferenceManager ===
# Model_Regressor_Return15M.onnx — input shape [N,33], output [N,1]
initial_type = [("float_input", FloatTensorType([None, 33]))]
onx = convert_xgboost(model, initial_types=initial_type)
out_path = os.path.join(OUT_DIR, "Model_Regressor_Return15M.onnx")
with open(out_path, "wb") as f:
    f.write(onx.SerializeToString())
print(f"\n✅ Export -> {out_path}")
print(f"   feature order = V3Full (33), input name 'float_input', KHONG scaler (raw feature)")

# ghi meta de truy vet
import json
json.dump(dict(label=LABEL, cutoff=CUTOFF, n_train=len(tr), n_oos=len(oos),
               ic_oos=round(float(ic_oos),4), ic_is=round(float(ic_is),4),
               feature_order=V3FULL, params=dict(max_depth=4, n_estimators=150, lr=0.05)),
          open(os.path.join(OUT_DIR,"train_meta.json"),"w"), indent=2)
print(f"   meta -> {OUT_DIR}/train_meta.json")
