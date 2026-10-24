"""BTC/ETH trades completeness on 30 random hours 2025-07..12 (seed fixed). Descriptive."""
import sys, io
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa
from concurrent.futures import ThreadPoolExecutor
rng = np.random.default_rng(20261024)
H0 = 1751328000000; H1 = 1767225600000
hrs = sorted(int(x) for x in rng.choice(np.arange(H0, H1, 3600000), 30, replace=False))
SY = ["BTCUSDT", "ETHUSDT"]
K = {}
for m in sorted(set(pd.Timestamp(h, unit="ms").strftime("%Y-%m") for h in hrs)):
    k = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet", filters=[("sym", "in", SY)], columns=["ts", "sym", "volume"]).to_pandas(); k["sym"] = k.sym.astype(str); K[m] = k
def fetch(a):
    H, s = a; ts = pd.Timestamp(H, unit="ms")
    bb, _ = L.get_bytes(f"binance_futures/{ts:%Y-%m-%d}/{ts:%H}/{s}_trades.parquet.zst")
    if bb is None: return a, None
    tb = pq.read_table(io.BytesIO(bb), columns=["trade_time", "quantity"])
    tt = tb.column("trade_time").to_numpy(); q = tb.column("quantity").cast(pa.float64()).to_numpy()
    return a, q[(tt >= H) & (tt < H + 3600000)].sum()
with ThreadPoolExecutor(8) as ex:
    res = dict(ex.map(fetch, [(H, s) for H in hrs for s in SY]))
r = []
for H in hrs:
    k = K[pd.Timestamp(H, unit="ms").strftime("%Y-%m")]
    row = {"hour": str(pd.Timestamp(H, unit="ms"))}
    for s in SY:
        kv = k[(k.sym == s) & (k.ts >= H) & (k.ts < H + 3600000)].volume.sum()
        row[s] = None if res[(H, s)] is None else res[(H, s)] / kv
    r.append(row)
r = pd.DataFrame(r); print(r.round(4).to_string())
for s in SY:
    print(s, "hours<0.99:", int((r[s] < 0.99).sum()), "missing files:", int(r[s].isna().sum()), "median", round(r[s].median(), 5))
