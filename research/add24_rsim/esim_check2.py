# compare inferred E (max within minute) vs 35000 + realized(<=H) when no cum open at H. Prints only ratios.
import csv, logging, collections
from datetime import datetime, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
F, UMAX, C0 = 0.0225, 0.6, 35000.0
def ts(s): return datetime.strptime(s, '%Y%m%d %H:%M')
rows = list(csv.DictReader(open(PD)))
for r in rows: r['t0']=ts(r['start']); r['t1']=ts(r['end']); r['m']=float(r['margin']); r['p']=float(r['pnl'])
dev = [r for r in rows if '20260401' <= r['start'][:8] < '20260615']
bymin = collections.defaultdict(list)
for r in dev: bymin[r['t0']].append(r)
for t in sorted(bymin):
    H = t.replace(minute=0)
    if t.minute == 0: H -= timedelta(hours=1)
    base = sum(r['m'] for r in rows if r['t0'] < t and r['t1'] > t)
    acc = 0.0; es = []
    for r in sorted(bymin[t], key=lambda r: -r['m']):
        es.append((r['m'] + (F/UMAX)*(base+acc))/F); acc += r['m']
    Einf = max(es)
    for lab, Hx in (('H', H), ('Hm1', H - timedelta(hours=1))):
        real = C0 + sum(r['p'] for r in rows if r['t1'] <= Hx)
        nopen = sum(1 for r in rows if r['t0'] <= Hx and r['t1'] > Hx)
        L.info('%s %s nopen=%d Einf/Erealized-1=%+.3e', t, lab, nopen, Einf/real - 1)
