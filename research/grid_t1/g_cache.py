#!/usr/bin/env python3
"""Build per-symbol aligned 1m OHLC cache in two passes (low memory, cgroup 6GB).

Pass 1: stream month parquets, append raw records per symbol to parts/<SYM>.bin.
Pass 2: per symbol, align to global minute grid and write cache/<SYM>.npz.
"""
import glob
import os
import numpy as np
import pyarrow.parquet as pq

RAW = os.path.expanduser("~/vz_e1/raw")
WK = os.path.expanduser("~/claude_master/grid_t1_wk")
CACHE = os.path.join(WK, "cache")
PARTS = os.path.join(WK, "parts")
os.makedirs(CACHE, exist_ok=True)
os.makedirs(PARTS, exist_ok=True)
TS0 = 1638316800000
TS1 = 1767225600000
N = (TS1 - TS0) // 60000


def pass1():
    syms = [s.strip() for s in open(os.path.join(WK, "syms.txt")) if s.strip()]
    handles = {s: open(os.path.join(PARTS, s + ".bin"), "wb") for s in syms}
    for f in sorted(glob.glob(os.path.join(RAW, "kline1m-*.parquet"))):
        t = pq.read_table(f, columns=["ts", "sym", "open", "high", "low", "close"])
        d = t.to_pandas()
        d = d[d["sym"].isin(syms)]
        for s, g in d.groupby("sym", observed=True, sort=False):
            a = np.empty((len(g), 5), np.float64)
            a[:, 0] = g["ts"].to_numpy(np.float64)
            a[:, 1] = g["open"].to_numpy(np.float64)
            a[:, 2] = g["high"].to_numpy(np.float64)
            a[:, 3] = g["low"].to_numpy(np.float64)
            a[:, 4] = g["close"].to_numpy(np.float64)
            handles[s].write(a.astype(np.float32).tobytes())
        print(os.path.basename(f), len(d), flush=True)
    for h in handles.values():
        h.close()


def pass2():
    syms = [s.strip() for s in open(os.path.join(WK, "syms.txt")) if s.strip()]
    for s in syms:
        p = os.path.join(PARTS, s + ".bin")
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            print("MISSING", s, flush=True)
            continue
        a = np.fromfile(p, dtype=np.float32).reshape(-1, 5)
        ts = a[:, 0].astype(np.int64)
        idx = (ts - TS0) // 60000
        ok = (idx >= 0) & (idx < N)
        idx, a = idx[ok], a[ok]
        o = np.full(N, np.nan, np.float32); h = np.full(N, np.nan, np.float32)
        l = np.full(N, np.nan, np.float32); c = np.full(N, np.nan, np.float32)
        o[idx] = a[:, 1]; h[idx] = a[:, 2]; l[idx] = a[:, 3]; c[idx] = a[:, 4]
        first = int(idx.min()); last = int(idx.max())
        cc = np.asarray(__import__("pandas").Series(c).ffill().bfill(), np.float32)
        o = np.where(np.isnan(o), cc, o).astype(np.float32)
        h = np.where(np.isnan(h), cc, h).astype(np.float32)
        l = np.where(np.isnan(l), cc, l).astype(np.float32)
        c = cc
        h = np.maximum.reduce([h, o, c]).astype(np.float32)
        l = np.minimum.reduce([l, o, c]).astype(np.float32)
        np.savez(os.path.join(CACHE, s + ".npz"), o=o, h=h, l=l, c=c,
                 first=np.int64(first), last=np.int64(last), ts0=np.int64(TS0), n=np.int64(N))
        print("wrote", s, first, last, flush=True)
        del o, h, l, c, a, ts, idx
        os.remove(p)


if __name__ == "__main__":
    import sys
    if sys.argv[1:] and sys.argv[1] == "2":
        pass2()
    else:
        pass1()
        pass2()
