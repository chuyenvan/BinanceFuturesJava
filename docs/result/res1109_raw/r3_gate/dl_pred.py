#!/usr/bin/env python3
"""Tai 8 pred_s*/pred.bin (output kernel nt-chain-y26) cho sang P1 R3; kiem md5 theo prereg R3 ?3."""
import hashlib, logging, os, urllib.request
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dl")
WANT = {"42": "482f764e", "7": "37982fd9", "13": "258bc7d9", "21": "6b3aff7f", "99": "0b5df665", "123": "635f1f59", "777": "b2231aa8", "2024": "43abd92a"}
D = "/home/ubuntu/claude_master/res1109/r3_gate/pred"
a = KaggleApi(); a.authenticate()
r = a.process_response(a.kernel_output_with_http_info(user_name="chuyendinh", kernel_slug="nt-chain-y26"))
for f in r["files"]:
    n = f["fileName"]
    if not (n.startswith("out/pred_s") and n.endswith("/pred.bin")):
        continue
    s = n.split("pred_s")[1].split("/")[0]
    out = "%s/pred_s%s.bin" % (D, s)
    if not os.path.exists(out):
        urllib.request.urlretrieve(f["url"], out + ".part"); os.rename(out + ".part", out)
    m = hashlib.md5(open(out, "rb").read()).hexdigest()
    log.info("s%s %d bytes md5 %s want %s %s", s, os.path.getsize(out), m, WANT[s], "OK" if m.startswith(WANT[s]) else "MISMATCH")
