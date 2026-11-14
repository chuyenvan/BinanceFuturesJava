"""IND_COMBO P0: push kernel ind-ho26 (enable_internet=false) | status | fetch. Chi push khi < 2 kernel dang chay."""
import json
import logging
import os
import shutil
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("ho26push")
G = "/home/ubuntu/claude_master/ind1114"
USER = "chuyendinh"
KREF = USER + "/ind-ho26"


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi()
    a.authenticate()
    return a


def running(a):
    ks = a.kernels_list(mine=True, page_size=40)
    busy = []
    for k in ks:
        try:
            st = str(a.kernels_status(k.ref).get("status")).lower()
        except Exception as e:  # noqa
            st = "err"
        if "running" in st or "queued" in st:
            busy.append(k.ref)
    return busy


if __name__ == "__main__":
    c = sys.argv[1]
    a = api()
    if c == "push":
        busy = running(a)
        log.info("dang chay %s", busy)
        if len(busy) >= 2:
            sys.exit(2)
        k = G + "/kernel"
        os.makedirs(k, exist_ok=True)
        shutil.copyfile(G + "/ho26k.py", k + "/run.py")
        md = {"id": KREF, "title": "ind-ho26", "code_file": "run.py", "language": "python", "kernel_type": "script",
              "is_private": True, "enable_gpu": False, "enable_internet": False,
              "dataset_sources": [USER + "/vz-kline1m-2026"], "competition_sources": [], "kernel_sources": []}
        json.dump(md, open(k + "/kernel-metadata.json", "w"), indent=1)
        r = a.kernels_push(k)
        log.info("PUSHED %s", getattr(r, "url", r))
    elif c == "status":
        log.info("STATUS %s", a.kernels_status(KREF))
    elif c == "fetch":
        os.makedirs(G + "/ho26out", exist_ok=True)
        a.kernels_output(KREF, G + "/ho26out")
        log.info("fetched %s", os.listdir(G + "/ho26out"))
