#!/usr/bin/env python3
"""TASK-251 — kiem chung CONVERT OFFLINE .bin.gz (cu) -> .t1c.gz (moi).

Khac test_tool1_col.py: file .t1c.gz o day KHONG do job export sinh ra ma do
ConvertTool1BinToCol.java doc lai chinh file .bin.gz roi ghi sang T1C1. Muc tieu la bat loi
ENDIAN (vao BIG-endian, ra LITTLE-endian) va bat mat/nhan ban dong.

    java -cp "target/binance-java-sdk-*.jar" \
         com.binance.chuyennd.ai_ml.features.export.fundingv2.ConvertTool1BinToCol ref.bin.gz out.t1c.gz
    python ml/lib/test_convert_bin_to_col.py ref.bin.gz out.t1c.gz

4 NGUONG BAT BUOC (sai thi in so do that roi exit 1, KHONG noi nguong):
  (a) moi cot: max|sai so| / IQR(cot) <= 5e-3   (+ kiem can ly thuyet range/128000)
  (b) vi tri NaN trung khit 100%
  (c) so record khop chinh xac
  (d) tap (ts, sym) khop chinh xac — so SAU KHI sort theo (sym, ts) vi sink co sort lai

Che do --prefix: dung cho file nguon BI CUT. Khi do converted chi chua k record DAU TIEN
(theo thu tu file goc) nen ref duoc cat con k dong dau roi moi so.
"""

import logging
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tool1_col import read_tool1  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("t1c-convert")

MAX_ERR_IQR = 5e-3
LEGACY_ITEMSIZE = 170


def order_by_key(a):
    """Sort (sym, ts) de can hang: T1C1 sort lai trong chunk nen thu tu file khac ref."""
    return np.lexsort((a["ts"], a["sym"]))


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    prefix_mode = "--prefix" in sys.argv[1:]
    if len(argv) != 2:
        log.error("Cu phap: test_convert_bin_to_col.py <ref .bin.gz> <converted .t1c.gz> [--prefix]")
        return 2
    ref_path, new_path = argv
    for p in (ref_path, new_path):
        if not os.path.exists(p):
            log.error("Thieu file %s", p)
            return 2

    ref = read_tool1(ref_path)
    new = read_tool1(new_path)

    # ---- (c) so record ----
    if prefix_mode:
        if len(new) > len(ref):
            log.error("(c) FAIL: converted %d record > ref %d — khong the la tien to", len(new), len(ref))
            return 1
        dropped = len(ref) - len(new)
        log.info("(c) --prefix: ref=%d record, converted=%d record (nguon cut nen MAT %d record cuoi = %d byte)",
                 len(ref), len(new), dropped, dropped * LEGACY_ITEMSIZE)
        ref = ref[:len(new)]
        ok_count = True
    else:
        ok_count = (len(ref) == len(new))
        log.info("(c) so record: ref=%d | converted=%d -> %s", len(ref), len(new),
                 "PASS" if ok_count else "FAIL")
        if not ok_count:
            return 1

    ref = ref[order_by_key(ref)]
    new = new[order_by_key(new)]

    # ---- (d) tap khoa (ts, sym) ----
    ts_bad = int((ref["ts"] != new["ts"]).sum())
    sym_bad = int((ref["sym"] != new["sym"]).sum())
    ok_key = (ts_bad == 0 and sym_bad == 0)
    if ok_key:
        log.info("(d) tap (ts,sym) khop 100%% sau sort: %d record | %d symbol | ts[%d..%d] -> PASS",
                 len(ref), len(np.unique(ref["sym"])), int(ref["ts"].min()), int(ref["ts"].max()))
    else:
        log.error("(d) FAIL: lech ts=%d o, lech sym=%d o (mat/nhan ban dong, hoac sai ENDIAN o ts/sym)",
                  ts_bad, sym_bad)
        bad = np.nonzero(ref["ts"] != new["ts"])[0][:3]
        for i in bad:
            log.error("    vi tri %d: ref(ts=%d,sym=%d) vs new(ts=%d,sym=%d)", i,
                      int(ref["ts"][i]), int(ref["sym"][i]), int(new["ts"][i]), int(new["sym"][i]))

    R = np.asarray(ref["f"], dtype=np.float64)
    N = np.asarray(new["f"], dtype=np.float64)
    n_cols = R.shape[1]

    # ---- (b) NaN mask ----
    m_ref = np.isnan(R)
    m_new = np.isnan(N)
    extra = int(np.count_nonzero(m_new & ~m_ref))
    missing = int(np.count_nonzero(m_ref & ~m_new))
    ok_nan = (extra == 0 and missing == 0)
    log.info("(b) NaN: ref=%d o | converted=%d o | thua=%d | thieu=%d -> %s",
             int(m_ref.sum()), int(m_new.sum()), extra, missing, "PASS" if ok_nan else "FAIL")

    # ---- (a) sai so / IQR tung cot ----
    worst_ratio, worst_col = 0.0, -1
    over_bound = []
    rows = []
    for j in range(n_cols):
        valid = ~m_ref[:, j]
        rv = R[valid, j]
        nv = N[valid, j]
        if rv.size == 0:
            rows.append((j, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
            continue
        q75, q25 = np.percentile(rv, [75, 25])
        iqr = q75 - q25
        err = float(np.max(np.abs(nv - rv)))
        ratio = err / iqr if iqr > 0 else (np.inf if err > 0 else 0.0)
        rng = float(rv.max() - rv.min())
        # can ly thuyet cua luong tu hoa T1C1: 0.5/scale = range/128000 (+ lam tron float32)
        bound = rng / 128000.0 + 6e-8 * float(np.max(np.abs(rv)))
        if err > bound * 1.001:
            over_bound.append((j, err, bound))
        rows.append((j, err, iqr, ratio, rng, rng / iqr if iqr > 0 else np.inf, bound))
        if ratio > worst_ratio:
            worst_ratio, worst_col = ratio, j
    ok_err = worst_ratio <= MAX_ERR_IQR
    ok_bound = not over_bound

    log.info("(a) 5 cot sai so lon nhat:")
    for j, err, iqr, ratio, rng, rr, bound in sorted(rows, key=lambda r: -r[3])[:5]:
        log.info("    f%-2d  err=%.6g  IQR=%.6g  err/IQR=%.3e  range/IQR=%.1f  can-ly-thuyet=%.6g",
                 j, err, iqr, ratio, rr, bound)
    log.info("(a) TE NHAT: f%d err/IQR=%.3e (nguong %.0e) -> %s", worst_col, worst_ratio,
             MAX_ERR_IQR, "PASS" if ok_err else "FAIL")
    if ok_bound:
        log.info("(a+) MOI cot nam trong can ly thuyet range/128000 -> giai ma CHINH XAC, sai so "
                 "THUAN TUY do luong tu hoa (khong sai endian, khong mat bit).")
    else:
        for j, err, bound in over_bound[:5]:
            log.error("(a+) f%d VUOT can ly thuyet: err=%.6g > %.6g -> CO BUG convert", j, err, bound)

    ok = ok_count and ok_key and ok_nan and ok_err and ok_bound
    log.info("KET QUA CONVERT: (a) sai so=%s | (a+) can ly thuyet=%s | (b) NaN=%s | (c) so record=%s "
             "| (d) khoa (ts,sym)=%s",
             "PASS" if ok_err else "FAIL", "PASS" if ok_bound else "FAIL",
             "PASS" if ok_nan else "FAIL", "PASS" if ok_count else "FAIL",
             "PASS" if ok_key else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
