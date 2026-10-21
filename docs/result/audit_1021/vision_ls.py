"""AUDIT 1021 viec B — CHI METADATA: liet ke S3 listing data.binance.vision (ten file / kich thuoc / ngay sua).
KHONG tai bat ky file du lieu nao (khong GET .zip). Chi goi ListObjects (XML)."""
import json, logging, sys, time, re
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("vls")
BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
OUT = sys.argv[1] if len(sys.argv) > 1 else "vision_2020_meta.json"


def ls(prefix, delimiter=None, max_keys=1000, marker=None):
    q = {"prefix": prefix, "max-keys": str(max_keys)}
    if delimiter: q["delimiter"] = delimiter
    if marker: q["marker"] = marker
    url = BASE + "?" + urllib.parse.urlencode(q)
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                root = ET.fromstring(r.read())
            break
        except Exception as e:
            log.info("retry %s %s", prefix, e); time.sleep(2 + 3 * k)
    else:
        raise RuntimeError("ls fail " + prefix)
    pre = [p.find(NS + "Prefix").text for p in root.findall(NS + "CommonPrefixes")]
    objs = [(c.find(NS + "Key").text, int(c.find(NS + "Size").text), c.find(NS + "LastModified").text)
            for c in root.findall(NS + "Contents")]
    trunc = (root.find(NS + "IsTruncated").text == "true")
    return pre, objs, trunc


def ls_all(prefix, delimiter=None):
    pres, objs, marker = [], [], None
    while True:
        p, o, t = ls(prefix, delimiter, marker=marker)
        pres += p; objs += o
        if not t: break
        marker = (o[-1][0] if o else p[-1])
    return pres, objs


def symbols(prefix):
    p, _ = ls_all(prefix, "/")
    return sorted(x[len(prefix):].strip("/") for x in p)


res = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "note": "chi listing S3, khong tai file du lieu"}

# 1) UM klines 1m monthly 2020 — so symbol theo thang
um_k = "data/futures/um/monthly/klines/"
syms = symbols(um_k)
log.info("UM klines symbols (moi thoi ky) = %d", len(syms))
def k2020(sym):
    _, o = ls_all(f"{um_k}{sym}/1m/{sym}-1m-2020")
    return sym, [(k.split("/")[-1], s, lm) for k, s, lm in o if k.endswith(".zip")]
per_month = defaultdict(list); files_k = {}
with ThreadPoolExecutor(16) as ex:
    for sym, fl in ex.map(k2020, syms):
        if fl:
            files_k[sym] = fl
            for name, s, lm in fl:
                per_month[name[len(sym) + 4:len(sym) + 11]].append(sym)
res["um_klines_1m_monthly_2020"] = {"n_symbols_any_2020": len(files_k),
    "per_month": {m: {"n": len(v), "symbols": sorted(v)} for m, v in sorted(per_month.items())},
    "total_bytes": sum(s for fl in files_k.values() for _, s, _ in fl),
    "lastmod_range": [min(lm for fl in files_k.values() for *_, lm in fl), max(lm for fl in files_k.values() for *_, lm in fl)] if files_k else None}
log.info("UM 1m 2020: %d symbol; theo thang %s", len(files_k), {m: len(v) for m, v in sorted(per_month.items())})

# 1b) UM klines daily 1m 2020 (kiem co ban daily khong)
_, o = ls_all(f"data/futures/um/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2020")
res["um_klines_1m_daily_2020_BTCUSDT_nfiles"] = len([x for x in o if x[0].endswith(".zip")])

# 2) fundingRate monthly 2020
um_f = "data/futures/um/monthly/fundingRate/"
fsyms = symbols(um_f)
def f2020(sym):
    _, o = ls_all(f"{um_f}{sym}/{sym}-fundingRate-2020")
    return sym, [(k.split("/")[-1], s, lm) for k, s, lm in o if k.endswith(".zip")]
fm = defaultdict(list); first_f = {}
with ThreadPoolExecutor(16) as ex:
    for sym, fl in ex.map(f2020, fsyms):
        for name, s, lm in fl:
            fm[name[-11:-4]].append(sym)
def ffirst(sym):
    _, o, _ = ls(f"{um_f}{sym}/{sym}-fundingRate-", max_keys=1)
    return sym, (o[0][0].split("/")[-1] if o else None)
with ThreadPoolExecutor(16) as ex:
    for sym, nm in ex.map(ffirst, fsyms): first_f[sym] = nm
res["um_fundingRate_monthly_2020"] = {"n_symbols_listed_total": len(fsyms),
    "per_month": {m: len(v) for m, v in sorted(fm.items())},
    "symbols_2020": sorted(set(s for v in fm.values() for s in v)),
    "earliest_file_BTCUSDT": first_f.get("BTCUSDT"),
    "n_symbols_earliest_le_2020": sum(1 for v in first_f.values() if v and re.search(r"-20(19|20)-", v))}
log.info("fundingRate 2020 per month %s", res["um_fundingRate_monthly_2020"]["per_month"])

