#!/usr/bin/env python3
"""GB intraday MTM — maxDD/UW tren chuoi equity MOC PHUT cho 4 chan cua
docs/PREREG_GIVEBACK_RATIO.md (moc 0.5 + ratio 1/2/5).

Tai dung NGUYEN logic da nghiem thu cua research/analysis/intraday_dd.py
(docs/RESULT_INTRADAY_DD.md, RISK_APPETITE §7.3). Chi doi RUNS + cache dir.
Cache `series.npz`: LAN CHAY DAU tao moi (4 chan = 4 chuoi), cac lan sau doc lai.

Usage: python3 research/analysis/gb_intraday.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import intraday_dd as I  # noqa: E402

OUT = "/home/ubuntu/gbr/intraday"
KOUT = "/home/ubuntu/kaggle_sim/out"

RUNS = {
    "base": os.path.join(KOUT, "kg0-g170"),   # moc 0.5
    "r1":   os.path.join(KOUT, "gb-r1"),      # TS_GIVEBACK_RATIO=1
    "r2":   os.path.join(KOUT, "gb-r2"),      # TS_GIVEBACK_RATIO=2
    "r5":   os.path.join(KOUT, "gb-r5"),      # TS_GIVEBACK_RATIO=5
}

if __name__ == "__main__":
    for k, v in RUNS.items():
        if not os.path.exists(os.path.join(v, "storage", "printDone.csv")):
            print("MISSING run dir %s (%s)" % (k, v))
            sys.exit(1)
    I.RUNS.clear()
    I.RUNS.update(RUNS)
    os.makedirs(OUT, exist_ok=True)
    sys.argv = ["gb_intraday", "--workers", "4", "--out", OUT,
                "--report", os.path.join(OUT, "report_gb_intraday.txt")]
    I.main()
