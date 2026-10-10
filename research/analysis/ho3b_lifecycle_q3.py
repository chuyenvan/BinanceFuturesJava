#!/usr/bin/env python3
"""HO3b (§4c): symbol_lifecycle cap nhat toi kline 2026-10-03 theo DUNG luat SymbolLifecycleBuilderLocal:
first/last = phut som/muon nhat symbol co mat trong kline (lich su = ban sao local, them Q3 tu seen_*.json cua ticker 242);
LIVE neu (maxTicker - last) <= 3 ngay, nguoc lai DEAD + delist = last. Ghi pickle {"symbol_lifecycle": [(sym, bins)]}.
Usage: ho3b_lifecycle_q3.py <out.pkl> <seen_dir>..."""
import glob, json, pickle, sys
d = pickle.load(open("/home/ubuntu/claude_master/1003/ho3b/ds_asdata/asdata_local.pkl", "rb"))
lc = {k: dict(b) for k, b in d["symbol_lifecycle"]}
q = {}
mx = 0
for sd in sys.argv[2:]:
    for f in sorted(glob.glob(sd + "/seen_*.json")):
        for s, (a, b) in json.load(open(f)).items():
            v = q.get(s)
            q[s] = [a, b] if v is None else [min(v[0], a), max(v[1], b)]
            mx = max(mx, b)
fresh = 3 * 86400000
rows, st = [], dict(existing=len(lc), q3_syms=len(q), new_syms=0, live=0, dead=0)
for s in sorted(set(lc) | set(q)):
    e = lc.get(s)
    first = e["first"] if e else q[s][0]
    last = max(e["last"] if e else 0, q[s][1] if s in q else 0)
    if e is None:
        st["new_syms"] += 1
    if mx - last <= fresh:
        status, delist = "LIVE", 0; st["live"] += 1
    else:
        status, delist = "DEAD", last; st["dead"] += 1
    rows.append((s, {"sym": s, "first": int(first), "last": int(last), "status": status, "delist": int(delist)}))
st["max_ticker_ts"] = mx
pickle.dump({"symbol_lifecycle": rows}, open(sys.argv[1], "wb"), protocol=4)
json.dump(st, open(sys.argv[1] + ".json", "w"), indent=1)
print(json.dumps(st))
