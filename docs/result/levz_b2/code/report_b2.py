"""LEVZ B2 step 4 - measurements (PREREG_LEVZ_B2 sec 3) and criteria (a)-(d) (sec 4) for every option O with out/grid_b2_<O>.parquet,
paired by cfg_id with the B1 baseline levz_b1/out/grid_b1.parquet ('gate off'). 'loi nhuan' = column <fold>_ret (fraction; 2 diem % = 0.02).
WFO via levz_b1 select_b1.wfo (top-1 = first config passing the FULL rule; top-20 = 20 best-score VALID configs = 'top20_valid',
ADDENDUM1 B of B1). Valid count = B1 in-sample rule (select_b1.rule on F1..F3, dd_mode DEV).
Criteria (all required):
 (a) F2: frac(ret > 0) >= 0.50 AND median ret >= 0
 (b) F1 and F3: median ret >= base median - 0.02 AND frac(ret > 0) >= base frac - 0.10
 (c) trades kept >= 0.50 in EVERY one of DEV, F1, F2, F3, where kept = min(median_cfg(n_O / n_base), median(n_O) / median(n_base))
     (CHOICES_B2: both readings, the smaller counts; DEV included)
 (d) WFO top20_valid median ret > 0 for 2024 AND 2025
usage: python3 code/report_b2.py  -> out/report_b2.json|md"""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2c
sys.path.pop(0)
import json
import logging
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b2.report')
SEL = b2c.b1('select_b1')
O = b2c.b2('opts')
GRID_B1 = '/home/ubuntu/claude_master/w3/levz_b1/out/grid_b1.parquet'
FOLDS = ('DEV', 'F1', 'F2', 'F3')
TOL_MED = 0.02
TOL_FRAC = 0.10
KEEP = 0.50


def fold_stats(df, base=None):
    out = {}
    for f in FOLDS:
        r = df['%s_ret' % f].values
        d = dict(median_ret=float(np.median(r)), frac_pos=float((r > 0).mean()),
                 median_maxdd_worst=float(np.median(df['%s_maxdd_worst' % f])), max_maxdd_worst=float(df['%s_maxdd_worst' % f].max()),
                 median_n=float(np.median(df['%s_n' % f])))
        if base is not None:
            rb = base['%s_ret' % f].values
            nb = base['%s_n' % f].values.astype(np.float64)
            no = df['%s_n' % f].values.astype(np.float64)
            d['median_diff_ret'] = float(np.median(r - rb))
            d['frac_improved'] = float((r > rb).mean())
            ok = nb > 0
            d['median_trade_ratio'] = float(np.median(no[ok] / nb[ok])) if ok.any() else None
            d['ratio_of_median_trades'] = float(np.median(no) / np.median(nb)) if np.median(nb) > 0 else None
            d['trades_kept'] = min(x for x in (d['median_trade_ratio'], d['ratio_of_median_trades']) if x is not None)
        out[f] = d
    return out


def criteria(st, stb, wf):
    c = {}
    c['a'] = bool(st['F2']['frac_pos'] >= 0.5 and st['F2']['median_ret'] >= 0.0)
    c['b'] = bool(all(st[f]['median_ret'] >= stb[f]['median_ret'] - TOL_MED and st[f]['frac_pos'] >= stb[f]['frac_pos'] - TOL_FRAC
                      for f in ('F1', 'F3')))
    c['c'] = bool(all(st[f]['trades_kept'] >= KEEP for f in FOLDS))
    c['d'] = bool(all(wf[y]['top20_valid'].get('n', 0) > 0 and wf[y]['top20_valid']['median_ret'] > 0.0 for y in ('2024', '2025')))
    c['pass_a_to_d'] = bool(c['a'] and c['b'] and c['c'] and c['d'])
    return c


