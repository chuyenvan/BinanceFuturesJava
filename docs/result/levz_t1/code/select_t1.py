"""LEVZ T1 measures (PREREG_LEVZ_T1 sec 4) per family x gate on the T1 grid DataFrame.
(i) share of configs with ret > 0 and median ret in F1 / F2 / F3 / DEV; median maxdd_worst per fold.
(ii) WFO with the B1 rule UNCHANGED (select_b1.rule, dd_mode 'folds'; neighbours = one parameter one step within the family):
     Y = 2024 rule on F1 -> F2; Y = 2025 rule on F1 + F2 -> F3; top-1 = first config passing the FULL rule (valid + maximin + plateau),
     top-20 = 20 best VALID by score (B1 ADD1 B); compared with the family median of the test fold. No valid config -> 'khong cham duoc'.
(iv) concentration on re-runs of one config / fold (concentration()): drop the best 5 % trades (by net), worst trade, trades / year,
     exit reasons by the REAL T1 reason (rt of the T1 exit table; HEDGE B1-reference bases: B1 reason names).
Criteria (sec 5, gate NONE only): see report_t1."""
import os
import sys
import math
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t1 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

CB = C.CB
SB1 = C.b1('select_b1')
FOLDS = ('F1', 'F2', 'F3', 'DEV')
WFO = (('2024', ('F1',), 'F2'), ('2025', ('F1', 'F2'), 'F3'))
BRK_LIST = C.fam_cfgs('BRK')
LADDER = {
    'BRK': dict(zmin=C.ZS, K=C.KS, s=C.BRK_S, R=C.BRK_R, H=C.BRK_H),
    'VOL': dict(zmin=C.ZS, K=C.KS, a=C.VOL_A, R=C.VOL_R, H=C.VOL_H),
    'PART': dict(zmin=C.ZS, K=C.KS, s=C.PART_S, H=C.PART_H),
    'STATE': dict(zmin=C.ZS, K=C.KS, zo=C.STATE_Z, s=C.STATE_SL, H=C.STATE_H),
    'HEDGE': dict(zmin=C.ZS, K=C.KS, inst=C.HEDGE_INST, h=C.HEDGE_H),
}


def pkeys(fam):
    return tuple(LADDER[fam]) + (('base', 'bxi') if fam == 'HEDGE' else ())


def _norm(v):
    return round(float(v), 4) if isinstance(v, (float, np.floating, int, np.integer)) and not isinstance(v, bool) else str(v)


def make_key(fam):
    pk = pkeys(fam)

    def key(d):
        return tuple(_norm(d[p]) for p in pk)
    return key


def make_neigh(fam):
    lad = LADDER[fam]
    pk = pkeys(fam)

    def neigh(cfg):
        out = []
        base = {p: cfg[p] for p in pk}
        for p, vals in lad.items():
            vals = list(vals)
            i = [_norm(v) for v in vals].index(_norm(cfg[p]))
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals):
                    d = dict(base)
                    d[p] = vals[j]
                    out.append(d)
        if fam == 'HEDGE' and cfg['base'] == 'BRK':          # move one BRK parameter of the base exit
            b = BRK_LIST[int(cfg['bxi'])]
            for p, vals in (('s', C.BRK_S), ('R', C.BRK_R), ('H', C.BRK_H)):
                vals = list(vals)
                i = vals.index(b[p])
                for j in (i - 1, i + 1):
                    if 0 <= j < len(vals):
                        nb = dict(b)
                        nb[p] = vals[j]
                        d = dict(base)
                        d['bxi'] = BRK_LIST.index(nb)
                        out.append(d)
        return out
    return neigh


def subset(df, fam, gate):
    d = df[(df['fam'] == fam) & (df['gate'] == gate)].copy()
    return d.reset_index(drop=True)


def describe(d):
    o = {}
    for f in FOLDS:
        r = d['%s_ret' % f]
        o[f] = dict(frac_pos=float((r > 0).mean()), median_ret=float(r.median()),
                    median_maxdd_worst=float(d['%s_maxdd_worst' % f].median()), median_maxdd_close=float(d['%s_maxdd' % f].median()),
                    median_n=float(d['%s_n' % f].median()))
    o['median_n_2024_2025'] = float((d['F2_n'] + d['F3_n']).median())
    return o


