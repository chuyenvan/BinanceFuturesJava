"""B1 - inventory Binance Vision S3 listing into ~/vz/manifest/<type>.csv.gz.

Read-only. No Binance REST. Only data.binance.vision via the S3 endpoint.
"""
import argparse
import csv
import gzip
import os
import sys
import time

from vz_common import (
    MANIFEST_DIR,
    TYPES,
    classify_symbol,
    open_gz_csv_writer,
    s3_list,
    setup_logging,
)

log = setup_logging("inventory")


def list_symbols(base):
    _, prefixes = s3_list(base + "/", delimiter="/")
    syms = [p.rstrip("/").split("/")[-1] for p in prefixes]
    return sorted(set(syms))


def list_files(prefix):
    keys, _ = s3_list(prefix)
    return keys


def run_type(typ):
    base, interval, granularity = TYPES[typ]
    log.info("type=%s base=%s interval=%s gran=%s", typ, base, interval, granularity)
    syms = list_symbols(base)
    log.info("type=%s symbols=%d", typ, len(syms))
    rows = []
    kept = dropped = 0
    for i, sym in enumerate(syms, 1):
        keep, flag = classify_symbol(sym)
        if not keep:
            dropped += 1
            continue
        kept += 1
        pfx = base + "/" + sym + "/"
        if interval:
            pfx += interval + "/"
        for k in list_files(pfx):
            key = k["key"]
            if not key or not key.endswith(".zip"):
                continue
            rows.append(
                {
                    "key": key,
                    "size": k["size"],
                    "last_modified": k["last_modified"],
                    "checksum_key": key + ".CHECKSUM",
                    "sym": sym,
                    "flag": flag,
                }
            )
        if i % 50 == 0:
            log.info("type=%s scanned %d/%d symbols rows=%d", typ, i, len(syms), len(rows))
    out = os.path.join(MANIFEST_DIR, typ + ".csv.gz")
    with open_gz_csv_writer(out) as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["key", "size", "last_modified", "checksum_key", "sym", "flag"],
        )
        w.writeheader()
        w.writerows(rows)
    total = sum(r["size"] for r in rows)
    log.info(
        "type=%s DONE files=%d kept_syms=%d dropped_syms=%d total_bytes=%d -> %s",
        typ, len(rows), kept, dropped, total, out,
    )
    return len(rows), total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("types", nargs="*", default=[],
                    help="subset of types; default = all")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    types = args.types or list(TYPES.keys())
    t0 = time.time()
    for typ in types:
        out = os.path.join(MANIFEST_DIR, typ + ".csv.gz")
        complete = False
        if os.path.exists(out) and not args.force:
            try:
                with gzip.open(out, "rt") as fh:
                    fh.readline()
                    complete = bool(fh.readline())
            except Exception:  # noqa: BLE001
                complete = False
        if complete:
            log.info("type=%s manifest complete - skip (use --force)", typ)
            continue
        for attempt in range(1, 5):
            try:
                run_type(typ)
                break
            except Exception as e:  # noqa: BLE001
                log.warning("type=%s failed attempt %d: %s", typ, attempt, e)
                if attempt == 4:
                    raise
                time.sleep(10 * attempt)
    log.info("inventory ALL DONE in %.1fs", time.time() - t0)


if __name__ == "__main__":
    sys.exit(main())
