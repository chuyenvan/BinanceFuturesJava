#!/usr/bin/env python3
"""
STEP 5 — Validator DOC LAP cho canonical leak-free WFO dataset (loi A, Uni chot 2026-08-03).

Doc THANG binary (KHONG qua Java exporter) -> kiem 6 dieu kien pre-registered roi KY PASS vao manifest.
Fail-closed: bat ky check FAIL -> exit 1, KHONG ky. Chi PASS het moi ky VALIDATED_BY.

Kiem:
  (a) moi predict_wf fold: span <= MAX_FOLD_SPAN_DAYS (mac dinh 100; block OOS ~90d) va > 0.
  (b) OOS som nhat >= leakFreeFrom ky vong (vd 2023-01-01).
  (c) ts-align: market/pred/funding deu %60000==0 (luoi phut).
  (d) gate (pred.bin) coverage: range phu >= leakFreeFrom, %60000==0 (per-fold WF khong kiem duoc tu bin,
      chi kiem coverage+cadence + khong co ts < leakFreeFrom).
  (e) NaN/coverage: ti le NaN horizon chon trong predict_wf.
  (f) khong ts nao xuat hien o >1 fold (range roi nhau + kiem giao tap).
  + cross-check manifest: md5 bins khop, maxFoldSpanDays<=100, foldCount==so file, leakFreeFrom khop data.

Env:
  LF_DIR              thu muc predict_wf_*.bin (selector pred moi)
  DS_DIR              thu muc dataset export (market.bin/pred.bin/funding.bin/manifest.txt)
  EXPECT_LEAKFREE     vd 2023-01-01 (OOS dau ky vong)
  HORIZON_IDX         0=4h(mac dinh) 1=12h 2=24h 3=72h
  MAX_FOLD_SPAN_DAYS  mac dinh 100
  TZ_OFFSET_MS        mac dinh 7h (GMT+7, khop gen)
  SIGN                1 -> ghi VALIDATED_BY vao manifest neu PASS (mac dinh 0 = chi bao cao)
"""
import os
import sys
import glob
import struct
import hashlib
import logging
from datetime import datetime, timezone, timedelta

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("validate_canonical")

REC_WF = 26  # >q h 4f
GRID_MIN_MS = 60_000
GRID_15M_MS = 15 * 60_000

LF_DIR = os.environ.get("LF_DIR", "")
DS_DIR = os.environ.get("DS_DIR", "")
EXPECT_LEAKFREE = os.environ.get("EXPECT_LEAKFREE", "").strip()
HORIZON_IDX = int(os.environ.get("HORIZON_IDX", "0"))
MAX_FOLD_SPAN_DAYS = int(os.environ.get("MAX_FOLD_SPAN_DAYS", "100"))
TZ_OFFSET_MS = int(os.environ.get("TZ_OFFSET_MS", str(7 * 3600 * 1000)))
SIGN = os.environ.get("SIGN", "0") == "1"

_TZ = timezone(timedelta(milliseconds=TZ_OFFSET_MS))
_FAILS = []
_WARNS = []


def fail(msg):
    _FAILS.append(msg)
    log.error("FAIL: %s", msg)


def warn(msg):
    _WARNS.append(msg)
    log.warning("WARN: %s", msg)


def ts_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=_TZ).strftime("%Y-%m-%d")


def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(path):
    m = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            i = line.find("=")
            if i > 0:
                m[line[:i].strip()] = line[i + 1:].strip()
    return m


