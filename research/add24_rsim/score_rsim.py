#!/usr/bin/env python3
"""ADD24 R-SIM scorer (DEV-B). Prints ONLY decision deviations / function-size / relative prices. NO PnL/ROI/balance.
usage: score_rsim.py <RUN_DIR> <FX_DIR> <lo YYYYMMDD> <hi YYYYMMDD> [--json out.json]"""
import csv, gzip, json, logging, struct, sys, collections, statistics
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); MIN = 60000; HR = 3600000
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
EXI = '/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz'
D, FX, lo, hi = sys.argv[1:5]
jout = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
QTR = sys.argv[sys.argv.index('--quarter') + 1] if '--quarter' in sys.argv else None
VT = sys.argv[sys.argv.index('--vtier') + 1] if '--vtier' in sys.argv else None   # ERRATA4 1b: vtier.json (cum TIER_DIV -> loai S-X/S-SZ/S-D)
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
f7 = lambda ms: datetime.fromtimestamp(ms / 1000, TZ7).strftime('%m-%d %H:%M')
bits = lambda b: struct.unpack('>f', struct.pack('>i', int(b)))[0]
res = {}
allpd = list(csv.DictReader(open(PD)))
grp = collections.defaultdict(list)
for r in allpd: grp[(r['sym'], r['end'])].append(r)
sim = [r for r in allpd if lo <= r['start'][:8] < hi]
for r in sim:
    r['t0'] = d7(r['start']); r['t1'] = d7(r['end']); r['s'] = r['sym'] + 'USDT'; r['h'] = int(r['time_order'])
    r['dca'] = len(grp[(r['sym'], r['end'])]) > 1   # printDone = 1 dong/leg; cum nhieu leg = cum DCA
    r['why'] = 'TRAIL' if r['status'] == 'STOP_MARKET_DONE' else ('TIME_STOP' if r['h'] >= 168 else 'SL_OTHER')
# ---------------- V-TIER (ERRATA4 1b): cum co su kien TIER_DIV (tier luoi sim != tier theo gio o phut du dieu kien DCA) loai khoi S-X / S-SZ / S-D
vt = json.load(open(VT)) if VT else None
excl = {(a, int(b)) for a, b in vt['exclude']} if vt else set()
vex = {(r['t0'], r['s']) for r in sim if (r['s'], d7(min(x['start'] for x in grp[(r['sym'], r['end'])]))) in excl}
res['V-TIER'] = dict(file=VT, status=(vt['status'] if vt else 'NOT_RUN'), TIER_DIV=(vt['TIER_DIV'] if vt else None),
                     TIER_DIV_cums=(vt['TIER_DIV_cums'] if vt else None), excluded_cums=sorted(excl), excluded_rows=len(vex),
                     moments_match_printDone00=(vt['moments_match_printDone00'] if vt else None), SIM_TIER_STALE=True)
# ---------------- S-G
tr = {}
passNon = collections.Counter(); passNonMin = set(); nGate = 0
for x in csv.DictReader(gzip.open(D + '/trace_dec.csv.gz', 'rt')):
    k = (int(x['ts']), x['symbol'])
    if x['gated'] == '1': nGate += 1
    tr[k] = x
    if x['pass'] == '1' and x['legacy'] == '1':
        passNon['n'] += 1; passNonMin.add(int(x['ts']))
pred = [r for r in sim if r['level'] == 'PREDICT_SYMBOL_TRADE']
sg_ok = []; sg_bad = []
for r in pred:
    x = tr.get((r['t0'], r['s']))
    if x and x['gated'] == '1' and x['pass'] == '1': sg_ok.append(r)
    else:
        det = 'NO_TRACE' if x is None else 'gated=%s held=%s legacy=%s pass=%s r=%.6g q=%.6g' % (
            x['gated'], x['held'], x['legacy'], x['pass'], bits(x['r_bits']), bits(x['q_bits']) if x['q_bits'] else float('nan'))
        sg_bad.append((f7(r['t0']), r['s'], det))
