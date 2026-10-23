"""LIQX_S0 V3: manual check of 5 largest LIQ_long buckets (A u B) read straight from raw files."""
import pandas as pd, pyarrow.parquet as pq, numpy as np, os, json
WK = os.path.expanduser("~/claude_master/liqx_wk")
OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/liqx_s0")
G = pd.read_parquet(WK + "/buckets_AB.parquet")
top = G[G.valid].nlargest(5, "liq_long")
rep = []
for _, r in top.iterrows():
    s, T = r.sym, int(r["T"]); ts = pd.Timestamp(T, unit="ms"); y, m = ts.year, ts.month
    met = pq.read_table(f"/home/ubuntu/vz/out/metrics5m/{y}/{y}-{m:02d}.parquet", columns=["ts", "sym", "oi", "oi_value"],
                        filters=[("ts", ">=", T - 300000), ("ts", "<=", T)]).to_pandas()
    met = met[met.sym.astype(str) == s]
    kl = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{y}-{m:02d}.parquet", columns=["ts", "sym", "close", "quote_volume", "taker_buy_quote"],
                       filters=[("ts", ">=", T - 360000), ("ts", "<", T)]).to_pandas()
    kl = kl[kl.sym.astype(str) == s].sort_values("ts")
    t = pd.read_csv(f"{WK}/tardis/liquidations_{y}-{m:02d}-01_PERPETUALS.csv.gz")
    t = t[(t.symbol == s) & (t.timestamp // 1000 >= T - 300000) & (t.timestamp // 1000 < T)]
    oiv0 = float(met[met.ts == T - 300000].oi_value.iloc[0]); oiv1 = float(met[met.ts == T].oi_value.iloc[0])
    k5 = kl[kl.ts >= T - 300000]
    man = dict(sym=s, T=str(ts), oiv0=oiv0, oiv1=oiv1, oidrop=max(0, oiv0 - oiv1),
               c0=float(kl[kl.ts == T - 360000].close.iloc[0]), c1=float(kl[kl.ts == T - 60000].close.iloc[0]),
               qv=float(k5.quote_volume.sum()), tbq=float(k5.taker_buy_quote.sum()),
               liq_long_raw=float((t[t.side == "sell"].price * t[t.side == "sell"].amount).sum()), n_sell=int((t.side == "sell").sum()),
               liq_short_raw=float((t[t.side == "buy"].price * t[t.side == "buy"].amount).sum()),
               first_last_liq=[str(pd.Timestamp(t.timestamp.min(), unit="us")), str(pd.Timestamp(t.timestamp.max(), unit="us"))])
    man["r5"] = float(np.log(man["c1"] / man["c0"])); man["tsx"] = max(0.0, man["qv"] - 2 * man["tbq"])
    pipe = dict(oiv0=r.oiv0, oiv1=r.oiv1, c0=r.c0, c1=r.c1, qv=r.qv, tbq=r.tbq, liq_long=r.liq_long, liq_short=r.liq_short)
    man["match"] = bool(all(abs(man[k] - pipe[k]) <= 1e-9 * max(1, abs(pipe[k])) for k in ("oiv0", "oiv1", "c0", "c1", "qv", "tbq"))
                        and abs(man["liq_long_raw"] - pipe["liq_long"]) <= 1e-6 * max(1, pipe["liq_long"]) and abs(man["liq_short_raw"] - pipe["liq_short"]) <= 1e-6 * max(1, pipe["liq_short"]))
    man["oi_contracts_drop"] = float(met[met.ts == T - 300000].oi.iloc[0] - met[met.ts == T].oi.iloc[0])
    rep.append(man); print(json.dumps(man))
json.dump(rep, open(OUT + "/v3_manual.json", "w"), indent=1)
