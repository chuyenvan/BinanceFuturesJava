#!/usr/bin/env python3
"""LS_TAKER BUILD — dung panel GIO (1h) cho 3 cot CHUA TUNG dung: ls_global, ls_toptrader, taker_buy.

Pre-reg: docs/prereg/PREREG_LS_TAKER.md (chot TRUOC khi do).

Vi sao panel GIO (khong phai 5m): moi horizon cua H1/H2 (1h/4h/24h) deu la boi so 1h, va rank
cross-section cua OI study cung lay tai moc gio -> panel gio cho GIA TRI Y HET, ton ~700MB thay vi
~10,6GB (dia / chi con ~8GB).

Nguon:
  OI   /home/ubuntu/claudedata/oi/oi_percoin_full.bin (140.924.110 x 30B; >i8 ts_ms, >i2 symId, 5x>f4)
       cot0=oi_delta24h cot1=oi_z cot2=ls_global cot3=ls_toptrader cot4=taker_buy
  GIA  /home/ubuntu/claudedata/rvb_1m/raw/<SYM>.f32 (ts <i4 phut tu 2021-01-01; o h l c v <f4)
  FUND Aerospike test/funding_data (CHI DOC)

Xuat /tmp/ls_study/: d24/oiz/lsg/lst/tak/c5/rg/f5 .npy (shape (NH,627) float32) + meta.json +
       events_5m.npz (gia tri 5m tai su kien MOM15 cho H3 overlay).

T0 = 2021-12-31 00:00 UTC (du 24h lookback cho H2 o moc DEV dau tien). Moc gio DEV dau = 24 (2022-01-01).
Thuan Python. Khong Java. Khong claude-run. Khong doc 2026 vao thong ke.
"""
import glob
import json
import logging
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

OUT = "/tmp/ls_study"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lsb")

OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
SYMMAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
POOLS = "/tmp/funding_factor/pools.npz"

UTC = timezone.utc
T0 = int(datetime(2021, 12, 31, tzinfo=UTC).timestamp())
T1 = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
T0_MIN = T0 // 60
NSTEP5 = (T1 - T0) // 300
NH = NSTEP5 // 12
H0 = 24
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 5)])
KDT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])
NAMES = ["d24", "oiz", "lsg", "lst", "tak"]


