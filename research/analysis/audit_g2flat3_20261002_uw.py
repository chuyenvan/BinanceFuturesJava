#!/usr/bin/env python3
"""Vi tri UW dai nhat + maxDD ngay cho B0/G2/R4/T170 (0-sim, doc sim.out)."""
import re, logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
L = logging.getLogger()
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?unP:\s*(-?\d+)")
for name, tag in [("B0", "de-p1"), ("G2", "gdv2-g2"), ("R4", "cp-r4-parity"), ("T170", "r4-par-t170"), ("R0", "p2-r0-base")]:
    eq = {}
    for line in open("/home/ubuntu/kaggle_sim/out/%s/logs/sim.out" % tag, errors="ignore"):
        if "BudgetManagerSimple: Update" in line:
            m = RX.search(line)
            if m:
                eq[m.group(1)] = float(m.group(2)) + float(m.group(3))
    days = sorted(eq)
    pk, pkd, best, bs, be, mdd, mdd_at, mdd_pk = None, None, 0, "", "", 0, "", ""
    for d in days:
        v = eq[d]
        if pk is None or v >= pk:
            if pkd and (days.index(d) - days.index(pkd)) > best:
                best, bs, be = days.index(d) - days.index(pkd), pkd, d
            pk, pkd = v, d
        dd = v / pk - 1
        if dd < mdd:
            mdd, mdd_at, mdd_pk = dd, d, pkd
    L.info("%s UWmax=%d tu %s den %s | maxDD_day=%.2f%% day %s (peak %s)", name, best, bs, be, mdd * 100, mdd_at, mdd_pk)
