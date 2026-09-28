#!/usr/bin/env python3
"""TRACKB step 1a — dung PANEL ngay (daily) cho book cross-section market-neutral.

Pre-reg: docs/prereg/PREREG_TRACKB_CROSSSECTION.md (commit 642afbd) — chot TRUOC khi do.

Nguon (doc-only):
  GIA      /home/ubuntu/java/fsrun/CLOSES_1H.bin   (>i8 ts, >i2 sym, >f4 close; 627 sym, 1h)
  FUNDING  Aerospike local test.funding_data .f_data = Snappy(JSON {ts_ms: rate})
  DELTA-OI /home/ubuntu/claudedata/oi/oi_percoin_full.bin (cot0=oi_delta24h cot1=oi_z)
  LIQ      Aerospike local test.kline_1m_opt (protobuf Snappy) — 1 ngay/mau, tinh USD volume

Xuat /tmp/trackb/panel.npz (float32, nho) + meta.json. Thuan Python, khong sim, khong 2026 vao thong ke.
"""
import glob
import json
import os
import struct
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
from devexport_202609 import parse_minute  # protobuf minute parser (da kiem o repo)

OUT = "/tmp/trackb"
os.makedirs(OUT, exist_ok=True)
UTC = timezone.utc
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
SYMMAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
H0 = 1609459200000          # 2021-01-01 00:00 UTC (ms)
T1 = 1767225600000          # 2026-01-01 00:00 UTC
NDAY = 1826                 # so ngay 2021-01-01 .. 2025-12-31 (luoi gio = 43824 = 1826*24)
HI = NDAY * 24              # so gio kha dung
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 5)])


def log(*a):
    print(*a, flush=True)


