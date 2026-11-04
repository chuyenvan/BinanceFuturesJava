#!/usr/bin/env python3
"""Regression test (PARITY_V11_WINDOW D2, buoc 2): JSON cua code tham so hoa chay lai D1 (PV_WORK=regr_d1/work) phai
BIT-IDENTICAL (sau json.load) voi artefact da commit cua D1 ADDENDUM1 (a7e2764f, docs/result/parity_v11_d1/add1/), va
file trung gian (giai nen) trung voi ~/claude_master/parity_v11w/work (lan chay ADDENDUM1). Ghi regress_d1.json."""
import gzip
import hashlib
import json
import os
import sys

REPO = os.path.expanduser("~/claude_master/vz_e1_wt")
ADD1 = REPO + "/docs/result/parity_v11_d1/add1"
OLDW = os.path.expanduser("~/claude_master/parity_v11w/work")
NEWW = os.path.expanduser("~/claude_master/parity_v11w/regr_d1/work")


def diff(a, b, path=""):
    if type(a) != type(b):
        return [path + ": type %s vs %s" % (type(a).__name__, type(b).__name__)]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(path + "/" + k + ": chi co o " + ("cu" if k in a else "moi"))
            else:
                out += diff(a[k], b[k], path + "/" + k)
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [path + ": len %d vs %d" % (len(a), len(b))]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, path + "[%d]" % i)
        return out
    return [] if a == b or (a != a and b != b) else [path + ": %r vs %r" % (a, b)]


def md5u(p):
    h = hashlib.md5()
    with (gzip.open(p, "rb") if p.endswith(".gz") else open(p, "rb")) as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


res = {"json": {}, "intermediate": {}}
for n in ("gate", "fund", "net", "s1", "gv_p2", "p3", "labels"):
    a = json.load(open("%s/%s_d1.json" % (ADD1, n)))
    b = json.load(open("%s/%s_d1.json" % (NEWW, n)))
    d = diff(a, b)
    res["json"][n] = {"identical": not d, "n_diff": len(d), "first": d[:5]}
a = json.load(open(OLDW + "/s1v_d1.json"))
b = json.load(open(NEWW + "/s1v_d1.json"))
d = diff(a, b)
res["json"]["s1v (vs work/s1v_d1.json cua D1)"] = {"identical": not d, "n_diff": len(d), "first": d[:5]}
for f in ("join_gate.csv.gz", "join_fund.csv.gz", "net_pw.csv.gz", "net_live_all.csv.gz", "p2_pairs.csv.gz",
          "s1v_rows.csv.gz", "p3_q.csv"):
    x, y = OLDW + "/" + f, NEWW + "/" + f
    res["intermediate"][f] = {"identical": os.path.exists(x) and os.path.exists(y) and md5u(x) == md5u(y)}
tsx = os.path.join(NEWW, "log_tsx.txt")
if os.path.exists(tsx):
    t = open(tsx).read().strip().splitlines()
    try:
        j = json.loads(t[-1])
        res["tsx_ew_engine"] = {"days64_identical": j["days64_identical"], "days32_identical": j["days32_identical"]}
    except Exception as e:  # noqa: BLE001
        res["tsx_ew_engine"] = {"error": str(e)}
res["ALL_JSON_IDENTICAL"] = all(v["identical"] for v in res["json"].values())
res["ALL_INTERMEDIATE_IDENTICAL"] = all(v["identical"] for v in res["intermediate"].values())
json.dump(res, open(NEWW + "/regress_d1.json", "w"), indent=1)
print(json.dumps(res, indent=1))
sys.exit(0 if res["ALL_JSON_IDENTICAL"] else 1)
