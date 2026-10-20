#!/usr/bin/env python3
"""Lien he lech breadth/p15 voi so symbol collector chot o giay ~4 (thieu_ws)."""
import glob, gzip, re, sys, datetime as dt
import numpy as np, pandas as pd
W = "/home/ubuntu/claude_master/parity_1020"
exec(open(W + "/par_a.py").read().split("res = {}")[0])
rows = []
pat = re.compile(r"Chốt nến phút (\d{8}) (\d\d):(\d\d) thành công\. Total: (\d+) symbols \(ws_final=(\d+) ws_flush_1s5=(\d+) rest_som=(\d+) rest_loi=(\d+) thieu_ws=(\d+)")
for s in gzip.open(W + "/raw242/collector_settle.gz", "rt", errors="ignore"):
    m = pat.search(s)
    if m:
        d, hh, mi = m.group(1), m.group(2), m.group(3)
        t = int(dt.datetime.strptime(d + hh + mi, "%Y%m%d%H%M").replace(tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000)
        rows.append(dict(min=t, total=int(m.group(4)), thieu=int(m.group(9)), tlog=s[11:23]))
C = pd.DataFrame(rows).drop_duplicates("min", keep="last")
P = pd.read_csv(W + "/out_minute_p15_rates.csv.gz")
X = P.merge(C, on="min", how="left")
print("joined", len(X), "missing collector", X.total.isna().sum())
X["partial"] = X.thieu > 0
print(X.groupby("partial").p15_rel.agg(["median", lambda x: (x <= 1e-3).mean(), "size"]))
X["thieu_b"] = pd.cut(X.thieu, [-1, 0, 100, 300, 400, 500, 800])
print(X.groupby("thieu_b").p15_rel.agg(["median", lambda x: (x <= 1e-3).mean(), "size"]))
X["day"] = pd.to_datetime(X["min"] + 7 * 3600000, unit="ms").dt.strftime("%m-%d")
print(X.groupby("day").partial.mean())
# so symbol hien co tren Aerospike cho vai phut partial
import aerospike
sys.argv = ["x"]
src = open(W + "/devexport_1020.py").read()
ns = {}
exec(src.split("# --------------------------- protobuf parse ---------------------------")[1].split("def time_feats")[0], ns) if False else None
from importlib.machinery import SourceFileLoader
dx = SourceFileLoader("dx", W + "/devexport_1020.py").load_module()
c = aerospike.client({"hosts": [("103.157.218.242", 3222)], "policies": {"timeout": 8000}}).connect()
for t in X[X.thieu > 400]["min"].head(5).tolist() + X[X.thieu == 0]["min"].head(2).tolist():
    k = dt.datetime.fromtimestamp(t / 1000, dt.timezone(dt.timedelta(hours=7))).strftime("%Y%m%d-%H%M")
    r = c.get(("ticker", "kline_1m_opt", k))
    syms, arr = dx.parse_minute(r[2]["data"])
    print(k, "now_in_aerospike", len(syms), "collector_total", int(X.loc[X["min"] == t, "total"].iloc[0]), "rel", float(X.loc[X["min"] == t, "p15_rel"].iloc[0]))
c.close()
X.to_csv(W + "/out_minute_collector.csv.gz", index=False)
