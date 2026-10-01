#!/usr/bin/env python3
"""GRID_RESEARCH fetch — tai kline 1m thang tu Binance public data (0-sim, read-only).

Pre-reg: docs/prereg/PREREG_GRID_RESEARCH.md. KHONG push du lieu. Trung gian /tmp/grid_research/.
Xuat manifest JSON (url + sha256 + rows) de dua vao ket qua.
"""
import hashlib
import io
import json
import os
import sys
import urllib.request
import zipfile

OUT = os.environ.get("GRID_DIR", "/tmp/grid_research")
COINS = "BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT DOGEUSDT".split()
MONTHS = ["2022-05", "2022-11", "2023-06", "2024-03", "2024-11", "2025-06"]
BASE = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"

os.makedirs(OUT, exist_ok=True)

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def fetch(sym, mon):
    url = BASE.format(s=sym, m=mon)
    p = os.path.join(OUT, "%s-%s.npy" % (sym, mon))
    if os.path.exists(p):
        return {"sym": sym, "month": mon, "cached": True, "path": p}
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    name = z.namelist()[0]
    txt = z.read(name).decode()
    lines = txt.strip().split("\n")
    # header optional
    if lines[0].startswith("open_time") or "open_time" in lines[0]:
        lines = lines[1:]
    import numpy as np
    arr = np.empty((len(lines), 6), dtype=np.float64)
    for i, ln in enumerate(lines):
        c = ln.split(",")
        arr[i] = (float(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5]))
    ts = arr[:, 0]
    # Binance doi sang microseconds cho file moi: chuan hoa ve ms
    if ts[0] > 1e14:
        ts = ts / 1000.0
        arr[:, 0] = ts
    np.save(p, arr)
    return {"sym": sym, "month": mon, "cached": False, "path": p, "url": url,
            "sha256": sha256(raw), "bytes": len(raw), "rows": int(len(lines))}

def main():
    man = []
    for s in COINS:
        for m in MONTHS:
            try:
                d = fetch(s, m)
                man.append(d)
                print("%s %s rows=%s" % (s, m, d.get("rows", "cached")), flush=True)
            except Exception as e:
                print("FAIL %s %s %s" % (s, m, e), flush=True)
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(man, f, indent=1)
    print("DONE n=%d" % len(man))

if __name__ == "__main__":
    main()
