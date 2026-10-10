#!/usr/bin/env python3
"""HO3 B2: liet ke phut THIEU key kline_1m_opt (CHI DOC, exists) tren 242 ns ticker cho 2026-07-01..10-01 +07."""
import datetime, json, sys
from concurrent.futures import ThreadPoolExecutor
import aerospike
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
cli = aerospike.client({"hosts": [("103.157.218.242", 3222)], "policies": {"timeout": 8000}}).connect()
t0 = datetime.datetime(2026, 7, 1, tzinfo=TZ7); t1 = datetime.datetime(2026, 10, 1, tzinfo=TZ7)
keys = []
t = t0
while t < t1:
    keys.append(t.strftime("%Y%m%d-%H%M")); t += datetime.timedelta(minutes=1)
def one(k):
    try:
        _, meta = cli.exists(("ticker", "kline_1m_opt", k))
        return k, meta is not None
    except aerospike.exception.RecordNotFound:
        return k, False
    except Exception as e:
        return k, None
miss, err = [], []
with ThreadPoolExecutor(40) as ex:
    for k, ok in ex.map(one, keys):
        if ok is False: miss.append(k)
        elif ok is None: err.append(k)
# gop thanh doan lien tiep
runs = []
for k in miss:
    ts = datetime.datetime.strptime(k, "%Y%m%d-%H%M")
    if runs and ts - runs[-1][1] == datetime.timedelta(minutes=1):
        runs[-1][1] = ts
    else:
        runs.append([ts, ts])
out = dict(window="2026-07-01..2026-10-01 +07", n_keys=len(keys), n_missing=len(miss), n_err=len(err),
           runs=[[a.strftime("%Y-%m-%d %H:%M"), b.strftime("%Y-%m-%d %H:%M"), int((b - a).total_seconds() // 60) + 1] for a, b in runs])
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "runs"}), "runs", len(runs), out["runs"][:20])
