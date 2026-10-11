#!/usr/bin/env python3
"""MAPAUD: so cac snapshot mapper (csv 781/863, pickle asdata, Oracle local test ns, 242 live) -> lich su id.
Usage: mapaud_hist.py <mapaud_dir>"""
import hashlib, json, logging, pickle, sys
import pandas as pd
import aerospike
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
D = sys.argv[1]
snaps = {}
for nm, p in [("csv781_0708", "/home/ubuntu/selector_pred_out/symbol_map.csv"),
              ("csv863_0806", "/home/ubuntu/claudedata/symbol_map_20260806.csv"),
              ("csv863_stage", "/home/ubuntu/claude_master/1011/ho4p1/stage/ho4p1-code/symbol_map_863.csv"),
              ("csv781_stage", "/home/ubuntu/claude_master/1011/ho4p1/stage/ho4p1-code/symbol_map_781.csv"),
              ("val_pred_0825", "/home/ubuntu/val_pred/symbol_map.csv")]:
    df = pd.read_csv(p)
    snaps[nm] = {"_rows": len(df), "_sha": hashlib.sha256(open(p, "rb").read()).hexdigest(),
                 "m": {}, "dup_rows": []}
    for s, i in zip(df.symbol, df.symId):
        if s in snaps[nm]["m"]:
            snaps[nm]["dup_rows"].append(s)
        snaps[nm]["m"][s] = int(i)
d = pickle.load(open("/home/ubuntu/claude_master/1003/ho3b/ds_asdata/asdata_local.pkl", "rb"))
snaps["asdata_pkl"] = {"m": {k: int(v) for k, v in d["symbol_mapper"][0][1]["data"].items()}}
try:
    c = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    _, meta, b = c.get(("test", "symbol_mapper", "global_id_map")); c.close()
    snaps["oracle_test_ns"] = {"m": {k: int(v) for k, v in b["data"].items()}, "gen": meta.get("gen")}
except Exception as e:  # noqa
    logging.error("oracle test ns: %s", e)
snaps["live242"] = {"m": json.load(open(f"{D}/mapaud_mapper_242.json"))}
SIXTEEN = ["MUUUSDT", "XBIUSDT", "BNCUSDT", "SOXSUSDT", "FWDIUSDT", "TZAUSDT", "MINIMAXUSDT", "VRTUSDT", "SNOWUSDT",
           "ZHIPUUSDT", "APPUSDT", "SHAZUSDT", "GEVUSDT", "SOFIUSDT", "PANWUSDT", "SKHYUSDT"]
out = {}
live = snaps["live242"]["m"]
for nm, sn in snaps.items():
    m = sn["m"]; inv = {}
    for s, v in m.items():
        inv.setdefault(v, []).append(s)
    ids = set(m.values())
    r = dict(n=len(m), max_id=max(ids), n_ids=len(ids), rows=sn.get("_rows"), sha=sn.get("_sha", "")[:16],
             dup_rows=sn.get("dup_rows"), gen=sn.get("gen"),
             dups={k: sorted(v) for k, v in sorted(inv.items()) if len(v) > 1},
             missing=[i for i in range(1, max(ids) + 1) if i not in ids],
             own_752_759={i: inv.get(i) for i in range(752, 760)},
             sixteen={s: m.get(s) for s in SIXTEEN},
             diff_vs_live=sorted([s for s in m if s in live and live[s] != m[s]])[:40],
             only_here=len([s for s in m if s not in live]))
    out[nm] = r
    logging.info("== %s %s", nm, json.dumps(r))
json.dump(out, open(f"{D}/mapaud_hist.json", "w"), indent=1)
