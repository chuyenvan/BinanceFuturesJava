#!/usr/bin/env python3
"""OI_STUDY_POSTHOC3 — %coin+ (chi so DA KHAI BAO trong pre-reg §2 'bao them %coin+'), POST-HOC.

Pre-reg docs/PREREG_OI_STUDY.md (7c5f025) §2 ghi: "bao them %coin+". Script nay tinh dung no cho
H1 24h (Q9 va EW): mean net theo tung symbol, dem ty le symbol co mean > 0 (voi >=1, >=5, >=10, >=20 lenh).
Thuan Python, khong Java, khong cham 2026.
"""
import json
import warnings
from datetime import datetime, timezone

import numpy as np

warnings.filterwarnings("ignore")
OUT = "/tmp/oi_study"
FEE, MIN_SYM = 0.0010, 50
UTC = timezone.utc

meta = json.load(open(OUT + "/meta.json"))
NSTEP, ncol, T0 = meta["nstep"], meta["ncol"], meta["T0"]
a0 = T0 * 1000 // 300000
i0 = (int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) * 1000 // 300000) - a0
d24 = np.load(OUT + "/d24.npy", mmap_mode="r")
c5 = np.load(OUT + "/c5.npy", mmap_mode="r")
rg5 = np.load(OUT + "/rg5.npy", mmap_mode="r")
f5 = np.load(OUT + "/f5.npy", mmap_mode="r")
hours = np.arange(i0 + ((-i0) % 12), NSTEP, 12, dtype=np.int64)
SUM = {"Q9": np.zeros(ncol), "EW": np.zeros(ncol)}
CNT = {"Q9": np.zeros(ncol, dtype=np.int64), "EW": np.zeros(ncol, dtype=np.int64)}
for i in hours:
    j = i + 288
    if j >= NSTEP:
        continue
    d, c = d24[i], c5[i]
    u = np.isfinite(d) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
    if u.sum() < MIN_SYM:
        continue
    idx = np.flatnonzero(u)
    order = np.argsort(d[idx], kind="stable")
    N = len(idx)
    dec_r = np.empty(N, dtype=np.int8)
    dec_r[order] = np.minimum(np.arange(N) * 10 // N, 9)
    net = (c5[j][idx] / c[idx] - 1.0 - FEE - 0.5 * rg5[i][idx] / c[idx] - (f5[j][idx] - f5[i][idx]))
    np.add.at(SUM["EW"], idx, net)
    np.add.at(CNT["EW"], idx, 1)
    m = dec_r == 9
    np.add.at(SUM["Q9"], idx[m], net[m])
    np.add.at(CNT["Q9"], idx[m], 1)
print("=== %%coin+ (H1 24h, net sau phi CHINH) — POST-HOC theo pre-reg §2 ===")
for tag in ("Q9", "EW"):
    cm = CNT[tag] > 0
    vals = SUM[tag][cm] / CNT[tag][cm]
    cnts = CNT[tag][cm]
    line = "  %-4s nsym=%d" % (tag, int(cm.sum()))
    for mt in (1, 5, 10, 20):
        s = vals[cnts >= mt]
        line += " | >=%d: nsym=%d %%coin+=%.1f%%" % (mt, len(s), 100 * (s > 0).mean())
    print(line)
print("  (event: Q9=%d EW=%d)" % (int(CNT["Q9"].sum()), int(CNT["EW"].sum())))
