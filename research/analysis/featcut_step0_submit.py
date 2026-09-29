"""BUOC 0: dua profiles/g2_flat3.properties len Kaggle (dataset nho) + submit sim validate parity FLAT3 650c386f."""
import json
import logging
import os
import shutil
import sys
import time

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks
from kaggle.api.kaggle_api_extended import KaggleApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
LOG = logging.getLogger("step0")
D = "/home/ubuntu/claude_master/0929/ds_prof_g2flat3"
os.makedirs(D, exist_ok=True)
shutil.copy("/home/ubuntu/src/BinanceFuturesJava/profiles/g2_flat3.properties", D + "/prof_g2_flat3.properties")
with open(D + "/dataset-metadata.json", "w") as f:
    json.dump({"title": "sim-prof-g2flat3", "id": "chuyendinh/sim-prof-g2flat3",
               "licenses": [{"name": "CC0-1.0"}]}, f)
api = KaggleApi()
api.authenticate()
try:
    api.dataset_create_new(folder=D, public=False, dir_mode="skip")
    LOG.info("dataset created")
except Exception as e:
    LOG.warning("create failed (%s) -> try version", e)
    api.dataset_create_version(folder=D, version_notes="g2_flat3", dir_mode="skip")
t0 = time.time()
while time.time() - t0 < 600:
    try:
        st = api.dataset_status("chuyendinh/sim-prof-g2flat3")
    except Exception as e:
        st = "ERR %s" % e
    LOG.info("dataset status=%s", st)
    if str(st).lower() == "ready":
        break
    time.sleep(15)
LOG.info("free_slots=%s", ks.free_slots())
ref = ks.submit("g2flat3-val", "g2_flat3", {}, jar_ds="sim-jar-gdv2", bundle_ds="sim-x1-2021-bundle",
                extra_ds=["sim-prof-g2flat3"], sim_end_date="20251231", code_sha="prereg76d9ba06")
LOG.info("SUBMITTED %s", ref)
