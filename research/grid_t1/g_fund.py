#!/usr/bin/env python3
"""Consolidate downloaded funding CSVs into per-symbol npz (ts ms, rate)."""
import glob
import os
import numpy as np
import pandas as pd

WK = os.path.expanduser("~/claude_master/grid_t1_wk")
OUT = os.path.join(WK, "fund")
os.makedirs(OUT, exist_ok=True)

rows = []
miss = []
for f in sorted(glob.glob(os.path.join(WK, "funding", "*.csv"))):
    base = os.path.basename(f)[:-4]
    sym = base.rsplit("-", 2)[0]
    d = pd.read_csv(f)
    if "calc_time" not in d.columns:
        continue
    d = d[pd.to_numeric(d["calc_time"], errors="coerce").notna()]
    if d.empty:
        continue
    rows.append(pd.DataFrame({"sym": sym,
                              "ts": pd.to_numeric(d["calc_time"]).astype(np.int64),
                              "rate": pd.to_numeric(d["last_funding_rate"]).astype(float)}))
for f in sorted(glob.glob(os.path.join(WK, "funding", "*.miss"))):
    miss.append(os.path.basename(f)[:-5])

if rows:
    df = pd.concat(rows, ignore_index=True).drop_duplicates(["sym", "ts"]).sort_values(["sym", "ts"])
    df.to_parquet(os.path.join(WK, "funding_all.parquet"), index=False)
    for sym, g in df.groupby("sym"):
        np.savez(os.path.join(OUT, sym + ".npz"), ts=g["ts"].to_numpy(np.int64),
                 rate=g["rate"].to_numpy(np.float64))
    print("symbols", df.sym.nunique(), "rows", len(df), "missing files", len(miss))
else:
    print("no funding rows")
