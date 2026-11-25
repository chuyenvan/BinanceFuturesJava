"""A1 independent recompute of LEVZ (prereg @5e1031bc). Own code, no import of RUN code.
Builds hourly panels from raw files, signals, episodes, outcomes, then compares to RUN events and computes stats.
usage: python3 recalc.py build   -> a1/panel.npz
       python3 recalc.py run     -> a1/ev_*.parquet, a1/recalc.json"""
import json
import logging
import math
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('a1')
CUT = 1767225600000
H = 3600000
M = 60000
T0 = 1638316800000
KL = '/home/ubuntu/claude_master/res1109/r1_s1/kl/kline1m-%s.parquet'
MET = '/home/ubuntu/vz/out/metrics5m/%s/%s.parquet'
FU = '/home/ubuntu/claude_master/1016/carry/fund/funding-%d.parquet'
D1 = '/home/ubuntu/claude_master/1016/screen/d1.parquet'
A1 = '/home/ubuntu/claude_master/w3/levz/a1/'
RUNOUT = '/home/ubuntu/claude_master/w3/levz/out/'
NH = (CUT - T0) // H
BAD = {'USDC', 'BUSD', 'TUSD', 'FDUSD', 'USDP', 'DAI', 'UST', 'USDE', 'EUR', 'AEUR', 'BTCDOM', 'DEFI', 'BLUEBIRD', 'FOOTBALL'}


def mlist():
    out = ['2021-12']
    for y in range(2022, 2026):
        for m in range(1, 13):
            out.append('%d-%02d' % (y, m))
    return out


def okname(s):
    return s.endswith('USDT') and '_' not in s and s[:-4] not in BAD


def rd(path, cols, tcol='ts'):
    t = pq.read_table(path, columns=cols, filters=[(tcol, '<', CUT)])
    df = t.to_pandas()
    assert len(df) == 0 or int(df[tcol].max()) < CUT
    return df


