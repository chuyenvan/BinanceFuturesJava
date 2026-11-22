#!/usr/bin/env python3
"""[LUOT8 R7 / ERRATA5 A] KET LUAN R-SIM bang SCRIPT (DEV-B). Khong PnL. Doc: <D>/score.json (score_rsim.py, nen co --vtier), classify_sx.json,
gates.json, add24_meta.txt, ssz_jar.csv; <FX>/manifest.json, exinfo.json, ssz_in.csv; vtier.json (tuy chon).
Luat: moi chi so >= 1 lech KHONG GIAI THICH => FAIL bat ke mau; INSUFFICIENT chi khi 0 lech va duoi mau.
 S-G   : mau >= 50 quyet dinh VA >= 10 phut; lenh PREDICT sim bi jar REJECT (khong phai N10) => FAIL.
 S-G2  : THO (pass bang nhau, seen +-1e-4) - PASS / FAIL.
 S-SZ  : leg EB2 > 1e-3 chi N11 (>= 3 leg cung phut, E suy nguoc trung <= 1e-4); leg > 1e-3 khong N11 => FAIL; ti le <= 1e-3 < 90 % (sau N11) => FAIL;
         leg khong co stepSize => FAIL; N11 > 2 phut => INSUFFICIENT; n < 50 => INSUFFICIENT.
 S-X   : MOI cum sim trong cua so (khong DCA, khong V-TIER) phai co trang thai: N10 / CHAM / NO_EXIT_SAU_END; con lai (rig khong vao, khong
         thoat khi sim thoat truoc END) => FAIL. (a) ly do thoat 100 %; (b) (cung phut + N8 K8) / tong >= 95 %, N8 <= 10 %, lech khac 0, > 1' 0;
         (c) TB Delta gia thoat trong [-0,2 %; +0,2 %], tung cum |Delta| <= 1,5 % hoac <= 2 tick tru N8. Mau: >= 30 cum thoat, >= 1 time-stop, >= 1 trail.
 S-D   : su kien sim phai khop; rig_extra => FAIL; 0 su kien hai phia => INSUFFICIENT_CO_PHU (khong chan, khong PASS).
 N10 > 5 % lenh PREDICT sim => CAN_OWNER. V-TIER FAIL_MOMENTS => HUY. Cong V1-V3/V5/V6/V9 sai => HUY. Cong lap dat L3 + L12 (rig_t <= START) sai => HUY.
 Co SIM_TIER_STALE + BD_ORDER LUON bat. RESULT: HUY > FAIL > INSUFFICIENT > PASS_CAN_OWNER.
usage: verdict_rsim.py <D> <FX> [vtier.json] [--out file]"""
import csv, json, re, sys, collections, logging
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
D, FX = sys.argv[1], sys.argv[2]
VT = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else D + '/verdict_rsim.json'
MIN = 60000
sc = json.load(open(D + '/score.json')); cl = json.load(open(D + '/classify_sx.json')); g = json.load(open(D + '/gates.json'))
man = json.load(open(FX + '/manifest.json')); START, END = int(man['START']), int(man['END'])
meta = open(D + '/add24_meta.txt').read()
R = {}
# ---- cong lap dat (m1)
def inst(key):
    m = re.search(r'^' + key + r'=(\w+) rig_t=(\d+)', meta, re.M)
    return dict(ok=bool(m and m.group(1) in ('installed', 'swapped') and int(m.group(2)) <= START), raw=(m.group(0) if m else None), START=START)
R['INSTALL'] = dict(L3=inst('x14'), L12=inst('simtier'))
R['INSTALL']['status'] = 'PASS' if R['INSTALL']['L3']['ok'] and R['INSTALL']['L12']['ok'] else 'HUY'
_ok = lambda k: bool(isinstance(g.get(k), dict) and g[k].get('ok') is True)
R['V_GATES'] = dict({k: _ok(k) for k in ('V1', 'V2', 'V3', 'V5', 'V6', 'V9')}, status='PASS' if all(_ok(k) for k in ('V1', 'V2', 'V3', 'V5', 'V6', 'V9')) else 'HUY')
vt = json.load(open(VT)) if VT else None
R['V-TIER'] = dict(status=(vt['status'] if vt else 'NOT_RUN'), TIER_DIV=(vt or {}).get('TIER_DIV'), excluded=(vt or {}).get('exclude'))
if vt and vt['status'] == 'FAIL_MOMENTS': R['V-TIER']['verdict'] = 'HUY'
elif not vt: R['V-TIER']['verdict'] = 'HUY'
else: R['V-TIER']['verdict'] = 'PASS'
# ---- S-G (R1)
sg = sc['S-G']
R['S-G'] = dict(decisions=sg['n_sim_predict'], minutes=sg['n_minutes'], fail=sg['fail'], fail_list=sg['fail_list'][:20],
                status=('FAIL' if sg['fail'] else ('PASS' if sg['n_sim_predict'] >= 50 and sg['n_minutes'] >= 10 else 'INSUFFICIENT')))
