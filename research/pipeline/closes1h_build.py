#!/usr/bin/env python3
"""closes1h_build.py — GENERATOR cho `/home/ubuntu/java/fsrun/CLOSES_1H.bin`.

BOI CANH (TASK F0, docs/plan/E3_HOLDOUT_2026_PREP.md muc 2.1): moi file tren dia/git deu
la READER cua CLOSES_1H.bin (VolTargetSizing.java, PacingSizing.java, feat_v2_build.py,
fs_dl.py ...). Khong co file nao GHI ra no. Script nay la generator.

DINH DANG (doc tu reader Java + do truc tiep file):
  ban ghi 14 byte big-endian `[ts:int64][symId:int16][close:float32]`.
  - ts = open_time + 3600000  (tuc la CLOSE time cua nen 1h; docs/prereg/PREREG_FS.md muc 0
    va docs/result/FS_RESULT.md muc 0.1 da DO: `CLOSES_1H.bin[t] == close cua kline co
    open_time = t - 1h`, sai so tuong doi max 4.14e-08 = float32 rounding).
  - symId = id trong /home/ubuntu/selector_pred_out/symbol_map.csv.
  - close = close nen 1h, float32 (float64 parse tu CSV -> float32, y het fs_dl.py da do khop).

THU TU (quyet dinh byte-identity):
  sap tang dan theo ts; TRONG CUNG ts, sap alphabet theo TEN symbol (do truc tiep, khong
  doan: 78 sym o ts dau tien xep dung thu tu 1INCHUSDT..ZRXUSDT). 0 trung khoa (ts,symId).

NGUON: Binance Vision futures UM kline 1h
  https://data.binance.vision/data/futures/um/monthly/klines/{SYM}/1h/{SYM}-1h-{YYYY-MM}.zip
  Thang 2021-01 .. 2025-12 (candle cuoi cua 2025 dong o 2026-01-01 00:00 nam trong file 2025-12).

CHAY:
  OUT=/home/ubuntu/f0_repro/CLOSES_1H.bin python3 research/pipeline/closes1h_build.py
  Thoi gian do duoc: ~15 phut (627 symbol x 60 thang, tai song song 20 threads, giai nen
  trong bo nho, khong bung CSV ra dia).

CAC CANH BAO:
  - thang thieu (symbol chua list / da delist) -> HTTP 404 -> bo qua (khong phai loi).
  - file 404 va thang khong co du lieu deu cho ket qua rong, khong cham tinh toan.
  - KHONG ghi de file dang dung: ghi ra OUT (thu muc moi), khong cham /home/ubuntu/java/fsrun/.
"""
import io
import logging
import os
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
LOG = logging.getLogger("closes1h")

# --- cau hinh ---
SRC_BIN = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"          # file tham chieu (chua bi ghi de)
MAP_CSV = "/home/ubuntu/selector_pred_out/symbol_map.csv"  # symId <-> symbol
OUT = os.environ.get("OUT", "/home/ubuntu/f0_repro/CLOSES_1H.bin")
VISION = "https://data.binance.vision/data/futures/um/monthly/klines"
MONTHS = [f"{y}-{m:02d}" for y in range(2021, 2026) for m in range(1, 13)]  # 2021-01..2025-12
HOUR_MS = 3_600_000
COLS = ["ot", "o", "h", "l", "c", "v", "ct", "qv", "n", "tbv", "tbqv", "ig"]
NTHREADS = int(os.environ.get("NTHREADS", "20"))


def universe():
    """627 symId co trong CLOSES_1H.bin (chi nhung symId THUC SU co du lieu, khong phai toan map)."""
    dt = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(SRC_BIN, dtype=dt)
    uids = np.unique(a["sym"].astype(np.int32))
    mp = pd.read_csv(MAP_CSV)
    i2s = dict(zip(mp.symId, mp.symbol))
    uni = [(int(s), i2s[int(s)]) for s in uids if int(s) in i2s]
    LOG.info("universe %d symbol (tu %s); MONTHS %s", len(uni), SRC_BIN, f"{MONTHS[0]}..{MONTHS[-1]}")
    return uni


def one_month(sym, ym):
    q = urllib.parse.quote(sym)   # URL-encode (vd '币安人生USDT' co ky tu non-ASCII)
    url = f"{VISION}/{q}/1h/{q}-1h-{ym}.zip"
    for att in range(3):
        try:
            raw = urllib.request.urlopen(url, timeout=90).read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + att)
        except Exception:
            time.sleep(1 + att)
    else:
        LOG.info("FAIL %s %s", sym, ym)
        return None
    z = zipfile.ZipFile(io.BytesIO(raw))
    K = pd.read_csv(z.open(z.namelist()[0]), header=None, names=COLS, dtype=str)
    K = K[pd.to_numeric(K.ot, errors="coerce").notna()]
    if len(K) == 0:
        return None
    ot = pd.to_numeric(K.ot).astype(np.int64).to_numpy()
    c = pd.to_numeric(K.c, errors="coerce").astype(np.float32).to_numpy()
    return ot, c


def one_sym(sid, sym):
    """Tai toan bo thang, tra ve (ts, close) arrays (ts = open_time + 1h)."""
    parts = [one_month(sym, ym) for ym in MONTHS]
    parts = [p for p in parts if p is not None]
    if not parts:
        return sid, np.zeros(0, np.int64), np.zeros(0, np.float32)
    ot = np.concatenate([p[0] for p in parts])
    c = np.concatenate([p[1] for p in parts])
    o = np.argsort(ot, kind="stable")
    ot, c = ot[o], c[o]
    _, keep = np.unique(ot, return_index=True)
    ot, c = ot[keep], c[keep]
    ts = ot + HOUR_MS
    return sid, ts, c


def main():
    uni = universe()
    # xep symbol theo TEN (thu tu trong cung ts) -> gan rank, dung lam khoa phu de sort
    uni_sorted = sorted(uni, key=lambda x: x[1])
    name_rank = {sid: i for i, (sid, _) in enumerate(uni_sorted)}

    rec_ts, rec_sym, rec_close, rec_nr = [], [], [], []
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=NTHREADS) as ex:
        futs = [ex.submit(one_sym, sid, sym) for sid, sym in uni]
        for fu in as_completed(futs):
            sid, ts, c = fu.result()
            done += 1
            if len(ts):
                rec_ts.append(ts)
                rec_sym.append(np.full(len(ts), sid, dtype=np.int16))
                rec_close.append(c)
                rec_nr.append(np.full(len(ts), name_rank[sid], dtype=np.int32))
            if done % 50 == 0:
                LOG.info("%d/%d sym, %.0fs", done, len(uni), time.time() - t0)

    ts = np.concatenate(rec_ts)
    sym = np.concatenate(rec_sym)
    close = np.concatenate(rec_close)
    nr = np.concatenate(rec_nr)
    LOG.info("raw %d rec, %.0fs; dang sort (ts asc, name asc)", len(ts), time.time() - t0)

    # sort on dinh theo (ts, name_rank) -> dung thu tu cua file goc
    order = np.lexsort((nr, ts))
    ts, sym, close = ts[order], sym[order], close[order]
    del nr, order

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    arr = np.empty(len(ts), dtype=DT)
    arr["ts"] = ts
    arr["sym"] = sym
    arr["c"] = close
    arr.tofile(OUT)
    LOG.info("ghi %s: %d rec = %d bytes (%.0fs)", OUT, len(arr), len(arr) * 14, time.time() - t0)
    # kiem tra nhanh: 0 trung khoa
    LOG.info("DONE")


if __name__ == "__main__":
    main()
