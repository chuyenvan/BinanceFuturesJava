#!/usr/bin/env python3
"""Build log-return phut ZILUSDT 2021-07..2025-12 tu kline1m Vision -> npz (key bt_ts, bt_r de dung lai book_hedge)."""
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("zil")
TS, CL = [], []
for ym in pd.period_range("2021-07", "2025-12", freq="M").strftime("%Y-%m"):
    d = pd.read_parquet(MT.kp(ym), columns=["ts", "sym", "close"])
    d = d[d["sym"].astype(str) == "ZILUSDT"].drop_duplicates("ts", keep="last").sort_values("ts")
    TS.append(d["ts"].to_numpy(np.int64))
    CL.append(d["close"].to_numpy(np.float64))
    log.info("%s n=%d", ym, len(d))
ts = np.concatenate(TS)
cl = np.concatenate(CL)
o = np.argsort(ts, kind="mergesort")
ts, cl = ts[o], cl[o]
gap = np.diff(ts) // 60000
r = np.log(cl[1:] / cl[:-1])
r[gap != 1] = 0.0  # khong gan return qua khoang trong du lieu
log.info("tong %d phut, gap>1: %d, |r|>0.2: %d", len(ts), int((gap != 1).sum()), int((np.abs(r) > 0.2).sum()))
np.savez("/home/ubuntu/claude_master/bookhedge_alt/zil_index.npz", bt_ts=ts[1:], bt_r=r)