g2 = sc.get('S-G2', {})
R['S-G2'] = dict({k: g2.get(k) for k in ('quarter', 'jar_pass', 'sim_pass', 'jar_seen', 'sim_seen', 'seen_rel')},
                 status=('PASS' if g2 and g2.get('sim_pass') is not None and g2['jar_pass'] == g2['sim_pass'] and abs(g2['seen_rel']) <= 1e-4 else 'FAIL'))
# ---- N10
n10 = sc['N10']; n10k = {(x[1], x[0]) for x in n10['list']}
R['N10'] = dict(n=n10['n'], share=n10['share_of_sim_predict'], status=('CAN_OWNER' if (n10['share_of_sim_predict'] or 0) > 0.05 else 'OK'))
# ---- S-SZ (R2, N11, m2)
step = {}; tick = {}
for s_ in json.load(open(FX + '/exinfo.json'))['symbols']:
    for f_ in s_['filters']:
        if f_['filterType'] == 'LOT_SIZE': step[s_['symbol']] = float(f_['stepSize'])
        if f_['filterType'] == 'PRICE_FILTER': tick[s_['symbol']] = float(f_['tickSize'])
sin = {(r['ts'], r['symbol']): r for r in csv.DictReader(open(FX + '/ssz_in.csv'))}
n10ts = set()
for x in csv.DictReader(open(D + '/legs.csv')):
    if x['outcome'] == 'NOT_BUYABLE' and x['detail']: n10ts.add((x['decision_ts'], x['symbol']))
errs = []; over = []; Einf = collections.defaultdict(list); nostep = []; n_ok = 0
excl_vt = {tuple(x) for x in (sc.get('V-TIER', {}).get('excluded_cums') or [])}
for j in csv.DictReader(open(D + '/ssz_jar.csv')):
    r = sin[(j['ts'], j['symbol'])]
    if r['dca_merged'] == '1' or r['level'] == 'DCA_LEVEL1': continue
    if (j['ts'], j['symbol']) in n10ts: continue
    if any(j['symbol'] == a and int(j['ts']) == b for a, b in excl_vt): continue
    m = float(r['margin_sim']); f = float(j['f_jar']); e = float(r['entry_sim']); st = step.get(j['symbol'], 0) or 0
    F = float(j['F_BASE']) * float(j['ratio0']) / 4.0; um = float(j['U_MAX'])
    Einf[j['ts']].append((j['symbol'], (m + F * float(r['M_run']) / um) / F))
    if st <= 0: nostep.append((j['ts'], j['symbol'])); continue
    q = int(f / e / st + 1e-9) * st; dv = abs(q * e - m) / m; errs.append(dv)
    if dv > 1e-3: over.append((j['ts'], j['symbol'], r['level'], dv))
n11 = []; bad = []; n11min = set()
for ts, sym, lv, dv in over:
    v = Einf[ts]; Es = dict(v)[sym]; clu = [x for x in v if abs(x[1] - Es) / Es <= 1e-4]
    if len(v) >= 3 and len(clu) >= 3: n11.append((ts, sym, lv, round(dv, 6))); n11min.add(ts)
    else: bad.append((ts, sym, lv, round(dv, 6)))
n = len(errs); share = (sum(1 for e in errs if e <= 1e-3) + len(n11)) / n if n else None
st_sz = 'FAIL' if (bad or nostep or (n and share < 0.9)) else ('INSUFFICIENT' if (n < 50 or len(n11min) > 2) else 'PASS')
R['S-SZ'] = dict(n=n, max=(max(errs) if errs else None), share_le_1e3_incl_N11=share, over_1e3=len(over), N11_legs=len(n11), N11_minutes=len(n11min),
                 unexplained=bad[:20], no_stepsize=nostep[:20], status=st_sz)
# ---- S-X (R3 R4 R5 + B1 B2)
lab = {(r['sym'], r['start']): r['label'] for r in cl['rows']}
rows = sc['rows']; states = collections.Counter(); missing = []; ex_ = []
for o in rows:
    key = (o['sym'], o['start'])
    if o['dca']: states['DCA_CUM(S-D)'] += 1; continue
    if o['rig'] == 'NOT_BUYABLE' and key in n10k: states['N10'] += 1; continue
    if o['rig'] == 'SUBMITTED' and o.get('rig_why') not in (None, 'NO_EXIT'): states['SCORED'] += 1; ex_.append(o); continue
    if o['rig'] == 'SUBMITTED' and o.get('rig_why') == 'NO_EXIT' and o['sim_end'] >= END: states['NO_EXIT_SAU_END'] += 1; continue
    states['MISSING'] += 1; missing.append((o['sym'], o['start'], o['rig'], o.get('rig_why')))
