#!/usr/bin/env python3
"""Ticker availability (sim Utils.isTickerAvailable: kline exists AND (high!=low OR quoteVol!=0)) for every NON-HELD candidate
minute in cand.csv.gz. Streams Vision monthly zips (sha256 vs .CHECKSUM), keeps only candidate minutes (<= 2026-09-30 23:59 +07).
Out (--out dir): unavail.csv (ts,symbol,reason), cand_bars.csv.gz (symbol,t,o,h,l,c for available candidate minutes in [lo,hi)),
avail_manifest.json (zip sha256/md5 per symbol-month)."""
import argparse, csv, gzip, hashlib, io, json, logging, os, time, urllib.request, zipfile
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s'); L = logging.getLogger('av')
TZ7 = timezone(timedelta(hours=7)); TS_MAX = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
ap = argparse.ArgumentParser(); ap.add_argument('--cand'); ap.add_argument('--lo'); ap.add_argument('--hi'); ap.add_argument('--out')
a = ap.parse_args()
d7 = lambda s: int(datetime.strptime(s, '%Y-%m-%d').replace(tzinfo=TZ7).timestamp() * 1000)
LO, HI = d7(a.lo), d7(a.hi)
need = {}
for r in csv.reader(gzip.open(a.cand, 'rt')):
    if r[0] == 'ts' or r[5] != '0': continue
    need.setdefault(r[1], set()).add(int(r[0]))
L.info('symbols=%d slots=%d', len(need), sum(len(v) for v in need.values()))
def get(url):
    for k in range(5):
        try:
            with urllib.request.urlopen(url, timeout=90) as r: return r.read()
        except Exception as e:
            if getattr(e, 'code', None) == 404: return None
            L.warning('retry %s %s', url, e); time.sleep(3 + 5 * k)
    raise RuntimeError(url)
man = {}; nun = 0
uf = open(a.out + '/unavail.csv', 'w'); uf.write('ts,symbol,reason\n')
bf = gzip.open(a.out + '/cand_bars.csv.gz', 'wt'); bf.write('symbol,t,o,h,l,c\n')
for s in sorted(need):
    ts = need[s]; months = sorted({datetime.fromtimestamp(t / 1000, timezone.utc).strftime('%Y-%m') for t in ts})
    got = {}; mi = {}
    for m in months:
        u = f'https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip'
        z = get(u)
        if z is None: mi[m] = 'MISSING'; continue
        ck = get(u + '.CHECKSUM'); sh = hashlib.sha256(z).hexdigest()
        if ck is None or ck.decode().split()[0] != sh: raise SystemExit('CHECKSUM FAIL ' + u)
        mi[m] = dict(sha256=sh, md5=hashlib.md5(z).hexdigest())
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            for nm in zf.namelist():
                for ln in io.TextIOWrapper(zf.open(nm)):
                    p = ln.strip().split(',')
                    if not p[0].isdigit(): continue
                    t = int(p[0])
                    if t in ts and t <= TS_MAX: got[t] = p
    man[s] = mi
    for t in sorted(ts):
        p = got.get(t)
        if p is None: uf.write('%d,%s,NO_KLINE\n' % (t, s)); nun += 1; continue
        if p[2] == p[3] and float(p[7]) == 0.0: uf.write('%d,%s,FLAT_ZERO\n' % (t, s)); nun += 1; continue
        if LO <= t < HI: bf.write('%s,%d,%s,%s,%s,%s\n' % (s, t, p[1], p[2], p[3], p[4]))
    L.info('%s months=%d slots=%d unavail_total=%d', s, len(months), len(ts), nun)
uf.close(); bf.close()
json.dump(dict(lo=a.lo, hi=a.hi, cand=a.cand, months=man, unavail=nun), open(a.out + '/avail_manifest.json', 'w'), indent=1)
L.info('DONE unavail=%d', nun)
