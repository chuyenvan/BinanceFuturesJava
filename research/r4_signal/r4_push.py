#!/usr/bin/env python3
"""R4_SIGNAL_SCREEN: tao dataset r4s-cells + push kernel r4s-fwd (enable_internet=false, khong jar) | status | fetch.
Usage: r4_push.py push | status | fetch. Chi push khi account < 2 kernel dang chay."""
import json
import logging
import os
import shutil
import sys
import time

sys.path.insert(0, "/home/ubuntu/claude_master/ho_tradfi_wk")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r4push")
G = "/home/ubuntu/claude_master/res1109/r4_signal/screen"
CODE = "/home/ubuntu/claude_master/vz_e1_wt/research/r4_signal/r4s_k.py"
USER = "chuyendinh"
KREF = USER + "/r4s-fwd"
DREF = USER + "/r4s-cells"


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
    d = G + "/ds_cells"
    if not os.path.exists(G + "/cells_created"):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        shutil.copyfile(G + "/r4s_cells.parquet", d + "/r4s_cells.parquet")
        json.dump({"title": "r4s-cells", "id": DREF, "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
        a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
        open(G + "/cells_created", "w").write(time.strftime("%F %T"))
        for _ in range(60):
            st = str(a.dataset_status(DREF)).lower()
            log.info("dataset status %s", st)
            if "ready" in st:
                break
            time.sleep(30)
    k = G + "/kernel"
    os.makedirs(k, exist_ok=True)
    shutil.copyfile(CODE, k + "/run.py")
    md = {"id": KREF, "title": "r4s-fwd", "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False,
          "dataset_sources": [DREF] + [USER + "/vz-kline1m-%d" % y for y in (2021, 2022, 2023, 2024, 2025, 2026)],
          "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(k + "/kernel-metadata.json", "w"), indent=1)
    r = a.kernels_push(k)
    log.info("PUSHED %s", getattr(r, "url", r))
    open(G + "/pushed", "w").write(time.strftime("%F %T"))


def status():
    s = api().kernels_status(KREF)
    st = str(getattr(s, "status", s))
    log.info("STATUS %s", st)
    return st


def fetch():
    o = G + "/out"
    os.makedirs(o, exist_ok=True)
    api().kernels_output(KREF, o)
    log.info("FETCHED %s", os.listdir(o))


if __name__ == "__main__":
    {"push": push, "status": status, "fetch": fetch}[sys.argv[1]]()