nx = len(ex_); why_eq = sum(1 for o in ex_ if o['rig_why'] == o['sim_why'])
n_ts = sum(1 for o in ex_ if o['sim_why'] == 'TIME_STOP'); n_tr = sum(1 for o in ex_ if o['sim_why'] == 'TRAIL')
sample = nx >= 30 and n_ts >= 1 and n_tr >= 1
same = [o for o in ex_ if o['dmin'] == 0]
n8 = [o for o in ex_ if o['dmin'] != 0 and abs(o['dmin']) <= MIN and lab.get((o['sym'], o['start'])) == 'K8_INTRABAR']
oth = [o for o in ex_ if o['dmin'] != 0 and o not in n8]
n8k = {(o['sym'], o['start']) for o in n8}
dpx = [(o['rig_exit_px'] - o['sim_exit_px']) / o['sim_exit_px'] for o in ex_]
mean = sum(dpx) / len(dpx) if dpx else None
badc = []
for o in ex_:
    if (o['sym'], o['start']) in n8k: continue
    d_ = abs(o['rig_exit_px'] - o['sim_exit_px']); t_ = tick.get(o['sym'])
    if d_ / o['sim_exit_px'] > 0.015 and not (t_ and d_ <= 2 * t_ + 1e-12): badc.append((o['sym'], o['start'], round(100 * (o['rig_exit_px'] - o['sim_exit_px']) / o['sim_exit_px'], 3)))
def st3(failed): return 'FAIL' if failed else ('PASS' if sample else 'INSUFFICIENT')
sxa = st3(why_eq != nx)
sxb = st3(bool(oth) or (nx and ((len(same) + len(n8)) / nx < 0.95 or len(n8) / nx > 0.10)))
sxc = st3(bool(badc) or (mean is not None and not (-0.002 <= mean <= 0.002)))
sxm = 'FAIL' if missing else 'PASS'
R['S-X'] = dict(states=dict(states), missing=missing[:20], n_exit=nx, n_time_stop=n_ts, n_trail=n_tr, sample_ok=sample,
                a_reason=dict(eq=why_eq, n=nx, diff=[(o['sym'], o['start'], o['sim_why'], o['rig_why']) for o in ex_ if o['rig_why'] != o['sim_why']][:10], status=sxa),
                b_minute=dict(same=len(same), n8=len(n8), n8_share=(len(n8) / nx if nx else None), other=[(o['sym'], o['start'], o['dmin'] // MIN) for o in oth][:10], status=sxb),
                c_price=dict(mean=mean, per_cum_fail=badc[:10], status=sxc), cums_status=sxm)
R['S-X']['status'] = 'FAIL' if 'FAIL' in (sxa, sxb, sxc, sxm) else ('INSUFFICIENT' if 'INSUFFICIENT' in (sxa, sxb, sxc) else 'PASS')
# ---- S-D (R6)
sd = sc['S-D']
sd_fail = bool(sd.get('rig_extra')) or (sd['n_events'] and sd['ok'] != sd['n_events'])
R['S-D'] = dict(n_events=sd['n_events'], ok=sd['ok'], rig_extra=sd.get('rig_extra'), status=('FAIL' if sd_fail else ('PASS' if sd['n_events'] else 'INSUFFICIENT_CO_PHU')))
R['FLAGS'] = dict(SIM_TIER_STALE=True, BD_ORDER=True, N10_CAN_OWNER=R['N10']['status'] == 'CAN_OWNER')
bb = [R[k]['status'] for k in ('S-G', 'S-G2', 'S-SZ', 'S-X', 'S-D')]
if 'HUY' in (R['INSTALL']['status'], R['V_GATES']['status'], R['V-TIER']['verdict']): res = 'HUY'
elif 'FAIL' in bb: res = 'FAIL'
elif 'INSUFFICIENT' in bb: res = 'INSUFFICIENT'
else: res = 'PASS_CAN_OWNER'
R['RESULT'] = dict(result=res, bb={k: R[k]['status'] for k in ('S-G', 'S-G2', 'S-SZ', 'S-X', 'S-D')},
                   note='PASS_CAN_OWNER = moi BB dat; cho owner chap nhan co SIM_TIER_STALE + BD_ORDER (+ N10 neu CAN_OWNER); S-D INSUFFICIENT_CO_PHU phu boi C0b S-DCA')
json.dump(R, open(OUT, 'w'), indent=1, default=str)
L.info('RESULT %s %s', res, json.dumps(R['RESULT']['bb']))
for k in ('INSTALL', 'V_GATES', 'V-TIER', 'S-G', 'S-G2', 'N10', 'S-SZ', 'S-X', 'S-D'):
    L.info('%-8s %s', k, json.dumps(R[k], default=str)[:400])
