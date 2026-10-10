#!/usr/bin/env python3
"""HO3b: upload thu muc ticker Q3 (1 thang) thanh dataset Kaggle rieng roi XOA .bin.gz local (giu MANIFEST_Q3.json).
Usage: ho3b_ticker_upload.py <dir> <dataset-slug>"""
import glob, json, logging, os, sys, time
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_tu")
d, slug = sys.argv[1], sys.argv[2]
man = json.load(open(os.path.join(d, "MANIFEST_Q3.json")))
fs = sorted(glob.glob(d + "/ticker_*.bin.gz"))
assert fs and len(fs) == len(man), (len(fs), len(man))
json.dump({"title": slug, "id": "chuyendinh/" + slug, "licenses": [{"name": "CC0-1.0"}]},
          open(os.path.join(d, "dataset-metadata.json"), "w"))
a = KaggleApi(); a.authenticate()
r = a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
log.info("UPLOAD %s -> %s", slug, getattr(r, "url", r))
for _ in range(60):
    st = a.dataset_status("chuyendinh/" + slug)
    if str(st) == "ready":
        break
    time.sleep(30)
log.info("status %s", st)
if str(st) == "ready":
    for f in fs:
        os.remove(f)
    log.info("da xoa %d file local", len(fs))
