"""LEVZ main (PREREG_LEVZ @5e1031bc). usage: python3 levz.py <explore|confirm>
explore: loads data only < 2024-02-01 (t0 in 2022-01-01..2023-12-31).
confirm: loads data < 2026-01-01 (t0 in 2024-01-01..2025-12-31).
Outputs: work/../out/events_<branch>_<period>.parquet, out/summary_<period>.json"""
import json
import logging
import math
import os
import sys
import numpy as np
import pandas as pd
import common as C

C.setup_log()
log = logging.getLogger('levz')
H = C.H_MS
H0 = 1638316800000  # 2021-12-01 00:00 UTC
OUT = '/home/ubuntu/claude_master/w3/levz/out'
PERIODS = {'explore': ('2022-01-01', '2024-01-01', '2024-01'),
           'confirm': ('2024-01-01', '2026-01-01', '2025-12')}
FEE = 0.0014
FEE_ST = 0.0024
HS = (4, 24, 72)
WS = (14, 7)
NBOOT = 10000
SEED = 20261125
Z_TH = 2.5
F_MIN = 0.0001
SD_OI_FLOOR = 0.02
SD_F_FLOOR = 0.00005
ZR_TH = -2.0
COOL_H = 72
E1_WIN = 24
MAIN = ['A1', 'A2', 'A3', 'A4']
BR = {'A1': (14, 'E0'), 'A2': (14, 'E1'), 'A3': (7, 'E0'), 'A4': (7, 'E1')}


