import sys, json, glob
import numpy as np, pandas as pd, pyarrow as pa, pyarrow.parquet as pq
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/mm_q1")
import mm_core as C
T = pd.read_csv("/home/ubuntu/claude_master/vz_e1_wt/docs/result/mm_q1/symhour_stats.csv.gz", usecols=["sym", "period", "H", "r_sym"])
T = T[T.period == "D"]
rows = []
for m, sub in T.groupby(pd.to_datetime(T.H, unit="ms").dt.strftime("%Y-%m")):
    k = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet", columns=["ts", "sym", "open", "close"], filters=[("sym", "in", sorted(sub.sym.unique()))]).to_pandas()
    k["sym"] = k.sym.astype(str); k = k.set_index(["sym", "ts"])
    for _, r in sub.iterrows():
        o = k.loc[(r.sym, r.H), "open"]; c = k.loc[(r.sym, r.H + 59 * 60000), "close"]
        rows.append((r.sym, r.H, r.r_sym, o, c, abs(c / o - 1 - r.r_sym)))
X = pd.DataFrame(rows, columns=["sym", "H", "r", "o", "c", "d"])
bad = X[X.d > 1e-9]
print("bad", len(bad), "by sym", bad.sym.value_counts().to_dict())
for _, r in bad.head(4).iterrows():
    fr = []
    for hh in (r.H - 3600000, r.H, r.H + 3600000):
        tb, _ = C.fetch(r.sym, int(hh), "trades", ["trade_id", "price", "quantity", "trade_time"])
        if tb is not None:
            d = tb.to_pandas(); d["src"] = hh; fr.append(d)
    d = pd.concat(fr); d["p"] = d.price.astype(float); d["q"] = d.quantity.astype(float)
    d = d[(d.p > 0) & (d.q > 0) & (d.trade_time >= r.H) & (d.trade_time < r.H + 3600000)]
    own = d[d.src == r.H].drop_duplicates("trade_id").sort_values(["trade_time", "trade_id"])
    uni = d.drop_duplicates("trade_id").sort_values(["trade_time", "trade_id"])
    tid = np.sort(uni.trade_id.to_numpy())
    print(r.sym, int(r.H), f"oracle o={r.o} c={r.c} | own first={own.p.iloc[0]} last={own.p.iloc[-1]} n={len(own)} | union first={uni.p.iloc[0]} last={uni.p.iloc[-1]} n={len(uni)} id_gaps={int((np.diff(tid)-1).clip(min=0).sum())} rows_from_other_files={int((d.src != r.H).sum())}")
