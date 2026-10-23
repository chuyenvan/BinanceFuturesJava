#!/usr/bin/env python3
"""Push a Kaggle kernel folder, verify it exists, poll until done, fetch small outputs.

Usage: run_kernel.py <folder> <owner/slug> <dest_dir>
Never contains credentials; uses ~/.kaggle/kaggle.json via the Kaggle API.
"""
import json
import os
import sys
import time

from kaggle.api.kaggle_api_extended import KaggleApi

folder, slug, dest = sys.argv[1], sys.argv[2], sys.argv[3]
api = KaggleApi()
api.authenticate()

t0 = time.time()
api.kernels_push(folder)
print(f"{time.strftime('%H:%M:%S')} pushed {slug}", flush=True)

# hard existence check: status must not be 404/empty
st = api.kernels_status(slug)
print("status after push:", st, flush=True)
if not st or "status" not in st:
    raise SystemExit("PUSH NOT VISIBLE - aborting")

last = None
while True:
    st = api.kernels_status(slug)
    s = st.get("status")
    if s != last:
        print(f"{time.strftime('%H:%M:%S')} status={s} after {time.time()-t0:.0f}s", flush=True)
        last = s
    if s in ("complete", "error", "cancelacknowledged", "canceled"):
        print("final:", st, flush=True)
        break
    if time.time() - t0 > 11 * 3600:
        raise SystemExit("timeout waiting")
    time.sleep(60)

os.makedirs(dest, exist_ok=True)
try:
    got = api.kernels_output(slug, dest, force=True, quiet=False)
    print("downloaded:", got)
except Exception as e:
    print("output download failed:", e)
print(json.dumps({"slug": slug, "status": st.get("status"),
                  "wall_sec": round(time.time() - t0, 1)}))
