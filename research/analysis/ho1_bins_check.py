#!/usr/bin/env python3
"""HO1 G-B4c — bins 2026 sau x1_build_map: cung (ts,sym) theo thu tu, multiset p0 tung tick == net015 dau vao.
Chi dem/kiem (khong thong ke gia tri). Usage: python3 ho1_bins_check.py <in_dir> <out_dir>"""
import glob
import hashlib
import json
import os
import sys

import numpy as np

DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
ind, outd = sys.argv[1], sys.argv[2]
res = {}
for f in sorted(glob.glob(ind + "/predict_wf_*.bin")):
    b = os.path.basename(f)
    a, o = np.fromfile(f, dtype=DT), np.fromfile(os.path.join(outd, b), dtype=DT)
    same_keys = len(a) == len(o) and np.array_equal(a["ts"], o["ts"]) and np.array_equal(a["sym"], o["sym"])
    ts = a["ts"].astype(np.int64)
    oa = np.lexsort((a["p0"].astype(np.float64), ts))
    ob = np.lexsort((o["p0"].astype(np.float64), ts))
    multiset = bool(np.array_equal(a["p0"][oa].view(np.uint32), o["p0"][ob].view(np.uint32)))
    res[b] = dict(n=int(len(a)), same_keys=bool(same_keys), multiset_equal=multiset,
                  n_changed=int((a["p0"].view(np.uint32) != o["p0"].view(np.uint32)).sum()),
                  sha256=hashlib.sha256(open(os.path.join(outd, b), "rb").read()).hexdigest(),
                  span_days=int((ts.max() - ts.min()) // 86400000), ts_min=int(ts.min()), ts_max=int(ts.max()))
ok = all(r["same_keys"] and r["multiset_equal"] and r["span_days"] <= 100 for r in res.values())
json.dump(dict(G_B4c=ok, files=res), open(os.path.join(outd, "bins_check.json"), "w"), indent=1)
print(json.dumps(dict(G_B4c=ok, files=res)))
sys.exit(0 if ok else 2)