def one(df, base=None):
    assert len(df) == 7020 and df['cfg_id'].tolist() == list(range(7020))
    if base is not None:
        assert df[list(SEL.PKEYS)].equals(base[list(SEL.PKEYS)])
    st = fold_stats(df, base)
    R = SEL.rule(df, ('F1', 'F2', 'F3'), 'DEV')
    wf = SEL.wfo(df)
    for y in wf:
        for kk in ('top20_rule', 'top20_valid', 'top1'):
            wf[y][kk].pop('dd_worst', None)
    return dict(folds=st, n_valid_insample=int(R['d']['valid'].sum()), chosen_insample=R['chosen'], wfo=wf)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    base = pd.read_parquet(GRID_B1).sort_values('cfg_id').reset_index(drop=True)
    rep = dict(base=one(base, base))
    stb = rep['base']['folds']
    mkm = b2c.b2('mkt')
    mk = mkm.load()
    nh, h0 = int(mk['NH']), int(mk['H0'])
    yr = pd.to_datetime(h0 + np.arange(nh, dtype=np.int64) * O.H, unit='ms').year.values
    rep['opts'] = {}
    for o in O.OPTS:
        fn = '%s/grid_b2_%s.parquet' % (b2c.OUT, o)
        if not os.path.exists(fn):
            rep['opts'][o] = dict(missing=True)
            continue
        df = pd.read_parquet(fn).sort_values('cfg_id').reset_index(drop=True)
        r = one(df, base)
        r['criteria'] = criteria(r['folds'], stb, r['wfo'])
        if o in O.GATES:
            g = O.gate_series(o, mk)
            r['gate_open'] = {str(y): float(g[yr == y].mean()) for y in (2022, 2023, 2024, 2025)}
        rep['opts'][o] = r
        log.info('%s criteria %s', o, r['criteria'])
    with open(b2c.OUT + '/report_b2.json', 'w') as fh:
        json.dump(rep, fh, indent=1, default=float)
    L = ['# report_b2 (PREREG_LEVZ_B2 sec 3-4) - CHUA AUDIT', '', '## Tom tat theo fold (median ret / frac lai / median diff vs goc / frac cai thien / lenh con lai)', '']
    L.append('| O | fold | med ret | frac lai | med diff | frac cai thien | lenh con lai | med maxDDw |')
    L.append('|---|---|---|---|---|---|---|---|')
    for f in FOLDS:
        s = stb[f]
        L.append('| GOC | %s | %.4f | %.3f | - | - | - | %.3f |' % (f, s['median_ret'], s['frac_pos'], s['median_maxdd_worst']))
    for o, r in rep['opts'].items():
        if r.get('missing'):
            L.append('| %s | (chua chay) |||||||' % o)
            continue
        for f in FOLDS:
            s = r['folds'][f]
            L.append('| %s | %s | %.4f | %.3f | %.4f | %.3f | %.3f | %.3f |' % (o, f, s['median_ret'], s['frac_pos'], s['median_diff_ret'],
                                                                         s['frac_improved'], s['trades_kept'], s['median_maxdd_worst']))
    L += ['', '## WFO + tieu chi', '', '| O | n hop le | 2024 top1 | 2024 top20v med | 2025 top1 | 2025 top20v med | a | b | c | d | dat a-d |',
          '|---|---|---|---|---|---|---|---|---|---|---|']

    def t1(w):
        return '%.4f' % w['top1']['rets'][0] if w['top1'].get('n') else '-'

    def t20(w):
        return '%.4f' % w['top20_valid']['median_ret'] if w['top20_valid'].get('n') else '-'
    b = rep['base']
    L.append('| GOC | %d | %s | %s | %s | %s | | | | | |' % (b['n_valid_insample'], t1(b['wfo']['2024']), t20(b['wfo']['2024']),
                                                         t1(b['wfo']['2025']), t20(b['wfo']['2025'])))
    for o, r in rep['opts'].items():
        if r.get('missing'):
            continue
        c = r['criteria']
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            o, r['n_valid_insample'], t1(r['wfo']['2024']), t20(r['wfo']['2024']), t1(r['wfo']['2025']), t20(r['wfo']['2025']),
            c['a'], c['b'], c['c'], c['d'], c['pass_a_to_d']))
    with open(b2c.OUT + '/report_b2.md', 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    log.info('report_b2 written (CHUA AUDIT)')


if __name__ == '__main__':
    main()
