#!/usr/bin/env python3
"""
Convert selector WFO (XGBoost binary:logistic, 45 feature) -> ONNX cho live
(FundingOnnxInferenceManager doc Funding_Classifier_Final.onnx).

Input : model_wfo_last_4h.ubj  (XGBoost booster, num_features=45)
Output: selector_wfo_4h.onnx    (output: label + probabilities[batch,2])

QUAN TRONG - parity da verify (2026-08-16):
  * 45 feature train order = f0..f39 (= ExportFeaturesForPythonTool.convertFeaturesToArray, 40 Tool1)
    + [oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy]  (5 OI, dung OI_NAMES).
    => KHOP CHINH XAC FundingOnnxInferenceManager.extractFeaturesToArray (#1..45).
  * probabilities[i][0] = P(no-pump), [i][1] = P(pump).
    Live dung preds[0]=P(no-pump), sort tang dan -> chon P(pump) cao nhat. DUNG CHIEU.
  * onnxmltools yeu cau feature name pattern f%d -> phai rename truoc convert
    (chi la nhan, index cay khong doi).
  * Parity xgb vs onnx: max|diff| ~ 4.5e-7.

Deploy (step 5, KHONG lam khi live dang chay model cu 21-input):
  1. Build jar tu branch module (co feature 21->45 + NUM_FEATURES=45).
  2. Copy selector_wfo_4h.onnx -> <run>/storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx tren 242.
  3. Restart v_t_m. (Atomic: jar moi + model moi cung luc.)
"""
import os
import numpy as np
import xgboost as xgb
from onnxmltools.convert import convert_xgboost
from onnxmltools.convert.common.data_types import FloatTensorType
import onnxruntime as ort

SRC = os.environ.get("SEL_UBJ", "model_wfo_last_4h.ubj")
DST = os.environ.get("SEL_ONNX", "selector_wfo_4h.onnx")

b = xgb.Booster()
b.load_model(SRC)
n = b.num_features()
assert n == 45, f"expect 45 feature, got {n}"

# onnxmltools can name f%d; rename (chi nhan, index khong doi)
b.feature_names = [f"f{i}" for i in range(n)]

onx = convert_xgboost(b, initial_types=[("input", FloatTensorType([None, n]))])
with open(DST, "wb") as f:
    f.write(onx.SerializeToString())

# --- verify parity ---
sess = ort.InferenceSession(DST)
rng = np.random.RandomState(7)
X = rng.randn(2000, n).astype(np.float32)
xp = b.inplace_predict(X)                                   # P(pump)
op = np.array(sess.run(None, {sess.get_inputs()[0].name: X})[1])[:, 1]
print("outputs:", [(o.name, o.shape) for o in sess.get_outputs()])
print("parity max|xgb-onnx|:", float(np.max(np.abs(xp - op))))
print("wrote:", DST, os.path.getsize(DST), "bytes")
