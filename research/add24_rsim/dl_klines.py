#!/usr/bin/env python3
"""Download Vision UM 1m klines (monthly zips) for printDone symbols; FILTER to [start-2h, end+2h] per cum (cap 2026-09-30 23:59 +07)
BEFORE writing. Verifies Vision .CHECKSUM sha256. Writes /dev/shm/add24/b/kl/<SYM>.csv.gz (symbol,t,o,h,l,c,qv) + kl_manifest.json."""
import csv, gzip, hashlib, io, json, logging, os, sys, time, urllib.request, zipfile
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s'); L = logging.getLogger('dl')
TZ7 = timezone(timedelta(hours=7)); MIN = 60000; H2 = 2 * 3600000
TS_MAX = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
OUT = os.environ.get('KL_OUT', '/dev/shm/add24/b/kl'); os.makedirs(OUT, exist_ok=True)
def d7(s): return int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
END_SEL = d7(os.environ.get('KL_END', '20260916 00:00')); BEG_SEL = d7(os.environ.get('KL_BEG', '20260315 00:00'))
iv = {}
for r in csv.DictReader(open(PD)):
    t0, t1 = d7(r['start']), d7(r['end'])
    if t0 < END_SEL and t1 >= BEG_SEL:   # DEV + OW1 cums and cums open across them (symbol list only, no PnL read)
        iv.setdefault(r['sym'] + 'USDT', []).append((t0 - H2, min(t1 + H2, TS_MAX)))
def merge(xs):
    xs = sorted(xs); out = [list(xs[0])]
    for a, b in xs[1:]:
        if a <= out[-1][1] + MIN: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out
man = {}
def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r: return r.read()
        except Exception as e:
            if getattr(e, 'code', None) == 404: return None
            L.warning('retry %s %s', url, e); time.sleep(3 + 5 * k)
    raise RuntimeError(url)
syms = sorted(iv)
L.info('symbols=%d', len(syms))
for s in syms:
    if os.path.exists(f'{OUT}/{s}.csv.gz') and s in man: continue
    ivs = merge(iv[s]); months = set()
    for a, b in ivs:
        d = datetime.fromtimestamp(a / 1000, timezone.utc).replace(day=1, hour=0, minute=0, second=0)
        e = datetime.fromtimestamp(b / 1000, timezone.utc)
        while d <= e:
            months.add(d.strftime('%Y-%m')); d = (d + timedelta(days=32)).replace(day=1)
    rows = []; zinfo = {}
    for m in sorted(months):
        u = f'https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip'
        z = get(u)
        if z is None: zinfo[m] = 'MISSING'; continue
        ck = get(u + '.CHECKSUM'); sh = hashlib.sha256(z).hexdigest()
        ok = ck is not None and ck.decode().split()[0] == sh
        zinfo[m] = dict(sha256=sh, md5=hashlib.md5(z).hexdigest(), checksum_ok=ok)
        if not ok: raise SystemExit(f'CHECKSUM FAIL {u}')
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            for nm in zf.namelist():
                for ln in io.TextIOWrapper(zf.open(nm)):
                    p = ln.strip().split(',')
                    if not p[0].isdigit(): continue
                    t = int(p[0])
                    if t > TS_MAX: continue                      # V3: never keep > 2026-09-30 23:59 +07
                    if any(a <= t <= b for a, b in ivs): rows.append((t, p[1], p[2], p[3], p[4], p[7]))
    rows.sort()
    assert all(r[0] <= TS_MAX for r in rows)
    with gzip.open(f'{OUT}/{s}.csv.gz', 'wt') as f:
        f.write('symbol,t,o,h,l,c,qv\n')
        for r in rows: f.write('%s,%d,%s,%s,%s,%s,%s\n' % ((s,) + r))
    exp = sum((b - a) // MIN + 1 for a, b in ivs)
    man[s] = dict(intervals=ivs, months=zinfo, rows=len(rows), expected_minutes=exp,
                  ts_min=rows[0][0] if rows else None, ts_max=rows[-1][0] if rows else None,
                  file_md5=hashlib.md5(open(f'{OUT}/{s}.csv.gz', 'rb').read()).hexdigest())
    L.info('%s months=%d rows=%d exp=%d', s, len(months), len(rows), exp)
    json.dump(man, open(OUT + '_manifest.json', 'w'), indent=1)
L.info('DONE symbols=%d', len(man))
