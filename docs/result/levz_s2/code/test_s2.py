"""LEVZ S2 tests (MASTER DEV order item 7). Real data ONLY for regression / causality (no PnL aggregated or reported: only
mismatch counts). usage: python3 code/test_s2.py <a|b|c|d|e|f|g|all_fake|all_real>  -> out/test_<x>.json"""
import json
import os
import sys
import tempfile
import shutil
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_s2 as CM
sys.path.pop(0)
log = CM.setup_log('test_s2')
import numpy as np
import pandas as pd
CB, P, X, SIM = CM.b1()
GR = CM.s2('grid_s2')
SEL = CM.s2('select_s2')
RD = CM.s2('rand_s2')


def save(name, res):
    with open('%s/test_%s.json' % (CM.OUT, name), 'w') as fh:
        json.dump(res, fh, indent=1, default=str)
    log.info('TEST %s pass=%s %s', name, res.get('pass'), json.dumps(res, default=str)[:600])
    return res


def eqv(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try:
            return (a == b) or (np.isnan(a) and np.isnan(b))
        except TypeError:
            return a == b
    return a == b


# (a) REF through the S2 path reproduces grid_b1: DEV == DEV, Y24 == F2, Y25 == F3 (all metric columns, exact)
def test_a(nmax=None):
    T = X.load_table(CM.WORK + '/exits_s2.npz')
    cands = GR.load_cands(CM.WORK + '/cand_s2.npz', ('REF',))
    g = pd.read_parquet(CB.OUT + '/grid_b1.parquet')
    g = g[(g['W'] == 7) & (g['E'] == 'E0') & (g['zmin'] == 3.0)]
    assert len(g) == 585
    gi = {(int(r['K']), float(r['SL']), int(r['H']), float(r['arm']), float(r['gap'])): r for r in g.to_dict('records')}
    cfgs = GR.all_cfgs(('REF',))[:nmax]
    nm, ncmp, bad = 0, 0, []
    t0 = time.time()
    for c in cfgs:
        r = GR.run_cfg(c, cands['REF'], T, folds=('DEV', 'Y24', 'Y25'))
        ref = gi[(c['K'], c['SL'], c['H'], c['arm'], c['gap'])]
        for mine, theirs in (('DEV', 'DEV'), ('Y24', 'F2'), ('Y25', 'F3')):
            for kk in [x[len(mine) + 1:] for x in r if x.startswith(mine + '_')]:
                ncmp += 1
                if not eqv(r['%s_%s' % (mine, kk)], ref.get('%s_%s' % (theirs, kk))):
                    nm += 1
                    if len(bad) < 10:
                        bad.append((c['cfg_id'], mine, kk))
    return save('a', dict(n_cfg=len(cfgs), n_compared=ncmp, n_mismatch=nm, examples=bad, sec=time.time() - t0, **{'pass': nm == 0}))


# (b) exit table rows shared with B1 == exits.npz
def test_b():
    E = CM.s2('exits_s2')
    reg = E.check()
    return save('b', dict(reg, **{'pass': reg['pass']}))


# (c) causality: perturb data after hour T (OI rows > T, funding settlements ts > T - 1 min), states + scores at rows <= T unchanged
def test_c(ncut=3, npt=40):
    SG = CM.s2('sig_s2')
    D = SG.load_data()
    full = SG.states(D.X, D.U, D.F, D.tms)
    full = {k: (v[0], v[1]) for k, v in full.items() if k != 'n_ranked'}
    rng = np.random.default_rng(20261129)
    r22 = (1640995200000 - CB.H0) // CB.H
    cuts = sorted(int(x) for x in rng.integers(r22, D.NH - 49, ncut))
    res = dict(cuts=cuts, per_def={k: dict(points=0, point_mismatch=0, prefix_mismatch=0, trunc_vs_full_mismatch=0,
                                           n_state_true_points=0) for k in full})
    for T in cuts:
        n = T + 49
        Xb, Ub, tb = D.X[:n], D.U[:n], D.tms[:n]
        base = SG.states(Xb, Ub, D.F, tb)
        Xp = Xb.copy()
        Xp[T + 1:] += rng.normal(0.0, 0.5, Xp[T + 1:].shape)
        Fp = {}
        for c, fs in D.F.items():
            g = dict(fs)
            fut = fs['ts'] > tb[T] - CB.M
            rate = np.where(fut, np.rint(rng.normal(0, 5e-4, len(fs['rate'])) * 1e8) / 1e8, fs['rate'])
            g['rate'], g['r8'] = rate, rate * 8.0 / fs['ih']
            Fp[c] = g
        pert = SG.states(Xp, Ub, Fp, tb)
        cols = np.flatnonzero(Ub[T])
        pts = rng.choice(cols, size=min(npt, len(cols)), replace=False)
        for k in full:
            Sb, sb = base[k]
            Sp, sp = pert[k]
            Sf, sf = full[k]
            d = res['per_def'][k]
            d['points'] += len(pts)
            d['n_state_true_points'] += int(Sb[T, pts].sum())
            same_s = lambda a, b: (a == b) | (np.isnan(a) & np.isnan(b))
            d['point_mismatch'] += int((Sb[T, pts] != Sp[T, pts]).sum() + (~same_s(sb[T, pts], sp[T, pts])).sum())
            d['prefix_mismatch'] += int((Sb[:T + 1] != Sp[:T + 1]).sum() + (~same_s(sb[:T + 1], sp[:T + 1])).sum())
            d['trunc_vs_full_mismatch'] += int((Sb[:T + 1] != Sf[:T + 1]).sum() + (~same_s(sb[:T + 1], sf[:T + 1])).sum())
        log.info('cut %d done %s', T, json.dumps(res['per_def']))
        del base, pert, Xp, Fp
    ok = all(v['points'] >= 100 and v['point_mismatch'] == 0 and v['prefix_mismatch'] == 0 and v['trunc_vs_full_mismatch'] == 0
             for v in res['per_def'].values())
    return save('c', dict(res, **{'pass': ok}))


# ---------------------------------------------------------------- fake data helpers
FAKE_NS = 60


def fake_grid(seed=1):
    rng = np.random.default_rng(seed)
    cfgs = GR.all_cfgs(('F',))
    rows = []
    for c in cfgs:
        r = dict(c)
        for f in GR.FOLDN:
            r[f + '_ret'] = float(rng.normal(0.02, 0.05))
            r[f + '_maxdd_worst'] = float(rng.uniform(0.02, 0.2))
            r[f + '_n'] = int(rng.integers(20, 80))
        rows.append(r)
    return pd.DataFrame(rows)


# (d) WFO never uses folds >= Y (spy on the rule input + poison test + hand-answer case)
def test_d():
    out = {}
    df = fake_grid()
    seen = []
    orig = SEL.RULE[0]

    def spy(d, folds, mode, **kw):
        seen.append((tuple(folds), tuple(sorted(c for c in d.columns if any(c.startswith(f + '_') for f in GR.FOLDN)))))
        return orig(d, folds, mode, **kw)
    SEL.RULE[0] = spy
    try:
        w1 = SEL.wfo_set(df)
    finally:
        SEL.RULE[0] = orig
    leak = []
    for folds, cols in seen:
        for c in cols:
            if not any(c.startswith(f + '_') for f in folds):
                leak.append(c)
    out['spy_calls'] = len(seen)
    out['spy_leak_cols'] = leak[:10]
    # poison: change every column of folds >= Y (and DEV) -> selection for Y unchanged
    pois_ok = True
    for Y, folds in SEL.TRAIN.items():
        d2 = df.copy()
        for f in GR.FOLDN:
            if f not in folds:
                for c in [x for x in d2.columns if x.startswith(f + '_')]:
                    d2[c] = -d2[c] * 7.0 + 3.0
        w2 = SEL.wfo_set(d2)
        pois_ok &= (w2[str(Y)]['chosen'] == w1[str(Y)]['chosen'] and w2[str(Y)]['passing20'] == w1[str(Y)]['passing20'])
    out['poison_ok'] = bool(pois_ok)
    # hand answer
    h = df.copy()
    for f in GR.FOLDN:
        h[f + '_ret'], h[f + '_maxdd_worst'], h[f + '_n'] = 0.01, 0.1, 50
    X1 = 100
    Z1 = 200
    h.loc[h['cfg_id'] == X1, 'Y22_ret'] = 0.5
    h.loc[h['cfg_id'] == Z1, ['Y22_ret', 'Y23_ret']] = 0.3
    h.loc[h['cfg_id'] == X1, 'Y23_ret'] = 0.01
    w3 = SEL.wfo_set(h)
    out['hand'] = dict(ch2023=w3['2023']['chosen'], exp2023=X1, ch2024=w3['2024']['chosen'], exp2024=Z1)
    h2 = h.copy()
    h2['Y22_ret'] = -0.01
    w4 = SEL.wfo_set(h2)
    out['no_valid_2023'] = w4['2023']['status']
    ok = (not leak) and pois_ok and w3['2023']['chosen'] == X1 and w3['2024']['chosen'] == Z1 and \
        w4['2023']['status'] == 'khong cham duoc 2023'
    return save('d', dict(out, **{'pass': bool(ok)}))


def fake_world(seed=7):
    """fake universe (FAKE_NS coins, real hour grid) + latent per-(k,c) edge A; table_fn builds a synthetic exit table."""
    rng = np.random.default_rng(seed)
    NH = CB.NH
    U = np.zeros((NH, FAKE_NS), bool)
    U[:, :50] = True
    ok1m = np.ones((NH, FAKE_NS), bool)
    return U, ok1m


def fake_table(ck, cc, edge):
    """deterministic synthetic exit table: per cfg xr = 1 - edge(k,c) + noise(k,c,cfg); exit at H hours ('time')."""
    n = len(ck)
    NX = len(CB.XCFGS)
    T = {}
    e = np.array([edge(int(k), int(c)) for k, c in zip(ck, cc)])
    rs_ = np.random.default_rng(12345)
    noise = np.array([np.random.default_rng([int(k), int(c), 99]).normal(0, 0.01, NX) for k, c in zip(ck, cc)]).reshape(n, NX)
    xr = 1.0 - e[:, None] + noise
    Hs = np.array([x[1] for x in CB.XCFGS])
    T['j'] = np.tile((60 * Hs).astype(np.int32), (n, 1))
    T['rs'] = np.full((n, NX), CB.R_TIME, dtype=np.int8)
    T['xr'] = xr
    T['fund'] = np.zeros((n, NX))
    T['mx'] = np.maximum(1.0, xr)
    T['mxh'] = np.maximum(1.0, xr)
    T['flag'] = np.zeros((n, NX), dtype=np.int8)
    hh = np.arange(CB.HMAX + 1)
    T['mk'] = 1.0 - e[:, None] * np.minimum(hh[None, :] / 24.0, 1.0)
    T['hm'] = np.maximum(T['mk'], 1.0)
    T['fh'] = np.zeros((n, CB.HMAX + 1))
    T['fc'] = np.zeros((n, CB.HMAX + 1))
    T['p0'] = np.ones(n)
    T['longgap'] = np.zeros(n, bool)
    T['k'], T['c'] = np.asarray(ck), np.asarray(cc)
    return T


def fake_sets(rng):
    """PLANT: ~150 episode hours/yr on coins 0..49 with edge 0.03; NOISE: same count, edge -0.002."""
    yrs = [(1640995200000 + i * 365 * 86400000 - CB.H0) // CB.H for i in range(4)]
    out = {}
    for name in ('PLANT', 'NOISE'):
        ks, cs = [], []
        for y0 in yrs:
            k = np.sort(rng.choice(np.arange(y0 + 10, y0 + 8700, 6), size=150, replace=False))
            c = rng.integers(0, 50, len(k))
            ks.append(k)
            cs.append(c)
        out[name] = (np.concatenate(ks), np.concatenate(cs))
    return out


def own_ep72_by_year(ck, cc):
    """independent re-implementation: per coin, sorted candidate hours, new episode when gap to PREVIOUS candidate > 72 h."""
    yr = pd.to_datetime(CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H, unit='ms').year.values
    cnt = {y: 0 for y in CM.YEARS}
    for c in np.unique(cc):
        prev = None
        for k in sorted(int(x) for x in np.asarray(ck)[np.asarray(cc) == c]):
            if prev is None or k - prev > 72:
                if int(yr[k]) in cnt:
                    cnt[int(yr[k])] += 1
            prev = k
    return [cnt[y] for y in CM.YEARS]


# (e) rand: per-year counts, distinct seeds, resumable
def test_e():
    rng = np.random.default_rng(3)
    U, ok1m = fake_world()
    sets = fake_sets(rng)
    tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    RD.G['pools'] = {s: RD.year_pools(U, ok1m, k, c, tms) for s, (k, c) in sets.items()}
    RD.G['table_fn'] = lambda ck, cc: fake_table(ck, cc, lambda k, c: -0.002)
    tmp = tempfile.mkdtemp(prefix='s2test_e_')
    try:
        n1 = RD.run_reps(['PLANT'], 2, tmp)
        n2 = RD.run_reps(['PLANT'], 3, tmp)
        df = pd.concat([pd.read_parquet(os.path.join(tmp, f)) for f in sorted(os.listdir(tmp)) if f.endswith('.parquet')])
        exp = own_ep72_by_year(sets['PLANT'][0], sets['PLANT'][1])   # independent of the tested pool builder (A1 NHO-3)
        cnt_ok = all([int(r['n_%d' % y]) for y in CM.YEARS] == exp for r in df.to_dict('records'))
        seeds_ok = df['seed'].nunique() == len(df)
        res = dict(first_run=n1, resume_run=n2, n_parts=int(len(df)), expected_per_year=exp, counts_ok=bool(cnt_ok),
                   seeds_unique=bool(seeds_ok))
        ok = n1 == 2 and n2 == 1 and len(df) == 3 and cnt_ok and seeds_ok
    finally:
        shutil.rmtree(tmp)
    return save('e', dict(res, **{'pass': bool(ok)}))


# (g) determinism: same inputs -> identical grid rows (fake) and identical REF rows (real, 3 configs; equality only)
def test_g():
    rng = np.random.default_rng(5)
    sets = fake_sets(rng)
    k, c = sets['PLANT']
    T = fake_table(k, c, lambda a, b: 0.01)
    cand = P.CandB1(k, c, np.ones(len(k)), np.arange(len(k)))
    cf = GR.all_cfgs(('PLANT',))[:5]
    a = GR.grid_df({'PLANT': cand}, T, cf)
    b = GR.grid_df({'PLANT': cand}, T, cf)
    same_fake = a.equals(b)
    Tr = X.load_table(CM.WORK + '/exits_s2.npz')
    cr = GR.load_cands(CM.WORK + '/cand_s2.npz', ('P6a',))
    cf2 = GR.all_cfgs(('P6a',))[::200]
    r1 = GR.grid_df(cr, Tr, cf2)
    r2 = GR.grid_df(cr, Tr, cf2)
    same_real = r1.equals(r2)
    return save('g', dict(same_fake=bool(same_fake), same_real=bool(same_real), **{'pass': bool(same_fake and same_real)}))


if __name__ == '__main__':
    t = sys.argv[1]
    fn = dict(a=test_a, b=test_b, c=test_c, d=test_d, e=test_e, g=test_g)
    if t == 'all_fake':
        for x in 'de':
            fn[x]()
    elif t == 'all_real':
        for x in 'bacg':
            fn[x]()
    elif t in fn:
        fn[t]()


# (c2) PURPOSEFUL causality points (MASTER): >= 100 hours IN state and >= 100 hours right BEFORE an entry per definition; for each
# chosen cut hour T: data after T perturbed, states + scores on rows <= T must equal the full-data run (strict at t = T).
def test_c2(need=100, max_cuts=700):
    SG = CM.s2('sig_s2')
    D = SG.load_data()
    full = SG.states(D.X, D.U, D.F, D.tms)
    full = {k: v for k, v in full.items() if k != 'n_ranked'}
    r22 = (1640995200000 - CB.H0) // CB.H
    NH = D.NH
    cnt_in, cnt_pre = {}, {}
    for k, (S, s) in full.items():
        pre = np.zeros_like(S)
        pre[:-1] = S[1:] & ~S[:-1]
        cnt_in[k] = S.sum(1)
        cnt_pre[k] = pre.sum(1)
    rows = np.arange(NH)
    elig = (rows >= r22) & (rows < NH - 49)
    rng = np.random.default_rng(20261130)
    order = rng.permutation(np.flatnonzero(elig))
    got = {k: [0, 0] for k in full}
    cuts = []
    # greedy over random order, prefer early hours (cost ~ T): sort candidates by T, take a cut if it helps a def still short
    cand_rows = np.sort(order)
    # pass 1: hours right before an entry (scarce) for defs still short; pass 2: in-state hours; earliest hours first (cost ~ T)
    for idx in (1, 0):
        cnt = cnt_pre if idx == 1 else cnt_in
        for T in cand_rows:
            if len(cuts) >= max_cuts or all(got[k][idx] >= need for k in full):
                break
            if int(T) in cuts:
                continue
            if any(got[k][idx] < need and cnt[k][T] > 0 for k in full):
                cuts.append(int(T))
                for k in full:
                    got[k][0] += int(cnt_in[k][T])
                    got[k][1] += int(cnt_pre[k][T])
    cuts.sort()
    log.info('c2 cuts=%d planned points %s', len(cuts), json.dumps(got))
    res = dict(n_cuts=len(cuts), per_def={k: dict(in_state_points=0, pre_entry_points=0, point_mismatch=0, prefix_mismatch=0)
                                          for k in full})
    same = lambda a, b: (a == b) | (np.isnan(a) & np.isnan(b))
    t0 = time.time()
    for i, T in enumerate(cuts):
        n = T + 49
        Xp = D.X[:n].copy()
        Xp[T + 1:] += rng.normal(0.0, 0.5, Xp[T + 1:].shape)
        Fp = {}
        for c, fs in D.F.items():
            g = dict(fs)
            fut = fs['ts'] > D.tms[T] - CB.M
            if fut.any():
                rate = np.where(fut, np.rint(rng.normal(0, 5e-4, len(fs['rate'])) * 1e8) / 1e8, fs['rate'])
                g['rate'], g['r8'] = rate, rate * 8.0 / fs['ih']
            Fp[c] = g
        pert = SG.states(Xp, D.U[:n], Fp, D.tms[:n])
        for k, (S, s) in full.items():
            Sp, sp = pert[k]
            d = res['per_def'][k]
            pin = np.flatnonzero(S[T])
            ppre = np.flatnonzero(S[T + 1] & ~S[T])
            d['in_state_points'] += len(pin)
            d['pre_entry_points'] += len(ppre)
            pc = np.concatenate([pin, ppre])
            d['point_mismatch'] += int((S[T, pc] != Sp[T, pc]).sum() + (~same(s[T, pc], sp[T, pc])).sum())
            d['prefix_mismatch'] += int((S[:T + 1] != Sp[:T + 1]).sum() + (~same(s[:T + 1], sp[:T + 1])).sum())
        del pert, Xp, Fp
        if i % 10 == 0:
            log.info('c2 cut %d/%d T=%d %.0fs %s', i + 1, len(cuts), T, time.time() - t0, json.dumps(res['per_def']))
    ok = all(v['in_state_points'] >= need and v['pre_entry_points'] >= need and v['point_mismatch'] == 0 and v['prefix_mismatch'] == 0
             for v in res['per_def'].values())
    return save('c2', dict(res, cuts=cuts, **{'pass': ok}))


# (f) end-to-end on FAKE data: grid -> select -> rand (3 reps) -> report. PLANT (edge 3 %) must be 'TAP DAT', NOISE must not.
def test_f(nrep=3):
    RP = CM.s2('report_s2')
    rng = np.random.default_rng(11)
    U, ok1m = fake_world()
    sets = fake_sets(rng)
    plant = set(zip(sets['PLANT'][0].tolist(), sets['PLANT'][1].tolist()))
    edge = lambda k, c: 0.03 if (k, c) in plant else -0.002
    names = ['PLANT', 'NOISE']
    code = np.unique(np.concatenate([sets[s][0] * 10000 + sets[s][1] for s in names]))
    T = fake_table(code // 10000, code % 10000, edge)
    cands = {}
    for s in names:
        k, c = sets[s]
        o = np.lexsort((c, k))
        k, c = k[o], c[o]
        cid = np.searchsorted(code, k * 10000 + c)
        cands[s] = P.CandB1(k, c, rng.random(len(k)), cid)
    tmp = tempfile.mkdtemp(prefix='s2test_f_')
    try:
        df = GR.run_grid(cands, T, tmp + '/grid_parts', tmp + '/grid.parquet', tuple(names), 1)
        sel = SEL.select_all(df)
        tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
        RD.G['pools'] = {s: RD.year_pools(U, ok1m, sets[s][0], sets[s][1], tms) for s in names}
        RD.G['table_fn'] = lambda ck, cc: fake_table(ck, cc, edge)
        RD.run_reps(names, nrep, tmp + '/rand_parts')
        rnd = RD.summarize(names, tmp + '/rand_parts', df, sel, nrep)
        rep = RP.build(df, sel, rnd, cands, T, None, names)
        RP.write_md(rep, tmp + '/REPORT.md')
        v = {s: rep[s]['verdict'] for s in names}
        crit = {s: {c: rep[s][c] for c in ('S_a', 'S_b', 'S_c', 'S_d', 'S_e')} for s in names}
    finally:
        shutil.rmtree(tmp)
    return save('f', dict(verdict=v, criteria=crit, **{'pass': v['PLANT'] == 'TAP DAT' and v['NOISE'] != 'TAP DAT'}))


if __name__ == '__main__' and sys.argv[1] in ('c2', 'f'):
    {'c2': test_c2, 'f': test_f}[sys.argv[1]]()


# (h) hand-answer tests added after A1 (NHO-1 / NHO-3 / ERRATA2 F1, F3); each case names the mutant it must catch
def test_h():
    RP = CM.s2('report_s2')
    out = {}
    # h1 p_wfo (ERRATA2 F1): real scored 2023+2024, real sum 0.10
    rows = [dict(scored='2023/2024', top20_2023=0.05, top20_2024=0.06, top20_2025=np.nan),          # 0.11 >= 0.10 -> True
            dict(scored='2023', top20_2023=0.50, top20_2024=np.nan, top20_2025=np.nan),             # misses 2024 -> False
            dict(scored='2023/2024/2025', top20_2023=0.01, top20_2024=0.02, top20_2025=0.90),      # real years 0.03 -> False
            dict(scored='', top20_2023=np.nan, top20_2024=np.nan, top20_2025=np.nan)]             # none -> False
    p = RD.p_wfo_stat(rows, ['2023', '2024'], 0.10)
    p3 = RD.p_wfo_stat([dict(scored='2023/2024', top20_2023=1.0, top20_2024=1.0, top20_2025=np.nan)], ['2023', '2024', '2025'], 0.1)
    pn = RD.p_wfo_stat(rows, [], float('nan'))
    out['h1_p_wfo'] = dict(got=p, exp=0.25, fewer_years_case=p3, exp_fewer=0.0, no_real_year=str(pn))
    h1 = p == 0.25 and p3 == 0.0 and np.isnan(pn)
    # h2 S-a
    cases = [({'2023': 0.1, '2024': -0.05, '2025': -0.01}, False),   # 1/3 > 0 (mutant >= 1/3 -> True)
             ({'2023': 0.1, '2024': 0.2, '2025': -0.05}, True),
             ({'2023': 0.3, '2024': 0.01, '2025': -0.5}, False),     # 2/3 > 0 but sum < 0
             ({'2024': 0.1, '2025': -0.01}, False), ({'2024': 0.1, '2025': 0.2}, True), ({'2025': 0.5}, False), ({}, False)]
    got = [RP.s_a(m) for m, e in cases]
    out['h2_s_a'] = dict(got=got, exp=[e for m, e in cases])
    h2 = got == [e for m, e in cases]
    # h3 top-20 definition (mutant top-200 / wrong order)
    df = fake_grid()
    for f in GR.FOLDN:
        df[f + '_ret'], df[f + '_maxdd_worst'], df[f + '_n'] = 0.01, 0.1, 50
    ids = list(range(0, 300, 10))   # 30 configs with distinct Y22 scores, descending
    for i, c in enumerate(ids):
        df.loc[df['cfg_id'] == c, 'Y22_ret'] = 0.5 - 0.01 * i
        df.loc[df['cfg_id'] == c, 'Y23_ret'] = float(i)          # test-year value = rank index
    w = SEL.wfo_set(df)
    exp_ids = ids[:20]
    out['h3_top20'] = dict(got_ids=w['2023']['passing20'], exp_ids=exp_ids, got_med=w['2023']['top20'].get('median_ret'),
                           exp_med=float(np.median(range(20))))
    h3 = w['2023']['passing20'] == exp_ids and w['2023']['top20']['median_ret'] == float(np.median(range(20)))
    # h4 seed depends on set and rep (mutant seed without set index)
    a, b, c2, a2 = RD.rng_for(0, 0).random(5), RD.rng_for(1, 0).random(5), RD.rng_for(0, 1).random(5), RD.rng_for(0, 0).random(5)
    h4 = (not np.allclose(a, b)) and (not np.allclose(a, c2)) and np.array_equal(a, a2)
    out['h4_seed'] = dict(set_differs=bool(not np.allclose(a, b)), rep_differs=bool(not np.allclose(a, c2)), reproducible=bool(np.array_equal(a, a2)))
    # h5 rand runs the FULL 585-config grid of its set (mutant: 195 configs / other set)
    rec = []
    orig = RD.GR.grid_df

    def spy(cands, T, cfgs):
        rec.append([dict(c) for c in cfgs])
        return orig(cands, T, cfgs)
    rng = np.random.default_rng(3)
    U, ok1m = fake_world()
    sets = fake_sets(rng)
    tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    RD.G['pools'] = {'PLANT': RD.year_pools(U, ok1m, sets['PLANT'][0], sets['PLANT'][1], tms)}
    RD.G['table_fn'] = lambda ck, cc: fake_table(ck, cc, lambda k, c: -0.002)
    RD.GR.grid_df = spy
    try:
        RD.one_rep(0, 'PLANT', 0)
    finally:
        RD.GR.grid_df = orig
    cf = rec[0] if rec else []
    keys = set((c['K'], c['SL'], c['H'], c['arm'], c['gap']) for c in cf)
    h5 = len(rec) == 1 and len(cf) == 585 and len(keys) == 585 and all(c['set'] == 'PLANT' for c in cf)
    out['h5_full_grid'] = dict(calls=len(rec), n_cfg=len(cf), n_unique=len(keys))
    # h6 has1m respected by the pool builder (fake: half the coins without 1m bar)
    ok_half = ok1m.copy()
    ok_half[:, 25:] = False
    pools = RD.year_pools(U, ok_half, sets['PLANT'][0], sets['PLANT'][1], tms)
    c0 = RD.R0.draw(pools, RD.rng_for(0, 0))
    h6 = bool(ok_half[c0.ck, c0.cc].all() and U[c0.ck, c0.cc].all())
    out['h6_has1m'] = dict(all_drawn_have_1m=h6, n=int(len(c0.ck)))
    ok = h1 and h2 and h3 and h4 and h5 and h6
    return save('h', dict(out, **{'pass': bool(ok)}))


# (e2) REAL pools (counting only): every drawn cell has U and has1m; drawn count per year == cand_s2.json ep72_b0 ==
# independent re-count from cand_s2.npz
def test_e2():
    pools, U, has1m = RD.real_pools()
    with open(CM.OUT + '/cand_s2.json') as fh:
        info = json.load(fh)
    cz = np.load(CM.WORK + '/cand_s2.npz')
    res, ok = {}, True
    for si, s in enumerate(CM.SETS):
        c0 = RD.R0.draw(pools[s], RD.rng_for(si, 0))
        yr = pd.to_datetime(CB.H0 + c0.ck * CB.H, unit='ms').year.values
        got = [int((yr == y).sum()) for y in CM.YEARS]
        js = [info['sets'][s]['ep72_b0'][str(y)] for y in CM.YEARS]
        own = own_ep72_by_year(cz[s + '_k'], cz[s + '_c'])
        cells = bool(U[c0.ck, c0.cc].all() and has1m[c0.ck, c0.cc].all())
        uniq = len(set(zip(c0.ck.tolist(), c0.cc.tolist()))) == len(c0.ck)
        res[s] = dict(drawn=got, cand_json=js, own_count=own, cells_in_U_has1m=cells, no_dup=uniq)
        ok &= got == js == own and cells and uniq
    return save('e2', dict(res, **{'pass': bool(ok)}))


if __name__ == '__main__' and sys.argv[1] in ('h', 'e2'):
    {'h': test_h, 'e2': test_e2}[sys.argv[1]]()
