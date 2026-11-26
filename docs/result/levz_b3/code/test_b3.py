"""LEVZ B3 tests (python3 code/test_b3.py [name ...] or pytest code/test_b3.py). Results -> out/test_report.json.
(a) causality per feature on REAL feature inputs (no labels) + px row-k timing vs 1m closes; (b) pool / exit-table regression vs B1;
(c) purge boundaries (WFO + CV both sides); (d) dot weights; (e) GroupKFold by quarter + CV folds leak-free; (f) full model -> wfo -> cv ->
report on FAKE data (planted signal found, pure noise not found); (g) determinism. Real labels are only compared for equality (b)."""
import os
import sys
import json
import logging
import tempfile
import time
sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('common_b3', os.path.join(_HERE, 'common_b3.py'))
C3 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault('common_b3', C3)
_spec.loader.exec_module(C3)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b3.test')
CAND = C3.b3('cand_b3')
FEAT = C3.b3('feat_b3')
MOD = C3.b3('model_b3')
WFO = C3.b3('wfo_b3')
CV = C3.b3('cv_b3')
REP = C3.b3('report_b3')
LABS = C3.b3('labels_b3')
RES = {}
_RAW = {}


def raw():
    if 'A' not in _RAW:
        _RAW['A'] = FEAT.load_raw()
    return _RAW['A']


# ---------------------------------------------------------------- (a)
def test_a_causal(n=200, seed=7, before=700, after=200):
    A = raw()
    P = dict(np.load(C3.WORK + '/pool_b3.npz'))
    full = pd.read_parquet(C3.WORK + '/feat_b3.parquet')
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(P['k']), n, replace=False)
    bad = {f: 0 for f in FEAT.ALL}
    bad_full = {f: 0 for f in FEAT.ALL}
    for i in pick:
        k, c = int(P['k'][i]), int(P['c'][i])
        a, b = max(0, k - before), min(C3.NH, k + after)
        B = FEAT.slice_raw(A, a, b)
        B2 = dict(B)
        r0 = k - a + 1                         # first row strictly after k
        nr = b - a - r0
        for kk in FEAT.TIME_KEYS:
            v = B[kk].copy()
            if nr > 0:
                perm = rng.permutation(nr)
                v[r0:] = v[r0:][perm]
                if v.dtype == bool:
                    v[r0:] = rng.random(v[r0:].shape) < 0.5
                else:
                    v[r0:] = v[r0:] * rng.uniform(0.5, 1.5, v[r0:].shape) + rng.normal(0, 1, v[r0:].shape)
            B2[kk] = v
        ag = B['AGE'].copy()
        d0 = k // 24 + 1
        ag[d0:] = rng.integers(-1, 2000, ag[d0:].shape)
        B2['AGE'] = ag
        f1 = FEAT.features(B, [k - a], [c]).iloc[0]
        f2 = FEAT.features(B2, [k - a], [c]).iloc[0]
        fr = full.iloc[i]
        assert int(fr['k']) == k and int(fr['c']) == c
        for f in FEAT.ALL:
            x, y = f1[f], f2[f]
            if not ((np.isnan(x) and np.isnan(y)) or x == y):
                bad[f] += 1
            z = fr[f]
            same = (np.isnan(x) and np.isnan(z)) or x == z or (np.isfinite(x) and np.isfinite(z) and abs(x - z) <= 1e-9 * max(1, abs(z)))
            if not same and not (f == 'levrun' and z >= before - 1):
                bad_full[f] += 1
    RES['a_causal'] = dict(n=n, mismatch_after_perturb=bad, mismatch_slice_vs_full=bad_full,
                           pass_=bool(sum(bad.values()) == 0 and sum(bad_full.values()) == 0))
    assert RES['a_causal']['pass_'], RES['a_causal']