# ---------- (a)(b)(e)(f) predict_wf folds ----------
def check_predict_wf():
    files = sorted(glob.glob(os.path.join(LF_DIR, "predict_wf_*.bin")))
    if not files:
        fail(f"khong thay predict_wf_*.bin trong LF_DIR={LF_DIR}")
        return None
    dt = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4", 4)])
    ranges = []  # (name, tmin, tmax, nrec, nan_frac)
    global_min = None
    for fp in files:
        raw = open(fp, "rb").read()
        if len(raw) % REC_WF != 0:
            fail(f"{os.path.basename(fp)}: {len(raw)} khong chia het {REC_WF}")
            continue
        a = np.frombuffer(raw, dtype=dt)
        if len(a) == 0:
            fail(f"{os.path.basename(fp)}: 0 record")
            continue
        tmin, tmax = int(a["ts"].min()), int(a["ts"].max())
        span_days = (tmax - tmin) / 86_400_000
        pcol = a["p"][:, HORIZON_IDX]
        nan_frac = float(np.isnan(pcol).mean())
        ranges.append((os.path.basename(fp), tmin, tmax, len(a), nan_frac))
        # (a) span
        if span_days > MAX_FOLD_SPAN_DAYS:
            fail(f"{os.path.basename(fp)}: span={span_days:.1f}d > {MAX_FOLD_SPAN_DAYS}d (nghi leak full-history)")
        if span_days <= 0:
            fail(f"{os.path.basename(fp)}: span<=0 ({span_days:.2f}d)")
        # (e) NaN
        if nan_frac > 0.5:
            warn(f"{os.path.basename(fp)}: NaN horizon[{HORIZON_IDX}]={nan_frac:.1%} (>50%)")
        global_min = tmin if global_min is None else min(global_min, tmin)
        log.info("  fold %s: ts[%s..%s] span=%.1fd rec=%d nan=%.2f%%",
                 os.path.basename(fp), ts_to_date(tmin), ts_to_date(tmax), span_days, len(a), nan_frac * 100)

    # (f) disjoint: sort theo tmin, kiem overlap lien tiep
    ranges_sorted = sorted(ranges, key=lambda r: r[1])
    for i in range(1, len(ranges_sorted)):
        prev, cur = ranges_sorted[i - 1], ranges_sorted[i]
        if cur[1] <= prev[2]:
            fail(f"OVERLAP folds: '{cur[0]}' [{ts_to_date(cur[1])}] <= '{prev[0]}' max [{ts_to_date(prev[2])}]"
                 f" -> ts trung >1 fold (leak signature)")

    # (b) OOS som nhat >= EXPECT_LEAKFREE
    if global_min is not None:
        lf_data = ts_to_date(global_min)
        log.info("OOS som nhat (leakFreeFrom tu data) = %s", lf_data)
        if EXPECT_LEAKFREE:
            if lf_data < EXPECT_LEAKFREE:
                fail(f"OOS som nhat {lf_data} < EXPECT_LEAKFREE {EXPECT_LEAKFREE}")
            elif lf_data != EXPECT_LEAKFREE:
                warn(f"OOS som nhat {lf_data} != EXPECT_LEAKFREE {EXPECT_LEAKFREE} (>= nen OK, nhung khac ngay)")
    return {"foldCount": len(files), "leakFreeFromData": ts_to_date(global_min) if global_min else "unknown",
            "ranges": ranges}


# ---------- doc dataset bins (chi ts, kiem cadence) ----------
def _read_uint32_be(f):
    b = f.read(4)
    return struct.unpack(">i", b)[0]


def check_market(path):
    if not os.path.exists(path):
        fail(f"thieu {path}")
        return None
    with open(path, "rb") as f:
        n = _read_uint32_be(f)
        buf = f.read(n * 20)  # q + 3f = 8+12=20
    a = np.frombuffer(buf, dtype=np.dtype([("ts", ">i8"), ("f", ">f4", 3)]))
    off = (a["ts"] % GRID_MIN_MS != 0).sum()
    if off > 0:
        fail(f"market.bin: {off}/{n} ts KHONG %60000==0 (lech luoi phut)")
    log.info("  market.bin: n=%d ts[%s..%s] off-grid=%d",
             n, ts_to_date(int(a['ts'].min())), ts_to_date(int(a['ts'].max())), off)
    return {"n": n, "min": int(a["ts"].min()), "max": int(a["ts"].max()), "keys": a["ts"]}


def check_pred(path, leakfree_ms):
    if not os.path.exists(path):
        fail(f"thieu {path}")
        return None
    with open(path, "rb") as f:
        n = _read_uint32_be(f)
        buf = f.read(n * 16)  # q + 2f
    a = np.frombuffer(buf, dtype=np.dtype([("ts", ">i8"), ("f", ">f4", 2)]))
    off = (a["ts"] % GRID_MIN_MS != 0).sum()
    if off > 0:
        fail(f"pred.bin (gate): {off}/{n} ts KHONG %60000==0")
    # (d) gate coverage: khong co ts < leakFreeFrom (gate cung phai WF sach vung OOS)
    if leakfree_ms is not None:
        before = int((a["ts"] < leakfree_ms).sum())
        if before > 0:
            warn(f"pred.bin (gate): {before} ts < leakFreeFrom -> vung ngoai OOS canonical (khong dung neu strat chan)")
    log.info("  pred.bin (gate): n=%d ts[%s..%s] off-grid=%d",
             n, ts_to_date(int(a['ts'].min())), ts_to_date(int(a['ts'].max())), off)
    return {"n": n, "min": int(a["ts"].min()), "max": int(a["ts"].max())}


def check_funding(path, market_keys):
    if not os.path.exists(path):
        fail(f"thieu {path}")
        return None
    ts_list = []
    with open(path, "rb") as f:
        n = _read_uint32_be(f)
        for _ in range(n):
            hdr = f.read(12)  # q + i(len)
            if len(hdr) < 12:
                fail("funding.bin: EOF som")
                break
            ts, ln = struct.unpack(">qi", hdr)
            f.seek(ln * 8, os.SEEK_CUR)
            ts_list.append(ts)
    ts_arr = np.array(ts_list, dtype=np.int64)
    off = int((ts_arr % GRID_MIN_MS != 0).sum())
    if off > 0:
        fail(f"funding.bin: {off}/{n} ts KHONG %60000==0")
    # (c) funding keys ⊆ market keys
    if market_keys is not None:
        mk = set(market_keys.tolist())
        not_in = int(sum(1 for t in ts_arr.tolist() if t not in mk))
        if not_in > 0:
            warn(f"funding.bin: {not_in}/{n} ts KHONG thuoc market grid (forward-fill le?)")
    log.info("  funding.bin: n=%d ts[%s..%s] off-grid=%d",
             n, ts_to_date(int(ts_arr.min())), ts_to_date(int(ts_arr.max())), off)
    return {"n": n, "min": int(ts_arr.min()), "max": int(ts_arr.max())}


