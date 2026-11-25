"""A1 brute-force per-trade check straight from raw files (no panels, no RUN code).
Samples trades from RUN events, recomputes z_oi, z_f, f, P(te), P(te+24h), gross, funding, EW, net_ex, z_r (E1)."""
import json
import logging
import math
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('smp')
CUT = 1767225600000
H = 3600000
M = 60000
KL = '/home/ubuntu/claude_master/res1109/r1_s1/kl/kline1m-%s.parquet'
MET = '/home/ubuntu/vz/out/metrics5m/%s/%s.parquet'
FU = '/home/ubuntu/claude_master/1016/carry/fund/funding-%d.parquet'
D1 = '/home/ubuntu/claude_master/1016/screen/d1.parquet'
RUNOUT = '/home/ubuntu/claude_master/w3/levz/out/'
A1 = '/home/ubuntu/claude_master/w3/levz/a1/'
BAD = {'USDC', 'BUSD', 'TUSD', 'FDUSD', 'USDP', 'DAI', 'UST', 'USDE', 'EUR', 'AEUR', 'BTCDOM', 'DEFI', 'BLUEBIRD', 'FOOTBALL'}
BRW = {'A1': 14, 'A2': 14, 'A3': 7, 'A4': 7}


def ym(ms):
    t = pd.Timestamp(ms, unit='ms')
    return '%d-%02d' % (t.year, t.month)


def yms(a, b):
    out, t = [], pd.Timestamp(a, unit='ms').to_period('M')
    e = pd.Timestamp(b, unit='ms').to_period('M')
    while t <= e:
        out.append(str(t))
        t += 1
    return [x for x in out if '2021-12' <= x <= '2025-12']


def rd(path, cols, filt):
    filt = filt + [('ts', '<', CUT)]
    d = pq.read_table(path, columns=cols, filters=filt).to_pandas()
    assert len(d) == 0 or d['ts'].max() < CUT
    return d


def kl_sym(sym, a, b):
    return pd.concat([rd(KL % m, ['ts', 'sym', 'close'], [('sym', '=', sym), ('ts', '>=', a), ('ts', '<=', b)]) for m in yms(a, b)]).sort_values('ts')


def oi_sym(sym, a, b):
    return pd.concat([rd(MET % (m[:4], m), ['ts', 'sym', 'oi'], [('sym', '=', sym), ('ts', '>=', a), ('ts', '<=', b)]) for m in yms(a, b)]).sort_values('ts')


FUN = None


def fund_sym(sym):
    global FUN
    if FUN is None:
        FUN = pd.concat([rd(FU % y, ['ts', 'sym', 'interval_h', 'rate'], []) for y in range(2021, 2026)])
        FUN['sym'] = FUN['sym'].astype(str)
    return FUN[FUN['sym'] == sym].sort_values('ts').drop_duplicates('ts', keep='last')


D1D = None


def univ(day):
    global D1D
    if D1D is None:
        D1D = pq.read_table(D1, columns=['sym', 'day', 'qv'], filters=[('day', '<', pd.Timestamp('2026-01-01'))]).to_pandas()
        assert D1D['day'].max() < pd.Timestamp('2026-01-01')
    out = []
    for s, g in D1D.groupby('sym'):
        if not (s.endswith('USDT') and '_' not in s and s[:-4] not in BAD):
            continue
        if g['day'].min() > day - pd.Timedelta(days=45):
            continue
        w = g[(g['day'] >= day - pd.Timedelta(days=30)) & (g['day'] <= day - pd.Timedelta(days=1))].drop_duplicates('day')
        if len(w) == 30 and w['qv'].mean() >= 20e6:
            out.append(s)
    return out


def px_at(sym_list, t):
    m = ym(t)
    d = rd(KL % m, ['ts', 'sym', 'close'], [('ts', '>=', t - 2 * H), ('ts', '<=', t)])
    d['sym'] = d['sym'].astype(str)
    d = d[d['sym'].isin(sym_list)]
    ex = d[d['ts'] == t].set_index('sym')['close']
    last = d.sort_values('ts').groupby('sym')['close'].last()
    return ex, last


