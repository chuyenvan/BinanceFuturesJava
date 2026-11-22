#!/usr/bin/env python3
"""Assemble rig fixture for Add24RsimMain from conv_rsim.py + dl_avail.py + dl_klines.py outputs. Gates V2/V3 (auto, abort).
Writes into --fx: klines.csv.gz, warm.csv.gz, follow.csv, mkt.csv.gz (header), manifest.json, exinfo.json; fx_check.json."""
import argparse, csv, gzip, hashlib, json, logging, os, collections
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s'); L = logging.getLogger('fx')
TZ7 = timezone(timedelta(hours=7)); MIN = 60000; HR = 3600000
TS_MAX = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
EXI = '/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz'
ap = argparse.ArgumentParser(); ap.add_argument('--fx'); ap.add_argument('--kl'); ap.add_argument('--klref', default=''); ap.add_argument('--end'); ap.add_argument('--patch_settling', action='store_true'); ap.add_argument('--warm_from', default=''); ap.add_argument('--mkt', default=''); ap.add_argument('--unavail_extra', default=''); ap.add_argument('--pin', default=''); ap.add_argument('--end_pad', action='store_true'); a = ap.parse_args()
man0 = json.load(open(a.fx + '/manifest_conv.json')); W0, LO, HI = man0['W0'], man0['LO'], man0['HI']
END = int(datetime.strptime(a.end, '%Y-%m-%d').replace(tzinfo=TZ7).timestamp() * 1000)
assert HI <= END <= TS_MAX + MIN
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()
un = set()
for r in csv.DictReader(open(a.fx + '/unavail.csv')): un.add((int(r['ts']), r['symbol']))
if a.unavail_extra:
    for r in csv.DictReader(open(a.unavail_extra)):
        if int(r['ts']) < LO: un.add((int(r['ts']), r['symbol']))
