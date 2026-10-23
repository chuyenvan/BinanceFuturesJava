"""LIQX_S0 step 1: daily quote volume per symbol from kline1m parquet (2021-12..2025-12) for PIT universe."""
import pyarrow.parquet as pq, pandas as pd, numpy as np, os, sys
WK = os.path.expanduser("~/claude_master/liqx_wk")
KL = "/home/ubuntu/vz_e1/raw/kline1m-%04d-%02d.parquet"
out = []
months = [(2021, 12)] + [(y, m) for y in range(2022, 2026) for m in range(1, 13)]
for y, m in months:
    pf = pq.ParquetFile(KL % (y, m))
    for i in range(pf.num_row_groups):
        t = pf.read_row_group(i, columns=["ts", "sym", "quote_volume"]).to_pandas()
        assert t.ts.dtype == np.int64
        t["day"] = (t.ts // 86_400_000).astype("int64") * 86_400_000
        g = t.groupby([t.sym.astype(str), "day"]).quote_volume.sum().reset_index()
        g.columns = ["sym", "day", "qv"]
        out.append(g)
    print(y, m, pf.num_row_groups, flush=True)
d = pd.concat(out, ignore_index=True)
d = d.groupby(["sym", "day"], as_index=False).qv.sum()
assert d.day.dtype == np.int64
d.to_parquet(WK + "/daily_qv.parquet", index=False)
print("rows", len(d), "syms", d.sym.nunique())
