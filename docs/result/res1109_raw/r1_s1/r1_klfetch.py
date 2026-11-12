#!/usr/bin/env python3
"""Tai lai kline1m Vision (Kaggle chuyendinh/vz-kline1m-YYYY) cho MTM gvz: 2021-12..2025-12.
Moi thang: tai file -> kiem sha256 voi README ~/vz/upload -> giu (ts,sym,close) nguyen dtype -> xoa ban goc.
Dung neu dia trong < 15 GB."""
import hashlib
import logging
import os
import re
import shutil
import sys

import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("klf")
OUT = "/home/ubuntu/claude_master/res1109/r1_s1/kl"
TMP = OUT + "/_tmp"
MIN_FREE = 15 * 2 ** 30


def months():
    out = ["2021-12"]
    for y in range(2022, 2026):
        out += ["%d-%02d" % (y, m) for m in range(1, 13)]
    return out


def readme_sha(y):
    t = open("/home/ubuntu/vz/upload/vz-kline1m-%s/README.md" % y).read()
    return dict(re.findall(r"\| (kline1m-\d{4}-\d{2}\.parquet) \|[^|]*\| \d+ \| ([0-9a-f]{64}) \|", t))


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    os.makedirs(TMP, exist_ok=True)
    for ym in months():
        dst = os.path.join(OUT, "kline1m-%s.parquet" % ym)
        if os.path.exists(dst):
            continue
        free = shutil.disk_usage("/").free
        if free < MIN_FREE:
            log.error("DUNG: dia trong %.1f GB < 15", free / 2 ** 30)
            sys.exit(5)
        y = ym[:4]
        fn = "kline1m-%s.parquet" % ym
        want = readme_sha(y).get(fn)
        api.dataset_download_file("chuyendinh/vz-kline1m-%s" % y, fn, path=TMP, force=True, quiet=True)
        src = os.path.join(TMP, fn)
        if not os.path.exists(src) and os.path.exists(src + ".zip"):
            import zipfile
            with zipfile.ZipFile(src + ".zip") as z:
                z.extractall(TMP)
            os.remove(src + ".zip")
        h = hashlib.sha256()
        with open(src, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        ok = want is not None and h.hexdigest() == want
        if not ok:
            log.error("DUNG: sha lech %s got=%s want=%s", fn, h.hexdigest(), want)
            sys.exit(6)
        t = pq.read_table(src, columns=["ts", "sym", "close"])
        pq.write_table(t, dst + ".part", compression="zstd")
        os.replace(dst + ".part", dst)
        log.info("%s rows=%d src=%.0fMB dst=%.0fMB sha_ok schema=%s", ym, t.num_rows, os.path.getsize(src) / 2 ** 20,
                 os.path.getsize(dst) / 2 ** 20, t.schema.types)
        os.remove(src)
    shutil.rmtree(TMP, ignore_errors=True)
    log.info("XONG")


if __name__ == "__main__":
    main()
