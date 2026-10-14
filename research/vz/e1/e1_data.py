"""VZ E1 - fetch the (only) allowed 2024 VZ datasets from Kaggle, idempotently.

Allowed: chuyendinh/vz-kline1m-2024, vz-basis1m-2024, vz-metrics5m(file 2024),
vz-funding (file 2024). No other year, no Binance REST.
Keeps the working set small: kline/basis are fetched per month and released on
request so the disk guard (>= 30 GB on /) is respected while Phase 1 runs.
"""
import csv
import os
import subprocess

import pandas as pd

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


# ---------------------------------------------------------------- anomalies
# The Phase-1 validate step ships `anomalies.csv` (sym, ts, reason) with each
# kline/basis dataset. Those rows are kept verbatim in the lake (never edited or
# deleted) but MUST be skipped by every consumer. Absent file == no anomalies.
ANOM = "anomalies.csv"
_ANOM_BY_SLUG = {}


def _anomalies_slug(slug):
    """{(sym, ts)} flagged for a dataset slug; cached, {} when the dataset ships none."""
    if slug in _ANOM_BY_SLUG:
        return _ANOM_BY_SLUG[slug]
    bad = set()
    d = os.path.join(RAW, "anomalies", slug.replace("/", "_"))
    dest = os.path.join(d, ANOM)
    if not os.path.exists(dest):
        os.makedirs(d, exist_ok=True)
        r = subprocess.run(["kaggle", "datasets", "download", "-d", slug, "-f", ANOM,
                            "-p", d], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(dest):
            log.info("no anomalies.csv in %s (no anomalies)", slug)
            _ANOM_BY_SLUG[slug] = bad
            return bad
    try:
        with open(dest, newline="") as fh:
            for row in csv.DictReader(fh):
                bad.add((row["sym"], int(row["ts"])))
    except Exception as e:  # noqa: BLE001
        log.warning("unreadable %s: %s", dest, e)
    log.info("anomalies %s: %d rows to skip", slug, len(bad))
    _ANOM_BY_SLUG[slug] = bad
    return bad


def anomalies(month, kind="kline"):
    """{(sym, ts)} rows to skip for a month, from that dataset's anomalies.csv."""
    return _anomalies_slug(kline_slug(month) if kind == "kline" else basis_slug(month))


def anomalies_for_path(path):
    """Anomalies for a local month parquet (`kline1m-YYYY-MM.parquet`); {} otherwise."""
    b = os.path.basename(path)
    for kind, pref in (("kline", "kline1m-"), ("basis", "basis1m-")):
        if b.startswith(pref) and b.endswith(".parquet"):
            month = b[len(pref):-len(".parquet")]
            try:
                return anomalies(month, kind)
            except Exception as e:  # noqa: BLE001
                log.warning("anomalies lookup failed for %s: %s", path, e)
                return set()
    return set()


def drop_anomalies(df, month, kind="kline"):
    """Drop the rows listed in the dataset's anomalies.csv (no-op when there are none)."""
    bad = anomalies(month, kind)
    if not bad or df is None or len(df) == 0:
        return df
    keep = pd.Series([(str(s), int(t)) not in bad
                      for s, t in zip(df["sym"], df["ts"])], index=df.index)
    n = int((~keep).sum())
    if n:
        log.info("drop %d anomaly row(s) from %s (%s)", n, month, kind)
    return df[keep]


def read_month(month, kind="kline", columns=None, fetch=True):
    """Read one month's kline/basis frame with anomalies.csv rows already removed."""
    df = pd.read_parquet(month_path(month, kind, fetch=fetch), columns=columns)
    return drop_anomalies(df, month, kind)
