"""LEVZ B3 step 6 - WFO scoring (PREREG_LEVZ_B3 sec 5-7 + ERRATA1 E1/E2-A).
Y = 2025 OFFICIAL (train 2022-01-01 .. purge, exit_2025); Y = 2024 DESCRIPTIVE ONLY ("DUOI NGUONG MAU - CHI MO TA", C0 failed,
exit_2024); Y = 2023 not done (ERRATA1). Per Y: M1 (10 seeds) and M2; 9 variants (T20/T10/T0 x K 3/5/10) each; 10 single-seed M1 models
(T20, K5, own OOF threshold); BL_S20 (s >= 80th pct of s on the train set, rank by s); BL_Z30 (s >= 3.0 = B1 W7_E0_3.0, rank by s);
RAND 500 (keep prob = n selected by CHINH / n pool in Y, random order). Portfolio = B1 port.run UNCHANGED (score goes where B1 had s),
fold Y-01-01 .. (Y+1)-01-01 - 1 h, fresh 10 000 equity (B1 fold convention). Data: DS object (real loader guarded; fake in test_b3).
usage: python3 code/wfo_b3.py --real I_HAVE_A1_PASS   (DEV must NOT run this on real data)"""
import os
import sys
import json
import logging
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

log = logging.getLogger('levz_b3.wfo')
MOD = C3.b3('model_b3')
CAND = C3.b3('cand_b3')
P = C3.b1('port')
NRAND = 500
RAND_SEED = 20261126
NBOOT = 1000
THR = ('T20', 'T10', 'T0')
KS = (3, 5, 10)
MAIN = ('M1', 'T20', 5)
OFFICIAL = {2025: True, 2024: False}
YEAR_EXIT = {2024: 0, 2025: 1}       # local exit column in DS.T / DS.y


class DS:
    """k, c, s, dot, w, year, quarter (n,), X (DataFrame n x F), y (n x 2: label by exit_2024, exit_2025), T (exit table, 2 local
    exit columns, cid = row), hs (H of local exits), names, kind ('real' / 'fake')."""
    pass


def load_real(token):
    assert token == 'I_HAVE_A1_PASS', 'real-data run is only allowed after A1 PASS'
    Pz = dict(np.load(C3.WORK + '/pool_b3.npz'))
    L = dict(np.load(C3.WORK + '/labels_b3.npz'))
    Fd = pd.read_parquet(C3.WORK + '/feat_b3.parquet')
    F = C3.b3('feat_b3')
    assert (Fd['k'].values == Pz['k']).all() and (Fd['c'].values == Pz['c']).all()
    assert (L['k'] == Pz['k']).all() and (L['c'] == Pz['c']).all()
    D = DS()
    D.kind = 'real'
    D.k, D.c, D.s, D.dot, D.w = Pz['k'], Pz['c'], Pz['s'], Pz['dot'], Pz['w']
    D.year, D.quarter = C3.year_of_k(D.k), C3.quarter_of_k(D.k)
    D.names = list(F.ALL)
    D.X = Fd[D.names].reset_index(drop=True)
    D.y = L['label']
    D.hs = [int(h) for h in L['hs']]
    D.T = {kk: L[kk] for kk in ('j', 'rs', 'xr', 'fund', 'mx', 'mxh', 'flag', 'mk', 'hm', 'fh', 'fc')}
    return D


def fold_k(Y):
    return C3.year_k0(Y), C3.year_k0(Y + 1) - 1


def run_port(D, xl, K, idx, score, Y):
    k0, kl = fold_k(Y)
    idx = np.asarray(idx, dtype=np.int64)
    cand = P.CandB1(D.k[idx], D.c[idx], np.asarray(score, dtype=np.float64)[idx], idx)
    tr, eq, m = P.run(int(K), cand, P.XView(D.T, xl), k0, kl)
    return tr, eq, m


