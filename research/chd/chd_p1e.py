"""Phase-1 quality checks on samples (independent of any pipeline)."""
import sys, io, os, glob, time
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa, pyarrow.compute as pc
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
S = "/home/ubuntu/claude_master/chd_wk/sample"
SY = ["BTCUSDT", "SOLUSDT", "MYXUSDT"]
HRS = [("2025-09-02", 12), ("2025-10-10", 21)]
def rd(date, h, s, t):
    return pq.read_table(f"{S}/{date}_{h:02d}_{s}_{t}.parquet")
def f64(tb, c):
    return tb.column(c).cast(pa.float64()).to_numpy()
def hour_ms(date, h):
    return int(pd.Timestamp(f"{date} {h:02d}:00", tz="UTC").value // 10**6)
# ---------- kline
K = {}
for m in ["2025-09", "2025-10"]:
    k = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet", filters=[("sym", "in", SY)]).to_pandas()
    k["sym"] = k["sym"].astype(str); K[m] = k
print("=== (b) trades vs kline1m")
for date, h in HRS:
    t0 = hour_ms(date, h); kl = K[date[:7]]
    for s in SY:
        tb = rd(date, h, s, "trades")
        tt = tb.column("trade_time").to_numpy(); q = f64(tb, "quantity"); p = f64(tb, "price"); ibm = tb.column("is_buyer_maker").to_numpy()
        ot = pc.value_counts(tb.column("order_type")).to_pylist()
        tid = np.sort(tb.column("trade_id").to_numpy()); gaps = np.diff(tid); nmiss = int((gaps - 1).clip(min=0).sum()); ndup = int((gaps == 0).sum())
        inh = (tt >= t0) & (tt < t0 + 3600000)
        kk = kl[(kl.sym == s) & (kl.ts >= t0) & (kl.ts < t0 + 3600000)]
        assert len(kk) == 60, len(kk)
        mi = (tt[inh] - t0) // 60000
        vmin = np.bincount(mi, weights=q[inh], minlength=60); qvmin = np.bincount(mi, weights=(p * q)[inh], minlength=60)
        tbmin = np.bincount(mi, weights=(q * (~ibm))[inh], minlength=60)
        ratio_v = vmin.sum() / kk.volume.sum(); ratio_qv = qvmin.sum() / kk.quote_volume.sum(); ratio_tb = tbmin.sum() / kk.taker_buy_base.sum()
        perm = vmin / kk.volume.to_numpy()
        bad = int((np.abs(perm - 1) > 0.01).sum())
        ntr_k = int(kk.n_trades.sum())
        print(f"{date} {h} {s}: rows={tb.num_rows} in_hour={inh.sum()} outside={(~inh).sum()} vol_ratio={ratio_v:.6f} qv_ratio={ratio_qv:.6f} takerbuy_ratio={ratio_tb:.6f} min_bad(>1%)={bad} min_ratio[min,max]=[{np.nanmin(perm):.4f},{np.nanmax(perm):.4f}] trade_id_missing={nmiss} dup={ndup} kline_n_trades={ntr_k} order_type={ot}")
        if bad:
            print("   bad minutes:", [(int(i), round(float(perm[i]), 4)) for i in np.where(np.abs(perm - 1) > 0.01)[0]][:15])
        rt = tb.column("received_time").to_numpy(); et = tb.column("event_time").to_numpy()
        lat = rt // 10**6 - et
        print(f"   recv-event latency ms p50={np.median(lat):.0f} p99={np.percentile(lat,99):.0f} max={lat.max()}; max gap event_time s={np.diff(np.sort(et)).max()/1000:.1f}")
print("=== mark_price / ticker / OI rows & gaps")
for date, h in HRS:
    t0 = hour_ms(date, h)
    for s in SY:
        for t, col in [("mark_price", "event_time"), ("ticker", "event_time"), ("open_interest", "timestamp"), ("liquidations", "trade_time")]:
            tb = rd(date, h, s, t); e = np.sort(tb.column(col).to_numpy())
            g = np.diff(np.concatenate([[t0], e, [t0 + 3600000]]))
            print(f"{date} {h} {s} {t}: rows={tb.num_rows} uniq_ts={len(np.unique(e))} range=[{(e.min()-t0)/1000:.1f}s,{(e.max()-t0)/1000:.1f}s] maxgap={g.max()/1000:.1f}s gaps>5s={int((g>5000).sum())}")
        tb = rd(date, h, s, "mark_price")
        e = tb.column("event_time").to_numpy(); g = np.diff(np.sort(e)); big = np.argsort(g)[-3:]
        es = np.sort(e)
        print("    mark_price biggest gaps (start UTC, s):", [(str(pd.Timestamp(int(es[i]), unit="ms")), g[i] / 1000) for i in big])
print("=== liquidations schema/semantics")
for date, h in HRS:
    for s in SY:
        df = rd(date, h, s, "liquidations").to_pandas()
        for c in ["quantity", "price", "average_price", "filled_quantity", "last_filled_quantity"]:
            df[c] = df[c].astype(float)
        df["notional"] = df.average_price * df.filled_quantity
        sec = df.trade_time // 1000
        print(f"{date} {h} {s}: n={len(df)} status={df.order_status.value_counts().to_dict()} type={df.order_type.value_counts().to_dict()} tif={df.time_in_force.value_counts().to_dict()} side_notional={df.groupby('side').notional.sum().round(0).to_dict()} max_per_sec={sec.value_counts().max()} filled==qty:{(df.filled_quantity==df.quantity).mean():.3f} dup(event_time,side,price,qty)={df.duplicated(['event_time','side','price','quantity']).sum()}")
