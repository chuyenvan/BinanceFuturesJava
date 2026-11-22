# Verify E_sim = 35000 + sum calTp(closed, end<=H) + sum_open@H qty*(close_1m[H] - entry), H = last hourly updateBalance before entries.
# Prints only relative ratios (no PnL / balance).
import csv, gzip, logging, collections, sys
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); MIN = 60000; HR = 3600000
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
KL = '/dev/shm/add24/b/kl'
F, UMAX, C0 = 0.0225, 0.6, 35000.0
lo, hi = sys.argv[1], sys.argv[2]
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
rows = list(csv.DictReader(open(PD)))
for r in rows:
    r['t0'] = d7(r['start']); r['t1'] = d7(r['end']); r['m'] = float(r['margin']); r['p'] = float(r['pnl'])
    r['q'] = float(r['quantity']); r['e'] = float(r['entry']); r['s'] = r['sym'] + 'USDT'
close = {}
def cl(s, t):
    if s not in close:
        close[s] = {}
        for x in csv.DictReader(gzip.open(f'{KL}/{s}.csv.gz', 'rt')): close[s][int(x['t'])] = float(x['c'])
    return close[s].get(t)
dev = [r for r in rows if lo <= r['start'][:8] < hi]
bym = collections.defaultdict(list)
for r in dev: bym[r['t0']].append(r)
out = []
for t in sorted(bym):
    H = (t // HR) * HR
    if H == t: H -= HR
    base = sum(r['m'] for r in rows if r['t0'] < t and r['t1'] > t)
    acc = 0.0; es = []
    for r in sorted(bym[t], key=lambda r: -r['m']):
        es.append((r['m'] + (F / UMAX) * (base + acc)) / F); acc += r['m']
    Einf = max(es)
    real = C0 + sum(r['p'] for r in rows if r['t1'] <= H)
    op = [r for r in rows if r['t0'] <= H < r['t1']]
    miss = [r['s'] for r in op if cl(r['s'], H) is None]
    unr = sum(r['q'] * (cl(r['s'], H) - r['e']) for r in op if cl(r['s'], H) is not None)
    Erec = real + unr
    L.info('%s n=%2d open@H=%2d miss_close=%d Einf/Erec-1=%+.2e', datetime.fromtimestamp(t/1000, TZ7).strftime('%m-%d %H:%M'),
           len(bym[t]), len(op), len(miss), Einf / Erec - 1)
