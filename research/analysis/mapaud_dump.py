#!/usr/bin/env python3
"""MAPAUD: doc symbol_mapper (CHI DOC) tu Aerospike 242 + Oracle local, luu snapshot JSON, dem id trung.
Usage: mapaud_dump.py <out_dir>"""
import hashlib, json, logging, os, sys
import aerospike
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
SRC = {"242": ("103.157.218.242", 3222), "oracle_local": ("127.0.0.1", 3222)}
KEY = ("ticker", "symbol_mapper", "global_id_map")


def canon_sha(m):
    s = "\n".join(f"{k},{int(v)}" for k, v in sorted(m.items()))
    return hashlib.sha256(s.encode()).hexdigest()


def dups(m):
    inv = {}
    for s, v in m.items():
        inv.setdefault(int(v), []).append(s)
    return {k: sorted(v) for k, v in sorted(inv.items()) if len(v) > 1}


res = {}
for name, (h, p) in SRC.items():
    try:
        c = aerospike.client({"hosts": [(h, p)], "policies": {"read": {"total_timeout": 20000}}}).connect()
        _, meta, bins = c.get(KEY)
        c.close()
        binname = list(bins.keys())
        m = {k: int(v) for k, v in bins[binname[0]].items()}
        ids = sorted(set(m.values()))
        missing = [i for i in range(1, max(ids) + 1) if i not in set(ids)]
        r = dict(bins=binname, n=len(m), n_ids=len(ids), max_id=max(ids), min_id=min(ids), gen=meta.get("gen"),
                 sha256_canon=canon_sha(m), dups=dups(m), missing_ids=missing)
        json.dump(m, open(f"{OUT}/mapaud_mapper_{name}.json", "w"), sort_keys=True)
        res[name] = r
        logging.info("%s %s", name, json.dumps(r))
    except Exception as e:  # noqa
        logging.error("%s loi %s", name, e)
        res[name] = {"error": str(e)}
json.dump(res, open(f"{OUT}/mapaud_dump_summary.json", "w"), indent=1)