def one(br, row):
    W = BRW[br]
    sym, t0, te = row['sym'], int(row['t0']), int(row['te'])
    Wms = W * 24 * H
    o = oi_sym(sym, t0 - Wms - 3 * H, t0)
    ots, ov = o['ts'].values, o['oi'].values
    xs = []
    for k in range(W * 24, -1, -1):
        s = t0 - k * H
        i = np.searchsorted(ots, s - 10 * M, 'right') - 1
        ok = i >= 0 and ov[i] > 0 and (s - ots[i]) < 70 * M
        xs.append(math.log(ov[i]) if ok else np.nan)
    xs = np.array(xs)
    win, x0 = xs[:-1], xs[-1]
    win = win[np.isfinite(win)]
    zoi = (x0 - win.mean()) / max(win.std(ddof=1), 0.02) if len(win) >= math.ceil(0.8 * W * 24) else np.nan
    f = fund_sym(sym)
    fts, fr, fih = f['ts'].values, f['rate'].values, f['interval_h'].values
    j = np.searchsorted(fts, t0 - M, 'right') - 1
    r8 = fr * 8.0 / fih
    fw = r8[(fts >= t0 - Wms) & (fts < fts[j])]
    fz = (r8[j] - fw.mean()) / max(fw.std(ddof=1), 0.00005)
    age_f_h = (t0 - fts[j]) / H
    k = kl_sym(sym, te - 2 * H, te + 25 * H)
    kt, kc = k['ts'].values, k['close'].values
    pte = kc[kt == te][0]
    e = te + 24 * H
    pe = kc[kt == e][0] if (kt == e).any() else kc[kt <= e][-1]
    gross = -(pe / pte - 1)
    fl = fr[(fts > te) & (fts <= e)].sum()
    frun = fr[(fts > te + M) & (fts <= e + M)].sum()
    U = univ(pd.Timestamp(te, unit='ms').normalize())
    a, _ = px_at(U, te)
    b, bl = px_at(U, e)
    rets = []
    for s in U:
        if s not in a.index:
            continue
        pb = b[s] if s in b.index else (bl[s] if s in bl.index else np.nan)
        if not np.isfinite(pb):
            kk = kl_sym(s, e - 3 * 24 * H, e)
            pb = kk['close'].values[-1]
        rets.append(pb / a[s] - 1)
    ew = float(np.mean(rets))
    out = dict(br=br, sym=sym, t0=t0, te=te, zoi=zoi, zf=fz, f=r8[j], age_f_h=age_f_h, pte=pte, pe=pe, gross=gross,
               fund_lit=fl, fund_run=frun, ew=ew, n_univ=len(U), n_univ_px=len(rets),
               net_ex=gross - 0.0014 + frun + ew, net_ex_lit=gross - 0.0014 + fl + ew)
    if row.get('lag_h', 0) > 0:
        kk = kl_sym(sym, te - Wms - 2 * H, te)
        kt2, kc2 = kk['ts'].values, kk['close'].values

        def cl(t):
            m = (kt2 >= t - H) & (kt2 <= t - M)
            return kc2[m][-1] if m.any() else np.nan
        cls = np.array([cl(te - q * H) for q in range(W * 24 + 1, -1, -1)])
        r1 = cls[1:] / cls[:-1] - 1
        w = r1[:-1]
        w = w[np.isfinite(w)]
        out['zr'] = r1[-1] / w.std(ddof=1)
    for kx, rx in (('zoi', 'z_oi'), ('zf', 'z_f'), ('f', 'f'), ('pte', 'p_te'), ('pe', 'p_end_24'), ('gross', 'gross_24'),
                   ('fund_run', 'fund_24'), ('fund_lit', 'fund_lit_24'), ('ew', 'ew_24'), ('net_ex', 'net_ex_24'), ('zr', 'z_r')):
        if kx in out and rx in row:
            out['d_' + kx] = float(out[kx] - row[rx])
    out['n_ew_run'] = int(row['n_ew_24'])
    return out


def main():
    rng = np.random.default_rng(99)
    res = []
    for pn, nper in (('explore', 5), ('confirm', 6)):
        for br in ('A1', 'A2', 'A3', 'A4'):
            d = pd.read_parquet(RUNOUT + 'events_%s_%s.parquet' % (br, pn))
            d = d[d['nop'] == 0].reset_index(drop=True)
            for i in rng.choice(len(d), size=nper, replace=False):
                r = one(br, d.loc[i].to_dict())
                r['period'] = pn
                res.append(r)
                log.info('%s %s %s dnet=%.2e dew=%.2e dzoi=%.2e dzf=%.2e', pn, br, r['sym'], r['d_net_ex'], r['d_ew'], r['d_zoi'], r['d_zf'])
    df = pd.DataFrame(res)
    df.to_csv(A1 + 'sample.csv', index=False)
    dc = [c for c in df.columns if c.startswith('d_')]
    s = {c: float(df[c].abs().max()) for c in dc}
    s['n'] = len(df)
    s['n_confirm'] = int((df['period'] == 'confirm').sum())
    s['ew_univ_mismatch'] = int((df['n_univ_px'] != df['n_ew_run']).sum())
    json.dump(s, open(A1 + 'sample.json', 'w'), indent=1)
    log.info('summary %s', s)


if __name__ == '__main__':
    main()
