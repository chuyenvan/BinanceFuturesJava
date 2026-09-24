"""Recon 0-cost: liet ke metadata aggTrades monthly tren data.binance.vision (S3 listing, chi ten+size).
KHONG tai file, KHONG tinh edge5/rank-IC."""
import json
import logging
import re
import urllib.request
from urllib.parse import quote as q
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("recon")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
PFX = "data/futures/um/monthly/aggTrades/"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
OUT = r"D:\claudedata\ofi_v3"


def s3list(prefix, delimiter=None):
    keys, prefixes, marker = [], [], ""
    while True:
        url = (f"{S3}?prefix={q(prefix)}" + (f"&delimiter={delimiter}" if delimiter else "")
               + (f"&marker={q(marker)}" if marker else ""))
        with urllib.request.urlopen(url, timeout=60) as r:
            root = ET.fromstring(r.read())
        for c in root.findall("s:Contents", NS):
            keys.append((c.find("s:Key", NS).text, int(c.find("s:Size", NS).text)))
        for p in root.findall("s:CommonPrefixes", NS):
            prefixes.append(p.find("s:Prefix", NS).text)
        trunc = root.find("s:IsTruncated", NS).text == "true"
        if not trunc:
            break
        nm = root.find("s:NextMarker", NS)
        marker = nm.text if nm is not None else (keys[-1][0] if keys else prefixes[-1])
    return keys, prefixes


_, syms = s3list(PFX, "/")
syms = [p[len(PFX):-1] for p in syms]
log.info("n symbol dirs = %d", len(syms))
rx = re.compile(r"-aggTrades-(\d{4}-\d{2})\.zip$")


def one(sym):
    try:
        keys, _ = s3list(f"{PFX}{sym}/")
    except Exception as e:  # noqa: BLE001
        log.warning("fail %s: %s", sym, e)
        return sym, None
    out = {}
    for k, sz in keys:
        m = rx.search(k)
        if m:
            out[m.group(1)] = sz
    return sym, out


res = {}
with ThreadPoolExecutor(16) as ex:
    for sym, d in ex.map(one, syms):
        res[sym] = d
with open(OUT + r"\vision_aggtrades_monthly.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False)
log.info("done, saved %d symbols, fail=%d", len(res), sum(1 for v in res.values() if v is None))
