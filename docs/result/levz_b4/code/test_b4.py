"""LEVZ B4 tests (PREREG_X3_1127 A7 + MASTER task list). Equality / identity checks only - NO profit aggregation.
usage: python3 code/test_b4.py a|b|c|d|e|f|g|h|i|all   (all = a..g + i; a, b, c, g use the real exit table / real paths;\nd, f synthetic; e, h FAKE data through port / grid / select / report; h ~ 10 min)"""
import os
import sys
import hashlib
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_b4 as C
sys.path.pop(0)
import numpy as np

log = C.setup_log('test')
CB = C.CB
X = C.load('exits_b4')
XB1 = C.b1('exits')
BIG = C.BIG
FEE = C.FEE
CMP = ('j', 'rs', 'xr', 'fund', 'mx', 'mxh', 'flag')


def _rows(n, m=600):
    return np.unique(np.linspace(0, n - 1, m).astype(np.int64))


def test_a():
    """n_add = 0 reproduces B1 (trailing cfgs) and T1 STATE (H 168) exactly; NONE hourly == B1 hourly (600 recomputed rows)."""
    T, HK = X.load_table()
    ucid = T['ucid']
    bz = np.load(CB.WORK + '/exits.npz')
    b = {kk: bz[kk] for kk in CMP + ('k', 'c', 'mk', 'hm', 'fh', 'fc')}       # preload (NpzFile re-reads on every access)
    tz = np.load(C.T1WORK + '/exits_t1_STATE.npz')
    t1 = {kk: tz[kk] for kk in CMP + ('rt', 'k', 'c')}
    assert (t1['k'][ucid] == T['k']).all() and (t1['c'][ucid] == T['c']).all()
    st1 = C.C1.fam_cfgs('STATE')
    nb = nt = 0
    skipped = []
    for xi, x in enumerate(C.XLIST):
        if x['dca'] != 'NONE':
            continue
        if x['ex'] == 'STATE':
            m = [i for i, d in enumerate(st1) if d['zo'] == 0.0 and d['s'] == x['s'] and d['H'] == x['H']]
            if not m:
                skipped.append('STATE s=%.2f H=%d (khong co trong T1)' % (x['s'], x['H']))
                continue
            ref = {kk: t1[kk][ucid, m[0]] for kk in CMP}
            ref['rt'] = t1['rt'][ucid, m[0]]
            for kk in CMP + ('rt',):
                assert np.array_equal(T[kk][:, xi], ref[kk].astype(T[kk].dtype)), ('T1', xi, kk)
            nt += 1
        else:
            bx = CB.xidx(x['s'], x['H'], x['arm'], x['gap'])
            for kk in CMP:
                assert np.array_equal(T[kk][:, xi], b[kk][ucid, bx].astype(T[kk].dtype)), ('B1', xi, kk)
            nb += 1
    assert nb == 8 and nt == 2, (nb, nt)
    st = XB1.Store()
    rr = _rows(len(ucid))
    for i in rr:
        p, nv, mm, gm, fh, lg = XB1.path_of(st, int(T['c'][i]), int(T['k'][i]))
        K = X.Kind(p, nv, fh, 0, 0.0)
        for kk in ('mk', 'hm', 'fh'):
            assert np.array_equal(getattr(K, kk), b[kk][ucid[i]]), ('hourly', kk, i)
        assert np.array_equal(np.cumsum(K.fh), b['fc'][ucid[i]])
    log.info('test a PASS: %d B1 trailing cfgs + %d T1 STATE cfgs x %d rows exact; NONE hourly exact on %d rows; khong kiem: %s',
             nb, nt, len(ucid), len(rr), skipped)


