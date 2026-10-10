#!/usr/bin/env python3
"""HO4: thu lay log (neu API tra) cua kernel dang chay. Usage: ho4_klog.py <slug>"""
import json, sys
from kaggle.api.kaggle_api_extended import KaggleApi
a = KaggleApi(); a.authenticate()
try:
    r = a.process_response(a.kernel_output_with_http_info("chuyendinh", sys.argv[1]))
    lg = r.get("log") or ""
    try:
        lines = "".join(x.get("data", "") for x in json.loads(lg))
    except Exception:  # noqa: BLE001
        lines = lg
    print("FILES", [f["fileName"] for f in r.get("files", [])][:10])
    print(lines[-3000:])
except Exception as e:  # noqa: BLE001
    print("ERR", repr(e)[:300])
