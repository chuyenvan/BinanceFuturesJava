"""LEVZ T1 tests (PREREG_LEVZ_T1 sec 6). usage: python3 test/test_t1.py [a b c d e f g ...] -> test/test_report_<parts>.json
(a) engine regression vs B1 exits.npz on >= 500 real candidates; (b) slow pure-Python reference for BRK/VOL/PART/STATE >= 500 trades;
(c) HEDGE h = 0 == B1 port exactly; (d) no look-ahead (VOL u, STATE); (e) ledger PnL == equity change; (f) full pipeline on FAKE paths;
(g) determinism. Real data used ONLY for exit tables (no portfolio / profit aggregation on real data)."""
import os
import sys
import json
import logging
import time
sys.dont_write_bytecode = True
CODE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'code')
sys.path.insert(0, CODE)
import common_t1 as C
sys.path.pop(0)
import numpy as np

log = logging.getLogger('levz_t1.test')
E = C.load('exits_t1')
CB = C.CB
XB1 = C.b1('exits')
RES = {}
SEED = 20261126


def rec(name, ok, **kw):
    RES[name] = dict(PASS=bool(ok), **kw)
    log.info('%s %s %s', 'PASS' if ok else 'FAIL', name, kw)


def sample_real(n, seed=SEED):
    cz = np.load(CB.WORK + '/cand_b1.npz')
    rng = np.random.default_rng(seed)
    idx = np.sort(rng.choice(len(cz['U_k']), size=n, replace=False))
    return idx, cz['U_k'][idx], cz['U_c'][idx]


# ---------------------------------------------------------------- (a)
def test_a(n=600):
    idx, ks, cs = sample_real(n)
    zf = np.load(CB.WORK + '/exits.npz')
    z = {kk: zf[kk] for kk in ('j', 'rs', 'xr', 'fund', 'mx', 'mxh', 'flag')}
    st = XB1.Store()
    bad = {}
    ncmp = 0
    for ii, (i, k, c) in enumerate(zip(idx, ks, cs)):
        p, nv, miss_m, gm, fh, lg = XB1.path_of(st, int(c), int(k))
        cu = E.Cur(p, nv, miss_m, fh, gm)
        for sl in CB.SLS:
            for hh in CB.HS:
                xi = CB.xidx(sl, hh, 0.0, 0.0)
                for mode in ('brk', 'state_never'):
                    r = E.bracket(cu, sl, None, hh) if mode == 'brk' else E.bracket(cu, sl, None, hh, E.BIG)
                    ref = dict(j=int(z['j'][i, xi]), rs=int(z['rs'][i, xi]), xr=float(z['xr'][i, xi]), fund=float(z['fund'][i, xi]),
                               mx=float(z['mx'][i, xi]), mxh=float(z['mxh'][i, xi]), flag=int(z['flag'][i, xi]))
                    got = dict(j=r['j'], rs=int(C.RT2RS[r['rt']]), xr=r['xr'], fund=r['fund'], mx=r['mx'], mxh=r['mxh'], flag=r['flag'])
                    ncmp += 1
                    for kk in ref:
                        if ref[kk] != got[kk]:
                            bad.setdefault(kk, 0)
                            bad[kk] += 1
    rec('a_engine_eq_b1_no_trail', not bad, candidates=n, comparisons=ncmp, mismatches=bad, note='exact equality (bitwise)')


# ---------------------------------------------------------------- fake context (no real data)
_FK = {}


def fake_ctx():
    if 'ctx' not in _FK:
        FK = C.load('fake_t1')
        G = C.load('grid_t1')
        _FK['F'] = FK.make()
        _FK['ctx'] = G.build_fake(_FK['F'])
        _FK['G'] = G
    return _FK['ctx'], _FK['G']


def _eq_dict(a, b, skip=('sec',)):
    bad = []
    for kk in b:
        if kk in skip:
            continue
        x, y = a.get(kk), b[kk]
        if isinstance(y, float) and np.isnan(y):
            if not (isinstance(x, float) and np.isnan(x)):
                bad.append(kk)
        elif x != y:
            bad.append(kk)
    return bad


