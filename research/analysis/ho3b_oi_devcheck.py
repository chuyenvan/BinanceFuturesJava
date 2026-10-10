#!/usr/bin/env python3
"""HO3b: kiem tinh dung code dung lai OI tren DEV 2025-12-29..12-31 (UTC) — so voi file ghim e3887f63.
Chi doan DEV (khong vao cong). In ty le khop tung cot (float32 bang nhau, NaN==NaN) + so dong."""
import glob, json, os, sys
import numpy as np
import pandas as pd
ODT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
PIN = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
LO = int(pd.Timestamp("2025-12-29", tz="UTC").value // 10**6)
HI = int(pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-01-01", tz="UTC").value // 10**6)
outd = sys.argv[1]
R = np.concatenate([np.fromfile(f, dtype=ODT) for f in glob.glob(outd + "/*.bin")])
R = R[(R["ts"] >= LO) & (R["ts"] < HI)]
syms = set(np.unique(R["sym"]).tolist())
n = os.path.getsize(PIN) // ODT.itemsize
parts = []
for k in range(0, n, 10_000_000):
    c = np.fromfile(PIN, dtype=ODT, count=min(10_000_000, n - k), offset=k * ODT.itemsize)
    t = c["ts"].astype(np.int64)
    m = (t >= LO) & (t < HI) & np.isin(c["sym"], list(syms))
    parts.append(c[m].copy())
P = np.concatenate(parts)
kr = R["ts"].astype(np.int64) * 10000 + R["sym"]
kp = P["ts"].astype(np.int64) * 10000 + P["sym"]
com, ir, ip = np.intersect1d(kr, kp, return_indices=True)
res = dict(rows_rebuild=int(len(R)), rows_pin=int(len(P)), both=int(len(com)), syms=len(syms))
NM = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
for j, nm in enumerate(NM):
    a = R["oi"][ir, j].astype(np.float32); b = P["oi"][ip, j].astype(np.float32)
    eq = (a == b) | (np.isnan(a) & np.isnan(b))
    rel = np.abs(a.astype(np.float64) - b) / np.maximum(np.abs(b.astype(np.float64)), 1e-12)
    res[nm] = dict(eq=float(eq.mean()), le1e6=float(((rel <= 1e-6) | eq).mean()))
print(json.dumps(res, indent=1))
