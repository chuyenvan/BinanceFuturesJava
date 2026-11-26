"""LEVZ S2 step 2: exit table (195 exit configs) for the union of work/cand_s2.npz via B1 exits.compute (NOT modified).
Chunked (2000 cands / part, work/exits_parts/part_XXXX.npz, atomic, resumable) then merged to work/exits_s2.npz
(same keys as B1 exits.npz; row i = cid i of the cand_s2 union). Regression: every row whose (k, c) is also in the B1 union
must equal exits.npz EXACTLY (all keys). Hygiene: rows, NaN / inf counts, exit-reason shares, longgap (no PnL aggregation).
usage: python3 code/exits_s2.py [all | merge | check]"""
import glob
import json
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_s2 as CM
log = CM.setup_log('exits_s2')
sys.path.pop(0)
import numpy as np
CB, P, X, SIM = CM.b1()
PARTS = CM.WORK + '/exits_parts'
CH = 2000
KEYS1 = ('k', 'c', 'p0', 'longgap')


def compute_all():
    cz = np.load(CM.WORK + '/cand_s2.npz')
    uk, uc = cz['U_k'], cz['U_c']
    os.makedirs(PARTS, exist_ok=True)
    st = X.Store()
    t0 = time.time()
    for i, a in enumerate(range(0, len(uk), CH)):
        fn = '%s/part_%04d.npz' % (PARTS, i)
        if os.path.exists(fn):
            continue
        b = min(a + CH, len(uk))
        out = X.compute(st, uk[a:b], uc[a:b])
        out['a'] = np.int64(a)
        np.savez(fn + '.tmp.npz', **out)
        os.replace(fn + '.tmp.npz', fn)
        log.info('part %d rows %d..%d %.0fs', i, a, b, time.time() - t0)
    merge()


def merge():
    cz = np.load(CM.WORK + '/cand_s2.npz')
    n = len(cz['U_k'])
    fs = sorted(glob.glob(PARTS + '/part_*.npz'))
    parts = [np.load(f) for f in fs]
    assert [int(p['a']) for p in parts] == list(range(0, n, CH)), 'missing parts'
    keys = [k for k in parts[0].files if k != 'a']
    out = {k: np.concatenate([p[k] for p in parts], axis=0) for k in keys}
    assert len(out['k']) == n and (out['k'] == cz['U_k']).all() and (out['c'] == cz['U_c']).all()
    np.savez(CM.WORK + '/exits_s2.npz.tmp.npz', **out)
    os.replace(CM.WORK + '/exits_s2.npz.tmp.npz', CM.WORK + '/exits_s2.npz')
    log.info('merged exits_s2 n=%d', n)
    check()


def regression(T2, T1):
    c2 = T2['k'].astype(np.int64) * 10000 + T2['c']
    c1 = T1['k'].astype(np.int64) * 10000 + T1['c']
    common, i2, i1 = np.intersect1d(c2, c1, return_indices=True)
    res = dict(n_common=int(len(common)), mismatch={})
    for k in T1:
        a, b = T2[k][i2], T1[k][i1]
        eq = (a == b) | (np.isnan(a) & np.isnan(b)) if a.dtype.kind == 'f' else (a == b)
        res['mismatch'][k] = int((~eq).sum())
    res['pass'] = all(v == 0 for v in res['mismatch'].values())
    return res


def check():
    T2 = X.load_table(CM.WORK + '/exits_s2.npz')
    T1 = X.load_table()
    reg = regression(T2, T1)
    hy = dict(rows=int(len(T2['k'])), nonfinite={k: int((~np.isfinite(v)).sum()) for k, v in T2.items() if v.dtype.kind == 'f'},
              reason_share={CB.RNAMES[r]: float((T2['rs'] == r).mean()) for r in range(len(CB.RNAMES))},
              longgap=int(T2['longgap'].sum()), flag_share=float(T2['flag'].mean()))
    with open(CM.OUT + '/exits_s2.json', 'w') as fh:
        json.dump(dict(regression=reg, hygiene=hy), fh, indent=1)
    log.info('exits_s2 regression %s hygiene %s', json.dumps(reg), json.dumps(hy))
    return reg


if __name__ == '__main__':
    {'all': compute_all, 'merge': merge, 'check': check}[sys.argv[1] if len(sys.argv) > 1 else 'all']()
