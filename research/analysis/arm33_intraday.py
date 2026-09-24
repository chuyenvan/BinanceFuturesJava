#!/usr/bin/env python3
"""ARM3-3NEN intraday MTM — maxDD/UW tren chuoi equity MOC PHUT cho 6 chan cua
docs/prereg/PREREG_ARM3_3NEN.md.

Tai dung NGUYEN logic da nghiem thu cua research/analysis/intraday_dd.py
(docs/result/RESULT_INTRADAY_DD.md, RISK_APPETITE §7.3). Chi doi RUNS + cache dir.

Usage: python3 research/analysis/arm33_intraday.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import intraday_dd as I  # noqa: E402

OUT = "/home/ubuntu/arm33/intraday"
KOUT = "/home/ubuntu/kaggle_sim/out"

RUNS = {
    "kg0-g170":      os.path.join(KOUT, "kg0-g170"),       # A1 KEEPLEG0 moc
    "sl3-v1-arm03":  os.path.join(KOUT, "sl3-v1-arm03"),   # A2 KEEPLEG0 arm3
    "hn-t100":       os.path.join(KOUT, "hn-t100"),        # B1 T100 moc
    "hn-t100-arm3":  os.path.join(KOUT, "hn-t100-arm3"),   # B2 T100 arm3
    "hn-g92":        os.path.join(KOUT, "hn-g92"),         # C1 GD92 moc
    "hn-g92-arm3":   os.path.join(KOUT, "hn-g92-arm3"),    # C2 GD92 arm3
}

if __name__ == "__main__":
    for k, v in RUNS.items():
        if not os.path.exists(os.path.join(v, "storage", "printDone.csv")):
            print("MISSING run dir %s (%s)" % (k, v))
            sys.exit(1)
    I.RUNS.clear()
    I.RUNS.update(RUNS)
    os.makedirs(OUT, exist_ok=True)
    sys.argv = ["arm33_intraday", "--workers", "4", "--out", OUT,
                "--report", os.path.join(OUT, "report_arm33_intraday.txt")]
    I.main()
