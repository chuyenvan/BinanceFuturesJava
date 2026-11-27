"""LLV (PREREG_X3_1127 part C1-C4). Long DEV ledgers (4 seeds) -> clusters -> causal leverage features at decision hour k
-> H1..H4 one-sided tests (year x seed sign table + month-block permutation, pooled mean over seeds), rough PnL impact,
descriptives, causality + reconciliation checks. Read-only on inputs; writes only levz_llv/{out,logs}.
Conventions: ledger start/end 'YYYYMMDD HH:MM' UTC+7 -> UTC = -7h (audited levz_an c_tzcheck). Decision hour k = last hour mark
STRICTLY before entry minute: T_k < ts (k = ceil((ts-H0)/H) - 1). sig row t = T_k uses info up to T_k (levz2 sig: OI tsr <= t-10min,
funding settlement ts <= t-1min, close of candle [t-1h,t)). doi24 = X[k] - X[k-24], X = ln OI (feat_b3 definition).
LEV24 = any j in [k-23, k]: z_oi >= 2.5 & z_f >= 2.5 & f > 1e-4 (NaN -> false)."""
import os, sys, json, logging
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

BASE = '/home/ubuntu/claude_master/w3/levz_llv'
OUT = BASE + '/out'
L2 = '/home/ubuntu/claude_master/w3/levz2/work'
L1 = '/home/ubuntu/claude_master/w3/levz/work'
LONG = '/home/ubuntu/claude_master/w3/p15_stab/s2/k/%s'
RUNS = ('c0s42', 'c0s7', 'c0s123', 'c0s13')
CUT = 1767225600000
DEV0 = 1640995200000
H0 = 1638316800000
H = 3600000
M = 60000
NPERM = 5000
YEARS = (2022, 2023, 2024, 2025)
log = logging.getLogger('llv')


def parse_t(s):
    t = pd.to_datetime(s.astype(str).str.strip(), format='%Y%m%d %H:%M') - pd.Timedelta(hours=7)
    return t.values.astype('datetime64[ms]').astype(np.int64)


