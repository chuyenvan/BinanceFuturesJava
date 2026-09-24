#!/usr/bin/env python3
"""SL3 intraday MTM — maxDD/UW tren chuoi equity MOC PHUT cho 5 chan cua
docs/prereg/PREREG_SL_7_TO_3.md.

Tai dung NGUYEN logic da nghiem thu cua research/analysis/intraday_dd.py
(docs/result/RESULT_INTRADAY_DD.md): equity_mtm(m) = 35,000 + realized(m) + unP(m), mark = priceClose 1m,
cong nghiem thu V1/V2/V3/V5 chay truoc khi bao cao. Chi doi RUNS + cache dir.

Usage: python3 research/analysis/sl3_intraday.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import intraday_dd as I  # noqa: E402

OUT = "/home/ubuntu/sl3/intraday"
KOUT = "/home/ubuntu/kaggle_sim/out"

intraday_dd_runs = {
    "base": os.path.join(KOUT, "sl3-base"),
    "v1": os.path.join(KOUT, "sl3-v1-arm03"),
    "v2": os.path.join(KOUT, "sl3-v2-sl3"),
    "v3": os.path.join(KOUT, "sl3-v3-both"),
    "v4": os.path.join(KOUT, "sl3-v4-sl7"),
}

if __name__ == "__main__":
    for k, v in intraday_dd_runs.items():
        if not os.path.exists(os.path.join(v, "storage", "printDone.csv")):
            print("MISSING run dir %s (%s)" % (k, v))
            sys.exit(1)
    I.RUNS.clear()
    I.RUNS.update(intraday_dd_runs)
    os.makedirs(OUT, exist_ok=True)
    sys.argv = ["sl3_intraday", "--workers", "4", "--out", OUT,
                "--report", os.path.join(OUT, "report_sl3_intraday.txt")]
    I.main()
