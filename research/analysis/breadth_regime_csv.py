"""BREADTH_REGIME_CSV (TASK B2 Buoc 6, docs/prereg/PREREG_BREADTH_GATE_SIM.md) - sinh file regime CSV
causal cho GATE_REGIME_ADAPTIVE tu dinh nghia A (breadth top50/MA200/50%) da khoa o Buoc 5.2/5.3
(docs/diag/DIAG_BREADTH_REGIME.md, VERDICT GO). KHONG sua research/analysis/breadth_regime.py - chi
import cac ham dung lai nguyen van (build_daily_close_by_sym, up_matrix, breadth_from_up_matrix,
day_id, cac hang so TOPN_MAIN/MA_MAIN/THRESHOLD_MAIN/MIN_PERIODS_FLOOR). Dinh dang cot GIONG
regime_build_ma200.py (Buoc 2): cot 0=utcDay, cot 3=regime - RegimeSchedule.java CHI doc 2 cot do,
con lai la audit-only.

Cong thuc (causal, dung du lieu <= D-1, giong het breadth_regime.py dinh nghia A):
  up_i(D)      = close_i[D-1] >= MA200_i_trailing(D)   (MA200 tren CHINH coin i, min_periods=30)
  breadth(D)   = 100 * mean_i(up_i(D)) tren cac coin i=1..50 "song" (co du lieu) tai D
  not_up(D)    = breadth(D) < 50.0
  regime(D)    = "NOTUP" neu not_up(D) else "UP"
  scale(D)     = 1.70 neu NOTUP else 1.00 (= EntryGate.REGIME_SCALE_NOTUP/REGIME_SCALE_UP mac dinh)

Xuat tu 2021-06-01 (lead 30 ngay truoc SIM start 2021-07-01, cung quy uoc voi regime_build_ma200.py)
den 2025-12-31. Neu breadth(D) = NaN (khong coin nao hop le tai D - khong ky vong xay ra trong
cua so nay voi top-50), quy dinh NOTUP (bao thu, ghi ro so ngay bi anh huong).

Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/breadth_regime_csv.py
Ghi: /home/ubuntu/regime_work/regime_daily_breadth.csv
"""
import csv
import datetime
import logging
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_rank_ic as T  # noqa: E402  (load_closes)
import breadth_regime as BR  # noqa: E402  (build_daily_close_by_sym, up_matrix,
                              #  breadth_from_up_matrix, day_id, TOPN_MAIN, MA_MAIN,
                              #  THRESHOLD_MAIN, MIN_PERIODS_FLOOR) - KHONG sua file nay.

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("breadth_regime_csv")

OUT_CSV = "/home/ubuntu/regime_work/regime_daily_breadth.csv"
D0_STR = "2021-06-01"  # lead-in, cung quy uoc regime_build_ma200.py (SIM start 2021-07-01)
D1_STR = "2025-12-31"
SIM0_STR = "2021-07-01"


def main():
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    log.info("=== BREADTH_REGIME_CSV: nap CLOSES_1H.bin (top-%d symId, MA=%d, threshold=%.1f%%) ===",
              BR.TOPN_MAIN, BR.MA_MAIN, BR.THRESHOLD_MAIN)
    df = T.load_closes()
    symids_main = list(range(1, BR.TOPN_MAIN + 1))
    daily_by_sym = BR.build_daily_close_by_sym(df, symids_main)
    log.info("symId 1..%d: %d co du lieu trong CLOSES_1H.bin", BR.TOPN_MAIN, len(daily_by_sym))

    day0, day1 = BR.day_id(D0_STR), BR.day_id(D1_STR)
    day_range = np.arange(day0, day1 + 1)
    sim0_day = BR.day_id(SIM0_STR)
    log.info("Xuat CSV %s..%s = %d ngay (SIM bat dau %s)", D0_STR, D1_STR, len(day_range), SIM0_STR)

    up_mat, alive_mat = BR.up_matrix(daily_by_sym, symids_main, day_range, BR.MA_MAIN,
                                       min_floor=BR.MIN_PERIODS_FLOOR)
    breadth, n_valid = BR.breadth_from_up_matrix(up_mat)

    n_nan = int(np.sum(np.isnan(breadth)))
    if n_nan:
        log.warning("CANH BAO: %d/%d ngay breadth=NaN (khong coin nao hop le) -> quy dinh NOTUP "
                     "(bao thu)", n_nan, len(day_range))

    not_up = np.where(np.isnan(breadth), True, breadth < BR.THRESHOLD_MAIN)

    rows = []
    nup = nnu = 0
    n_partial = 0
    for i, D in enumerate(day_range):
        b = breadth[i]
        nv = int(n_valid[i])
        if nv < BR.TOPN_MAIN:
            n_partial += 1
        reg = "NOTUP" if not_up[i] else "UP"
        scale = "1.70" if reg == "NOTUP" else "1.00"
        dt = datetime.datetime.utcfromtimestamp(int(D) * 86400).strftime("%Y-%m-%d")
        b_str = "%.4f" % b if np.isfinite(b) else "NaN"
        rows.append((int(D), dt, b_str, reg, scale, nv, BR.TOPN_MAIN, BR.MA_MAIN, BR.THRESHOLD_MAIN))
        if D >= sim0_day:
            if reg == "UP":
                nup += 1
            else:
                nnu += 1

    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utcDay", "dateUTC", "breadth_pct", "regime", "scale", "n_valid_coins",
                    "topn_main", "ma_window", "threshold_pct"])
        w.writerows(rows)

    tot = nup + nnu
    log.info("wrote %d rows -> %s (ngay co it hon %d coin hop le trong toan bo output: %d)",
              len(rows), OUT_CSV, BR.TOPN_MAIN, n_partial)
    log.info("SIM-range(%s..%s) days=%d UP=%d(%.1f%%) NOTUP=%d(%.1f%%)",
              SIM0_STR, D1_STR, tot, nup, 100.0 * nup / tot, nnu, 100.0 * nnu / tot)

    from collections import Counter
    yc, yu = Counter(), Counter()
    for (D, dt, b, reg, sc, nv, topn, maw, thr) in rows:
        if D < sim0_day:
            continue
        y = dt[:4]
        yc[y] += 1
        if reg == "UP":
            yu[y] += 1
    log.info("Theo nam (breadth top%d/MA%d/%.0f%%) UP%%:", BR.TOPN_MAIN, BR.MA_MAIN, BR.THRESHOLD_MAIN)
    for y in sorted(yc):
        log.info("  %s: UP %d/%d = %.1f%% NOTUP %.1f%%", y, yu[y], yc[y],
                  100.0 * yu[y] / yc[y], 100.0 * (yc[y] - yu[y]) / yc[y])


if __name__ == "__main__":
    main()
