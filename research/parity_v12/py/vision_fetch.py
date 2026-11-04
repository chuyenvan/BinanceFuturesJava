#!/usr/bin/env python3
"""PARITY_V11_WINDOW (docs/prereg/PREREG_PARITY_V11_WINDOW.md §2.1): tai Vision UM 1m DAILY (file tinh data.binance.vision),
GIU zip goc + manifest md5. Khong Binance REST, khong doc 242.

argv: universe.txt day_from day_to out_root [--kind klines_1m]
  out_root/<YYYY-MM-DD>/<SYM>.zip ; out_root/<YYYY-MM-DD>/_manifest.csv (sym,http,bytes,md5)
Zip da co + md5 khop manifest => bo qua (idempotent). 404 ghi vao manifest (symbol khong co ngay do).
"""
import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import hashlib
import logging
import os
import sys
import time
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("vision_fetch")
URL = "https://data.binance.vision/data/futures/um/daily/klines/{s}/1m/{s}-1m-{d}.zip"


def get(job):
    s, d, path = job
    if os.path.exists(path) and os.path.getsize(path) > 0:
        b = open(path, "rb").read()
        return s, 200, len(b), hashlib.md5(b).hexdigest(), "cached"
    for k in range(4):
        try:
            with urllib.request.urlopen(URL.format(s=urllib.request.quote(s), d=d), timeout=40) as r:
                b = r.read()
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(b)
            os.replace(tmp, path)
            return s, 200, len(b), hashlib.md5(b).hexdigest(), "new"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return s, 404, 0, "", "404"
            time.sleep(1 + 2 * k)
        except Exception:  # noqa: BLE001 - mang chap chon: thu lai
            time.sleep(1 + 2 * k)
    return s, -1, 0, "", "error"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("day_from")
    ap.add_argument("day_to")
    ap.add_argument("out_root")
    ap.add_argument("--threads", type=int, default=24)
    a = ap.parse_args()
    syms = sorted({x.strip() for x in open(a.universe) if x.strip() and not x.startswith("#")})
    d0 = dt.date.fromisoformat(a.day_from)
    d1 = dt.date.fromisoformat(a.day_to)
    rc = 0
    d = d0
    while d <= d1:
        ds = d.isoformat()
        od = os.path.join(a.out_root, ds)
        os.makedirs(od, exist_ok=True)
        jobs = [(s, ds, os.path.join(od, s + ".zip")) for s in syms]
        st = {}
        rows = []
        t0 = time.time()
        with cf.ThreadPoolExecutor(a.threads) as ex:
            for s, code, n, md5, how in ex.map(get, jobs):
                st[how] = st.get(how, 0) + 1
                rows.append((s, code, n, md5))
        rows.sort()
        with open(os.path.join(od, "_manifest.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sym", "http", "bytes", "md5"])
            w.writerows(rows)
        n200 = sum(1 for r in rows if r[1] == 200)
        log.info("day %s syms=%d ok=%d (%.2f%%) stat=%s %.0fs", ds, len(syms), n200, 100.0 * n200 / max(1, len(syms)), st,
                 time.time() - t0)
        if st.get("error"):
            log.error("day %s: %d file loi mang (chay lai)", ds, st["error"])
            rc = 2
        d += dt.timedelta(days=1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
