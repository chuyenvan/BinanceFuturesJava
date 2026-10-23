import pyarrow.parquet as pq, pandas as pd, numpy as np
d0 = int(pd.Timestamp("2022-04-01", tz="UTC").value // 10**6)
k = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-2022-04.parquet", columns=["ts", "sym", "volume"], filters=[("ts", ">=", d0), ("ts", "<", d0 + 86400000)]).to_pandas()
c = k.groupby("sym", observed=True).size(); print(c.value_counts().head())
s = c[c < 1440].index[0]; t = k[k.sym == s].ts.values
miss = np.setdiff1d(d0 + 60000 * np.arange(1440), t); print(s, len(miss), pd.to_datetime(miss[[0, -1]], unit="ms"))
allmiss = set(d0 + 60000 * np.arange(1440))
for s2 in c[c < 1440].index[:10]:
    tt = k[k.sym == s2].ts.values; m = np.setdiff1d(d0 + 60000 * np.arange(1440), tt)
    print(s2, len(m), pd.Timestamp(m.min(), unit="ms"), pd.Timestamp(m.max(), unit="ms"))
