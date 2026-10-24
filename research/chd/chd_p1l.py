"""D3 plan + size estimate from inventory (no downloads)."""
import glob
import numpy as np, pandas as pd, pyarrow.parquet as pq
H = 3600000
e = pd.read_parquet("/home/ubuntu/claude_master/liqx_wk/s1/episodes.parquet")
e = e[(e.level == "MKT") & (e.variant == "main") & (e.T_on >= 1751328000000) & (e.T_on < 1767225600000)].sort_values("T_on")
print("episodes main 2025H2:", len(e), "incl 10-10 21:00:", (e.T_on == 1760130000000).any())
fr = []
for f in glob.glob("/home/ubuntu/kaggle_sim/out/tsx-x14-*/storage/printDone.csv"):
    d = pd.read_csv(f, index_col=False); d.columns = [c.strip() for c in d.columns]
    d["sym"] = d["sym"].astype(str).str.strip(); d["sym"] = d["sym"].where(d["sym"].str.endswith("USDT"), d["sym"] + "USDT")
    d["su"] = (pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)).astype("int64") // 10**6
    fr.append(d[["sym", "su"]])
x14 = pd.concat(fr)
KC = {}
def kl(m):
    if m not in KC:
        k = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet", columns=["ts", "sym", "quote_volume"]).to_pandas(); k["sym"] = k.sym.astype(str); KC[m] = k
    return KC[m]
plan = []
for _, r in e.iterrows():
    a = (r.T_on - 2 * H) // H * H; b = r.T_on + 6 * H  # hours h with [h,h+1h) overlapping [on-2h, on+6h)
    hours = list(range(a, b, H))
    ms = sorted(set(pd.Timestamp(t, unit="ms").strftime("%Y-%m") for t in (r.T_on - 24 * H, r.T_on)))
    for old in [mm for mm in KC if mm not in ms]:
        del KC[old]
    k = pd.concat([kl(m) for m in ms]); k = k[(k.ts >= r.T_on - 24 * H) & (k.ts < r.T_on)]
    top = k.groupby("sym").quote_volume.sum().sort_values(ascending=False)
    xs = sorted(set(x14[(x14.su >= r.T_on - 2 * H) & (x14.su < r.T_on + 6 * H)].sym))
    for hh in hours:
        for rank, s in enumerate(top.index[:50]):
            plan.append((r.T_on, hh, s, rank + 1, s in xs))
        for s in xs:
            if s not in set(top.index[:50]):
                plan.append((r.T_on, hh, s, int(top.index.get_loc(s)) + 1 if s in top.index else 999, True))
P = pd.DataFrame(plan, columns=["onset", "hour_ms", "symbol", "rank", "x14"]).drop_duplicates(["hour_ms", "symbol"])
print("plan symbol-hours", len(P), "unique hours", P.hour_ms.nunique(), "x14 symbols", P[P.x14].symbol.nunique())
P["date"] = pd.to_datetime(P.hour_ms, unit="ms").dt.strftime("%Y-%m-%d"); P["hour"] = pd.to_datetime(P.hour_ms, unit="ms").dt.hour.astype("int8")
inv = []
for d in sorted(P.date.unique()):
    f = f"/home/ubuntu/claude_master/chd_wk/inv/{d}.parquet"
    v = pd.read_parquet(f); v = v[v.data_type.astype(str).isin(["trades", "orderbook"])]
    v = v.astype({"date": str, "symbol": str, "data_type": str}); inv.append(v[["date", "hour", "symbol", "data_type", "size"]])
inv = pd.concat(inv)
m = P.merge(inv, on=["date", "hour", "symbol"], how="left")
for lab, sel in [("top50+X14", (m["rank"] <= 50) | m.x14), ("top20+X14", (m["rank"] <= 20) | m.x14), ("10-10 21:00 ep top50+X14", (m.hour_ms >= 1760130000000 - 2 * H) & (m.hour_ms < 1760130000000 + 6 * H) & ((m["rank"] <= 50) | m.x14))]:
    s = m[sel]
    g = s.groupby("data_type")["size"].agg(["size", "sum"])
    print(lab, "symbol-hours", s[["hour_ms", "symbol"]].drop_duplicates().shape[0], "files/GB:", {k: (int(v["size"]), round(v["sum"] / 1e9, 2)) for k, v in g.iterrows()}, "missing (sym-hour without trades file):", int(s[s.data_type.isna()].shape[0]))
P.to_parquet("/home/ubuntu/claude_master/chd_wk/d3_plan.parquet")
