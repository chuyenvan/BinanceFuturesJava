import pyarrow.parquet as pq, pandas as pd, numpy as np
G = pd.read_parquet("/home/ubuntu/claude_master/liqx_wk/buckets_AB.parquet", columns=["sym", "day", "T", "valid", "nbar", "c1", "oiv1"])
v = G.groupby(["sym", "day"]).agg(valid=("valid", "sum"), nbar0=("nbar", lambda x: (x == 0).sum()), c1na=("c1", lambda x: x.isna().sum()), oina=("oiv1", lambda x: x.isna().sum())).reset_index()
v["d"] = pd.to_datetime(v.day, unit="ms").dt.date
bad = v[v.valid < 288]
print(bad.groupby("d").size())
b4 = bad[bad.d.astype(str) == "2022-04-01"]
print(b4.head(40).to_string())
d0 = int(pd.Timestamp("2022-04-01", tz="UTC").value // 10**6)
k = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-2022-04.parquet", columns=["ts", "sym"]).to_pandas()
f = k.groupby("sym", observed=True).ts.min()
print("first ts for missing syms:", {s: str(pd.Timestamp(f.get(s, 0), unit="ms")) for s in b4.sym[:15]})
