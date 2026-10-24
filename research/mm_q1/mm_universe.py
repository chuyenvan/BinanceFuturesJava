"""MM_Q1 symbol universe: median daily quote volume 2025-07 (PIT, missing day = 0), rank, seeded pick."""
import io, sys, json
import numpy as np, pandas as pd, pyarrow.parquet as pq
k = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-2025-07.parquet", columns=["ts", "sym", "quote_volume"]).to_pandas()
k["sym"] = k.sym.astype(str)
assert k.ts.dtype == np.int64
k["day"] = k.ts // 86400000
days = np.arange(1751328000000 // 86400000, 1751328000000 // 86400000 + 31)
assert k.day.min() == days[0] and k.day.max() == days[-1], (k.day.min(), k.day.max())
d = k.groupby(["sym", "day"]).quote_volume.sum().unstack().reindex(columns=days).fillna(0.0)
nb = k.groupby(["sym", "day"]).size().unstack().reindex(columns=days).fillna(0)
med = d.median(axis=1)
EXCL_BASE = ("USDC", "FDUSD", "TUSD", "USDP", "USDE", "BUSD", "BTCDOM", "DEFI", "FOOTBALL", "BLUEBIRD")
t = pd.DataFrame({"med_qv": med, "full31": (nb > 0).all(axis=1), "bars": nb.sum(axis=1)})
t = t[t.index.str.endswith("USDT")]
t["excluded_stable_index"] = [s[:-4] in EXCL_BASE for s in t.index]
t = t[~t.excluded_stable_index].sort_values("med_qv", ascending=False)
t["rank"] = np.arange(1, len(t) + 1)
print("n symbols ranked", len(t))
print(t.head(8).to_string())
inv = pd.read_parquet("/home/ubuntu/claude_master/chd_wk/inv/2025-07-01.parquet").astype({"symbol": str, "data_type": str})
have = inv[inv.data_type.isin(["trades", "orderbook"])].groupby("symbol").data_type.nunique()
have = set(have[have == 2].index)
t["chd_0701"] = [s in have for s in t.index]
rng = np.random.default_rng(20261024)
out = {}
for name, lo, hi in [("mid", 20, 40), ("small", 80, 150)]:
    band = t[(t["rank"] >= lo) & (t["rank"] <= hi)]
    elig = band[band.full31 & band.chd_0701 & (band.bars == 31 * 1440)]
    print(name, "band", len(band), "eligible", len(elig), "ineligible:", band[~band.index.isin(elig.index)][["rank", "full31", "bars", "chd_0701"]].to_dict("index"))
    pick = list(rng.choice(np.array(sorted(elig.index)), 4, replace=False))
    out[name] = [(s, int(t.loc[s, "rank"]), round(float(t.loc[s, "med_qv"]) / 1e6, 2)) for s in pick]
out["big"] = [(s, int(t.loc[s, "rank"]), round(float(t.loc[s, "med_qv"]) / 1e6, 2)) for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]]
print(json.dumps(out))
