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


# dataset slug per year (2024 == DS_KLINE / DS_BASIS above)
KLINE_SLUG = "chuyendinh/vz-kline1m-%s"
BASIS_SLUG = "chuyendinh/vz-basis1m-%s"


def kline_slug(month):
    return KLINE_SLUG % month[:4]


def basis_slug(month):
    return BASIS_SLUG % month[:4]


def kline_month(month):
    return _kaggle(kline_slug(month), "kline1m-%s.parquet" % month, RAW)


def basis_month(month):
    return _kaggle(basis_slug(month), "basis1m-%s.parquet" % month, RAW)


def local_month(month, kind="kline"):
    """Local parquet for one month: the raw cache first, then the Phase-1 export.

    Returns None when neither exists. The confirmation runner checks this to
    REFUSE (read nothing, invent nothing) when a dataset is not in the lake yet.
    """
    for p in (os.path.join(RAW, "%s1m-%s.parquet" % (kind, month)),
              os.path.expanduser("~/vz/out/%s1m/%s/%s.parquet"
                                 % (kind, month[:4], month))):
        if os.path.exists(p) and os.path.getsize(p) > 0 and _valid_parquet(p):
            return p
    return None


def month_path(month, kind="kline", fetch=True):
    """Local path for a month (raw cache or Phase-1 export); download if fetch."""
    p = local_month(month, kind)
    if p is not None:
        return p
    if not fetch:
        raise FileNotFoundError("no local %s for %s (fetch disabled)" % (kind, month))
    return kline_month(month) if kind == "kline" else basis_month(month)


def kaggle_files(slug):
    """Names of the files in a Kaggle dataset (metadata listing only; no download).

    Returns None when the listing is unavailable. Used to tell "dataset not
    uploaded yet" apart from "not cached" before any download is attempted.
    """
    r = subprocess.run(["kaggle", "datasets", "files", slug],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    names = set()
    for line in r.stdout.splitlines():
        tok = line.split()
        if tok and (tok[0].endswith(".parquet") or tok[0].endswith(".md")):
            names.add(tok[0])
    return names or None


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
