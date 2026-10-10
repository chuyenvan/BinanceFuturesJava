#!/usr/bin/env python3
"""HO3b: cat file OI dung lai ve ts >= 2026-06-29 00:00 UTC (giu phan Q3 + bien) de tra dia Oracle; ghi tong ket."""
import glob, json, os
import numpy as np
ODT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
LO = 1782691200000
d = "/home/ubuntu/claude_master/1003/ho3b/oi_rebuild"
n0 = n1 = 0
for f in sorted(glob.glob(d + "/*.bin")):
    a = np.fromfile(f, dtype=ODT)
    b = a[a["ts"].astype(np.int64) >= LO]
    n0 += len(a); n1 += len(b)
    b.astype(ODT).tofile(f + ".tmp"); os.replace(f + ".tmp", f)
json.dump(dict(trim_lo_ms=LO, rows_before=n0, rows_after=n1), open(d + "/TRIM.json", "w"))
print(n0, n1)
