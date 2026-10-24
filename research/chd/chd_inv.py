"""Full S3 inventory of binance_futures objects per (date,hour). Resumable: one parquet per date."""
import sys, os, time, datetime as dt
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
OUT = "/home/ubuntu/claude_master/chd_wk/inv"
LOG = "/home/ubuntu/claude_master/chd_wk/progress.log"
os.makedirs(OUT, exist_ok=True)
d0 = dt.date.fromisoformat(sys.argv[1]); d1 = dt.date.fromisoformat(sys.argv[2])
def log(m):
    with open(LOG, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S") + " inv " + m + "\n")
def one(args):
    d, h = args
    for a in range(6):
        try:
            return L.list_hour(d, h)
        except Exception as e:
            time.sleep(2 ** a)
            err = e
    raise err
log(f"start {d0}..{d1}")
d = d0
with ThreadPoolExecutor(8) as ex:
    while d <= d1:
        ds = d.isoformat(); fn = f"{OUT}/{ds}.parquet"
        if not os.path.exists(fn):
            t = time.time()
            res = list(ex.map(one, [(ds, h) for h in range(24)]))
            rows = []
            for h, objs in enumerate(res):
                for o in objs:
                    rows.append((ds, h, o.get("symbol"), o.get("data_type") or ("kline" if o["key"].endswith(("_kline.parquet.zst", "_kline.parquet")) else "UNPARSED"), o.get("extension"), o["size"], o["key"] if o.get("data_type") is None else None))
            df = pd.DataFrame(rows, columns=["date", "hour", "symbol", "data_type", "ext", "size", "rawkey"])
            df["hour"] = df["hour"].astype("int8"); df["size"] = df["size"].astype("int64")
            for c in ["date", "symbol", "data_type", "ext"]:
                df[c] = df[c].astype("category")
            df.to_parquet(fn + ".tmp", index=False); os.replace(fn + ".tmp", fn)
            log(f"{ds} n={len(df)} hours={df.hour.nunique() if len(df) else 0} t={time.time()-t:.1f}s")
        d += dt.timedelta(days=1)
log("done")
