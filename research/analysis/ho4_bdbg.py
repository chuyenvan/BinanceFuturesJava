#!/usr/bin/env python3
"""HO4: go loi so khoa bins (stage B common=0)."""
import numpy as np
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
n = np.fromfile("/home/ubuntu/claude_master/1010/ho4/chain/bins/predict_wf_20251001.bin", dtype=DT)
d = np.fromfile("/home/ubuntu/predwf_map_s1a2_x1_2021/predict_wf_20251001.bin", dtype=DT)
o = np.fromfile("/home/ubuntu/claude_master/1010/ho4/chain/net015/predict_wf_20251001.bin", dtype=DT)
for nm, a in (("new_bins", n), ("dev_bins", d), ("new_net", o)):
    print(nm, len(a), a["ts"][:2].astype(np.int64), a["sym"][:2].astype(int), a["ts"].dtype, a.dtype.itemsize)
kn = np.asarray(n["ts"], np.int64) * 10000 + np.asarray(n["sym"], np.int64)
kd = np.asarray(d["ts"], np.int64) * 10000 + np.asarray(d["sym"], np.int64)
print(kn[:3], kd[:3], len(np.intersect1d(kn, kd)))
