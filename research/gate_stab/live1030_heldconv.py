import re, datetime as dt, numpy as np, pandas as pd, sys
sys.path.insert(0, '/home/ubuntu/claude_master/1016/grr')
import grr_lib as G
D = '/home/ubuntu/claude_master/gst1030'
H = 3600000; DAY = 86400000; PCT = float(np.float32(0.999950829))
def ms7(s):  # 'dd/mm/yyyy HH:MM:SS' +07
    return int((dt.datetime.strptime(s, '%d/%m/%Y %H:%M:%S') - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - 7 * H
f7 = G.f
ev = []
for ln in open(D + '/shadow_events.txt'):
    m = re.match(r'(\S+ \S+)\.\d+\s+(open|closed) (\S+)', ln)
    if m: ev.append((ms7(m.group(1)), m.group(2), m.group(3)))
opens = {}; closes = {}
for t, k, s in ev:
    if k == 'open': opens.setdefault(s, []).append(t)
    else: closes.setdefault(s, []).append(t)
def held(sym, t):  # sel ts t (decision made at ~t+66s)
    dec = t + 66000
    for to in opens.get(sym, []):
        if to < dec - 1000:
            cl = [c for c in closes.get(sym, []) if c > to]
            if not cl or cl[0] > dec: return True
    return False
S = pd.read_parquet(D + '/sel_1030_cf.parquet')
S['held'] = [held(s, t) for s, t in zip(S.symbol, S.ts)]
b = S[(S.hhmm >= '10-30 03:30') & (S.hhmm < '10-30 04:00')]
print('burst recs', len(b), 'pass', int(b.pass_act.sum()), 'pass&held', int((b.pass_act & b.held).sum()), 'pass&new', int((b.pass_act & ~b.held).sum()))
ts, r, bad = G.load(D + '/gate_ratio_live_2242.bin')
o = np.argsort(ts, kind='stable'); ts = ts[o]; r = r[o].astype(np.float32)
# drop burst records of held symbols (sim convention): match by (ts, r) multiset
drop = b[b.held]
key = set(zip(drop.ts.values.tolist(), np.round(drop.r.values.astype(np.float64), 6).tolist()))
mask = np.ones(len(ts), bool); hit = 0
for i in np.where((ts >= b.ts.min()) & (ts <= b.ts.max()))[0]:
    k = (int(ts[i]), round(float(r[i]), 6))
    if k in key: mask[i] = False; key.discard(k); hit += 1
print('dropped held burst records', hit, 'of', len(drop))
def q_at(h, msk):
    a = np.sort(r[(ts >= h - 90 * DAY) & (ts < h) & msk]); m = len(a)
    k = min(m - 1, max(0, int(np.floor(PCT * (m - 1))))); return float(a[k]), m - 1 - k
h4 = (b.ts.min() // H + 1) * H
for hh in range(0, 6):
    h = h4 + hh * H
    print(f7(h), 'q_live %.6f' % q_at(h, np.ones(len(ts), bool))[0], 'q_simconv %.6f' % q_at(h, mask)[0])
qs = q_at(h4, mask)[0]
W = S[(S.hhmm >= '10-30 04:00') & (S.hhmm < '10-30 11:00')].copy()
W['pass_s'] = W.r >= qs
for c in ['pass_act', 'pass_x', 'pass_s']:
    x = W[W[c]]
    print(c, 'pass', len(x), 'new(not held)', int((~x.held).sum()), 'syms_new', sorted(set(x[~x.held].symbol.str.replace('USDT', ''))))
