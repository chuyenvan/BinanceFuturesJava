#!/usr/bin/env python3
"""S3_FUNDING — dung lai `funding.bin` cua WFO dataset tu thu muc bins selector, BYTE-FAITHFUL.

Ban dich Python CUA:
  WfoDataset.buildFundingFromWfFiles(predDir, horizonIdx)   (+ WfFileMeta: md5/ts-range/rec)
  WfoDataset.forwardFillToGrid(src15m, marketGrid, staleMs)

Doc `src/main/java/com/binance/chuyennd/ai_ml/wfo/framework/WfoDataset.java`:
  * bins 26 B/rec big-endian `>q h 4f`: ts, symId(int16), p4h, p12h, p24h, p72h
  * `score = 1.0f - pwin` (DAO DAU), `encoded = ((long) symId << 32) | (rawIntBits(score) & 0xFFFFFFFFL)`
  * NaN pwin -> BO
  * file doc theo TEN TANG DAN; trong file theo THU TU RECORD (=> thu tu mang `long[]` moi moc)
  * forward-fill: voi moi moc phut trong luoi market, lay `floorEntry(15m)`; bo neu
    `t - floorKey > staleMs` (mac dinh 900000 ms) hoac truoc moc dau tien
  * `writeFunding`: `int n` (BE) ; moi moc: `long ts`, `int len`, `len` x `long`
  * guard overlap ts-range giua cac file (per-fold phai ROI NHAU) -> THROW

Dung (khong thay doi format):
  python3 s3_funding.py --bins <dir> --data <dir chua market.bin> --out <funding.bin>
                       [--horizon 0] [--stale-min 15] [--json <path>]

Ghi JSON: md5, bytes, fundingCount, fundingRaw15mCount, foldCount, maxFoldSpanDays,
leakFreeFrom, binsSha256 (noi tiep file sort ten), va `predictWf.*` (md5/ts/span/rec).
KHONG in ra stdout ban du lieu lon; chi log 1 dong/1 file (nhu ban Java).
"""
import argparse
import hashlib
import json
import logging
import os
import sys
import time

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("s3_funding")

REC = 26
BE_I8 = np.dtype(">i8")
BE_I4 = np.dtype(">i4")
BE_F4 = np.dtype(">f4")


def md5_file(path, chunk=1 << 22):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def sha256_files_concat(paths):
    """Giong BinsProvenance.sha256: sha256 tren noi dung NOI TIEP cac file sort theo ten."""
    h = hashlib.sha256()
    for p in paths:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 22), b""):
                h.update(b)
    return h.hexdigest()


def read_market_keys(market_bin):
    """market.bin: int n (BE); moi ban ghi: long ts, 3 x float."""
    n = np.frombuffer(open(market_bin, "rb").read(4), dtype=BE_I4)[0]
    a = np.memmap(market_bin, dtype=np.uint8, mode="r", offset=4)
    row = np.dtype([("ts", ">i8"), ("a", ">f4"), ("b", ">f4"), ("c", ">f4")])
    m = np.frombuffer(a, dtype=row, count=int(n))
    return np.asarray(m["ts"], dtype=np.int64), int(n)


def read_bins_file(path):
    """-> ts (int64), sym (int16), pwin (float32 horizon 0)."""
    n = os.path.getsize(path) // REC
    row = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"),
                    ("p2", ">f4"), ("p3", ">f4")])
    m = np.memmap(path, dtype=row, mode="r", shape=(n,))
    return np.asarray(m["ts"], dtype=np.int64), np.asarray(m["sym"], dtype=np.int16), \
        np.asarray(m["p0"], dtype=np.float32)


