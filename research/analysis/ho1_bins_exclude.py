#!/usr/bin/env python3
"""HO1 B6 — loai symbol 2026 thieu mapper/pin khoi bins 2026 (quyet dinh MASTER 6: KHONG giao dich).
Entry PREDICT/market-signal chi lay coin tu bins (predict2Symbol) => bo ban ghi cua coin do = khong the vao lenh.
Usage: python3 ho1_bins_exclude.py <symbols.json> <in_dir> <out_dir>"""
import glob
import hashlib
import json
import os
import sys

import numpy as np

DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
sj, ind, outd = sys.argv[1:4]
ex = set(json.load(open(sj))["excluded_symids"])
os.makedirs(outd, exist_ok=True)
res = {"excluded_symids": sorted(ex)}
for f in sorted(glob.glob(ind + "/predict_wf_2026*.bin")):
    a = np.fromfile(f, dtype=DT)
    keep = ~np.isin(a["sym"].astype(int), list(ex))
    p = os.path.join(outd, os.path.basename(f))
    a[keep].tofile(p)
    res[os.path.basename(f)] = dict(n_in=int(len(a)), n_dropped=int((~keep).sum()),
                                     sha256=hashlib.sha256(open(p, "rb").read()).hexdigest())
json.dump(res, open(os.path.join(outd, "exclude.json"), "w"), indent=1)
print(json.dumps(res))
