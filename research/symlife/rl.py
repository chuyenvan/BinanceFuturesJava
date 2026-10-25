"""SYMLIFE step2: tu ~/vz_e1/raw/kline1m-YYYY-MM.parquet (2021-12..2025-12) -> bang (sym, day) n_bars, n_active, first_ts, last_ts.
Doc lap. ts int64 ms. Output ~/claude_master/symlife_wk/raw_daycov.parquet"""
import os, glob, numpy as np, pandas as pd, pyarrow.parquet as pq
WK = os.path.expanduser("~/claude_master/symlife_wk")
fs = sorted(glob.glob(os.path.expanduser("~/vz_e1/raw/kline1m-20*.parquet")))
out = []
for f in fs:
    t = pq.read_table(f, columns=["ts", "sym", "active", "n_trades"])
    ts = t.column("ts").to_numpy()
    assert t.schema.field("ts").type == "int64"
    sym = t.column("sym").to_pandas().astype(str).to_numpy() if False else t.column("sym").combine_chunks().dictionary_decode().to_numpy(zero_copy_only=False)
    df = pd.DataFrame({"sym": pd.Categorical(sym), "ts": ts, "active": t.column("active").to_numpy(zero_copy_only=False),
                       "ntr": t.column("n_trades").to_numpy()})
    assert (df.ts % 60000 == 0).all()
    df["day"] = df.ts // 86400000
    g = df.groupby(["sym", "day"], observed=True).agg(n_bars=("ts", "size"), n_active=("active", "sum"),
                                                      n_trade_pos=("ntr", lambda x: int((x > 0).sum())),
                                                      first_ts=("ts", "min"), last_ts=("ts", "max")).reset_index()
    dup = df.duplicated(["sym", "ts"]).sum()
    print(os.path.basename(f), len(df), df.sym.nunique(), "dup", dup, flush=True)
    g["sym"] = g["sym"].astype(str)
    out.append(g)
    del df, t
R = pd.concat(out, ignore_index=True)
R["day"] = R["day"].astype("int64")
R.to_parquet(WK + "/raw_daycov.parquet", index=False)
print("DONE", len(R), R.sym.nunique())