# ---------------------------------------------------------------- (c)
def test_c():
    ctx, G = fake_ctx()
    P = C.b1('port')
    HG = C.load('hedge_t1')
    ncfg, bad, ntr = 0, {}, 0
    for base, xi in (('BRK', 0), ('BRK', 47), ('BRK', 89), ('B1', 12), ('B1', 170), ('B1', 72)):
        X = G.xview(ctx, base, xi)
        for z in C.ZS:
            for K in C.KS:
                for g in C.GATES:
                    cand = ctx.cand[(z, g)]
                    a = HG.run_all(K, cand, X, 0.0, ctx.legs['BTCETH'])
                    b = P.run_all(K, cand, X)
                    d = _eq_dict(a, b)
                    for name, a0, b0 in P.FOLDS:
                        k0 = P.S.kidx(P.S.ms(a0)); kl = P.S.kidx(P.S.ms(b0)) - 1
                        t1, e1, _ = HG.run(K, cand, X, k0, kl, 0.0, ctx.legs['BTC'])
                        t2, e2, _ = P.run(K, cand, X, k0, kl)
                        ntr += len(t2)
                        if not (t1.equals(t2) and e1.equals(e2)):
                            d.append('frames_' + name)
                    ncfg += 1
                    if d:
                        bad[(base, xi, z, K, g)] = d
    rec('c_hedge_h0_eq_b1_port', not bad, configs=ncfg, trades_compared=ntr, mismatches=str(bad)[:500], data='FAKE paths')
# appended into test_t1.py (tests b d e f g)


