#!/usr/bin/env python3
"""TSX HO addendum 1: duong song song tren Oracle - tai parquet tu Kaggle vz-kline1m-{2025,2026}, chay DUNG
read_month/logret/build_index cua edge_attr_build.py (trich ast) -> ew_out_local/ew_2026.npz. Xoa parquet sau moi thang."""
import ast, glob, hashlib, json, logging, os, sys, zipfile  # noqa: E401

import numpy as np
import pandas as pd  # noqa: F401
import pyarrow.parquet as pq  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ewloc")
W = "/home/ubuntu/claude_master/tsx/ho"
KL = W + "/kl"
OUTD = W + "/ew_out_local"
os.makedirs(KL, exist_ok=True)
os.makedirs(OUTD, exist_ok=True)
MIN = 60000
src = open("/home/ubuntu/claude_master/edge_attr/edge_attr_build.py").read()
tree = ast.parse(src)
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name in ("read_month", "logret", "build_index"):
        exec(compile(ast.get_source_segment(src, n), "eab", "exec"), globals())

from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402
A = KaggleApi()
A.authenticate()


def kp(ym):
    p = KL + "/kline1m-%s.parquet" % ym
    if not os.path.exists(p):
        ds = "chuyendinh/vz-kline1m-%s" % ym[:4]
        A.dataset_download_file(ds, "kline1m-%s.parquet" % ym, path=KL, quiet=True)
        for z in glob.glob(KL + "/*.zip"):
            with zipfile.ZipFile(z) as f:
                f.extractall(KL)
            os.remove(z)
    log.info("kp %s exists=%s size=%s", ym, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else None)
    return p if os.path.exists(p) else None


ML = ["2025-10", "2025-11", "2025-12"] + ["2026-%02d" % m for m in range(1, 10)]
parts = []
for ym in ML:
    r = build_index([ym])  # noqa: F821
    parts.append(r)
    for p in glob.glob(KL + "/kline1m-%s.parquet" % ym):
        os.remove(p)
ew_ts = np.concatenate([p[0] for p in parts])
ew_r = np.concatenate([p[1] for p in parts])
bt_ts = np.concatenate([p[2] for p in parts])
bt_r = np.concatenate([p[3] for p in parts])
miss = sum((p[4] for p in parts), [])
np.savez_compressed(OUTD + "/ew_2026.npz", ew_ts=ew_ts, ew_r=ew_r, bt_ts=bt_ts, bt_r=bt_r)
h = hashlib.md5(open(OUTD + "/ew_2026.npz", "rb").read()).hexdigest()
json.dump({"months": ML, "miss": miss, "n_ew": int(len(ew_ts)), "md5": h}, open(OUTD + "/ew_2026.json", "w"))
log.info("EW_LOCAL_DONE miss=%s n=%d md5=%s", miss, len(ew_ts), h)
