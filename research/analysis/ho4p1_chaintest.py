#!/usr/bin/env python3
"""HO4-P1: smoke test ham cua ho4p1_chain.py tren Oracle (du lieu DEV nho, 2025-11-10..11-13; KHONG du lieu 2026).
Usage: ho4p1_chaintest.py"""
import glob, json, logging, os, sys
import numpy as np
import pandas as pd
W = "/home/ubuntu/claude_master/1011/ho4p1"
T = W + "/ctest"
os.makedirs(T, exist_ok=True)
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho4p1_chainops as CO
cfg = dict(mode="none", tag="ctest", code_dir=W + "/stage/ho4p1-code", model_sha=CO.MODEL_SHA, pin_sha=CO.PIN_SHA)
json.dump(cfg, open(T + "/cfg.json", "w"))
sys.argv = ["x", T + "/cfg.json"]; os.environ["HO4P1_WORK"] = T
import ho4p1_chain as C
C.OUT = T + "/out"; os.makedirs(C.OUT, exist_ok=True)
log = logging.getLogger("ct")
lo, hi = C.ms_utc("2025-11-10"), C.ms_utc("2025-11-13")
# OI nho tu ghim
pin = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
n = os.path.getsize(pin) // C.ODT.itemsize
parts = []
for k in range(0, n, 10_000_000):
    c = np.fromfile(pin, dtype=C.ODT, count=min(10_000_000, n - k), offset=k * C.ODT.itemsize)
    t = c["ts"].astype(np.int64)
    parts.append(c[(t >= C.ms_utc("2025-10-20")) & (t < hi)].copy())
np.concatenate(parts).astype(C.ODT).tofile(C.G.OI_FILE)
log.info("OI test %d", os.path.getsize(C.G.OI_FILE) // C.ODT.itemsize)
srcs = [(f, 0, 1 << 62) for f in sorted(glob.glob("/home/ubuntu/ds_feat15m/features_20251001*"))]
log.info("t1 src %s", srcs)
os.makedirs(C.OUT + "/net015", exist_ok=True)
info = C.net015_fold(srcs, lo, hi, C.OUT + "/net015/predict_wf_20251001.bin")
log.info("NET %s", info)
cl = np.fromfile(C.CODE + "/closes_dev_tail.bin", dtype=C.CDT)
cl = cl[(cl["ts"].astype(np.int64) >= C.ms_utc("2025-11-01")) & (cl["ts"].astype(np.int64) < hi + 86400000)]
F, fi = C.featv2(cl, False, C.ms_utc("2025-11-01"), hi + 3600000 * 24, lo - 24 * 3600000, C.OUT + "/feat.parquet")
log.info("FEAT %s", fi)
F = F[["ts", "sym"] + C.S1.KEEP].copy(); F["sym"] = F.sym.astype(np.int64)
raw, a = C.read_pred("/home/ubuntu/claude_master/1003/ho1/gate/pred_s42/pred.bin")
ts = a["ts"].astype(np.int64); p = a["p15"].astype(np.float32)
labs = sorted(glob.glob("/home/ubuntu/ds_label15m/funding_label_20251001*.pb"))
r = C.pool_s1(ts, p, [(lo, hi, labs)], F, C.CODE + "/s1a2x1_cut20251001.json", "ho4p1ctest")
log.info("S1 %s", r)
b = C.bins("ho4p1ctest", ["20251001"], C.OUT + "/net015", C.OUT + "/bins")
log.info("BINS %s", b)
log.info("DROP %s", C.drop_syms(C.OUT + "/bins/predict_wf_20251001.bin", {3, 4}))
os.remove(C.G.OI_FILE)
log.info("CTEST_OK")
