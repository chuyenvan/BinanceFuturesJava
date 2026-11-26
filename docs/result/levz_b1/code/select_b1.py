"""LEVZ B1 selection + reports (PREREG_LEVZ_B1 sec 4 (i)-(v)) on out/grid_b1.parquet.
rule(df, folds, dd_mode): the rule only ever SEES the columns of the allowed folds (restrict() drops every other fold's columns;
asserted). valid = n >= 30 in each allowed fold AND ret > 0 in each AND maxDD-worst <= 30 % (in-sample: DEV_maxdd_worst as B0;
WFO: max of the allowed folds' maxdd_worst); score = min over allowed folds of ret / maxdd_worst (floor 1e-9; B0 score_of);
rank score desc, tie cfg_id asc; plateau: >= 60 % of neighbours (one parameter moved one step) have ret > 0 in ALL allowed folds.
Neighbours: W, E, zmin, K, SL, H adjacent in their grid lists; trailing = arm in order (3, 5, 7, 10, off) with gap fixed, gap in
(2, 3, 5) with arm fixed; 'off' <-> (10 %, g) for every g (CHOICES_B1, CAN MASTER QUYET).
(ii) WFO: Y=2024 rule on F1 only -> F2; Y=2025 rule on F1+F2 -> F3; top-1 and top-20 (primary: first 20 passing the FULL rule
incl. plateau; also reported: first 20 valid by score).
usage: python3 code/select_b1.py [grid_b1.parquet]  -> out/select_b1.json, out/select_b1.md"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]
import json
import logging
sys.dont_write_bytecode = True
sys.path.insert(0, _HERE)
import common_b1 as CB
sys.path.pop(0)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b1.select')
MIN_N = 30
MAX_DD = 0.30
PLATEAU = 0.60
DD_FLOOR = 1e-9
ALLF = ('DEV', 'F1', 'F2', 'F3')
STD = dict(W=(14, 7), E=('E0', 'E1'), zmin=(2.5, 3.0, 3.5), K=(3, 5, 10), SL=CB.SLS, H=CB.HS)
PKEYS = ('W', 'E', 'zmin', 'K', 'SL', 'H', 'arm', 'gap')
ARM_ORDER = CB.ARMS + ('off',)


def restrict(df, allowed):
    """keep parameter columns + columns of allowed folds only."""
    keep = [c for c in df.columns if not any(c.startswith(f + '_') for f in ALLF) or any(c.startswith(f + '_') for f in allowed)]
    out = df[keep].copy()
    for f in ALLF:
        if f not in allowed:
            assert not any(c.startswith(f + '_') for c in out.columns)
    return out


def neighbours(cfg):
    out = []
    for p, vals in STD.items():
        vals = list(vals)
        i = vals.index(cfg[p])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                d = {q: cfg[q] for q in PKEYS}
                d[p] = vals[j]
                out.append(d)
    a, g = float(cfg['arm']), float(cfg['gap'])
    base = {q: cfg[q] for q in PKEYS}
    if a == 0.0:
        for gg in CB.GAPS:
            d = dict(base)
            d['arm'], d['gap'] = 0.10, gg
            out.append(d)
    else:
        i = ARM_ORDER.index(a)
        for j in (i - 1, i + 1):
            if 0 <= j < len(ARM_ORDER):
                d = dict(base)
                if ARM_ORDER[j] == 'off':
                    d['arm'], d['gap'] = 0.0, 0.0
                else:
                    d['arm'] = ARM_ORDER[j]
                out.append(d)
        gi = CB.GAPS.index(g)
        for j in (gi - 1, gi + 1):
            if 0 <= j < len(CB.GAPS):
                d = dict(base)
                d['gap'] = CB.GAPS[j]
                out.append(d)
    return out


def _key(d):
    return (int(d['W']), str(d['E']), round(float(d['zmin']), 3), int(d['K']), round(float(d['SL']), 3), int(d['H']),
            round(float(d['arm']), 3), round(float(d['gap']), 3))


def rule(df, folds, dd_mode, neigh=neighbours, key=_key, pkeys=PKEYS):
    """apply the selection rule using ONLY the allowed folds. dd_mode: 'DEV' (in-sample, B0) or 'folds' (WFO)."""
    allowed = tuple(folds) + (('DEV',) if dd_mode == 'DEV' else ())
    d = restrict(df, allowed)
    ret = np.vstack([d['%s_ret' % f].values for f in folds])
    ddw = np.vstack([d['%s_maxdd_worst' % f].values for f in folds])
    nn = np.vstack([d['%s_n' % f].values for f in folds])
    score = (ret / np.maximum(ddw, DD_FLOOR)).min(axis=0)
    pos = (ret > 0).all(axis=0)
    ddv = d['DEV_maxdd_worst'].values if dd_mode == 'DEV' else ddw.max(axis=0)
    valid = (nn >= MIN_N).all(axis=0) & pos & (ddv <= MAX_DD)
    d['score'], d['pos'], d['valid'] = score, pos, valid
    idx = {key(r): bool(r['pos']) for r in d[list(pkeys) + ['pos']].to_dict('records')}
    ranked = d[d['valid']].sort_values(['score', 'cfg_id'], ascending=[False, True], kind='mergesort')
    tried, passing = [], []
    for r in ranked.to_dict('records'):
        nb = neigh(r)
        got = [idx[key(x)] for x in nb if key(x) in idx]
        assert len(got) == len(nb), 'grid incomplete: missing neighbours'
        frac = float(np.mean(got)) if got else 0.0
        ok = frac >= PLATEAU
        if len(tried) < 200:
            tried.append(dict(cfg_id=int(r['cfg_id']), score=float(r['score']), n_nb=len(got), frac=frac, ok=ok))
        if ok:
            passing.append(int(r['cfg_id']))
            if len(passing) >= 20:
                break
    chosen = passing[0] if passing else None
    return dict(d=d, ranked=ranked, tried=tried, passing20=passing, chosen=chosen,
                valid20=ranked['cfg_id'].head(20).astype(int).tolist())


def _oos(df, ids, f):
    if not ids:
        return dict(n=0)
    s = df.set_index('cfg_id').loc[ids]
    r = s['%s_ret' % f].values
    return dict(n=len(ids), median_ret=float(np.median(r)), frac_pos=float((r > 0).mean()),
                rets=[float(x) for x in r], dd_worst=[float(x) for x in s['%s_maxdd_worst' % f].values],
                n_trades=[int(x) for x in s['%s_n' % f].values])


def wfo(df):
    out = {}
    for Y, folds, test in (('2024', ('F1',), 'F2'), ('2025', ('F1', 'F2'), 'F3')):
        R = rule(df, folds, 'folds')
        o = dict(select_folds=list(folds), test_fold=test, n_valid=int(R['d']['valid'].sum()), chosen=R['chosen'])
        o['top1'] = _oos(df, [R['chosen']] if R['chosen'] is not None else [], test)
        o['top20_rule'] = _oos(df, R['passing20'], test)
        o['top20_valid'] = _oos(df, R['valid20'], test)
        o['grid_all'] = dict(median_ret=float(df['%s_ret' % test].median()), frac_pos=float((df['%s_ret' % test] > 0).mean()))
        out[Y] = o
    return out


def robustness(df):
    from scipy.stats import spearmanr
    sc = {f: (df['%s_ret' % f] / np.maximum(df['%s_maxdd_worst' % f], DD_FLOOR)).values for f in ('F1', 'F2', 'F3')}
    out = {}
    for a, b in (('F1', 'F2'), ('F2', 'F3'), ('F1', 'F3')):
        out['spearman_%s_%s' % (a, b)] = float(spearmanr(sc[a], sc[b]).correlation)
    for f in ALLF:
        out['frac_pos_%s' % f] = float((df['%s_ret' % f] > 0).mean())
    out['frac_pos_all3'] = float(((df['F1_ret'] > 0) & (df['F2_ret'] > 0) & (df['F3_ret'] > 0)).mean())
    return out


def marginal(d, ranked):
    out = {}
    for p in PKEYS:
        out[p] = {str(v): dict(median_score=float(d.loc[d[p] == v, 'score'].median()), n_valid=int((ranked[p] == v).sum()),
                               median_DEV_ret=float(d.loc[d[p] == v, 'DEV_ret'].median()))
                  for v in sorted(d[p].unique(), key=lambda x: str(x))}
    return out


def ref_b0(df):
    """(v) B0 759/758 parameters with trailing 10 % / 5 % on the 1m engine."""
    m = (df['W'] == 7) & (df['E'] == 'E0') & (df['zmin'] == 3.0) & (df['K'] == 3) & (df['SL'] == 0.15) & (df['H'] == 24)
    r = df[m & (df['arm'] == 0.10) & (df['gap'] == 0.05)]
    assert len(r) == 1
    return r.iloc[0].to_dict()


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    path = sys.argv[1] if len(sys.argv) > 1 else CB.OUT + '/grid_b1.parquet'
    df = pd.read_parquet(path)
    assert len(df) == 7020 and df['cfg_id'].nunique() == 7020
    R = rule(df, ('F1', 'F2', 'F3'), 'DEV')
    rep = dict(n_cfg=7020, n_valid=int(R['d']['valid'].sum()), chosen=R['chosen'], plateau_tried=R['tried'][:50],
               top20=R['d'].set_index('cfg_id').loc[R['valid20']].reset_index()[['cfg_id'] + list(PKEYS) + [
                   'score', 'F1_ret', 'F2_ret', 'F3_ret', 'F1_n', 'F2_n', 'F3_n', 'DEV_ret', 'DEV_maxdd_worst']].to_dict('records'),
               marginal=marginal(R['d'], R['ranked']), wfo=wfo(df), robust=robustness(df), ref_b0_759_trail_10_5=ref_b0(df))
    with open(CB.OUT + '/select_b1.json', 'w') as fh:
        json.dump(rep, fh, indent=1, default=float)
    R['d'].to_parquet(CB.OUT + '/grid_b1_scored.parquet', index=False)
    log.info('select_b1 chosen=%s n_valid=%d (CHUA AUDIT)', rep['chosen'], rep['n_valid'])


if __name__ == '__main__':
    main()


# ---------------------------------------------------------------- (iv) breakdown (re-runs port for ONE config on DEV)
def ew_alt_daily():
    """EW alt daily return: mean over coins in universe at day start of CLH(next 00:00) / CLH(00:00) - 1 (marks = 1m close)."""
    hz = np.load(CB.WORK + '/hourly.npz')
    clh = hz['CLH'].astype(np.float64)
    U = np.load(CB.L2 + '/work/inputs.npz')['U']
    k = np.arange(0, CB.NH, 24)
    a, b = clh[k[:-1]], clh[k[1:]]
    u = U[k[:-1]] & np.isfinite(a) & np.isfinite(b)
    r = np.where(u, b / np.where(u, a, 1.0) - 1.0, 0.0)
    ew = r.sum(axis=1) / np.maximum(u.sum(axis=1), 1)
    t = CB.H0 + k[:-1] * CB.H
    return pd.Series(ew, index=t)


def breakdown(cfg, T=None, cz=None):
    P = CB.load('port')
    X = CB.load('exits')
    if T is None:
        T = X.load_table()
    if cz is None:
        cz = np.load(CB.WORK + '/cand_b1.npz')
    cand = P.load_class(cz, int(cfg['W']), cfg['E'], float(cfg['zmin']))
    xv = P.XView(T, CB.xidx(cfg['SL'], cfg['H'], cfg['arm'], cfg['gap']))
    S = P.S
    k0, kl = S.kidx(S.ms('2022-01-01')), S.kidx(S.ms('2026-01-01')) - 1
    tr, eq, m = P.run(int(cfg['K']), cand, xv, k0, kl)
    syms = CB.meta()['syms']
    tr['sym'] = [syms[c] for c in tr['c']]
    tr['month'] = pd.to_datetime(CB.H0 + tr['ke'].values * CB.H, unit='ms').strftime('%Y-%m')
    tot = float(tr['net'].sum())
    out = dict(n=int(len(tr)), net_total=tot, fund_total=float(tr['funding'].sum()), fees_total=float(tr['fees'].sum()))
    out['by_reason'] = {r: dict(n=int((tr['reason'] == r).sum()), net=float(tr.loc[tr['reason'] == r, 'net'].sum()))
                        for r in CB.RNAMES}
    n5 = int(np.ceil(0.05 * len(tr)))
    top = tr['net'].sort_values(ascending=False).head(n5)
    out['top5pct'] = dict(n=n5, net=float(top.sum()), net_without=tot - float(top.sum()))
    out['by_month'] = tr.groupby('month')['net'].sum().to_dict()
    bc = tr.groupby('sym')['net'].sum().sort_values(ascending=False)
    out['top5_coins'] = bc.head(5).to_dict()
    out['worst_ret'] = float(tr['ret'].min())
    out['worst_ret_over_SL'] = float(-tr['ret'].min() / float(cfg['SL']))
    out['worst_mx_over_SL'] = float((tr['mx'].max() - 1.0) / float(cfg['SL']))
    e = eq.set_index('t')['eq']
    d = e[(e.index % 86400000) == 0]
    dr = d.pct_change().dropna()
    ew = ew_alt_daily().reindex(dr.index - 86400000)
    out['corr_daily_ew_alt'] = float(np.corrcoef(dr.values, ew.values)[0, 1]) if len(dr) > 2 else None
    return out