def ms(s):
    return int(pd.Timestamp(s, tz='UTC').value // 10**6)


def next_month_ms(ym):
    y, m = int(ym[:4]), int(ym[5:])
    m += 1
    if m == 13:
        y, m = y + 1, 1
    return ms('%04d-%02d-01' % (y, m))


class Data:
    def __init__(self, end_ym):
        self.cut = next_month_ms(end_ym)
        assert self.cut <= C.CUTOFF_MS
        self.NH = (self.cut - H0) // H
        mons = C.months('2021-12', end_ym)
        syms = set()
        for ym in mons:
            syms |= set(pd.read_parquet('%s/hr_%s.parquet' % (C.WORK, ym), columns=['sym'])['sym'].astype(str).unique())
        self.syms = sorted(s for s in syms if C.sym_ok(s))
        self.col = {s: i for i, s in enumerate(self.syms)}
        ns, NH = len(self.syms), self.NH
        self.P0 = np.full((NH, ns), np.nan)
        self.CL = np.full((NH, ns), np.nan)
        self.CM = np.full((NH, ns), np.nan)
        for ym in mons:
            d = pd.read_parquet('%s/hr_%s.parquet' % (C.WORK, ym))
            d['sym'] = d['sym'].astype(str)
            d = d[d['sym'].isin(self.col) & (d['h'] >= H0) & (d['h'] < self.cut)]
            r = ((d['h'].values - H0) // H).astype(np.int64)
            c = d['sym'].map(self.col).values.astype(np.int64)
            self.P0[r, c] = d['p0'].values
            self.CL[r, c] = d['clast'].values
            self.CM[r, c] = d['cmax'].values
        self.X = np.full((NH, ns), np.nan)
        tsr = np.full((NH, ns), -1, dtype=np.int64)
        for ym in mons:
            d = pd.read_parquet('%s/oi_%s.parquet' % (C.WORK, ym))
            d['sym'] = d['sym'].astype(str)
            d = d[d['sym'].isin(self.col) & (d['h'] >= H0) & (d['h'] < self.cut)]
            r = ((d['h'].values - H0) // H).astype(np.int64)
            c = d['sym'].map(self.col).values.astype(np.int64)
            t = d['tsr'].values
            assert (t <= d['h'].values - 10 * C.M_MS).all() and (t > d['h'].values - 70 * C.M_MS).all()
            m = t > tsr[r, c]
            self.X[r[m], c[m]] = d['x'].values[m]
            tsr[r[m], c[m]] = t[m]
        del tsr
        # last close with open_time <= h
        a = self.P0.copy()
        prev = np.vstack([np.full((1, ns), np.nan), self.CL[:-1]])
        a = np.where(np.isfinite(a), a, prev)
        self.LAST = pd.DataFrame(a).ffill().values
        # universe
        u = C.universe_days(self.cut)
        u = u[u['sym'].isin(self.col)]
        self.U = np.zeros((NH, ns), dtype=bool)
        d0 = ((u['day'].values.astype('datetime64[ms]').astype(np.int64) - H0) // H).astype(np.int64)
        c = u['sym'].map(self.col).values.astype(np.int64)
        for k in range(24):
            r = d0 + k
            m = (r >= 0) & (r < NH)
            self.U[r[m], c[m]] = True
        # funding
        fl = []
        for y in range(2021, int(end_ym[:4]) + 1):
            f = C.read_funding(y, self.cut)
            fl.append(f)
        f = pd.concat(fl, ignore_index=True)
        f = f[f['sym'].isin(self.col) & np.isfinite(f['rate']) & (f['interval_h'] > 0)]
        f = f.sort_values(['sym', 'ts'], kind='mergesort').drop_duplicates(['sym', 'ts'], keep='last')
        self.F = {}
        for s, g in f.groupby('sym', sort=True):
            ts = g['ts'].values.astype(np.int64)
            rate = g['rate'].values.astype(np.float64)
            ih = g['interval_h'].values.astype(np.int64)
            self.F[self.col[s]] = dict(ts=ts, rate=rate, ih=ih, r8=rate * 8.0 / ih,
                                       crate=np.concatenate([[0.0], np.cumsum(rate)]))
        self.tms = H0 + np.arange(NH, dtype=np.int64) * H
        log.info('data loaded end=%s NH=%d ns=%d', end_ym, NH, ns)


def roll_z_inputs(A, Wh):
    mp = int(math.ceil(0.8 * Wh))
    r = pd.DataFrame(A).rolling(Wh, min_periods=mp)
    m = r.mean().shift(1).values
    sd = r.std(ddof=1).shift(1).values
    return m, sd


def oi_z(X, Wh):
    m, sd = roll_z_inputs(X, Wh)
    z = (X - m) / np.maximum(sd, SD_OI_FLOOR)
    return z, sd


def ret_z(CL, Wh):
    ns = CL.shape[1]
    cp = np.vstack([np.full((1, ns), np.nan), CL[:-1]])  # close of hour candle [t-1h, t)
    r1 = np.full_like(cp, np.nan)
    r1[1:] = cp[1:] / cp[:-1] - 1.0
    m, sd = roll_z_inputs(r1, Wh)
    with np.errstate(divide='ignore', invalid='ignore'):
        z = np.where(sd > 0, r1 / sd, np.nan)
    return z


def fund_z(fs, tms, Wh):
    """f(t) = r8 of latest settlement with ts <= t-1min (must be current: t - ts <= ih h + 1min);
    z_f over settlements in [t-W, latest) (latest excluded); need n >= 0.8 * W/ih(latest)."""
    NH = len(tms)
    ts, r8, ih = fs['ts'], fs['r8'], fs['ih']
    j = np.searchsorted(ts, tms - C.M_MS, side='right') - 1
    valid = j >= 0
    jj = np.clip(j, 0, None)
    fresh = valid & ((tms - ts[jj]) <= ih[jj] * H + C.M_MS)
    lo = np.searchsorted(ts, tms - Wh * H, side='left')
    n = (jj - lo).astype(np.float64)
    c = float(r8.mean())
    y = r8 - c
    S1 = np.concatenate([[0.0], np.cumsum(y)])
    S2 = np.concatenate([[0.0], np.cumsum(y * y)])
    s1 = S1[jj] - S1[np.minimum(lo, jj)]
    s2 = S2[jj] - S2[np.minimum(lo, jj)]
    with np.errstate(divide='ignore', invalid='ignore'):
        mean = s1 / n + c
        var = (s2 - s1 * s1 / n) / (n - 1)
    sd = np.sqrt(np.maximum(var, 0.0))
    ok = fresh & (n >= 2) & (n >= 0.8 * (Wh / ih[jj]))
    f = np.where(fresh, r8[jj], np.nan)
    z = np.where(ok, (f - mean) / np.maximum(sd, SD_F_FLOOR), np.nan)
    sd = np.where(ok, sd, np.nan)
    return f, z, sd


def signals(D, W):
    Wh = W * 24
    zoi, sdoi = oi_z(D.X, Wh)
    zr = ret_z(D.CL, Wh)
    NH, ns = D.X.shape
    F = np.full((NH, ns), np.nan)
    ZF = np.full((NH, ns), np.nan)
    SDF = np.full((NH, ns), np.nan)
    for c, fs in D.F.items():
        f, z, sd = fund_z(fs, D.tms, Wh)
        F[:, c], ZF[:, c], SDF[:, c] = f, z, sd
    doi = np.full((NH, ns), np.nan)
    doi[24:] = np.exp(D.X[24:] - D.X[:-24]) - 1.0
    return dict(zoi=zoi, sdoi=sdoi, zr=zr, f=F, zf=ZF, sdf=SDF, doi=doi)


def episodes(cond):
    out = []
    rows, cols = np.nonzero(cond)
    order = np.lexsort((rows, cols))
    rows, cols = rows[order], cols[order]
    last = {}
    for r, c in zip(rows.tolist(), cols.tolist()):
        lr = last.get(c)
        if lr is None or r - lr > COOL_H:
            out.append((r, c))
            last[c] = r
    out.sort()
    return out


def e1_entry(zr, r, c):
    NH = zr.shape[0]
    for k in range(1, E1_WIN + 1):
        rr = r + k
        if rr >= NH:
            return None, None
        v = zr[rr, c]
        if np.isfinite(v) and v <= ZR_TH:
            return rr, k
    return None, None


def fund_sum(fs, a_ms, b_ms):
    """sum of rate for settlements with ts in (a, b]."""
    if fs is None:
        return 0.0
    i = np.searchsorted(fs['ts'], a_ms, side='right')
    j = np.searchsorted(fs['ts'], b_ms, side='right')
    return float(fs['crate'][j] - fs['crate'][i])


def outcomes(D, ev, side):
    """side = -1 short, +1 long. ev: list of dict(r0, c, re, ...). Returns DataFrame."""
    NH = D.NH
    rows = []
    for e in ev:
        c, re = e['c'], e['re']
        p0 = D.P0[re, c]
        if not np.isfinite(p0):
            e['nop'] = 1
            rows.append(e)
            continue
        e['nop'] = 0
        e['p_te'] = p0
        te_ms = int(D.tms[re])
        fs = D.F.get(c)
        uc = D.U[re] & np.isfinite(D.P0[re])
        for Hh in HS:
            rend = re + Hh
            sub = 0
            if rend < NH and np.isfinite(D.P0[rend, c]):
                p1 = D.P0[rend, c]
            else:
                p1 = D.LAST[min(rend, NH - 1), c]
                sub = 1
            ret = p1 / p0 - 1.0
            gross = side * ret
            # holding = fill at close of 1m candle te (te+1m) .. close of candle te+H (te+H+1m)
            fsum = fund_sum(fs, te_ms + C.M_MS, te_ms + Hh * H + C.M_MS)
            flit = fund_sum(fs, te_ms, te_ms + Hh * H)
            fund = -side * fsum
            net = gross - FEE + fund
            ri = min(rend, NH - 1)
            ew = float(np.mean(D.LAST[ri, uc] / D.P0[re, uc] - 1.0)) if uc.any() else np.nan
            nex = net - side * ew
            if side < 0:
                mae = float(np.nanmax(D.CM[re:min(rend, NH), c]) / p0 - 1.0)
            else:
                mae = np.nan
            e.update({'p_end_%d' % Hh: p1, 'sub_%d' % Hh: sub, 'gross_%d' % Hh: gross, 'fund_%d' % Hh: fund,
                      'fund_lit_%d' % Hh: -side * flit, 'net_%d' % Hh: net, 'ew_%d' % Hh: ew,
                      'net_ex_%d' % Hh: nex, 'mae_%d' % Hh: mae, 'n_ew_%d' % Hh: int(uc.sum())})
        rows.append(e)
    return pd.DataFrame(rows)


def boot(x, wk):
    x = np.asarray(x, dtype=np.float64)
    if len(x) < 2:
        return dict(ci_lo=np.nan, ci_hi=np.nan, p=np.nan, se=np.nan, mde80=np.nan, nweeks=int(len(set(wk))))
    uw, inv = np.unique(wk, return_inverse=True)
    sums = np.bincount(inv, weights=x)
    cnt = np.bincount(inv).astype(np.float64)
    K = len(uw)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, K, size=(NBOOT, K))
    bm = sums[idx].sum(1) / cnt[idx].sum(1)
    obs = x.mean()
    p = (1.0 + np.sum(bm - obs >= obs)) / (NBOOT + 1.0)
    se = float(bm.std(ddof=1))
    return dict(ci_lo=float(np.percentile(bm, 2.5)), ci_hi=float(np.percentile(bm, 97.5)), p=float(p), se=se,
                mde80=float((1.6448536269514722 + 0.8416212335729143) * se), nweeks=int(K))


def week_of(ms_arr):
    d = np.asarray(ms_arr, dtype=np.int64) // 86400000
    return (d + 3) // 7  # Monday-start calendar weeks


def summarize(df, side):
    s = {'n_episodes': int(len(df))}
    if len(df) == 0 or 'net_ex_24' not in df:
        s['n'] = 0
        return s
    d = df[df['nop'] == 0]
    s['n'] = int(len(d))
    s['n_noprice'] = int((df['nop'] == 1).sum())
    if len(d) == 0:
        return s
    for Hh in HS:
        k = '_%d' % Hh
        s['mean_net_ex' + k] = float(d['net_ex' + k].mean())
        s['median_net_ex' + k] = float(d['net_ex' + k].median())
        s['mean_net' + k] = float(d['net' + k].mean())
        s['mean_gross' + k] = float(d['gross' + k].mean())
        s['mean_fund' + k] = float(d['fund' + k].mean())
        s['mean_fund_lit' + k] = float(d['fund_lit' + k].mean())
        s['mean_ew' + k] = float(d['ew' + k].mean())
        s['mean_net_ex_stress' + k] = float((d['net_ex' + k] - (FEE_ST - FEE)).mean())
        s['mean_net_stress' + k] = float((d['net' + k] - (FEE_ST - FEE)).mean())
        s['n_sub' + k] = int(d['sub' + k].sum())
        if side < 0:
            s['mae10' + k] = float((d['mae' + k] >= 0.10).mean())
            s['mae20' + k] = float((d['mae' + k] >= 0.20).mean())
    s.update(boot(d['net_ex_24'].values, week_of(d['te'].values)))
    yr = pd.to_datetime(d['t0'], unit='ms').dt.year
    s['by_year'] = {str(y): {'n': int((yr == y).sum()), 'mean_net_ex_24': float(d.loc[yr == y, 'net_ex_24'].mean())}
                    for y in sorted(yr.unique())}
    v = np.sort(d['net_ex_24'].values)[::-1]
    k5 = int(math.ceil(0.05 * len(v)))
    s['mean_net_ex_24_drop_top5'] = float(v[k5:].mean()) if len(v) > k5 else np.nan
    return s


def holm(ps):
    keys = sorted(ps, key=lambda k: (ps[k], k))
    m = len(keys)
    out, run = {}, 0.0
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (m - i) * ps[k]))
        out[k] = run
    return out


def run(period):
    p_a, p_b, end_ym = PERIODS[period]
    ra, rb = (ms(p_a) - H0) // H, (ms(p_b) - H0) // H
    D = Data(end_ym)
    os.makedirs(OUT, exist_ok=True)
    summ = {'period': period, 't0_from': p_a, 't0_to_excl': p_b, 'data_end_month': end_ym, 'branches': {}, 'desc': {}, 'v4': {}}
    S = {}
    for W in WS:
        S[W] = signals(D, W)
    branches = {}
    for W in WS:
        g = S[W]
        fin = D.U & np.isfinite(g['zoi']) & np.isfinite(g['zf'])
        branches['W%d_lev' % W] = ('short', fin & (g['zoi'] > Z_TH) & (g['zf'] > Z_TH) & (g['f'] > F_MIN), W)
        branches['D_W%d_mirror' % W] = ('long', fin & (g['zoi'] > Z_TH) & (g['zf'] < -Z_TH) & (g['f'] < 0), W)
        branches['D_W%d_only_zoi' % W] = ('short', D.U & np.isfinite(g['zoi']) & (g['zoi'] > Z_TH), W)
        branches['D_W%d_only_zf' % W] = ('short', D.U & np.isfinite(g['zf']) & (g['zf'] > Z_TH), W)
    g = S[14]
    branches['D_hard'] = ('short', D.U & np.isfinite(g['f']) & np.isfinite(g['doi']) & (g['f'] >= 0.0005) & (g['doi'] >= 0.25), 14)
    results = {}
    for name, (sd, cond, W) in branches.items():
        g = S[W]
        eps = [(r, c) for r, c in episodes(cond) if ra <= r < rb]
        side = -1 if sd == 'short' else 1
        modes = ['E0', 'E1'] if name.startswith('W') else ['E0']
        for mode in modes:
            ev = []
            nconf, lags = 0, []
            for r, c in eps:
                e = dict(sym=D.syms[c], c=c, r0=r, t0=int(D.tms[r]), z_oi=float(g['zoi'][r, c]), z_f=float(g['zf'][r, c]),
                         f=float(g['f'][r, c]), sd_oi=float(g['sdoi'][r, c]), sd_f=float(g['sdf'][r, c]),
                         doi24=float(g['doi'][r, c]))
                if mode == 'E0':
                    e['re'] = r
                    e['lag_h'] = 0
                else:
                    re, lag = e1_entry(g['zr'], r, c)
                    if re is None:
                        continue
                    nconf += 1
                    lags.append(lag)
                    e['re'] = re
                    e['lag_h'] = lag
                    e['z_r'] = float(g['zr'][re, c])
                e['te'] = int(D.tms[e['re']])
                ev.append(e)
            df = outcomes(D, ev, side)
            if name.startswith('W'):
                key = [k for k, v in BR.items() if v == (W, mode)][0]
            else:
                key = name
            results[key] = df
            sm = summarize(df, side)
            sm['n_t0_episodes'] = len(eps)
            if mode == 'E1':
                sm['e1_confirmed'] = nconf
                sm['e1_confirm_rate'] = nconf / len(eps) if eps else np.nan
                sm['e1_lag_median_h'] = float(np.median(lags)) if lags else np.nan
            if key in BR:
                summ['branches'][key] = sm
            else:
                summ['desc'][key] = sm
            if key in BR or key == 'D_hard':
                cols = ['sym', 't0', 'te', 'lag_h', 'z_oi', 'z_f', 'f', 'sd_oi', 'sd_f', 'doi24', 'nop', 'p_te']
                if mode == 'E1':
                    cols.append('z_r')
                for Hh in HS:
                    cols += [x + '_%d' % Hh for x in ('p_end', 'sub', 'gross', 'fund', 'fund_lit', 'net', 'ew', 'net_ex', 'mae', 'n_ew')]
                out = df[[x for x in cols if x in df.columns]] if len(df) else pd.DataFrame(columns=cols)
                out.to_parquet('%s/events_%s_%s.parquet' % (OUT, key, period), index=False)
            # V4 descriptors at t0 (episode level)
            if mode == 'E0' and name.startswith('W'):
                yrs = pd.Series([pd.Timestamp(D.tms[r], unit='ms').year for r, c in eps])
                zo = np.array([g['sdoi'][r, c] for r, c in eps])
                zf = np.array([g['sdf'][r, c] for r, c in eps])
                ff = np.array([g['f'][r, c] for r, c in eps])
                dd = np.array([g['doi'][r, c] for r, c in eps])
                q = [0.05, 0.25, 0.5, 0.75, 0.95]
                summ['v4'][name] = dict(
                    episodes_by_year={str(k): int(v) for k, v in yrs.value_counts().sort_index().items()},
                    floor_oi_rate=float(np.mean(zo < SD_OI_FLOOR)) if len(eps) else np.nan,
                    floor_f_rate=float(np.mean(zf < SD_F_FLOOR)) if len(eps) else np.nan,
                    floor_any_rate=float(np.mean((zo < SD_OI_FLOOR) | (zf < SD_F_FLOOR))) if len(eps) else np.nan,
                    f_q=[float(v) for v in np.nanquantile(ff, q)] if len(eps) else [],
                    doi24_q=[float(v) for v in np.nanquantile(dd, q)] if len(eps) else [])
    if period == 'confirm':
        ph = holm({k: summ['branches'][k]['p'] for k in MAIN})
        for k in MAIN:
            summ['branches'][k]['p_holm'] = ph[k]
    with open('%s/summary_%s.json' % (OUT, period), 'w') as fh:
        json.dump(summ, fh, indent=1, sort_keys=True, default=float)
    for k in MAIN:
        b = summ['branches'][k]
        log.info('%s %s n=%s mean_net_ex_24=%s p=%s', period, k, b.get('n'), b.get('mean_net_ex_24'), b.get('p'))
    log.info('done %s', period)


if __name__ == '__main__':
    run(sys.argv[1])