def test_a_px_timing(n=500, seed=8):
    """px row k (HI/LO/CL) must be the candle ending at T_k: CL[k] == close of the 1m bar with open T_k - 1 min."""
    A = raw()
    mm = np.load(C3.B1WORK + '/close1m.npy', mmap_mode='r')
    rng = np.random.default_rng(seed)
    fin = np.argwhere(np.isfinite(A['CL'][1:]) & A['HAS'][1:]) + np.array([1, 0])
    pick = fin[rng.choice(len(fin), n, replace=False)]
    eq, eq_next = 0, 0
    for k, c in pick:
        v = float(A['CL'][k, c])
        prev = float(mm[c, 60 * k - 1])
        nxt = float(mm[c, min(60 * k + 59, mm.shape[1] - 1)])
        eq += abs(v - prev) <= 1e-6 * abs(v)
        eq_next += abs(v - nxt) <= 1e-6 * abs(v)
    RES['a_px_timing'] = dict(n=n, match_close_at_Tk=int(eq), match_close_at_Tk_plus_1h=int(eq_next), pass_=bool(eq >= 0.98 * n))
    assert RES['a_px_timing']['pass_'], RES['a_px_timing']


# ---------------------------------------------------------------- (b)
def test_b_regression(n=300, seed=9):
    P = dict(np.load(C3.WORK + '/pool_b3.npz'))
    cz = np.load(C3.B1WORK + '/cand_b1.npz')
    reg = CAND.regress(P['k'], P['c'], P['s'], cz)
    L = np.load(C3.WORK + '/labels_b3.npz')
    T1 = C3.b1('exits').load_table()
    idx = np.flatnonzero(P['b1cid'] >= 0)
    xs = [int(x) for x in L['xs']]
    hc = L['mk'].shape[1]
    eqd = {kk: bool(np.array_equal(T1[kk][P['b1cid'][idx]][:, xs], L[kk][idx])) for kk in LABS.PER}
    eqd.update({kk: bool(np.array_equal(T1[kk][P['b1cid'][idx]][:, :hc], L[kk][idx])) for kk in LABS.HOURLY})
    # fresh recompute of random pool rows (incl. rows NOT in B1) == stored table
    rng = np.random.default_rng(seed)
    pick = np.sort(rng.choice(len(P['k']), n, replace=False))
    st = C3.b1('exits').Store()
    out = LABS.compute_table(st, P['k'][pick], P['c'][pick], xs, hc)
    fresh = {kk: bool(np.array_equal(out[kk], L[kk][pick])) for kk in LABS.PER + LABS.HOURLY}
    # independent: B1 port._net(p) / N for every row and both exits (not label_of)
    Pm = C3.b1('port')
    N = 1000.0
    lab = np.array([[Pm._net([0, 0, 0, N, 0, 0, float(L['xr'][i, j]), float(L['fund'][i, j])]) / N for j in range(L['xr'].shape[1])]
                    for i in range(L['xr'].shape[0])])
    RES['b_regression'] = dict(pool=reg, exits_vs_b1=eqd, n_overlap=int(len(idx)), fresh_recompute=fresh, n_fresh=n,
                               label_vs_port_net=bool(np.allclose(lab, L['label'], rtol=0, atol=1e-12)),
                               pass_=bool(all(v['equal'] for v in reg.values()) and all(eqd.values()) and all(fresh.values())
                                          and np.allclose(lab, L['label'], rtol=0, atol=1e-12)))
    assert RES['b_regression']['pass_'], RES['b_regression']


# ---------------------------------------------------------------- (c)
def test_c_purge():
    ok = []
    for Y, Hx in ((2024, 336), (2025, 24)):
        lim = C3.year_k0(Y) - Hx - 24
        k0 = C3.kidx(C3.ms(C3.TRAIN_START))
        ks = np.array([k0 - 1, k0, lim - 1, lim, lim + 1, C3.year_k0(Y), C3.year_k0(Y) + 5])
        m = CAND.train_mask(ks, Y, Hx)
        ok.append(m.tolist() == [False, True, True, True, False, False, False])
    for (y, q) in ((2023, 0), (2024, 2), (2025, 3)):
        for Hx in (24, 336):
            a, b = CV.q_bounds(y, q)
            ks = np.array([a - Hx - 25, a - Hx - 24, a - 1, a, b, b + 1, b + Hx + 24, b + Hx + 25])
            ks = ks[ks < C3.NH]
            va, tr = CV.cv_masks(ks, y, q, Hx)
            exp_va = [False, False, False, True, True, False, False, False][:len(ks)]
            exp_tr = [True, False, False, False, False, False, False, True][:len(ks)]
            ok.append(va.tolist() == exp_va and tr.tolist() == exp_tr)
    a, b = CV.q_bounds(2024, 0)
    ok.append(a == C3.kidx(C3.ms('2024-01-01')) and b == C3.kidx(C3.ms('2024-04-01')) - 1)
    a, b = CV.q_bounds(2025, 3)
    ok.append(b == C3.NH - 1)
    RES['c_purge'] = dict(checks=ok, pass_=bool(all(ok)))
    assert all(ok), ok