# 3) metrics (OI 5m) daily — ngay som nhat moi symbol
um_m = "data/futures/um/daily/metrics/"
msyms = symbols(um_m)
def mfirst(sym):
    _, o, _ = ls(f"{um_m}{sym}/{sym}-metrics-", max_keys=1)
    return sym, (o[0][0].split("/")[-1] if o else None)
mf = {}
with ThreadPoolExecutor(16) as ex:
    for sym, nm in ex.map(mfirst, msyms): mf[sym] = nm
dates = sorted(v[-14:-4] for v in mf.values() if v)
res["um_metrics_daily"] = {"n_symbols": len(msyms), "earliest_overall": dates[0] if dates else None,
    "earliest_BTCUSDT": mf.get("BTCUSDT"), "n_symbols_with_2020_file": sum(1 for d in dates if d.startswith("2020")),
    "earliest_dates_hist": dict(sorted(defaultdict(int, {d[:7]: dates.count(d) for d in set(dates)}).items())[:12])}
_, o = ls_all(f"{um_m}BTCUSDT/BTCUSDT-metrics-2020")
res["um_metrics_daily"]["BTCUSDT_2020_nfiles"] = len([x for x in o if x[0].endswith(".zip")])
log.info("metrics earliest %s BTC %s", res["um_metrics_daily"]["earliest_overall"], mf.get("BTCUSDT"))

# 4) bookDepth daily — ngay som nhat (BTCUSDT + toan bo)
um_b = "data/futures/um/daily/bookDepth/"
bsyms = symbols(um_b)
def bfirst(sym):
    _, o, _ = ls(f"{um_b}{sym}/{sym}-bookDepth-", max_keys=1)
    return sym, (o[0][0].split("/")[-1] if o else None)
bf = {}
with ThreadPoolExecutor(16) as ex:
    for sym, nm in ex.map(bfirst, bsyms): bf[sym] = nm
bd = sorted(v[-14:-4] for v in bf.values() if v)
res["um_bookDepth_daily"] = {"n_symbols": len(bsyms), "earliest_overall": bd[0] if bd else None,
    "earliest_BTCUSDT": bf.get("BTCUSDT"), "n_symbols_with_2020": sum(1 for d in bd if d.startswith("2020"))}

# 5) aggTrades monthly 2020 (so symbol co file 2020)
um_a = "data/futures/um/monthly/aggTrades/"
asyms = symbols(um_a)
def a2020(sym):
    _, o = ls_all(f"{um_a}{sym}/{sym}-aggTrades-2020")
    return sym, len([x for x in o if x[0].endswith(".zip")]), sum(x[1] for x in o)
an = {}; ab = 0
with ThreadPoolExecutor(16) as ex:
    for sym, n, b in ex.map(a2020, asyms):
        if n: an[sym] = n; ab += b
res["um_aggTrades_monthly_2020"] = {"n_symbols": len(an), "total_bytes": ab}

# 6) premiumIndexKlines / markPriceKlines / indexPriceKlines 1m 2020 — BTCUSDT (basis)
for kind in ("premiumIndexKlines", "markPriceKlines", "indexPriceKlines"):
    _, o = ls_all(f"data/futures/um/monthly/{kind}/BTCUSDT/1m/BTCUSDT-1m-2020")
    res[f"um_{kind}_1m_2020_BTCUSDT_nfiles"] = len([x for x in o if x[0].endswith(".zip")])
    _, o2, _ = ls(f"data/futures/um/monthly/{kind}/BTCUSDT/1m/BTCUSDT-1m-", max_keys=1)
    res[f"um_{kind}_1m_BTCUSDT_earliest"] = o2[0][0].split("/")[-1] if o2 else None

# 7) spot klines 1m monthly 2020 — so cap USDT co file 2020
sp_k = "data/spot/monthly/klines/"
ssyms = [s for s in symbols(sp_k) if s.endswith("USDT")]
def s2020(sym):
    _, o = ls_all(f"{sp_k}{sym}/1m/{sym}-1m-2020")
    return sym, len([x for x in o if x[0].endswith(".zip")])
sn = {}
with ThreadPoolExecutor(16) as ex:
    for sym, n in ex.map(s2020, ssyms):
        if n: sn[sym] = n
res["spot_klines_1m_monthly_2020_USDT"] = {"n_symbols": len(sn), "n_12_months": sum(1 for v in sn.values() if v == 12)}

# 8) UM 2021-01 (doi chieu so symbol dau ky DEV)
_, _ = None, None
def k2101(sym):
    _, o = ls_all(f"{um_k}{sym}/1m/{sym}-1m-2021-01")
    return sym, bool(o)
n2101 = 0
with ThreadPoolExecutor(16) as ex:
    for sym, ok in ex.map(k2101, syms): n2101 += ok
res["um_klines_1m_2021_01_n_symbols"] = n2101

json.dump(res, open(OUT, "w"), indent=1)
log.info("WROTE %s", OUT)
