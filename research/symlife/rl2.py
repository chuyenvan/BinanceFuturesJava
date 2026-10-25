"""SYMLIFE: raw kline -> per sym: first/last ts CO GIAO DICH (n_trades>0), chinh xac phut. Doc lap."""
import os, glob, pandas as pd, pyarrow.parquet as pq, pyarrow.compute as pc
WK = os.path.expanduser("~/claude_master/symlife_wk")
out = []
for f in sorted(glob.glob(os.path.expanduser("~/vz_e1/raw/kline1m-20*.parquet"))):
    t = pq.read_table(f, columns=["ts", "sym", "n_trades"])
    t = t.filter(pc.greater(t["n_trades"], 0))
    df = pd.DataFrame({"sym": t.column("sym").combine_chunks().dictionary_decode().to_numpy(zero_copy_only=False), "ts": t.column("ts").to_numpy()})
    out.append(df.groupby("sym").ts.agg(["min", "max", "size"]).reset_index())
R = pd.concat(out)
R["sym"] = R.sym.where(R.sym.str.endswith("USDT"), R.sym + "USDT")
G = R.groupby("sym").agg(raw_ft=("min", "min"), raw_lt=("max", "max"), raw_ntr=("size", "sum")).reset_index()
G.to_parquet(WK + "/raw_trade_ts.parquet", index=False)
print("DONE", len(G))
