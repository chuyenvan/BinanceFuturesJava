"""Dump 1 lan funding rate BTCUSDT tu Aerospike (nguon THAT ma engine dung:
set funding_data, bin f_data = Snappy(JSON ts->rate)) ra CSV cho overlay hedge.

Chay: python3 dump_funding_btc.py  -> /home/ubuntu/hedge_a/funding_btcusdt.csv
KHONG sua Aerospike (chi doc). KHONG dung .pb/.bin label files.
"""
import json
import logging

import aerospike
import cramjam
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("dump_funding")

NS = "test"
SET = "funding_data"
SYM = "BTCUSDT"
OUT = "/home/ubuntu/hedge_a/funding_btcusdt.csv"

cl = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 30000}}).connect()
key, meta, rec = cl.get((NS, SET, SYM))
raw = bytes(cramjam.snappy.decompress_raw(rec["f_data"]))
m = json.loads(raw.decode("utf-8"))
cl.close()

ts = np.array(sorted(int(k) for k in m), dtype=np.int64)
rate = np.array([float(m[str(t)]) for t in ts], dtype=np.float64)
df = pd.DataFrame({"ts_ms": ts, "rate": rate})
df["dt_utc"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
df.to_csv(OUT, index=False)

log.info("n=%d range=%s .. %s", len(df), df.dt_utc.iloc[0], df.dt_utc.iloc[-1])
log.info("rate mean=%.8f median=%.8f min=%.8f max=%.8f pct_pos=%.2f%%",
         rate.mean(), np.median(rate), rate.min(), rate.max(), 100.0 * (rate > 0).mean())
d = np.diff(ts) / 3600000.0
log.info("gap hours: median=%.3f p10=%.3f p90=%.3f max=%.3f", np.median(d),
         np.percentile(d, 10), np.percentile(d, 90), d.max())
sub = df[(df.dt_utc >= "2021-07-01") & (df.dt_utc <= "2025-12-31 23:59:59")]
log.info("window 2021-07-01..2025-12-31: n=%d sum_rate=%.6f (=tong 8h-rate)", len(sub), sub.rate.sum())
log.info("wrote %s", OUT)