# ---------------------------------------------------------------- (d)
def test_d_dots():
    ck = np.array([0, 10, 33, 57, 0, 200, 100])
    cc = np.array([0, 0, 0, 0, 1, 1, 0])
    dot, size, w = CAND.dots(ck, cc)
    exp_groups = [[0, 1, 2], [3], [4], [5], [6]]
    ok = all(len(set(dot[g])) == 1 for g in exp_groups) and len(set(dot)) == 5
    ok = ok and np.allclose(w[[0, 1, 2]], 1 / 3) and w[3] == 1 and w[6] == 1
    P = dict(np.load(C3.WORK + '/pool_b3.npz'))
    sums = np.bincount(P['dot'], weights=P['w'])
    ok2 = bool(np.allclose(sums, 1.0))
    RES['d_dots'] = dict(synthetic=bool(ok), real_weight_sum_per_dot_is_1=ok2, pass_=bool(ok and ok2))
    assert ok and ok2


# ---------------------------------------------------------------- (e)
def test_e_groupkfold():
    P = dict(np.load(C3.WORK + '/pool_b3.npz'))
    q = C3.quarter_of_k(P['k'])
    res = []
    for Y, Hx in ((2025, 24), (2024, 336)):
        tm = np.flatnonzero(CAND.train_mask(P['k'], Y, Hx))
        for tr, va in MOD.folds(q[tm]):
            res.append(len(set(q[tm][tr]) & set(q[tm][va])) == 0)
    for (y, qq) in CV.quarter_list():
        for Hx in (24, 336):
            va, tr = CV.cv_masks(P['k'], y, qq, Hx)
            a, b = CV.q_bounds(y, qq)
            res.append(not (va & tr).any() and not ((P['k'][tr] >= a - Hx - 24) & (P['k'][tr] <= b + Hx + 24)).any())
    RES['e_groupkfold'] = dict(n_checks=len(res), pass_=bool(all(res)))
    assert all(res)


# ---------------------------------------------------------------- fake data
def fake_ds(planted, seed, n_dots=2600, n_coins=150, hx=24):
    rng = np.random.default_rng(seed)
    k_lo, k_hi = C3.kidx(C3.ms('2022-01-01')), C3.NH - 2
    ks, cs, lat = [], [], []
    for d in range(n_dots):
        k0 = int(rng.integers(k_lo, k_hi - 10))
        c = int(rng.integers(0, n_coins))
        L = int(rng.integers(1, 7))
        z = rng.normal()
        for j in range(L):
            ks.append(k0 + j)
            cs.append(c)
            lat.append(z)
    df = pd.DataFrame(dict(k=ks, c=cs, z=lat)).drop_duplicates(['k', 'c']).sort_values(['k', 'c']).reset_index(drop=True)
    n = len(df)
    D = WFO.DS()
    D.kind = 'fake_planted' if planted else 'fake_noise'
    D.k, D.c = df['k'].values.astype(np.int64), df['c'].values.astype(np.int64)
    D.s = 1.5 + np.abs(rng.normal(0, 1, n))
    D.dot, _, D.w = CAND.dots(D.k, D.c)
    D.year, D.quarter = C3.year_of_k(D.k), C3.quarter_of_k(D.k)
    D.names = list(FEAT.ALL)
    X = rng.normal(0, 1, (n, len(D.names)))
    X[:, 0] = df['z'].values + 0.3 * rng.normal(0, 1, n)
    D.X = pd.DataFrame(X, columns=D.names)
    noise = rng.normal(0, 0.03, n)
    y = (0.03 * df['z'].values if planted else 0.0) + noise
    fee = C3.b1('port').FEE
    xr = (1.0 - fee - y) / (1.0 + fee)
    D.y = np.column_stack([y, y])
    hcol = hx + 1
    h = np.arange(hcol)
    mk = 1.0 + (xr[:, None] - 1.0) * h[None, :] / hx
    D.T = dict(j=np.full((n, 2), 60 * hx, dtype=np.int32), rs=np.full((n, 2), C3.CB.R_TIME, dtype=np.int8),
               xr=np.column_stack([xr, xr]), fund=np.zeros((n, 2)), mx=np.column_stack([np.maximum(1, xr)] * 2),
               mxh=np.column_stack([np.maximum(xr, mk[:, hx - 1])] * 2), flag=np.zeros((n, 2), dtype=np.int8),
               mk=mk, hm=mk.copy(), fh=np.zeros((n, hcol)), fc=np.zeros((n, hcol)))
    D.hs = [hx, hx]
    return D


