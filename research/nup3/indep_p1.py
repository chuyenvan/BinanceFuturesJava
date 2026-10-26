#!/usr/bin/env python3
"""NUP3 P1 — kiem tay DOC LAP (chi csv/datetime/json, khong import pipeline): cum/nam + ΣPnL sleeve va toan danh muc
cho 1 arm x 1 seed. Cum = (so, sym, gio dong). Gan theo gio dong +07, DEV 2022-01-01 -> 2025-12-31.
Dong sleeve co gio dong < 2022-01-01 bi bo qua ngay khi doc (khong cong PnL).
Usage: python3 indep_p1.py <tag>"""
import csv
import json
import sys
from datetime import datetime

tag = sys.argv[1]
p = "/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv" % tag
A, B = datetime(2022, 1, 1), datetime(2026, 1, 1)
cl = {"S": {}, "B": {}}
pnl = {"S": 0.0, "B": 0.0}
pnly = {"S": {}, "B": {}}
with open(p, newline="") as f:
    rd = csv.reader(f)
    h = [c.strip() for c in next(rd)]
    ie, ip, isy = h.index("end"), h.index("pnl"), h.index("sym")
    for row in rd:
        if not row:
            continue
        bk = "S" if row[-1].strip() == "book=sleeve" else "B"
        te = datetime.strptime(row[ie].strip(), "%Y%m%d %H:%M")
        if not (A <= te < B):
            continue
        y = te.year
        cl[bk].setdefault(y, set()).add((row[isy].strip(), row[ie].strip()))
        v = float(row[ip])
        pnl[bk] += v
        pnly[bk][y] = pnly[bk].get(y, 0.0) + v
out = {}
for bk in ("S", "B"):
    out[bk] = dict(n_cl={y: len(cl[bk].get(y, ())) for y in range(2022, 2026)}, pnl=pnl[bk])
out["P"] = dict(n_cl={y: out["S"]["n_cl"][y] + out["B"]["n_cl"][y] for y in range(2022, 2026)}, pnl=pnl["S"] + pnl["B"])
print(json.dumps(out))
