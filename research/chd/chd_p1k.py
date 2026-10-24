"""Coverage (20 symbols) + size/request estimates from the S3 inventory (no downloads)."""
import glob, os, sys, json
import numpy as np, pandas as pd, pyarrow.parquet as pq
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
INV = sorted(glob.glob("/home/ubuntu/claude_master/chd_wk/inv/*.parquet"))
print("inventory days", len(INV), INV[0][-18:], INV[-1][-18:])
# top-20 by quote volume 2025-07..12 (PIT-free descriptive pick)
qv = None
for m in ["2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"]:
    k = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet", columns=["sym", "quote_volume"]).to_pandas()
    s = k.groupby("sym", observed=True).quote_volume.sum(); qv = s if qv is None else qv.add(s, fill_value=0)
TOP20 = list(qv.sort_values(ascending=False).index[:20].astype(str))
print("TOP20", TOP20)
TYPES = ["liquidations", "open_interest", "mark_price", "trades", "orderbook", "ticker", "aggtrades"]
tot = []; cov = []; hrs_all = []
for f in INV:
    d = pd.read_parquet(f)
    if not len(d): continue
    d["data_type"] = d.data_type.astype(str); d["symbol"] = d.symbol.astype(str)
    tot.append(d.groupby("data_type").agg(n=("size", "size"), b=("size", "sum")).assign(date=d.date.iloc[0]))
    hrs_all.append(d.groupby("hour").size().rename("n").reset_index().assign(date=str(d.date.iloc[0])))
    x = d[d.symbol.isin(TOP20) & d.data_type.isin(TYPES)]
    cov.append(x[["date", "hour", "symbol", "data_type", "size"]].astype({"date": str}))
tot = pd.concat(tot).reset_index()
cov = pd.concat(cov); hrs_all = pd.concat(hrs_all)
T = tot.groupby("data_type").agg(files=("n", "sum"), GB=("b", "sum")); T["GB"] /= 1e9
T["files_per_hour"] = T.files / len(hrs_all)
T["hours_at_20fps"] = T.files / 20 / 3600
print("=== totals over inventory (wire bytes)"); print(T.round(3).to_string())
# hours present globally
hrs_all["t"] = pd.to_datetime(hrs_all.date) + pd.to_timedelta(hrs_all.hour, unit="h")
first, last = hrs_all.t.min(), hrs_all.t.max()
full = pd.date_range(first, last, freq="h")
print("global first/last hour", first, last, "hours expected", len(full), "hours with any object", hrs_all.t.nunique(), "missing:", [str(x) for x in full.difference(hrs_all.t)][:30])
med = hrs_all.n.median(); low = hrs_all[hrs_all.n < 0.5 * med]
print("hours with < 50% of median object count:", len(low), low.sort_values("t").t.astype(str).tolist()[:30])
# coverage per symbol x type over full span
cov["t"] = pd.to_datetime(cov.date) + pd.to_timedelta(cov.hour, unit="h")
rows = []
for s in TOP20:
    cs = cov[cov.symbol == s]
    if not len(cs): rows.append({"symbol": s}); continue
    span = pd.date_range(max(cs.t.min(), first), cs.t.max(), freq="h")
    r = {"symbol": s, "first": str(cs.t.min())[:13], "last": str(cs.t.max())[:13], "span_h": len(span)}
    for ty in TYPES:
        r[ty] = round(cs[cs.data_type == ty].t.nunique() / len(span), 4)
    rows.append(r)
C = pd.DataFrame(rows); print("=== coverage (fraction of hours in span with a file)"); print(C.to_string())
print("min coverage per type:", C[TYPES].min().round(4).to_dict())
# per-type missing hours for BTC
b = cov[cov.symbol == "BTCUSDT"]
for ty in ["liquidations", "open_interest", "mark_price", "trades", "orderbook"]:
    miss = full.difference(b[b.data_type == ty].t)
    print(f"BTC {ty} missing hours: {len(miss)}", [str(x)[:13] for x in miss[:12]])
# per (symbol,hour) mean sizes for trades/orderbook: top-20 vs rest
cov.to_parquet("/home/ubuntu/claude_master/chd_wk/cov_top20.parquet")
tot.to_parquet("/home/ubuntu/claude_master/chd_wk/inv_daily_totals.parquet")