def ref_one(p, nv, miss_m, fh, gm, n, a, s, arm, gap, hh, state_m):
    """pure-Python minute loop (independent of exits_b4)."""
    pl = [float(v) for v in p[:nv]]
    p0 = pl[0]
    N = 1.0 / (1 + n)
    L = [p0 * (1.0 + a * l) for l in range(1, n + 1)]
    fm = [BIG] * n
    legs = [p0]
    armed, trough = False, None
    j, rt = None, None
    for i in range(1, nv):
        pi = pl[i]
        for l in range(n):
            if fm[l] == BIG and pi >= L[l] * (1.0 - 1e-12):
                fm[l] = i
                legs.append(L[l])
        q = 0.0
        for x in legs:
            q += N / x
        avg = p0 if len(legs) == 1 else N * len(legs) / q
        if pi >= avg * (1.0 + s):
            j, rt = i, C.RT_SL
            break
        if arm > 0:
            if armed:
                if pi >= trough * (1.0 + gap):
                    j, rt = i, C.RT_TRAIL
                    break
                trough = min(trough, pi)
            elif pi <= avg * (1.0 - arm):
                armed, trough = True, pi
        if i == state_m:
            j, rt = i, C.RT_STATE
            break
        if i == 60 * hh:
            j, rt = i, C.RT_TIME
            break
        if i == miss_m:
            j, rt = i, C.RT_MISS
            break
    if j is None:
        j, rt = nv - 1, C.RT_EOD
    xp = pl[j] * (1.0 + CB.SL_SLIP if rt == C.RT_SL else (1.0 + CB.TR_SLIP if rt == C.RT_TRAIL else 1.0))
    filled = [(p0, 0)] + [(L[l], fm[l]) for l in range(n) if fm[l] <= j]
    fund = 0.0
    for h in range(1, min((j + 1) // 60, CB.HMAX) + 1):
        w = sum(N * p0 / Lx for Lx, f in filled if f < 60 * h - 1)
        fund += w * fh[h]
    gross = sum(N * (1.0 - xp / Lx) for Lx, f in filled)
    fees = FEE * N * len(filled) + FEE * sum(N * xp / Lx for Lx, f in filled)
    retb = gross - fees + fund
    unf = n + 1 - len(filled)
    xr = sum(N * xp / Lx for Lx, f in filled) + N * unf * (1.0 - FEE) / (1.0 + FEE)
    qty = sum(N / Lx for Lx, f in filled)
    mkm = [N * unf * 0 + sum(N * pl[i] / Lx for Lx, f in filled if f <= i) + N * (n + 1 - sum(1 for Lx, f in filled if f <= i)) * (1.0 - FEE)
           for i in range(0, j + 1)]
    return dict(j=j, rt=rt, xr=xr, fund=fund, retb=retb, nleg=len(filled), avg=N * len(filled) / qty / p0, mx=max(mkm),
                fills=[f for Lx, f in filled[1:]])


def test_b(m=600, per=8):
    """reference loop vs exits_b4 on >= 500 real candidates x 8 DCA cfgs each (all 48 DCA cfgs covered)."""
    T, HK = X.load_table()
    st = XB1.Store()
    dx = [xi for xi, x in enumerate(C.XLIST) if x['n_add'] > 0]
    rr = _rows(len(T['k']), m)
    nchk = 0
    seen = set()
    for t, i in enumerate(rr):
        p, nv, mm, gm, fh, lg = XB1.path_of(st, int(T['c'][i]), int(T['k'][i]))
        sth = int(T['sth'][i])
        for u in range(per):
            xi = dx[(t * per + u) % len(dx)]
            seen.add(xi)
            x = C.XLIST[xi]
            sm = 60 * sth if (x['ex'] == 'STATE' and sth < BIG) else BIG
            r = ref_one(p, nv, mm, fh, gm, x['n_add'], x['a'], x['s'], x['arm'], x['gap'], x['H'], sm)
            assert int(T['j'][i, xi]) == r['j'] and int(T['rt'][i, xi]) == r['rt'] and int(T['nleg'][i, xi]) == r['nleg'], (i, xi, r)
            for kk in ('xr', 'fund', 'retb', 'avg', 'mx'):
                assert abs(float(T[kk][i, xi]) - r[kk]) <= 1e-12 * max(1.0, abs(r[kk])), (i, xi, kk, T[kk][i, xi], r[kk])
            # port identity: net per budget from xr_eff / fund_eff == direct DCA ledger
            pn = 1.0 - T['xr'][i, xi] - FEE * (1.0 + T['xr'][i, xi]) + T['fund'][i, xi]
            assert abs(pn - r['retb']) <= 1e-12, (i, xi, pn, r['retb'])
            # hourly mark of the kind == reference MTM at minutes 60 h <= j
            h = HK[x['dca']]
            K = X.Kind(p, nv, fh, x['n_add'], x['a'])
            assert np.array_equal(K.mk, h['mk'][i]) and np.array_equal(K.fh, h['fh'][i])
            nchk += 1
    # STATE H 72 with n_add = 0 has no T1 twin (test a): reference loop on 300 real candidates, both SL
    sx = [xi for xi, x in enumerate(C.XLIST) if x['dca'] == 'NONE' and x['ex'] == 'STATE' and x['H'] == 72]
    ns = 0
    for i in rr[:300]:
        p, nv, mm, gm, fh, lg = XB1.path_of(st, int(T['c'][i]), int(T['k'][i]))
        sth = int(T['sth'][i])
        for xi in sx:
            x = C.XLIST[xi]
            r = ref_one(p, nv, mm, fh, gm, 0, 0.0, x['s'], 0.0, 0.0, 72, 60 * sth if sth < BIG else BIG)
            assert int(T['j'][i, xi]) == r['j'] and int(T['rt'][i, xi]) == r['rt'], (i, xi)
            for kk in ('xr', 'fund', 'retb', 'mx'):
                assert abs(float(T[kk][i, xi]) - r[kk]) <= 1e-12 * max(1.0, abs(r[kk])), (i, xi, kk)
            ns += 1
    assert len(rr) >= 500 and seen == set(dx) and ns >= 400
    log.info('test b PASS: %d candidates x %d cfgs = %d checks, all %d DCA cfgs covered; STATE H72 n_add 0: %d candidates x 2 SL = %d',
             len(rr), per, nchk, len(dx), min(300, len(rr)), ns)


def test_c(m=200):
    """causality: prices after the exit minute do not change the result; legs fill only at/below the exit minute at close >= level."""
    T, HK = X.load_table()
    st = XB1.Store()
    rng = np.random.default_rng(7)
    rr = _rows(len(T['k']), m)
    n = 0
    for i in rr:
        p, nv, mm, gm, fh, lg = XB1.path_of(st, int(T['c'][i]), int(T['k'][i]))
        sth = int(T['sth'][i])
        rows, kinds = X.candidate(p, nv, mm, gm, fh, sth)
        for xi, x in enumerate(C.XLIST):
            r = rows[xi]
            j = r['j']
            q = p.copy()
            q[j + 1:] = q[j + 1:] * rng.uniform(0.5, 2.0, len(q) - j - 1)
            fq = fh.copy()          # funding beyond the exit hour perturbed too
            hx = (j + 1) // 60
            fq[hx + 1:] = rng.normal(0, 1e-3, len(fq) - hx - 1)
            K = X.Kind(q, nv, fq, x['n_add'], x['a'])
            sm = 60 * sth if (x['ex'] == 'STATE' and sth < BIG) else BIG
            r2 = X.exit_one(q, nv, mm, gm, K, x['s'], x['arm'], x['gap'], x['H'], sm)
            for kk in X.KEYS:
                assert r[kk] == r2[kk], (i, xi, kk)
            K0 = kinds[x['dca']]
            for f, Lv in zip(K0.f, K0.L):
                if f <= j:
                    assert p[f] >= Lv * (1 - 1e-12) and (f == 1 or p[1:f].max() < Lv * (1 - 1e-12)), (i, xi)
            n += 1
    log.info('test c PASS: %d (candidate, cfg) perturbed after exit -> identical; fills causal', n)


def synth(pts, fhv=0.0):
    """piecewise-constant path from [(minute, price)] (price holds until next point); nv = NPATH; constant funding fhv per hour."""
    p = np.empty(CB.NPATH)
    for (m0, v), nxt in zip(pts, pts[1:] + [(CB.NPATH, None)]):
        p[m0:nxt[0]] = v
    fh = np.zeros(CB.HMAX + 1)
    fh[1:] = fhv
    return p, CB.NPATH, BIG, None, fh


def run1(path, dca, s, ex, hh, sth=BIG):
    p, nv, mm, gm, fh = path
    xi = [i for i, x in enumerate(C.XLIST) if (x['dca'], x['s'], x['ex'], x['H']) == (dca, s, ex, hh)][0]
    x = C.XLIST[xi]
    K = X.Kind(p, nv, fh, x['n_add'], x['a'])
    sm = 60 * sth if (ex == 'STATE' and sth < BIG) else BIG
    return X.exit_one(p, nv, mm, gm, K, x['s'], x['arm'], x['gap'], x['H'], sm)


def test_d():
    """hand ledgers (3 trades)."""
    # 1) one leg (D1_5, leg 105 never reached), flat 100 then 98 at the 72 h time stop
    r = run1(synth([(0, 100.0), (60, 98.0)]), 'D1_5', 0.15, 'TR10_5', 72)
    exp = 0.5 * (1 - 0.98) - 0.0007 * 0.5 - 0.0007 * 0.5 * 0.98
    assert r['nleg'] == 1 and r['j'] == 4320 and r['rt'] == C.RT_TIME and abs(r['retb'] - exp) < 1e-12, r
    assert abs((1 - r['xr'] - FEE * (1 + r['xr']) + r['fund']) - exp) < 1e-12
    # 2) two legs then SL from average cost: 105 at min 10 (fill), 118 at min 20 (avg 102.439 -> SL level 117.805)
    r = run1(synth([(0, 100.0), (10, 105.0), (20, 118.0)]), 'D1_5', 0.15, 'TR10_5', 72)
    avg = 1.0 / (0.5 / 100 + 0.5 / 105)
    xp = 118.0 * 1.003
    exp = 0.5 * (1 - xp / 100) + 0.5 * (1 - xp / 105) - 0.0007 * 1.0 - 0.0007 * (0.5 * xp / 100 + 0.5 * xp / 105)
    assert r['nleg'] == 2 and r['j'] == 20 and r['rt'] == C.RT_SL and abs(r['avg'] - avg / 100) < 1e-12 and abs(r['retb'] - exp) < 1e-12, r
    assert -r['worst'] <= 1.5 * 0.15 and abs(exp - (-0.15686925)) < 1e-6
    # 3) three legs then trailing 5/3 from avg, with funding 0.0001 per hour
    path = synth([(0, 100.0), (10, 105.0), (20, 110.0), (100, 95.0), (130, 90.0), (200, 93.0)], 0.0001)
    r = run1(path, 'D2_5', 0.30, 'TR5_3', 168)
    N = 1 / 3
    xp = 93.0 * 1.001
    Ls = (100.0, 100.0 * (1.0 + 0.05 * 1), 100.0 * (1.0 + 0.05 * 2))     # limit fills at EXACTLY the level
    fund = 3 * 0.0001 * sum(N * 100 / Lx for Lx in Ls)        # boundaries h = 1, 2, 3 (59, 119, 179 <= 200)
    exp = sum(N * (1 - xp / Lx) for Lx in Ls) - 0.0007 * 1.0 - 0.0007 * sum(N * xp / Lx for Lx in Ls) + fund
    assert r['nleg'] == 3 and r['j'] == 200 and r['rt'] == C.RT_TRAIL and abs(r['retb'] - exp) < 1e-12 and abs(r['fund'] - fund) < 1e-15, r
    assert abs(r['avg'] - 3 / sum(1 / Lx for Lx in Ls) / 100) < 1e-12
    # max loss per slot <= theory: SL s from avg on a 1-minute jump to the level => loss <= (1 + s) 1.003 - 1 + 2 FEE (1 + s)
    for dca in C.DNAMES:
        for s in C.SLS:
            r = run1(synth([(0, 100.0), (5, 100.0 * (1 + s) * 3)]), dca, s, 'TR5_3', 72)
            assert -r['retb'] <= (1 + s) * 3 * 1.003 - 1 + 2 * FEE * (1 + s) * 3 + 1e-12      # gap jump: bounded by the jump itself
            r = run1(synth([(0, 100.0)] + [(10 * q, 100.0 * (1 + 0.001 * q)) for q in range(1, 600)]), dca, s, 'TR5_3', 168)
            assert r['rt'] == C.RT_SL and -r['retb'] <= (1 + s) * 1.001 * 1.003 - 1 + 2 * FEE * (1 + s) + 1e-12, (dca, s, r)
    log.info('test d PASS: 3 hand ledgers + max-loss bounds')


def test_f():
    """synthetic: pump then crash => every DCA kind beats NONE; one-way squeeze to SL => DCA NOT better than NONE beyond 0.1 % of budget
    (with SL from average cost the realised loss on a filled budget is the same s: CHOICES_B4 #9); crash without pump => DCA worse."""
    pump = synth([(0, 100.0)] + [(10 * q, 100.0 + q) for q in range(1, 26)] + [(400, 70.0), (500, 80.0)])
    r0 = run1(pump, 'NONE', 0.30, 'TR10_5', 168)['retb']
    for d in C.DNAMES[1:]:
        assert run1(pump, d, 0.30, 'TR10_5', 168)['retb'] > r0, d
    sq = synth([(0, 100.0)] + [(q, 100.0 * (1 + 0.0002 * q)) for q in range(1, 20000)])
    for s in C.SLS:
        r0 = run1(sq, 'NONE', s, 'TR5_3', 168)['retb']
        for d in C.DNAMES[1:]:
            r = run1(sq, d, s, 'TR5_3', 168)
            assert r['rt'] == C.RT_SL and r['retb'] <= r0 + 0.001, (d, s, r['retb'], r0)
    crash = synth([(0, 100.0), (30, 80.0)])
    r0 = run1(crash, 'NONE', 0.15, 'TR10_5', 72)['retb']
    for d in C.DNAMES[1:]:
        assert run1(crash, d, 0.15, 'TR10_5', 72)['retb'] < r0, d
    log.info('test f PASS: pump-crash DCA > NONE; squeeze DCA <= NONE + 0.1 pct; crash-no-pump DCA < NONE')


def test_g():
    """determinism: two computations of 150 real candidates -> identical bytes."""
    T, HK = X.load_table()
    st = XB1.Store()
    rr = _rows(len(T['k']), 150)
    hs = []
    for _ in range(2):
        A, HA = X.compute(st, T['k'][rr], T['c'][rr], T['sth'][rr])
        h = hashlib.sha256()
        for kk in X.KEYS:
            h.update(np.ascontiguousarray(A[kk]).tobytes())
        for dn in C.DNAMES:
            for kk in ('mk', 'hm', 'fh'):
                h.update(HA[dn][kk].tobytes())
        hs.append(h.hexdigest())
        for kk in X.KEYS:
            assert np.array_equal(A[kk], T[kk][rr]), kk
    assert hs[0] == hs[1]
    log.info('test g PASS: deterministic + equal to stored table (sha %s)', hs[0][:16])


def test_e():
    """port on FAKE data (pump + rand): ledger PnL == equity change, open slots <= K at every hour, each trade's notional = the WHOLE
    slot budget eq(ke) x 0.60 / K (unfilled legs keep their budget idle; nobody else uses it), trade ret == exits_b4 retb per budget."""
    G = C.load('grid_b4')
    P = C.b1('port')
    name, a, b = [f for f in P.FOLDS if f[0] == 'DEV'][0]
    k0, kl = P.S.kidx(P.S.ms(a)), P.S.kidx(P.S.ms(b)) - 1
    n = nidle = 0
    for kind in ('pump', 'rand'):
        ctx = G.build_fake(kind, 2)
        for xi in range(C.NX):
            for K, z in ((3, 2.5), (10, 3.0)):
                dbg = []
                tr, eq, m = P.run(K, ctx.cand[z], X.view(ctx.T, ctx.HK, xi), k0, kl, debug=dbg)
                scale = max(1.0, float(np.abs(eq['eq']).max()))
                assert abs(m['acct_err']) <= 1e-9 * scale and abs(m['eq_end_ledger_minus_eq']) <= 1e-9 * scale, (kind, xi, K, m['acct_err'])
                cnt = np.zeros(kl - k0 + 2)
                np.add.at(cnt, tr['ke'].values - k0, 1)
                np.add.at(cnt, tr['kx'].values - k0, -1)
                assert np.cumsum(cnt).max() <= K, (kind, xi, K)
                eqk = dict(dbg)
                for ke, N in zip(tr['ke'].values, tr['notional_in'].values):
                    assert abs(N - eqk[int(ke)] * 0.60 / K) <= 1e-12 * N, (kind, xi, ke)
                ok = tr['reason'].values != 'eod'
                cid = tr['cid'].values.astype(np.int64)
                assert np.allclose(tr['ret'].values[ok], ctx.T['retb'][cid[ok], xi], rtol=0, atol=1e-12)
                nidle += int((ctx.T['nleg'][cid, xi] < C.XLIST[xi]['n_add'] + 1).sum())
                n += 1
    assert nidle > 0
    log.info('test e PASS: %d port runs (60 cfgs x 2 K/z x pump/rand, DEV): acct, slots <= K, whole-budget notional, ret == retb; '
             '%d trades with unfilled legs keep their slot', n, nidle)


def test_h(nrand=20):
    """end-to-end on FAKE data: pump-then-crash => at least one DCA kind 'DCA DAT'; driftless random walk x nrand seeds => count
    kinds reaching 'DCA DAT' (false alarm rate reported; the test FAILS only if > 10 % of (seed, kind) pairs are DAT)."""
    G = C.load('grid_b4')
    S4 = C.load('select_b4')
    R4 = C.load('report_b4')

    def verdicts(kind, seed):
        ctx = G.build_fake(kind, seed)
        df = G.run_grid(ctx)
        rows = R4.build(S4.measures(df, ctx))
        return {dn: rows[dn]['verdict'] for dn in C.DNAMES[1:]}
    v = verdicts('pump', 1)
    assert any(x == R4.V_OK for x in v.values()), v
    fa = part = 0
    for sd in range(100, 100 + nrand):
        vv = verdicts('rand', sd)
        fa += sum(x == R4.V_OK for x in vv.values())
        part += sum(x == R4.V_PART for x in vv.values())
        log.info('test h rand seed %d: %s', sd, vv)
    tot = 4 * nrand
    assert fa <= 0.10 * tot, (fa, tot)
    log.info('test h PASS: pump -> %s; rand %d seeds: DAT %d / %d (%.1f pct), CO CAI THIEN %d / %d', v, nrand, fa, tot, 100.0 * fa / tot,
             part, tot)


def test_i():
    """ERRATA1 E1 branch of report_b4.criteria on hand-made select dicts (FAKE): NONE unscored + DCA top-20 median > 0 => V-b True;
    NONE unscored + DCA median <= 0 => V-b False; NONE scored => compared with NONE's top-20 median as before."""
    R4 = C.load('report_b4')

    def sel(m24, m25, scored=(True, True), kmed=(-0.01, -0.02)):
        w = {}
        for Y, m, sc, km in zip(('2024', '2025'), (m24, m25), scored, kmed):
            w[Y] = dict(scored=sc, top20_valid=dict(median_ret=m) if sc else dict(n=0), kind_median_test=km)
        return dict(n_cfg=108, wfo=w, describe={f: dict(frac_pos=0.6) for f in ('F1', 'F2', 'F3', 'DEV')}, conc={})
    un = sel(None, None, scored=(False, False), kmed=(-0.05, 0.03))
    r = R4.criteria(sel(0.02, 0.01), un)
    assert r['V']['V-b'] and r['vb_base'] == {'2024': 0.0, '2025': 0.0}
    assert sum('KHONG DCA khong cham duoc nam' in n for n in r['notes']) == 2 and any('-0.05' in n for n in r['notes'])
    assert not R4.criteria(sel(0.02, 0.0), un)['V']['V-b']
    assert not R4.criteria(sel(-0.01, 0.05), un)['V']['V-b']
    half = sel(0.10, None, scored=(True, False), kmed=(0.0, 0.01))          # NONE scores 2024 only
    assert R4.criteria(sel(0.11, 0.001), half)['V']['V-b'] and not R4.criteria(sel(0.09, 0.5), half)['V']['V-b']
    sc = sel(0.05, 0.05)
    assert R4.criteria(sel(0.06, 0.06), sc)['V']['V-b'] and not R4.criteria(sel(0.05, 0.06), sc)['V']['V-b']
    assert not R4.criteria(sel(0.04, 0.10), sc)['V']['V-b']
    ku = sel(None, 0.2, scored=(False, True))                                 # kind unscored => V-a, V-b False
    r = R4.criteria(ku, un)
    assert not r['V']['V-a'] and not r['V']['V-b']
    log.info('test i PASS: ERRATA1 E1 V-b branches (NONE unscored -> baseline 0; NONE scored -> unchanged; kind unscored -> False)')


if __name__ == '__main__':
    which = sys.argv[1]
    for t in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'i'):
        if which in (t, 'all'):
            globals()['test_' + t]()
    if which == 'h':
        test_h()
