#!/usr/bin/env python3
"""SCREEN tuong quan 2024: coin nao bam nhan to ALT (book 97% alt) tot hon BTC/ETH.

Chi doc 2024 (nam kham pha). Nguon: /home/ubuntu/vz_e1/raw/kline1m-2024-MM.parquet.
Ra: bang xep hang corr(daily) voi EW (equal-weight alt) va BTC, kem thanh khoan.
Khong do outcome hedge o buoc nay (chi chon ung vien).
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

RAW = "/home/ubuntu/vz_e1/raw"
OUT = "/home/ubuntu/claude_master/bookhedge_alt/screen_2024.json"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

files = sorted(glob.glob(os.path.join(RAW, "kline1m-2024-*.parquet")))
print("months:", [os.path.basename(f)[-14:-8] for f in files], flush=True)

parts = []
for f in files:
    t = pq.read_table(f, columns=["ts", "sym", "close", "quote_volume"])
    d = t.to_pandas()
    d["day"] = (d["ts"].astype(np.int64) // 86400000).astype(np.int32)
    g = (d.groupby(["sym", "day"], sort=False)
           .agg(close=("close", "last"), qv=("quote_volume", "sum"), n=("ts", "size"))
           .reset_index())
    parts.append(g)
    print("  %s rows=%d syms=%d" % (os.path.basename(f)[-14:-8], len(d), d["sym"].nunique()), flush=True)
    del d, t, g

df = pd.concat(parts, ignore_index=True)
del parts
print("tong rows ngay-symbol:", len(df), flush=True)

close = df.pivot_table(index="day", columns="sym", values="close", aggfunc="last")
qv = df.pivot_table(index="day", columns="sym", values="qv", aggfunc="sum")
nmin = df.pivot_table(index="day", columns="sym", values="n", aggfunc="sum")
del df

r = np.log(close).diff()
days = close.index.to_numpy()

# EW (equal-weight alt) + BTC tu index.npz -> daily log return
z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
def daily(ts, rr):
    d = (ts.astype(np.int64) // 86400000).astype(np.int32)
    s = pd.Series(rr, index=d).groupby(level=0).sum()
    return s
ew_d = daily(z["ew_ts"], z["ew_r"])
bt_d = daily(z["bt_ts"], z["bt_r"])
ew = ew_d.reindex(days)
bt = bt_d.reindex(days)

rows = []
for sym in r.columns:
    x = r[sym]
    ok = x.notna() & nmin[sym].ge(1000)  # >=1000 phut/ngay
    n = int(ok.sum())
    if n < 250:
        continue
    xv = x[ok]
    qvs = qv[sym][ok]
    med_qv = float(qvs.median())
    if med_qv < 1e6:
        continue
    cb = float(np.corrcoef(xv, bt[ok])[0, 1])
    ce = float(np.corrcoef(xv, ew[ok])[0, 1])
    rows.append(dict(sym=sym, corr_ew=ce, corr_btc=cb, n_days=n,
                     med_qv_usd=med_qv, vol_daily=float(xv.std() * 100),
                     beta_ew=float(np.polyfit(ew[ok], xv, 1)[0])))
res = pd.DataFrame(rows).sort_values("corr_ew", ascending=False)
print("\n=== TOP 25 theo corr voi EW (nhan to alt) ===", flush=True)
print(res.head(25).to_string(index=False, float_format=lambda v: "%.3f" % v), flush=True)
print("\n=== BTC / ETH / BTCDOM de so ===", flush=True)
print(res[res["sym"].isin(["BTCUSDT", "ETHUSDT", "BTCDOMUSDT", "BTCSTUSDT"])].to_string(index=False, float_format=lambda v: "%.3f" % v), flush=True)

json.dump(res.to_dict("records"), open(OUT, "w"), indent=1)
print("\nsaved", OUT, "n_sym", len(res), flush=True)
