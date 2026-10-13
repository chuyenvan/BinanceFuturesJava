"""B2 - fetch Vision zips for one manifest type and one month, verify sha256.

Usage: vz_fetch.py <manifest_type> <YYYY-MM>
"""
import argparse
import csv
import gzip
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from vz_common import (
    MANIFEST_DIR,
    ROOT,
    STATE_DIR,
    TMP_DIR,
    VISION_BASE,
    http_get,
    sha256_file,
    setup_logging,
    TYPES,
)

log = setup_logging("fetch")
RETRIES = 5


def month_match(key, yyyy_mm, granularity):
    name = key.rsplit("/", 1)[-1]
    if granularity == "monthly":
        return name.endswith("-%s.zip" % yyyy_mm)
    return ("-%s-" % yyyy_mm) in name and name.endswith(".zip")


def load_manifest(typ, yyyy_mm):
    path = os.path.join(MANIFEST_DIR, typ + ".csv.gz")
    with gzip.open(path, "rt") as fh:
        rows = list(csv.DictReader(fh))
    _, _, gran = TYPES[typ]
    sel = [r for r in rows if month_match(r["key"], yyyy_mm, gran)]
    return sel


def download_one(rec, outdir, stats, lock):
    key = rec["key"]
    url = VISION_BASE + "/" + key
    csum_url = url + ".CHECKSUM"
    fname = key.rsplit("/", 1)[-1]
    dest = os.path.join(outdir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) == int(rec["size"]):
        stats["skipped"] += 1
        return ("skip", key)
    delay = 2
    for attempt in range(1, RETRIES + 1):
        try:
            r = http_get(csum_url, timeout=60)
            if r.status_code in (403, 404):
                with lock:
                    stats["missing"].append(key)
                return ("missing", key)
            r.raise_for_status()
            expect = r.text.split()[0].strip()
            r2 = http_get(url, timeout=60, stream=True)
            if r2.status_code in (403, 404):
                with lock:
                    stats["missing"].append(key)
                return ("missing", key)
            r2.raise_for_status()
            tmp = dest + ".part"
            with open(tmp, "wb") as fh:
                for chunk in r2.iter_content(1 << 20):
                    fh.write(chunk)
            got = sha256_file(tmp)
            if got != expect:
                os.remove(tmp)
                raise RuntimeError("checksum mismatch %s != %s" % (got, expect))
            os.rename(tmp, dest)
            with lock:
                stats["ok"] += 1
                stats["bytes"] += os.path.getsize(dest)
            return ("ok", key)
        except Exception as e:  # noqa: BLE001
            if attempt == RETRIES:
                with lock:
                    stats["bad"].append({"key": key, "err": str(e)})
                return ("bad", key)
            time.sleep(delay)
            delay = min(delay * 2, 32)
    return ("bad", key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("type")
    ap.add_argument("month")
    args = ap.parse_args()
    typ, ym = args.type, args.month
    outdir = os.path.join(TMP_DIR, typ, ym)
    os.makedirs(outdir, exist_ok=True)
    stats = {"ok": 0, "skipped": 0, "bytes": 0, "missing": [], "bad": []}
    lock = threading.Lock()

    # idempotency: skip if month already done
    st_path = os.path.join(STATE_DIR, typ, ym + ".json")
    if os.path.exists(st_path):
        with open(st_path) as fh:
            prev = json.load(fh)
        if prev.get("fetch_done"):
            log.info("type=%s month=%s already fetched (state) - skip", typ, ym)
            return 0

    recs = load_manifest(typ, ym)
    log.info("type=%s month=%s files=%d", typ, ym, len(recs))
    if not recs:
        log.warning("no files for %s %s", typ, ym)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(download_one, r, outdir, stats, lock) for r in recs]
        for i, _ in enumerate(as_completed(futs), 1):
            if i % 200 == 0:
                log.info("type=%s %s progress %d/%d ok=%d", typ, ym, i, len(recs), stats["ok"])
    dur = time.time() - t0
    os.makedirs(os.path.dirname(st_path), exist_ok=True)
    res = {
        "type": typ,
        "month": ym,
        "fetch_done": True,
        "n_zip": len(recs),
        "n_ok": stats["ok"],
        "n_skipped": stats["skipped"],
        "n_missing": len(stats["missing"]),
        "n_bad": len(stats["bad"]),
        "zip_bytes": stats["bytes"],
        "seconds": round(dur, 1),
        "missing": stats["missing"][:5000],
        "bad": stats["bad"][:200],
    }
    with open(st_path, "w") as fh:
        json.dump(res, fh, indent=1)
    log.info(
        "type=%s month=%s DONE ok=%d missing=%d bad=%d bytes=%d in %.1fs",
        typ, ym, stats["ok"], len(stats["missing"]), len(stats["bad"]), stats["bytes"], dur,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