def _sum(m):
    return dict(ret=float(m['ret']), n=int(m['n']), maxdd_worst=float(m['maxdd_worst']), maxdd=float(m['maxdd']),
                eq_end=float(m['eq_end']), acct_err=float(m['acct_err']))


BLZ = 3.0


def split_masks(D, Y):
    """(train idx, test idx) of year Y: train = cand_b3.train_mask (2022-01-01 .. k0(Y) - H - 24), test = entries in [k0(Y), kl)."""
    Hx = D.hs[YEAR_EXIT[Y]]
    tm = CAND.train_mask(D.k, Y, Hx)
    k0, kl = fold_k(Y)
    te = (D.k >= k0) & (D.k < kl)
    assert not (tm & te).any()
    return np.flatnonzero(tm), np.flatnonzero(te)


def bl_s20_thr(s_train):
    return float(np.quantile(s_train, 0.80))


def bl_z30_mask(s):
    return np.asarray(s) >= BLZ


def rand_p_keep(n_sel_main, n_test):
    """prereg sec 7: (n candidates over the MAIN threshold in Y) / (n pool candidates in Y)."""
    return n_sel_main / max(n_test, 1)


def rand_pvalue(rr, main_ret):
    return float((np.asarray(rr, dtype=np.float64) >= main_ret).mean())


def drop_top5(net):
    """P5 / Q5: remove the ceil(5 %) trades with the LARGEST net; returns (n removed, net total of the rest)."""
    net = np.asarray(net, dtype=np.float64)
    n5 = int(np.ceil(0.05 * len(net)))
    return n5, float(net.sum() - np.sort(net)[::-1][:n5].sum()) if len(net) else 0.0


def oof_fold_sizes(groups):
    groups = np.asarray(groups)
    out = []
    for tr, va in MOD.folds(groups):
        out.append(dict(n_val=int(len(va)), quarters_val=[int(q) for q in np.unique(groups[va])]))
    return out


def c0_of(D, Y, Hx):
    tm = CAND.train_mask(D.k, Y, Hx)
    last = tm & (D.year == Y - 1)
    nd, nl = len(np.unique(D.dot[tm])), len(np.unique(D.dot[last]))
    return dict(n_train_dots=int(nd), n_lastyear_dots=int(nl), C0=bool(nd >= C3.C0_TOTAL and nl >= C3.C0_LAST))


def boot_ic(score, y, w, dot, seed, nb=NBOOT):
    ud, inv = np.unique(dot, return_inverse=True)
    rng = np.random.default_rng(seed)
    out = []
    members = [np.flatnonzero(inv == i) for i in range(len(ud))]
    for _ in range(nb):
        pick = rng.integers(0, len(ud), len(ud))
        ii = np.concatenate([members[p] for p in pick])
        out.append(MOD.wspearman(score[ii], y[ii], w[ii]))
    out = np.array(out)
    return [float(np.nanquantile(out, 0.025)), float(np.nanquantile(out, 0.975))]


def deciles(score, y, w):
    q = pd.qcut(pd.Series(score).rank(method='first'), 10, labels=False)
    df = pd.DataFrame(dict(q=q, y=y, w=w))
    g = df.groupby('q')
    return [dict(decile=int(i), n=int(len(x)), mean_label=float(x['y'].mean()), wmean_label=float(np.average(x['y'], weights=x['w'])))
            for i, x in g]


def perm_importance(R, X, y, w, names, seed):
    base = MOD.wspearman(MOD.predict(R, X), y, w)
    rng = np.random.default_rng(seed)
    X = np.asarray(X, dtype=np.float64)
    out = {}
    for j, n in enumerate(names):
        Xp = X.copy()
        Xp[:, j] = Xp[rng.permutation(len(Xp)), j]
        out[n] = float(base - MOD.wspearman(MOD.predict(R, Xp), y, w))
    return dict(base_ic=float(base), drop=out)


