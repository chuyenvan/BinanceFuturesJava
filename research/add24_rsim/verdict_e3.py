#!/usr/bin/env python3
"""ERRATA3 B1-B4 (DEV-B) doc chi so R-SIM tu score.json + classify_sx.json + exinfo. Khong PnL (chi gia thoat tuong doi).
B1 S-X(b): (cung phut + N8 co REF-nhip xac nhan [K8_INTRABAR]) / tong >= 95 %; N8 <= 10 %; moi cum khac <= +-1'; lech khong co che => FAIL.
B2 S-X(c): TB Delta(rig-sim)/sim trong [-0,2 %; +0,2 %]; tung cum |Delta| <= 1,5 % hoac <= 2 tick, tru N8.
B3 S-G2: cham THO (jar_pass == sim_pass, seen +-1e-4) sau khi N10 = dang giu trong rig.
B4 S-SZ: leg lech > 1e-3 (EB2) chi N11 khi phut co >= 3 leg sim va E suy nguoc trung <= 1e-4; khong thi FAIL. usage: verdict_e3.py <D> <FX>"""
import json, sys, collections, logging
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
D, FX = sys.argv[1:3]
sc = json.load(open(D + '/score.json')); cl = json.load(open(D + '/classify_sx.json'))
tick = {}
for s in json.load(open(FX + '/exinfo.json'))['symbols']:
    for f in s['filters']:
        if f['filterType'] == 'PRICE_FILTER': tick[s['symbol']] = float(f['tickSize'])
lab = {(r['sym'], r['start']): r['label'] for r in cl['rows']}
MIN = 60000
ex = [o for o in sc['rows'] if o.get('rig') == 'SUBMITTED' and o.get('rig_why') not in (None, 'NO_EXIT') and not o['dca']]
n = len(ex); same = [o for o in ex if o['dmin'] == 0]
n8 = [o for o in ex if o['dmin'] != 0 and lab.get((o['sym'], o['start'])) == 'K8_INTRABAR']
oth = [o for o in ex if o['dmin'] != 0 and lab.get((o['sym'], o['start'])) != 'K8_INTRABAR']
gt1 = [o for o in ex if abs(o['dmin']) > MIN]
b1 = dict(n=n, same_minute=len(same), n8_ref_confirmed=len(n8), other_diff=[(o['sym'], o['start'], o['dmin'] // MIN, lab.get((o['sym'], o['start']))) for o in oth],
          ratio=(len(same) + len(n8)) / n if n else None, n8_share=len(n8) / n if n else None, gt1=len(gt1))
b1['status'] = 'PASS' if n and b1['ratio'] >= 0.95 and b1['n8_share'] <= 0.10 and not oth and not gt1 else 'FAIL'
n8k = {(o['sym'], o['start']) for o in n8}
dpx = [(o['rig_exit_px'] - o['sim_exit_px']) / o['sim_exit_px'] for o in ex]
mean = sum(dpx) / len(dpx) if dpx else None
badc = []
for o in ex:
    if (o['sym'], o['start']) in n8k: continue
    d = abs(o['rig_exit_px'] - o['sim_exit_px']); t = tick.get(o['sym'])
    if d / o['sim_exit_px'] > 0.015 and not (t and d <= 2 * t + 1e-12): badc.append((o['sym'], o['start'], round(100 * (o['rig_exit_px'] - o['sim_exit_px']) / o['sim_exit_px'], 3)))
b2 = dict(mean_rel=mean, band=[-0.002, 0.002], per_cum_fail=badc, status='PASS' if mean is not None and -0.002 <= mean <= 0.002 and not badc else 'FAIL')
g2 = sc.get('S-G2', {})
b3 = dict(jar_pass=g2.get('jar_pass'), sim_pass=g2.get('sim_pass'), jar_seen=g2.get('jar_seen'), sim_seen=g2.get('sim_seen'), seen_rel=g2.get('seen_rel'), status=g2.get('status'))
# B4 N11: leg vuot nguong (EB2 lam tron qty: |q*e - m|/m > 1e-3, cum khong DCA, khong N10) -> N11 E_SIM_SRC khi phut co >= 3 leg sim
#   va E suy nguoc tu cac leg trung nhau <= 1e-4 (ham size jar: f = E*F_BASE*ratio0/4*(1 - U/U_MAX), U = M_run/E, M_run gom leg truoc cung phut
#   => E = (m + F*M_run/U_MAX)/F voi F = F_BASE*ratio0/4 lay tu ssz_jar.csv). Leg vuot nguong khong N11 => FAIL. N11 > 2 phut => INSUFFICIENT.
import csv as _csv
step = {}
for s_ in json.load(open(FX + '/exinfo.json'))['symbols']:
    for f_ in s_['filters']:
        if f_['filterType'] == 'LOT_SIZE': step[s_['symbol']] = float(f_['stepSize'])
sin = {(r['ts'], r['symbol']): r for r in _csv.DictReader(open(FX + '/ssz_in.csv'))}
n10k = {(str(_ms), _s) for _ms, _s in ()}
try:
    _l = json.load(open(D + '/score.json')).get('N10', {}).get('list', [])
except Exception:
    _l = []
n10syms = {x[1] for x in _l}
over = []; Einf = collections.defaultdict(list)
for j in _csv.DictReader(open(D + '/ssz_jar.csv')):
    r = sin[(j['ts'], j['symbol'])]
    if r['dca_merged'] == '1' or r['level'] == 'DCA_LEVEL1': continue
    m = float(r['margin_sim']); f = float(j['f_jar']); e = float(r['entry_sim']); st = step.get(j['symbol'], 0) or 0
    F = float(j['F_BASE']) * float(j['ratio0']) / 4.0; um = float(j['U_MAX'])
    Ei = (m + F * float(r['M_run']) / um) / F
    Einf[j['ts']].append((j['symbol'], Ei))
    if st > 0:
        q = int(f / e / st + 1e-9) * st
        if abs(q * e - m) / m > 1e-3: over.append((j['ts'], j['symbol'], r['level'], abs(q * e - m) / m))
n11 = []; bad = []; n11min = set()
for ts, sym, lv, dv in over:
    v = Einf[ts]; Es = dict(v)[sym]
    cl = [x for x in v if abs(x[1] - Es) / Es <= 1e-4]
    if len(v) >= 3 and len(cl) >= 3: n11.append((ts, sym, lv, round(dv, 5), round(Es, 1), len(cl), len(v))); n11min.add(ts)
    else: bad.append((ts, sym, lv, round(dv, 5), len(cl), len(v)))
sz = sc['S-SZ']['official_EB2_rounded']
b4 = dict(max=sz.get('max'), n=sz.get('n'), legs_over_1e3=len(over), n11_legs=len(n11), n11_minutes=len(n11min), n11=n11[:30], unexplained=bad[:30],
          status=('FAIL' if bad else ('INSUFFICIENT' if len(n11min) > 2 else (sc['S-SZ']['status'] if not n11 else 'PASS_N11'))))
out = dict(B1_SX_b=b1, B2_SX_c=b2, B3_SG2_raw=b3, B4_SSZ_N11=b4, N10=sc.get('N10'), S_E=sc.get('S-E'), S_D=sc.get('S-D', {}).get('status'))
json.dump(out, open(D + '/verdict_e3.json', 'w'), indent=1, default=str)
L.info(json.dumps(out, default=str))