def main():
    t0 = time.time()
    mp = pd.read_csv(SYMMAP)
    i2s = dict(zip(mp.symId.astype(int), mp.symbol))
    sm = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
    s2i = dict(zip(sm["symbol"], sm["symId"].astype(int)))
    del sm

    # ---------------- 1. GIA: ma tran gio ----------------
    a = np.fromfile(CLOSES, dtype=np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")]))
    ts = a["ts"].astype(np.int64)
    sy = a["sym"].astype(np.int64)
    cc = a["c"].astype(np.float32)
    del a
    log("closes raw n=%d" % len(ts))
    # luoi gio: h = (ts - H0)/3600000 ; chi giu ts < T1 va %3600000==0
    m = (ts >= H0) & (ts < T1) & (ts % 3600000 == 0)
    ts = ts[m]; sy = sy[m]; cc = cc[m]
    NH = int((T1 - H0) // 3600000)                     # 43824 gio
    syms_all = sorted(set(int(x) for x in np.unique(sy)))   # symId co trong panel gia
    cidx = {s: i for i, s in enumerate(syms_all)}
    NS = len(syms_all)
    H = np.full((NH, NS), np.nan, dtype=np.float32)
    hh = ((ts - H0) // 3600000).astype(np.int64)
    col = np.array([cidx[int(x)] for x in sy], dtype=np.int64)
    H[hh, col] = cc
    del ts, sy, cc, hh, col
    log("H %s (%.0fs)" % (H.shape, time.time() - t0))

    # ---------------- 2. daily grid + tin hieu gia ----------------
    d_idx = np.arange(0, NDAY) * 24                      # gio tai 00:00 UTC moi ngay
    D = H[d_idx]                                         # (NDAY, NS)
    # fwd 24h, lo/hi trong 24h toi
    fwd = np.full_like(D, np.nan)
    fwd[:-1] = D[1:] / D[:-1] - 1.0
    lo24 = np.full_like(D, np.nan)
    hi24 = np.full_like(D, np.nan)
    for i in range(NDAY - 1):
        seg = H[d_idx[i] + 1: min(d_idx[i] + 25, HI)]
        if seg.shape[0] == 0:
            continue
        lo24[i] = np.nanmin(seg, axis=0)
        hi24[i] = np.nanmax(seg, axis=0)
    # vol 168h (std log-ret 1h) va ret 168h
    with np.errstate(divide="ignore", invalid="ignore"):
        R = np.diff(np.log(H), axis=0)                   # (NH-1, NS)
    R = np.where(np.isfinite(R), R, np.nan)
    vol168 = np.full((NDAY, NS), np.nan, dtype=np.float32)
    ret168 = np.full((NDAY, NS), np.nan, dtype=np.float32)
    for i in range(NDAY):
        g = d_idx[i]
        if g >= 169:
            vol168[i] = np.nanstd(R[g - 168: g], axis=0)
            ret168[i] = D[i] / D[i - 7] - 1.0
    del R, H
    log("daily signals done (%.0fs)" % (time.time() - t0))

    # ---------------- 3. FUNDING: tong 24h ----------------
    import aerospike
    import cramjam
    c = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 60000}}).connect()
    # luoi 8h (chu ky funding) — vector hoa, khong vong lap Python theo ngay
    STEP8 = 8 * 3600 * 1000
    NBIN = int((T1 - H0) // STEP8)
    FR8 = np.full((NBIN, NS), np.nan, dtype=np.float32)
    miss = 0
    for j, s in enumerate(syms_all):
        nm = i2s.get(s)
        if nm is None:
            miss += 1
            continue
        try:
            k = c.get(("test", "funding_data", nm))
            d = json.loads(bytes(cramjam.snappy.decompress_raw(k[2]["f_data"])))
            ft = np.array([int(t) for t in d], dtype=np.int64)
            fr = np.array([float(d[str(t)]) if str(t) in d else d[t] for t in ft], dtype=np.float32)
            b = (ft - H0) // STEP8
            ok = (b >= 0) & (b < NBIN)
            FR8[b[ok], j] = fr[ok]
        except Exception:
            miss += 1
    day_bin = (np.arange(NDAY, dtype=np.int64) * 86400000) // STEP8      # bin chua moc 00:00
    # cua so (t-24h, t] = 3 bin: [b-2, b-1, b]
    idxs = np.stack([np.clip(day_bin - 2, 0, NBIN - 1), np.clip(day_bin - 1, 0, NBIN - 1),
                     np.clip(day_bin, 0, NBIN - 1)], axis=0)              # (3, NDAY)
    W = FR8[idxs]                                                        # (3, NDAY, NS)
    fin = np.isfinite(W)
    fsum = np.where(fin.any(axis=0), np.nansum(W, axis=0), np.nan).astype(np.float32)
    fmax = np.where(fin.any(axis=0), np.nanmax(np.abs(W), axis=0), np.nan).astype(np.float32)
    del W, FR8
    log("funding xong miss=%d (%.0fs)" % (miss, time.time() - t0))

    # ---------------- 4. DELTA-OI tai moc 00:00 ----------------
    oid = np.full((NDAY, NS), np.nan, dtype=np.float32)
    oiz = np.full((NDAY, NS), np.nan, dtype=np.float32)
    colmap = np.full(int(max(syms_all)) + 1, -1, dtype=np.int64)
    for s, j in cidx.items():
        colmap[s] = j
    mm = np.memmap(OI, dtype=OI_DT, mode="r")
    tot = len(mm)
    CH = 20_000_000
    kept = 0
    for s0 in range(0, tot, CH):
        b = mm[s0:s0 + CH]
        tts = np.asarray(b["ts"], dtype=np.int64)
        m = (tts >= H0) & (tts < T1) & (tts % 86400000 == 0)
        if not m.any():
            continue
        row = ((tts[m] - H0) // 86400000).astype(np.int64)
        syv = np.asarray(b["sym"], dtype=np.int64)[m]
        colv = np.where(syv <= len(colmap) - 1, colmap[np.clip(syv, 0, len(colmap) - 1)], -1)
        f = np.asarray(b["f"], dtype=np.float32)[m]
        ok = colv >= 0
        oid[row[ok], colv[ok]] = f[ok, 0]
        oiz[row[ok], colv[ok]] = f[ok, 1]
        kept += int(ok.sum())
    del mm
    log("OI xong kept=%d (%.0fs)" % (kept, time.time() - t0))

    # ---------------- 5. THANH KHOAN: ngay 15 moi thang ----------------
    sample_days = []
    for y in range(2021, 2026):
        for mo in range(1, 13):
            sample_days.append((y, mo))
    dv = {}   # symId -> list USD volume
    for (y, mo) in sample_days:
        key_day = "%04d%02d15" % (y, mo)
        if (y, mo) == (2025, 12):
            key_day = "20251215"
        tot_usd = {}
        nrec = 0
        for h in range(24):
            for mi in range(0, 60, 15):     # 4 phut/15' -> 96 record/ngay (du de uoc luong)
                kk = "%s-%02d%02d" % (key_day, h, mi)
                try:
                    r = c.get(("test", "kline_1m_opt", kk))[2]["data"]
                except Exception:
                    continue
                try:
                    sy_list, arr = parse_minute(r)
                except Exception:
                    continue
                nrec += 1
                for k, nm in enumerate(sy_list):
                    v = float(arr[k, 4])
                    if v > 0:
                        tot_usd[nm] = tot_usd.get(nm, 0.0) + v
        if nrec == 0:
            continue
        for nm, v in tot_usd.items():
            sid = s2i.get(nm)
            if sid is not None:
                dv.setdefault(sid, []).append(v * 15.0)   # scale: 15' sample -> full day
        log("liq %s nrec=%d nsym=%d (%.0fs)" % (key_day, nrec, len(tot_usd), time.time() - t0))
    dv_med = np.full(NS, np.nan, dtype=np.float32)
    dv_n = np.zeros(NS, dtype=np.int32)
    for sid, arr in dv.items():
        if sid in cidx:
            j = cidx[sid]
            dv_med[j] = float(np.median(arr))
            dv_n[j] = len(arr)
    log("liq med done nsym=%d (%.0fs)" % (int(np.isfinite(dv_med).sum()), time.time() - t0))

    np.savez(OUT + "/panel.npz", D=D, fwd=fwd, lo24=lo24, hi24=hi24, vol168=vol168,
             ret168=ret168, fsum=fsum, fmax=fmax, oid=oid, oiz=oiz, dv_med=dv_med, dv_n=dv_n)
    json.dump(dict(syms=syms_all, sym_names=[i2s.get(s) for s in syms_all],
                   NDAY=NDAY, NS=NS, H0=H0, T1=T1, mp_kv=None), open(OUT + "/meta.json", "w"))
    log("PANEL_DONE %.0fs size=%.1fMB" % (time.time() - t0, os.path.getsize(OUT + "/panel.npz") / 1e6))


if __name__ == "__main__":
    main()
