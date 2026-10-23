import pandas as pd, numpy as np, pyarrow.parquet as pq, pyarrow.compute as pc, glob, os
W = os.path.expanduser("~/claude_master/liqx_wk")
# 1 Tardis
fs = sorted(glob.glob(W + "/tardis/*.csv.gz"))
allsym = set(); 
for f in fs[:1] + fs[-1:]:
    d = pd.read_csv(f)
    print(os.path.basename(f), d.dtypes.to_dict())
    print(" side", d.side.value_counts().to_dict(), "id null", d.id.isna().mean(), "exch", d.exchange.unique())
    print(" ts-local us median", np.median(d.local_timestamp - d.timestamp), "ts%1000", (d.timestamp % 1000 == 0).mean())
    print(" nonUSDT", sorted(set(s for s in d.symbol.unique() if not s.endswith("USDT")))[:20])
    print(" min max ts", pd.to_datetime(d.timestamp.min(), unit="us"), pd.to_datetime(d.timestamp.max(), unit="us"))
    # same-second dup per symbol (snapshot check)
    sec = d.timestamp // 1_000_000
    print(" max events per sym-second", d.groupby([d.symbol, sec]).size().max(), "frac sym-sec >1", (d.groupby([d.symbol, sec]).size() > 1).mean())
d = pd.read_csv(fs[0]); b = d[d.symbol == "BTCUSDT"]
os.system("curl -s -o /tmp/liqx0_btc.gz https://datasets.tardis.dev/v1/binance-futures/liquidations/2022/01/01/BTCUSDT.csv.gz")
e = pd.read_csv("/tmp/liqx0_btc.gz"); print("BTC per-sym rows", len(e), "in PERP", len(b), "equal", e.reset_index(drop=True)[["timestamp","side","price","amount"]].equals(b.reset_index(drop=True)[["timestamp","side","price","amount"]]))
# 2 OI semantics
for day, mf in [("2024-01-01", "/home/ubuntu/vz/out/metrics5m/2024/2024-01.parquet"), ("2022-05-01", "/home/ubuntu/vz/out/metrics5m/2022/2022-05.parquet")]:
    t = pd.read_csv(W + "/probe/dt_%s.csv.gz" % day, usecols=["timestamp", "open_interest"]).dropna()
    t["ms"] = (t.timestamp // 1000).astype("int64"); t = t.sort_values("ms")
    print(day, "tardis OI rows", len(t), "median dt s", np.median(np.diff(t.ms)) / 1000, "n unique OI", t.open_interest.nunique())
    tab = pq.read_table(mf, filters=[("sym", "=", "BTCUSDT")]).to_pandas()
    t0 = int(pd.Timestamp(day, tz="UTC").value // 10**6)
    v = tab[(tab.ts >= t0 + 3600_000) & (tab.ts < t0 + 86400_000 - 3600_000)].copy()
    print(" vision ts%300000==0", (v.ts % 300000 == 0).mean(), "rows", len(v))
    # OI change times in tardis
    ch = t.ms[t.open_interest.diff() != 0]
    print(" tardis OI change interval median s", np.median(np.diff(ch.values)) / 1000)
    for L in range(-300_000, 300_001, 15_000):
        idx = np.searchsorted(t.ms.values, v.ts.values + L, side="right") - 1
        oi_t = t.open_interest.values[idx]
        err = np.abs(v.oi.values - oi_t) / v.oi.values
        print("  L=%+5ds med_relerr=%.2e exact=%.3f" % (L // 1000, np.median(err), (err < 1e-9).mean()))
# 3 completeness
for mf, day in [("/home/ubuntu/vz/out/metrics5m/2022/2022-01.parquet", "2022-01-01"), ("/home/ubuntu/vz/out/metrics5m/2025/2025-12.parquet", "2025-12-01")]:
    t0 = int(pd.Timestamp(day, tz="UTC").value // 10**6)
    m = pq.read_table(mf, columns=["ts", "sym", "oi_value"], filters=[("ts", ">=", t0), ("ts", "<=", t0 + 86400_000)]).to_pandas()
    c = m.groupby("sym", observed=True).ts.nunique()
    print(day, "metrics syms", len(c), "cnt dist", c.value_counts().head(5).to_dict(), "dup rows", len(m) - m.groupby(["sym", "ts"], observed=True).ngroups, "ts mod", (m.ts % 300000).value_counts().head(3).to_dict())
    kf = "/home/ubuntu/vz_e1/raw/kline1m-%s.parquet" % day[:7]
    k = pq.read_table(kf, columns=["ts", "sym", "active"], filters=[("ts", ">=", t0), ("ts", "<", t0 + 86400_000)]).to_pandas()
    kc = k.groupby("sym", observed=True).ts.nunique()
    print(" kline syms", len(kc), "cnt dist", kc.value_counts().head(5).to_dict(), "active frac", k.active.mean())
