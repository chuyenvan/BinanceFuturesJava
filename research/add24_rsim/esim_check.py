# ADD24 R-SIM DEV: infer E_sim from leg0 margins (linear in E) - no PnL printed.
import csv, sys, logging, collections
from datetime import datetime
logging.basicConfig(level=logging.INFO, format='%(message)s')
L = logging.getLogger()
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
LO, HI = '20260401', '20260615'
F, UMAX = 0.0225, 0.6
def ts(s): return datetime.strptime(s, '%Y%m%d %H:%M')
rows = list(csv.DictReader(open(PD)))
for r in rows:
    r['t0'] = ts(r['start']); r['t1'] = ts(r['end']); r['m'] = float(r['margin'])
    r['dca'] = abs(float(r['entry']) - float(r['lastentry'])) > 1e-12
dev = [r for r in rows if LO <= r['start'][:8] < HI]
L.info('dev=%d dca_in_dev=%d dca_all_2026=%d', len(dev), sum(r['dca'] for r in dev),
       sum(r['dca'] for r in rows if r['start'][:4] == '2026' and r['start'][:8] < HI))
bymin = collections.defaultdict(list)
for r in dev: bymin[r['t0']].append(r)
mode = sys.argv[1] if len(sys.argv) > 1 else 'close_first'
for t in sorted(bymin):
    ents = sorted(bymin[t], key=lambda r: -r['m'])  # hypothesis: order = descending margin
    if mode == 'close_first':
        base = sum(r['m'] for r in rows if r['t0'] < t and r['t1'] > t)
    else:
        base = sum(r['m'] for r in rows if r['t0'] < t and r['t1'] >= t)
    acc = 0.0; es = []
    for r in ents:
        M = base + acc
        E = (r['m'] + (F / UMAX) * M) / F
        es.append(E); acc += r['m']
    spread = (max(es) - min(es)) / es[0]
    L.info('%s n=%2d lvl=%s U0=%.4f Einf_relspread=%.2e', t, len(ents),
           ','.join(sorted(set(r['level'][:3] for r in ents))), base / es[0], spread)
