"""LEVZ B4 measures (PREREG_X3_1127 A5) per DCA kind on the B4 grid DataFrame (108 cfgs per kind, NONE = control, same procedure).
- share of cfgs with ret > 0 and median ret per fold F1 / F2 / F3 / DEV ([in-sample] for DEV);
- WFO with select_b1.rule UNCHANGED (dd_mode 'folds'): Y 2024 rule on F1 -> F2; Y 2025 rule on F1 + F2 -> F3; top-1 = first cfg passing
  the FULL rule; top-20 = 20 best VALID by score (as T1 / T2). Neighbours INSIDE the DCA kind: zmin, K, SL, H one step; exit
  TR5_3 <-> TR10_5 (STATE has no exit neighbour; CHOICES_B4);
- top-1 re-run on its test fold: drop the 5 % MOST PROFITABLE trades, worst trade, worst slot loss per budget = min(exits_b4 'worst'
  of the trade, trade ret) (V-e).
usage: python3 code/select_b4.py --real I_HAVE_A1_PASS  -> out/select_b4.json   |   --fake KIND --seed S (grid from out/fake)"""
import json
import math
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_b4 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = C.setup_log('select')
SB1 = C.b1('select_b1')
FOLDS = ('F1', 'F2', 'F3', 'DEV')
WFO = (('2024', ('F1',), 'F2'), ('2025', ('F1', 'F2'), 'F3'))
PKEYS = ('dca', 'zmin', 'K', 's', 'H', 'ex')
LADDER = dict(zmin=C.ZS, K=C.KS, s=C.SLS, H=C.HS)
EXN = {'TR5_3': ['TR10_5'], 'TR10_5': ['TR5_3'], 'STATE': []}


def _n(v):
    return v if isinstance(v, str) else round(float(v), 4)


def key(d):
    return tuple(_n(d[p]) for p in PKEYS)


def neigh(cfg):
    base = {p: cfg[p] for p in PKEYS}
    out = []
    for p, vals in LADDER.items():
        vals = [_n(v) for v in vals]
        i = vals.index(_n(cfg[p]))
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                d = dict(base)
                d[p] = vals[j]
                out.append(d)
    for e in EXN[cfg['ex']]:
        d = dict(base)
        d['ex'] = e
        out.append(d)
    return out


def subset(df, dn):
    return df[df['dca'] == dn].reset_index(drop=True)


def describe(d):
    o = {}
    for f in FOLDS:
        r = d['%s_ret' % f]
        o[f] = dict(frac_pos=float((r > 0).mean()), median_ret=float(r.median()),
                    median_maxdd_worst=float(d['%s_maxdd_worst' % f].median()), median_n=float(d['%s_n' % f].median()))
    return o


def wfo(d):
    out = {}
    for Y, folds, test in WFO:
        R = SB1.rule(d, folds, 'folds', neigh=neigh, key=key, pkeys=PKEYS)
        o = dict(select_folds=list(folds), test_fold=test, n_valid=int(R['d']['valid'].sum()), chosen=R['chosen'],
                 top20_ids=R['valid20'])
        o['top1'] = SB1._oos(d, [R['chosen']] if R['chosen'] is not None else [], test)
        o['top20_valid'] = SB1._oos(d, R['valid20'], test)
        o['top20_rule'] = SB1._oos(d, R['passing20'], test)
        o['kind_median_test'] = float(d['%s_ret' % test].median())
        o['scored'] = bool(R['valid20'])
        out[Y] = o
    return out


def concentration(ctx, cfg, fold):
    P = C.b1('port')
    G = C.load('grid_b4')
    name, a, b = [f for f in P.FOLDS if f[0] == fold][0]
    k0, kl = P.S.kidx(P.S.ms(a)), P.S.kidx(P.S.ms(b)) - 1
    tr, eq, m = P.run(int(cfg['K']), ctx.cand[float(cfg['zmin'])], G.xview(ctx, cfg['xi']), k0, kl)
    net = tr['net'].values.astype(float)
    n = len(net)
    n5 = int(math.ceil(0.05 * n)) if n else 0
    srt = np.sort(net)[::-1]
    w = np.minimum(ctx.T['worst'][tr['cid'].values.astype(np.int64), int(cfg['xi'])], tr['ret'].values) if n else np.zeros(0)
    yrs = len(eq) / (24 * 365.25)
    return dict(fold=fold, n=n, net_total=float(net.sum()), n_drop_best5=n5, net_without_best5=float(srt[n5:].sum()),
                worst_trade_ret=float(tr['ret'].min()) if n else None, worst_slot=float(w.min()) if n else None,
                s=float(cfg['s']), trades_per_year=n / yrs if yrs > 0 else None, ret=float(m['ret']),
                acct_gap=float(m['eq_end_ledger_minus_eq']), acct_err=float(m['acct_err']))


def measures(df, ctx=None):
    res = {}
    for dn in C.DNAMES:
        d = subset(df, dn)
        assert len(d) == C.N_PER_DCA, (dn, len(d))
        w = wfo(d)
        o = dict(n_cfg=int(len(d)), describe=describe(d), wfo=w, conc={})
        if ctx is not None:
            for Y, folds, test in WFO:
                cid = w[Y]['chosen']
                if cid is not None:
                    cfg = d.set_index('cfg_id').loc[cid].to_dict()
                    cfg['cfg_id'] = cid
                    o['conc'][Y] = concentration(ctx, cfg, test)
        res[dn] = o
    return res


def main(argv):
    G = C.load('grid_b4')
    if '--fake' in argv:
        kind, seed = argv[argv.index('--fake') + 1], int(argv[argv.index('--seed') + 1])
        df = pd.read_parquet(C.OUT + '/fake/grid_%s_%d.parquet' % (kind, seed))
        ctx, fn = G.build_fake(kind, seed), C.OUT + '/fake/select_%s_%d.json' % (kind, seed)
    else:
        C.require_real(argv)
        df = pd.read_parquet(C.OUT + '/grid_b4.parquet')
        ctx, fn = G.build_real(C.REAL_KEY), C.OUT + '/select_b4.json'
    assert len(df) == C.N_TOTAL and df['cfg_id'].nunique() == C.N_TOTAL
    res = measures(df, ctx)
    with open(fn + '.tmp', 'w') as fh:
        json.dump(res, fh, indent=1, default=float)
    os.replace(fn + '.tmp', fn)
    log.info('select_b4 done -> %s (CHUA AUDIT)', fn)


if __name__ == '__main__':
    main(sys.argv[1:])