def wfo_year(D, Y, nrand=NRAND, ledger=None, describe=True):
    xl = YEAR_EXIT[Y]
    Hx = D.hs[xl]
    t0 = time.time()
    itr, ite = split_masks(D, Y)
    tm = np.zeros(len(D.k), dtype=bool)
    tm[itr] = True
    y = D.y[:, xl]
    X = D.X.values
    res = dict(Y=Y, official=OFFICIAL[Y], label='WFO %d' % Y + ('' if OFFICIAL[Y] else ' - DUOI NGUONG MAU - CHI MO TA'),
               exit_local=xl, H_exit=Hx, n_train=int(len(itr)), n_test=int(len(ite)), C0=c0_of(D, Y, Hx),
               purge_last_k=int(C3.year_k0(Y) - Hx - 24))
    assert not tm[ite].any() and (D.k[itr] <= C3.year_k0(Y) - Hx - 24).all()
    res['oof_folds'] = oof_fold_sizes(D.quarter[itr])
    R = {}
    for kind in ('M1', 'M2'):
        R[kind] = MOD.train_predict(kind, X[itr], y[itr], D.w[itr], D.quarter[itr], X[ite])
    res['thresholds'] = {kind: MOD.thresholds(R[kind]['oof']) for kind in R}
    score_full = {}
    var = {}
    for kind in ('M1', 'M2'):
        sc = np.full(len(D.k), np.nan)
        sc[ite] = R[kind]['te']
        score_full[kind] = sc
        for tn in THR:
            sel = ite[MOD.select(sc[ite], tn, res['thresholds'][kind][tn])]
            for K in KS:
                name = '%s_%s_K%d' % (kind, tn, K)
                tr, eq, m = run_port(D, xl, K, sel, sc, Y)
                var[name] = _sum(m)
                var[name]['n_selected'] = int(len(sel))
                if ledger is not None:
                    tr = tr.assign(variant=name, Y=Y)
                    ledger.append(tr)
                if (kind, tn, K) == MAIN:
                    main_tr, main_eq = tr, eq
    res['variants'] = var
    main = '%s_%s_K%d' % MAIN
    n_sel_main = var[main]['n_selected']
    ss = {}
    for i, sd in enumerate(R['M1']['seeds']):
        thr = MOD.thresholds(R['M1']['oof_s'][i])['T20']
        sc = np.full(len(D.k), np.nan)
        sc[ite] = R['M1']['te_s'][i]
        sel = ite[sc[ite] >= thr]
        tr, eq, m = run_port(D, xl, 5, sel, sc, Y)
        ss['seed%d' % sd] = dict(_sum(m), thr=thr, n_selected=int(len(sel)))
    res['single_seed'] = ss
    bl = {}
    thr_s = bl_s20_thr(D.s[itr])
    sel = ite[D.s[ite] >= thr_s]
    tr, eq, m = run_port(D, xl, 5, sel, D.s, Y)
    bl['BL_S20'] = dict(_sum(m), thr=thr_s, n_selected=int(len(sel)))
    sel = ite[bl_z30_mask(D.s[ite])]
    tr, eq, m = run_port(D, xl, 5, sel, D.s, Y)
    bl['BL_Z30'] = dict(_sum(m), n_selected=int(len(sel)))
    res['baselines'] = bl
    p_keep = rand_p_keep(n_sel_main, len(ite))
    rr = []
    for r in range(nrand):
        rng = np.random.default_rng([RAND_SEED, Y, r])
        keep = rng.random(len(ite)) < p_keep
        sc = np.full(len(D.k), np.nan)
        sc[ite] = rng.random(len(ite))
        tr, eq, m = run_port(D, xl, 5, ite[keep], sc, Y)
        rr.append(float(m['ret']))
    rr = np.array(rr)
    res['rand'] = dict(n=nrand, p_keep=float(p_keep), rets=[float(x) for x in rr],
                       p=rand_pvalue(rr, var[main]['ret']) if nrand else None, median=float(np.median(rr)) if nrand else None)
    # P5 / Q5 on the MAIN ledger
    net = main_tr['net'].values
    n5, wo = drop_top5(net)
    res['main_trades'] = dict(n=int(len(net)), net_total=float(net.sum()), n_top5=n5, net_without_top5=wo)
    if describe:
        yte, wte = y[ite], D.w[ite]
        d = {}
        for kind in ('M1', 'M2'):
            s_ = R[kind]['te']
            d[kind] = dict(ic=MOD.wspearman(s_, yte, wte), ic_ci95=boot_ic(s_, yte, wte, D.dot[ite], RAND_SEED + Y),
                           deciles=deciles(s_, yte, wte) if len(ite) >= 10 else None,
                           ic_insample_train=MOD.wspearman(MOD.predict(R[kind], X[itr]), y[itr], D.w[itr]),
                           ic_oof_train=MOD.wspearman(R[kind]['oof'], y[itr], D.w[itr]),
                           gain=MOD.gain_importance(R[kind], D.names))
        d['M1']['perm_test'] = perm_importance(R['M1'], X[ite], yte, wte, D.names, RAND_SEED)
        d['BL_s_ic'] = MOD.wspearman(D.s[ite], yte, wte)
        mt = main_tr.copy()
        mt['month'] = pd.to_datetime(C3.H0 + mt['ke'].values * C3.H, unit='ms').strftime('%Y-%m')
        d['main_by_month'] = {k_: float(v) for k_, v in mt.groupby('month')['net'].sum().items()}
        wst = mt.sort_values('net').head(10)
        d['main_worst10'] = wst[['c', 'ke', 'kx', 'reason', 'net', 'ret']].to_dict('records')
        vc = mt['c'].value_counts()
        d['neighbours_M1'] = {n_: var[n_] for n_ in var if n_.startswith('M1_') and n_ != main}
        d['main_same_coin'] = dict(n_coins=int(len(vc)), max_trades_one_coin=int(vc.max()) if len(vc) else 0,
                                   n_coins_ge2=int((vc >= 2).sum()))
        res['describe'] = d
    res['sec'] = time.time() - t0
    return res, score_full


