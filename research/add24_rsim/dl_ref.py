#!/usr/bin/env python3
"""BTCUSDT 1m (ref symbol KillSwitch C1) cho [lo, end) (+07), loc truoc khi ghi, <= 2026-09-30 23:59 +07. Out: <out>/BTCUSDT.csv.gz + ref_manifest.json"""
import gzip, hashlib, io, json, sys, urllib.request, zipfile, logging
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s'); L = logging.getLogger('ref')
TZ7 = timezone(timedelta(hours=7)); TS_MAX = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
lo, end, out = sys.argv[1], sys.argv[2], sys.argv[3]
d7 = lambda s: int(datetime.strptime(s, '%Y-%m-%d').replace(tzinfo=TZ7).timestamp() * 1000)
LO, END = d7(lo), min(d7(end), TS_MAX + 60000)
s = 'BTCUSDT'; man = {}; rows = []
m = datetime.fromtimestamp(LO / 1000, timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
while m.timestamp() * 1000 < END:
    ym = m.strftime('%Y-%m'); u = f'https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{ym}.zip'
    z = urllib.request.urlopen(u, timeout=90).read(); ck = urllib.request.urlopen(u + '.CHECKSUM', timeout=60).read().decode().split()[0]
    sh = hashlib.sha256(z).hexdigest(); assert ck == sh, u
    man[ym] = dict(sha256=sh, md5=hashlib.md5(z).hexdigest())
    with zipfile.ZipFile(io.BytesIO(z)) as zf:
        for nm in zf.namelist():
            for ln in io.TextIOWrapper(zf.open(nm)):
                p = ln.strip().split(',')
                if p[0].isdigit() and LO <= int(p[0]) < END and int(p[0]) <= TS_MAX: rows.append((int(p[0]), p[1], p[2], p[3], p[4], p[7]))
    m = (m + timedelta(days=32)).replace(day=1)
rows.sort()
with gzip.open(out + '/BTCUSDT.csv.gz', 'wt') as f:
    f.write('symbol,t,o,h,l,c,qv\n')
    for r in rows: f.write('BTCUSDT,%d,%s,%s,%s,%s,%s\n' % r)
exp = (END - LO) // 60000
json.dump(dict(months=man, rows=len(rows), expected=exp, ts_min=rows[0][0], ts_max=rows[-1][0]), open(out + '/ref_manifest.json', 'w'), indent=1)
L.info('BTC rows=%d expected=%d', len(rows), exp)
