#!/usr/bin/env python3
"""OI_STUDY BUILD — dung 5 ma tran (5m step x symbol) tu nguon CAUSAL.

Pre-reg: docs/PREREG_OI_STUDY.md (commit 7c5f025, chot TRUOC khi do).

Nguon:
  OI    /home/ubuntu/claudedata/oi/oi_percoin_full.bin  (140.924.110 x 30B; >i8 ts, >i2 sym, 5x>f4)
        cot0 = oi_delta24h, cot1 = oi_z   (2 cot thuc su la OI)
  GIA   /home/ubuntu/claudedata/rvb_1m/raw/<SYM>.f32   (ts <i4 phut tu 2021-01-01, o h l c v <f4)
  FUND  Aerospike test/funding_data (bin f_data = snappy(JSON {ts_ms: rate})) — CHI DOC

Xuat /tmp/oi_study/: d24.npy oiz.npy c5.npy rg5.npy f5.npy meta.json
  d24/oiz : gia tri OI tai moc 5m
  c5      : close (USD) tai moc 5m
  rg5     : (high-low) cua nen 1m tai moc 5m  -> slip = 0,5*rg5/c5
  f5      : FUNDING TICH LUY (sum rate co ts_ms <= moc)
Thuan Python, khong Java, khong claude-run, khong 2026 trong thong ke (ma tran chi chua <= 2025-12-31).
"""
import glob
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

OUT = "/tmp/oi_study"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("oib")

OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
SYMMAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
RAW = "/home/ubuntu/claudedata/rvb_1m/raw"

UTC = timezone.utc
STEP_MS = 300000
BASE_MIN = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() // 60)   # 26824320
T0 = int(datetime(2021, 12, 20, tzinfo=UTC).timestamp())             # warm-up >= 24h truoc DEV
T1 = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())               # khong bao gio doc 2026 vao thong ke
NSTEP = (T1 - T0) // 300
DEV_START_MS = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) * 1000   # ms (doi chieu: oi_study.py KHONG dung khoa nay nua)
DEV_END_MS = T1
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
KDT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])


