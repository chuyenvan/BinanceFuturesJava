#!/usr/bin/env python3
"""S-SZ inputs: for every sim cum (leg0) with start in [lo,hi): E_sim(t), U_sim(t) per verified formula, sim processing order
inside minute (BIG_DOWN first, then PREDICT by selector rank from cand.csv.gz). Writes ssz_in.csv (no PnL columns; E/U are
normalisation inputs, written to tmpfs only, never printed). Also prints a numpy REF precheck (relative error only)."""
import csv, gzip, logging, sys, collections
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); HR = 3600000
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
KL = __import__('os').environ.get('KL_DIR', '/dev/shm/add24/b/kl'); C0 = 35000.0
lo, hi, fx = sys.argv[1], sys.argv[2], sys.argv[3]
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
rows = list(csv.DictReader(open(PD)))
for r in rows:
    r['t0'] = d7(r['start']); r['t1'] = d7(r['end']); r['m'] = float(r['margin']); r['p'] = float(r['pnl'])
    r['q'] = float(r['quantity']); r['e'] = float(r['entry']); r['s'] = r['sym'] + 'USDT'
    r['dca'] = r['level'] == 'DCA_LEVEL1'
rank = {}
for x in csv.reader(gzip.open(fx + '/cand.csv.gz', 'rt')):
    if x[0] != 'ts' and x[6] == '1': rank[(int(x[0]), x[1])] = int(x[3])
close = {}
def cl(s, t):
    if s not in close:
        close[s] = {int(x['t']): float(x['c']) for x in csv.DictReader(gzip.open(f'{KL}/{s}.csv.gz', 'rt'))}
    return close[s].get(t)
win = [r for r in rows if lo <= r['start'][:8] < hi]
bym = collections.defaultdict(list)
for r in win: bym[r['t0']].append(r)
out = []; errs = []
for t in sorted(bym):
    H = (t // HR) * HR
    if H == t: H -= HR
    real = C0 + sum(r['p'] for r in rows if r['t1'] <= H)
    op = [r for r in rows if r['t0'] <= H < r['t1']]
    assert all(cl(r['s'], H) is not None for r in op), 'missing close at H'
    E = real + sum(r['q'] * (cl(r['s'], H) - r['e']) for r in op)
    base = sum(r['m'] for r in rows if r['t0'] < t and r['t1'] > t)
    order = sorted(bym[t], key=lambda r: (0 if r['level'] == 'BIG_DOWN' else 1, rank.get((t, r['s']), 999)))
    acc = 0.0
    for k, r in enumerate(order):
        U = (base + acc) / E
        ref = 0.0225 * E * (1 - U / 0.6)
        out.append((t, r['s'], r['level'], k, E, U, r['m'], int(r['dca']), base + acc, r['e'], r['q']))
        errs.append(abs(r['m'] - ref) / r['m']); acc += r['m']
with open(fx + '/ssz_in.csv', 'w') as f:
    f.write('ts,symbol,level,ord_in_min,E_sim,U_sim,margin_sim,dca_merged,M_run,entry_sim,qty_sim\n')
    for o in out: f.write('%d,%s,%s,%d,%.9g,%.12g,%.9g,%d,%.9g,%.9g,%.9g\n' % o)
errs.sort(); n = len(errs)
L.info('cums=%d REFprecheck rel_err: max=%.2e p90=%.2e share<=1e-3=%.3f share<=5e-3=%.3f dca_merged=%d', n, errs[-1],
       errs[int(0.9 * (n - 1))], sum(e <= 1e-3 for e in errs) / n, sum(e <= 5e-3 for e in errs) / n, sum(o[7] for o in out))