def build():
    syms = set()
    for ym in mlist():
        s = pq.read_table(KL % ym, columns=['sym']).column('sym').unique().to_pylist()
        syms |= set(str(x) for x in s)
    syms = sorted(x for x in syms if okname(x))
    col = {s: i for i, s in enumerate(syms)}
    ns = len(syms)
    P0 = np.full((NH, ns), np.nan)
    CL = np.full((NH, ns), np.nan)
    CM = np.full((NH, ns), np.nan)
    for ym in mlist():
        k = rd(KL % ym, ['ts', 'sym', 'close'])
        c = k['sym'].astype(str).map(col)
        m = c.notna().values & np.isfinite(k['close'].values) & (k['close'].values > 0)
        ts = k['ts'].values[m].astype(np.int64)
        cc = c.values[m].astype(np.int64)
        px = k['close'].values[m]
        del k, c
        r = (ts - T0) // H
        key = r * ns + cc
        o = np.lexsort((ts, key))
        key, ts, px, r, cc = key[o], ts[o], px[o], r[o], cc[o]
        last = np.r_[key[1:] != key[:-1], True]
        CL[r[last], cc[last]] = px[last]
        mx = pd.Series(px).groupby(key).max()
        kk = mx.index.values
        CM[kk // ns, kk % ns] = mx.values
        z = (ts % H) == 0
        P0[r[z], cc[z]] = px[z]
        log.info('kline %s', ym)
    XR = np.full((NH, ns), np.nan)
    TR = np.full((NH, ns), -1, dtype=np.int64)
    for ym in mlist():
        d = rd(MET % (ym[:4], ym), ['ts', 'sym', 'oi'])
        c = d['sym'].astype(str).map(col)
        m = c.notna().values & np.isfinite(d['oi'].values) & (d['oi'].values > 0)
        ts = d['ts'].values[m].astype(np.int64)
        cc = c.values[m].astype(np.int64)
        oi = d['oi'].values[m]
        # first hour h with ts <= h - 10m
        r = -((-(ts + 10 * M - T0)) // H)
        ok = (r >= 0) & (r < NH)
        ts, cc, oi, r = ts[ok], cc[ok], oi[ok], r[ok]
        key = r * ns + cc
        o = np.lexsort((ts, key))
        ts, cc, oi, r, key = ts[o], cc[o], oi[o], r[o], key[o]
        lst = np.r_[key[1:] != key[:-1], True]
        ts, cc, oi, r = ts[lst], cc[lst], oi[lst], r[lst]
        newer = ts > TR[r, cc]
        XR[r[newer], cc[newer]] = np.log(oi[newer])
        TR[r[newer], cc[newer]] = ts[newer]
        assert (TR[r, cc] <= r * H + T0 - 10 * M).all()
        log.info('oi %s', ym)
    np.savez(A1 + 'panel.npz', P0=P0, CL=CL, CM=CM, XR=XR, TR=TR, syms=np.array(syms))
    log.info('saved ns=%d', ns)


def universe(syms):
    t = pq.read_table(D1, columns=['sym', 'day', 'qv'], filters=[('day', '<', pd.Timestamp(CUT, unit='ms'))])
    d = t.to_pandas()
    assert d['day'].max() < pd.Timestamp('2026-01-01')
    col = {s: i for i, s in enumerate(syms)}
    U = np.zeros((NH, len(syms)), dtype=bool)
    for s, g in d.groupby('sym'):
        if s not in col:
            continue
        q = g.drop_duplicates('day').set_index('day')['qv'].sort_index()
        full = pd.date_range(q.index[0], q.index[-1], freq='D')
        q = q.reindex(full)
        prev30 = q.shift(1).rolling(30, min_periods=30).mean()
        days = full[(prev30.values >= 20e6) & (full - full[0] >= pd.Timedelta(days=45))]
        for dd in days:
            r = (int(dd.value // 10**6) - T0) // H
            if 0 <= r and r + 24 <= NH:
                U[r:r + 24, col[s]] = True
            elif 0 <= r < NH:
                U[r:NH, col[s]] = True
    return U


def funding(syms):
    col = {s: i for i, s in enumerate(syms)}
    f = pd.concat([rd(FU % y, ['ts', 'sym', 'interval_h', 'rate']) for y in range(2021, 2026)], ignore_index=True)
    f['sym'] = f['sym'].astype(str)
    f = f[f['sym'].isin(col) & np.isfinite(f['rate']) & (f['interval_h'] > 0)]
    f = f.sort_values(['sym', 'ts']).drop_duplicates(['sym', 'ts'], keep='last')
    out = {}
    for s, g in f.groupby('sym'):
        ts = g['ts'].values.astype(np.int64)
        rate = g['rate'].values.astype(float)
        ih = g['interval_h'].values.astype(float)
        out[col[s]] = (ts, rate, ih, rate * 8.0 / ih, np.r_[0.0, np.cumsum(rate)])
    return out


def zroll(A, Wh):
    mp = int(math.ceil(0.8 * Wh))
    S = pd.DataFrame(A).shift(1).rolling(Wh, min_periods=mp)
    return S.mean().values, S.std(ddof=1).values


def zf_col(fs, tms, Wh, fresh_rule):
    ts, rate, ih, r8, _ = fs
    j = np.searchsorted(ts, tms - M, side='right') - 1
    has = j >= 0
    j = np.maximum(j, 0)
    lo = np.searchsorted(ts, tms - Wh * H, side='left')
    lo = np.minimum(lo, j)
    n = (j - lo).astype(float)
    c0 = r8.mean()
    y = r8 - c0
    s1 = np.r_[0.0, np.cumsum(y)]
    s2 = np.r_[0.0, np.cumsum(y * y)]
    a = s1[j] - s1[lo]
    b = s2[j] - s2[lo]
    with np.errstate(all='ignore'):
        mu = a / n + c0
        sd = np.sqrt(np.maximum((b - a * a / n) / (n - 1), 0))
    f = np.where(has, r8[j], np.nan)
    if fresh_rule:
        f = np.where(has & (tms - ts[j] <= ih[j] * H + M), f, np.nan)
    ok = np.isfinite(f) & (n >= 2) & (n >= 0.8 * Wh / ih[j])
    z = np.where(ok, (f - mu) / np.maximum(sd, 0.00005), np.nan)
    return f, z


def fsum(fs, a, b):
    if fs is None:
        return 0.0
    ts, cr = fs[0], fs[4]
    return float(cr[np.searchsorted(ts, b, 'right')] - cr[np.searchsorted(ts, a, 'right')])


def week(ms):
    return (np.asarray(ms) // 86400000 + 3) // 7


def boot(x, wk, seed=777, nb=10000):
    u, inv = np.unique(wk, return_inverse=True)
    sm = np.bincount(inv, weights=x)
    ct = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(u), size=(nb, len(u)))
    bm = sm[idx].sum(1) / ct[idx].sum(1)
    o = x.mean()
    return float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5)), float((1 + np.sum(bm - o >= o)) / (nb + 1))


def run():
    z = np.load(A1 + 'panel.npz')
    P0, CL, CM, XR, TR = z['P0'], z['CL'], z['CM'], z['XR'], z['TR']
    syms = [str(s) for s in z['syms']]
    ns = len(syms)
    tms = T0 + np.arange(NH, dtype=np.int64) * H
    U = universe(syms)
    F = funding(syms)
    log.info('loaded')
    # literal OI: latest record ts <= t-10m, no staleness bound
    XL = pd.DataFrame(XR).ffill().values
    # last close with open_time <= h
    prevCL = np.vstack([np.full((1, ns), np.nan), CL[:-1]])
    LAST = pd.DataFrame(np.where(np.isfinite(P0), P0, prevCL)).ffill().values
    # hourly return for z_r: close(t)=CL[r-1]
    c1 = prevCL
    r1 = np.full((NH, ns), np.nan)
    r1[1:] = c1[1:] / c1[:-1] - 1
    variants = {'R': dict(X=XR, fresh=True), 'L': dict(X=XL, fresh=False)}
    allres = {}
    for vn, vv in variants.items():
        for W in (14, 7):
            Wh = W * 24
            mu, sd = zroll(vv['X'], Wh)
            zoi = (vv['X'] - mu) / np.maximum(sd, 0.02)
            del mu, sd
            mr, sr = zroll(r1, Wh)
            del mr
            with np.errstate(all='ignore'):
                zr = np.where(sr > 0, r1 / sr, np.nan)
            del sr
            ff = np.full((NH, ns), np.nan)
            zf = np.full((NH, ns), np.nan)
            for c, fs in F.items():
                ff[:, c], zf[:, c] = zf_col(fs, tms, Wh, vv['fresh'])
            cond = U & (zoi > 2.5) & (zf > 2.5) & (ff > 0.0001)
            rows, cols = np.nonzero(cond)
            o = np.lexsort((rows, cols))
            eps, lastr = [], {}
            for r, c in zip(rows[o].tolist(), cols[o].tolist()):
                if c not in lastr or r - lastr[c] > 72:
                    eps.append((r, c))
                    lastr[c] = r
            for mode in ('E0', 'E1'):
                recs = []
                for r, c in eps:
                    if mode == 'E0':
                        re = r
                    else:
                        re = None
                        for kk in range(1, 25):
                            if r + kk < NH and np.isfinite(zr[r + kk, c]) and zr[r + kk, c] <= -2:
                                re = r + kk
                                break
                        if re is None:
                            continue
                    p0 = P0[re, c]
                    if not np.isfinite(p0):
                        continue
                    rec = dict(sym=syms[c], t0=int(tms[r]), te=int(tms[re]), z_oi=float(zoi[r, c]), z_f=float(zf[r, c]),
                               f=float(ff[r, c]), p_te=float(p0), oi_age_min=float((tms[r] - TR[r, c]) / M) if TR[r, c] > 0 else np.nan)
                    uc = U[re] & np.isfinite(P0[re])
                    rec['n_univ_te'] = int(U[re].sum())
                    rec['n_univ_noprice'] = int((U[re] & ~np.isfinite(P0[re])).sum())
                    for Hh in (24,):
                        e = re + Hh
                        if e < NH and np.isfinite(P0[e, c]):
                            p1 = P0[e, c]
                        elif e < NH:
                            p1 = LAST[e, c]
                        else:
                            p1 = CL[NH - 1, c] if np.isfinite(CL[NH - 1, c]) else LAST[NH - 1, c]
                        if e < NH:
                            pe = np.where(np.isfinite(P0[e]), P0[e], LAST[e])
                        else:
                            pe = np.where(np.isfinite(CL[NH - 1]), CL[NH - 1], LAST[NH - 1])
                        ew = float(np.mean(pe[uc] / P0[re, uc] - 1))
                        g = -(p1 / p0 - 1)
                        fr = fsum(F.get(c), tms[re] + M, tms[re] + Hh * H + M)
                        fl = fsum(F.get(c), tms[re], tms[re] + Hh * H)
                        rec.update({'p_end_24': float(p1), 'gross_24': g, 'fund_24': fr, 'fund_lit_24': fl, 'ew_24': ew,
                                    'net_24': g - 0.0014 + fr, 'net_ex_24': g - 0.0014 + fr + ew,
                                    'net_ex_lit_24': g - 0.0014 + fl + ew,
                                    'mae_24': float(np.nanmax(CM[re:min(e, NH), c]) / p0 - 1)})
                    recs.append(rec)
                df = pd.DataFrame(recs)
                br = {(14, 'E0'): 'A1', (14, 'E1'): 'A2', (7, 'E0'): 'A3', (7, 'E1'): 'A4'}[(W, mode)]
                df.to_parquet(A1 + 'ev_%s_%s.parquet' % (vn, br), index=False)
                allres[(vn, br)] = df
                log.info('%s %s n=%d', vn, br, len(df))
            del zoi, zr, ff, zf, cond
    # compare + stats
    P = {'explore': (1640995200000, 1704067200000), 'confirm': (1704067200000, CUT)}
    cmp_, st = {}, {}
    for (vn, br), df in allres.items():
        for pn, (a, b) in P.items():
            d = df[(df['t0'] >= a) & (df['t0'] < b)].copy()
            key = '%s_%s_%s' % (vn, br, pn)
            if vn == 'R':
                rr = pd.read_parquet(RUNOUT + 'events_%s_%s.parquet' % (br, pn))
                rr = rr[rr['nop'] == 0]
                mg = d.merge(rr, on=['sym', 't0', 'te'], how='outer', suffixes=('', '_run'), indicator=True)
                both = mg[mg['_merge'] == 'both']
                cmp_[key] = dict(n_a1=len(d), n_run=len(rr), both=len(both),
                                 a1_only=mg.loc[mg['_merge'] == 'left_only', ['sym', 't0']].astype(str).values.tolist()[:10],
                                 run_only=mg.loc[mg['_merge'] == 'right_only', ['sym', 't0']].astype(str).values.tolist()[:10],
                                 **{'maxabs_' + x: float(np.nanmax(np.abs(both[x] - both[x + '_run']))) if len(both) else None
                                    for x in ('z_oi', 'z_f', 'f', 'p_te', 'p_end_24', 'gross_24', 'fund_24', 'fund_lit_24', 'ew_24', 'net_ex_24', 'mae_24')})
            st[key] = stats(d)
            st[key + '_fundlit'] = stats(d.assign(net_ex_24=d['net_ex_lit_24'], net_24=d['net_24'] - d['fund_24'] + d['fund_lit_24']))
    json.dump(dict(cmp=cmp_, stats=st), open(A1 + 'recalc.json', 'w'), indent=1, default=float)
    log.info('done')


def stats(d):
    if len(d) == 0:
        return dict(n=0)
    x = d['net_ex_24'].values
    lo, hi, p = boot(x, week(d['te'].values))
    v = np.sort(x)[::-1]
    k5 = int(math.ceil(0.05 * len(v)))
    yr = pd.to_datetime(d['t0'], unit='ms').dt.year
    return dict(n=len(d), mean=float(x.mean()), median=float(np.median(x)), ci=[lo, hi], p=p, drop5=float(v[k5:].mean()),
                net=float(d['net_24'].mean()), gross=float(d['gross_24'].mean()), ew=float(d['ew_24'].mean()),
                fund=float(d['fund_24'].mean()), fund_lit=float(d['fund_lit_24'].mean()),
                stress=float(x.mean() - 0.001), mae10=float((d['mae_24'] >= 0.10).mean()),
                gross_minus_ew=float((d['gross_24'] + d['ew_24']).mean()),
                frac_gross_pos=float((d['gross_24'] > 0).mean()),
                by_year={str(y): [int((yr == y).sum()), float(x[(yr == y).values].mean())] for y in sorted(yr.unique())})


if __name__ == '__main__':
    build() if sys.argv[1] == 'build' else run()
