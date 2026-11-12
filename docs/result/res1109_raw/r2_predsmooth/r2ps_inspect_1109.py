#!/usr/bin/env python3
"""R2 PHA0: kiem dinh dang/do phan giai pred.bin + bins selector (chi doc, nhe)."""
import glob
import logging
import os
import struct
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("r2ps")


def read_pred(p):
    with open(p, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        a = np.frombuffer(f.read(16 * n), dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("r4h", ">f4")]))
    return a


def describe_pred(p):
    a = read_pred(p)
    ts = a["ts"].astype(np.int64)
    v = a["p15"].astype(np.float64)
    d = np.diff(ts)
    u, c = np.unique(d, return_counts=True)
    top = sorted(zip(c, u), reverse=True)[:5]
    LOG.info("FILE %s n=%d first=%s last=%s", p, len(a),
             np.datetime64(int(ts[0]), "ms"), np.datetime64(int(ts[-1]), "ms"))
    LOG.info("  dt top(count,ms)=%s  sorted=%s  nan=%d", top, bool((d > 0).all()), int(np.isnan(v).sum()))
    LOG.info("  ts mod 60000 !=0: %d ; gaps>60s: %d ; max gap min: %.1f", int((ts % 60000 != 0).sum()),
             int((d > 60000).sum()), d.max() / 60000.0)
    q = np.nanquantile(v, [0.0, 0.5, 0.9, 0.99, 0.999, 0.9999, 1.0])
    LOG.info("  p15 quantiles 0/50/90/99/99.9/99.99/100 = %s", np.round(q, 5).tolist())
    # tu tuong quan theo lag (phut) tren chuoi lien tuc
    for lag in (1, 5, 15, 60, 240):
        x, y = v[:-lag], v[lag:]
        ok = (ts[lag:] - ts[:-lag]) == lag * 60000
        r = np.corrcoef(x[ok], y[ok])[0, 1]
        LOG.info("  acf lag %3d min = %.4f (n=%d)", lag, r, int(ok.sum()))
    # cac phut cuc tri: top 0.01% -> gia tri trung binh 15/60/240 truoc do (causal) so voi gia tri diem
    s = np.cumsum(np.concatenate([[0.0], v]))
    thr = np.quantile(v, 0.9999)
    idx = np.where(v >= thr)[0]
    for w in (15, 60, 240):
        ii = idx[idx >= w - 1]
        m = (s[ii + 1] - s[ii + 1 - w]) / w
        LOG.info("  top0.01%% phut (n=%d): p15 diem med=%.5f ; mean%d causal med=%.5f ; ty le mean/diem med=%.3f",
                 len(ii), float(np.median(v[ii])), w, float(np.median(m)), float(np.median(m / v[ii])))
    return a


def describe_bins(d):
    fs = sorted(glob.glob(os.path.join(d, "predict_wf_*.bin")))
    LOG.info("BINS %s files=%d", d, len(fs))
    for p in fs[:2] + fs[-1:]:
        with open(p, "rb") as f:
            n = struct.unpack(">i", f.read(4))[0]
            tss = []
            lens = []
            for _ in range(min(n, 400)):
                t, ln = struct.unpack(">qi", f.read(12))
                f.seek(8 * ln, 1)
                tss.append(t)
                lens.append(ln)
        dd = np.diff(np.array(tss))
        u, c = np.unique(dd, return_counts=True)
        LOG.info("  %s n=%d first=%s dt(ms,count)=%s len_med=%d", os.path.basename(p), n,
                 np.datetime64(int(tss[0]), "ms"), list(zip(u.tolist(), c.tolist()))[:4], int(np.median(lens)))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        if os.path.isdir(p):
            describe_bins(p)
        else:
            describe_pred(p)