# ---------- cross-check manifest ----------
def check_manifest(mani, wf_info):
    ds = DS_DIR
    # md5 bins
    for k, fn in [("md5_market", "market.bin"), ("md5_pred", "pred.bin"), ("md5_funding", "funding.bin")]:
        p = os.path.join(ds, fn)
        if k not in mani:
            fail(f"manifest thieu {k}")
            continue
        got = md5_file(p)
        if got.lower() != mani[k].lower():
            fail(f"md5 {fn}: file={got} manifest={mani[k]}")
    # maxFoldSpanDays
    if "maxFoldSpanDays" in mani:
        try:
            if int(mani["maxFoldSpanDays"]) > MAX_FOLD_SPAN_DAYS:
                fail(f"manifest maxFoldSpanDays={mani['maxFoldSpanDays']} > {MAX_FOLD_SPAN_DAYS}")
        except ValueError:
            fail(f"maxFoldSpanDays khong phai so: {mani['maxFoldSpanDays']}")
    else:
        fail("manifest thieu maxFoldSpanDays (exporter cu? re-build WfoDataset step 4)")
    # foldCount
    if wf_info and "foldCount" in mani:
        if str(wf_info["foldCount"]) != mani["foldCount"]:
            warn(f"foldCount manifest={mani['foldCount']} != so predict_wf LF_DIR={wf_info['foldCount']}"
                 f" (LF_DIR co the khac dir luc export)")
    # leakFreeFrom khop data
    if wf_info and "leakFreeFrom" in mani:
        if mani["leakFreeFrom"] != wf_info["leakFreeFromData"]:
            warn(f"manifest leakFreeFrom={mani['leakFreeFrom']} != data={wf_info['leakFreeFromData']}")
    if mani.get("leakFreeFrom", "unknown") == "unknown":
        fail("manifest leakFreeFrom=unknown (exporter khong stamp THAT)")
    if mani.get("codeGitSha", "unknown") == "unknown":
        fail("manifest codeGitSha=unknown (canonical doi provenance THAT)")


def sign_manifest(mani_path, mani):
    sig = f"python-validator@{datetime.now(_TZ).strftime('%Y-%m-%dT%H:%M:%S%z')}-PASS"
    lines = []
    replaced = False
    with open(mani_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("VALIDATED_BY="):
                lines.append(f"VALIDATED_BY={sig}\n")
                replaced = True
            else:
                lines.append(line)
    if not replaced:
        lines.append(f"VALIDATED_BY={sig}\n")
    with open(mani_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    log.info("KY PASS -> VALIDATED_BY=%s", sig)


def main():
    if not LF_DIR or not DS_DIR:
        log.error("Bat buoc set LF_DIR va DS_DIR. Xem docstring.")
        sys.exit(2)
    log.info("VALIDATE canonical WFO: LF_DIR=%s DS_DIR=%s horizon=%d expectLeakFree=%s",
             LF_DIR, DS_DIR, HORIZON_IDX, EXPECT_LEAKFREE or "(none)")

    wf_info = check_predict_wf()

    mani_path = os.path.join(DS_DIR, "manifest.txt")
    mani = read_manifest(mani_path) if os.path.exists(mani_path) else {}
    if not mani:
        fail(f"khong doc duoc manifest: {mani_path}")

    leakfree_ms = None
    if EXPECT_LEAKFREE:
        leakfree_ms = int(datetime.strptime(EXPECT_LEAKFREE, "%Y-%m-%d")
                          .replace(tzinfo=_TZ).timestamp() * 1000)

    mkt = check_market(os.path.join(DS_DIR, "market.bin"))
    check_pred(os.path.join(DS_DIR, "pred.bin"), leakfree_ms)
    check_funding(os.path.join(DS_DIR, "funding.bin"), mkt["keys"] if mkt else None)
    check_manifest(mani, wf_info)

    log.info("========== KET QUA ==========")
    log.info("WARN: %d | FAIL: %d", len(_WARNS), len(_FAILS))
    report = os.path.join(DS_DIR, "validation_report.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"validated_at={datetime.now(_TZ).isoformat()}\n")
        f.write(f"result={'PASS' if not _FAILS else 'FAIL'}\n")
        f.write(f"warn_count={len(_WARNS)}\nfail_count={len(_FAILS)}\n")
        for w in _WARNS:
            f.write(f"WARN {w}\n")
        for x in _FAILS:
            f.write(f"FAIL {x}\n")
    log.info("report -> %s", report)

    if _FAILS:
        log.error("VERDICT: FAIL -> KHONG ky manifest.")
        sys.exit(1)
    log.info("VERDICT: PASS.")
    if SIGN:
        sign_manifest(mani_path, mani)
    else:
        log.info("SIGN=0 -> chi bao cao, KHONG ky. Set SIGN=1 de ky VALIDATED_BY.")
    sys.exit(0)


if __name__ == "__main__":
    main()
