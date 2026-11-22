#!/usr/bin/env python3
"""ADD24 S-X phan loai lech (DEV-B). DOC LAP: khong import Java, chi doc printDone + klines fixture + output rig (score.json).
REF-SIM (quy tac sim theo NEN, a8690d46 OrderTargetInfoTest.updateStatusNew/updateTPSL): vao = close nen t0; tu nen t0+1:
  neu chua arm: r = high/e-1; r > 0.07 => SL = e*(1+rate(r)), KHONG khop trong nen nay (BLOCK_INTRABAR_LOOKAHEAD);
  neu da arm: low <= SL(tu nen truoc) => thoat nen nay gia min(SL, open); khong thi r = high/e-1 >= 0.07 => SL moi neu cao hon & > e.
REF-NHIP (mo hinh rig CrashDayRig.applyPrices + MockExchangeGateway.triggerStops): moi nen 4 moc gia +0/+15/+30/+45 s:
  nen giam (c<o): O,H,L,C ; con lai: O,L,H,C. Vi the mo luc t0+1'+6 s (gia vao = gia sim, follow) => moc dau tinh tu +15 s nen t0+1.
  Moi moc: da arm va moc <= SL => khop tai GIA MOC (nen do); khong thi peak=max(peak,moc); r=peak/e-1; r >= 0.07 => arm/nang SL
  (SL moi co hieu luc tu moc ke tiep).  rate(r) = round((r - min(r, 0.03))/0.005)*0.005 (TS_GIVEBACK_RATIO 1, TS_MAX_GAP 0.03).
Chi xet cum thoat TRAIL (time-stop da so rieng). Nhan: K8_INTRABAR (REF-nhip trung phut rig VA REF-sim trung phut sim),
GAP_FILL (cung phut, rig khop tai moc < SL, sim min(SL,open)), OTHER (ung vien lech logic that). Khong in PnL."""
import csv, gzip, json, sys, collections
from datetime import datetime, timezone, timedelta
TZ7 = timezone(timedelta(hours=7)); MIN = 60000
D, FX, lo, hi = sys.argv[1:5]
LANE = sys.argv[5] if len(sys.argv) > 5 else 'orig'   # sim: O,L,H,C ; sens: O,H,L,C ; orig: rig cu (giam O,H,L,C / tang O,L,H,C)
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
f7 = lambda ms: datetime.fromtimestamp(ms / 1000, TZ7).strftime('%m-%d %H:%M')
def rate(r):
    g = min(r * 1.0, 0.03); return round((r - g) / 0.005) * 0.005
bars = collections.defaultdict(dict)
for x in csv.reader(gzip.open(FX + '/klines.csv.gz', 'rt')):
    if x[0] == 'symbol': continue
    bars[x[0]][int(x[1])] = tuple(float(v) for v in x[2:6])
def ref_sim(s, e, t0, tend):
    SL = None; t = t0 + MIN
    while t <= tend + 3 * 24 * 60 * MIN:
        b = bars[s].get(t)
        if b is None: t += MIN; continue
        o, h, l, c = b
        if SL is not None and l <= SL: return t, min(SL, o)
        r = h / e - 1
        if SL is None:
            if r > 0.07: SL = e * (1 + rate(r))
        elif r >= 0.07:
            n = e * (1 + rate(r))
            if n > SL and n > e: SL = n
        t += MIN
    return None, None
def ref_nhip(s, e, t0, tend):
    SL = None; peak = e; t = t0 + MIN; first = True
    while t <= tend + 3 * 24 * 60 * MIN:
        b = bars[s].get(t)
        if b is None: t += MIN; first = False; continue
        o, h, l, c = b
        marks = (o, l, h, c) if LANE == 'sim' else ((o, h, l, c) if LANE == 'sens' else ((o, h, l, c) if c < o else (o, l, h, c)))
        for i, m in enumerate(marks):
            if first and i == 0: continue
            if SL is not None and m <= SL: return t, (SL if o > SL else o), SL   # ERRATA2 2a: khop = SL neu open > SL, nguoc lai open
            peak = max(peak, m); r = peak / e - 1
            if r >= 0.07:
                n = e * (1 + rate(r))
                if SL is None or (n > SL and n > e): SL = n
        first = False; t += MIN
    return None, None, None
sc = json.load(open(D + '/score.json'))
pd = {(d7(r['start']), r['sym'] + 'USDT'): r for r in csv.DictReader(open('/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv')) if lo <= r['start'][:8] < hi}
out = []; cnt = collections.Counter(); valid = [0, 0]
for o in sc['rows']:
    if o.get('rig_exit_ms') is None or o['sim_why'] != 'TRAIL': continue
    k = (d7(o['start'].replace('-', '')[:4] and ('2026' + o['start'][:2] + o['start'][3:5] + ' ' + o['start'][6:])), o['sym'])
    r = pd[k]; e = float(r['entry']); t0 = k[0]; tend = d7(r['end'])
    st, sp = ref_sim(o['sym'], e, t0, tend)
    valid[0] += 1; valid[1] += int(st == tend and abs(sp - float(r['tp'])) / float(r['tp']) < 2e-3)
    rig_min = (o['rig_exit_ms'] // MIN) * MIN
    dpx = (o['rig_exit_px'] - o['sim_exit_px']) / o['sim_exit_px']
    if rig_min == tend and dpx >= -0.015: continue
    nt, npx, nsl = ref_nhip(o['sym'], e, t0, tend)
    ob = bars[o['sym']].get(rig_min)
    if nt == rig_min and st == tend and rig_min != tend: lab = 'K8_INTRABAR'
    elif rig_min == tend and dpx < -0.015 and ob and abs(o['rig_exit_px'] - min(ob)) / o['rig_exit_px'] < 1e-6 and float(r['tp']) >= min(ob): lab = 'GAP_FILL'
    elif rig_min == tend and dpx < -0.015: lab = 'FILL_MODEL_SAME_MIN'
    else: lab = 'OTHER'
    cnt[lab] += 1
    out.append(dict(sym=o['sym'], start=o['start'], label=lab, dmin=(rig_min - tend) // MIN, dpx_pct=round(100 * dpx, 3),
                    ref_sim_exit=(f7(st) if st else None), sim_exit=f7(tend), ref_sim_ok=bool(st == tend),
                    ref_nhip_exit=(f7(nt) if nt else None), rig_exit=f7(rig_min), ref_nhip_eq_rig=bool(nt == rig_min),
                    rig_bar_ohlc=ob, rig_px=o['rig_exit_px'], sim_px=float(r['tp']), ref_nhip_px=npx, ref_nhip_sl=nsl))
res = dict(ref_sim_validation=dict(n_trail=valid[0], ref_sim_reproduces_sim_exit=valid[1]), counts=dict(cnt), rows=out)
json.dump(res, open(D + '/classify_sx.json', 'w'), indent=1, default=str)
print(json.dumps(dict(ref_sim_validation=res['ref_sim_validation'], counts=res['counts'])))
for x in out: print(x['sym'], x['start'], x['label'], 'dmin', x['dmin'], 'dpx%', x['dpx_pct'], 'REFsim', x['ref_sim_exit'], 'sim', x['sim_exit'], 'REFnhip', x['ref_nhip_exit'], 'rig', x['rig_exit'])