def wfo(d, fam):
    out = {}
    for Y, folds, test in WFO:
        R = SB1.rule(d, folds, 'folds', neigh=make_neigh(fam), key=make_key(fam), pkeys=pkeys(fam))
        o = dict(select_folds=list(folds), test_fold=test, n_valid=int(R['d']['valid'].sum()), chosen=R['chosen'],
                 top20_ids=R['valid20'])
        o['top1'] = SB1._oos(d, [R['chosen']] if R['chosen'] is not None else [], test)
        o['top20_valid'] = SB1._oos(d, R['valid20'], test)
        o['top20_rule'] = SB1._oos(d, R['passing20'], test)
        o['family_median_test'] = float(d['%s_ret' % test].median())
        o['reachable'] = bool(R['valid20'])
        if not o['reachable']:
            o['note'] = 'khong cham duoc %s' % Y
        out[Y] = o
    return out


def measures(df):
    res = {}
    for fam in ('BRK', 'VOL', 'PART', 'STATE', 'HEDGE'):
        for g in C.GATES:
            d = subset(df, fam, g)
            if not len(d):
                continue
            res['%s|%s' % (fam, g)] = dict(n_cfg=int(len(d)), describe=describe(d), wfo=wfo(d, fam),
                                           label='gate hau kiem' if g == 'G_EW14' else '')
    return res


# ---------------------------------------------------------------- (iv) concentration (re-run one config / fold)
def rerun(ctx, cfg, fold):
    G = C.load('grid_t1')
    P = C.b1('port')
    HG = C.load('hedge_t1')
    name, a, b = [f for f in P.FOLDS if f[0] == fold][0]
    k0, kl = P.S.kidx(P.S.ms(a)), P.S.kidx(P.S.ms(b)) - 1
    cand = ctx.cand[(float(cfg['zmin']), cfg['gate'])]
    if cfg['fam'] == 'HEDGE':
        X = G.xview(ctx, cfg['base'], int(cfg['bxi']))
        return HG.run(int(cfg['K']), cand, X, k0, kl, float(cfg['h']), ctx.legs[cfg['inst']])
    return P.run(int(cfg['K']), cand, G.xview(ctx, cfg['fam'], int(cfg['xi'])), k0, kl)


def real_reasons(ctx, cfg, tr):
    """REAL T1 exit reason per trade (rt of the exit table); fold-end closes stay 'eod'."""
    if cfg['fam'] == 'HEDGE':
        fam, xi = cfg['base'], int(cfg['bxi'])
    else:
        fam, xi = cfg['fam'], int(cfg['xi'])
    if fam == 'B1':
        return tr['reason'].values
    rt = ctx.T[fam]['rt'][:, xi]
    out = np.array([C.RTNAMES[int(rt[c])] for c in tr['cid'].values], dtype=object)
    out[tr['reason'].values == 'eod'] = 'eod'
    return out


def concentration(ctx, cfg, fold):
    tr, eq, m = rerun(ctx, cfg, fold)
    net = tr['net'].values.astype(float)
    hed = float(m.get('hedge_pnl', 0.0))
    n = len(net)
    n5 = int(math.ceil(0.05 * n)) if n else 0
    srt = np.sort(net)[::-1]
    yrs = (len(eq)) / (24 * 365.25)
    rr = real_reasons(ctx, cfg, tr)
    reasons = {str(r): int((rr == r).sum()) for r in sorted(set(rr.tolist()))}
    return dict(fold=fold, n=n, net_total=float(net.sum()) + hed, hedge_pnl=hed, n_drop_best5=n5,
                net_without_best5=float(srt[n5:].sum()) + hed, best5_net=float(srt[:n5].sum()),
                worst_trade_ret=float(tr['ret'].min()) if n else None, trades_per_year=n / yrs if yrs > 0 else None,
                reasons_real=reasons, ret=float(m['ret']))
