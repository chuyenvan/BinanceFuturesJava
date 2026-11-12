#!/usr/bin/env python3
"""R2 PHA0: nhip cap nhat score selector (bins >q h 4f) - top-24 doi bao nhieu giua 2 moc 15' lien tiep."""
import logging
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("r2bins")
K = 24


def main(p):
    dt = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("s0", ">f4"), ("s1", ">f4"), ("s2", ">f4"), ("s3", ">f4")])
    raw = np.fromfile(p, dtype=np.uint8)
    n = (len(raw)) // 26
    a = np.frombuffer(raw[: n * 26].tobytes(), dtype=dt)
    ts = a["ts"].astype(np.int64)
    LOG.info("file=%s rec=%d (du %d byte) ts0=%s tsN=%s", p, n, len(raw) - n * 26,
             np.datetime64(int(ts[0]), "ms"), np.datetime64(int(ts[-1]), "ms"))
    u, start = np.unique(ts, return_index=True)
    d = np.diff(u)
    uu, cc = np.unique(d, return_counts=True)
    LOG.info("so tick=%d dt(ms,count) top=%s", len(u), sorted(zip(cc.tolist(), uu.tolist()), reverse=True)[:3])
    ends = np.append(start[1:], len(a))
    tops = []
    for s, e in zip(start, ends):
        blk = a[s:e]
        o = np.argsort(-blk["s0"], kind="stable")[:K]  # slot0 = P(win), sim score = 1-slot0 => slot0 CAO = hang tot
        tops.append(set(blk["sym"][o].tolist()))
    same_h, diff_h = [], []
    for i in range(1, len(u)):
        if u[i] - u[i - 1] != 900000:
            continue
        j = len(tops[i] & tops[i - 1]) / K
        if u[i] // 3600000 == u[i - 1] // 3600000:
            same_h.append(j)
        else:
            diff_h.append(j)
    LOG.info("overlap top%d giua 2 tick 15' lien tiep: CUNG gio med=%.3f mean=%.3f (n=%d) | QUA gio med=%.3f mean=%.3f (n=%d)",
             K, np.median(same_h), np.mean(same_h), len(same_h), np.median(diff_h), np.mean(diff_h), len(diff_h))


if __name__ == "__main__":
    main(sys.argv[1])
