#!/usr/bin/env python3
"""DEV-2: suy thoi diem leg DAU cua cum DCA sim (printDone chi co cum gop: start = leg DCA, margin/quantity tong, entry = gia TB).
Ung vien T0 = phut symbol nam trong top-24 ung vien sim (cand.csv.gz) truoc start; p0 = close(T0) (Vision), p1 = close(start).
q0 = (M - Q*p1)/(p0 - p1) phai la boi so minQty (pin sim) va 0 < q0 < Q; them dieu kien DCA: p1/p0 - 1 <= level1. Khong in PnL."""
import csv, gzip, io, json, sys, urllib.request, zipfile, hashlib
from datetime import datetime, timezone, timedelta
TZ7 = timezone(timedelta(hours=7)); MIN = 60000
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
f7 = lambda ms: datetime.fromtimestamp(ms / 1000, TZ7).strftime('%m-%d %H:%M')
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
cums = [r for r in csv.DictReader(open(PD)) if r['level'] == 'DCA_LEVEL1' and '20260101' <= r['start'][:8] < '20260401']
OUT = '/dev/shm/add24/b/dev2/kl'
res = {}
for r in cums:
    s = r['sym'] + 'USDT'; ts = d7(r['start']); Q = float(r['quantity']); M = float(r['margin'])
    bars = {}
    for m in ('2026-01', '2026-02'):
        u = f'https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip'
        try: z = urllib.request.urlopen(u, timeout=90).read()
        except Exception as e: continue
        ck = urllib.request.urlopen(u + '.CHECKSUM', timeout=60).read().decode().split()[0]
        assert ck == hashlib.sha256(z).hexdigest()
        with zipfile.ZipFile(io.BytesIO(z)) as zf:
            for nm in zf.namelist():
                for ln in io.TextIOWrapper(zf.open(nm)):
                    p = ln.strip().split(',')
                    if p[0].isdigit(): bars[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]), float(p[4]))
    with gzip.open(f'{OUT}/{s}.csv.gz', 'wt') as f:
        f.write('symbol,t,o,h,l,c\n')
        for t in sorted(bars):
            if t <= d7('20260630 23:59'): f.write('%s,%d,%s,%s,%s,%s\n' % ((s, t) + tuple(repr(v) for v in bars[t])))
    p1 = bars[ts][3]
    cand = []
    for x in csv.reader(gzip.open('/dev/shm/add24/b/fx_dev/cand.csv.gz', 'rt')):
        if x[0] == 'ts' or x[1] != s: continue
        t = int(x[0])
        if t >= ts: break
        if t < ts - 30 * 24 * 60 * MIN or t not in bars: continue
        p0 = bars[t][3]
        if p0 <= p1: continue
        q0 = (M - Q * p1) / (p0 - p1)
        if 0 < q0 < Q:
            cand.append((abs(q0 - round(q0)), t, p0, q0, p1 / p0 - 1))
    cand.sort()
    res[s] = dict(start=r['start'], status=r['status'], hours=r['time_order'], Q=Q, n_cand_minutes=len(cand),
                  best=[(f7(t), round(q0, 4), round(dd, 4), round(err, 6)) for err, t, p0, q0, dd in cand[:6]])
print(json.dumps(res, indent=1))
