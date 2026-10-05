#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPLOY242 — export 1 fold gate p15 (recipe train_gate_fold.py) ra ONNX ung vien + parity Python vs ORT + manifest.
Usage: CUTOFF=20260701 python3 deploy242_export_fold.py   (out: <OUT>/model_cut<CUTOFF>/)
CUTOFF > 20260101 => model DUNG du lieu 2026 de train (chi hop le cho LIVE, KHONG cho cham DEV) — ghi ro trong manifest.
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deploy242_gate_lineage as L   # noqa: E402

LOG = logging.getLogger("deploy242_export")


def main():
    cutoff = os.environ.get("CUTOFF", "20260701")
    out_dir = os.path.join(L.OUT, "model_cut%s" % cutoff)
    store = pd.read_csv(L.STORE, usecols=["timestamp"] + L.V3FULL + ["label_oldbasket"]).dropna(subset=["label_oldbasket"])
    store[L.V3FULL] = store[L.V3FULL].astype(np.float32)
    lab_max = store.timestamp.max()
    m, meta = L.train_fold(store, cutoff)
    p = L.export_onnx(m, os.path.join(out_dir, "Model_Regressor_Return15M.onnx"))
    fd, _ = L.load_feat_dump(L.FEAT_DUMP_DIR)
    rng = np.random.default_rng(20261002)
    X = np.vstack([store[L.V3FULL].values[rng.choice(len(store), 20000, replace=False)],
                   fd[L.V3FULL].values.astype(np.float32)])
    d = np.abs(m.predict(X).astype(np.float64) - L.ort_predict(p, X))
    p_live = L.ort_predict(p, fd[L.V3FULL].values.astype(np.float32))
    man = {"cutoff": cutoff, "train": meta, "store_label_ts_max": str(pd.to_datetime(lab_max, unit="ms")),
           "uses_2026_in_train": meta["train_ts_max"] >= "2026-01-01", "xgb_params": L.XGB_PARAMS,
           "features_v3full_order": L.V3FULL, "onnx": L.onnx_info(p),
           "parity_py_vs_ort": {"n": int(len(X)), "max_abs": float(d.max()), "pass_1e6": bool(d.max() <= 1e-6)},
           "dist_on_live_featdump": L.dist(p_live, "cut%s(feat_dump LIVE)" % cutoff),
           "corr_vs_onnx242_live": L.corr(p_live, fd.p15_out.values),
           "status": "CANDIDATE — CHUA deploy"}
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=1, default=str)
    LOG.info("[EXPORT] %s sha256=%s parity=%s", p, man["onnx"]["sha256"], man["parity_py_vs_ort"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
