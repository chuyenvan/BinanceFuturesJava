#!/usr/bin/env python3
"""BOOK_HEDGE_DYN - buoc 1: dung du lieu da coin.

(a) Bang NGAY cho toan bo symbol (close cuoi ngay, qv, so phut) 2021-07..2025-12.
(b) Universe moi thang: >=60 ngay du lieu + median qv >= 10M trong 90 ngay truoc, top 30 thanh khoan
    (loai BTC/ETH/BTCDOM/stablecoin) -> luu danh sach thang.
(c) Minute returns cho HOP cua cac universe do, tren luoi phut cua edge_attr (bt_ts).
Khong dung thong tin tuong lai: universe thang m chi dung 90 ngay TRUOC m.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402

OUT = "/home/ubuntu/claude_master/bookhedge_dyn"
os.makedirs(OUT, exist_ok=True)
MONTHS = list(pd.period_range("2021-07", "2025-12", freq="M").strftime("%Y-%m"))
EXCL = {"BTCUSDT", "ETHUSDT", "BTCDOMUSDT"}
STABLE = ("USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "DAIUSDT", "USDPUSDT")

# ---------- Phase A: daily table ----------
dp = os.path.join(OUT, "daily.parquet")
if os.path.exists(dp):
    day = pd.read_parquet(dp)
    print("daily cache:", day.shape, flush=True)
else:
    parts = []
    for ym in MONTHS:
        d = pd.read_parquet(MT.kp(ym), columns=["ts", "sym", "close", "quote_volume"])
        d["day"] = (d["ts"].astype(np.int64) // 86400000).astype(np.int32)
        g = (d.groupby(["sym", "day"], sort=False)
               .agg(close=("close", "last"), qv=("quote_volume", "sum"), n=("ts", "size"))
               .reset_index())
        parts.append(g)
        print("  %s rows=%d syms=%d" % (ym, len(g), g["sym"].nunique()), flush=True)
        del d, g
    day = pd.concat(parts, ignore_index=True)
    del parts
    day.to_parquet(dp)
    print("daily saved:", day.shape, flush=True)

day = day[~day["sym"].astype(str).isin(EXCL | set(STABLE))]
day = day[day["n"] >= 1000]  # >=1000 phut/ngay

# ---------- Phase B: universe moi thang ----------
days = np.sort(day["day"].unique())
uni = {}
for ym in MONTHS:
    y, m = int(ym[:4]), int(ym[5:])
    start = int(pd.Timestamp(year=y, month=m, day=1).value // 10 ** 6 // 86400000)
    w = day[(day["day"] >= start - 90) & (day["day"] < start)]
    if len(w) == 0:
        uni[ym] = []
        continue
    g = w.groupby("sym").agg(days=("day", "nunique"), med_qv=("qv", "median"))
    g = g[(g["days"] >= 60) & (g["med_qv"] >= 10e6)].sort_values("med_qv", ascending=False)
    uni[ym] = list(g.index[:30])
    print("%s universe %d: %s" % (ym, len(uni[ym]), uni[ym][:5]), flush=True)
json.dump(uni, open(os.path.join(OUT, "universe.json"), "w"), indent=1)

pool = sorted({s for v in uni.values() for s in v})
print("pool size:", len(pool), flush=True)

# ---------- Phase C: minute returns tren luoi chung ----------
z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
grid = z["bt_ts"].astype(np.int64)
pos = {int(t): i for i, t in enumerate(grid)}
M = len(grid)
ret = {s: np.zeros(M, np.float32) for s in pool}
last = {s: np.full(M, np.nan, np.float32) for s in pool}

for ym in MONTHS:
    d = pd.read_parquet(MT.kp(ym), columns=["ts", "sym", "close"])
    d = d[d["sym"].astype(str).isin(set(pool))]
    d["ts"] = d["ts"].astype(np.int64)
    d = d.drop_duplicates(["sym", "ts"], keep="last")
    for s, grp in d.groupby("sym", sort=False):
        idx = grp["ts"].map(pos)
        ok = idx.notna().to_numpy()
        if not ok.any():
            continue
        ii = idx[ok].to_numpy(np.int64)
        cc = grp["close"].to_numpy(np.float64)[ok]
        last[s][ii] = cc
    print("  minute %s done" % ym, flush=True)
    del d

for s in pool:
    p = last[s]
    r = np.zeros(M, np.float32)
    valid = ~np.isnan(p)
    idx = np.where(valid)[0]
    if len(idx) < 2:
        ret[s] = r
        continue
    v = p[idx]
    rr = np.log(v[1:] / v[:-1]).astype(np.float32)
    gap = np.diff(idx)
    rr[gap != 1] = 0.0
    r[idx[1:]] = rr
    ret[s] = r
    del p

np.savez_compressed(os.path.join(OUT, "minute_returns.npz"), grid=grid, **{s: ret[s] for s in pool})
json.dump(pool, open(os.path.join(OUT, "pool.json"), "w"))
print("saved minute_returns.npz:", len(pool), "symbols x", M, "phut", flush=True)
