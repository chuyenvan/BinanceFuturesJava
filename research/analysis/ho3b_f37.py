#!/usr/bin/env python3
"""HO3b ADDENDUM-4 §2: dem lenh H1 (start >= 2026-01-01 +07) cua 37 symbol khong co funding Vision trong 48 run ho26.
Chi dem so lenh theo symbol/run; KHONG in PnL."""
import glob, json, logging, os, sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("f37")
F = json.load(open("/home/ubuntu/src/BinanceFuturesJava/docs/result/ho3/f_h1.json"))
S37 = set(F["sym_vision_vs_local_not_100"])
res = {"symbols": sorted(S37), "runs": {}, "by_symbol": {}}
cols_seen = None
for p in sorted(glob.glob("/home/ubuntu/kaggle_sim/out/ho26-*/storage/printDone.csv")):
    tag = p.split("/")[-3]
    d = pd.read_csv(p, index_col=False, dtype=str)
    cols_seen = list(d.columns)
    sc = [c for c in d.columns if c.strip().lower() in ("symbol", "sym")][0]
    st = d["start"].astype(str).str.strip()
    h1 = d[st >= "20260101"]
    sym = h1[sc].astype(str).str.strip()
    m = sym.isin(S37) | sym.str.replace("USDT", "").isin({s.replace("USDT", "") for s in S37})
    res["runs"][tag] = dict(n_h1=int(len(h1)), n_37=int(m.sum()))
    for s, c in sym[m].value_counts().items():
        res["by_symbol"][s] = res["by_symbol"].get(s, 0) + int(c)
res["total_37"] = sum(v["n_37"] for v in res["runs"].values())
res["columns"] = cols_seen
json.dump(res, open(sys.argv[1], "w"), indent=1)
log.info("total_37=%d by_symbol=%s", res["total_37"], res["by_symbol"])
