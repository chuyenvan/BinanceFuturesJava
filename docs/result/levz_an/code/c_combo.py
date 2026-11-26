"""C step 2: LONG (4 runs, MTM daily) x SHORT (cfg 4107, 5204, 3550 + 50 family) on the SAME capital, 2022-01-01..2025-12-31.
Short daily equity = levz_b1 port hourly MTM eq at 00:00 UTC boundaries (last day ends at 2025-12-31 23:00, the fold end mark).
Combined daily return = r_long + m x r_short (both sleeves sized off the same capital, daily-rebalanced approximation),
m in {0.5, 1.0, 1.5}; no weight optimisation. Exposure = |notional| / equity per sleeve; combined gross = long + m x short.
Conflicts: short trade interval overlapping a long position (union of long legs) on the same symbol.
Outputs out/c_pairs.parquet (one row per long run x short cfg x period), out/c_combo.parquet (metrics per run x cfg x m),
out/c_tail.parquet, out/c_conflicts.parquet, out/c_short_daily.parquet."""
import sys
import os
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.c_combo')
MS = (0.5, 1.0, 1.5)


def perf(r):
    r = np.asarray(r, dtype=np.float64)
    eq = np.cumprod(1 + r)
    yrs = len(r) / 365.0
    cagr = eq[-1] ** (1 / yrs) - 1 if eq[-1] > 0 else -1.0
    pk = np.maximum.accumulate(np.concatenate([[1.0], eq]))
    dd = float(np.max(1 - np.concatenate([[1.0], eq]) / pk))
    sh = float(np.mean(r) / np.std(r, ddof=1) * np.sqrt(365)) if np.std(r) > 0 else np.nan
    return dict(tot=float(eq[-1] - 1), cagr=float(cagr), maxdd=dd, calmar=float(cagr / dd) if dd > 0 else np.nan, sharpe=sh)