def main():
    t_all = time.time()
    sm = pd.read_csv(SYMMAP)
    s2i = dict(zip(sm["symbol"], sm["symId"]))
    files = sorted(glob.glob(RAW + "/*.f32"))
    syms = [os.path.basename(p)[:-4] for p in files]
    ids = np.array([s2i[s] for s in syms], dtype=np.int64)
    ncol = len(syms)
    i2c = {int(i): c for c, i in enumerate(ids)}
    log.info("NSTEP=%d ncol=%d T0=%s", NSTEP, ncol, datetime.fromtimestamp(T0, UTC))

    meta = dict(nstep=NSTEP, ncol=ncol, T0=T0, T1=T1, step_ms=STEP_MS,
                base_min=BASE_MIN, dev_start_ms=DEV_START_MS, dev_end_ms=DEV_END_MS,
                syms=syms, symids=ids.tolist())

    # ---------- 1. OI ----------
    if not os.path.exists(OUT + "/d24.npy"):
        d24 = np.lib.format.open_memmap(OUT + "/d24.npy", mode="w+", dtype=np.float32, shape=(NSTEP, ncol))
        oiz = np.lib.format.open_memmap(OUT + "/oiz.npy", mode="w+", dtype=np.float32, shape=(NSTEP, ncol))
        d24[:] = np.nan
        oiz[:] = np.nan
        mm = np.memmap(OI, dtype=OI_DT, mode="r")
        tot = len(mm)
        CH = 20_000_000
        kept = 0
        for s in range(0, tot, CH):
            b = mm[s:s + CH]
            ts = np.asarray(b["ts"], dtype=np.int64)
            sym = np.asarray(b["sym"], dtype=np.int64)
            m = (ts >= T0 * 1000) & (ts < T1 * 1000)
            if not m.any():
                continue
            ts = ts[m]
            sym = sym[m]
            u, inv = np.unique(sym, return_inverse=True)
            cmap = np.array([i2c.get(int(x), -1) for x in u])
            cc = cmap[inv]
            ok = cc >= 0
            stp = (ts // 300000) - (T0 * 1000 // 300000)
            oi = np.asarray(b["oi"][m], dtype=np.float32)
            good = ok & (stp >= 0) & (stp < NSTEP)
            d24[stp[good], cc[good]] = oi[good, 0]
            oiz[stp[good], cc[good]] = oi[good, 1]
            kept += int(good.sum())
            if (s // CH) % 2 == 0:
                log.info("OI chunk %d/%d kept=%d el=%.0fs", s // CH, tot // CH, kept, time.time() - t_all)
        del mm
        d24.flush(); oiz.flush()
        log.info("OI xong kept=%d el=%.0fs", kept, time.time() - t_all)
    else:
        log.info("d24.npy co san -> bo qua")

    # ---------- 2. GIA ----------
    if not os.path.exists(OUT + "/c5.npy"):
        c5 = np.lib.format.open_memmap(OUT + "/c5.npy", mode="w+", dtype=np.float32, shape=(NSTEP, ncol))
        rg5 = np.lib.format.open_memmap(OUT + "/rg5.npy", mode="w+", dtype=np.float32, shape=(NSTEP, ncol))
        c5[:] = np.nan
        rg5[:] = np.nan
        t0_min = int(T0 // 60)
        t1_min = int(T1 // 60)
        for c, p in enumerate(files):
            a = np.fromfile(p, dtype=KDT)
            ts = a["ts"].astype(np.int64)
            o = np.argsort(ts, kind="stable")
            ts = ts[o]
            _, u = np.unique(ts, return_index=True)
            hl = a["h"][o][u].astype(np.float32)
            ll = a["l"][o][u].astype(np.float32)
            cl = a["c"][o][u].astype(np.float32)
            ts = ts[u]
            g = (ts >= t0_min) & (ts < t1_min) & (ts % 5 == 0)
            ts, hl, ll, cl = ts[g], hl[g], ll[g], cl[g]
            if len(ts) == 0:
                continue
            stp = (ts - t0_min) // 5
            ok = cl > 0
            c5[stp[ok], c] = cl[ok]
            rg5[stp[ok], c] = hl[ok] - ll[ok]
            if c % 100 == 0:
                log.info("GIA %d/%d el=%.0fs", c, ncol, time.time() - t_all)
        c5.flush(); rg5.flush()
        log.info("GIA xong el=%.0fs", time.time() - t_all)
    else:
        log.info("c5.npy co san -> bo qua")

    # ---------- 3. FUNDING ----------
    if not os.path.exists(OUT + "/f5.npy"):
        import aerospike
        import cramjam
        f5 = np.lib.format.open_memmap(OUT + "/f5.npy", mode="w+", dtype=np.float32, shape=(NSTEP, ncol))
        f5[:] = 0.0
        cli = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 60000}}).connect()
        step_ms = (np.arange(NSTEP, dtype=np.int64) + (T0 // 300000)) * 300000
        nmiss = 0
        for c, s in enumerate(syms):
            try:
                k = cli.get(("test", "funding_data", s))
                d = json.loads(bytes(cramjam.snappy.decompress_raw(k[2]["f_data"])))
                it = sorted((int(t), float(v)) for t, v in d.items())
                ft = np.array([x[0] for x in it], dtype=np.int64)
                fr = np.array([x[1] for x in it], dtype=np.float64)
                pos = np.searchsorted(ft, step_ms, side="right")
                cs = np.concatenate([[0.0], np.cumsum(fr)])[:len(ft) + 1]
                f5[:, c] = cs[pos].astype(np.float32)
            except Exception as e:
                nmiss += 1
                log.warning("funding %s fail %r", s, e)
            if c % 100 == 0:
                log.info("FUND %d/%d miss=%d el=%.0fs", c, ncol, nmiss, time.time() - t_all)
        f5.flush()
        log.info("FUND xong miss=%d el=%.0fs", nmiss, time.time() - t_all)
    else:
        log.info("f5.npy co san -> bo qua")

    json.dump(meta, open(OUT + "/meta.json", "w"))
    json.dump({"syms": syms}, open(OUT + "/syms.json", "w"))
    open(OUT + "/BUILD_DONE", "w").write("ok %.0fs\n" % (time.time() - t_all))
    log.info("BUILD_DONE el=%.0fs", time.time() - t_all)


if __name__ == "__main__":
    main()
