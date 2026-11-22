#!/usr/bin/env python3
"""mkt toan thi truong (Vision UM daily 1m) cho [lo, hi) (+07, 'YYYYmmdd HH:MM'), universe = USDT PERPETUAL trong exchange_info_pin sim (HO-bundle)
U exchangeInfo 20261027; loc truoc khi ghi; <= 2026-09-30 23:59 +07. Out: <out>/mkt.csv.gz (symbol,t,o,h,l,c,qv) + mkt_manifest.json"""
import gzip, hashlib, io, json, sys, urllib.request, zipfile, logging, concurrent.futures as cf
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s'); L = logging.getLogger('mkt')
TZ7 = timezone(timedelta(hours=7)); TS_MAX = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
lo, hi, out = sys.argv[1], sys.argv[2], sys.argv[3]
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
LO, HI = d7(lo), min(d7(hi), TS_MAX + 60000)
uni = set()
pin = json.load(open('/home/ubuntu/claude_master/1009/ho26/kaggle/sim-ho26a-bundle/exchange_info_pin.json'))
for s in pin['symbols']:
    if s['symbol'].endswith('USDT'): uni.add(s['symbol'])
ei = json.load(gzip.open('/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz'))
for s in ei['symbols']:
    if s['symbol'].endswith('USDT') and s.get('contractType') == 'PERPETUAL': uni.add(s['symbol'])
days = []
d = datetime.fromtimestamp(LO / 1000, timezone.utc).date()
while datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000 < HI:
    days.append(d.isoformat()); d += timedelta(days=1)
def one(s):
    rows = []; info = {}
    for dy in days:
        u = f'https://data.binance.vision/data/futures/um/daily/klines/{s}/1m/{s}-1m-{dy}.zip'
        try: z = urllib.request.urlopen(u, timeout=60).read()
        except Exception as e:
            info[dy] = 'MISSING'; continue
        try:
            ck = urllib.request.urlopen(u + '.CHECKSUM', timeout=60).read().decode().split()[0]
        except Exception: ck = None
        sh = hashlib.sha256(z).hexdigest()
        if ck is not None and ck != sh: raise RuntimeError('CHECKSUM ' + u)
        info[dy] = sh[:16]
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            for nm in zf.namelist():
                for ln in io.TextIOWrapper(zf.open(nm)):
                    p = ln.strip().split(',')
                    if p[0].isdigit() and LO <= int(p[0]) < HI and int(p[0]) <= TS_MAX: rows.append((s, int(p[0]), p[1], p[2], p[3], p[4], p[7]))
    return s, rows, info
allrows = []; man = {}
with cf.ThreadPoolExecutor(8) as ex:
    for s, rows, info in ex.map(one, sorted(uni)):
        allrows += rows; man[s] = dict(rows=len(rows), days=info)
allrows.sort(key=lambda r: (r[0], r[1]))
with gzip.open(out + '/mkt.csv.gz', 'wt') as f:
    f.write('symbol,t,o,h,l,c,qv\n')
    for r in allrows: f.write('%s,%d,%s,%s,%s,%s,%s\n' % r)
json.dump(dict(lo=lo, hi=hi, universe=len(uni), with_data=sum(1 for v in man.values() if v['rows']), rows=len(allrows), symbols=man), open(out + '/mkt_manifest.json', 'w'))
L.info('mkt universe=%d with_data=%d rows=%d', len(uni), sum(1 for v in man.values() if v['rows']), len(allrows))
