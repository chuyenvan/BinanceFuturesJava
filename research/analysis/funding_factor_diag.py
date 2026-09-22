#!/usr/bin/env python3
"""FUNDING_FACTOR diag (DESCRIPTIVE, post-hoc) — d15 tai entry cho cac dong P-COIN/M-LEVEL MOM15.

Muc dich: kiem tra T3 (+24h) co phai chi la PROXY cua do sau dump (d15) khong.
Doc $FF_OUT/pools.npz + raw/*.f32. Ghi $FF_OUT/d15.npz. Thuan Python, chi doc.
"""
import os
import glob
import time
import logging

import numpy as np

OUT = os.environ.get("FF_OUT", "/tmp/funding_factor")
RAW = os.environ.get("FF_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/diag.log")])
log = logging.getLogger("ffdiag")
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])


def load_sym(path):
    a = np.fromfile(path, dtype=DT)
    ts = a["ts"].astype(np.int64)
    o = np.argsort(ts, kind="stable")
    ts = ts[o]; a = a[o]
    _, ix = np.unique(ts, return_index=True)
    return ts[ix], a["h"][ix].astype(np.float32), a["c"][ix].astype(np.float32)


def d15_of(h, c):
    n = len(h)
    d = np.full(n, np.nan, dtype=np.float32)
    if n >= 15:
        win = np.lib.stride_tricks.sliding_window_view(h, 15)
        mx = win.max(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            d[14:] = np.where(mx > 0, c[14:] / mx - 1.0, np.nan).astype(np.float32)
    return d


def main():
    z = np.load(OUT + "/pools.npz")
    p_min, p_sym = z["p_min"], z["p_sym"]
    m_min, m_sym = z["m_min"], z["m_sym"]
    files = sorted(glob.glob(RAW + "/*.f32"))
    p_d15 = np.full(len(p_min), np.nan, dtype=np.float32)
    m_d15 = np.full(len(m_min), np.nan, dtype=np.float32)
    order_p = np.argsort(p_sym, kind="stable")
    bp = np.searchsorted(p_sym[order_p], np.arange(len(files) + 1))
    order_m = np.argsort(m_sym, kind="stable")
    bm = np.searchsorted(m_sym[order_m], np.arange(len(files) + 1))
    t0 = time.time()
    for i in range(len(files)):
        need_p = order_p[bp[i]:bp[i + 1]]
        need_m = order_m[bm[i]:bm[i + 1]]
        if len(need_p) == 0 and len(need_m) == 0:
            continue
        ts, h, c = load_sym(files[i])
        d = d15_of(h, c)
        for rows, mins, out in ((need_p, p_min, p_d15), (need_m, m_min, m_d15)):
            if len(rows) == 0:
                continue
            mm = mins[rows]
            idx = np.searchsorted(ts, mm)
            ok = (idx < len(ts)) & (ts[np.clip(idx, 0, len(ts) - 1)] == mm)
            out[rows[ok]] = d[idx[ok]]
        if i % 100 == 0:
            log.info("diag %d/%d el=%.0fs", i, len(files), time.time() - t0)
    np.savez(OUT + "/d15.npz", p_d15=p_d15, m_d15=m_d15)
    log.info("saved d15.npz  p_finite=%d/%d  m_finite=%d/%d el=%.0fs",
             int(np.isfinite(p_d15).sum()), len(p_d15), int(np.isfinite(m_d15).sum()), len(m_d15),
             time.time() - t0)


if __name__ == "__main__":
    main()