def test_f_fake_pipeline(nrand=200):
    out = {}
    tmp = tempfile.mkdtemp(prefix='levzb3_')
    try:
        for planted in (True, False):
            D = fake_ds(planted, seed=11)
            pre = os.path.join(tmp, ('pl_' if planted else 'no_'))
            W = WFO.run_all(D, pre + 'wfo_b3', nrand=nrand)
            CVr = CV.run_all(D, pre + 'cv_b3.json')
            v, md = REP.build(pre)
            r25 = W['years']['2025']
            out['planted' if planted else 'noise'] = dict(
                n=int(len(D.k)), Q=W['Q'], rand_p=r25['rand']['p'], ic_m1=r25['describe']['M1']['ic'],
                ic_m2=r25['describe']['M2']['ic'], main_ret=r25['variants']['M1_T20_K5']['ret'], rand_median=r25['rand']['median'],
                C1=CVr['C1'], C1_n_pos=CVr['C1_n_pos'], C2=CVr['C2'], C3=CVr['C3'], verdict=v,
                top_gain=max(r25['describe']['M1']['gain'].items(), key=lambda x: x[1])[0],
                report_has_tags=bool(REP.TCV in md and REP.T24 in md))
    finally:
        for f in sorted(os.listdir(tmp)):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
    p, z = out['planted'], out['noise']
    ok_p = p['ic_m1'] > 0.2 and p['rand_p'] <= 0.05 and p['Q']['Q1'] and p['C1'] and p['top_gain'] == FEAT.ALL[0] and p['report_has_tags']
    ok_n = z['rand_p'] > 0.05 and abs(z['ic_m1']) < 0.1 and not z['C1'] and z['verdict'] != 'B3 DAT MUC YEU (1 nam WFO + CV)'
    out['pass_planted'], out['pass_noise'] = bool(ok_p), bool(ok_n)
    out['pass_'] = bool(ok_p and ok_n)
    RES['f_fake_pipeline'] = out
    assert out['pass_'], out


# ---------------------------------------------------------------- (g)
def test_g_determinism():
    D = fake_ds(True, seed=12, n_dots=1500)
    r1, s1 = WFO.wfo_year(D, 2025, nrand=20, describe=False)
    r2, s2 = WFO.wfo_year(D, 2025, nrand=20, describe=False)
    for r in (r1, r2):
        r.pop('sec')
    a = json.dumps(r1, sort_keys=True, default=float) == json.dumps(r2, sort_keys=True, default=float)
    b = all(np.array_equal(s1[kk], s2[kk], equal_nan=True) for kk in s1)
    o1, _ = CV.cv_oof(D, 1, seeds=(0, 1))
    o2, _ = CV.cv_oof(D, 1, seeds=(0, 1))
    c = np.array_equal(o1, o2, equal_nan=True)
    A = raw()
    P = dict(np.load(C3.WORK + '/pool_b3.npz'))
    sel = np.arange(0, len(P['k']), 97)
    f1 = FEAT.features(A, P['k'][sel], P['c'][sel])
    f2 = FEAT.features(A, P['k'][sel], P['c'][sel])
    d = f1.equals(f2)
    RES['g_determinism'] = dict(wfo_json_equal=bool(a), scores_equal=bool(b), cv_oof_equal=bool(c), features_equal=bool(d),
                                pass_=bool(a and b and c and d))
    assert a and b and c and d


