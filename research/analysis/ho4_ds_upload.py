#!/usr/bin/env python3
"""HO4-P3: tao dataset Kaggle nho cho cong sim (hardlink vao thu muc stage, khong nhan doi dia).
ho4-dev-mkt (market.bin), ho4-dev-pred (pred.bin), ho4-dev-bins (2 bins fold 20250701/20251001) + ghi chain/bins_md5.json.
KHONG dat ten manifest.txt/config.properties (kernel sim chon file dau tien theo ten). Usage: ho4_ds_upload.py"""
import hashlib, json, logging, os, shutil, sys
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
W = "/home/ubuntu/claude_master/1010/ho4"
C = W + "/chain"
ST = W + "/stage"


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


a = KaggleApi(); a.authenticate()
bm = {n: md5f(C + "/bins/" + n) for n in ("predict_wf_20250701.bin", "predict_wf_20251001.bin")}
json.dump(bm, open(C + "/bins_md5.json", "w"), indent=1)
for slug, files in (("ho4-dev-mkt", [C + "/market.bin"]), ("ho4-dev-pred", [C + "/pred.bin"]),
                    ("ho4-dev-bins", [C + "/bins/predict_wf_20250701.bin", C + "/bins/predict_wf_20251001.bin"])):
    d = os.path.join(ST, slug)
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    man = {}
    for f in files:
        os.link(f, os.path.join(d, os.path.basename(f)))
        man[os.path.basename(f)] = md5f(f)
    json.dump(man, open(os.path.join(d, "HO4_MD5.json"), "w"), indent=1)
    json.dump({"title": slug, "id": "chuyendinh/" + slug, "licenses": [{"name": "CC0-1.0"}]},
              open(os.path.join(d, "dataset-metadata.json"), "w"))
    a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
    logging.info("CREATED %s %s", slug, man)
