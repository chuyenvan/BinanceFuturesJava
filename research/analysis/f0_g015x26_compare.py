#!/usr/bin/env python3
"""f0_g015x26_compare.py — so sanh bins tai lap predwf_G015x26 vs bins goc (16 fold DEV).

Bo sung % bit-identical (float32) ma G3 chua bao — TASK F0 item 3.
Ghep theo khoa (ts,symId). Tra cac chi so: n, khoa trung, spearman (rank-IC), max|d|,
% float32 bit-identical, sha256 trung.

CHAY: ORIG=<dir goc> REGEN=<dir tai lap> python3 research/analysis/f0_g015x26_compare.py
Mac dinh: ORIG=/home/ubuntu/claudedata/predwf_G015x26  REGEN=/home/ubuntu/f0_repro/g015x26_regen
"""
import hashlib
import os
import sys

import numpy as np
from scipy.stats import spearmanr

ORIG = os.environ.get("ORIG", "/home/ubuntu/claudedata/predwf_G015x26")
REGEN = os.environ.get("REGEN", "/home/ubuntu/f0_repro/g015x26_regen")
CUTS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401",
        "20230701", "20231001", "20240101", "20240401", "20240701", "20241001",
        "20250101", "20250401", "20250701", "20251001"]


def load(p):
    a = np.fromfile(p, dtype=np.uint8)
    n = len(a) // 26
    a = a[:n * 26].reshape(n, 26)
    ts = np.frombuffer(a[:, 0:8].tobytes(), dtype=">i8").astype(np.int64)
    sym = np.frombuffer(a[:, 8:10].tobytes(), dtype=">i2").astype(np.int64)
    p0 = np.frombuffer(a[:, 10:14].tobytes(), dtype=">f4")
    return ts, sym, p0  # p0 giu float32 de dem bit-identical


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


print("%-9s %9s %9s %6s %10s %11s %11s %8s"%(
    "cutoff", "n_orig", "n_regen", "keys", "spearman", "max|d|", "%bit_id", "sha_eq"))
rows = []
for c in CUTS:
    po = f"{ORIG}/predict_wf_{c}.bin"
    pr = f"{REGEN}/predict_wf_{c}.bin"
    if not os.path.exists(pr):
        print("%-9s MISSING %s" % (c, pr))
        continue
    t1, s1, p1 = load(po)
    t2, s2, p2 = load(pr)
    k1 = t1 * 100000 + s1
    k2 = t2 * 100000 + s2
    o1 = np.argsort(k1, kind="stable")
    o2 = np.argsort(k2, kind="stable")
    keq = np.array_equal(k1[o1], k2[o2])
    a = p1[o1]
    b = p2[o2]
    m = np.isfinite(a.astype(np.float64)) & np.isfinite(b.astype(np.float64))
    # % float32 bit-identical (dung bit view, chi tren khoa co ca hai)
    bit_id = float(np.mean(a[m].view(np.uint32) == b[m].view(np.uint32)))
    d = np.abs(a[m].astype(np.float64) - b[m].astype(np.float64))
    mx = float(d.max()) if m.any() else float("nan")
    idx = np.random.default_rng(0).choice(np.flatnonzero(m), size=min(400000, int(m.sum())),
                                         replace=False)
    sp = float(spearmanr(a[idx].astype(np.float64), b[idx].astype(np.float64)).statistic)
    shq = sha256(po) == sha256(pr)
    print("%-9s %9d %9d %6s %10.8f %11.3e %11.6f %8s"%(
        c, len(t1), len(t2), keq, sp, mx, bit_id, shq))
    rows.append((c, len(t1), len(t2), keq, sp, mx, bit_id))

if rows:
    print("SUMMARY folds=%d keys_all_equal=%s min_spearman=%.8f max_of_max|d|=%.3e "
          "min_%%bit_id=%.6f" % (
              len(rows), all(r[3] for r in rows), min(r[4] for r in rows),
              max(r[5] for r in rows), min(r[6] for r in rows)))
