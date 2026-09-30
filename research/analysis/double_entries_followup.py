#!/usr/bin/env python3
"""DOUBLE_ENTRIES follow-up: cho batch1 (p1..p5) xong -> submit p6 -> cho -> fetch ca 6 (md5)."""
import hashlib
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import double_entries_run as D  # noqa: E402
from tools import kaggle_sim as ks  # noqa: E402


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


print("WAIT batch1", flush=True)
st = ks.wait([ks.kernel_ref(D.tag_of(n)) for n in ["p1", "p2", "p3", "p4", "p5"]])
print("BATCH1", json.dumps(st), flush=True)

print("SUBMIT p6", flush=True)
D.do_submit(["p6"])
print("SUBMITTED p6", flush=True)

print("FETCH all", flush=True)
res = {}
for n in ["p1", "p2", "p3", "p4", "p5", "p6"]:
    out = ks.fetch(D.tag_of(n))
    md5 = md5f(out["print_done"]) if out["print_done"] else None
    res[n] = dict(md5=md5, result=out["result"])
    print("FETCH %s md5=%s %s" % (n, md5, json.dumps(out["result"])), flush=True)
json.dump(res, open("/tmp/de_fetch.json", "w"), indent=1)
print("DONE_FETCH", flush=True)
