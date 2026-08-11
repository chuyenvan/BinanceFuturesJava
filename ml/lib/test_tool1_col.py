#!/usr/bin/env python3
"""TASK-251 — kiểm chứng round-trip Java(Tool1ColSink) -> Python(tool1_col.read_tool1).

Chay TREN MAY WINDOWS, khong can Oracle/Kaggle:
    mvn -DskipTests package && mvn -DskipTests test-compile
    java -cp "target/binance-java-sdk-*.jar;target/test-classes" \
         com.binance.chuyennd.ai_ml.features.export.fundingv2.Tool1ColRoundTripMain <outDir>
    python ml/lib/test_tool1_col.py <outDir>

Doc <outDir>/rt_features_ref.bin.gz (dinh dang CU = gia tri GOC chinh xac bit) va
<outDir>/rt_features.t1c.gz (dinh dang MOI), can theo khoa (sym, ts) roi so TUNG O.

3 NGUONG BAT BUOC (khong noi nguong cho qua — sai thi in so do that roi exit 1):
  (a) moi cot: max|sai so| / IQR(cot) <= 5e-3
  (b) vi tri NaN trung khit 100% (khong thua khong thieu 1 o)
  (c) ti le nen: (170 * so record) / size(.t1c.gz) >= 3.5
"""

import logging
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tool1_col import read_tool1  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("t1c-roundtrip")

MAX_ERR_IQR = 5e-3
MIN_RATIO = 3.5
LEGACY_ITEMSIZE = 170


def order_by_key(a):
    """Sap xep theo (sym, ts) de can hang giua 2 dinh dang (T1C1 sort trong chunk nen thu tu khac)."""
    return np.lexsort((a["ts"], a["sym"]))


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "target/t1c_roundtrip"
    new_path = os.path.join(out_dir, "rt_features.t1c.gz")
    ref_path = os.path.join(out_dir, "rt_features_ref.bin.gz")
    for p in (new_path, ref_path):
        if not os.path.exists(p):
            log.error("Thieu file %s — chay Tool1ColRoundTripMain truoc.", p)
            return 2

    ref = read_tool1(ref_path)
    new = read_tool1(new_path)
    log.info("ref=%d record | new=%d record", len(ref), len(new))
    if len(ref) != len(new):
        log.error("SO RECORD LECH: ref=%d new=%d", len(ref), len(new))
        return 1

    ref = ref[order_by_key(ref)]
    new = new[order_by_key(new)]
    if not np.array_equal(ref["ts"], new["ts"]) or not np.array_equal(ref["sym"], new["sym"]):
        n_ts = int((ref["ts"] != new["ts"]).sum())
        n_sym = int((ref["sym"] != new["sym"]).sum())
        log.error("KHOA (ts,sym) KHONG KHOP: lech ts=%d o, lech sym=%d o", n_ts, n_sym)
        return 1
    log.info("Khoa (ts,sym) khop 100%% (%d record, %d symbol, ts[%d..%d])",
             len(ref), len(np.unique(ref["sym"])), int(ref["ts"].min()), int(ref["ts"].max()))

    R = np.asarray(ref["f"], dtype=np.float64)
    N = np.asarray(new["f"], dtype=np.float64)
    n_cols = R.shape[1]

    # ---- (b) NaN mask ----
    m_ref = np.isnan(R)
    m_new = np.isnan(N)
    extra = int(np.count_nonzero(m_new & ~m_ref))
    missing = int(np.count_nonzero(m_ref & ~m_new))
    log.info("(b) NaN: ref=%d o | new=%d o | thua=%d | thieu=%d",
             int(m_ref.sum()), int(m_new.sum()), extra, missing)
    ok_nan = (extra == 0 and missing == 0)

    # ---- (a) sai so tuong doi IQR tung cot ----
    # Sai so lang tu hoa T1C1 la HANG SO theo cot: 0.5/scale = range/128000 (scale = 64000/range).
    # Nen ngoai nguong (a), kiem luon: err THUC TE <= can ly thuyet -> chung minh giai ma CHINH XAC
    # (khong mat bit vi delta tran int16 / byte-split / cumsum sai). Neu vuot can nay = CO BUG THAT.
    worst_ratio, worst_col = 0.0, -1
    over_bound = []
    rows = []
    for j in range(n_cols):
        valid = ~m_ref[:, j]
        rv = R[valid, j]
        nv = N[valid, j]
        q75, q25 = np.percentile(rv, [75, 25])
        iqr = q75 - q25
        err = float(np.max(np.abs(nv - rv))) if rv.size else 0.0
        ratio = err / iqr if iqr > 0 else (np.inf if err > 0 else 0.0)
        rng = float(rv.max() - rv.min()) if rv.size else 0.0
        # can ly thuyet + bien do lam tron float32 cua chinh gia tri (2^-24 tuong doi)
        bound = rng / 128000.0 + 6e-8 * float(np.max(np.abs(rv))) if rv.size else 0.0
        if err > bound * 1.001:
            over_bound.append((j, err, bound))
        rows.append((j, err, iqr, ratio, rng, rng / iqr if iqr > 0 else np.inf, bound))
        if ratio > worst_ratio:
            worst_ratio, worst_col = ratio, j
    ok_err = worst_ratio <= MAX_ERR_IQR
    ok_bound = not over_bound

    log.info("(a) 5 cot sai so lon nhat (err/IQR):")
    for j, err, iqr, ratio, rng, rr, bound in sorted(rows, key=lambda r: -r[3])[:5]:
        log.info("    f%-2d  err=%.6g  IQR=%.6g  err/IQR=%.3e  range/IQR=%.1f  can-ly-thuyet=%.6g",
                 j, err, iqr, ratio, rr, bound)
    log.info("(a) TE NHAT: f%d err/IQR=%.3e (nguong %.0e; tuong duong range/IQR <= %.0f)",
             worst_col, worst_ratio, MAX_ERR_IQR, MAX_ERR_IQR * 128000)
    if ok_bound:
        log.info("(a+) MOI cot deu nam trong can ly thuyet range/128000 -> giai ma CHINH XAC, "
                 "sai so con lai THUAN TUY do luong tu hoa (khong mat bit).")
    else:
        for j, err, bound in over_bound[:5]:
            log.error("(a+) f%d VUOT can ly thuyet: err=%.6g > %.6g -> CO BUG ma hoa/giai ma", j, err, bound)

    # ---- (c) ti le nen ----
    new_size = os.path.getsize(new_path)
    ref_size = os.path.getsize(ref_path)
    raw = len(ref) * LEGACY_ITEMSIZE
    ratio_raw = raw / new_size
    ratio_gz = ref_size / new_size
    log.info("(c) raw=%d B (%d B/rec) | cu-gzip=%d B (%.2f B/rec) | moi=%d B (%.2f B/rec)",
             raw, LEGACY_ITEMSIZE, ref_size, ref_size / len(ref), new_size, new_size / len(ref))
    log.info("(c) raw/moi = %.2fx (nguong >= %.1fx) | cu-gzip/moi = %.2fx", ratio_raw, MIN_RATIO, ratio_gz)
    ok_ratio = ratio_raw >= MIN_RATIO

    log.info("KET QUA: (a) sai so=%s | (a+) can ly thuyet=%s | (b) NaN=%s | (c) nen=%s",
             "PASS" if ok_err else "FAIL",
             "PASS" if ok_bound else "FAIL",
             "PASS" if ok_nan else "FAIL",
             "PASS" if ok_ratio else "FAIL")
    return 0 if (ok_err and ok_bound and ok_nan and ok_ratio) else 1


if __name__ == "__main__":
    sys.exit(main())