# ---------------------------------------------------------------- (b) slow independent reference (pure Python per minute)
def ref_single(p, nv, miss_m, fh, sl, tp, hh, state_m):
    p0 = float(p[0])
    fund = 0.0
    for i in range(1, nv):
        if (i + 1) % 60 == 0 and (i + 1) // 60 <= 720:
            fund += float(fh[(i + 1) // 60])
        x = float(p[i])
        if x >= p0 * (1.0 + sl):
            return i, 'sl', x * 1.003 / p0, fund
        if tp and x <= p0 * (1.0 - tp):
            return i, 'tp', 1.0 - tp, fund
        if i == state_m:
            return i, 'state', x / p0, fund
        if i == 60 * hh:
            return i, 'time', x / p0, fund
        if i == miss_m:
            return i, 'miss', x / p0, fund
    return nv - 1, 'eod', float(p[nv - 1]) / p0, fund


def ref_part(p, nv, miss_m, fh, s, hh):
    p0 = float(p[0])
    fund = 0.0
    ph, i1 = 0, None
    for i in range(1, nv):
        if (i + 1) % 60 == 0 and (i + 1) // 60 <= 720:
            fund += float(fh[(i + 1) // 60]) * (1.0 if ph == 0 else 0.5)
        x = float(p[i])
        if ph == 0:
            if x >= p0 * (1.0 + s):
                return i, 'sl', x * 1.003 / p0, fund, -1
            if x <= p0 * (1.0 - s):
                ph, i1 = 1, i
                if i == 60 * hh:
                    return i, 'time', 0.5 * (1 - s) + 0.5 * x / p0, fund, i1
                if i == miss_m:
                    return i, 'miss', 0.5 * (1 - s) + 0.5 * x / p0, fund, i1
                continue
            if i == 60 * hh:
                return i, 'time', x / p0, fund, -1
            if i == miss_m:
                return i, 'miss', x / p0, fund, -1
        else:
            if x >= p0:
                return i, 'be', 0.5 * (1 - s) + 0.5 * x * 1.003 / p0, fund, i1
            if x <= p0 * (1.0 - 3 * s):
                return i, 'tp', 0.5 * (1 - s) + 0.5 * (1 - 3 * s), fund, i1
            if i == 60 * hh:
                return i, 'time', 0.5 * (1 - s) + 0.5 * x / p0, fund, i1
            if i == miss_m:
                return i, 'miss', 0.5 * (1 - s) + 0.5 * x / p0, fund, i1
    x = float(p[nv - 1]) / p0
    return nv - 1, 'eod', (0.5 * (1 - s) + 0.5 * x) if ph else x, fund, (i1 if ph else -1)


def ref_u(CL, k, c):
    import math
    rs = []
    for t in range(max(1, k - 167), k + 1):
        a, b = float(CL[t - 1, c]), float(CL[t, c])
        if math.isfinite(a) and math.isfinite(b) and a > 0 and b > 0:
            rs.append(math.log(b / a))
    if len(rs) < 24:
        return float('nan')
    mu = sum(rs) / len(rs)
    return math.sqrt(sum((r - mu) ** 2 for r in rs) / (len(rs) - 1)) * math.sqrt(24.0)


def ref_state_h(sig, k, c, zo):
    for h in range(1, 721):
        r = k + h
        if r >= sig['z_oi'].shape[0]:
            break
        a, b, f = float(sig['z_oi'][r, c]), float(sig['z_f'][r, c]), float(sig['f'][r, c])
        if a < zo or b < zo or f <= 0.0001:
            return h
    return None


def test_b(n=500, per=3):
    idx, ks, cs = sample_real(n, seed=SEED + 1)
    st = XB1.Store()
    CL = E.load_CL()
    sig = E.load_sig()
    conds = {zo: E.state_cond(sig, zo) for zo in C.STATE_Z}
    rng = np.random.default_rng(SEED + 2)
    bad = {f: 0 for f in E.FAMS}
    cnt = {f: 0 for f in E.FAMS}
    reasons = {f: {} for f in E.FAMS}
    ex = []
    umax = 0.0
    for k, c in zip(ks, cs):
        k, c = int(k), int(c)
        p, nv, miss_m, gm, fh, lg = XB1.path_of(st, c, k)
        mi = miss_m if miss_m < nv else -1
        cu = E.Cur(p, nv, miss_m, fh, gm)
        u, _ = E.vol_u(CL, k, c)
        ur = ref_u(CL, k, c)
        if np.isfinite(ur) or np.isfinite(u):
            umax = max(umax, abs(u - ur) / max(abs(ur), 1e-12) if np.isfinite(ur) and np.isfinite(u) else 1.0)
        for fam in E.FAMS:
            xs = C.fam_cfgs(fam)
            for xi in rng.choice(len(xs), size=per, replace=False):
                x = xs[int(xi)]
                if fam == 'BRK':
                    g = E.bracket(cu, x['s'], x['R'] * x['s'], x['H'])
                    r = ref_single(p, nv, mi, fh, x['s'], x['R'] * x['s'], x['H'], -1)
                elif fam == 'VOL':
                    sl = C.VOL_CAP if not np.isfinite(ur) else min(max(x['a'] * ur, 0.02), 0.5)
                    g = E.bracket(cu, E.vol_sl(x['a'], u), x['R'] * E.vol_sl(x['a'], u) if x['R'] > 0 else None, x['H'])
                    r = ref_single(p, nv, mi, fh, sl, x['R'] * sl if x['R'] > 0 else 0.0, x['H'], -1)
                elif fam == 'STATE':
                    hs = ref_state_h(sig, k, c, x['zo'])
                    he = E.state_hour(conds[x['zo']], k, c)
                    g = E.bracket(cu, x['s'], None, x['H'], 60 * he if he < E.BIG else E.BIG)
                    r = ref_single(p, nv, mi, fh, x['s'], 0.0, x['H'], 60 * hs if hs else -1)
                else:
                    g = E.part(cu, x['s'], x['H'])
                    r = ref_part(p, nv, mi, fh, x['s'], x['H'])
                cnt[fam] += 1
                nm = C.RTNAMES[g['rt']]
                reasons[fam][r[1]] = reasons[fam].get(r[1], 0) + 1
                ok = (g['j'] == r[0] and nm == r[1] and abs(g['xr'] - r[2]) <= 1e-12 * max(1, abs(r[2]))
                      and abs(g['fund'] - r[3]) <= 1e-12)
                if fam == 'PART':
                    ok = ok and int(g['j1']) == int(r[4])
                if not ok:
                    bad[fam] += 1
                    if len(ex) < 5:
                        ex.append((fam, k, c, x, dict(j=g['j'], rt=nm, xr=g['xr'], fund=g['fund']), r[:4]))
    rec('b_slow_reference', not any(bad.values()) and umax <= 1e-9 and min(cnt.values()) >= 500, trades=cnt, mismatches=bad,
        vol_u_max_rel_err=umax, ref_reasons=reasons, examples=str(ex)[:800], data='REAL candidates (exit tables only)')


# ---------------------------------------------------------------- (d) no look-ahead
def test_d(n=300):
    idx, ks, cs = sample_real(n, seed=SEED + 3)
    CL = E.load_CL().copy()
    sig = E.load_sig()
    rng = np.random.default_rng(SEED + 4)
    bad_u = bad_s = bad_p = 0
    used_k = 0
    st = XB1.Store()
    for k, c in zip(ks, cs):
        k, c = int(k), int(c)
        u0, _ = E.vol_u(CL, k, c)
        CL2 = CL[:, c].copy()
        CL[k + 1:, c] = rng.uniform(1, 1e6, size=CL.shape[0] - k - 1)
        u1, _ = E.vol_u(CL, k, c)
        CL[:, c] = CL2
        if not (u0 == u1 or (np.isnan(u0) and np.isnan(u1))):
            bad_u += 1
        CL3 = CL[:, c].copy()
        CL[k, c] = CL[k, c] * 1.5 if np.isfinite(CL[k, c]) else CL[k, c]
        u2, _ = E.vol_u(CL, k, c)
        CL[:, c] = CL3
        used_k += int(np.isfinite(u0) and u2 != u0)
        for zo in C.STATE_Z:
            cond = E.state_cond(sig, zo)
            h = E.state_hour(cond, k, c)
            if h < E.BIG:
                col = cond[:, c].copy()
                cond[k + h + 1:, c] = rng.random(cond.shape[0] - k - h - 1) < 0.5
                cond[k + 1:k + h, c] = False
                h2 = E.state_hour(cond, k, c)
                cond[:, c] = col
                cond[k + 1:k + h + 1, c] = False                 # trigger row removed -> must exit later (row k+h is used)
                h3 = E.state_hour(cond, k, c)
                cond[:, c] = col
                if h2 != h or not (h3 > h):
                    bad_s += 1
        p, nv, miss_m, gm, fh, lg = XB1.path_of(st, c, k)
        cu = E.Cur(p, nv, miss_m, fh, gm)
        rows = E.candidate_rows(cu, ('BRK', 'PART'))
        for fam, rr in rows.items():
            for xi in (0, len(rr) - 1):
                j = int(rr[xi]['j'])
                if j < nv - 1:
                    q = p.copy()
                    q[j + 1:] = q[j + 1:] * rng.uniform(0.2, 5.0)
                    cu2 = E.Cur(q, nv, miss_m, fh, gm)
                    r2 = E.candidate_rows(cu2, (fam,))[fam][xi]
                    if (r2['j'], r2['rt'], r2['xr']) != (rr[xi]['j'], rr[xi]['rt'], rr[xi]['xr']):
                        bad_p += 1
    rec('d_no_lookahead', bad_u == 0 and bad_s == 0 and bad_p == 0, candidates=n, vol_u_changed_by_future=bad_u,
        vol_u_uses_row_k=used_k, state_future_or_unfinalised=bad_s, exit_changed_by_post_exit_prices=bad_p)


# ---------------------------------------------------------------- (e) ledger, (f) pipeline, (g) determinism  (FAKE data)
def test_e():
    ctx, G = fake_ctx()
    HG = C.load('hedge_t1')
    P = C.b1('port')
    worst = 0.0
    n = 0
    for fam, xi, h, ins in (('BRK', 10, 0.0, None), ('VOL', 5, 0.0, None), ('PART', 3, 0.0, None), ('STATE', 2, 0.0, None),
                            ('BRK', 47, 1.0, 'BTCETH'), ('B1', 170, 0.5, 'BTC'), ('PART', 6, 0.0, None)):
        X = G.xview(ctx, fam, xi)
        for z in C.ZS:
            for K in C.KS:
                cand = ctx.cand[(z, 'NONE')]
                for name, a, b in P.FOLDS:
                    k0, kl = P.S.kidx(P.S.ms(a)), P.S.kidx(P.S.ms(b)) - 1
                    if ins is None:
                        tr, eq, m = P.run(K, cand, X, k0, kl)
                        hp = 0.0
                    else:
                        tr, eq, m = HG.run(K, cand, X, k0, kl, h, ctx.legs[ins])
                        hp = m['hedge_pnl']
                        worst = max(worst, abs(m['hedge_acct_err']))
                    err = abs(float(tr['net'].sum()) + hp - (float(eq['eq'].values[-1]) - 10000.0))
                    worst = max(worst, err, abs(m['acct_err']), abs(m['eq_end_ledger_minus_eq']))
                    n += 1
    rec('e_ledger_equals_equity_change', worst <= 1e-6, runs=n, max_abs_err=worst, data='FAKE paths')


def test_f(nrep=3, nproc=2):
    import tempfile
    import shutil
    ctx, G = fake_ctx()
    SEL = C.load('select_t1')
    RT = C.load('rand_t1')
    REP = C.load('report_t1')
    d = tempfile.mkdtemp(prefix='t1f_', dir=C.WORK)
    try:
        t0 = time.time()
        df = G.run_grid(ctx, C.all_cfgs(), d + '/grid', nproc=nproc)
        tg = time.time() - t0
        sec = df.groupby('fam')['sec'].mean().to_dict()
        rc = RT.build_fake(_FK['F'])
        t0 = time.time()
        rd = RT.run_reps(rc, RT.jobs_for(RT.FAMS, nrep), d + '/rand', nproc=nproc)
        tr_ = time.time() - t0
        rsec = rd.groupby('fam')['sec'].mean().to_dict()
        rres = RT.summarize(rd, df, RT.FAMS)
        rep = REP.build(df, rres, ctx)
        REP.write(rep, d + '/report_t1')
        md = open(d + '/report_t1.md').read()
        keys = sorted(rep['fam'])
        part_real = [c['reasons_real'] for kk, e in rep['fam'].items() if kk.startswith('PART') for c in e['concentration'].values() if c]
        ok = (len(df) == C.n_total() and len(keys) == 10 and all('criteria' in rep['fam'][kk] for kk in keys if kk.endswith('NONE'))
              and len(rd) == nrep * 10 and 'gate hau kiem' in md)
        shutil.copy(d + '/report_t1.md', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fake_report_t1.md'))
        rec('f_pipeline_fake', ok, n_cfg=len(df), grid_sec_total=tg, sec_per_cfg_by_fam=sec, rand_reps=len(rd), rand_sec_total=tr_,
            rand_sec_per_rep_by_fam=rsec, keys=keys, part_real_reasons=part_real, fake_ncand=int(len(_FK['F'].U_k)), nproc=nproc)
    finally:
        shutil.rmtree(d)


def test_g():
    FK = C.load('fake_t1')
    ctx, G = fake_ctx()
    F2 = FK.make()
    same_data = all(np.array_equal(getattr(_FK['F'], a), getattr(F2, a)) for a in ('mm', 'FR', 'U_k', 'U_c'))
    ctx2 = G.build_fake(F2)
    bad = []
    for f in E.FAMS:
        for kk in ('j', 'rt', 'xr', 'fund', 'mxh'):
            if not np.array_equal(ctx.T[f][kk], ctx2.T[f][kk]):
                bad.append((f, kk))
    cf = [c for c in C.all_cfgs() if c['cfg_id'] % 97 == 0]
    for c in cf:
        a = G.run_cfg(ctx, c)
        b = G.run_cfg(ctx2, c)
        if _eq_dict(a, b):
            bad.append(c['cfg_id'])
    RT = C.load('rand_t1')
    rc = RT.build_fake(_FK['F'])
    r1 = RT.one_rep(rc, 'BRK', 'NONE', 0)
    r2 = RT.one_rep(rc, 'BRK', 'NONE', 0)
    r1.pop('sec'); r2.pop('sec')
    if r1 != r2:
        bad.append('rand')
    rec('g_deterministic', same_data and not bad, configs=len(cf), mismatches=str(bad)[:300])


# ---------------------------------------------------------------- (h) 'miss' path (missing run > 24 h): real candidates have none
def test_h():
    """Real B1 exits.npz has 0 'miss' exits (no union candidate's 30-day path meets a > 24 h gap: longgap = 0), so (a) cannot cover it.
    FAKE coin 5 has a 2 000-minute gap; candidates entered 1..700 h before it: T1 (BRK no TP, STATE never, PART) vs B1 exits_core."""
    ctx, G = fake_ctx()
    F = _FK['F']
    st = XB1.Store(mm=F.mm, gaps=F.gaps, FR=F.FR)
    g0 = int(F.gaps[1][0])
    ks = [(g0 // 60) - d for d in (1, 2, 5, 23, 24, 25, 60, 167, 168, 169, 300, 500, 700)]
    bad, nmiss, nmiss_part, ncmp = 0, 0, 0, 0
    for k in ks:
        p, nv, miss_m, gm, fh, lg = XB1.path_of(st, 5, k)
        r1 = XB1.exits_core(p, nv, miss_m, fh, gm)
        cu = E.Cur(p, nv, miss_m, fh, gm)
        for sl in CB.SLS:
            for hh in CB.HS:
                xi = CB.xidx(sl, hh, 0.0, 0.0)
                for r in (E.bracket(cu, sl, None, hh), E.bracket(cu, sl, None, hh, E.BIG)):
                    ncmp += 1
                    nmiss += int(r['rt'] == C.RT_MISS)
                    got = (r['j'], int(C.RT2RS[r['rt']]), r['xr'], r['fund'], r['mx'], r['mxh'], r['flag'])
                    ref = (int(r1['j'][xi]), int(r1['rs'][xi]), float(r1['xr'][xi]), float(r1['fund'][xi]), float(r1['mx'][xi]),
                           float(r1['mxh'][xi]), int(r1['flag'][xi]))
                    bad += int(got != ref)
        for x in C.fam_cfgs('PART'):
            r = E.part(cu, x['s'], x['H'])
            rr = ref_part(p, nv, miss_m if miss_m < nv else -1, fh, x['s'], x['H'])
            nmiss_part += int(r['rt'] == C.RT_MISS)
            bad += int(not (r['j'] == rr[0] and C.RTNAMES[r['rt']] == rr[1] and abs(r['xr'] - rr[2]) <= 1e-12))
    rec('h_miss_path_fake', bad == 0 and nmiss > 0, comparisons=ncmp, miss_exits=nmiss, part_miss_exits=nmiss_part, mismatches=bad,
        note='real B1 exits.npz: 0 miss exits, longgap = 0 on all 8 524 union candidates')


# ---------------------------------------------------------------- (i) report prints REAL T1 reasons (PART tp / be), not mapped port codes
def test_i():
    ctx, G = fake_ctx()
    SEL = C.load('select_t1')
    bad, seen = [], {}
    for xi in range(C.NFAM['PART']):
        cfg = dict(fam='PART', xi=xi, zmin=2.5, K=5, gate='NONE')
        c = SEL.concentration(ctx, cfg, 'DEV')
        tr, eq, m = SEL.rerun(ctx, cfg, 'DEV')
        rt = ctx.T['PART']['rt'][:, xi]
        exp = {}
        for cid, rsn in zip(tr['cid'].values, tr['reason'].values):
            nm = 'eod' if rsn == 'eod' else C.RTNAMES[int(rt[cid])]
            exp[nm] = exp.get(nm, 0) + 1
        if exp != c['reasons_real']:
            bad.append(xi)
        for kk, v in c['reasons_real'].items():
            seen[kk] = seen.get(kk, 0) + v
    rec('i_report_real_reasons_part', not bad and seen.get('be', 0) > 0 and seen.get('tp', 0) > 0, reasons_seen=seen, mismatches=bad,
        data='FAKE paths')


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    parts = sys.argv[1:] or ['a']
    for p in parts:
        t0 = time.time()
        globals()['test_' + p]()
        log.info('test_%s %.1fs', p, time.time() - t0)
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_report_%s.json' % ''.join(parts))
    with open(fn, 'w') as fh:
        json.dump(RES, fh, indent=1, default=str)
    log.info('ALL %s', 'PASS' if all(v['PASS'] for v in RES.values()) else 'FAIL')


if __name__ == '__main__':
    main()
