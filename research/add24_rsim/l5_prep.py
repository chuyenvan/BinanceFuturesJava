#!/usr/bin/env python3
"""LUOT5 1c prep (DEV-B): cums.csv (cum sim cham 2026-01-01..09-30), market.csv (sim market.bin), p15.csv (pred_2026.bin). Khong PnL."""
import csv, struct, logging, numpy as np
from collections import defaultdict
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); S = '/dev/shm/add24/b/l5'
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
LO = int(datetime(2026, 1, 1, tzinfo=TZ7).timestamp() * 1000); HI = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
g = defaultdict(list)
for r in csv.DictReader(open(PD)): g[(r['sym'], r['end'])].append(r)
n = 0
with open(S + '/cums.csv', 'w') as f:
    f.write('cid,sym,first,t0,tEnd,nlegs,lv0,legs\n')
    for (sym, end), rs in sorted(g.items(), key=lambda kv: min(d7(x['start']) for x in kv[1])):
        rs.sort(key=lambda x: d7(x['start'])); t0 = d7(rs[0]['start']); te = min(d7(end), HI + 60000)
        if te <= LO or t0 > HI: continue
        cid = '%s@%d' % (sym, t0)
        f.write('%s,%sUSDT,%s,%d,%d,%d,%s,%s\n' % (cid, sym, rs[0]['entry'], t0, te, len(rs), rs[0]['level'], ';'.join('%d:%s:%s' % (d7(x['start']), x['level'], x['margin']) for x in rs)))
        n += 1
L.info('cums %d', n)
raw = open('/home/ubuntu/claude_master/w3/ho5/a3/data26/ds/pred_2026.bin', 'rb').read(); m = struct.unpack('>i', raw[:4])[0]
pr = np.frombuffer(raw[4:], dtype=np.dtype([('ts', '>i8'), ('p15', '>f4'), ('risk', '>f4')]), count=m)
pr = pr[pr['ts'] <= HI]
with open(S + '/p15.csv', 'w') as f:
    f.write('ts,p15\n')
    for t, p in zip(pr['ts'], pr['p15']): f.write('%d,%r\n' % (t, float(p)))
a = np.load(S + '/market26.npy'); a = a[a['ts'] <= HI]
with open(S + '/market.csv', 'w') as f:
    f.write('ts,down,up,down15\n')
    for r in a: f.write('%d,%r,%r,%r\n' % (r['ts'], float(r['d']), float(r['u']), float(r['d15'])))
L.info('p15 %d [%d..%d] market %d', len(pr), pr['ts'].min(), pr['ts'].max(), len(a))
