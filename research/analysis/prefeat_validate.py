#!/usr/bin/env python3
"""prefeat_validate.py — kiem chung prefeat_full.py TAI LAP dung A.parquet cua Stage 0
tren cung cua so (GRID0..GRID1) va cung tap dong (joined.parquet).

Neu trung (sai so ~1e-6 tuong doi) => dinh nghia feature cua Stage 2 == dinh nghia da do o Stage 0.
Read-only. Khong train, khong sim.
"""
import os, sys, time, logging
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prefeat_full as P

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("valid")

GRID0 = 1646092800000      # 2022-03-01 UTC (ms) — giong prescreen_build.py
GRID1 = 1719792000000      # 2024-07-01 UTC (ms)
JOINED = "/tmp/evfeat/joined.parquet"
APQ = "/tmp/prefeat/A.parquet"


def main():
    t0 = time.time()
    j = pd.read_parquet(JOINED, columns=["ts", "symId"])
    A = pd.read_parquet(APQ)
    m = pd.read_csv(P.MAP)
    i2s = dict(zip(m.symId.astype(np.int32), m.symbol))
    rng = np.random.default_rng(11)
    syms = [int(s) for s in rng.choice(np.unique(j.symId.values), 3, replace=False)]
    log.info("sym kiem: %s", {s: i2s[s] for s in syms})
    grid = np.arange(GRID0 // 60000, GRID1 // 60000 + 1, 15).astype(np.int64)
    j["_m"] = (j.ts.values // 60000).astype(np.int64)
    P.oi_by = P.scan_oi(syms)
    P.i2s = i2s
    cols = ["rvol7d", "mom7d", "mom30d", "daysSinceHigh30D", "oi_delta7d"]
    for sid in syms:
        x = P.build_coin_A(i2s[sid], grid, None)
        x["oi_delta7d"] = P.oi_feats(sid, grid)
        idx = np.flatnonzero(j.symId.values == sid)
        pos = np.searchsorted(grid, j["_m"].values[idx])
        ok = pos < len(grid)
        pos = pos[ok]; idx = idx[ok]
        a = A.iloc[idx]
        for c in cols:
            v_new = np.asarray(x[c], np.float64)[pos]
            v_old = a[c].to_numpy(np.float64)
            fin = np.isfinite(v_new) & np.isfinite(v_old)
            if fin.sum() == 0:
                log.info("  %s %-18s KHONG co dong finite chung", i2s[sid], c); continue
            d = np.abs(v_new[fin] - v_old[fin])
            rel = d / np.maximum(np.abs(v_old[fin]), 1e-12)
            log.info("  %s %-18s n=%d max|d|=%.3e max_rel=%.3e | nan_new=%d nan_old=%d nan_lech=%d",
                     i2s[sid], c, int(fin.sum()), d.max(), rel.max(),
                     int(np.isnan(v_new).sum()), int(np.isnan(v_old).sum()),
                     int((np.isnan(v_new) != np.isnan(v_old)).sum()))
    log.info("DONE %.0fs", time.time() - t0)


if __name__ == "__main__":
    main()
