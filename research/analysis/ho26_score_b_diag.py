#!/usr/bin/env python3
"""HO26 scorer B - chan doan tu kiem 1 (sau khi thay eq Σpnl lech result.json ~0,3%).
Khong doi dinh nghia/luat. Kiem: result.equity_final == b+unP dong Update cuoi log; b_final == 35000 + Σpnl dong khong REQUEST;
so chan REQUEST (con mo luc dung sim, pnl = MTM tai 2026-07-01 06:59 +07)."""
import csv, json, logging, os, re, sys
OUT = '/home/ubuntu/kaggle_sim/out'
RX = re.compile(r'Update (\d{8} \d\d:\d\d) => b:\s*(-?\d+).*?unP:\s*(-?\d+)')
logging.basicConfig(level=logging.INFO, format='%(message)s')
res = {}
for c in ('b0', 'k24', 'm2'):
    for fee in ('s', 'b'):
        for s in (42, 7, 13, 21, 99, 123, 777, 2024):
            d = os.path.join(OUT, 'ho26-%s-%s-s%d' % (c, fee, s))
            rj = json.load(open(os.path.join(d, 'result.json')))
            last = None
            for line in open(os.path.join(d, 'logs/sim.out'), errors='replace'):
                m = RX.search(line)
                if m:
                    last = m
            rows = list(csv.DictReader(open(os.path.join(d, 'storage/printDone.csv'))))
            req = [r for r in rows if r['status'] == 'REQUEST']
            real = 35000 + sum(float(r['pnl']) for r in rows if r['status'] != 'REQUEST')
            res[os.path.basename(d)] = dict(
                last_update=last.group(1), last_b_unp=int(last.group(2)) + int(last.group(3)),
                eq_final=rj['equity_final'], b_final=rj['b_final'], eq_eq_last=int(last.group(2)) + int(last.group(3)) == rj['equity_final'],
                n_request=len(req), pnl_request=sum(float(r['pnl']) for r in req), real_nonreq=real,
                diff_bfinal=real - rj['b_final'])
json.dump(res, open(sys.argv[1], 'w'), indent=1)
v = list(res.values())
logging.info('eq_final==last b+unP: %d/%d; max|b_final - (35000+Σpnl non-REQUEST)| = %.2f; REQUEST legs total %d (runs with >0: %d)',
             sum(x['eq_eq_last'] for x in v), len(v), max(abs(x['diff_bfinal']) for x in v),
             sum(x['n_request'] for x in v), sum(x['n_request'] > 0 for x in v))
logging.info('last_update set: %s', sorted({x['last_update'] for x in v}))