def merge_iv(a):
    a = sorted(a)
    out = []
    for s, e in a:
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def main():
    A.setup_log('c_combo')
    ld = pd.read_parquet(A.OUT + '/c_long_daily.parquet')
    lh = pd.read_parquet(A.OUT + '/c_long_hourly.parquet')
    legs = pd.read_parquet(A.OUT + '/c_long_legs.parquet')
    eqh = pd.read_parquet(A.OUT + '/a_eq_hourly.parquet')
    tr = pd.read_parquet(A.OUT + '/a_trades.parquet')
    with open(A.OUT + '/a_check.json') as fh:
        ck = json.load(fh)
    cfgs = ck['cfgs']
    fam = ck['family']
    k0, kl = A.dev_k()
    days = pd.date_range('2022-01-01', '2025-12-31', freq='D', tz='UTC')
    # short daily
    sd = {}
    rows = []
    for cfg in cfgs:
        e = eqh[eqh['cfg_id'] == cfg].reset_index(drop=True)
        assert len(e) == kl - k0 + 1
        t = A.dts(e['t'])
        b = e['eq'].values[(t.hour == 0)]
        assert len(b) == len(days)
        eend = np.concatenate([b[1:], [e['eq'].values[-1]]])
        r = eend / b - 1
        nopen = e['n_open'].values
        sd[cfg] = dict(r=r, expo=e['expo'].fillna(0).values, active=nopen > 0, expo_d=pd.Series(e['expo'].fillna(0).values).groupby(t.floor('D').values).mean().values)
        rows.append(pd.DataFrame({'cfg_id': cfg, 'd': days, 'r': r, 'expo_mean': sd[cfg]['expo_d']}))
    pd.concat(rows).to_parquet(A.OUT + '/c_short_daily.parquet', index=False)
    hrs = A.H0 + np.arange(k0, kl + 1, dtype=np.int64) * A.H
    yrs_h = A.dts(hrs).year.values
    yrs_d = days.year.values
    pairs, combo, tail, conf = [], [], [], []
    for run in A.LONG_RUNS:
        L = ld[ld['run'] == run].reset_index(drop=True)
        assert len(L) == len(days)
        rl = (L['eq_mtm'] / L['eq_mtm_prev'] - 1).values
        rl_real = (L['eq_real'] / L['eq_real_prev'] - 1).values
        H = lh[lh['run'] == run].reset_index(drop=True)
        assert len(H) == len(hrs)
        lexpo = H['expo'].values
        lact = H['n_open'].values > 0
        lexpo_d = L['expo_mean'].values
        # long position intervals per symbol (union of legs)
        lg = legs[legs['run'] == run]
        liv = {s: merge_iv(list(zip(v['ts'].tolist(), v['te'].tolist()))) for s, v in lg.groupby('usym')}
        for cfg in cfgs:
            S = sd[cfg]
            rs = S['r']
            for per in ('all', 2022, 2023, 2024, 2025):
                md = np.ones(len(days), bool) if per == 'all' else (yrs_d == per)
                mh = np.ones(len(hrs), bool) if per == 'all' else (yrs_h == per)
                a, b = pd.Series(rl[md], index=days[md]), pd.Series(rs[md], index=days[md])
                wk = pd.DataFrame({'a': (1 + a).resample('W').prod() - 1, 'b': (1 + b).resample('W').prod() - 1})
                mo = pd.DataFrame({'a': (1 + a).resample('MS').prod() - 1, 'b': (1 + b).resample('MS').prod() - 1})
                g1 = lexpo[mh] + S['expo'][mh]
                pairs.append(dict(run=run, cfg_id=cfg, period=str(per), corr_d=float(np.corrcoef(a, b)[0, 1]) if b.std() > 0 else np.nan,
                                  corr_d_real=float(np.corrcoef(rl_real[md], rs[md])[0, 1]) if b.std() > 0 else np.nan,
                                  corr_w=float(wk['a'].corr(wk['b'])), corr_m=float(mo['a'].corr(mo['b'])) if len(mo) > 2 else np.nan,
                                  both_active=float((lact[mh] & S['active'][mh]).mean()), long_active=float(lact[mh].mean()),
                                  short_active=float(S['active'][mh].mean()),
                                  long_active_given_short=float(lact[mh][S['active'][mh]].mean()) if S['active'][mh].any() else np.nan,
                                  gross_max=float(g1.max()), gross_p50=float(np.median(g1)), gross_p95=float(np.quantile(g1, 0.95)),
                                  gross_p99=float(np.quantile(g1, 0.99)), long_expo_max=float(lexpo[mh].max()), short_expo_max=float(S['expo'][mh].max())))
            # combined portfolios (full period + per year)
            for m in MS:
                rc = rl + m * rs
                for per in ('all', 2022, 2023, 2024, 2025):
                    md = np.ones(len(days), bool) if per == 'all' else (yrs_d == per)
                    row = dict(run=run, cfg_id=cfg, m=m, period=str(per))
                    for nm, x in (('L', rl[md]), ('S', m * rs[md]), ('C', rc[md])):
                        for kk, v in perf(x).items():
                            row[nm + '_' + kk] = v
                    u = lexpo_d[md] + m * S['expo_d'][md]
                    row['util_mean'] = float(np.mean(u))
                    g = lexpo[(np.ones(len(hrs), bool) if per == 'all' else yrs_h == per)] + m * S['expo'][(np.ones(len(hrs), bool) if per == 'all' else yrs_h == per)]
                    row['util_peak_h'] = float(g.max())
                    combo.append(row)
            # tails: 10 worst days of each sleeve
            for who, x, y in (('long_worst', rl, rs), ('short_worst', rs, rl)):
                o = np.argsort(x)[:10]
                tail.append(dict(run=run, cfg_id=cfg, kind=who, own_sum=float(x[o].sum()), other_sum=float(y[o].sum()),
                                 other_mean=float(y[o].mean()), other_pos=int((y[o] > 0).sum()), other_neg=int((y[o] < 0).sum()),
                                 other_zero=int((y[o] == 0).sum()), days=','.join(days[o].strftime('%Y-%m-%d'))))
            # one-way conflicts
            t = tr[tr['cfg_id'] == cfg]
            nconf, hconf, ylist = 0, 0.0, []
            for s_, a_, b_ in zip(t['sym'].tolist(), t['t_entry'].tolist(), t['t_exit'].tolist()):
                ov = 0.0
                for s0, e0 in liv.get(s_, []):
                    lo, hi = max(a_, s0), min(b_, e0)
                    if hi > lo:
                        ov += (hi - lo) / 3.6e6
                if ov > 0:
                    nconf += 1
                    hconf += ov
                    ylist.append(A.dts([a_]).year[0])
            conf.append(dict(run=run, cfg_id=cfg, n_short=len(t), n_conflict=nconf, conflict_hours=hconf,
                             by_year=json.dumps({int(k): int(v) for k, v in pd.Series(ylist).value_counts().items()})))
        log.info('run %s done', run)
    P = pd.DataFrame(pairs)
    P['family'] = P['cfg_id'].isin(fam)
    P.to_parquet(A.OUT + '/c_pairs.parquet', index=False)
    Cb = pd.DataFrame(combo)
    Cb['family'] = Cb['cfg_id'].isin(fam)
    Cb.to_parquet(A.OUT + '/c_combo.parquet', index=False)
    pd.DataFrame(tail).assign(family=lambda x: x['cfg_id'].isin(fam)).to_parquet(A.OUT + '/c_tail.parquet', index=False)
    pd.DataFrame(conf).assign(family=lambda x: x['cfg_id'].isin(fam)).to_parquet(A.OUT + '/c_conflicts.parquet', index=False)
    log.info('c_combo done')


if __name__ == '__main__':
    main()