def build_funding(bins_dir, market_keys, horizon_idx=0, stale_ms=900000):
    files = sorted(f for f in os.listdir(bins_dir)
                   if f.startswith("predict_wf_") and f.endswith(".bin"))
    if not files:
        raise SystemExit("S3_FAIL: khong thay predict_wf_*.bin trong %s" % bins_dir)
    paths = [os.path.join(bins_dir, f) for f in files]
    ts_all, enc_all, meta, ranges = [], [], [], []
    for f, p in zip(files, paths):
        ts, sym, p0 = read_bins_file(p)
        keep = ~np.isnan(p0)
        score = (np.float32(1.0) - p0[keep]).astype(np.float32)
        enc = (sym[keep].astype(np.int64) << 32) | (score.view(np.int32).astype(np.int64)
                                                   & 0xFFFFFFFF)
        ts_all.append(ts[keep])
        enc_all.append(enc)
        tmin, tmax = int(ts.min()), int(ts.max())
        for r in ranges:                                   # guard: per-fold phai ROI NHAU
            if tmin <= r[1] and r[0] <= tmax:
                raise SystemExit("S3_FAIL: LEAK-SUSPECT predict_wf (%s vs %s)" % (f, r))
        ranges.append((tmin, tmax))
        meta.append(dict(name=f, path=p, md5=md5_file(p), minTs=tmin, maxTs=tmax,
                         nrec=int(len(ts)), nan_drop=int((~keep).sum())))
        LOG.info("  doc %s: %d rec (kept=%d)", f, len(ts), int(keep.sum()))
    ts_cat = np.concatenate(ts_all)
    enc_cat = np.concatenate(enc_all)
    ts_cat, enc_cat = ts_cat[keep_order := np.argsort(ts_cat, kind="stable")], enc_cat[keep_order]
    uniq, counts = np.unique(ts_cat, return_counts=True)
    offs = np.concatenate([[0], np.cumsum(counts)])
    LOG.info("buildFundingFromWfFiles: horizon=%d | %d file | %d rec | %d moc 15m",
             horizon_idx, len(files), len(ts_cat), len(uniq))
    # forward-fill
    idx = np.searchsorted(uniq, market_keys, side="right") - 1
    ok = idx >= 0
    ok[ok] &= (market_keys[ok] - uniq[idx[ok]]) <= stale_ms
    keys_out = market_keys[ok]
    grp = idx[ok]
    LOG.info("forwardFillToGrid: grid=%d filled=%d beforeFirst=%d skippedStale=%d",
             len(market_keys), len(keys_out), int((idx < 0).sum()),
             int(((idx >= 0) & ~ok).sum()))
    return keys_out, enc_cat, offs, grp, uniq, meta, paths


def write_funding(path, keys_out, enc_cat, offs, grp, md5_only=False):
    """Ghi funding.bin dung layout DataOutputStream (BE). Tra (md5, nbytes).

    md5_only=True: KHONG ghi dia, chi bam md5 incremental tren CHUOI BYTE DAY DU
    (dung khi dia khong du cho 4,4 GB ma van muon kiem byte-faithful).
    """
    import hashlib as _h
    n = len(keys_out)
    payload = [enc_cat[offs[i]:offs[i + 1]].astype(BE_I8).tobytes() for i in range(len(offs) - 1)]
    ts_b = np.asarray(keys_out, dtype=BE_I8).tobytes()
    ln_b = np.asarray(offs[grp + 1] - offs[grp], dtype=BE_I4).tobytes()
    head = np.asarray([n], dtype=BE_I4).tobytes()
    h = _h.md5()
    h.update(head)
    nb = len(head)
    t0 = time.time()
    f = None if md5_only else open(path, "wb", buffering=1 << 26)
    if f is not None:
        f.write(head)
    for k in range(n):
        chunk = ts_b[k * 8:(k + 1) * 8] + ln_b[k * 4:(k + 1) * 4] + payload[grp[k]]
        h.update(chunk)
        nb += len(chunk)
        if f is not None:
            f.write(chunk)
    if f is not None:
        f.close()
    LOG.info("writeFunding%s: %d moc | %.1f MB | %.0fs | md5=%s",
             " (md5-only)" if md5_only else "", n, nb / 1e6, time.time() - t0, h.hexdigest())
    return h.hexdigest(), nb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins", required=True)
    ap.add_argument("--data", required=True, help="thu muc chua market.bin")
    ap.add_argument("--out", required=True, help="duong dan funding.bin")
    ap.add_argument("--horizon", type=int, default=0)
    ap.add_argument("--stale-min", type=int, default=15)
    ap.add_argument("--json", default=None)
    ap.add_argument("--md5-only", action="store_true",
                    help="bam md5 khong ghi dia (dia nho, kiem byte-faithful)")
    a = ap.parse_args()
    t0 = time.time()
    market_keys, market_n = read_market_keys(os.path.join(a.data, "market.bin"))
    keys_out, enc_cat, offs, grp, uniq, meta, paths = build_funding(
        a.bins, market_keys, a.horizon, a.stale_min * 60000)
    md5f, nb = write_funding(a.out, keys_out, enc_cat, offs, grp, md5_only=a.md5_only)
    span = max((m["maxTs"] - m["minTs"]) // 86400000 for m in meta) if meta else 0
    res = dict(bins_dir=os.path.abspath(a.bins), horizon=a.horizon,
               marketCount=market_n, fundingCount=int(len(keys_out)),
               fundingRaw15mCount=int(len(uniq)),
               md5_funding=md5f, bytes=nb,
               foldCount=len(meta), maxFoldSpanDays=int(span),
               binsSha256=sha256_files_concat(paths),
               minTs=int(keys_out.min()) if len(keys_out) else None,
               maxTs=int(keys_out.max()) if len(keys_out) else None,
               secs=round(time.time() - t0, 1), predictWf=meta)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=1)
    LOG.info("S3_FUNDING_OK md5=%s fundingCount=%d raw15m=%d foldCount=%d secs=%.1f",
             res["md5_funding"], res["fundingCount"], res["fundingRaw15mCount"],
             res["foldCount"], res["secs"])


if __name__ == "__main__":
    main()
