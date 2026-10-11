#!/usr/bin/env python3
"""HO4-P1: so set symbol_mapper (ban sao asdata dung trong kernel) voi symbol_map.csv 863 (id cua net015/bins)."""
import json, logging, pickle, sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
d = pickle.load(open("/home/ubuntu/claude_master/1003/ho3b/ds_asdata/asdata_local.pkl", "rb"))
m = d["symbol_mapper"][0][1]["data"]
mp = pd.read_csv("/home/ubuntu/claude_master/1011/ho4p1/stage/ho4p1-code/symbol_map_863.csv")
csv = dict(zip(mp.symbol, mp.symId))
only_csv = sorted(s for s in csv if s not in m)
only_set = sorted(s for s in m if s not in csv)
diff = sorted(s for s in csv if s in m and int(m[s]) != int(csv[s]))
logging.info("set n=%d max=%d | csv n=%d max=%d", len(m), max(int(v) for v in m.values()), len(csv), max(csv.values()))
logging.info("chi csv %d: %s", len(only_csv), [(s, csv[s]) for s in only_csv])
logging.info("chi set %d: %s", len(only_set), only_set[:20])
logging.info("id khac %d: %s", len(diff), diff[:20])
dup = {}
for s, v in m.items():
    dup.setdefault(int(v), []).append(s)
logging.info("id trung trong set: %s", {k: v for k, v in dup.items() if len(v) > 1})
