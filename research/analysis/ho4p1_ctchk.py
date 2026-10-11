#!/usr/bin/env python3
"""HO4-P1: so net015 smoke test (rows_t1 + ONNX) voi file goc backup e03f0e58 tren khoa chung (kiem duong ong, DEV)."""
import logging, sys
import numpy as np
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
a = np.fromfile("/home/ubuntu/claude_master/1011/ho4p1/ctest/out/net015/predict_wf_20251001.bin", dtype=DT)
r = np.fromfile("/home/ubuntu/claude_master/1009/ho26/orig/predict_wf_20251001.bin", dtype=DT)
ka = a["ts"].astype(np.int64) * 10000 + a["sym"]
kr = r["ts"].astype(np.int64) * 10000 + r["sym"]
m = (kr >= ka.min()) & (kr <= ka.max())
c, ia, ib = np.intersect1d(ka, kr, return_indices=True)
d = np.abs(a["p0"][ia].astype(float) - r["p0"][ib].astype(float))
logging.info("n_new %d n_orig_win %d common %d maxd %.3g p1nan %.3f", len(a), int(m.sum()), len(c), d.max(), np.isnan(a["p1"].astype(float)).mean())
