#!/usr/bin/env python3
"""PAIRS_T1 - build the 1h panel from Vision kline1m (Kaggle vz-kline1m-YYYY) + funding (vz-funding).

DEV only: 2021-01-01 00:00Z <= ts < 2026-01-01 00:00Z. No 2026, no 2020s/bcast, no Binance REST.
Hourly bar h (open time H0 + h*1h): open = open of first ACTIVE minute in the hour, close = close of the
last ACTIVE minute, qv = sum quote_volume, nmin = number of active minutes. Missing hour => NaN.
Funding: rate placed at hour index round((ts - H0)/1h) (calc_time is a few ms after the hour mark).
Output: ~/claude_master/pairs/data/panel_1h.npz (+ panel_meta.json). Usage: python3 build_1h.py
"""
import glob
import hashlib
import json
import logging
import os
import sys
import time

import numpy as np
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("build_1h")

D = os.path.expanduser("~/claude_master/pairs/data")
RAW_E1 = os.path.expanduser("~/vz_e1/raw")
H0 = 1609459200000          # 2021-01-01 00:00Z
T1 = 1767225600000          # 2026-01-01 00:00Z
NH = (T1 - H0) // 3600000   # 43824
HMS = 3600000


def month_files():
    out = []
    for y in range(2021, 2026):
        for m in range(1, 13):
            mm = "%d-%02d" % (y, m)
            p1 = os.path.join(D, "kline1m", "kline1m-%s.parquet" % mm)
            p2 = os.path.join(RAW_E1, "kline1m-%s.parquet" % mm)
            p = p1 if os.path.exists(p1) else p2
            if not os.path.exists(p):
                raise SystemExit("MISSING month %s" % mm)
            out.append((mm, p))
    return out


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def keep_symbol(s):
    return s.endswith("USDT") and "_" not in s


def main():
    t0 = time.time()
    files = month_files()
    per = {}   # sym -> dict of arrays (lazy)
    stats = dict(rows=0, inactive=0, inactive_volpos=0, out_of_range=0, files={})

    def arr(s):
        if s not in per:
            per[s] = dict(o=np.full(NH, np.nan), c=np.full(NH, np.nan),
                          q=np.zeros(NH, np.float64), n=np.zeros(NH, np.int16))
        return per[s]

    for mm, p in files:
        pf = pq.ParquetFile(p)
        nr = 0
        for rg in range(pf.num_row_groups):
            t = pf.read_row_group(rg, columns=["ts", "sym", "open", "close", "quote_volume", "volume", "active"])
            symc = t.column("sym").combine_chunks()
            syms_rg = symc.dictionary.to_pylist() if hasattr(symc, "dictionary") else None
            idx = symc.indices.to_numpy() if hasattr(symc, "indices") else None
            ts = t.column("ts").to_numpy()
            o = t.column("open").to_numpy()
            c = t.column("close").to_numpy()
            q = t.column("quote_volume").to_numpy()
            v = t.column("volume").to_numpy()
            act = t.column("active").to_numpy(zero_copy_only=False)
            nr += len(ts)
            stats["rows"] += len(ts)
            stats["inactive"] += int((~act).sum())
            stats["inactive_volpos"] += int(((~act) & (v > 0)).sum())
            for k in np.unique(idx):
                s = syms_rg[k]
                if not keep_symbol(s):
                    continue
                sel = (idx == k) & act
                tt = ts[sel]
                if len(tt) == 0:
                    continue
                order = np.argsort(tt, kind="stable")
                tt = tt[order]
                h = (tt - H0) // HMS
                inr = (h >= 0) & (h < NH)
                stats["out_of_range"] += int((~inr).sum())
                if not inr.any():
                    continue
                h = h[inr]
                oo = o[sel][order][inr]
                cc = c[sel][order][inr]
                qq = q[sel][order][inr]
                uh, first = np.unique(h, return_index=True)
                last = np.r_[first[1:], len(h)] - 1
                A = arr(s)
                A["o"][uh] = oo[first]
                A["c"][uh] = cc[last]
                A["q"][uh] += np.add.reduceat(qq, first)
                A["n"][uh] += (last - first + 1).astype(np.int16)
        stats["files"][mm] = dict(path=p, rows=nr, bytes=os.path.getsize(p), sha256=sha256(p))
        log.info("month %s rows=%d syms_so_far=%d %.0fs", mm, nr, len(per), time.time() - t0)

    syms = sorted(per)
    S = len(syms)
    O = np.stack([per[s]["o"] for s in syms], axis=1)
    C = np.stack([per[s]["c"] for s in syms], axis=1)
    Q = np.stack([per[s]["q"] for s in syms], axis=1).astype(np.float64)
    N = np.stack([per[s]["n"] for s in syms], axis=1)
    del per
    # funding
    import pandas as pd
    F = np.zeros((NH, S), np.float64)
    FN = np.zeros((NH, S), np.int8)
    s2i = {s: i for i, s in enumerate(syms)}
    fstats = {}
    for y in range(2021, 2026):
        p = os.path.join(D, "funding", "funding-%d.parquet" % y)
        f = pd.read_parquet(p)
        f = f[(f.ts >= H0) & (f.ts < T1)]
        f["sym"] = f["sym"].astype(str)
        f = f[f.sym.isin(s2i)]
        h = np.rint((f.ts.values - H0) / HMS).astype(np.int64)
        off = (f.ts.values - H0) - h * HMS
        ok = (h >= 0) & (h < NH)
        si = f.sym.map(s2i).values.astype(np.int64)
        np.add.at(F, (h[ok], si[ok]), f.rate.values[ok])
        np.add.at(FN, (h[ok], si[ok]), 1)
        fstats[y] = dict(rows=int(len(f)), sha256=sha256(p), max_abs_offset_ms=int(np.abs(off).max()) if len(off) else 0,
                         nsym=int(f.sym.nunique()))
        log.info("funding %d rows=%d nsym=%d maxoff=%dms", y, len(f), f.sym.nunique(), fstats[y]["max_abs_offset_ms"])
    stats["funding"] = fstats
    stats["dup_funding_cells"] = int((FN > 1).sum())
    first = np.array([np.argmax(~np.isnan(C[:, j])) for j in range(S)])
    lastv = np.array([NH - 1 - np.argmax(~np.isnan(C[::-1, j])) for j in range(S)])
    out = os.path.join(D, "panel_1h.npz")
    np.savez(out, syms=np.array(syms), open=O, close=C, qv=Q, nmin=N, fund=F, first=first, last=lastv,
             H0=np.array([H0]), NH=np.array([NH]))
    stats.update(S=S, NH=int(NH), panel=out, panel_sha256=sha256(out), secs=time.time() - t0,
                 delisted_before_2025_12_01=[syms[j] for j in range(S) if lastv[j] < NH - 31 * 24])
    json.dump(stats, open(os.path.join(D, "panel_meta.json"), "w"), indent=1)
    log.info("DONE S=%d panel=%s %.0fs inactive=%d (vol>0: %d)", S, out, time.time() - t0,
             stats["inactive"], stats["inactive_volpos"])


if __name__ == "__main__":
    main()
