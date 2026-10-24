"""(a) liq vs P2 proxy, (c) OI vs Vision metrics, trades union across neighbour hours."""
import sys, io, time
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa
from concurrent.futures import ThreadPoolExecutor
pd.set_option("display.width", 250)
def get_df(key):
    b, _ = L.get_bytes(key)
    return None if b is None else pq.read_table(io.BytesIO(b)).to_pandas()
def key(date, h, s, t):
    return f"binance_futures/{date}/{h:02d}/{s}_{t}.parquet.zst"
def hms(date, h):
    return int(pd.Timestamp(f"{date} {h:02d}:00", tz="UTC").value // 10**6)
# --- trades union BTC/SOL 10-10 20..22
print("=== trades union over files 20,21,22 for trade_time in 21:00-22:00")
k = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-2025-10.parquet", filters=[("sym", "in", ["BTCUSDT", "SOLUSDT", "ETHUSDT", "XRPUSDT", "MYXUSDT"])]).to_pandas(); k["sym"] = k.sym.astype(str)
t0 = hms("2025-10-10", 21)
for s in ["BTCUSDT", "SOLUSDT"]:
    fr = [get_df(key("2025-10-10", h, s, "trades")) for h in (20, 21, 22)]
    d = pd.concat([f for f in fr if f is not None]).drop_duplicates("trade_id")
    d = d[(d.trade_time >= t0) & (d.trade_time < t0 + 3600000)]
    kv = k[(k.sym == s) & (k.ts >= t0) & (k.ts < t0 + 3600000)].volume.sum()
    print(s, "union vol ratio", round(d.quantity.astype(float).sum() / kv, 6), "rows", len(d), "per-file in-hour rows", [int(((f.trade_time >= t0) & (f.trade_time < t0 + 3600000)).sum()) for f in fr])
# --- OI vs Vision
print("=== (c) OI chd vs Vision metrics5m")
SY5 = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "MYXUSDT"]
jobs = [(d, h, s) for d in ("2025-09-02", "2025-10-10") for h in range(24) for s in SY5]
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(lambda a: get_df(key(a[0], a[1], a[2], "open_interest")), jobs))
oi = pd.concat([r for r in res if r is not None])
oi["oi"] = oi.sum_open_interest.astype(float); oi["oiv"] = oi.sum_open_interest_value.astype(float)
print("chd OI rows", len(oi), "dup (symbol,timestamp)", oi.duplicated(["symbol", "timestamp"]).sum(), "ts mod 300000 !=0:", (oi.timestamp % 300000 != 0).sum())
oi = oi.drop_duplicates(["symbol", "timestamp"], keep="last")
pub = (oi.received_time // 10**6 - oi.timestamp) / 1000
print("publish delay received-timestamp s: p5/p50/p95", np.percentile(pub, [5, 50, 95]).round(1))
vm = pd.concat([pq.read_table(f"/home/ubuntu/vz/out/metrics5m/2025/2025-{m}.parquet", filters=[("sym", "in", SY5)], columns=["ts", "sym", "oi", "oi_value"]).to_pandas() for m in ("09", "10")])
vm["sym"] = vm.sym.astype(str)
for lag in (-300000, 0, 300000):
    m = oi.merge(vm.assign(timestamp=vm.ts + lag), left_on=["symbol", "timestamp"], right_on=["sym", "timestamp"], suffixes=("", "_v"))
    re = (m.oi / m.oi_v - 1).abs()
    print(f"lag chd_ts = vision_ts{lag/60000:+.0f}m: n={len(m)} exact_oi={np.mean(re < 1e-9):.3f} median_rel={re.median():.2e} p95={re.quantile(.95):.2e}")
# --- (a) liq vs P2
print("=== (a) liquidations 2025-10-10 21:00-22:00 vs P2 proxy")
vmo = pq.read_table("/home/ubuntu/vz/out/metrics5m/2025/2025-10.parquet", filters=[("sym", "in", SY5)], columns=["ts", "sym", "oi_value"]).to_pandas(); vmo["sym"] = vmo.sym.astype(str)
rows = []
for s in SY5:
    fr = [get_df(key("2025-10-10", h, s, "liquidations")) for h in (21, 22)]
    lq = pd.concat([f for f in fr if f is not None]).drop_duplicates()
    lq = lq[(lq.trade_time >= t0) & (lq.trade_time < t0 + 3600000)]
    lq["n"] = lq.average_price.astype(float) * lq.filled_quantity.astype(float)
    ll = lq[lq.side == "SELL"].n.sum(); ls = lq[lq.side == "BUY"].n.sum()
    kk = k[k.sym == s].set_index("ts")
    out = {"sym": s, "liq_long_usd": ll, "liq_short_usd": ls, "n_liq": len(lq)}
    for conv, sh in (("NEW", 300000), ("RAW", 0)):
        ov = vmo[vmo.sym == s].assign(te=lambda x: x.ts + sh).set_index("te").oi_value
        p2 = 0.0; ok = 0
        for T in range(t0 + 300000, t0 + 3600000 + 1, 300000):
            if T - 300000 not in ov.index or T not in ov.index:
                continue
            bars = kk.loc[T - 300000:T - 60000]
            if len(bars) != 5:
                continue
            od = max(0.0, ov[T - 300000] - ov[T])
            tsx = max(0.0, (bars.quote_volume - bars.taker_buy_quote).sum() - bars.taker_buy_quote.sum())
            p2 += min(od, tsx); ok += 1
        out[f"P2_{conv}"] = p2; out[f"nb_{conv}"] = ok
    rows.append(out)
r = pd.DataFrame(rows)
r["ratio_liq/P2_NEW"] = r.liq_long_usd / r.P2_NEW
r["ratio_liq/P2_RAW"] = r.liq_long_usd / r.P2_RAW
print(r.round(3).to_string())
