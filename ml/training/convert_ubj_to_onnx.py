#!/usr/bin/env python3
"""
TASK-109 buoc 1: convert 4 model selector .ubj (XGBClassifier binary:logistic) -> ONNX,
de Java doc qua onnxruntime (giong gate). Verify .ubj predict_proba == ONNX predict tren random input.

NHE: chi load 4 model ~1MB + random input, KHONG dung OI/Tool1 (tranh OOM local).
Output: model_<H>.onnx canh model_<H>.ubj. Input ONNX: float [None,45] ten 'float_input', output prob P(win).
"""
import os, sys, glob
import numpy as np

MODEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "E:/educa/source/github/20260415/BinanceFuturesJava/ml/funding_selector/models_v1"
HORIZONS = ["4h", "12h", "24h", "72h"]
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES
N = len(FEAT)
assert N == 45

import xgboost as xgb
from onnxmltools.convert.common.data_types import FloatTensorType
from onnxmltools.convert import convert_xgboost
import onnxruntime as ort

rng = np.random.default_rng(0)
Xtest = rng.standard_normal((200, N)).astype(np.float32)

for H in HORIZONS:
    ubj = os.path.join(MODEL_DIR, f"model_{H}.ubj")
    assert os.path.exists(ubj), f"thieu {ubj}"
    # load bang Booster (giong generate_predict.py): binary:logistic -> predict = sigmoid(margin) = P(win)
    bst = xgb.Booster()
    bst.load_model(ubj)
    orig_names = bst.feature_names
    if orig_names is not None:
        assert orig_names == FEAT, f"{H} feat mismatch: {orig_names[:3]} vs {FEAT[:3]}"
    # predict chuan THEO TEN goc (oi_z...) de dung thu tu
    dm_ref = xgb.DMatrix(Xtest, feature_names=orig_names if orig_names else None)
    proba_ref = bst.predict(dm_ref)  # P(win) cho binary:logistic
    # onnxmltools chi hieu ten f%d -> doi feature_names ve f0..f44 (chi doi TEN, gia tri/thu tu giu nguyen)
    bst.feature_names = [f"f{j}" for j in range(N)]

    # convert Booster sang ONNX
    onx = convert_xgboost(bst, initial_types=[("float_input", FloatTensorType([None, N]))])
    out_path = os.path.join(MODEL_DIR, f"model_{H}.onnx")
    with open(out_path, "wb") as f:
        f.write(onx.SerializeToString())

    # verify ONNX == .ubj
    sess = ort.InferenceSession(out_path, providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name
    outs = sess.run(None, {in_name: Xtest})
    # tim output prob: classifier ONNX thuong tra [label, prob_dict|prob_array]
    prob_onnx = None
    for o in outs:
        arr = np.asarray(o)
        if arr.ndim == 2 and arr.shape[1] == 2:
            prob_onnx = arr[:, 1]; break
        if isinstance(o, list) and o and isinstance(o[0], dict):
            prob_onnx = np.array([d.get(1, d.get("1", 0.0)) for d in o]); break
    if prob_onnx is None:
        # fallback: output cuoi cung
        prob_onnx = np.asarray(outs[-1]).ravel()
    diff = float(np.max(np.abs(proba_ref - prob_onnx)))
    print(f"{H}: input={in_name} outputs={[np.asarray(o).shape if not isinstance(o,list) else 'list' for o in outs]} | max|ubj-onnx|={diff:.8f} -> {out_path}")
    assert diff < 1e-5, f"{H} LECH {diff} - convert sai"

print("OK: 4 model .ubj -> .onnx, verify khop < 1e-5")
