"""LEVZ B3 step 2 - exit_Y (PREREG_LEVZ_B3 sec 3) from levz_b1/out/grid_b1.parquet WITHOUT look-ahead.
Rows W = 7, E = E0 only (1 755 = 3 zmin x 3 K x 195 exits). Per exit (SL, H, arm, gap): score = median over the 9 (zmin, K) configs of
the profit of the folds < Y: Y = 2024 -> column F1_ret (fold 2022-01-01..2024-01-01); Y = 2025 -> F1_ret + F2_ret (SUM of the two
independent fold returns, CHOICES_B3 #3). exit_Y = argmax score; ties -> smaller SL, then shorter H, then B1 trailing order (TRAILS index).
Y = 2023 would need a fold ending 2023-01-01 (2022 alone): grid_b1 has only DEV/F1/F2/F3 => NOT computable by the rule (reported, no
substitute). The function only ever reads the allowed fold columns (restrict + assert).
usage: python3 code/exitsel_b3.py  -> out/exitsel_b3.json"""
import os
import sys
import json
import logging
sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('common_b3', os.path.join(_HERE, 'common_b3.py'))
C3 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault('common_b3', C3)
_spec.loader.exec_module(C3)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b3.exitsel')
FOLDS_FOR = {2024: ('F1',), 2025: ('F1', 'F2')}
XKEYS = ('SL', 'H', 'arm', 'gap')


def restrict(df, folds):
    keep = ['W', 'E', 'zmin', 'K', 'SL', 'H', 'arm', 'gap'] + ['%s_ret' % f for f in folds]
    out = df[keep].copy()
    for f in ('DEV', 'F1', 'F2', 'F3'):
        if f not in folds:
            assert not any(c.startswith(f + '_') for c in out.columns)
    return out


def select(df, Y, agg='sum'):
    folds = FOLDS_FOR[Y]
    d = restrict(df, folds)
    d = d[(d['W'] == 7) & (d['E'] == 'E0')]
    assert len(d) == 1755, len(d)
    if agg == 'sum':
        d['p'] = sum(d['%s_ret' % f] for f in folds)
    elif agg == 'compound':
        d['p'] = np.prod([1.0 + d['%s_ret' % f].values for f in folds], axis=0) - 1.0
    else:
        raise ValueError(agg)
    g = d.groupby(list(XKEYS))
    sc = g['p'].median().rename('score').reset_index()
    sc['n_zk'] = g['p'].size().values
    assert (sc['n_zk'] == 9).all() and len(sc) == 195
    sc['trail_i'] = [C3.CB.TRAILS.index((float(a), float(b))) for a, b in zip(sc['arm'], sc['gap'])]
    sc = sc.sort_values(['score', 'SL', 'H', 'trail_i'], ascending=[False, True, True, True], kind='mergesort').reset_index(drop=True)
    top = sc.iloc[0]
    xi = C3.CB.xidx(top['SL'], top['H'], top['arm'], top['gap'])
    n_tie = int((sc['score'] == top['score']).sum())
    return dict(Y=Y, columns_used=['%s_ret' % f for f in folds], agg=agg, rows='W==7 & E==E0 (1755)', xi=int(xi),
                SL=float(top['SL']), H=int(top['H']), arm=float(top['arm']), gap=float(top['gap']), score=float(top['score']),
                n_tied_at_top=n_tie, top5=sc.head(5)[list(XKEYS) + ['score']].to_dict('records'))


def main():
    df = pd.read_parquet(C3.B1OUT + '/grid_b1.parquet')
    assert len(df) == 7020
    rep = {}
    for Y in (2024, 2025):
        rep['exit_%d' % Y] = select(df, Y, 'sum')
        alt = select(df, Y, 'compound')
        rep['exit_%d_alt_compound' % Y] = dict(xi=alt['xi'], SL=alt['SL'], H=alt['H'], arm=alt['arm'], gap=alt['gap'],
                                                same_as_main=bool(alt['xi'] == rep['exit_%d' % Y]['xi']))
        log.info('exit_%d %s', Y, {k: rep['exit_%d' % Y][k] for k in ('xi', 'SL', 'H', 'arm', 'gap', 'score', 'n_tied_at_top')})
    rep['exit_2023'] = dict(xi=None, note='khong tinh duoc exit_2023 dung luat: grid_b1 khong co fold rieng < 2023 (chi DEV/F1/F2/F3); '
                                          'de MASTER quyet')
    with open(C3.OUT + '/exitsel_b3.json', 'w') as fh:
        json.dump(rep, fh, indent=1, default=float)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    main()
