#!/usr/bin/env python3
"""[LUOT7 / EB28-EB29] ban sua cua ssz_inputs.py (giu file goc cho A1): (a) vi the HUY NIEM YET (STOP_LOSS_DONE, end >= deliveryDate-1'
theo exinfo fixture): sim KHONG giai phong margin luc end ma o moc gio dau tien H > end + 2 ngay, H khong phai 00:00 UTC
(Simulator:474-480 updateSymbolDeListed: timeUpdate < time - 2*DAY; nhanh nua dem UTC khong goi) -> margin con trong M_run va
equity tinh MTM q*(tp - e) toi luc do, pnl ghi so luc dong that; (b) thu tu leg BIG_DOWN trong phut = thu tu duyet HashSet<Short>
symbol2BUY cua sim (Simulator:350-376: bucket = id & (cap-1), cap theo resize HashMap; id = mapper ov_idtostr.tsv HO5), roi PREDICT.
S-SZ inputs: for every sim cum (leg0) with start in [lo,hi): E_sim(t), U_sim(t) per verified formula, sim processing order
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
import json as _json
_dd = {s['symbol']: int(s.get('deliveryDate') or 0) for s in _json.load(open(fx + '/exinfo.json'))['symbols']}
_ids = {}
for _ln in open('/home/ubuntu/claude_master/w3/ho5/mapper/ov_idtostr.tsv', encoding='utf-8'):
    _p = _ln.rstrip('\n').split('\t')
    if len(_p) == 2 and _p[0].isdigit(): _ids[_p[1]] = int(_p[0])
DAY = 86400000
def _rel(end):   # moc gio dau tien H > end + 2 ngay, H % 1h == 0, H % DAY != 0 (UTC)
    H = ((end + 2 * DAY) // HR + 1) * HR
    while H % DAY == 0: H += HR
    return H
def _hs_order(ids):   # thu tu duyet java.util.HashSet<Short> sau khi add lan luot (HashMap resize giu thu tu tuong doi)
    cap = 16; bk = [[] for _ in range(cap)]; n = 0
    for i in ids:
        bk[i & (cap - 1)].append(i); n += 1
        if n > 0.75 * cap:
            cap *= 2; nb = [[] for _ in range(cap)]
            for b in bk:
                for x in b: nb[x & (cap - 1)].append(x)
            bk = nb
    return [x for b in bk for x in b]
for r in rows:
    r['t0'] = d7(r['start']); r['t1'] = d7(r['end']); r['m'] = float(r['margin']); r['p'] = float(r['pnl'])
    r['q'] = float(r['quantity']); r['e'] = float(r['entry']); r['s'] = r['sym'] + 'USDT'
    r['dca'] = r['level'] == 'DCA_LEVEL1'
    r['tp'] = float(r['tp']) if r['tp'] not in ('', 'null') else None
    dd = _dd.get(r['s'], 0)
    r['delist'] = r['status'] == 'STOP_LOSS_DONE' and 0 < dd < 4000000000000 and r['t1'] >= dd - 60000
    r['t1m'] = _rel(r['t1']) if r['delist'] else r['t1']   # thoi diem sim giai phong margin + ghi so pnl
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
    real = C0 + sum(r['p'] for r in rows if r['t1m'] <= H)
    op = [r for r in rows if r['t0'] <= H < r['t1']]
    assert all(cl(r['s'], H) is not None for r in op), 'missing close at H'
    dl = [r for r in rows if r['delist'] and r['t1'] <= H < r['t1m']]   # huy niem yet: chua dong trong sim -> MTM tai gia cuoi (tp)
    E = real + sum(r['q'] * (cl(r['s'], H) - r['e']) for r in op) + sum(r['q'] * (r['tp'] - r['e']) for r in dl)
    base = sum(r['m'] for r in rows if r['t0'] < t and r['t1m'] > t)
    bd = sorted([r for r in bym[t] if r['level'] == 'BIG_DOWN'], key=lambda r: rank.get((t, r['s']), 999))
    bo = {i: k for k, i in enumerate(_hs_order([_ids.get(r['s'], 9999) for r in bd]))}
    order = sorted(bym[t], key=lambda r: (0, bo.get(_ids.get(r['s'], 9999), 999)) if r['level'] == 'BIG_DOWN' else (1, rank.get((t, r['s']), 999)))
    if dl: L.info('delist_held t=%d %s', t, [r['s'] for r in dl])
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
