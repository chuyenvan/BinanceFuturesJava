#!/usr/bin/env python3
"""LUOT7 EB25: mkt toan san (Vision UM daily 1m) CHI cho danh sach NGAY UTC (ngay co phut gia cham bac grid cua cum rig/sim giu + ngay
truoc do cho d15). Universe nhu dl_mkt.py. EB24: loai moi dong ts > 2026-09-30 23:59:59 +07 TRUOC khi giu trong bo nho; tu choi ngay UTC
cuoi 2026-09-30 (chua 10-01 +07) tru khi cat. Ghi TUAN TU theo symbol (khong giu toan bo trong RAM).
usage: dl_mkt_days.py <YYYY-MM-DD,...> <out_dir>"""
import gzip, hashlib, io, json, sys, time, urllib.request, zipfile, logging, concurrent.futures as cf
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s'); L = logging.getLogger('mktd')
TZ7 = timezone(timedelta(hours=7)); TS_MAX = int(datetime(2026, 9, 30, 23, 59, 59, tzinfo=TZ7).timestamp() * 1000)
days = sorted(sys.argv[1].split(',')); out = sys.argv[2]
if any(d >= '2026-09-30' for d in days): raise SystemExit('EB24: TU CHOI ngay UTC >= 2026-09-30 (file chua du lieu >= 2026-10-01 +07)')
uni = set()
for s in json.load(open('/home/ubuntu/claude_master/1009/ho26/kaggle/sim-ho26a-bundle/exchange_info_pin.json'))['symbols']:
    if s['symbol'].endswith('USDT'): uni.add(s['symbol'])
for s in json.load(gzip.open('/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz'))['symbols']:
    if s['symbol'].endswith('USDT') and s.get('contractType') == 'PERPETUAL': uni.add(s['symbol'])
def one(s):
    rows = []; info = {}; cut = 0
    for dy in days:
        u = f'https://data.binance.vision/data/futures/um/daily/klines/{s}/1m/{s}-1m-{dy}.zip'
        try: z = urllib.request.urlopen(u, timeout=60).read()
        except Exception: info[dy] = 'MISSING'; continue
        try: ck = urllib.request.urlopen(u + '.CHECKSUM', timeout=60).read().decode().split()[0]
        except Exception: ck = None
        sh = hashlib.sha256(z).hexdigest()
        if ck is not None and ck != sh: raise RuntimeError('CHECKSUM ' + u)
        info[dy] = sh[:16]
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            for nm in zf.namelist():
                for ln in io.TextIOWrapper(zf.open(nm)):
                    p = ln.strip().split(',')
                    if not p[0].isdigit(): continue
                    t = int(p[0])
                    if t > TS_MAX: cut += 1; continue          # EB24: cat TRUOC khi giu
                    rows.append((s, t, p[1], p[2], p[3], p[4], p[7]))
    rows.sort(key=lambda r: r[1])
    return s, rows, info, cut
t0 = time.time(); man = {}; n = 0; ncut = 0
with gzip.open(out + '/mkt.csv.gz', 'wt') as f, cf.ThreadPoolExecutor(8) as ex:
    f.write('symbol,t,o,h,l,c,qv\n')
    for s, rows, info, cut in ex.map(one, sorted(uni)):
        for r in rows: f.write('%s,%d,%s,%s,%s,%s,%s\n' % r)
        n += len(rows); ncut += cut; man[s] = dict(rows=len(rows), days=info)
json.dump(dict(days=days, universe=len(uni), with_data=sum(1 for v in man.values() if v['rows']), rows=n, cut_eb24=ncut,
               seconds=round(time.time() - t0), symbols=man), open(out + '/mkt_manifest.json', 'w'))
L.info('mkt days=%d universe=%d with_data=%d rows=%d cut_eb24=%d sec=%d', len(days), len(uni), sum(1 for v in man.values() if v['rows']), n, ncut, time.time() - t0)
