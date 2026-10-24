"""FEE0 step0(b): list USDC-M symbols from Binance Vision S3 (monthly+daily klines 1m prefixes) and first date PIT."""
import re, json, os, urllib.request, xml.etree.ElementTree as ET
B = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
WK = os.path.expanduser("~/claude_master/fee0_wk"); os.makedirs(WK, exist_ok=True)


def ls(prefix, delim=True):
    out_p, out_k, marker = [], [], ""
    while True:
        u = f"{B}?prefix={prefix}" + ("&delimiter=/" if delim else "") + (f"&marker={marker}" if marker else "")
        x = ET.fromstring(urllib.request.urlopen(u, timeout=60).read())
        ps = [e.find(NS + "Prefix").text for e in x.findall(NS + "CommonPrefixes")]
        ks = [e.find(NS + "Key").text for e in x.findall(NS + "Contents")]
        out_p += ps; out_k += ks
        if x.find(NS + "IsTruncated").text != "true":
            break
        marker = (ps + ks)[-1] if not x.find(NS + "NextMarker") is not None else x.find(NS + "NextMarker").text
        marker = x.find(NS + "NextMarker").text if x.find(NS + "NextMarker") is not None else sorted(ps + ks)[-1]
    return out_p, out_k


p, _ = ls("data/futures/um/daily/klines/")
syms = sorted(q.split("/")[-2] for q in p if q.split("/")[-2].endswith("USDC"))
print("n USDC daily symbols", len(syms))
res = {}
for s in syms:
    _, ks = ls(f"data/futures/um/daily/klines/{s}/1m/", delim=False)
    ds = sorted(re.findall(r"(\d{4}-\d{2}-\d{2})\.zip$", k)[0] for k in ks if k.endswith(".zip"))
    res[s] = {"first": ds[0] if ds else None, "last": ds[-1] if ds else None, "n_days": len(ds)}
    print(s, res[s])
pm, _ = ls("data/futures/um/monthly/klines/")
msyms = sorted(q.split("/")[-2] for q in pm if q.split("/")[-2].endswith("USDC"))
for s in msyms:
    _, ks = ls(f"data/futures/um/monthly/klines/{s}/1m/", delim=False)
    ms = sorted(re.findall(r"(\d{4}-\d{2})\.zip$", k)[0] for k in ks if k.endswith(".zip"))
    res.setdefault(s, {})["monthly_first"] = ms[0] if ms else None
    res[s]["monthly_last"] = ms[-1] if ms else None
    res[s]["n_months"] = len(ms)
pb, _ = ls("data/futures/um/daily/bookDepth/")
bsyms = sorted(q.split("/")[-2] for q in pb if q.split("/")[-2].endswith("USDC"))
for s in bsyms:
    _, ks = ls(f"data/futures/um/daily/bookDepth/{s}/", delim=False)
    ds = sorted(re.findall(r"(\d{4}-\d{2}-\d{2})\.zip$", k)[0] for k in ks if k.endswith(".zip"))
    res.setdefault(s, {})["bookDepth_first"] = ds[0] if ds else None
    res[s]["bookDepth_last"] = ds[-1] if ds else None
    res[s]["bookDepth_n"] = len(ds)
pf, _ = ls("data/futures/um/monthly/fundingRate/")
fsyms = sorted(q.split("/")[-2] for q in pf if q.split("/")[-2].endswith("USDC"))
for s in fsyms:
    res.setdefault(s, {})["funding_monthly"] = True
json.dump(res, open(WK + "/usdc_listing.json", "w"), indent=1)
print("monthly", len(msyms), "bookDepth", len(bsyms), "funding", len(fsyms))
