#!/usr/bin/env python3
"""R5_SIGNAL_QUALITY: dataset r5q-basket + kernel r5q-fwd (enable_internet=false) | status | fetch."""
import json
import logging
import os
import shutil
import sys
import time

sys.path.insert(0, "/home/ubuntu/claude_master/ho_tradfi_wk")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r5push")
G = "/home/ubuntu/claude_master/res1109/r5_quality"
CODE = "/home/ubuntu/claude_master/vz_e1_wt/research/r5_quality/r5k.py"
USER = "chuyendinh"
KREF, DREF = USER + "/r5q-fwd", USER + "/r5q-basket"


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi()
    a.authenticate()
    return a


def push():
    import notf_orch as N
    busy = N.running()
    if len(busy) >= 2:
        log.error("dang chay %s -> khong push", busy)
        sys.exit(2)
    a = api()
    d = G + "/ds_basket"
    if not os.path.exists(G + "/ds_created"):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        for f in ("r5q_basket.parquet", "r5q_symmap.csv"):
            shutil.copyfile(G + "/" + f, d + "/" + f)
        json.dump({"title": "r5q-basket", "id": DREF, "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
        a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
        open(G + "/ds_created", "w").write(time.strftime("%F %T"))
        log.info("dataset tao xong -> doi 5' cho xu ly")
        time.sleep(300)
    k = G + "/kernel"
    os.makedirs(k, exist_ok=True)
    shutil.copyfile(CODE, k + "/run.py")
    md = {"id": KREF, "title": "r5q-fwd", "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False,
          "dataset_sources": [DREF] + [USER + "/vz-kline1m-%d" % y for y in (2022, 2023, 2024, 2025, 2026)],
          "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(k + "/kernel-metadata.json", "w"), indent=1)
    r = a.kernels_push(k)
    log.info("PUSHED %s", getattr(r, "url", r))
    open(G + "/pushed", "w").write(time.strftime("%F %T"))


def status():
    s = api().kernels_status(KREF)
    st = str(getattr(s, "status", s))
    log.info("STATUS %s", st)


def fetch():
    o = G + "/out"
    os.makedirs(o, exist_ok=True)
    api().kernels_output(KREF, o)
    log.info("FETCHED %s", os.listdir(o))


if __name__ == "__main__":
    {"push": push, "status": status, "fetch": fetch}[sys.argv[1]]()
