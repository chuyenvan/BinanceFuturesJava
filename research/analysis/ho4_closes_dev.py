#!/usr/bin/env python3
"""HO4-P3 (ADDENDUM-5 §5.3, dau vao cong V): CLOSES_1H lat DEV dung lai tu Vision 1h bang CHINH generator F0
closes1h_build.py (thang 2025-04..2025-12, universe = 627 symbol cua CLOSES_1H.bin ghim), roi so voi file ghim tren
[2025-05-01, 2026-01-01) UTC: khoa (ts, sym) + close float32 bang. Chi dem/ty le. Usage: ho4_closes_dev.py <out.bin>"""
import json, logging, sys
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/pipeline")
import closes1h_build as C  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho4clo")
OUT = sys.argv[1]
C.MONTHS = ["2025-%02d" % m for m in range(4, 13)]
C.OUT = OUT
C.main()
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
LO, HI = 1746057600000, 1767225600000   # 2025-05-01 .. 2026-01-01 UTC
a = np.fromfile(C.SRC_BIN, dtype=DT); b = np.fromfile(OUT, dtype=DT)
a = a[(a["ts"].astype(np.int64) >= LO) & (a["ts"].astype(np.int64) < HI)]
b = b[(b["ts"].astype(np.int64) >= LO) & (b["ts"].astype(np.int64) < HI)]
ka = a["ts"].astype(np.int64) * 10000 + a["sym"].astype(np.int64)
kb = b["ts"].astype(np.int64) * 10000 + b["sym"].astype(np.int64)
com, ia, ib = np.intersect1d(ka, kb, return_indices=True)
ca, cb = a["c"][ia].astype(np.float32), b["c"][ib].astype(np.float32)
eq = (ca == cb) | (np.isnan(ca) & np.isnan(cb))
mon = {}
for t, e in zip(a["ts"][ia].astype(np.int64)[~eq], [0] * int((~eq).sum())):
    k = str(np.datetime64(int(t), "ms"))[:7]
    mon[k] = mon.get(k, 0) + 1
r = dict(pin=int(len(a)), new=int(len(b)), common=int(len(com)), pin_only=int(len(a) - len(com)), new_only=int(len(b) - len(com)),
         eq=int(eq.sum()), eq_frac_common=float(eq.mean()) if len(com) else None, neq_by_month=mon,
         pin_only_syms=int(len(np.unique(a["sym"][np.setdiff1d(np.arange(len(a)), ia)]))))
json.dump(r, open(OUT + ".cmp.json", "w"), indent=1)
log.info("CLOSES cmp %s", r)
