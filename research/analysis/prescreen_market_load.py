#!/usr/bin/env python3
"""PRESCREEN Stage 0 — BUILD feature nhom B (regime THI TRUONG) tren luoi NGAY.
Pre-reg: docs/prereg/PREREG_PRESCREEN_FEAT.md (commit 6695a8c). THUAN PYTHON OFFLINE.
Nguon 1m: /home/ubuntu/claudedata/rvb_1m/raw/*.f32 (627 sym).
Ra: /tmp/prefeat/B.parquet (day_ms, <feature>) — merge_asof backward (shift 1 ngay) o buoc eval.
"""
import os, sys, glob, time, logging
import numpy as np, pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("buildB")
RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
OUT = "/tmp/prefeat"; os.makedirs(OUT, exist_ok=True)
DT1M = np.dtype([("t", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])
K0 = int(pd.Timestamp("2021-12-31 00:00", tz="UTC").value // 3_600_000_000_000)   # gio dau
K1 = int(pd.Timestamp("2024-07-01 00:00", tz="UTC").value // 3_600_000_000_000)
W = 168


def main():
    t0 = time.time()
    syms = sorted(os.path.basename(p)[:-4] for p in glob.glob(RAW + "/*.f32"))
    n = len(syms)
    nh = K1 - K0 + 1
    log.info("coins=%d hours=%d", n, nh)
    C = np.full((n, nh), np.nan, np.float64)
    O = np.full((n, nh), np.nan, np.float64)
    for i, s in enumerate(syms):
        a = np.fromfile(os.path.join(RAW, s + ".f32"), dtype=DT1M)
        m = a["t"].astype(np.int64)
        sel = (m >= K0 * 60) & (m <= (K1 * 60 + 59))
        mm = m[sel]
        if len(mm) == 0:
            continue
        kk = mm // 60
        cc = a["c"][sel].astype(np.float64)
        oo = a["o"][sel].astype(np.float64)
        isopen = (mm % 60) == 0
        isclos = (mm % 60) == 59
        if isopen.any():
            O[i, kk[isopen] - K0] = oo[isopen]
        if isclos.any():
            C[i, kk[isclos] - K0] = cc[isclos]
        if i % 50 == 0:
            log.info(" load %d/%d (%.0fs)", i, n, time.time() - t0)
    log.info("matrices built (%.0fs)", time.time() - t0)
    np.save(os.path.join(OUT, "B_C.npy"), C.astype(np.float32))
    log.info("btc idx=%s", syms.index("BTCUSDT") if "BTCUSDT" in syms else -1)
    log.info("C nan rate=%.4f O nan rate=%.4f", np.isnan(C).mean(), np.isnan(O).mean())
    log.info("syms sample=%s", syms[:5])
    with open(os.path.join(OUT, "B_syms.txt"), "w") as f:
        f.write("\n".join(syms))


if __name__ == "__main__":
    main()
