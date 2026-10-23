#!/usr/bin/env python3
"""GRID_T1 data prep: monthly quote-volume stats + universe selection + per-symbol 1m cache.

Chỉ đọc parquet tĩnh trong ~/vz_e1/raw. Không gọi API.
"""
import glob
import os
import sys
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

RAW = os.path.expanduser("~/vz_e1/raw")
WORK = os.path.expanduser("~/claude_master/grid_t1_wk")
os.makedirs(WORK, exist_ok=True)


def months():
    return sorted(glob.glob(os.path.join(RAW, "kline1m-*.parquet")))


def stage_vol():
    rows = []
    for f in months():
        m = os.path.basename(f)[len("kline1m-"):-len(".parquet")]
        t = pq.read_table(f, columns=["sym", "quote_volume", "ts", "close"])
        d = t.to_pandas()
        d["day"] = (d["ts"] // 86_400_000).astype(np.int64)
        g = d.groupby("sym", observed=True).agg(qv=("quote_volume", "sum"),
                                                ndays=("day", "nunique"),
                                                n=("ts", "size"),
                                                last=("ts", "max"),
                                                px=("close", "last"))
        g["month"] = m
        rows.append(g.reset_index())
        print(m, len(g), flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(os.path.join(WORK, "monthly_vol.parquet"), index=False)
    print("wrote", len(out))


if __name__ == "__main__":
    stage_vol()
