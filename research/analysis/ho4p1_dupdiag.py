#!/usr/bin/env python3
"""HO4-P1 chan doan loi chain-y26: trung khoa (ts,sym) Tool1 fold Q3. Chi dem khoa trung/ts/symId (khong gia tri feature).
Usage: ho4p1_dupdiag.py <t1 file> [more files...]"""
import json, logging, os, sys
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/pipeline")
import g015_net_train as G
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
out = {}
for p in sys.argv[1:]:
    x = G.read_tool1(p, grid_ms=G.GRID_MS)
    t = x["ts"].astype(np.int64); s = x["sym"].astype(np.int64)
    k = t * 10000 + s
    u, c = np.unique(k, return_counts=True)
    d = u[c > 1]
    r = dict(n=int(len(k)), n_dup_keys=int(len(d)), ts_min=int(t.min()), ts_max=int(t.max()))
    if len(d):
        ds = d % 10000; dt = d // 10000
        r["dup_syms"] = {int(a): int(b) for a, b in zip(*np.unique(ds, return_counts=True))}
        r["dup_ts_range"] = [int(dt.min()), int(dt.max())]
        r["n_dup_ts"] = int(len(np.unique(dt)))
    out[os.path.basename(p)] = r
    logging.info("%s %s", os.path.basename(p), json.dumps(r)[:1500])
