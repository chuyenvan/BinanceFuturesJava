#!/usr/bin/env python3
"""LUOT7 3c/N11: E_sim tai moi phut co leg sim (cong thuc ssz_inputs) voi gia MTM = (a) Vision klines, (b) ticker SIM (tk26);
so voi E suy nguoc tu leg PREDICT sim (E_inf = (m + F*M_run/U_MAX)/F, cum >= 3 leg trung 1e-4). Chi in sai lech TUONG DOI. Khong PnL."""
import csv, gzip, collections, statistics, os, sys
from datetime import datetime, timezone, timedelta
TZ7 = timezone(timedelta(hours=7)); HR = 3600000
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
f7 = lambda ms: datetime.fromtimestamp(ms / 1000, TZ7).strftime('%m-%d %H:%M')
FX, KL, SC = sys.argv[1:4]
rows = list(csv.DictReader(open('/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv')))
for r in rows:
    r['t0'] = d7(r['start']); r['t1'] = d7(r['end']); r['p'] = float(r['pnl']); r['q'] = float(r['quantity']); r['e'] = float(r['entry']); r['s'] = r['sym'] + 'USDT'
sim = {(r['symbol'], int(r['t'])): float(r['close']) for r in csv.DictReader(open(SC)) if r['close']}
vc = {}
def vis(s, t):
    if s not in vc: vc[s] = {int(x['t']): float(x['c']) for x in csv.DictReader(gzip.open(f'{KL}/{s}.csv.gz', 'rt'))}
    return vc[s].get(t)
g = collections.defaultdict(list)
for r in csv.DictReader(open(FX + '/ssz_in.csv')): g[int(r['ts'])].append(r)
for t in sorted(g):
    rs = [r for r in g[t] if r['level'] == 'PREDICT_SYMBOL_TRADE']
    Ei = [(float(r['margin_sim']) + 0.0375 * float(r['M_run'])) / 0.0225 for r in rs]
    H = (t // HR) * HR
    if H == t: H -= HR
    real = 35000 + sum(r['p'] for r in rows if r['t1'] <= H)
    op = [r for r in rows if r['t0'] <= H < r['t1']]
    Ev = real + sum(r['q'] * (vis(r['s'], H) - r['e']) for r in op)
    miss = [r['s'] for r in op if (r['s'], H) not in sim]
    Es = real + sum(r['q'] * (sim.get((r['s'], H), vis(r['s'], H)) - r['e']) for r in op)
    big = sorted(((abs(r['q'] * (sim.get((r['s'], H), 0) - vis(r['s'], H))) / Ev, r['s'], round(100 * (sim.get((r['s'], H), 0) / vis(r['s'], H) - 1), 2)) for r in op if (r['s'], H) in sim), reverse=True)[:2]
    if len(Ei) >= 3:
        e0 = statistics.median(Ei)
        print(f7(t), 'nPRE', len(rs), 'E_inf_spread %.1e' % ((max(Ei) - min(Ei)) / e0), 'rel(E_vision/E_inf-1) %+.4f' % (Ev / e0 - 1),
              'rel(E_simtk/E_inf-1) %+.5f' % (Es / e0 - 1), 'open', len(op), 'miss_simtk', len(miss), 'top_px_diff', [(b[1], b[2]) for b in big])
    else:
        print(f7(t), 'nPRE', len(rs), '(<3 leg PREDICT) rel(E_simtk/E_vision-1) %+.5f' % (Es / Ev - 1))
