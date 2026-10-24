import sys, io, time, glob, os
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import pandas as pd, pyarrow.parquet as pq
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
# alt X14: most legs in 2025-07..12 over seeds
fr = []
for f in glob.glob("/home/ubuntu/kaggle_sim/out/tsx-x14-s*/storage/printDone.csv"):
    d = pd.read_csv(f, index_col=False); d.columns = [c.strip() for c in d.columns]
    d["sym"] = d["sym"].astype(str).str.strip(); d["sym"] = d["sym"].where(d["sym"].str.endswith("USDT"), d["sym"] + "USDT")
    d["su"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
    fr.append(d[["sym", "su"]])
d = pd.concat(fr)
d = d[(d.su >= "2025-07-01") & (d.su < "2026-01-01")]
vc = d.sym.value_counts()
print("x14 2025H2 legs top:", vc.head(8).to_dict())
os.makedirs("sample", exist_ok=True)
objs = L.list_hour("2025-09-02", 12)
print("unparsed keys sample:", [o["key"] for o in objs if o["data_type"] is None][:4])
mode = sys.argv[1] if len(sys.argv) > 1 else "schema"
syms = ["BTCUSDT", "SOLUSDT"] + [s for s in vc.index if s not in ("BTCUSDT", "SOLUSDT")][:1]
print("syms", syms)
types = ["liquidations", "open_interest", "mark_price", "trades", "aggtrades", "ticker", "orderbook"]
for date, h in [("2025-09-02", 12), ("2025-10-10", 21)]:
    objs = {(o["symbol"], o["data_type"]): o for o in L.list_hour(date, h)}
    for s in syms:
        for t in types:
            o = objs.get((s, t))
            if o is None:
                print(date, h, s, t, "MISSING"); continue
            t0 = time.time(); b, wire = L.get_bytes(o["key"]); dt = time.time() - t0
            fn = f"sample/{date}_{h:02d}_{s}_{t}.parquet"
            open(fn, "wb").write(b)
            pf = pq.ParquetFile(io.BytesIO(b))
            df = pf.read().to_pandas()
            print(f"== {date} {h} {s} {t} rows={len(df)} wire={wire/1e6:.3f}MB raw={len(b)/1e6:.3f}MB t={dt:.1f}s codec={pf.metadata.row_group(0).column(0).compression if pf.metadata.num_row_groups else None}")
            if s == "BTCUSDT" and date == "2025-09-02":
                print(pf.schema_arrow)
                print(df.head(4).to_string())
