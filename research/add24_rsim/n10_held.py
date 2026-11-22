#!/usr/bin/env python3
"""ERRATA3 B3 (DEV-B): N10 = sim vao, jar chan bang guard production (legs.csv NOT_BUYABLE + detail) dung phut+symbol (moi entry sim trong FX).
Rig coi symbol N10 la DANG GIU trong dung khoang sim giu cua CHINH cum do (PREDICT: start+1' .. end, excl) => xoa nen symbol do trong
khoang do khoi klines.csv.gz (ticker null => SKIP_AFTER_RANK, khong nap gate - nhu sim giu). usage: n10_held.py <run_dir luot 1> <FX_in> <FX_out>"""
import csv, gzip, json, sys, os, shutil, logging
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); MIN = 60000
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
D, FI, FO = sys.argv[1:4]
se = {(int(r['ts']), r['symbol']): r['level'] for r in csv.DictReader(open(FI + '/sim_entries.csv'))}
n10 = {}
for x in csv.DictReader(open(D + '/legs.csv')):
    k = (int(x['decision_ts']), x['symbol'])
    if x['outcome'] == 'NOT_BUYABLE' and x['detail'] and k in se: n10[k] = x['detail']
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
iv = []
for r in csv.DictReader(open(PD)):
    k = (d7(r['start']), r['sym'] + 'USDT')
    if k in n10:
        f0 = k[0] + (MIN if r['level'] == 'PREDICT_SYMBOL_TRADE' else 0); iv.append((k[1], f0, d7(r['end']), r['level']))
if os.path.exists(FO): shutil.rmtree(FO)
shutil.copytree(FI, FO)
nd = 0; nk = 0
with gzip.open(FO + '/klines.csv.gz', 'wt') as fo:
    for ln in gzip.open(FI + '/klines.csv.gz', 'rt'):
        p = ln.split(',', 2)
        if p[0] != 'symbol' and any(p[0] == s and a <= int(p[1]) < b for s, a, b, _ in iv): nd += 1; continue
        fo.write(ln); nk += 1
json.dump(dict(n10=[(k[0], k[1], v) for k, v in sorted(n10.items())], held=iv, bars_removed=nd, bars_kept=nk - 1),
          open(FO + '/n10_held.json', 'w'), indent=1)
L.info('N10 %d held_iv %d bars_removed %d', len(n10), len(iv), nd)
