#!/usr/bin/env python3
"""ERRATA4 1b (DEV-B): cong V-TIER. TIER_DIV = (cum sim, phut) thoa MOI dieu kien DCA khac (dca_all.csv: thi truong BIG_DOWN/isDcaAlt
tren market.bin sim, gate entryGate sp=null, shouldDcaGrid voi legCount SIM tai phut do; U < 0,6) ma tier LUOI sim (simtier_code.csv,
code a8690d46 tai moc cap nhat cua sim) va tier THEO GIO (tier_hourly.csv.gz, nhip production) cho quyet dinh chan DCA KHAC nhau.
Cum xet: cum sim co leg0 trong [lo, hi) (cua so cham) - va bao cao them moi cum dang giu trong [lo, hi) (vd GUA leg0 06-25).
EB24: assert moi ts <= 2026-09-30 23:59:59 +07. Khong PnL (E chi noi bo cho U).
usage: vtier.py <lo YYYYMMDD> <hi YYYYMMDD> <out.json> [l5_dir] [simtier_code.csv]"""
import csv, gzip, json, sys, logging
from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); HR = 3600000; TS_MAX = 1790787599999; UMAX = 0.6
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
f7 = lambda ms: datetime.fromtimestamp(ms / 1000, TZ7).strftime('%Y-%m-%d %H:%M')
lo, hi, outp = d7(sys.argv[1] + ' 00:00'), d7(sys.argv[2] + ' 00:00'), sys.argv[3]
L5 = sys.argv[4] if len(sys.argv) > 4 else '/dev/shm/add24/b/l5'
STC = sys.argv[5] if len(sys.argv) > 5 else '/dev/shm/add24/b/l6/simtier_code.csv'
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
# tier luoi sim: moc -> tap KHONG T3 (code a8690d46)
stale = defaultdict(set)
for r in csv.DictReader(open(STC)):
    m = int(r['moment']); assert m <= TS_MAX
    stale[m]
    if r['tier'] != 'TIER_3_SHITCOIN': stale[m].add(r['symbol'])
moms = sorted(stale)
# kiem: moc cap nhat sim = moi leg printDone o phut :00 (2026) - phai trung danh sach moc cua simtier (khong co moc moi trong cua so)
legs = [dict(sym=r['sym'] + 'USDT', s=d7(r['start']), e=d7(r['end']), m=float(r['margin']), pnl=float(r['pnl'])) for r in csv.DictReader(open(PD))]
pd00 = sorted({x['s'] for x in legs if x['s'] % HR == 0 and d7('20260101 00:00') <= x['s'] <= TS_MAX})
moments_ok = pd00 == moms
def stale_t3(s, t):
    i = bisect_right(moms, t)
    return None if not i else (s not in stale[moms[i - 1]])
fresh = {}
with gzip.open(L5 + '/tier_hourly.csv.gz', 'rt') as f:
    for ln in f:
        h, s, rk, n = ln.rstrip().split(','); h = int(h)
        if h > TS_MAX: raise SystemExit('EB24 vi pham ' + ln)
        if h < lo - HR or h >= hi: continue
        fresh.setdefault(h, set())
        if int(rk) < int(int(n) * 0.8): fresh[h].add(s)
def fresh_t3(s, t):
    h = (t // HR) * HR
    return None if h not in fresh else (s not in fresh[h])
close = sorted((x['e'], x['pnl']) for x in legs); cts = [c[0] for c in close]; acc = []; a = 0.0
for c in close: a += c[1]; acc.append(a)
def U(t):
    i = bisect_right(cts, t - 1); E = 35000.0 + (acc[i - 1] if i else 0.0)
    return sum(x['m'] for x in legs if x['s'] <= t < x['e']) / E
cums = {r['cid']: dict(sym=r['sym'], t0=int(r['t0']), te=int(r['tEnd']), dca=[int(a.split(':')[0]) for a in r['legs'].split(';')[1:]])
        for r in csv.DictReader(open(L5 + '/cums.csv'))}
ev = []; nmin = 0; miss = 0
for r in csv.DictReader(open(L5 + '/dca_all.csv')):
    c = cums[r['cid']]; t = int(r['t']); assert t <= TS_MAX
    if not (lo <= t < hi) and not (lo <= c['t0'] < hi): continue
    if t >= hi: continue
    lc = 1 + sum(1 for x in c['dca'] if x < t)
    if not (int(r['mask']) >> (lc - 1)) & 1 or U(t) >= UMAX: continue
    a_, b_ = stale_t3(c['sym'], t), fresh_t3(c['sym'], t)
    nmin += 1
    if a_ is None or b_ is None: miss += 1; continue
    if a_ != b_:
        ev.append(dict(cid=r['cid'], sym=c['sym'], t0=f7(c['t0']), t0_ms=c['t0'], t=f7(t), sim_tier3=a_, hourly_tier3=b_, in_window_leg0=lo <= c['t0'] < hi))
inw = [e for e in ev if e['in_window_leg0']]
excl = sorted({(e['sym'], e['t0_ms']) for e in inw})
out = dict(window=[f7(lo), f7(hi)], moments_sim=[f7(m) for m in moms], moments_match_printDone00=moments_ok,
           dca_eligible_minutes=nmin, no_state=miss, TIER_DIV=len(inw), TIER_DIV_cums=len(excl), exclude=[list(x) for x in excl],
           TIER_DIV_all_held=len(ev), events=ev[:200],
           status=('FAIL_MOMENTS' if not moments_ok else ('PASS_0' if not inw else 'DIV_EXCLUDE')))
json.dump(out, open(outp, 'w'), indent=1)
L.info(json.dumps({k: v for k, v in out.items() if k != 'events'}))
