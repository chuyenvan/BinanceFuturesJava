import json, glob
import numpy as np, pandas as pd
T = pd.read_csv("/home/ubuntu/claude_master/vz_e1_wt/docs/result/mm_q1/symhour_stats.csv.gz")
T["as0"] = T.v5_as0 / T.v5_n * 1e4
print(T.groupby("sym").as0.describe().round(3).to_string())
w = T.sort_values("as0").head(8)[["sym", "period", "H", "as0", "v5_n"]]
print(w.to_string())
# non-update rows
for f in glob.glob("/home/ubuntu/claude_master/mm_wk/res/*/*.json"):
    r = json.load(open(f))
    if r.get("info") and r["info"].get("n_nonupdate_rows", 0) > 0:
        print("nonupdate", r["sym"], r["period"], r["H"], r["status"], r["info"]["n_nonupdate_rows"], r["info"]["pu_breaks"])
# btc r missing hours
m = set()
for f in glob.glob("/home/ubuntu/claude_master/mm_wk/res/*/K_*.json"):
    r = json.load(open(f))
    if r["status"] == "rej_btc_r_missing":
        m.add(r["H"])
print("btc_r_missing hours", sorted(pd.to_datetime(sorted(m), unit="ms").strftime("%Y-%m-%d %H").tolist()))
nd = []
for f in glob.glob("/home/ubuntu/claude_master/mm_wk/res/*/K_*.json"):
    r = json.load(open(f))
    if r["status"] == "rej_no_data":
        nd.append((r["sym"], pd.to_datetime(r["H"], unit="ms").strftime("%Y-%m-%d %H")))
print("no_data", sorted(nd))
