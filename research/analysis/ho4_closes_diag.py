#!/usr/bin/env python3
"""HO4-P3 chan doan cong V: dong CLOSES_1H chi co o ban Vision dung lai (khong co o ghim) theo symbol/khoang thoi gian.
Chi dem. Usage: ho4_closes_diag.py <out.json>"""
import json, logging, sys
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
LO, HI = 1746057600000, 1767225600000
a = np.fromfile("/home/ubuntu/java/fsrun/CLOSES_1H.bin", dtype=DT)
b = np.fromfile("/home/ubuntu/claude_master/1010/ho4/s1/CLOSES_1H_dev.bin", dtype=DT)
f = lambda x: x[(x["ts"].astype(np.int64) >= LO) & (x["ts"].astype(np.int64) < HI)]
a, b = f(a), f(b)
ka = a["ts"].astype(np.int64) * 10000 + a["sym"].astype(np.int64)
kb = b["ts"].astype(np.int64) * 10000 + b["sym"].astype(np.int64)
only = b[~np.isin(kb, ka)]
mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
i2s = dict(zip(mp.symId, mp.symbol))
d = pd.DataFrame({"ts": only["ts"].astype(np.int64), "sym": only["sym"].astype(int)})
g = d.groupby("sym").ts.agg(["count", "min", "max"]).sort_values("count", ascending=False)
pin_last = pd.DataFrame({"ts": a["ts"].astype(np.int64), "sym": a["sym"].astype(int)}).groupby("sym").ts.max()
pin_first = pd.DataFrame({"ts": a["ts"].astype(np.int64), "sym": a["sym"].astype(int)}).groupby("sym").ts.min()
rows = []
for s, r in g.head(40).iterrows():
    rows.append(dict(sym=i2s.get(s, s), n=int(r["count"]), first=str(pd.to_datetime(r["min"], unit="ms")), last=str(pd.to_datetime(r["max"], unit="ms")),
                     pin_first=str(pd.to_datetime(pin_first.get(s), unit="ms")) if s in pin_first else None,
                     pin_last=str(pd.to_datetime(pin_last.get(s), unit="ms")) if s in pin_last else None))
per_hour = d.groupby("ts").size()
res = dict(n_only=int(len(d)), n_sym=int(d.sym.nunique()), hours_with_extra=int(len(per_hour)), top=rows,
           n_hours_window=int((HI - LO) // 3600000))
json.dump(res, open(sys.argv[1], "w"), indent=1)
logging.info(json.dumps(res, indent=0)[:3500])
