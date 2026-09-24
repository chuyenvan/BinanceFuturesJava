#!/usr/bin/env python3
"""compare_bin_spearman.py — do 'venh' giua 2 bo bins `predict_wf_*.bin` (26 B/rec, >qh4f).

CHI DOC FILE (khong train, khong sim, khong Java). Dung cho cong tai lap Stage 2:
  A45 (retrain 45 cot)  vs  bins goc  ->  spearman / max|d| / top-8/tick trung
  B40 (subset 40 cot)   vs  bins goc  ->  muc lech cua subset

Dung:
  python3 compare_bin_spearman.py <bin_A> <bin_B> [--fold-cutoff YYYYMMDD]

Dinh dang bins: ban ghi 26 byte big-endian `[ts:int64][symId:int16][p4h,p12h,p24h,p72h:float32]`;
chi slot p0 (=4h) duoc dung.
"""
import argparse
import struct
import sys

import numpy as np

DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4", 4)])
ITEMSIZE = 26


def load(p):
    raw = np.fromfile(p, dtype=np.uint8)
    if raw.size % ITEMSIZE:
        raise SystemExit("file %s: %d byte khong chia het cho %d (khong phai bins?)"
                         % (p, raw.size, ITEMSIZE))
    return np.frombuffer(raw.tobytes(), dtype=DT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin_a")
    ap.add_argument("bin_b")
    ap.add_argument("--topk", type=int, default=8, help="so coin/tick de do trung top-K")
    a = ap.parse_args()
    A, B = load(a.bin_a), load(a.bin_b)
    ka = A["ts"].astype(np.int64) * 1024 + A["sym"].astype(np.int64)
    kb = B["ts"].astype(np.int64) * 1024 + B["sym"].astype(np.int64)
    ia = np.argsort(ka, kind="stable")
    ib = np.argsort(kb, kind="stable")
    ks_a, ks_b = ka[ia], kb[ib]
    inter = np.intersect1d(ks_a, ks_b)
    pa = A["p"][:, 0][ia][np.searchsorted(ks_a, inter)]
    pb = B["p"][:, 0][ib][np.searchsorted(ks_b, inter)]
    from scipy.stats import spearmanr
    rho = float(spearmanr(pa, pb).statistic)
    print("rows A=%d B=%d | khoa chung=%d (%.4f%% cua A)"
          % (len(A), len(B), len(inter), 100.0 * len(inter) / len(A)))
    print("spearman(p0 A,B) = %.6f | max|d| = %.4g | p_mean A=%.6f B=%.6f"
          % (rho, float(np.abs(pa - pb).max()), pa.mean(), pb.mean()))
    # top-K/tick trung
    ta = A["ts"][ia][np.searchsorted(ks_a, inter)]
    order = np.argsort(ta, kind="stable")
    hit = tot = 0
    starts = np.flatnonzero(np.diff(ta[order], prepend=-1) != 0)
    for i0, i1 in zip(starts, list(starts[1:]) + [len(order)]):
        idx = order[i0:i1]
        if len(idx) < a.topk:
            continue
        sa = set(idx[np.argsort(pa[idx])[-a.topk:]])
        sb = set(idx[np.argsort(pb[idx])[-a.topk:]])
        hit += len(sa & sb)
        tot += a.topk
    print("top-%d/tick trung = %.4f (tren %d tick)" % (a.topk, hit / max(tot, 1), len(starts)))


if __name__ == "__main__":
    sys.exit(main())
