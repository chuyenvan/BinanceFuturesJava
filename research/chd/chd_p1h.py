"""Trades completeness vs kline1m on onset hour of each MKT episode (variant main, 2025-07..12). Descriptive."""
import sys, io
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa
from concurrent.futures import ThreadPoolExecutor
a, b = int(sys.argv[1]), int(sys.argv[2])
SY = ["BTCUSDT", "SOLUSDT", "DOGEUSDT"]
e = pd.read_parquet("/home/ubuntu/claude_master/liqx_wk/s1/episodes.parquet")
e = e[(e.level == "MKT") & (e.variant == "main") & (e.T_on >= 1751328000000) & (e.T_on < 1767225600000)].sort_values("T_on").reset_index(drop=True)
hrs = sorted(set((t // 3600000) * 3600000 for t in e.T_on))[a:b]
KC = {}
def kl(m):
    if m not in KC:
        k = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet", filters=[("sym", "in", SY)], columns=["ts", "sym", "volume"]).to_pandas(); k["sym"] = k.sym.astype(str); KC[m] = k
    return KC[m]
def fetch(args):
    H, s, t = args
    ts = pd.Timestamp(H, unit="ms"); key = f"binance_futures/{ts:%Y-%m-%d}/{ts:%H}/{s}_{t}.parquet.zst"
    bb, _ = L.get_bytes(key)
    if bb is None: return args, None
    cols = ["trade_time", "quantity", "trade_id"] if t == "trades" else ["event_time"]
    return args, pq.read_table(io.BytesIO(bb), columns=cols)
jobs = [(H, s, "trades") for H in hrs for s in SY] + [(H, "BTCUSDT", "mark_price") for H in hrs]
with ThreadPoolExecutor(8) as ex:
    res = dict(ex.map(fetch, jobs))
for H in hrs:
    k = kl(pd.Timestamp(H, unit="ms").strftime("%Y-%m"))
    out = [str(pd.Timestamp(H, unit="ms"))]
    for s in SY:
        tb = res[(H, s, "trades")]
        if tb is None: out.append(f"{s}:MISSING"); continue
        tt = tb.column("trade_time").to_numpy(); q = tb.column("quantity").cast(pa.float64()).to_numpy()
        inh = (tt >= H) & (tt < H + 3600000)
        kv = k[(k.sym == s) & (k.ts >= H) & (k.ts < H + 3600000)].volume.sum()
        tid = np.sort(tb.column("trade_id").to_numpy()); miss = int((np.diff(tid) - 1).clip(min=0).sum())
        out.append(f"{s}:{q[inh].sum()/kv:.4f}(miss_id={miss})")
    mp = res[(H, "BTCUSDT", "mark_price")]
    out.append(f"markBTC rows={mp.num_rows if mp is not None else 0}")
    print(" | ".join(out))
