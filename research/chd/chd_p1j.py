"""Liquidations CHD vs independent reference (Tardis day-01 or owner's collector). Descriptive."""
import sys, io
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import numpy as np, pandas as pd, pyarrow.parquet as pq
from concurrent.futures import ThreadPoolExecutor
ref, date = sys.argv[1], sys.argv[2]; hours = [int(x) for x in sys.argv[3].split(",")]
keys = [o["key"] for h in hours for o in L.list_hour(date, h) if o["data_type"] == "liquidations"]
def f(k):
    b, _ = L.get_bytes(k)
    return None if b is None else pq.read_table(io.BytesIO(b)).to_pandas()
with ThreadPoolExecutor(8) as ex:
    c = pd.concat([x for x in ex.map(f, keys) if x is not None])
t0 = int(pd.Timestamp(f"{date} {hours[0]:02d}:00", tz="UTC").value // 10**6) + 60000
t1 = int(pd.Timestamp(f"{date} {hours[-1]:02d}:00", tz="UTC").value // 10**6) + 3600000 - 60000
c = c[(c.event_time >= t0) & (c.event_time < t1)].copy()
c["n"] = c.average_price.astype(float) * c.filled_quantity.astype(float)
c["n_p"] = c.price.astype(float) * c.quantity.astype(float)
print("CHD files", len(keys), "rows in window", len(c), "dup(symbol,event_time,side)", c.duplicated(["symbol", "event_time", "side"]).sum())
if ref == "tardis":
    r = pd.read_csv(f"/home/ubuntu/claude_master/liqx_wk/tardis/liquidations_{date}_PERPETUALS.csv.gz")
    r["event_time"] = (r.timestamp // 1000).astype("int64"); r["side"] = r.side.map({"sell": "SELL", "buy": "BUY"}); r["n"] = r.price * r.amount
else:
    r = pd.read_csv(f"/home/ubuntu/collect/liq/{date}.csv.gz")
    r = r[r.status == "FILLED"]; r["n"] = r.avg_price * r.filled_qty
r = r[(r.event_time >= t0) & (r.event_time < t1)]
if ref == "tardis" and len(sys.argv) > 4:
    c["event_time"] = c["trade_time"]; print("  (matching tardis timestamp to CHD trade_time)")
m = c.merge(r[["symbol", "event_time", "side", "n"]], on=["symbol", "event_time", "side"], how="outer", suffixes=("_c", "_r"), indicator=True)
vc = m._merge.value_counts().to_dict()
both = m[m._merge == "both"]
print(f"ref={ref} {date} hours={hours} window=[+1m,-1m]: ref_rows={len(r)} match={vc.get('both',0)} chd_only={vc.get('left_only',0)} ref_only={vc.get('right_only',0)}")
print(f"  notional: CHD(avg*filled)={c.n.sum():,.0f} CHD(price*qty)={c.n_p.sum():,.0f} REF={r.n.sum():,.0f}; matched rel diff median={((both.n_c/both.n_r)-1).abs().median():.2e}")
ro = m[m._merge == "right_only"]
if len(ro):
    print("  ref_only by minute (top):", (pd.to_datetime(ro.event_time, unit="ms").dt.floor("min").value_counts().head(5)).to_dict())
    print("  ref_only by symbol (n, notional):", ro.groupby("symbol").n_r.agg(["size", "sum"]).sort_values("sum", ascending=False).head(8).round(0).to_dict("index"))
    print("  ref_only symbols with ANY CHD liq file in window:", sorted(set(ro.symbol) & set(c.symbol))[:10])
lo = m[m._merge == "left_only"]
if len(lo):
    print("  chd_only by minute (top):", (pd.to_datetime(lo.event_time, unit="ms").dt.floor("min").value_counts().head(5)).to_dict())
