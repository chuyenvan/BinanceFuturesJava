#!/usr/bin/env python3
"""HO1 B4a — CLOSES_1H doan 2026 (Vision futures 1h, thang 2026-01..2026-06) bang CHINH generator closes1h_build.py
(ts = open_time + 1h; sort (ts, ten)). Universe = symbol cua CLOSES_1H.bin ghim (DEV, 627) + symbol trong symbol_map co
ban ghi trong file nhan 2026 (chi doc cot symbol = availability; coin niem yet 2026 — tuong tu DEV: universe = moi coin co
du lieu). Doan DEV KHONG tai lai (giu file ghim). Chi kiem toan ven. Usage: python3 ho1_closes2026.py <out.bin>"""
import glob
import hashlib
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/pipeline")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import closes1h_build as C  # noqa: E402
from funding_label_pb import read_label  # noqa: E402

OUT = sys.argv[1]
C.MONTHS = ["2026-%02d" % m for m in range(1, 7)]
C.OUT = OUT
_base = C.universe()
mp = pd.read_csv(C.MAP_CSV)
s2i = dict(zip(mp.symbol, mp.symId))
lab = set()
for f in sorted(glob.glob("/home/ubuntu/ds_label15m/funding_label_2026*.pb")):
    lab |= set(read_label(f, usecols=["symbol"]).symbol.unique())
have = set(s for s, _ in _base)
EXTRA = sorted((int(s2i[n]), n) for n in lab if n in s2i and int(s2i[n]) not in have)
C.universe = lambda: _base + EXTRA
C.main()
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
a = np.fromfile(OUT, dtype=DT)
ts = a["ts"].astype(np.int64)
k = ts * 10000 + a["sym"].astype(np.int64)
ext_ids = set(s for s, _ in EXTRA)
meta = dict(n=int(len(a)), ts_min=int(ts.min()), ts_max=int(ts.max()), n_sym=int(len(np.unique(a["sym"]))),
            n_universe_dev=len(_base), extra=[n for _, n in EXTRA],
            extra_with_data=int(len(ext_ids & set(np.unique(a["sym"]).astype(int)))),
            dup_keys=int(len(k) - len(np.unique(k))), nan_close=int(np.isnan(a["c"].astype(np.float32)).sum()),
            md5=hashlib.md5(open(OUT, "rb").read()).hexdigest(), months=C.MONTHS, src_universe=C.SRC_BIN)
json.dump(meta, open(OUT + ".json", "w"), indent=1)
logging.getLogger().info("CLOSES 2026: %s", meta)
