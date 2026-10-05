#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPLOY242 — PROBE lineage ONNX242 (= wfo_models/fold_20): retrain recipe train_gate_fold.py o nhieu CUTOFF,
so du doan voi ONNX242 va wfo_models/fold_18/19 tren CUNG mau store => cutoff nao tai lap model dong bang.
+ kiem bat bien buffer gate: factor*gs = p15/r >= DYN_MIN*gs (0,26787*1,55) tren record LIVE (sau 01/10 11:04 +07).
0-sim, offline, chi doc. Output: <OUT>/lineage_probe.json
"""
import glob
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deploy242_gate_lineage as L   # noqa: E402  (dung chung recipe/IO)

LOG = logging.getLogger("deploy242_probe")
CUTS = ["20250701", "20251001", "20260101", "20260401", "20260701"]


def main():
    store = pd.read_csv(L.STORE, usecols=["timestamp"] + L.V3FULL + ["label_oldbasket"]).dropna(subset=["label_oldbasket"])
    store[L.V3FULL] = store[L.V3FULL].astype(np.float32)
    rng = np.random.default_rng(7)
    ev = store[store.timestamp >= L.cut_ms("20240101")]
    ev = ev.iloc[np.sort(rng.choice(len(ev), 200000, replace=False))]
    X = ev[L.V3FULL].values.astype(np.float32)
    frozen = {k: L.ort_predict(p, X) for k, p in
              [("ONNX242", L.LIVE_ONNX)] + [(os.path.basename(os.path.dirname(p)), p) for p in
               sorted(glob.glob(L.WFO_MODELS + "/fold_1[6-9]/Model_Regressor_Return15M.onnx"))]}
    out = {"eval_rows": int(len(ev)), "eval_from": "2024-01-01", "pairs": {}}
    for c in CUTS:
        m, meta = L.train_fold(store, c)
        p = m.predict(X).astype(np.float64)
        for k, v in frozen.items():
            r = L.corr(p, v)
            out["pairs"]["retrain%s~%s" % (c, k)] = r
            LOG.info("[PROBE] retrain cutoff=%s vs %-8s pearson=%.5f spearman=%.5f max|d|=%.4g",
                     c, k, r["pearson"], r["spearman"], r["max_abs_diff"])

    # ---- bat bien buffer gate tren record LIVE (G2 bat tu 01/10 11:04 +07 = 04:04 UTC)
    bts, br, _ = L.load_gate_buffer(L.GATE_BUF)
    fd, _ = L.load_feat_dump(L.FEAT_DUMP_DIR)
    b = pd.DataFrame({"ts": bts, "r": br}).merge(fd[["ts", "p15_out"]], on="ts", how="left")
    t_live = int(pd.Timestamp("2026-10-01 04:04:00").value // 10 ** 6)
    floor = 0.26787 * 1.55
    res_b = {}
    for name, sub in [("seed_or_pre", b[b.ts < t_live]), ("live_after_g2", b[b.ts >= t_live])]:
        s = sub.dropna(subset=["p15_out"])
        fgs = (s.p15_out / s.r).values
        res_b[name] = {"records": int(len(sub)), "with_p15": int(len(s)),
                       "fgs_min": float(fgs.min()) if len(fgs) else None,
                       "frac_below_floor": float((fgs < floor - 1e-4).mean()) if len(fgs) else None,
                       "fallback_pass_if_same_p15": int((s.p15_out >= 0.008 * fgs).sum()) if len(fgs) else None}
        LOG.info("[BUF] %s %s", name, res_b[name])
    out["buffer_invariant"] = res_b
    with open(os.path.join(L.OUT, "lineage_probe.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
