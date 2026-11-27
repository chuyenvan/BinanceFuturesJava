"""LEVZ T2 measures (PREREG_LEVZ_T2 sec 4 (ii)(iii)(v)) per entry type on the T2 grid DataFrame.
(ii) share of configs with ret > 0 and median ret per fold F1 / F2 / F3 / DEV ([in-sample] label for DEV in the report).
(iii) WFO with select_b1.rule UNCHANGED (dd_mode 'folds'): Y = 2024 rule on F1 -> F2; Y = 2025 rule on F1 + F2 -> F3; top-1 = first
     config passing the FULL rule; top-20 = 20 best VALID by score (B1 ADD1 B). Neighbours (plateau) = one parameter one step INSIDE
     the exit family, as T1: zmin, K for all; B1 exits: SL, H, trailing exactly as select_b1.neighbours (W / E fixed in T2);
     PART: s, H; STATE: zo, s, H. Compared with the entry type's median of the test fold. No valid config -> year not scored.
(v) concentration (re-run of the top-1 config on its test fold): drop the best 5 % trades, worst trade, trades / year.
wfo_stat(): placebo statistic = top-20 median 2024 + 2025 over the scored years (ADD1 M3).
usage: python3 code/select_t2.py --real I_HAVE_A1_PASS   -> out/select_t2.json"""
import json
import math
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = C.setup_log('select')
CB = C.CB
C1 = C.C1
SB1 = C.b1('select_b1')
FOLDS = ('F1', 'F2', 'F3', 'DEV')
WFO = (('2024', ('F1',), 'F2'), ('2025', ('F1', 'F2'), 'F3'))
PKEYS = ('xfam', 'zmin', 'K', 'SL', 'H', 'arm', 'gap', 's', 'zo')
LADDER = {'B1': dict(zmin=C.ZS, K=C.KS, SL=CB.SLS, H=CB.HS),
          'PART': dict(zmin=C.ZS, K=C.KS, s=C1.PART_S, H=C1.PART_H),
          'STATE': dict(zmin=C.ZS, K=C.KS, zo=C1.STATE_Z, s=C1.STATE_SL, H=C1.STATE_H)}


def _n(v):
    if isinstance(v, str):
        return v
    v = float(v)
    return 'na' if not np.isfinite(v) else round(v, 4)


def key(d):
    return tuple(_n(d[p]) for p in PKEYS)


def neigh(cfg):
    fam = cfg['xfam']
    base = {p: cfg[p] for p in PKEYS}
    out = []
    for p, vals in LADDER[fam].items():
        vals = list(vals)
        i = [_n(v) for v in vals].index(_n(cfg[p]))
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                d = dict(base)
                d[p] = vals[j]
                out.append(d)
    if fam == 'B1':                                    # trailing neighbours: select_b1 logic, W / E fixed
        a, g = float(cfg['arm']), float(cfg['gap'])
        if a == 0.0:
            for gg in CB.GAPS:
                d = dict(base)
                d['arm'], d['gap'] = 0.10, gg
                out.append(d)
        else:
            i = SB1.ARM_ORDER.index(a)
            for j in (i - 1, i + 1):
                if 0 <= j < len(SB1.ARM_ORDER):
                    d = dict(base)
                    if SB1.ARM_ORDER[j] == 'off':
                        d['arm'], d['gap'] = 0.0, 0.0
                    else:
                        d['arm'] = SB1.ARM_ORDER[j]
                    out.append(d)
            gi = CB.GAPS.index(g)
            for j in (gi - 1, gi + 1):
                if 0 <= j < len(CB.GAPS):
                    d = dict(base)
                    d['gap'] = CB.GAPS[j]
                    out.append(d)
    return out


def subset(df, e):
    return df[df['entry'] == e].reset_index(drop=True)


def describe(d):
    o = {}
    for f in FOLDS:
        r = d['%s_ret' % f]
        o[f] = dict(frac_pos=float((r > 0).mean()), median_ret=float(r.median()),
                    median_maxdd_worst=float(d['%s_maxdd_worst' % f].median()), median_n=float(d['%s_n' % f].median()))
    o['median_n_2024_2025'] = float((d['F2_n'] + d['F3_n']).median())
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
        o['entry_median_test'] = float(d['%s_ret' % test].median())
        o['scored'] = bool(R['valid20'])
        out[Y] = o
    return out


def wfo_stat(w):
    """placebo statistic: sum over scored years of the top-20 median; scored years listed."""
    yrs = [Y for Y in ('2024', '2025') if w[Y]['scored']]
    s = float(sum(w[Y]['top20_valid']['median_ret'] for Y in yrs)) if yrs else float('nan')
    return dict(wfo_sum=s, scored_years=yrs, top20_2024=w['2024']['top20_valid'].get('median_ret', np.nan),
                top20_2025=w['2025']['top20_valid'].get('median_ret', np.nan))


def rerun(ctx, cfg, fold):
    P = C.b1('port')
    G = C.load('grid_t2')
    name, a, b = [f for f in P.FOLDS if f[0] == fold][0]
    k0, kl = P.S.kidx(P.S.ms(a)), P.S.kidx(P.S.ms(b)) - 1
    return P.run(int(cfg['K']), ctx.cand[(cfg['entry'], float(cfg['zmin']))], G.xview(ctx, cfg['entry'], cfg['xfam'], cfg['xi']),
                 k0, kl)


def concentration(ctx, cfg, fold):
    tr, eq, m = rerun(ctx, cfg, fold)
    net = tr['net'].values.astype(float)
    n = len(net)
    n5 = int(math.ceil(0.05 * n)) if n else 0
    srt = np.sort(net)[::-1]
    yrs = len(eq) / (24 * 365.25)
    return dict(fold=fold, n=n, net_total=float(net.sum()), n_drop_best5=n5, net_without_best5=float(srt[n5:].sum()),
                best5_net=float(srt[:n5].sum()), worst_trade_ret=float(tr['ret'].min()) if n else None,
                trades_per_year=n / yrs if yrs > 0 else None, ret=float(m['ret']),
                acct_gap=float(m['eq_end_ledger_minus_eq']))


def measures(df, ctx=None, entries=C.ENTRIES):
    res = {}
    for e in entries:
        d = subset(df, e)
        assert len(d) == C.N_PER_ENTRY, (e, len(d))
        w = wfo(d)
        o = dict(n_cfg=int(len(d)), describe=describe(d), wfo=w, stat=wfo_stat(w))
        if ctx is not None:
            o['conc'] = {}
            for Y, folds, test in WFO:
                cid = w[Y]['chosen']
                if cid is not None:
                    cfg = d.set_index('cfg_id').loc[cid].to_dict()
                    cfg['cfg_id'] = cid
                    o['conc'][Y] = concentration(ctx, cfg, test)
        res[e] = o
    return res


def main(argv):
    C.require_real(argv)
    G = C.load('grid_t2')
    df = pd.read_parquet(C.OUT + '/grid_t2.parquet')
    assert len(df) == C.N_TOTAL and df['cfg_id'].nunique() == C.N_TOTAL
    ctx = G.build_real(C.REAL_KEY)
    res = measures(df, ctx)
    with open(C.OUT + '/select_t2.json.tmp', 'w') as fh:
        json.dump(res, fh, indent=1, default=float)
    os.replace(C.OUT + '/select_t2.json.tmp', C.OUT + '/select_t2.json')
    log.info('select_t2 done (CHUA AUDIT)')


if __name__ == '__main__':
    main(sys.argv[1:])
