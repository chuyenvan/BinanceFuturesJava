"""LEVZ T2 tests (task list a-h). Each test logs PASS / FAIL (assert) and NEVER logs profit numbers of real configs.
usage: python3 code/test_t2.py a_exits | a_grid | b | c | d | e | f | g | h | all"""
import os
import shutil
import sys
import tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = C.setup_log('test')
CB = C.CB


def _eq(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype.kind == 'f' or b.dtype.kind == 'f':
        return a.shape == b.shape and np.array_equal(a.astype(np.float64), b.astype(np.float64), equal_nan=True)
    return np.array_equal(a, b)


# ---------------------------------------------------------------- (a) E0 through the T2 path == B1 / T1
def test_a_exits():
    XT = C.load('exits_t2')
    t = XT.load_table('E0')
    b = np.load(CB.WORK + '/exits.npz')
    cid = t['cid_b1']
    assert (b['k'][cid] == t['k']).all() and (b['c'][cid] == t['c']).all() and (t['r'] == 0).all() and (t['kb'] == t['k']).all()
    bad = [kk for kk in ('j', 'rs', 'xr', 'fund', 'mx', 'mxh', 'flag') if not _eq(t['B1_' + kk], b[kk][cid])]
    bad += [kk for kk in ('mk', 'hm', 'fh') if not _eq(t[kk][:, :C.HMAX + 1], b[kk][cid])]
    if not _eq(np.cumsum(t['fh'], axis=1)[:, :C.HMAX + 1], b['fc'][cid]):
        bad.append('fc')
    for f in ('PART', 'STATE'):
        z = np.load('%s/exits_t1_%s.npz' % (C.T1WORK, f))
        assert (z['k'][cid] == t['k']).all()
        bad += ['%s_%s' % (f, kk) for kk in z.files if kk not in ('k', 'c') and not _eq(t['%s_%s' % (f, kk)], z[kk][cid])]
    assert not bad, bad
    log.info('PASS a_exits: E0 exit table == B1 exits.npz (7 arrays x 195 + hourly) and T1 PART / STATE tables, n=%d', len(cid))


METRIC_SKIP = {'sec', 'cfg_id', 'fam', 'xi', 'W', 'E', 'zmin', 'K', 'gate', 'SL', 'H', 'arm', 'gap', 's', 'zo', 'R', 'a', 'base',
               'bxi', 'inst', 'h', 'entry', 'xfam'}


def test_a_grid(nproc=3):
    """E0 grid through T2 (1 899 configs) == grid_b1 W7 E0 rows (1 755) and grid_t1 PART / STATE gate NONE (144); exact equality
    of every metric column (logs only counts)."""
    G = C.load('grid_t2')
    XT = C.load('exits_t2')
    cls = C.cand_classes()[0]
    ctx = G.build_ctx({'E0': XT.load_table('E0')}, cls, ('E0',))
    tmp = tempfile.mkdtemp(prefix='t2a_')
    try:
        df = G.run_grid(ctx, C.all_cfgs(('E0',)), tmp + '/parts', nproc=nproc)
    finally:
        shutil.rmtree(tmp)
    assert len(df) == C.N_PER_ENTRY
    gb = pd.read_parquet(CB.OUT + '/grid_b1.parquet')
    gb = gb[(gb['W'] == 7) & (gb['E'] == 'E0')]
    d1 = df[df['xfam'] == 'B1'].copy()
    key_b = lambda r: (round(r['zmin'], 3), int(r['K']), round(r['SL'], 3), int(r['H']), round(r['arm'], 3), round(r['gap'], 3))
    ib = {key_b(r): r for r in gb.to_dict('records')}
    cols = [c for c in gb.columns if c not in METRIC_SKIP]
    nb, bad = 0, []
    for r in d1.to_dict('records'):
        o = ib[key_b(r)]
        for c in cols:
            if not _eq(r[c], o[c]):
                bad.append((r['cfg_id'], c))
        nb += 1
    assert nb == 1755 and not bad, (nb, bad[:10])
    gt = pd.read_parquet(C.T1OUT + '/grid_t1.parquet')
    gt = gt[gt['fam'].isin(['PART', 'STATE']) & (gt['gate'] == 'NONE')]
    it = {(r['fam'], int(r['xi']), round(r['zmin'], 3), int(r['K'])): r for r in gt.to_dict('records')}
    cols = [c for c in gt.columns if c not in METRIC_SKIP and c in df.columns]
    assert len(cols) >= 40
    nt = 0
    for r in df[df['xfam'] != 'B1'].to_dict('records'):
        o = it[(r['xfam'], int(r['xi']), round(r['zmin'], 3), int(r['K']))]
        for c in cols:
            if not _eq(r[c], o[c]):
                bad.append((r['cfg_id'], c))
        nt += 1
    assert nt == 144 and not bad, (nt, bad[:10])
    log.info('PASS a_grid: E0 via T2 reproduces grid_b1 W7E0 (1755 cfgs x %d cols) and grid_t1 PART/STATE NONE (144) exactly',
             len([c for c in gb.columns if c not in METRIC_SKIP]))


# ---------------------------------------------------------------- shared real-data helpers (entries / exits only, no profit)
_R = {}


def real_src():
    if 'src' not in _R:
        EN = C.load('entry_t2')
        _R['src'] = EN.Src()
        _R['en'] = EN.load_entries()
        g = np.load(CB.WORK + '/gaps.npz')
        _R['g'] = (g['c'], g['g0'], g['g1'], g['first'])
    return _R['src'], _R['en']


def ref_real(c, j):
    """independent REAL-bar test: j >= first bar and no gap row with g0 <= j < g1."""
    gc, g0, g1, first = _R['g']
    if first[c] < 0 or j < first[c]:
        return False
    sel = gc == c
    return not bool(np.any((g0[sel] <= j) & (g1[sel] > j)))


def ref_oi(syms_needed):
    """independent OI table: {(sym, h): x} with the LAST record (max tsr) per (sym, h), lag rule asserted."""
    import glob as _g
    out = {}
    for f in sorted(_g.glob(C.OIDIR + '/oi_20*.parquet')):
        d = pd.read_parquet(f)
        d = d[d['sym'].astype(str).isin(syms_needed) & (d['h'] < CB.CUT)]
        assert ((d['h'] - d['tsr']) >= 600000).all()
        d = d.sort_values(['sym', 'h', 'tsr'], kind='mergesort').drop_duplicates(['sym', 'h'], keep='last')
        for s_, h_, x_ in zip(d['sym'].astype(str), d['h'].values, d['x'].values):
            out[(s_, int(h_))] = float(x_)
    return out


# ---------------------------------------------------------------- (b) entry minute / price vs pure-Python reference loops
def ref_entry(mm, k, c, e, p0, oi=None, sym=None):
    base = 60 * k
    nmin = mm.shape[1]
    if e == 'E0':
        return base, float(mm[c, base])
    if e in C.EL_B:
        lv = p0 * (1.0 + C.EL_B[e])
        for i in range(1, C.WIN_MIN):
            j = base + i
            if j >= nmin:
                break
            if ref_real(c, j) and float(mm[c, j]) >= lv:
                return j, lv
        return -1, None
    if e == 'EB':
        vals = [float(mm[c, base - 1 - 60 * h]) for h in range(24) if base - 1 - 60 * h >= 0]
        vals = [v for v in vals if v == v]
        L = min(vals)
        for jj in range(1, 49):
            j = base + 60 * jj
            if j >= nmin:
                break
            if float(mm[c, j - 1]) < L and ref_real(c, j):
                return j, float(mm[c, j]) * 0.999
        return -1, None
    x = C.EO_X[e]
    mx = None
    for jj in range(0, 49):
        h = k + jj
        if h >= C.NH:
            break
        v = oi.get((sym, C.H0 + h * C.H))
        cur = float(np.exp(v)) if v is not None else None
        if cur is not None:
            mx = cur if mx is None else max(mx, cur)
        if jj == 0:
            continue
        j = base + 60 * jj
        if j >= nmin:
            break
        if cur is not None and mx is not None and cur <= (1.0 - x) * mx and ref_real(c, j):
            return j, float(mm[c, j]) * 0.999
    return -1, None


def test_b(n=500):
    src, en = real_src()
    syms = CB.meta()['syms']
    rng = np.random.default_rng(1)
    pick = np.sort(rng.choice(len(en['k']), size=n, replace=False))
    oi = ref_oi(set(syms[int(c)] for c in en['c'][pick]))
    for e in C.ENTRIES:
        bad, nf = 0, 0
        for i in pick:
            k, c, p0 = int(en['k'][i]), int(en['c'][i]), float(en['p0'][i])
            m, px = ref_entry(src.mm, k, c, e, p0, oi, syms[c])
            m2, px2 = int(en[e + '_m'][i]), float(en[e + '_px'][i])
            ok = (m == m2) and ((m < 0 and np.isnan(px2)) or (m >= 0 and px == px2))
            bad += int(not ok)
            nf += int(m >= 0)
        assert bad == 0, (e, bad)
        log.info('PASS b %s: %d real candidates, entry minute + price == reference loop (filled %d)', e, n, nf)
    lo = [(int(i), e) for e in C.NEW_ENTRIES for i in np.flatnonzero((en[e + '_m'] >= 0) & (en[e + '_px'] < 0.5 * en['p0']))]
    for i, e in lo:
        m = int(en[e + '_m'][i])
        assert ref_real(int(en['c'][i]), m) and abs(float(src.mm[int(en['c'][i]), m]) * 0.999 - en[e + '_px'][i]) < 1e-9
    log.info('PASS b low-price check: %d entries with px/p0 < 0.5 are real bars of the data (no index error)', len(lo))


# ---------------------------------------------------------------- (c) causality: changing data after the decision keeps the entry
def test_c(n=200):
    EN = C.load('entry_t2')
    src, en = real_src()
    rng = np.random.default_rng(2)
    X = src.X
    for e in C.NEW_ENTRIES:
        pick = rng.choice(len(en['k']), size=n, replace=False)
        nf = 0
        for i in pick:
            k, c = int(en['k'][i]), int(en['c'][i])
            m = int(en[e + '_m'][i])
            row = np.array(src.mm[c:c + 1])
            gc, g0, g1, first = _R['g']
            sel = gc == c
            Xc = X[:, c:c + 1].copy()
            cut = m if m >= 0 else 60 * k + C.WIN_MIN          # perturb strictly after the decision minute / window
            hcut = m // 60 if m >= 0 else k + C.WIN_H
            row[0, cut + 1:] *= rng.uniform(0.5, 1.5, size=row.shape[1] - cut - 1).astype(np.float32)
            Xc[hcut + 1:] += rng.normal(0.0, 0.3, size=Xc[hcut + 1:].shape)
            s2 = EN.Src(mm=row, gaps=(np.zeros(int(sel.sum()), np.int64), g0[sel], g1[sel]), first=first[c:c + 1], X=Xc)
            m2, px2 = EN.entry_one(s2, k, 0, e, float(en['p0'][i]))
            assert m2 == m and (m < 0 or px2 == en[e + '_px'][i]), (e, i)
            nf += int(m >= 0)
        log.info('PASS c %s: %d real candidates (filled %d): perturbing prices after the entry minute and OI rows after the '
                 'decision hour leaves entry minute / price unchanged', e, n, nf)


# ---------------------------------------------------------------- (d) exit table from the real entry minute vs reference loop
D_B1 = [(0.15, 24, 0.0, 0.0), (0.15, 72, 0.03, 0.02), (0.30, 168, 0.05, 0.03)]


def ref_exit(mm, FR, c, m, px, kind, prm, cond=None):
    """minute loop from the entry; returns (j' from T_kb, code, xr, fund). kind B1 / PART / STATE."""
    kb, r = divmod(m, 60)
    if kind == 'B1':
        sl, H, a, g = prm
    elif kind == 'PART':
        sl, H = prm
    else:
        zo, sl, H = prm
    armed, trough, part1 = None, None, None
    stc = None
    if kind == 'STATE':
        for h in range(1, 721):
            if kb + h < C.NH and cond[kb + h, c]:
                stc = 60 * (kb + h)
                break
    res = None
    for i in range(1, 60 * H + 1):
        j = m + i
        v = float(mm[c, j])
        if kind == 'PART' and part1 is not None:
            if v >= px:
                res = (j, 'be', 0.5 * (1 - sl) + 0.5 * v * 1.003 / px)
            elif v <= px * (1 - 3 * sl):
                res = (j, 'tp', 0.5 * (1 - sl) + 0.5 * (1 - 3 * sl))
            elif i == 60 * H:
                res = (j, 'time', 0.5 * (1 - sl) + 0.5 * v / px)
            if res:
                break
            continue
        if v >= px * (1 + sl):
            res = (j, 'sl', v * 1.003 / px)
            break
        if kind == 'B1' and a > 0:
            if armed is not None and v >= trough * (1 + g):
                res = (j, 'trail', v * 1.001 / px)
                break
            if armed is None and v <= px * (1 - a):
                armed, trough = i, v
            elif armed is not None:
                trough = min(trough, v)
        if kind == 'PART' and v <= px * (1 - sl):
            part1 = j
            if i == 60 * H:
                res = (j, 'time', 0.5 * (1 - sl) + 0.5 * v / px)
                break
            continue
        if kind == 'STATE' and j == stc:
            res = (j, 'state', v / px)
            break
        if i == 60 * H:
            res = (j, 'time', v / px)
            break
    j, code, xr = res

    def fsum(j0, j1):
        f = 0.0
        for h in range(1, 723):
            b = 60 * (kb + h) - 1
            if b > m and b > j0 and b <= j1 and kb + h < C.NH:
                f += FR[kb + h, c] * float(mm[c, b]) / px
        return f
    if kind == 'PART' and part1 is not None:
        fund = fsum(-1, part1) + 0.5 * fsum(part1, j)
    else:
        fund = fsum(-1, j)
    return j - 60 * kb, code, xr, fund


def test_d(n=300):
    XT = C.load('exits_t2')
    E1 = C.t1('exits_t1')
    src, en = real_src()
    t = XT.load_table('EL_1')
    st = C.b1('exits').Store()
    gc, g0, g1, first = _R['g']
    ok = (t['r'] > 0) & (t['m'] + C.NPATH + 60 < C.NMIN)
    cand = np.flatnonzero(ok)
    rng = np.random.default_rng(4)
    cand = rng.permutation(cand)
    conds = XT.load_conds()
    xis = [CB.xidx(*x) for x in D_B1]
    RN = {CB.R_SL: 'sl', CB.R_TRAIL: 'trail', CB.R_TIME: 'time'}
    used = 0
    for i in cand:
        c, m, px = int(t['c'][i]), int(t['m'][i]), float(t['px'][i])
        sel = (gc == c) & (g1 > m) & (g0 < m + C.NPATH + 60)
        if sel.any():
            continue
        for xi, prm in zip(xis, D_B1):
            jp, code, xr, fund = ref_exit(st.mm, st.FR, c, m, px, 'B1', prm)
            assert t['B1_j'][i, xi] == jp and RN[int(t['B1_rs'][i, xi])] == code, (i, prm)
            assert abs(t['B1_xr'][i, xi] - xr) < 1e-12 and abs(t['B1_fund'][i, xi] - fund) < 1e-12, (i, prm)
        prm = (0.08, 72)
        xi = [j for j, x in enumerate(C.C1.fam_cfgs('PART')) if (x['s'], x['H']) == prm][0]
        jp, code, xr, fund = ref_exit(st.mm, st.FR, c, m, px, 'PART', prm)
        assert t['PART_j'][i, xi] == jp and C.C1.RTNAMES[int(t['PART_rt'][i, xi])] == code, (i, 'PART', jp, code)
        assert abs(t['PART_xr'][i, xi] - xr) < 1e-12 and abs(t['PART_fund'][i, xi] - fund) < 1e-12
        prm = (1.0, 0.15, 168)
        xi = [j for j, x in enumerate(C.C1.fam_cfgs('STATE')) if (x['zo'], x['s'], x['H']) == prm][0]
        jp, code, xr, fund = ref_exit(st.mm, st.FR, c, m, px, 'STATE', prm, conds[1.0])
        assert t['STATE_j'][i, xi] == jp and C.C1.RTNAMES[int(t['STATE_rt'][i, xi])] == code, (i, 'STATE', jp, code)
        assert abs(t['STATE_xr'][i, xi] - xr) < 1e-12 and abs(t['STATE_fund'][i, xi] - fund) < 1e-12
        used += 1
        if used >= n:
            break
    assert used >= n
    log.info('PASS d: %d real EL_1 trades with r > 0 (no gap in path): 3 B1 exits + PART(8%%,72h) + STATE(zo1,15%%,168h) == '
             'reference minute loop (j from T_kb, reason, xr, funding)', used)


# ---------------------------------------------------------------- fake helpers
_F = {}


def fake(seed, plant=False, ncand=600):
    key = (seed, plant, ncand)
    if key not in _F:
        FK = C.load('fake_t2')
        o = FK.make(seed=seed, ns=12, ncand=ncand, plant=plant)
        _F[key] = o
    return _F[key]


def fake_ctx(o, entries):
    FK = C.load('fake_t2')
    G = C.load('grid_t2')
    tabs = FK.tables(o, entries)
    return G.build_ctx(tabs, o.cls, entries), tabs


# ---------------------------------------------------------------- (e) accounting / slots / cooldown (fake data)
def test_e():
    P = C.b1('port')
    G = C.load('grid_t2')
    o = fake(3)
    ctx, tabs = fake_ctx(o, ('EL_1',))
    k0, kl = P.S.kidx(P.S.ms('2022-01-01')), P.S.kidx(P.S.ms('2026-01-01')) - 1
    t = tabs['EL_1']
    nchk = 0
    for (xf, xi) in (('B1', 0), ('B1', 100), ('B1', 194), ('PART', 0), ('STATE', 3)):
        for K in (3, 10):
            for z in (2.5, 3.5):
                tr, eq, m = P.run(K, ctx.cand[('EL_1', z)], G.xview(ctx, 'EL_1', xf, xi), k0, kl)
                assert abs(float(tr['net'].sum()) - (float(eq['eq'].iloc[-1]) - P.INIT)) < 1e-6
                assert abs(m['eq_end_ledger_minus_eq']) < 1e-6
                ke, kx = tr['ke'].values, tr['kx'].values
                for h in np.unique(ke):
                    assert int(((ke <= h) & (kx > h)).sum()) <= K
                for c in np.unique(tr['c']):
                    kk = np.sort(ke[tr['c'].values == c])
                    assert (np.diff(kk) > P.COOL).all()
                kbset = set(zip(t['kb'].tolist(), t['c'].tolist()))
                assert all((a, b) in kbset for a, b in zip(ke.tolist(), tr['c'].tolist()))
                assert (t['kb'][tr['cid'].values] == ke).all() and (kx >= ke).all()
                nchk += 1
    log.info('PASS e: %d fake runs: ledger sum(net) == equity change, <= K open per hour, cooldown > 72 h per coin, entries only at '
             'filled (kb, coin), cid row matches kb', nchk)


# ---------------------------------------------------------------- (f) placebo mechanics (fake data)
def test_f():
    PL = C.load('placebo_t2')
    o = fake(5)
    PL.setup(src=o.src, st=o.st, conds=o.conds, en=o.en, cls=o.cls)
    idx, k, c, d = PL.filled(o.en, 'EL_1')
    ms = PL.draw_time(o.src, k, c, PL.rng_for('time', 'EL_1', 0))
    assert len(ms) == len(k) and (ms >= 60 * k + 1).all() and (ms <= 60 * k + C.WIN_MIN).all()
    assert all(o.src.real(int(cc), int(mm), int(mm) + 1)[0] for cc, mm in zip(c, ms))
    ms2 = PL.draw_perm(o.src, k, c, d, PL.rng_for('perm', 'EL_1', 0))
    yr = C.year_of_k(k)
    for y in np.unique(yr):
        assert sorted((ms2 - 60 * k)[yr == y].tolist()) == sorted(d[yr == y].tolist())     # no gaps in fake => exact permutation
    r1 = PL.one_rep('time', 'EL_1', 0)
    r2 = PL.one_rep('time', 'EL_1', 0)
    for kk in r1:
        if not kk.startswith('sec'):
            assert _eq(r1[kk], r2[kk]), kk
    assert r1['n_used'] == r1['n_filled'] == len(k)
    tmp = tempfile.mkdtemp(prefix='t2f_')
    try:
        for sh in ((0, 2), (1, 2)):
            PL.run(('time',), ('EL_1', 'EB'), {'time': 2}, tmp + '/A', 1, sh)
        PL.run(('time',), ('EL_1', 'EB'), {'time': 2}, tmp + '/B', 3, (0, 1))
        fa, fb = sorted(os.listdir(tmp + '/A')), sorted(os.listdir(tmp + '/B'))
        assert fa == fb and len(fa) == 4
        for f in fa:
            a, b = pd.read_parquet(tmp + '/A/' + f), pd.read_parquet(tmp + '/B/' + f)
            cols = [x for x in a.columns if not x.startswith('sec')]
            assert a[cols].equals(b[cols]), f
    finally:
        shutil.rmtree(tmp)
    log.info('PASS f: placebo same count (%d), minutes inside 48 h window on real bars, perm = within-year permutation, '
             'same seed => same rep, shards 0/2 + 1/2 == single process (4 parts)', len(k))


# ---------------------------------------------------------------- (g) end-to-end on fake data: planted => DAT, noise => KHONG HON E0
def _pipeline(o, nplc, tmp):
    G = C.load('grid_t2')
    SEL = C.load('select_t2')
    PL = C.load('placebo_t2')
    RP = C.load('report_t2')
    ents = ('E0', 'EL_2')
    ctx, tabs = fake_ctx(o, ents)
    df = G.run_grid(ctx, C.all_cfgs(ents), tmp + '/grid', nproc=3)
    sel = SEL.measures(df, ctx, ents)
    PL.setup(src=o.src, st=o.st, conds=o.conds, en=o.en, cls=o.cls)
    PL.run(('time',), ('EL_2',), {'time': nplc}, tmp + '/plc', 3, (0, 1))
    res = PL.summarize(tmp + '/plc', {'EL_2': sel['EL_2']['stat']}, {'time': nplc, 'perm': 20})
    p = res['time|EL_2']['p']
    return RP.criteria(sel['EL_2'], sel['E0'], p, bool(res['time|EL_2']['nrep'] == nplc)), p


def test_g():
    tmp = tempfile.mkdtemp(prefix='t2g_')
    try:
        cr, p = _pipeline(fake(11, plant=True), 19, tmp + '/A')
        log.info('g planted: p=%.3f U=%s verdict=%s', p, cr['U'], cr['verdict'])
        assert cr['verdict'] == 'KIEU VAO DAT'
        cr2, p2 = _pipeline(fake(12, plant=False), 3, tmp + '/B')
        log.info('g noise: p=%.3f U=%s verdict=%s', p2, cr2['U'], cr2['verdict'])
        assert cr2['verdict'] == 'KHONG HON E0'
    finally:
        shutil.rmtree(tmp)
    log.info('PASS g: fake planted EL_2 -> KIEU VAO DAT (19 placebo reps, CHOICES 14); pure noise -> KHONG HON E0 (3 reps)')


# ---------------------------------------------------------------- (h) determinism
def test_h():
    EN = C.load('entry_t2')
    XT = C.load('exits_t2')
    G = C.load('grid_t2')
    src, en = real_src()
    rng = np.random.default_rng(8)
    pick = np.sort(rng.choice(len(en['k']), size=300, replace=False))
    a = EN.compute(src, en['k'][pick], en['c'][pick])
    b = EN.compute(src, en['k'][pick], en['c'][pick])
    assert all(_eq(a[kk], b[kk]) for kk in a)
    assert all(_eq(a[kk], en[kk][pick]) for kk in a)
    st = C.b1('exits').Store()
    conds = XT.load_conds()
    idx, ms, cs, pxs = XT.entry_rows(en, 'EL_2')
    s1 = XT.compute(st, ms[:200], cs[:200], pxs[:200], conds)
    s2 = XT.compute_par(st, ms[:400], cs[:400], pxs[:400], conds, nproc=3, chunk=50)
    t = XT.load_table('EL_2')
    assert all(_eq(s1[kk], s2[kk][:200]) for kk in s1)
    assert all(_eq(s2[kk], t[kk][:400]) for kk in s2)
    o = fake(5)
    ctx, _ = fake_ctx(o, ('EO_3',))
    cf = C.all_cfgs(('EO_3',))[::30]
    tmp = tempfile.mkdtemp(prefix='t2h_')
    try:
        d1 = G.run_grid(ctx, cf, tmp + '/1', nproc=1)
        d2 = G.run_grid(ctx, cf, tmp + '/2', nproc=3)
    finally:
        shutil.rmtree(tmp)
    cols = [x for x in d1.columns if x != 'sec']
    assert d1[cols].equals(d2[cols])
    log.info('PASS h: entries recomputed == saved (300 real), exits serial == parallel == saved (400 real EL_2), fake grid '
             '%d cfgs 1 proc == 3 proc', len(cf))


def test_n12():
    """A1 N1 / N2 on synthetic select dicts: incomplete placebo => U-c False (+ note); E0 not scored in a year => U-f False."""
    RP = C.load('report_t2')

    def sel(t24, t25, sc=(True, True)):
        w = {Y: dict(top20_valid=dict(median_ret=v), scored=s_) for Y, v, s_ in (('2024', t24, sc[0]), ('2025', t25, sc[1]))}
        return dict(wfo=w, describe={f: dict(frac_pos=0.9) for f in ('F1', 'F2', 'F3')} | {'median_n_2024_2025': 500},
                    conc={Y: dict(net_without_best5=1.0) for Y in ('2024', '2025')})
    good, e0 = sel(0.2, 0.3), sel(0.1, 0.1)
    r = RP.criteria(good, e0, 0.0099, True)
    assert r['verdict'] == RP.V_OK and all(r['U'].values())
    r = RP.criteria(good, e0, 0.0099, False)
    assert r['U']['U-c'] is False and r['verdict'] != RP.V_OK and any('chua du' in n for n in r['notes'])
    r = RP.criteria(good, sel(0.1, float('nan'), (True, False)), 0.0099, True)
    assert r['U']['U-f'] is False and r['verdict'] == RP.V_NO and any('E0 khong cham duoc 2025' in n for n in r['notes'])
    r = RP.criteria(good, e0, 0.06, True)
    assert r['U']['U-c'] is False and r['verdict'] == RP.V_NO
    log.info('PASS n12: incomplete placebo => U-c False (note); E0 unscored year => U-f False (note); full => KIEU VAO DAT')


TESTS = {'n12': test_n12, 'a_exits': test_a_exits, 'a_grid': test_a_grid, 'b': test_b, 'c': test_c, 'd': test_d, 'e': test_e, 'f': test_f,
         'g': test_g, 'h': test_h}

if __name__ == '__main__':
    names = sys.argv[1:] or ['all']
    if names == ['all']:
        names = list(TESTS)
    for n in names:
        TESTS[n]()