def load_dense(syms):
    NH = (CUT - H0) // H
    col = {s: i for i, s in enumerate(syms)}
    d = pd.read_parquet(L2 + '/sig_W7.parquet')
    assert int(d['t'].max()) < CUT
    r = ((d['t'].values - H0) // H).astype(np.int64)
    c = d['sym'].astype(str).map(col).values.astype(np.int64)
    S = {}
    for kk in ('z_oi', 'z_f', 'f'):
        a = np.full((NH, len(syms)), np.nan, dtype=np.float64)
        a[r, c] = d[kk].values
        S[kk] = a
    u = np.zeros((NH, len(syms)), dtype=bool)
    u[r, c] = d['u'].values.astype(bool)
    S['u'] = u
    del d
    X = np.full((NH, len(syms)), np.nan)
    tsr = np.full((NH, len(syms)), -1, dtype=np.int64)
    y, mo = 2021, 12
    while (y, mo) <= (2025, 12):
        d = pd.read_parquet('%s/oi_%04d-%02d.parquet' % (L1, y, mo))
        d['sym'] = d['sym'].astype(str)
        d = d[d['sym'].isin(col) & (d['h'] >= H0) & (d['h'] < CUT)]
        assert (d['tsr'].values <= d['h'].values - 10 * M).all()
        rr = ((d['h'].values - H0) // H).astype(np.int64)
        cc = d['sym'].map(col).values.astype(np.int64)
        t = d['tsr'].values
        o = np.argsort(t, kind='mergesort')
        X[rr[o], cc[o]] = d['x'].values[o]
        tsr[rr[o], cc[o]] = t[o]
        mo += 1
        if mo == 13:
            y, mo = y + 1, 1
    S['X'] = X
    S['tsr'] = tsr
    return S


def clusters(run, col):
    dd = LONG % run
    with open(dd + '/result.json') as fh:
        R = json.load(fh)
    d = pd.read_csv(dd + '/storage/printDone.csv')
    d = d.loc[:, ~d.columns.str.startswith('Unnamed')]
    assert (d['side'] == 'BUY').all()
    d['ts'] = parse_t(d['start'])
    d['te'] = parse_t(d['end'])
    assert int(d['te'].max()) < CUT and (d['te'] >= d['ts']).all()
    d = d.sort_values(['sym', 'ts', 'te'], kind='mergesort').reset_index(drop=True)
    cid = np.zeros(len(d), dtype=np.int64)
    cur, cs, cend, ntouch = -1, None, None, 0
    for i, (s, ts, te) in enumerate(zip(d['sym'].values, d['ts'].values, d['te'].values)):
        if s != cs or ts > cend:
            cur += 1
            cs, cend = s, te
        else:
            if ts == cend:
                ntouch += 1
            cend = max(cend, te)
        cid[i] = cur
    d['cid'] = cid
    d['tstop'] = d['time_order'].isin([168, 336, 504])
    g = d.groupby('cid')
    C = pd.DataFrame({'sym': g['sym'].first(), 'ts': g['ts'].min(), 'te': g['te'].max(), 'nleg': g.size(),
                      'pnl': g['pnl'].sum(), 'margin': g['margin'].sum(), 'tstop': g['tstop'].any(),
                      'nsl': g['status'].apply(lambda x: int((x == 'STOP_LOSS_DONE').sum()))}).reset_index()
    C['ret'] = C['pnl'] / C['margin']
    C['run'] = run

    def mp(s):
        s = str(s)
        for cand in (s + 'USDT', s, s[:-4] if s.endswith('USDT') else None):
            if cand is not None and cand in col:
                return col[cand]
        return -1
    C['c'] = C['sym'].map(mp).astype(int)
    chk = dict(n_legs=len(d), n_clusters=len(C), touch_chain=ntouch, sum_pnl_legs=float(d['pnl'].sum()),
               sum_pnl_clusters=float(C['pnl'].sum()), eq_delta=float(R['equity_final'] - R['equity_start']))
    assert abs(chk['sum_pnl_legs'] - chk['sum_pnl_clusters']) < 1e-6 * max(1, abs(chk['sum_pnl_legs']))
    return C, chk


def features(C, S):
    ts = C['ts'].values
    k = -(-(ts - H0) // H) - 1          # T_k < ts strictly
    C['k'] = k
    C['Tk'] = H0 + k * H
    assert (C['Tk'].values < ts).all()
    c = C['c'].values
    ok = (c >= 0) & (k >= 24)
    kk, cc = np.where(ok, k, 0), np.where(ok, c, 0)
    for nm in ('z_oi', 'z_f', 'f'):
        C[nm] = np.where(ok, S[nm][kk, cc], np.nan)
    C['u'] = np.where(ok, S['u'][kk, cc], False)
    C['doi24'] = np.where(ok, S['X'][kk, cc] - S['X'][kk - 24, cc], np.nan)
    with np.errstate(invalid='ignore'):
        D0 = (S['z_oi'] >= 2.5) & (S['z_f'] >= 2.5) & (S['f'] > 1e-4)
    cp = np.vstack([np.zeros((1, D0.shape[1]), dtype=np.int64), np.cumsum(D0, axis=0)])
    C['LEV24'] = np.where(ok, (cp[kk + 1, cc] - cp[np.maximum(kk - 23, 0), cc]) > 0, False)
    C['elig'] = ok & C['u'].values & np.isfinite(C[['z_oi', 'z_f', 'f', 'doi24']].values).all(axis=1)
    dt = pd.to_datetime(C['ts'].values, unit='ms')
    C['year'] = dt.year
    C['mon'] = dt.year * 100 + dt.month
    return C


def groups(C):
    G = {}
    G['H1'] = C['LEV24'].values.astype(bool)
    G['H2'] = (C['z_oi'].values <= -1)
    G['H3'] = (C['f'].values < 0)
    h4 = np.zeros(len(C), dtype=bool)
    for (r, y), ix in C.groupby(['run', 'year']).groups.items():
        ix = np.asarray(ix)
        e = ix[C['elig'].values[ix]]
        if len(e) == 0:
            continue
        q = np.quantile(C['doi24'].values[e], 0.2)
        h4[e] = C['doi24'].values[e] <= q
    G['H4'] = h4
    return G


SIGN = {'H1': -1, 'H2': 1, 'H3': 1, 'H4': 1}


def diff(ret, g):
    if g.sum() == 0 or (~g).sum() == 0:
        return np.nan
    return ret[g].mean() - ret[~g].mean()


def perm_test(E, g, rng):
    """E: eligible DEV clusters (all seeds). stat = mean over seeds of diff; permute labels within (run, month)."""
    parts = []
    for r in RUNS:
        m = (E['run'] == r).values
        ret = E['ret'].values[m]
        gg = g[m]
        blk = E['mon'].values[m]
        base = np.argsort(blk, kind='mergesort')
        parts.append((ret, gg, blk, base))
    obs = np.mean([diff(p[0], p[1]) for p in parts])
    cnt = 0
    null = np.empty(NPERM)
    for b in range(NPERM):
        vals = []
        for ret, gg, blk, base in parts:
            idx = np.lexsort((rng.random(len(gg)), blk))
            gp = np.empty_like(gg)
            gp[base] = gg[idx]
            vals.append(diff(ret, gp))
        null[b] = np.mean(vals)
    return obs, null


def main():
    os.makedirs(OUT, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(BASE + '/logs/llv.log'), logging.StreamHandler()])
    with open(L2 + '/sig_meta.json') as fh:
        meta = json.load(fh)
    assert int(meta['H0']) == H0
    syms = meta['syms']
    col = {s: i for i, s in enumerate(syms)}
    S = load_dense(syms)
    log.info('dense loaded')
    allC, chk = [], {}
    for r in RUNS:
        C, ck = clusters(r, col)
        C = features(C, S)
        chk[r] = ck
        allC.append(C)
    C = pd.concat(allC, ignore_index=True)
    G = groups(C)
    for h in G:
        C[h] = G[h]
    C.to_parquet(OUT + '/clusters.parquet', index=False)
    res = {'check': chk}
    dev = C['year'].isin(YEARS).values
    # counts
    cnt = {}
    for r in RUNS:
        m = (C['run'] == r).values
        dm = m & dev
        cnt[r] = dict(n_all=int(m.sum()), n_dev=int(dm.sum()), n_pre2022=int((m & (C['year'] < 2022).values).sum()),
                      by_year={int(y): int((dm & (C['year'] == y).values).sum()) for y in YEARS},
                      unmapped=int((dm & (C['c'].values < 0)).sum()), unmapped_syms=sorted(set(C.loc[dm & (C['c'].values < 0), 'sym'].astype(str))),
                      not_univ=int((dm & (C['c'].values >= 0) & ~C['u'].values.astype(bool)).sum()),
                      elig=int((dm & C['elig'].values).sum()),
                      nleg_dist={int(a): int(b) for a, b in C.loc[dm, 'nleg'].value_counts().sort_index().items()})
    res['counts'] = cnt
    E = C[dev & C['elig'].values].reset_index(drop=True)
    rng = np.random.default_rng(20261127)
    tests = {}
    for h in ('H1', 'H2', 'H3', 'H4'):
        g = E[h].values.astype(bool)
        tab = []
        seed_ok = 0
        for r in RUNS:
            nright = 0
            for y in YEARS:
                m = ((E['run'] == r) & (E['year'] == y)).values
                ret, gg = E['ret'].values[m], g[m]
                dlt = diff(ret, gg)
                right = bool(np.isfinite(dlt) and SIGN[h] * dlt > 0)
                nright += right
                tab.append(dict(run=r, year=y, n_g=int(gg.sum()), n_rest=int((~gg).sum()),
                                mean_g=float(ret[gg].mean()) if gg.sum() else None,
                                mean_rest=float(ret[~gg].mean()) if (~gg).sum() else None,
                                diff=None if not np.isfinite(dlt) else float(dlt), right=right))
            seed_ok += nright >= 3
        obs, null = perm_test(E, g, rng)
        p = float((1 + np.sum(SIGN[h] * null >= SIGN[h] * obs - 1e-15)) / (NPERM + 1))
        cons = bool(seed_ok >= 3)
        tests[h] = dict(n_g=int(g.sum()), frac_g=float(g.mean()), diff_pooled=float(obs), p=p, seeds_consistent=int(seed_ok),
                        consistent=cons, verdict='CO MANH MOI' if (cons and p <= 0.0125) else 'KHONG CO MANH MOI', table=tab,
                        null_mean=float(null.mean()), null_sd=float(null.std()))
        log.info('%s n_g=%d diff=%.5f p=%.4f seeds_ok=%d', h, g.sum(), obs, p, seed_ok)
    res['tests'] = tests
    # impact (rough; ignores slot/quota feedback)
    imp = {}
    Cd = C[dev].reset_index(drop=True)
    for h in ('H1', 'H2', 'H3', 'H4'):
        rows = []
        for r in RUNS:
            m = (Cd['run'] == r).values
            el = Cd['elig'].values & m
            g = Cd[h].values.astype(bool) & el
            base = float(Cd['pnl'].values[m].sum())
            if h == 'H1':
                drop = g
            else:
                drop = el & ~g
            var = base - float(Cd['pnl'].values[drop].sum())
            yr = {}
            for y in YEARS:
                my = m & (Cd['year'] == y).values
                yr[int(y)] = dict(base=float(Cd['pnl'].values[my].sum()), var=float(Cd['pnl'].values[my].sum() - Cd['pnl'].values[drop & my].sum()))
            rows.append(dict(run=r, base=base, var=var, frac_dropped=float(drop.sum() / m.sum()), by_year=yr))
        imp[h] = rows
    res['impact'] = imp
    # descriptives
    desc = {}
    desc['lev24_frac_elig'] = float(E['H1'].mean())
    qrows = []
    E['qz'] = -1
    for (r, y), ix in E.groupby(['run', 'year']).groups.items():
        ix = np.asarray(ix)
        E.loc[ix, 'qz'] = pd.qcut(E['z_oi'].values[ix], 5, labels=False, duplicates='drop')
    for y in list(YEARS) + ['all']:
        m = np.ones(len(E), bool) if y == 'all' else (E['year'] == y).values
        row = {'year': y}
        for q in range(5):
            mq = m & (E['qz'].values == q)
            row['q%d' % (q + 1)] = float(E['ret'].values[mq].mean()) if mq.any() else None
            row['n%d' % (q + 1)] = int(mq.sum())
        qrows.append(row)
    desc['zoi_quintile_ret'] = qrows
    E['bigloss'] = E['ret'] <= -0.10
    gl = {}
    for h in ('H1', 'H2', 'H3', 'H4'):
        g = E[h].values.astype(bool)
        gl[h] = dict(tstop_g=float(E['tstop'].values[g].mean()), tstop_rest=float(E['tstop'].values[~g].mean()),
                     big_g=float(E['bigloss'].values[g].mean()), big_rest=float(E['bigloss'].values[~g].mean()),
                     sl_g=float((E['nsl'].values[g] > 0).mean()), sl_rest=float((E['nsl'].values[~g] > 0).mean()),
                     med_g=float(np.median(E['ret'].values[g])), med_rest=float(np.median(E['ret'].values[~g])))
    desc['group_exit'] = gl
    desc['ret_overall'] = dict(mean=float(E['ret'].mean()), median=float(E['ret'].median()), sd=float(E['ret'].std()))
    res['desc'] = desc
    # causality check: 50 random clusters
    sig = pd.read_parquet(L2 + '/sig_W7.parquet')
    sig['sym'] = sig['sym'].astype(str)
    sig = sig.set_index(['sym', 't'])
    pick = E.sample(50, random_state=7)
    bad = 0
    det = []
    for rr in pick.itertuples(index=False):
        sy = syms[rr.c]
        k = int(rr.k)
        o1 = rr.Tk < rr.ts and rr.Tk == H0 + k * H and rr.ts - rr.Tk <= H
        row = sig.loc[(sy, int(rr.Tk))]
        o2 = np.isclose(row['z_oi'], rr.z_oi) and np.isclose(row['z_f'], rr.z_f) and np.isclose(row['f'], rr.f)
        o3 = S['tsr'][k, rr.c] <= rr.Tk - 10 * M and S['tsr'][k - 24, rr.c] <= rr.Tk - 24 * H - 10 * M and S['tsr'][k, rr.c] > 0
        o4 = np.isclose(S['X'][k, rr.c] - S['X'][k - 24, rr.c], rr.doi24)
        ok = bool(o1 and o2 and o3 and o4)
        bad += not ok
        det.append(dict(run=rr.run, sym=sy, ts=int(rr.ts), Tk=int(rr.Tk), lag_min=float((rr.ts - rr.Tk) / M), ok=ok))
    res['causal'] = dict(n=50, n_bad=bad, min_lag_min=float(min(d['lag_min'] for d in det)), max_lag_min=float(max(d['lag_min'] for d in det)),
                         all_clusters_Tk_lt_ts=bool((C['Tk'] < C['ts']).all()))
    log.info('causal bad=%d', bad)
    with open(OUT + '/llv.json', 'w') as fh:
        json.dump(res, fh, indent=1, default=str)
    log.info('done')


if __name__ == '__main__':
    main()