def criteria_Q(r):
    """ERRATA1 E2 (A) on WFO 2025 result dict."""
    main = '%s_%s_K%d' % MAIN
    v = r['variants'][main]
    nb = [n for n in r['variants'] if n.startswith('M1_') and n != main]
    assert len(nb) == 8
    q = {}
    q['Q1'] = v['ret'] > 0
    q['Q2'] = v['ret'] > r['baselines']['BL_S20']['ret'] and v['ret'] > r['baselines']['BL_Z30']['ret']
    q['Q3'] = r['rand']['p'] is not None and r['rand']['p'] <= 0.05
    q['Q4'] = v['n'] >= 30
    q['Q5'] = r['main_trades']['net_without_top5'] > 0
    q['Q6'] = sum(x['ret'] > 0 for x in r['single_seed'].values()) >= 8
    q['Q7'] = v['maxdd_worst'] <= 0.25
    q['Q8'] = sum(r['variants'][n]['ret'] > 0 for n in nb) >= 5
    return {k_: bool(x) for k_, x in q.items()}


def run_all(D, out_prefix, nrand=NRAND, years=(2025, 2024)):
    ledger = []
    rep = dict(kind=D.kind, n_pool=int(len(D.k)), years={})
    for Y in years:
        r, _ = wfo_year(D, Y, nrand=nrand, ledger=ledger)
        rep['years'][str(Y)] = r
    if '2025' in rep['years']:
        rep['Q'] = criteria_Q(rep['years']['2025'])
    led = pd.concat(ledger, ignore_index=True) if ledger else pd.DataFrame()
    led.to_parquet(out_prefix + '_ledger.parquet', index=False)
    with open(out_prefix + '.json', 'w') as fh:
        json.dump(rep, fh, indent=1, default=float)
    return rep


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    assert len(sys.argv) == 3 and sys.argv[1] == '--real', __doc__
    D = load_real(sys.argv[2])
    run_all(D, C3.OUT + '/wfo_b3')
