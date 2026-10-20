#!/usr/bin/env python3
"""TSX: ngay 'ca thi truong alt dang sap' (nhan qua): ngay d+1 co co neu ALT_EW cuoi ngay d <= -30% so dinh 30 ngay (d-30..d)."""
import hashlib
import json

import numpy as np
import pandas as pd

z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
ts = pd.to_datetime(z["ew_ts"].astype(np.int64), unit="ms")
L = pd.Series(np.cumsum(z["ew_r"].astype(np.float64)), index=ts)
eod = L.groupby(L.index.floor("D")).last()
mx = eod.rolling(31, min_periods=1).max()
dd = np.exp(eod - mx) - 1
flag_days = sorted((dd[dd <= -0.30].index + pd.Timedelta(days=1)))
flag_days = [d for d in flag_days if pd.Timestamp("2021-07-01") <= d <= pd.Timestamp("2025-12-31")]
rng, start, prev = [], None, None
for d in flag_days:
    if start is None:
        start = prev = d
    elif d == prev + pd.Timedelta(days=1):
        prev = d
    else:
        rng.append((start, prev))
        start = prev = d
if start is not None:
    rng.append((start, prev))
s = ",".join("%s-%s" % (a.strftime("%Y%m%d"), b.strftime("%Y%m%d")) for a, b in rng)
by_year = pd.Series(1, index=pd.DatetimeIndex(flag_days)).groupby(lambda x: x.year).sum().to_dict()
out = dict(rule="flag(d+1) iff exp(L_eod(d) - max L_eod(d-30..d)) - 1 <= -0.30, L = cumsum log-ret ALT_EW (index.npz)",
           n_days=len(flag_days), n_ranges=len(rng), by_year={int(k): int(v) for k, v in by_year.items()},
           ranges=s, sha256=hashlib.sha256(s.encode()).hexdigest())
json.dump(out, open("/home/ubuntu/claude_master/tsx/flags.json", "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "ranges"}))
print(s[:600], "... len", len(s))