def main():
    t_all = time.time()
    sm = pd.read_csv(SYMMAP)
    s2i = dict(zip(sm["symbol"], sm["symId"]))
    files = sorted(glob.glob(RAW + "/*.f32"))
    syms = [os.path.basename(p)[:-4] for p in files]
    ids = np.array([s2i[s] for s in syms], dtype=np.int64)
    ncol = len(syms)
    i2c = {int(i): c for c, i in enumerate(ids)}
    log.info("NH=%d NSTEP5=%d ncol=%d T0=%s", NH, NSTEP5, ncol, datetime.fromtimestamp(T0, UTC))
    json.dump(dict(NH=NH, NSTEP5=NSTEP5, ncol=ncol, T0=T0, T1=T1, T0_MIN=T0_MIN, H0=H0,
                   syms=syms, symids=ids.tolist()), open(OUT + "/meta.json", "w"))

    # ---------- 1. OI: 5 cot tai moc GIO ----------
    if not os.path.exists(OUT + "/lsg.npy"):
        arrs = {}
        for nm in NAMES:
            arrs[nm] = np.lib.format.open_memmap(OUT + "/%s.npy" % nm, mode="w+", dtype=np.float32,
                                                 shape=(NH, ncol))
            arrs[nm][:] = np.nan
        mm = np.memmap(OI, dtype=OI_DT, mode="r")
        tot = len(mm)
        CH = 10_000_000
        kept = 0
        for s in range(0, tot, CH):
            b = mm[s:s + CH]
            ts = np.asarray(b["ts"], dtype=np.int64)
            m = (ts >= T0 * 1000) & (ts < T1 * 1000)
            if not m.any():
                continue
            stp = (ts[m] // 300000) - (T0 * 1000 // 300000)
            g = (stp >= 0) & (stp < NSTEP5) & (stp % 12 == 0)
            if not g.any():
                continue
            hp = (stp[g] // 12)
            sym = np.asarray(b["sym"], dtype=np.int64)[m][g]
            u, inv = np.unique(sym, return_inverse=True)
            cc = np.array([i2c.get(int(x), -1) for x in u], dtype=np.int64)
            ccv = cc[inv]
            ok = ccv >= 0
            f = np.asarray(b["f"], dtype=np.float32)[m][g]
            for k, nm in enumerate(NAMES):
                arrs[nm][hp[ok], ccv[ok]] = f[ok, k]
            kept += int(ok.sum())
            log.info("OI chunk %d/%d kept=%d el=%.0fs", s // CH, tot // CH, kept, time.time() - t_all)
        del mm
        for nm in NAMES:
            arrs[nm].flush()
        log.info("OI xong kept=%d el=%.0fs", kept, time.time() - t_all)
    else:
        log.info("OI cot gio co san -> bo qua")

    # ---------- 2. GIA: c5, rg tai moc GIO ----------
    if not os.path.exists(OUT + "/c5.npy"):
        c5 = np.lib.format.open_memmap(OUT + "/c5.npy", mode="w+", dtype=np.float32, shape=(NH, ncol))
        rg = np.lib.format.open_memmap(OUT + "/rg.npy", mode="w+", dtype=np.float32, shape=(NH, ncol))
        c5[:] = np.nan
        rg[:] = np.nan
        t1_min = int(T1 // 60)
        for c, p in enumerate(files):
            a = np.fromfile(p, dtype=KDT)
            ts = a["ts"].astype(np.int64)
            o = np.argsort(ts, kind="stable")
            ts = ts[o]
            _, u = np.unique(ts, return_index=True)
            ts = ts[u]; oo = o[u]
            g = (ts >= T0_MIN) & (ts < t1_min) & ((ts - T0_MIN) % 60 == 0)
            if not g.any():
                continue
            st = (ts[g] - T0_MIN) // 60
            cl = a["c"][oo][g].astype(np.float32)
            hl = a["h"][oo][g].astype(np.float32)
            ll = a["l"][oo][g].astype(np.float32)
            ok = cl > 0
            c5[st[ok], c] = cl[ok]
            rg[st[ok], c] = hl[ok] - ll[ok]
            if c % 100 == 0:
                log.info("GIA %d/%d el=%.0fs", c, ncol, time.time() - t_all)
        c5.flush(); rg.flush()
        log.info("GIA xong el=%.0fs", time.time() - t_all)
    else:
        log.info("c5/rg co san -> bo qua")

    # ---------- 3. FUNDING tich luy tai moc GIO ----------
    if not os.path.exists(OUT + "/f5.npy"):
        import aerospike
        import cramjam
        f5 = np.lib.format.open_memmap(OUT + "/f5.npy", mode="w+", dtype=np.float32, shape=(NH, ncol))
        f5[:] = 0.0
        cli = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 60000}}).connect()
        hr_ms = (np.arange(NH, dtype=np.int64) * 12 + (T0 * 1000 // 300000)) * 300000
        nmiss = 0
        for c, s in enumerate(syms):
            try:
                k = cli.get(("test", "funding_data", s))
                d = json.loads(bytes(cramjam.snappy.decompress_raw(k[2]["f_data"])))
                it = sorted((int(t), float(v)) for t, v in d.items())
                ft = np.array([x[0] for x in it], dtype=np.int64)
                fr = np.array([x[1] for x in it], dtype=np.float64)
                pos = np.searchsorted(ft, hr_ms, side="right")
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
        log.info("f5 co san -> bo qua")

    # ---------- 4. GIA TRI 5m tai su kien MOM15 (cho H3 overlay) ----------
    # CANH BAO (da sua): `m_sym` cua pools.npz la CHI SO COT 0-based (0..626, max = ncol-1) theo thu tu
    # sorted glob RAW/*.f32 — KHONG phai symId. Ban dau build nay so khop bang symId => SAI SYMBOL
    # (48,1% "khop" nhung lech coin). Sua: quy symId -> chi so cot truoc khi so khop.
    if not os.path.exists(OUT + "/events_5m.npz"):
        z = np.load(POOLS)
        m_min = z["m_min"].astype(np.int64)
        m_sym = z["m_sym"].astype(np.int64)   # CHI SO COT 0-based
        colmap = np.full(int(ids.max()) + 1, -1, dtype=np.int64)
        colmap[ids] = np.arange(ncol, dtype=np.int64)   # symId -> cot
        t0m = T0 // 60
        stp = (m_min - t0m) // 5
        off = m_min - (t0m + 5 * stp)
        keep = (stp >= 0) & (stp < NSTEP5) & (off <= 15)
        key = stp * 100000 + m_sym
        ordk = np.argsort(key, kind="stable")
        sk = key[ordk]
        vals = {nm: np.full(len(m_min), np.nan, dtype=np.float32) for nm in NAMES}
        mm = np.memmap(OI, dtype=OI_DT, mode="r")
        tot = len(mm)
        CH = 10_000_000
        nhit = 0
        for s in range(0, tot, CH):
            b = mm[s:s + CH]
            ts = np.asarray(b["ts"], dtype=np.int64)
            m = (ts >= T0 * 1000) & (ts < T1 * 1000)
            if not m.any():
                continue
            st = (ts[m] // 300000) - (T0 * 1000 // 300000)
            syid = np.asarray(b["sym"], dtype=np.int64)[m]
            sy = np.where(syid <= ids.max(), colmap[np.clip(syid, 0, ids.max())], -1)
            kk = st * 100000 + sy
            pos = np.searchsorted(sk, kk)
            pc = np.clip(pos, 0, len(sk) - 1)
            hit = (pc < len(sk)) & (sk[pc] == kk) & keep[ordk[pc]]
            if not hit.any():
                continue
            f = np.asarray(b["f"], dtype=np.float32)[m][hit]
            orig = ordk[pc[hit]]
            for i, nm in enumerate(NAMES):
                vals[nm][orig] = f[:, i]
            nhit += int(hit.sum())
            log.info("EV chunk %d/%d hit=%d el=%.0fs", s // CH, tot // CH, nhit, time.time() - t_all)
        del mm
        out = dict(vals)
        out["stp5"] = stp.astype(np.int64)
        out["off"] = off.astype(np.int64)
        np.savez_compressed(OUT + "/events_5m.npz", **out)
        log.info("EVENTS xong nhit=%d el=%.0fs", nhit, time.time() - t_all)

    open(OUT + "/BUILD_DONE", "w").write("ok %.0fs\n" % (time.time() - t_all))
    log.info("BUILD_DONE el=%.0fs", time.time() - t_all)


if __name__ == "__main__":
    main()