# ---------------------------------------------------------------- (h) unit tests: model / wfo / cv formulas (hand answers)
def _small_fake(seed=21):
    return fake_ds(True, seed=seed, n_dots=700)


def test_h_weights():
    nb, ns = 900, 200
    ck = np.r_[np.arange(nb) + 20000, np.full(ns, 20000)]
    cc = np.r_[np.zeros(nb, dtype=np.int64), np.arange(1, ns + 1)]
    dot, size, w = CAND.dots(ck, cc)
    okw = np.allclose(w[:nb], 1.0 / nb) and np.allclose(w[nb:], 1.0)
    X = np.zeros((nb + ns, 3))
    y = np.r_[np.ones(nb), -np.ones(ns)]
    wm = (1.0 - ns) / (1.0 + ns)                     # weighted mean -0.990; unweighted would be +0.636
    p1 = float(MOD.fit_m1(X, y, w, 0).predict(X[:1])[0])
    p2 = float(MOD.RankRidge().fit(X, y, w).predict(X[:1])[0])
    ok_fit = abs(p1 - wm) < 0.02 and abs(p2 - wm) < 0.02
    # wiring WFO: weights + groups passed to train_predict == 1 / dot size and calendar quarter (independent)
    D = _small_fake()
    cap = []
    orig = MOD.train_predict

    def spy(kind, Xtr, ytr, wtr, gtr, Xte, seeds=MOD.SEEDS):
        R = orig(kind, Xtr, ytr, wtr, gtr, Xte, seeds)
        cap.append(dict(kind=kind, w=np.array(wtr), g=np.array(gtr), n=len(ytr), nte=len(Xte), R=R))
        return R
    MOD.train_predict = spy
    try:
        res, _ = WFO.wfo_year(D, 2025, nrand=3, describe=False)
    finally:
        MOD.train_predict = orig
    lim = C3.year_k0(2025) - D.hs[1] - 24
    itr = np.flatnonzero((D.k >= C3.kidx(C3.ms('2022-01-01'))) & (D.k <= lim))
    size_ind = pd.Series(D.dot).map(pd.Series(D.dot).value_counts()).values
    t = pd.to_datetime(C3.H0 + D.k * C3.H, unit='ms')
    qind = (t.year * 10 + (t.month - 1) // 3).values
    ok_wire = all(np.allclose(c['w'], 1.0 / size_ind[itr]) and c['n'] == len(itr) for c in cap)
    ok_grp = all(len(set(zip(c['g'].tolist(), qind[itr].tolist()))) == len(set(qind[itr].tolist())) == len(set(c['g'].tolist()))
                 for c in cap)
    # same for CV fit_m1
    capw = []
    origf = MOD.fit_m1

    def spyf(X_, y_, w_, seed):
        capw.append(np.array(w_))
        return origf(X_, y_, w_, seed)
    MOD.fit_m1 = spyf
    try:
        CV.cv_oof(D, 1, seeds=(0,))
    finally:
        MOD.fit_m1 = origf
    exp = []
    for (yy, q) in CV.quarter_list():
        a, b = CV.q_bounds(yy, q)
        va = (D.k >= a) & (D.k <= b)
        if not va.any():
            continue
        tr = (D.k >= C3.kidx(C3.ms('2022-01-01'))) & ~va & ~((D.k >= a - 48) & (D.k <= b + 48))
        exp.append(1.0 / size_ind[tr])
    ok_cv = len(exp) == len(capw) and all(np.allclose(a_, b_) for a_, b_ in zip(capw, exp))
    RES['h_weights'] = dict(w_formula=bool(okw), pred_m1=p1, pred_m2=p2, weighted_mean=wm, fit_uses_w=bool(ok_fit),
                            wfo_passes_w=bool(ok_wire), wfo_groups_quarter=bool(ok_grp), cv_passes_w=bool(ok_cv),
                            pass_=bool(okw and ok_fit and ok_wire and ok_grp and ok_cv))
    RES['_h_cap'] = (D, res, cap)
    assert RES['h_weights']['pass_'], RES['h_weights']


def test_i_wfo_formulas():
    a = MOD.thresholds(np.arange(1, 101, dtype=float))
    ok_thr = a == dict(T20=80.2, T10=90.1, T0=0.0) or (abs(a['T20'] - 80.2) < 1e-9 and abs(a['T10'] - 90.1) < 1e-9 and a['T0'] == 0.0)
    ok_sel = (MOD.select(np.array([0.0, 1e-9, -1.0]), 'T0', 0.0).tolist() == [False, True, False]
              and MOD.select(np.array([80.2, 80.1]), 'T20', 80.2).tolist() == [True, False])
    ok_bls = abs(WFO.bl_s20_thr(np.arange(1, 101, dtype=float)) - 80.2) < 1e-9
    ok_blz = WFO.bl_z30_mask(np.array([2.5, 2.99, 3.0, 3.5])).tolist() == [False, False, True, True]
    ok_pk = abs(WFO.rand_p_keep(12, 40) - 0.3) < 1e-12
    ok_pv = WFO.rand_pvalue([0.1, 0.2, 0.3, 0.4], 0.3) == 0.5 and WFO.rand_pvalue([0.1, 0.2], 0.3) == 0.0
    n5, wo = WFO.drop_top5([5.0, -3.0, 10.0, 2.0, -1.0] + [0.0] * 16)
    ok_q5 = (n5, wo) == (2, -2.0)
    # wiring on a fake run (from test_h if available)
    if '_h_cap' not in RES:
        test_h_weights()
    D, res, cap = RES['_h_cap']
    itr, ite = WFO.split_masks(D, 2025)
    k0, kl = C3.year_k0(2025), C3.year_k0(2026) - 1
    ite_ind = np.flatnonzero((D.k >= k0) & (D.k < kl))
    itr_ind = np.flatnonzero((D.k >= C3.kidx(C3.ms('2022-01-01'))) & (D.k <= k0 - D.hs[1] - 24))
    ok_split = np.array_equal(ite, ite_ind) and np.array_equal(itr, itr_ind) and len(np.intersect1d(itr, ite)) == 0
    R1 = [c['R'] for c in cap if c['kind'] == 'M1'][0]
    th = res['thresholds']['M1']
    ok_wthr = abs(th['T20'] - np.quantile(R1['oof'], 0.8)) < 1e-12 and abs(th['T10'] - np.quantile(R1['oof'], 0.9)) < 1e-12
    ok_wsel = res['variants']['M1_T20_K5']['n_selected'] == int((R1['te'] >= np.quantile(R1['oof'], 0.8)).sum())
    ok_wsel = ok_wsel and res['variants']['M1_T0_K5']['n_selected'] == int((R1['te'] > 0).sum())
    ok_wbl = (abs(res['baselines']['BL_S20']['thr'] - np.quantile(D.s[itr_ind], 0.8)) < 1e-12
              and res['baselines']['BL_S20']['n_selected'] == int((D.s[ite_ind] >= np.quantile(D.s[itr_ind], 0.8)).sum())
              and res['baselines']['BL_Z30']['n_selected'] == int((D.s[ite_ind] >= 3.0).sum()))
    ok_wpk = abs(res['rand']['p_keep'] - res['variants']['M1_T20_K5']['n_selected'] / len(ite_ind)) < 1e-12
    ok_wpv = abs(res['rand']['p'] - float(np.mean(np.array(res['rand']['rets']) >= res['variants']['M1_T20_K5']['ret']))) < 1e-12
    # Q5 wiring: rebuild MAIN ledger and drop the ceil(5 %) LARGEST net independently
    led = []
    D2 = D
    res2, _ = WFO.wfo_year(D2, 2025, nrand=0, ledger=led, describe=False)
    tr = pd.concat(led)
    tr = tr[tr['variant'] == 'M1_T20_K5']
    net = np.sort(tr['net'].values)
    n5i = int(np.ceil(len(net) * 5 / 100))
    ok_wq5 = res2['main_trades']['n_top5'] == n5i and abs(res2['main_trades']['net_without_top5'] - net[:len(net) - n5i].sum()) < 1e-6
    d = dict(thresholds=ok_thr, select=ok_sel, bl_s20=ok_bls, bl_z30=ok_blz, p_keep=ok_pk, pvalue=ok_pv, q5=ok_q5, split=ok_split,
             wire_thr=ok_wthr, wire_select=ok_wsel, wire_bl=ok_wbl, wire_p_keep=ok_wpk, wire_pvalue=ok_wpv, wire_q5=ok_wq5)
    d = {k_: bool(v) for k_, v in d.items()}
    RES['i_wfo_formulas'] = dict(d, pass_=bool(all(d.values())))
    assert all(d.values()), d


def test_j_cv_formulas():
    ks = np.concatenate([C3.year_k0(y) + 100 + np.arange(10) for y in (2023, 2024, 2025)] + [np.array([C3.year_k0(2026) - 1])])
    v = np.r_[np.arange(1, 31, dtype=float), 1000.0]
    ok_thr = abs(CV.span_thr(v, ks) - 24.2) < 1e-9                      # one threshold over 2023-2025 (kl hour excluded)
    ok_c1 = CV.c1_count([dict(ic=0.1), dict(ic=-0.1), dict(ic=0.0), dict(ic=None), dict(ic=0.2)]) == 2
    base = dict(pnl={2023: 1.0, 2024: 1.0, 2025: 1.0}, ret=0.3, BL_S20=dict(ret=0.1))
    ok_c2 = CV.c2_pass(base)
    for y in (2023, 2024, 2025):
        b = json.loads(json.dumps(base))
        b['pnl'] = {int(k_): x for k_, x in b['pnl'].items()}
        b['pnl'][y] = -0.01
        ok_c2 = ok_c2 and not CV.c2_pass(b)
    b = dict(base, BL_S20=dict(ret=0.3))
    ok_c2 = ok_c2 and not CV.c2_pass(b)
    ok_c3 = CV.c3_pass(dict(ret=0.01)) and not CV.c3_pass(dict(ret=0.0))
    d = dict(span_threshold=bool(ok_thr), c1_count=bool(ok_c1), c2=bool(ok_c2), c3=bool(ok_c3))
    RES['j_cv_formulas'] = dict(d, pass_=bool(all(d.values())))
    assert all(d.values()), d


ALLT = dict(a_causal=test_a_causal, a_px_timing=test_a_px_timing, b_regression=test_b_regression, c_purge=test_c_purge,
            d_dots=test_d_dots, e_groupkfold=test_e_groupkfold, f_fake_pipeline=test_f_fake_pipeline, g_determinism=test_g_determinism,
            h_weights=test_h_weights, i_wfo_formulas=test_i_wfo_formulas, j_cv_formulas=test_j_cv_formulas)


def main(names):
    path = C3.OUT + '/test_report.json'
    rep = json.load(open(path)) if os.path.exists(path) else {}
    for nm in names:
        t0 = time.time()
        try:
            ALLT[nm]()
            st = 'PASS'
        except AssertionError as e:
            st = 'FAIL'
            log.error('%s FAIL %s', nm, str(e)[:2000])
        rep[nm] = dict(status=st, sec=time.time() - t0, detail=RES.get(nm))
        RES.pop('_h_cap', None) if nm == 'i_wfo_formulas' else None
        log.info('%s %s %.1fs', nm, st, time.time() - t0)
        with open(path, 'w') as fh:
            json.dump(rep, fh, indent=1, default=float)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    main(sys.argv[1:] or list(ALLT))
