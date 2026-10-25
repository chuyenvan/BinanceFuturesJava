"""SYMLIFE step1: Binance Vision S3 listing -> per-symbol list of daily kline-1m dates (+monthly) for UM futures.
Doc lap, chi doc listing (khong tai data). Output: ~/claude_master/symlife_wk/vision_listing.json"""
import re, json, os, sys, time, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
B = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
WK = os.path.expanduser("~/claude_master/symlife_wk"); os.makedirs(WK, exist_ok=True)


def get(u):
    for k in range(6):
        try:
            return urllib.request.urlopen(u, timeout=60).read()
        except Exception as e:
            if k == 5:
                raise
            time.sleep(2 * (k + 1))


def ls(prefix, delim=True):
    out_p, out_k, marker = [], [], ""
    while True:
        u = f"{B}?prefix={urllib.parse.quote(prefix)}" + ("&delimiter=/" if delim else "") + (f"&marker={urllib.parse.quote(marker)}" if marker else "")
        x = ET.fromstring(get(u))
        ps = [e.find(NS + "Prefix").text for e in x.findall(NS + "CommonPrefixes")]
        ks = [e.find(NS + "Key").text for e in x.findall(NS + "Contents")]
        out_p += ps; out_k += ks
        if x.find(NS + "IsTruncated").text != "true":
            break
        nm = x.find(NS + "NextMarker")
        marker = nm.text if nm is not None else sorted(ps + ks)[-1]
    return out_p, out_k


import urllib.parse
pd_, _ = ls("data/futures/um/daily/klines/")
pm_, _ = ls("data/futures/um/monthly/klines/")
dsyms = sorted(q.split("/")[-2] for q in pd_)
msyms = sorted(q.split("/")[-2] for q in pm_)
print("daily syms", len(dsyms), "monthly syms", len(msyms), flush=True)


def one_daily(s):
    _, ks = ls(f"data/futures/um/daily/klines/{s}/1m/", delim=False)
    return s, sorted(set(re.findall(r"(\d{4}-\d{2}-\d{2})\.zip$", k)[0] for k in ks if k.endswith(".zip")))


def one_monthly(s):
    _, ks = ls(f"data/futures/um/monthly/klines/{s}/1m/", delim=False)
    return s, sorted(set(re.findall(r"(\d{4}-\d{2})\.zip$", k)[0] for k in ks if k.endswith(".zip")))


res = {"daily": {}, "monthly": {}, "listed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
with ThreadPoolExecutor(12) as ex:
    for i, (s, ds) in enumerate(ex.map(one_daily, dsyms)):
        res["daily"][s] = ds
        if i % 100 == 0:
            print("d", i, s, len(ds), flush=True)
    for i, (s, ms) in enumerate(ex.map(one_monthly, msyms)):
        res["monthly"][s] = ms
json.dump(res, open(WK + "/vision_listing.json", "w"))
print("DONE", len(res["daily"]), len(res["monthly"]), sum(len(v) for v in res["daily"].values()))
