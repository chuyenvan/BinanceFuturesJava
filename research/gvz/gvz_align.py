import numpy as np, pandas as pd, logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("al")
S = "/home/ubuntu/claude_master/gvz/store/gate_dataset_full.csv"
lo = pd.Timestamp("2022-03-01").value // 10**6
hi = pd.Timestamp("2022-03-04").value // 10**6
it = pd.read_csv(S, usecols=["timestamp", "momentum1M", "momentum5M", "volatility1M", "volumeSpike", "rsi14"], chunksize=200000)
parts = []
for c in it:
    c = c[(c.timestamp >= lo) & (c.timestamp < hi)]
    if len(c):
        parts.append(c)
    elif parts:
        break
st = pd.concat(parts).set_index("timestamp")
k = pd.read_parquet("/home/ubuntu/vz_e1/raw/kline1m-2022-03.parquet", columns=["ts", "sym", "close", "open"])
for sym in ["BTCUSDT", "ETHUSDT"]:
    b = k[k.sym == sym].set_index("ts").sort_index()
    log.info("%s ts dtype %s first %s", sym, b.index.dtype, b.index[:2].tolist())
    ts_ms = b.index.astype("int64")
    if ts_ms.max() > 1e14:
        ts_ms = ts_ms // 10**6 if ts_ms.max() > 1e16 else ts_ms // 10**3
    cl = pd.Series(b.close.values, index=ts_ms)
    r = cl.pct_change()            # r at open-time t = close[t]/close[t-1]-1 (bar closes at t+1m)
    for sh in [-3, -2, -1, 0, 1, 2]:
        x = r.reindex(st.index + sh * 60000).values
        y = st.momentum1M.values
        m = np.isfinite(x) & np.isfinite(y)
        log.info("%s momentum1M vs r(open=T%+d m) corr=%.4f n=%d", sym, sh, np.corrcoef(x[m], y[m])[0, 1], m.sum())
log.info("head %s", st.head(3).to_dict())
