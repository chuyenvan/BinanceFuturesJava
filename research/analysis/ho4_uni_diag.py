#!/usr/bin/env python3
"""HO4-P3 chan doan cong M/G/T: symbol co trong universe Vision dung lai nhung KHONG co trong ticker DEV (theo thang),
va ti le phut quoteVolume=0 cua chung tren Vision (settle/ngung giao dich). Chi dem. Usage: ho4_uni_diag.py <out.json>"""
import io, json, logging, sys, urllib.request, urllib.parse, zipfile
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho3_b2_kline_as as k1
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
U = json.load(open("/home/ubuntu/claude_master/1010/ho4/kaggle/out/ho4-dev-x/out/universe_by_month.json"))
KURL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"


def zfrac(sm):
    s, m = sm
    with urllib.request.urlopen(KURL.format(s=urllib.parse.quote(s), m=m), timeout=60) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    rows = [ln.split(",") for ln in z.read(z.namelist()[0]).decode().splitlines()]
    rows = [x for x in rows if x and x[0].isdigit()]
    return s, len(rows), sum(1 for x in rows if float(x[7]) == 0.0)


res = {}
for m, day in (("2025-07", "20250715"), ("2025-10", "20251015"), ("2025-12", "20251220")):
    mm = k1.load_ticker(day)
    dev = set()
    for v in mm.values():
        dev |= set(v)
    extra = sorted(set(U[m]) - dev)
    with ThreadPoolExecutor(8) as ex:
        z = list(ex.map(zfrac, [(s, m) for s in extra]))
    res[m] = dict(n_vision=len(U[m]), n_dev_day=len(dev), n_extra=len(extra), dev_not_vision=sorted(dev - set(U[m])),
                  extra=[dict(sym=s, rows=n, zero_qv=k, zero_frac=round(k / max(n, 1), 4)) for s, n, k in z])
    logging.info("%s vision=%d dev=%d extra=%d all_zero=%d", m, len(U[m]), len(dev), len(extra), sum(1 for _, n, k in z if n and k == n))
json.dump(res, open(sys.argv[1], "w"), indent=1)
