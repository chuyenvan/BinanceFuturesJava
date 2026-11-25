"""LEVZ2 selection rule (PREREG_LEVZ2 sec 5), applied mechanically to out/grid.parquet.
- valid: >= 30 trades in EACH fold F1,F2,F3 AND net profit > 0 in all 3 folds AND DEV maxDD (worst-in-hour) <= 30 %.
- score = MIN over F1..F3 of (fold net return / fold maxDD worst-in-hour)   [CHOICES2: maxDD = worst-in-hour]
- rank valid by score desc (tie: cfg_id asc); plateau: neighbours = change exactly ONE parameter to an ADJACENT grid value
  (binary: the other value); if < 60 % of neighbours have net profit > 0 in all 3 folds => drop, try next.
- first survivor = CHOSEN; none => 'KHONG CO CAU HINH'.
usage: python3 code/select.py [grid.parquet]   -> out/select.json, out/select.md"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]  # this file must not shadow stdlib select
import importlib.util
import json
import logging
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

log = logging.getLogger('levz2.select')
BASE = '/home/ubuntu/claude_master/w3/levz2'
FOLDS3 = ('F1', 'F2', 'F3')
MIN_N = 30
MAX_DD = 0.30
PLATEAU = 0.60
DD_FLOOR = 1e-9


def _sim():
    mn = 'levz2_sim'
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(_HERE, 'sim.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod


def score_of(row):
    """maximin of fold return / fold maxDD (worst-in-hour)."""
    return float(min(row['%s_ret' % f] / max(row['%s_maxdd_worst' % f], DD_FLOOR) for f in FOLDS3))


def valid_of(row):
    return bool(all(row['%s_n' % f] >= MIN_N for f in FOLDS3) and all(row['%s_ret' % f] > 0 for f in FOLDS3)
                and row['DEV_maxdd_worst'] <= MAX_DD)


def pos3_of(row):
    return bool(all(row['%s_ret' % f] > 0 for f in FOLDS3))


def neighbours(cfg, grid):
    """configs differing in exactly ONE parameter, moved to an ADJACENT value of that parameter's grid list."""
    out = []
    for p, vals in grid.items():
        vals = list(vals)
        i = vals.index(cfg[p])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                d = {q: cfg[q] for q in grid}
                d[p] = vals[j]
                out.append(d)
    return out


def _key(d, pkeys):
    return tuple(d[p] for p in pkeys)


def select(df, grid, pkeys):
    df = df.copy()
    df['score'] = [score_of(r) for r in df.to_dict('records')]
    df['valid'] = [valid_of(r) for r in df.to_dict('records')]
    df['pos3'] = [pos3_of(r) for r in df.to_dict('records')]
    idx = {_key(r, pkeys): r for r in df.to_dict('records')}
    ranked = df[df['valid']].sort_values(['score', 'cfg_id'], ascending=[False, True], kind='mergesort')
    tried = []
    chosen = None
    for r in ranked.to_dict('records'):
        nb = neighbours(r, grid)
        got = [idx[_key(d, pkeys)] for d in nb if _key(d, pkeys) in idx]
        assert len(got) == len(nb), 'grid incomplete: missing neighbours'
        frac = float(np.mean([g['pos3'] for g in got])) if got else 0.0
        tried.append(dict(cfg_id=int(r['cfg_id']), score=float(r['score']), n_nb=len(got), frac_nb_pos3=frac,
                          plateau_ok=bool(frac >= PLATEAU)))
        if frac >= PLATEAU:
            chosen = r
            break
    return df, ranked, tried, chosen


def report(df, ranked, tried, chosen, grid, pkeys):
    rep = {'n_cfg': int(len(df)), 'n_valid': int(df['valid'].sum()), 'frac_valid': float(df['valid'].mean())}
    q = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    rep['score_q_all'] = [float(x) for x in np.quantile(df['score'], q)]
    rep['score_q_valid'] = [float(x) for x in np.quantile(ranked['score'], q)] if len(ranked) else []
    rep['plateau_tried'] = tried
    rep['chosen'] = None if chosen is None else {p: chosen[p] for p in pkeys + ('cfg_id', 'score')}
    rep['verdict'] = 'KHONG CO CAU HINH' if chosen is None else 'CO CAU HINH CHON'
    marg = {}
    for p in pkeys:
        marg[p] = {str(v): dict(median_score_all=float(df.loc[df[p] == v, 'score'].median()),
                                median_score_valid=(float(ranked.loc[ranked[p] == v, 'score'].median())
                                                    if (ranked[p] == v).any() else None),
                                n_valid=int(ranked[p].eq(v).sum()))
                   for v in grid[p]}
    rep['marginal'] = marg
    cols = ['cfg_id'] + list(pkeys) + ['score', 'F1_ret', 'F2_ret', 'F3_ret', 'F1_n', 'F2_n', 'F3_n', 'DEV_ret',
                                       'DEV_maxdd_worst', 'DEV_cagr']
    top = ranked[cols].head(20)
    rep['top20'] = top.to_dict('records')
    return rep, top


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    S = _sim()
    path = sys.argv[1] if len(sys.argv) > 1 else BASE + '/out/grid.parquet'
    df = pd.read_parquet(path)
    assert len(df) == 1296 and df['cfg_id'].nunique() == 1296, 'grid incomplete'
    df, ranked, tried, chosen = select(df, S.GRID, S.PKEYS)
    rep, top = report(df, ranked, tried, chosen, S.GRID, S.PKEYS)
    with open(BASE + '/out/select.json', 'w') as fh:
        json.dump(rep, fh, indent=1, default=float)
    df.to_parquet(BASE + '/out/grid_scored.parquet', index=False)
    with open(BASE + '/out/select.md', 'w') as fh:
        fh.write('# LEVZ2 select (CHUA AUDIT)\n\nverdict: %s\nchosen: %s\nvalid: %d / %d (%.3f)\n\n'
                 % (rep['verdict'], rep['chosen'], rep['n_valid'], rep['n_cfg'], rep['frac_valid']))
        fh.write('score quantiles all %s\nscore quantiles valid %s\n\n' % (rep['score_q_all'], rep['score_q_valid']))
        fh.write(top.to_string(index=False) + '\n\nmarginal:\n' + json.dumps(rep['marginal'], indent=1) + '\n')
    log.info('select verdict=%s chosen=%s n_valid=%d', rep['verdict'], rep['chosen'], rep['n_valid'])


if __name__ == '__main__':
    main()
