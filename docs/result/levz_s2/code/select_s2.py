"""LEVZ S2 step 4: WFO (PREREG_LEVZ_S2 sec 4). Test year Y in {2023, 2024, 2025}; selection inside ONE set using ONLY folds < Y
(Y22 | Y22+Y23 | Y22+Y23+Y24) with select_b1.rule(..., dd_mode='folds') NOT modified: valid = n >= 30 & ret > 0 in every train fold &
max train maxDD-worst <= 30 %; score = min over train folds of ret / maxDD-worst; plateau >= 60 % neighbours ret > 0 in all train folds.
The df handed to rule() contains ONLY parameter columns + train-fold columns (asserted). Neighbours = select_b1.neighbours restricted
to K, SL, H, trailing (W / E / zmin are constants inside a set; CHOICES_S2 #4). Reports top-1, median of top-20 (first 20 passing the
full rule = select_b1 'top20_rule'), median of first 20 valid, grid median of the set in year Y. No valid config => 'khong cham duoc Y'.
LOCKED: real data only with --real I_HAVE_A1_PASS.  usage: python3 code/select_s2.py --real I_HAVE_A1_PASS"""
import json
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_s2 as CM
sys.path.pop(0)
import numpy as np
import pandas as pd
CB, P, X, SIM = CM.b1()
sys.path.insert(0, CM.B1CODE)
SB1 = CM.imp('select_b1', CM.B1CODE + '/select_b1.py')
sys.path.pop(0)
log = CM.setup_log('select_s2')
FOLDN = tuple(f[0] for f in CM.YFOLDS)
TRAIN = {2023: ('Y22',), 2024: ('Y22', 'Y23'), 2025: ('Y22', 'Y23', 'Y24')}
RULE = [SB1.rule]   # indirection so tests can spy


def neigh_s2(cfg):
    return [d for d in SB1.neighbours(cfg) if (d['W'], d['E'], d['zmin']) == (cfg['W'], cfg['E'], cfg['zmin'])]


def prep(df_set):
    d = df_set.copy()
    d['W'], d['E'], d['zmin'] = 7, 'E0', 3.0  # constants (members of select_b1.STD); neighbours changing them are dropped
    return d


def train_view(d, folds):
    cols = [c for c in d.columns if not any(c.startswith(f + '_') for f in FOLDN) or any(c.startswith(f + '_') for f in folds)]
    v = d[cols].copy()
    bad = [c for c in v.columns if any(c.startswith(f + '_') for f in FOLDN if f not in folds)]
    assert not bad, bad
    return v


def wfo_set(df_set):
    d = prep(df_set)
    out = {}
    for Y, folds in TRAIN.items():
        test = CM.FOLD_OF_YEAR[Y]
        R = RULE[0](train_view(d, folds), folds, 'folds', neigh=neigh_s2)
        ch = R['chosen']
        o = dict(train=list(folds), test=test, n_valid=int(R['d']['valid'].sum()), chosen=ch,
                 passing20=[int(x) for x in R['passing20']], valid20=[int(x) for x in R['valid20']])
        o['status'] = 'ok' if ch is not None else 'khong cham duoc %d' % Y
        o['top1'] = SB1._oos(d, [ch] if ch is not None else [], test)
        o['top20'] = SB1._oos(d, o['passing20'], test)
        o['top20_valid'] = SB1._oos(d, o['valid20'], test)
        o['grid_median'] = float(d[test + '_ret'].median())
        o['grid_frac_pos'] = float((d[test + '_ret'] > 0).mean())
        out[str(Y)] = o
    # MASTER decision on CHOICES #5: no silent 0 - sum over SCORED years only (year scored <=> a config passes the full rule)
    sc = [str(Y) for Y in TRAIN if out[str(Y)]['chosen'] is not None and out[str(Y)]['top20'].get('n', 0) > 0]
    out['scored_years'] = sc
    out['n_scored'] = len(sc)
    out['wfo_sum_top20'] = float(sum(out[Y]['top20']['median_ret'] for Y in sc)) if sc else float('nan')
    return out


def select_all(df):
    return {s: wfo_set(df[df['set'] == s].reset_index(drop=True)) for s in df['set'].unique()}


def main():
    CM.require_real(sys.argv)
    df = pd.read_parquet(CM.OUT + '/grid_s2.parquet')
    assert len(df) == 2925
    res = select_all(df)
    with open(CM.OUT + '/select_s2.json', 'w') as fh:
        json.dump(res, fh, indent=1, default=float)
    log.info('select_s2 done (CHUA AUDIT)')


if __name__ == '__main__':
    main()
