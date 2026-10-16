import json
import logging
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("diag")
d = pd.read_parquet("/home/ubuntu/vz_bd/r2_legs_2024.parquet")
rows = []
for m, g in d.groupby(d.t0.dt.month):
    k = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-2024-%02d.parquet" % m, columns=["ts", "sym", "open", "high", "low", "close"]).to_pandas()
    k = k[k.sym.isin(set(g.symbol))].set_index(["sym", "ts"]).sort_index()
    for i, r in g.iterrows():
        t0 = int(r.t0.value // 10**6)
        w = [k.loc[(r.symbol, t0 + j * 60000)] if (r.symbol, t0 + j * 60000) in k.index else None for j in (-1, 0)]
        w = [x for x in w if x is not None]
        if not w:
            continue
        lo, hi = min(x.low for x in w), max(x.high for x in w)
        c = w[-1].close
        rows.append(dict(i=i, rel=abs(r.mid / c - 1), inrange=bool(lo * 0.998 <= r.mid <= hi * 1.002),
                         lag_s=(r.t_dec - r.snap_ts).total_seconds(), bar_ret=w[-1].close / w[-1].open - 1))
x = pd.DataFrame(rows)
res = dict(n=len(x), rel_q=x.rel.quantile([.5, .75, .9, .95, .99]).round(4).to_dict(),
           in_range_2bar=float(x.inrange.mean()), lag_q=x.lag_s.quantile([.5, .9, .99]).to_dict(),
           rel_by_crash={"bar<=-2%": float(x[x.bar_ret <= -0.02].rel.median()), "bar>-2%": float(x[x.bar_ret > -0.02].rel.median())},
           within1_noncrash=float((x[x.bar_ret > -0.02].rel <= 0.01).mean()), n_crash=int((x.bar_ret <= -0.02).sum()))
log.info(json.dumps(res, default=str))
