#!/usr/bin/env python3
"""LUOT7: cap (symbol, H) can gia MTM cho E_sim moi phut co leg sim trong [lo,hi) (H = moc gio updateBalance truoc t)."""
import csv, sys, collections
from datetime import datetime, timezone, timedelta
TZ7 = timezone(timedelta(hours=7)); HR = 3600000
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
lo, hi, out = sys.argv[1:4]
rows = list(csv.DictReader(open('/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv')))
for r in rows: r['t0'] = d7(r['start']); r['t1'] = d7(r['end'])
ts = sorted({r['t0'] for r in rows if lo <= r['start'][:8] < hi})
P = set()
for t in ts:
    H = (t // HR) * HR
    if H == t: H -= HR
    for r in rows:
        if r['t0'] <= H < r['t1']: P.add((r['sym'] + 'USDT', H))
with open(out, 'w') as f:
    f.write('symbol,t\n')
    for s, h in sorted(P): f.write('%s,%d\n' % (s, h))
print('pairs', len(P), 'minutes', len(ts))
