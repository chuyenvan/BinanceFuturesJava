#!/usr/bin/env python3
"""HO4-P0b Q1(iii): so 3 duong cho store gate tren cung phut (DEV 2025): DEV store (gate_dataset_full, export 08-08) vs
port Python devexport_202609 doc Aerospike LOCAL hien tai (--cluster local) vs file khac (vd D1 Java tren ticker DEV).
33 cot V3FULL, rel 1e-6 (NaN==NaN). Chi dem/ty le. Usage: ho4b_portcmp.py <out.json> <name=csv[.gz]> ..."""
import json, logging, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava"); sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
use = ["timestamp"] + GA.V3FULL
srcs = {"dev": GA.STORE}
for a in sys.argv[2:]:
    k, v = a.split("=", 1)
    srcs[k] = v
D = {}
for k, p in srcs.items():
    d = pd.read_csv(p, usecols=lambda c: c in use or c == "ts")
    if "ts" in d.columns and "timestamp" not in d.columns:
        d = d.rename(columns={"ts": "timestamp"})
    D[k] = d
ts = None
for k in srcs:
    if k != "dev":
        t = set(D[k].timestamp)
        ts = t if ts is None else ts & t
D = {k: v[v.timestamp.isin(ts)].drop_duplicates("timestamp").set_index("timestamp").sort_index() for k, v in D.items()}
res = dict(n_ts=len(ts), pairs={})
keys = list(srcs)
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        a, b = D[keys[i]], D[keys[j]]
        idx = a.index.intersection(b.index)
        per = {}
        tot = bad = 0
        for c in GA.V3FULL:
            x, y = a.loc[idx, c].to_numpy(np.float64), b.loc[idx, c].to_numpy(np.float64)
            ok = (np.abs(x - y) <= 1e-6 * np.maximum(1.0, np.abs(y))) | (np.isnan(x) & np.isnan(y))
            per[c] = round(float(ok.mean()), 4)
            tot += len(ok); bad += int((~ok).sum())
        res["pairs"]["%s_vs_%s" % (keys[i], keys[j])] = dict(rows=int(len(idx)), ok_frac=1 - bad / max(tot, 1),
                                                           cols_bad={c: v for c, v in per.items() if v < 0.999})
        logging.info("%s vs %s rows=%d ok=%.4f bad_cols=%s", keys[i], keys[j], len(idx), 1 - bad / max(tot, 1),
                     {c: v for c, v in per.items() if v < 0.999})
json.dump(res, open(sys.argv[1], "w"), indent=1)
