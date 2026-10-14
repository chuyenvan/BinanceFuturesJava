"""VZ E1 - fetch the (only) allowed 2024 VZ datasets from Kaggle, idempotently.

Allowed: chuyendinh/vz-kline1m-2024, vz-basis1m-2024, vz-metrics5m(file 2024),
vz-funding (file 2024). No other year, no Binance REST.
Keeps the working set small: kline/basis are fetched per month and released on
request so the disk guard (>= 30 GB on /) is respected while Phase 1 runs.
"""
import os
import subprocess

from e1_common import (DS_BASIS, DS_FUNDING, DS_KLINE, DS_METRICS, RAW,
                       setup_logging)

log = setup_logging("e1_data")


def _valid_parquet(path):
    try:
        import pyarrow.parquet as pq
        pq.ParquetFile(path).metadata
        return True
    except Exception:
        return False


def _kaggle(ds, fname, dest_dir):
    dest = os.path.join(dest_dir, fname)
    if os.path.exists(dest) and os.path.getsize(dest) > 0 and _valid_parquet(dest):
        return dest
    if os.path.exists(dest):
        log.warning("discarding unreadable download %s", dest)
        os.remove(dest)
    os.makedirs(dest_dir, exist_ok=True)
    log.info("kaggle download %s -f %s", ds, fname)
    r = subprocess.run(["kaggle", "datasets", "download", "-d", ds, "-f", fname,
                        "-p", dest_dir], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dest):
        raise RuntimeError("download failed %s/%s: %s %s" % (ds, fname, r.stdout, r.stderr))
    return dest


def kline_month(month):
    return _kaggle(DS_KLINE, "kline1m-%s.parquet" % month, RAW)


def basis_month(month):
    return _kaggle(DS_BASIS, "basis1m-%s.parquet" % month, RAW)


def metrics_year(year="2024"):
    return _kaggle(DS_METRICS, "metrics5m-%s.parquet" % year, RAW)


def funding_year(year="2024"):
    return _kaggle(DS_FUNDING, "funding-%s.parquet" % year, RAW)


def release(month):
    """Delete raw kline/basis for a month (never metrics/funding)."""
    for p in (os.path.join(RAW, "kline1m-%s.parquet" % month),
              os.path.join(RAW, "basis1m-%s.parquet" % month)):
        if os.path.exists(p):
            os.remove(p)
