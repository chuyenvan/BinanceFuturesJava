#!/usr/bin/env python3
"""VOLTARGET_G2: chay B0 (OFF, guard kernel da va) + VT_COIN tren Kaggle, jar sim-jar-gdv2 (KHONG build).
Pre-reg docs/prereg/PREREG_VOLTARGET_G2.md (+AMEND1). VT_PORT hoan (target 25% hard-code, can build).
Ha tang: COIN mode doc /home/ubuntu/java/fsrun/CLOSES_1H.bin + /home/ubuntu/selector_pred_out/symbol_map.csv
=> dataset phu sim-vt-data + kernel tao symlink (vá KERNEL_TEMPLATE trong bo nho, KHONG sua tools/kaggle_sim.py).
Usage: python3 voltarget_g2_run.py upload | submit | wait | fetch
"""
import hashlib
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
LOG = logging.getLogger("vtg2run")
D = "/home/ubuntu/claude_master/0929/ds_vt_data"
SRC = {"CLOSES_1H.bin": "/home/ubuntu/java/fsrun/CLOSES_1H.bin",
       "symbol_map.csv": "/home/ubuntu/selector_pred_out/symbol_map.csv"}
SLUG = "sim-vt-data"
TAGS = {"b0": {}, "coin": {"SIZE_VOL_TARGET_MODE": "COIN"}}
END, JAR_DS, BUNDLE = "20251231", "sim-jar-gdv2", "sim-x1-2021-bundle"

ANCHOR = 'env.update({str(k): str(v) for k, v in (CFG.get("extra_env") or {}).items()})'
SNIP = '''
# [VT-G2] COIN mode can 2 file o duong dan cung (khong co trong bundle) -> symlink tu dataset sim-vt-data
for _nm, _dst in (("CLOSES_1H.bin", "/home/ubuntu/java/fsrun/CLOSES_1H.bin"),
                  ("symbol_map.csv", "/home/ubuntu/selector_pred_out/symbol_map.csv")):
    _src = [p for p in sorted(glob.glob(IN + "/**/" + _nm, recursive=True)) if "/sim-vt-data/" in p]
    if not _src:
        LOG.error("MISSING %s trong sim-vt-data", _nm)
        sys.exit(1)
    os.makedirs(os.path.dirname(_dst), exist_ok=True)
    if not os.path.lexists(_dst):
        os.symlink(_src[0], _dst)
    LOG.info("VT link %s -> %s (%d bytes)", _dst, _src[0], os.path.getsize(_dst))
'''


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def upload():
    os.makedirs(D, exist_ok=True)
    shas = {}
    for n, s in SRC.items():
        shutil.copy(s, os.path.join(D, n))
        shas[n] = sha(os.path.join(D, n))
        LOG.info("copy %s sha256=%s", n, shas[n])
    json.dump(shas, open("/home/ubuntu/claude_master/0929/vt_data_sha.json", "w"))
    json.dump({"title": SLUG, "id": "chuyendinh/" + SLUG, "licenses": [{"name": "CC0-1.0"}]},
              open(D + "/dataset-metadata.json", "w"))
    api = KaggleApi()
    api.authenticate()
    try:
        api.dataset_create_new(folder=D, public=False, dir_mode="skip")
        LOG.info("dataset created")
    except Exception as e:
        LOG.warning("create failed (%s) -> version", e)
        api.dataset_create_version(folder=D, version_notes="vt data", dir_mode="skip")
    t0 = time.time()
    while time.time() - t0 < 900:
        st = str(api.dataset_status("chuyendinh/" + SLUG))
        LOG.info("dataset status=%s", st)
        if st.lower() == "ready":
            return
        time.sleep(20)
    LOG.error("dataset chua ready")
    sys.exit(2)


def tag(n):
    return "vt-g2-" + n


def submit(names):
    assert ANCHOR in ks.KERNEL_TEMPLATE, "anchor khong thay trong KERNEL_TEMPLATE"
    ks.KERNEL_TEMPLATE = ks.KERNEL_TEMPLATE.replace(ANCHOR, ANCHOR + "\n" + SNIP, 1)
    LOG.info("free_slots=%s", ks.free_slots())
    refs = {}
    for n in names:
        refs[n] = ks.submit(tag(n), "g2_flat3", TAGS[n], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                            extra_ds=["sim-prof-g2flat3", SLUG], sim_end_date=END, code_sha="prereg-ecae6ef3")
        LOG.info("SUBMIT %s -> %s overrides=%s", n, refs[n], json.dumps(TAGS[n]))
    json.dump(refs, open("/home/ubuntu/claude_master/0929/vt_refs.json", "w"))


def wait(names):
    refs = [ks.kernel_ref(tag(n)) for n in names]
    LOG.info("STATUS %s", ks.wait(refs))


def fetch(names):
    for n in names:
        out = ks.fetch(tag(n))
        LOG.info("FETCH %s %s", n, json.dumps(out["result"]))
        LOG.info("   printDone=%s", out["print_done"])


if __name__ == "__main__":
    cmd = sys.argv[1]
    names = sys.argv[2:] or list(TAGS)
    {"upload": lambda: upload(), "submit": lambda: submit(names), "wait": lambda: wait(names),
     "fetch": lambda: fetch(names)}[cmd]()