# warm buffer rows (fed in sim before START): non-held, available
WF = int(datetime.strptime(a.warm_from, '%Y-%m-%d').replace(tzinfo=TZ7).timestamp() * 1000) if a.warm_from else W0
def qk(t):
    d = datetime.fromtimestamp(t / 1000, TZ7); return '%dQ%d' % (d.year, (d.month - 1) // 3 + 1)
fedq = collections.Counter()
nw = 0; maxw = 0; minw = None
with gzip.open(a.fx + '/warm.csv.gz', 'wt') as fw:
    fw.write('ts,sp,p15\n')
    for r in csv.reader(gzip.open(a.fx + '/cand.csv.gz', 'rt')):
        if r[0] == 'ts': continue
        t = int(r[0])
        if t >= LO: break
        if r[5] != '0' or (t, r[1]) in un: continue
        fedq[qk(t)] += 1
        if t < WF: continue
        fw.write('%d,%s,%s\n' % (t, r[2], r[4])); nw += 1; maxw = max(maxw, t); minw = t if minw is None else minw
assert maxw < LO
# fed count per quarter (validation vs sim [GATE-RATIO] seen per quarter)
q2 = int(datetime(2026, 4, 1, tzinfo=TZ7).timestamp() * 1000)
fedQ1 = 0
for r in csv.reader(gzip.open(a.fx + '/cand.csv.gz', 'rt')):
    if r[0] == 'ts': continue
    t = int(r[0])
    if t < q2 and r[5] == '0' and (t, r[1]) not in un: fedQ1 += 1
# skipFull approx (U with realized-only E) in warm-up window
rows = list(csv.DictReader(open(PD)))
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
for r in rows: r['t0'] = d7(r['start']); r['t1'] = d7(r['end']); r['m'] = float(r['margin']); r['p'] = float(r['pnl'])
ev = sorted([(r['t0'], r['m']) for r in rows] + [(r['t1'], -r['m']) for r in rows])
umax = 0.0; mrun = 0.0; i = 0; closes = sorted((r['t1'], r['p']) for r in rows); j = 0; real = 35000.0
for t in range(W0, HI, HR):
    while i < len(ev) and ev[i][0] <= t: mrun += ev[i][1]; i += 1
    while j < len(closes) and closes[j][0] <= t: real += closes[j][1]; j += 1
    umax = max(umax, mrun / real)
# klines: sim symbols (kl) + candidate bars
seen = set(); nk = 0; tmax = 0
with gzip.open(a.fx + '/klines.csv.gz', 'wt') as fk:
    fk.write('symbol,t,o,h,l,c\n')
    srcs = [os.path.join(a.kl, fn) for fn in sorted(os.listdir(a.kl))] + ([os.path.join(a.klref, fn) for fn in sorted(os.listdir(a.klref)) if fn.endswith('.csv.gz')] if a.klref else [])
    for fp in srcs:
        for r in csv.reader(gzip.open(fp, 'rt')):
            if r[0] == 'symbol': continue
            t = int(r[1])
            if t >= END: continue
            assert t <= TS_MAX
            if (r[0], t) in seen: continue
            fk.write('%s,%s,%s,%s,%s,%s\n' % tuple(r[:6])); seen.add((r[0], t)); nk += 1; tmax = max(tmax, t)
    for r in csv.reader(gzip.open(a.fx + '/cand_bars.csv.gz', 'rt')):
        if r[0] == 'symbol': continue
        t = int(r[1])
        if (r[0], t) in seen or t >= END: continue
        assert t <= TS_MAX
        fk.write(','.join(r[:6]) + '\n'); nk += 1
# V2: kline coverage per sim cum [start, min(end, END)] (minutes)
v2 = []
kl = collections.defaultdict(set)
for s, t in seen: kl[s].add(t)
for r in rows:
    if not (LO <= r['t0'] < HI): continue
    s = r['sym'] + 'USDT'; t1 = min(r['t1'], END - MIN)
    miss = [t for t in range(r['t0'], t1 + MIN, MIN) if t not in kl[s]]
    if miss: v2.append(dict(symbol=s, start=r['start'], n_missing=len(miss), first=miss[0]))
epx = {(r['t0'], r['sym'] + 'USDT'): r['entry'] for r in rows}
with open(a.fx + '/follow.csv', 'w') as f:
    f.write('ts,symbol,cid,entry_px\n')
    for r in csv.DictReader(open(a.fx + '/sim_entries.csv')):
        t = int(r['ts']); f.write('%d,%s,c3-%s-%d-0,%s\n' % (t, r['symbol'], r['symbol'], t // MIN, epx[(t, r['symbol'])]))
MKT_FROM = LO
if a.mkt:
    import shutil; shutil.copy(a.mkt, a.fx + '/mkt.csv.gz')
    MKT_FROM = min(int(x.split(',')[1]) for x in gzip.open(a.mkt, 'rt') if not x.startswith('symbol'))
else:
    with gzip.open(a.fx + '/mkt.csv.gz', 'wt') as f: f.write('symbol,t,o,h,l,c,qv\n')
ei = json.load(gzip.open(EXI)); patched = []
if a.patch_settling:
    for s_ in ei['symbols']:
        if s_.get('status') != 'TRADING' and s_.get('contractType') == 'PERPETUAL' and s_.get('quoteAsset') == 'USDT':
            patched.append((s_['symbol'], s_.get('status'))); s_['status'] = 'TRADING'
pin_diff = []
if a.pin:   # ERRATA2 2c: bo loc san = pin cua sim (tickSize, LOT_SIZE/MARKET_LOT_SIZE minQty = don vi qty sim) khi khac 20261027
    def flat(fl):
        out = []
        for x in fl: out += (x if isinstance(x, list) else [x])
        return out
    pm = {}
    for s_ in json.load(open(a.pin))['symbols']:
        f = {x['filterType']: x for x in flat(s_.get('filters', []))}
        pm[s_['symbol']] = f
    for s_ in ei['symbols']:
        P = pm.get(s_['symbol'])
        if not P: continue
        ch = []
        for f in s_['filters']:
            ft = f['filterType']
            if ft == 'PRICE_FILTER' and 'PRICE_FILTER' in P and 'tickSize' in P['PRICE_FILTER'] and float(P['PRICE_FILTER']['tickSize']) != float(f['tickSize']):
                ch.append(('tick', f['tickSize'], P['PRICE_FILTER']['tickSize'])); f['tickSize'] = P['PRICE_FILTER']['tickSize']
            if ft in ('LOT_SIZE', 'MARKET_LOT_SIZE') and ft in P and 'minQty' in P[ft]:
                q = P[ft]['minQty']
                if float(f.get('stepSize', q)) != float(q) or float(f.get('minQty', q)) != float(q):
                    ch.append((ft, f.get('stepSize'), q)); f['stepSize'] = q; f['minQty'] = q
        if ch: pin_diff.append((s_['symbol'], ch))
json.dump(ei, open(a.fx + '/exinfo.json', 'w'))
man = dict(START=LO, END=END + (MIN if a.end_pad else 0), END_DATA=END, mkt=dict(**{'from': MKT_FROM}), add24_rsim=True, W0=W0, HI_entries=HI)
json.dump(man, open(a.fx + '/manifest.json', 'w'), indent=1)
chk = dict(warm_rows=nw, warm_max_ts=maxw, warm_min_ts=minw, warm_from=WF, fed_by_quarter=dict(fedq), fed_Q1_reconstructed=fedQ1, unavail=len(un), umax_warm_to_hi_realizedE=umax,
           klines_rows=nk, klines_ts_max=tmax, V3_ok=tmax <= TS_MAX and tmax < END, V2_cums_with_missing=v2,
           files={fn: md5(os.path.join(a.fx, fn)) for fn in sorted(os.listdir(a.fx)) if os.path.isfile(os.path.join(a.fx, fn))},
           exinfo_src_md5=md5(EXI), exinfo_patched_settling=patched, pin=a.pin, pin_md5=(md5(a.pin) if a.pin else None), pin_diff_n=len(pin_diff), pin_diff=pin_diff)
json.dump(chk, open(a.fx + '/fx_check.json', 'w'), indent=1)
L.info('warm=%d fedQ1=%d unavail=%d umax=%.3f klines=%d V2_missing_cums=%d V3=%s', nw, fedQ1, len(un), umax, nk, len(v2), chk['V3_ok'])
