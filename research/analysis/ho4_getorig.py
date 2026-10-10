#!/usr/bin/env python3
"""HO4: tai 1 file tu dataset Kaggle (backup net015 goc) + kiem sha256. Usage: ho4_getorig.py <ds> <file> <outdir> <sha256>"""
import hashlib, logging, os, sys, zipfile
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
ds, fn, out, want = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
a = KaggleApi(); a.authenticate()
a.dataset_download_file(ds, fn, path=out, force=True, quiet=True)
p = os.path.join(out, fn)
if not os.path.exists(p) and os.path.exists(p + ".zip"):
    with zipfile.ZipFile(p + ".zip") as z:
        z.extractall(out)
    os.remove(p + ".zip")
h = hashlib.sha256(open(p, "rb").read()).hexdigest()
logging.info("%s sha256=%s ok=%s bytes=%d", p, h, h == want, os.path.getsize(p))
sys.exit(0 if h == want else 2)
