#!/usr/bin/env python3
"""R4 PHA0 proxy (market-level, KHONG phai gate that): trong cac phut p15 cuc tri, bao nhieu phut la dinh moi 15'
(p15(t) > max p15[t-15..t-1]) va CUSUM. Chi mo ta, khong PnL."""
import logging
import struct
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("r4nov")


def load(p):
    with open(p, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        a = np.frombuffer(f.read(16 * n), dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("r4h", ">f4")]))
    return a["ts"].astype(np.int64), a["p15"].astype(np.float64)


def episodes(idx, gap):
    out = []
    for i, x in enumerate(idx):
        if i == 0 or x - idx[i - 1] > gap:
            out.append([x])
        else:
            out[-1].append(x)
    return out


def main(p, frac):
    ts, v = load(p)
    n = len(v)
    k = int(round(frac * n))
    top = np.sort(np.argsort(-v)[:k])
    prevmax = np.full(n, np.inf)
    prevmax[15:] = sliding_window_view(v[:-1], 15).max(axis=1)[: n - 15]
    novel = v > prevmax
    eps = episodes(top.tolist(), 60)
    LOG.info("n=%d k=%d episodes=%d phut/dot med=%.1f", n, k, len(eps), float(np.median([len(e) for e in eps])))
    LOG.info("ty le phut top la dinh moi 15': %.3f", float(novel[top].mean()))
    pos = []
    for e in eps:
        nv = [novel[x] for x in e]
        pos.append(sum(nv))
    LOG.info("so phut dinh-moi moi dot: med=%.1f mean=%.2f ; dot co >=1 phut dinh-moi: %d/%d",
             float(np.median(pos)), float(np.mean(pos)), int(sum(1 for x in pos if x > 0)), len(eps))
    # vi tri phut dinh-moi trong dot (phut thu may tu dau dot)
    rel = [x - e[0] for e in eps for x in e if novel[x]]
    LOG.info("vi tri phut dinh-moi trong dot (phut tu dau dot): med=%.0f p75=%.0f", float(np.median(rel)), float(np.percentile(rel, 75)))
    # surprise = p15(t) - mean60(t-1)
    s = np.cumsum(np.concatenate([[0.0], v]))
    m60 = np.full(n, np.nan)
    m60[60:] = (s[60:n] - s[0:n - 60]) / 60.0  # mean of v[t-60..t-1]
    sur = v - m60
    ok = ~np.isnan(sur)
    sur_top = np.sort(np.argsort(-np.where(ok, sur, -np.inf))[:k])
    jac = len(set(top.tolist()) & set(sur_top.tolist())) / len(set(top.tolist()) | set(sur_top.tolist()))
    x = sur[ok]
    lag1 = np.corrcoef(x[:-1], x[1:])[0, 1]
    lag15 = np.corrcoef(x[:-15], x[15:])[0, 1]
    LOG.info("surprise60: ACF lag1=%.3f lag15=%.3f ; Jaccard top-k vs p15 top-k=%.3f ; so dot=%d",
             lag1, lag15, jac, len(episodes(sur_top.tolist(), 60)))


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
