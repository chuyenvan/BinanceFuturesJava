#!/usr/bin/env python3
"""exec_finalize.py -- EXEC: gop kiem dinh phu (bookTicker, dieu tra V1, tom tat tai) vao exec_result.json; ghi manifest md5
cache tu tao (agg/kl npz, pkl) TRUOC khi xoa. Usage: exec_finalize.py merge | manifest"""
import glob
import hashlib
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("exec_fin")
W = "/home/ubuntu/claude_master/1012/exec"
J = "/home/ubuntu/src/BinanceFuturesJava/docs/result/exec_result.json"


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


if sys.argv[1] == "merge":
    j = json.load(open(J))
    for k, f in (("bookticker", "bt_cmp.json"), ("V1_diag", "v1diag.json"), ("V1_diag2", "v1diag2.json"),
                 ("fetch_agg", "fetch_agg_summary.json"), ("fetch_kl", "fetch_kl_summary.json")):
        j[k] = json.load(open(os.path.join(W, f)))
    json.dump(j, open(J, "w"), indent=1)
    log.info("merge xong")
else:
    fs = sorted(glob.glob(W + "/agg/*.npz") + glob.glob(W + "/kl/*.npz") + glob.glob(W + "/*.pkl"))
    with open(W + "/cache_manifest.md5", "w") as f:
        for p in fs:
            f.write("%s  %s %d\n" % (md5f(p), os.path.relpath(p, W), os.path.getsize(p)))
    log.info("manifest %d file, md5 manifest %s, md5 sim.pkl %s, legs.pkl %s", len(fs), md5f(W + "/cache_manifest.md5"),
             md5f(W + "/sim.pkl"), md5f(W + "/legs.pkl"))
