"""SHORTVOL_T0: fetch Deribit public DVOL (BTC, ETH) via curl. 1D and 3600 resolution.
Raw JSON pages saved to WK/dvol/raw/, merged CSV to WK/dvol/dvol_{CUR}_{RES}.csv (ts int64 ms, open, high, low, close).
Deribit data: personal-use only (Membership Terms cl. 2.10) => NOT committed to repo; only sha256 recorded.
"""
import json, os, subprocess, time, hashlib
import pandas as pd
WK = os.path.expanduser("~/claude_master/shortvol_t0_wk/dvol")
os.makedirs(os.path.join(WK, "raw"), exist_ok=True)
URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={c}&start_timestamp={s}&end_timestamp={e}&resolution={r}"
S = 1638316800000  # 2021-12-01 00:00 UTC
E = {"1D": 1767052800000, "3600": 1767139200000}  # 1D: last candle ts 2025-12-30 ; 3600: up to 2025-12-31 00:00
for cur in ["BTC", "ETH"]:
    for res in ["1D", "3600"]:
        end = E[res]; rows = []; page = 0
        while True:
            u = URL.format(c=cur, s=S, e=end, r=res)
            out = subprocess.run(["curl", "-sS", "--max-time", "30", u], capture_output=True, text=True, check=True).stdout
            fn = os.path.join(WK, "raw", "%s_%s_p%03d.json" % (cur, res, page))
            open(fn, "w").write(out)
            j = json.loads(out)["result"]
            rows += j["data"]
            cont = j.get("continuation")
            print(cur, res, "page", page, "n", len(j["data"]), "min", min(r[0] for r in j["data"]) if j["data"] else None, "cont", cont, flush=True)
            page += 1
            if cont is None or not j["data"]:
                break
            end = int(cont); time.sleep(0.3)
        d = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close"])
        d["ts"] = d["ts"].astype("int64")
        nd = int(d.duplicated("ts").sum())
        # duplicates across pages: must be identical rows
        assert d.drop_duplicates().duplicated("ts").sum() == 0, "conflicting duplicate ts"
        d = d.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
        d = d[(d.ts >= S) & (d.ts <= E[res])]
        p = os.path.join(WK, "dvol_%s_%s.csv" % (cur, res))
        d.to_csv(p, index=False)
        print(cur, res, "rows", len(d), "dup_removed", nd, "first", pd.to_datetime(d.ts.iloc[0], unit="ms"), "last", pd.to_datetime(d.ts.iloc[-1], unit="ms"),
              "sha256", hashlib.sha256(open(p, "rb").read()).hexdigest(), flush=True)
