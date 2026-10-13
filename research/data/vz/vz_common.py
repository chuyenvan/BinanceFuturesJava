"""Shared helpers for the VZ data-lake pipeline (Binance Vision -> Kaggle).

Only data.binance.vision and s3-ap-northeast-1.amazonaws.com may be contacted.
Any other host raises, by design (see docs/plan/VZ_DATA_LAKE.md section 5).
"""
import gzip
import hashlib
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests

ALLOWED_HOSTS = {"data.binance.vision", "s3-ap-northeast-1.amazonaws.com"}
log = logging.getLogger("vz_common")
VISION_BASE = "https://data.binance.vision"
S3_ENDPOINT = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"

ROOT = os.path.expanduser("~/vz")
MANIFEST_DIR = os.path.join(ROOT, "manifest")
TMP_DIR = os.path.join(ROOT, "tmp")
OUT_DIR = os.path.join(ROOT, "out")
REPORT_DIR = os.path.join(ROOT, "reports")
STATE_DIR = os.path.join(ROOT, "state")
LOG_DIR = os.path.join(ROOT, "logs")

# S3 type -> (path base under data/futures/um, interval subdir or None, granularity)
P = "data/futures/um/"
TYPES = {
    "kline1m": (P + "monthly/klines", "1m", "monthly"),
    "premiumIndex1m": (P + "monthly/premiumIndexKlines", "1m", "monthly"),
    "markPrice1m": (P + "monthly/markPriceKlines", "1m", "monthly"),
    "indexPrice1m": (P + "monthly/indexPriceKlines", "1m", "monthly"),
    "metrics": (P + "daily/metrics", None, "daily"),
    "fundingRate": (P + "monthly/fundingRate", None, "monthly"),
}

# dataset slug -> list of S3 manifest types that feed it
DS_SOURCES = {
    "kline1m": ["kline1m"],
    "basis1m": ["premiumIndex1m", "markPrice1m", "indexPrice1m"],
    "metrics5m": ["metrics"],
    "funding": ["fundingRate"],
}

# stable / index flags for symbol filtering
STABLE_BASES = ("USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP")


def setup_logging(name):
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger(name)


def assert_allowed(url):
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise RuntimeError("host not allowed by VZ allowlist: %s" % host)


def http_get(url, **kw):
    assert_allowed(url)
    kw.setdefault("timeout", 60)
    return requests.get(url, **kw)


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _strip_ns(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def s3_list(prefix, delimiter=None, timeout=60):
    """Paginated S3 ListObjectsV2-style listing. Returns (keys, common_prefixes).

    keys: list of dicts {key, size, last_modified}
    """
    keys = []
    prefixes = []
    marker = None
    last_cp = [None]
    while True:
        params = {"prefix": prefix}
        if delimiter:
            params["delimiter"] = delimiter
        if marker:
            params["marker"] = marker
        root = None
        delay = 2
        for attempt in range(1, 6):
            try:
                r = http_get(S3_ENDPOINT, params=params, timeout=timeout)
                r.raise_for_status()
                root = ET.fromstring(r.content)
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 5:
                    raise
                log.warning("s3_list retry %d prefix=%s err=%s", attempt, prefix, e)
                time.sleep(delay)
                delay = min(delay * 2, 30)
        last_key = None
        truncated = False
        for el in root:
            name = _strip_ns(el.tag)
            if name == "Contents":
                rec = {}
                for c in el:
                    cn = _strip_ns(c.tag)
                    rec[cn] = c.text
                keys.append(
                    {
                        "key": rec.get("Key"),
                        "size": int(rec.get("Size", 0)),
                        "last_modified": rec.get("LastModified"),
                    }
                )
                last_key = rec.get("Key")
            elif name == "CommonPrefixes":
                for c in el:
                    if _strip_ns(c.tag) == "Prefix":
                        prefixes.append(c.text)
                        last_cp[0] = c.text
            elif name == "IsTruncated":
                truncated = (el.text or "").lower() == "true"
        if not truncated:
            break
        nxt = last_key or last_cp[0]
        if not nxt:
            break
        marker = nxt
    return keys, prefixes


def classify_symbol(sym):
    """Return (keep, flag).

    keep: bool  -> keep for the lake (USDT-margined perp)
    flag: str   -> '' | 'index' (BTCDOM) | 'stable'
    """
    if sym.endswith("_250926") or (len(sym) > 6 and sym[-7] == "_" and sym[-6:].isdigit()):
        return False, "quarterly"
    if not sym.endswith("USDT"):
        return False, "non_usdt"
    if sym == "BTCDOMUSDT":
        return True, "index"
    base = sym[:-4]
    if base in STABLE_BASES:
        return True, "stable"
    return True, ""


def open_gz_csv_writer(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return gzip.open(path, "wt", newline="")
