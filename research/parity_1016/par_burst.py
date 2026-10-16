#!/usr/bin/env python3
"""Cua so dot 10-08: p15 live vs offline quanh cac phut gate pass."""
import logging
import os
import sys

import numpy as np
import onnxruntime as ort
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from par_feat_lib import FEATS, read_live  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("burst")
EXP, SHADOW = sys.argv[1], sys.argv[2]
t0 = int(pd.Timestamp("2026-10-08 14:50", tz="Asia/Ho_Chi_Minh").value // 10**6)
t1 = int(pd.Timestamp("2026-10-09 12:00", tz="Asia/Ho_Chi_Minh").value // 10**6)
L = read_live(SHADOW, t0, t1)
E = pd.read_csv(EXP)
E["min"] = E.ts.astype("int64")
J = L.merge(E, on="min", suffixes=("_l", "_e"))
sess = ort.InferenceSession(SHADOW + "/storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx", providers=["CPUExecutionProvider"])
nm = sess.get_inputs()[0].name
J["p15_off"] = sess.run(None, {nm: J[[f + "_e" for f in FEATS]].astype(np.float32).values})[0].reshape(-1)
d = (J.p15_off - J.p15_out).abs()
log.info("%s joined=%d p15 |d| med %.2e p99 %.2e max %.2e", SHADOW, len(J), d.median(), d.quantile(.99), d.max())
J["t"] = pd.to_datetime(J["min"], unit="ms", utc=True).dt.tz_convert("Asia/Ho_Chi_Minh").dt.strftime("%m-%d %H:%M")
w = J[(J.p15_out >= 0.015) | (J.p15_off >= 0.015)][["t", "p15_out", "p15_off", "momentum15M_l", "momentum15M_e", "advanceDeclineRatio_l", "advanceDeclineRatio_e"]]
log.info("phut p15 >= 1,5%% (live hoac offline):\n%s", w.to_string(index=False))