sim_min = sorted({r['t0'] for r in pred})
res['S-G'] = dict(n_sim_predict=len(pred), n_minutes=len(sim_min), jar_pass=len(sg_ok), fail=len(sg_bad), fail_list=sg_bad,
                  jar_pass_non_sim_candidates=passNon['n'], minutes_with_non_sim_pass=len(passNonMin),
                  minutes_non_sim_pass_and_no_sim_entry=len(passNonMin - set(sim_min)), gated_rows=nGate,
                  sample_ok=(len(pred) >= 50 and len(sim_min) >= 10),
                  # [LUOT8 R1 / ERRATA5 A] mau = >= 50 quyet dinh (phut, symbol) VA >= 10 phut (ERRATA2); lenh sim bi jar REJECT => FAIL bat ke mau
                  status=('FAIL' if sg_bad else ('PASS' if (len(pred) >= 50 and len(sim_min) >= 10) else 'INSUFFICIENT')))
# ---------------- N10 PROD_GUARD (ERRATA1 EB8): sim vao, jar chan bang guard production co ly do (legs.csv detail) dung phut+symbol
legs = [x for x in csv.DictReader(open(D + '/legs.csv'))]
n10 = {}
for x in legs:
    if x['outcome'] in ('NOT_BUYABLE',) and x['detail']:
        n10[(int(x['decision_ts']), x['symbol'])] = x['detail']
simk = {(r['t0'], r['s']) for r in sim}
n10 = {k: v for k, v in n10.items() if k in simk}
npred = sum(1 for r in sim if r['level'] == 'PREDICT_SYMBOL_TRADE')
res['N10'] = dict(n=len(n10), n_predict=sum(1 for k in n10 if any(r['t0'] == k[0] and r['s'] == k[1] and r['level'] == 'PREDICT_SYMBOL_TRADE' for r in sim)),
                  share_of_sim_predict=(sum(1 for k in n10 if any(r['t0'] == k[0] and r['s'] == k[1] and r['level'] == 'PREDICT_SYMBOL_TRADE' for r in sim)) / npred if npred else None),
                  list=[(f7(k[0]), k[1], v) for k, v in sorted(n10.items())])
