"""R1 PHA0 (chi doc): leg B0 x14 (DEV) vao o tick CO diem S1 (pred_s1a2x1.parquet) hay tick S1 trong
(bins map giu nguyen thu tu net015). printDone start = GMT+7 => ts = ((ms - 7h)//15')*15'."""
import glob
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("r1cov")
Q = 900000
s1 = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2x1.parquet", columns=["ts"])
log.info("s1 dtype=%s min=%s max=%s n=%d", s1.ts.dtype, s1.ts.min(), s1.ts.max(), len(s1))
ts = s1.ts
if np.issubdtype(ts.dtype, np.datetime64):
    ts = ts.astype("datetime64[ms]").astype("int64")
S1TS = set(np.unique(ts.values.astype("int64")))
log.info("so tick co S1 = %d", len(S1TS))
rows = []
for d in sorted(glob.glob("/home/ubuntu/kaggle_sim/out/" + sys.argv[1])):
    x = pd.read_csv(d + "/storage/printDone.csv", index_col=False, usecols=["level", "pnl", "start"])
    x["pnl"] = pd.to_numeric(x["pnl"], errors="coerce")
    ms = pd.to_datetime(x["start"], format="%Y%m%d %H:%M").astype("datetime64[ms]").astype("int64")
    x["tick"] = ((ms - 7 * 3600000) // Q) * Q
    x["on_tick"] = ((ms - 7 * 3600000) % Q) == 0
    x["s1"] = x["tick"].isin(S1TS)
    x["year"] = pd.to_datetime(x["tick"], unit="ms").dt.year
    x = x[(x.year >= 2022) & (x.year <= 2025)]
    if len(sys.argv) > 2 and sys.argv[2] == "on15":
        x = x[x.on_tick]
    for (lv, yr), g in x.groupby(["level", "year"]):
        rows.append(dict(tag=d.rsplit("/", 1)[-1], level=lv, year=yr, n=len(g), s1_share_n=g.s1.mean(),
                         on15=g.on_tick.mean(),
                         s1_share_pnl=g.loc[g.s1, "pnl"].sum() / g.pnl.sum() if g.pnl.sum() else np.nan,
                         pnl_s1=g.loc[g.s1, "pnl"].mean(), pnl_nos1=g.loc[~g.s1, "pnl"].mean()))
df = pd.DataFrame(rows)
log.info("\n%s", df.groupby(["level", "year"])[["n", "on15", "s1_share_n", "s1_share_pnl", "pnl_s1", "pnl_nos1"]].mean()
         .to_string(float_format=lambda v: "%.3f" % v))
