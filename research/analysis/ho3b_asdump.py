#!/usr/bin/env python3
"""HO3b: dump (CHI DOC) Aerospike LOCAL Oracle ns test cac set nho can cho exporter Java trong kernel Kaggle:
funding_data (f_data/f_map), symbol_mapper, symbol_lifecycle -> pickle {set: [(userkey, bins)]}. Khong ghi gi vao Aerospike.
Usage: ho3b_asdump.py <out.pkl>"""
import hashlib, json, pickle, sys
import aerospike
c = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 20000}}).connect()
out = {}
for st in ("funding_data", "symbol_mapper", "symbol_lifecycle"):
    rows = []

    def cb(rec):
        k, meta, bins = rec
        rows.append((k[2], dict(bins)))
    q = c.scan("test", st)
    q.foreach(cb, {"timeout": 0})
    out[st] = rows
    print(st, len(rows), "rows; userkey None:", sum(1 for r in rows if r[0] is None))
c.close()
pickle.dump(out, open(sys.argv[1], "wb"), protocol=4)
print("md5", hashlib.md5(open(sys.argv[1], "rb").read()).hexdigest())