if QTR:
    import re as _re
    simq = {}
    for ln in gzip.open('/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/logs/sim.out.gz', 'rt', errors='replace'):
        if 'GATE-RATIO on pct' in ln:
            for q, a_, b_ in _re.findall(r'(\d{4}Q\d):(\d+)/(\d+)', ln): simq[q] = (int(a_), int(b_))
    def qk(t):
        d_ = datetime.fromtimestamp(t / 1000, TZ7); return '%dQ%d' % (d_.year, (d_.month - 1) // 3 + 1)
    gq = collections.Counter(); pq = collections.Counter(); minsq = set()
    for k_, x in tr.items():
        if x['gated'] == '1':
            gq[qk(k_[0])] += 1; minsq.add(k_[0])
            if x['pass'] == '1': pq[qk(k_[0])] += 1
    sp_, ss_ = simq.get(QTR, (None, None))
    # dieu chinh N10-cascade: symbol N10 (jar chan, sim giu) trong khoang sim GIU -> rig van coi la ung vien (sim khong nap)
    n10s = {k_[1] for k_ in n10}
    heldiv = collections.defaultdict(list)
    for r in allpd:
        if r['sym'] + 'USDT' in n10s:
            f0 = d7(r['start']) + (MIN if r['level'] == 'PREDICT_SYMBOL_TRADE' else 0); heldiv[r['sym'] + 'USDT'].append((f0, d7(r['end'])))
    adjg = 0; adjp = 0
    for k_, x in tr.items():
        if x['gated'] == '1' and qk(k_[0]) == QTR and any(a0 <= k_[0] < b0 for a0, b0 in heldiv.get(k_[1], ())):
            adjg += 1; adjp += int(x['pass'] == '1')
    res['S-G2'] = dict(quarter=QTR, jar_pass=pq[QTR], sim_pass=sp_, jar_seen=gq[QTR], sim_seen=ss_,
                       seen_rel=(gq[QTR] / ss_ - 1) if ss_ else None, minutes_gated=len(minsq),
                       n10_cascade_rows=adjg, n10_cascade_pass=adjp, jar_pass_adj=pq[QTR] - adjp, jar_seen_adj=gq[QTR] - adjg,
                       seen_rel_adj=((gq[QTR] - adjg) / ss_ - 1) if ss_ else None,
                       status_adj=('PASS' if sp_ is not None and pq[QTR] - adjp == sp_ and abs((gq[QTR] - adjg) / ss_ - 1) <= 1e-4 else 'FAIL'),
                       status=('PASS' if sp_ is not None and pq[QTR] == sp_ and abs(gq[QTR] / ss_ - 1) <= 1e-4 else 'FAIL'))
# ---------------- S-SZ (jar function)
ei = json.load(open(FX + '/exinfo.json')); step = {}
for s in ei['symbols']:
    for f in s['filters']:
        if f['filterType'] == 'LOT_SIZE': step[s['symbol']] = float(f['stepSize'])
sin = {(r['ts'], r['symbol']): r for r in csv.DictReader(open(FX + '/ssz_in.csv'))}
e1 = []; e2 = []; nd = 0; nostep = []
for j in csv.DictReader(open(D + '/ssz_jar.csv')):
    r = sin[(j['ts'], j['symbol'])]
    if r['dca_merged'] == '1' or r['level'] == 'DCA_LEVEL1': nd += 1; continue
    if (int(j['ts']), j['symbol']) in n10: continue
    if (int(j['ts']), j['symbol']) in vex: continue
    m = float(r['margin_sim']); f = float(j['f_jar']); e = float(r['entry_sim']); st = step.get(j['symbol'], 0) or 0
    e1.append(abs(m - f) / m)
    if st <= 0: nostep.append((j['ts'], j['symbol']))   # [LUOT8 m2] khong bo qua im lang
    if st > 0:
        q = int(f / e / st + 1e-9) * st
        e2.append(abs(q * e - m) / m)
def dist(v):
    if not v: return {}
    v = sorted(v); n = len(v)
    return dict(n=n, max=v[-1], p90=v[int(0.9 * (n - 1))], share_le_1e3=sum(x <= 1e-3 for x in v) / n, share_le_5e3=sum(x <= 5e-3 for x in v) / n)
d1 = dist(e1)
d2 = dist(e2)
res['S-SZ'] = dict(official_EB2_rounded=d2, original_metric=d1, excluded_dca=nd, excluded_n10=len(n10),
                   no_stepsize=nostep,
                   # [LUOT8 R2] lech (> 5e-3 hoac ti le <= 1e-3 < 90 %) hoac leg khong cham duoc (stepSize <= 0) => FAIL bat ke mau; N11 xu o verdict
                   status=('FAIL' if (nostep or (d2.get('n', 0) and (d2['share_le_5e3'] < 1.0 or d2['share_le_1e3'] < 0.9))) else ('PASS' if d2.get('n', 0) >= 50 else 'INSUFFICIENT')))
# ---------------- rig cums: legs (SUBMITTED leg0) + fills + events
outc = collections.Counter((x['level'], x['outcome']) for x in legs)
fills = list(csv.DictReader(open(D + '/fills.csv')))
ev = list(csv.DictReader(open(D + '/events.csv')))
tstop = collections.defaultdict(list)
for e in ev:
    if e['type'] == 'TRAIL_TIME_STOP': tstop[e['symbol']].append(int(e['ms']))
arm = collections.defaultdict(list)
for e in ev:
    if e['type'] == 'TRAIL_ARM': arm[e['symbol']].append(int(e['ms']))
KB = {}
for x in csv.reader(gzip.open(FX + '/klines.csv.gz', 'rt')):
    if x[0] != 'symbol': KB[(x[0], int(x[1]))] = float(x[2])
buys = collections.defaultdict(list); sells = collections.defaultdict(list)
for f in fills:
    (buys if f['side'] == 'BUY' else sells)[f['symbol']].append((int(f['ms']), float(f['price']), f['cid']))
rows = []
for r in sim:
    if (r['t0'], r['s']) in vex: continue
    lg = [x for x in legs if x['symbol'] == r['s'] and int(x['decision_ts']) == r['t0']]
    st = lg[0]['outcome'] if lg else 'NO_LEG'
    o = dict(sym=r['s'], start=f7(r['t0']), level=r['level'], rig=st, sim_why=r['why'], sim_end=r['t1'], sim_h=r['h'], dca=r['dca'])
    if st == 'SUBMITTED':
        b = [x for x in buys[r['s']] if x[0] >= r['t0']]
        o['rig_entry_px'] = b[0][1] if b else None
        o['sim_entry_px'] = float(r['entry'])
        s_ = [x for x in sells[r['s']] if b and x[0] >= b[0][0]]
        if s_:
            ms, px, cid = s_[0]
            ts_ = [t for t in tstop[r['s']] if abs(t - ms) <= 60000]
            o['rig_why'] = 'TIME_STOP' if ts_ else 'TRAIL'
            o['rig_exit_ms'] = ms; o['rig_fill_raw'] = px
            if o['rig_why'] == 'TRAIL':   # ERRATA2 2a: khop stop = SL neu open nen kich > SL, nguoc lai = open
                sl = [(int(e['ms']), float(e['value'])) for e in ev if e['symbol'] == r['s'] and e['type'] == 'TRAIL_STOP_PLACED' and int(e['ms']) <= ms]
                b0 = (ms // MIN) * MIN
                bo = KB.get((r['s'], b0))
                if sl and bo is not None:
                    # SL dat TRONG nen khop (nang tai moc H cung nen) => gia cat xuong qua SL => khop = SL; SL co tu truoc nen => min(SL, open)
                    px = sl[-1][1] if (sl[-1][0] >= b0 or bo > sl[-1][1]) else bo
                    o['sl_at_exit'] = sl[-1][1]; o['bar_open'] = bo; o['sl_set_in_exit_bar'] = sl[-1][0] >= b0
            o['rig_exit_px'] = px
            o['sim_exit_px'] = float(r['tp'])
            o['dmin'] = (ms // MIN) * MIN - r['t1']
            o['rig_age_h'] = (ms - r['t0']) / HR
            o['armed'] = any(b[0][0] <= t <= ms for t in arm[r['s']])
        else:
            o['rig_why'] = 'NO_EXIT'
    rows.append(o)
sub = [o for o in rows if o['rig'] == 'SUBMITTED']
ex = [o for o in sub if o.get('rig_why') not in (None, 'NO_EXIT') and not o['dca']]
why_eq = [o for o in ex if o['rig_why'] == o['sim_why']]
dmin = collections.Counter(o['dmin'] // MIN for o in ex)
dpx = [(o['rig_exit_px'] - o['sim_exit_px']) / o['sim_exit_px'] for o in ex]
same = sum(1 for o in ex if o['dmin'] == 0)
pm1 = sum(1 for o in ex if abs(o['dmin']) == MIN)
dm = statistics.mean(dpx) if dpx else None
bad_c = [o for o in ex if (o['rig_exit_px'] - o['sim_exit_px']) / o['sim_exit_px'] < -0.015]
res['S-X_summary'] = dict(n=len(ex), reason_eq_share=(len(why_eq) / len(ex) if ex else None), same_minute=same,
                          same_minute_share=(same / len(ex) if ex else None), pm1=pm1, gt1=len(ex) - same - pm1,
                          px_mean=dm, n_below_m1p5=len(bad_c), excluded_n10=len(n10), excluded_dca=sum(1 for r in sim if r['dca']))
res['S-X'] = dict(n_sim=len(sim), rig_outcomes=dict((f'{a}|{b}', c) for (a, b), c in outc.items()), n_rig_exit=len(ex),
                  reason_equal=len(why_eq), reason_diff=[(o['sym'], o['start'], o['sim_why'], o['rig_why'], round(o['rig_age_h'], 2), o['sim_h']) for o in ex if o['rig_why'] != o['sim_why']],
                  exit_minute_delta_hist=dict(sorted(dmin.items())),
                  exit_px_rel_mean=(statistics.mean(dpx) if dpx else None), exit_px_rel_min=(min(dpx) if dpx else None),
                  exit_px_rel_max=(max(dpx) if dpx else None),
                  n_time_stop_sim=sum(o['sim_why'] == 'TIME_STOP' for o in ex), n_trail_sim=sum(o['sim_why'] == 'TRAIL' for o in ex),
                  no_exit=[(o['sym'], o['start']) for o in sub if o.get('rig_why') == 'NO_EXIT'])
ent = [(o['rig_entry_px'] - o['sim_entry_px']) / o['sim_entry_px'] * 1e4 for o in sub if o.get('rig_entry_px')]
res['S-E'] = dict(n=len(ent), mean_bps=statistics.mean(ent) if ent else None, p90_abs_bps=sorted(abs(x) for x in ent)[int(0.9 * (len(ent) - 1))] if ent else None)
sd = []
for (sy, en), v in grp.items():
    v = sorted(v, key=lambda r: d7(r['start']))
    if (sy + 'USDT', d7(v[0]['start'])) in excl: continue
    if len(v) < 2 or not (lo <= v[0]['start'][:8] < hi): continue
    s_ = sy + 'USDT'
    rl = sorted([x for x in legs if x['symbol'] == s_ and x['level'] == 'DCA_LEVEL1' and x['outcome'] == 'SUBMITTED'], key=lambda x: int(x['decision_ts']))
    for i, r in enumerate(v[1:], 1):
        t = d7(r['start'])
        m = [x for x in rl if abs(int(x['decision_ts']) - t) <= MIN]
        sd.append(dict(sym=s_, leg=i, sim=f7(t), rig=[(f7(int(x['decision_ts'])), x['leg_idx']) for x in rl],
                       ok=bool(m) and m[0]['leg_idx'] == str(i), rig_dca_before=[f7(int(x['decision_ts'])) for x in rl if int(x['decision_ts']) < t - MIN]))
# [LUOT7 EB25] chieu nguoc: leg DCA rig SUBMITTED ma sim KHONG co (cum sim cung symbol, leg0 trong cua so, khong leg DCA sim +-1') = lech
rig_extra = []; rig_dca_in = 0
for x in legs:
    if x['level'] != 'DCA_LEVEL1' or x['outcome'] != 'SUBMITTED': continue
    tx = int(x['decision_ts']); s_ = x['symbol']
    cum = [v for (sy, en), v in grp.items() if sy + 'USDT' == s_ and d7(min(r['start'] for r in v)) <= tx < d7(en)]
    if not cum: rig_extra.append((f7(tx), s_, 'NO_SIM_CUM')); continue
    v = sorted(cum[0], key=lambda r: d7(r['start'])); l0 = d7(v[0]['start'])
    if not (lo <= v[0]['start'][:8] < hi): continue
    rig_dca_in += 1
    if (s_, l0) in excl: continue
    if not any(abs(d7(r['start']) - tx) <= MIN for r in v[1:]): rig_extra.append((f7(tx), s_, 'SIM_NO_DCA'))
sd_ok = all(x['ok'] and not x['rig_dca_before'] for x in sd)
res['S-D'] = dict(n_events=len(sd), ok=sum(x['ok'] and not x['rig_dca_before'] for x in sd), events=sd, rig_dca_legs_in_window=rig_dca_in,
                  rig_extra=rig_extra,
                  status=('FAIL' if (rig_extra or (sd and not sd_ok)) else ('PASS' if sd else 'INSUFFICIENT_CO_PHU')))   # [LUOT8 R6] 0 su kien hai phia: khong bao gio PASS
res['rows'] = rows
if jout: json.dump(res, open(jout, 'w'), indent=1, default=str)
for k in ('V-TIER', 'S-G', 'S-G2', 'N10', 'S-SZ', 'S-X_summary', 'S-X', 'S-E', 'S-D'):
    if k not in res: continue
    L.info('%s %s', k, json.dumps({a: b for a, b in res[k].items() if a not in ('fail_list',)}, default=str)[:1500])
L.info('S-G fail_list %s', res['S-G']['fail_list'][:20])
