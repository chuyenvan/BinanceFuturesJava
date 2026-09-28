#!/usr/bin/env python3
"""Tai lai output kernel ofi-v3-ms-s{42..45} (chi 3 pred) + dataset ofi-money-ext-trades vao thu muc tam."""
import os, sys, glob, shutil
from kaggle.api.kaggle_api_extended import KaggleApi
W = "/home/ubuntu/claude_audit_0928/ofirx"
api = KaggleApi(); api.authenticate()
KEEP = {"pred_ofi_candidate_v2.parquet", "pred_baseline_fresh.parquet", "pred_ofi_noise_v2.parquet"}
for s in [int(x) for x in sys.argv[1].split(",")]:
    d = os.path.join(W, "kout%d" % s)
    if all(os.path.exists(os.path.join(d, k)) for k in KEEP):
        print("have", d); continue
    tmp = os.path.join(W, "dltmp%d" % s); os.makedirs(tmp, exist_ok=True)
    api.kernels_output("chuyendinh/ofi-v3-ms-s%d" % s, path=tmp)
    os.makedirs(d, exist_ok=True)
    for p in glob.glob(os.path.join(tmp, "**", "*"), recursive=True):
        b = os.path.basename(p)
        if b in KEEP or b.endswith(".json"):
            shutil.move(p, os.path.join(d, b))
    shutil.rmtree(tmp)
    print("OK", d, sorted(os.listdir(d)), flush=True)
if len(sys.argv) > 2:
    d = os.path.join(W, "exttrades_old"); os.makedirs(d, exist_ok=True)
    api.dataset_download_files("chuyendinh/ofi-money-ext-trades", path=d, unzip=True)
    print("DS", os.listdir(d))
