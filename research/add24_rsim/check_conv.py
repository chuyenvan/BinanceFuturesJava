# verify converter vs printDone: score==symbolPred, p15==pred15m (float32 bitwise), entry not held. No PnL.
import csv, gzip, logging, numpy as np, sys
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); fx = sys.argv[1]; lo, hi = sys.argv[2], sys.argv[3]
def d7(s): return int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp()*1000)
pd = [r for r in csv.DictReader(open('/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv')) if lo <= r['start'][:8] < hi]
want = {(d7(r['start']), r['sym']+'USDT'): r for r in pd}
f32 = lambda x: np.float32(float(x)) if x not in ('null','',None) else None
ok_sc = ok_p = bad_h = n = 0; bad = []
for row in csv.DictReader(gzip.open(fx + '/cand.csv.gz', 'rt')):
    if row['sim_entry'] != '1': continue
    k = (int(row['ts']), row['symbol']); r = want[k]; n += 1
    if f32(row['score']) == f32(r['symbolPred']): ok_sc += 1
    else: bad.append(('score', k, row['score'], r['symbolPred']))
    if f32(row['p15']) == f32(r['pred15m']): ok_p += 1
    else: bad.append(('p15', k, row['p15'], r['pred15m']))
    if row['held_sim'] == '1': bad_h += 1
L.info('entries_in_cand=%d score_eq=%d p15_eq=%d held_flag_on_entry=%d', n, ok_sc, ok_p, bad_h)
for b in bad[:10]: L.info('MISMATCH %s', b)
