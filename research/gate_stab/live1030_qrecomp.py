import sys, glob, gzip, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, '/home/ubuntu/claude_master/1016/grr')
import grr_lib as G
D = '/home/ubuntu/claude_master/gst1030'
ts, r, BAD = G.load(D + '/gate_ratio_live_2242.bin')
ts = np.asarray(ts, dtype=np.int64); r = np.asarray(r, dtype=np.float32)
o = np.argsort(ts, kind='stable'); ts = ts[o]; r = r[o]
PCT = np.float32(0.999950829); DAY = 86400000; H = 3600000
def f7(t): return dt.datetime.utcfromtimestamp(t/1000 + 7*3600).strftime('%m-%d %H:%M')
print('bad', BAD); print('records', len(ts), f7(ts[0]), '->', f7(ts[-1]))
def q_at(h, mask=None):
    sel = (ts >= h - 90*DAY) & (ts < h)
    if mask is not None: sel &= mask
    a = np.sort(r[sel]); m = len(a)
    k = min(m-1, max(0, int(np.floor(float(PCT)*(m-1)))))
    return a[k], m, m-1-k
# burst = records in 10-30 03:30..04:00 (+07) with r >= 0.007255
t0 = int(dt.datetime(2026,10,29,20,30).timestamp()*1000)  # 03:30 +07 = 20:30 UTC
t0 = int((dt.datetime(2026,10,30,3,30) - dt.datetime(1970,1,1)).total_seconds()*1000) - 7*H
t1 = t0 + 30*60000
burst = (ts >= t0) & (ts < t1)
print('burst window recs', burst.sum(), 'r>=0.007255:', int(((r >= 0.007255) & burst).sum()), 'max r', r[burst].max())
nob = ~burst
hstart = int((dt.datetime(2026,10,30,0,0) - dt.datetime(1970,1,1)).total_seconds()*1000) - 7*H
print('hour(+07)  q_recomp  m  n_above | q_excl_burst')
QA = {}; QX = {}
for i in range(0, 22):
    h = hstart + i*H
    q, m, na = q_at(h); qx, mx, nax = q_at(h, nob)
    QA[h] = q; QX[h] = qx
    print(f7(h), '%.9g' % q, m, na, '| %.9g' % qx)
# top values
srt = np.sort(r[(ts < hstart + 5*H)])[::-1]
print('top60 r (all, ts<05:00):', np.round(srt[:60], 5).tolist())
# sel_dump counterfactual
fs = sorted(glob.glob(D + '/sel/*.csv.gz'))
S = pd.concat([pd.read_csv(x) for x in fs]).drop_duplicates(['ts', 'symbol'])
S = S[S['rank'] <= 24]
fac = np.maximum(np.float32(0.26787), (S.gateValue.values.astype(np.float32) / np.float32(0.15)) * np.float32(1.2876))
S['r'] = S.p15.values.astype(np.float32) / (fac * np.float32(1.55))
S['h'] = (S.ts // H) * H
S['q_act'] = S.h.map(QA); S['q_x'] = S.h.map(QX)
S['hhmm'] = S.ts.map(f7)
S = S[S.h.isin(list(QA.keys()))]
S['pass_act'] = S.r >= S.q_act; S['pass_x'] = S.r >= S.q_x
g = S.groupby('h').agg(n=('r', 'size'), pa=('pass_act', 'sum'), px=('pass_x', 'sum'))
g.index = [f7(x) for x in g.index]; print(g.to_string())
pm = S[S.pass_act | S.pass_x].groupby('hhmm').agg(pa=('pass_act', 'sum'), px=('pass_x', 'sum'), p15=('p15', 'first'), syms=('symbol', lambda s: ','.join(x.replace('USDT', '') for x in list(s)[:8])))
print(pm.to_string())
S.to_parquet(D + '/sel_1030_cf.parquet')
