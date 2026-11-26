"""LEVZ S2 step 1: candidate sets (PREREG_LEVZ_S2 sec 2). REF = cand_b1 W7_E0_3.0 (copied); P5, P5b, P6a, P6b from sig_s2.states
via B0 sim.candidates() (E0: every state hour with a 1m bar has1m; order k asc, s desc, c asc). Cooldown 72 h is applied by the
B1 portfolio (port.py), as for B1. Output work/cand_s2.npz (cand_b1 layout: <set>_k/_c/_s/_cid, U_k/U_c) + out/cand_s2.json.
Regression vs levz_rev/sigcount/out/cand_s2.npz (P6a = D6_W7_Q0.999, P6b = D6_W7_Q0.998 identical; P5/P5b = D5/D5b p2 minus hours
with < 40 ranked coins).
usage: python3 code/cand_s2.py"""
import json
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_s2 as CM
log = CM.setup_log('cand_s2')
import numpy as np
import pandas as pd
import sig_s2 as SG
sys.path.pop(0)
CB, P, X, SIM = CM.b1()
R0 = CB.load_b0('rand')


def to_cand(S, score, U, has1m):
    Zs = np.where(S, score, np.nan)
    assert np.isfinite(Zs[S]).all()
    return SIM.candidates(Zs, Zs, np.ones(S.shape), None, U, has1m, 'E0', -1e300)


def yearly(ck, cc, tms):
    yr = pd.to_datetime(tms, unit='ms').year.values
    ek, ec = R0.episode_starts(ck, cc)
    L = SG.L
    cond = np.zeros((len(tms), int(cc.max()) + 1 if len(cc) else 1), bool)
    cond[ck, cc] = True
    ep = np.array([r for r, c in L.episodes(cond)], dtype=np.int64)
    f = lambda a: {str(y): int((yr[a] == y).sum()) for y in CM.YEARS}
    return dict(n_cand=f(ck), ep72_b0=f(ek), ep72_cool=f(ep) if len(ep) else {})


def main():
    t0 = time.time()
    D = SG.load_data()
    U, tms = D.U, D.tms
    has1m = np.load(CB.WORK + '/hourly.npz')['has1m']
    assert has1m.shape == U.shape
    st = SG.states(D.X, U, D.F, tms)
    log.info('states computed %.0fs', time.time() - t0)
    cz = np.load(CB.WORK + '/cand_b1.npz')
    sets = {'REF': (cz['W7_E0_3.0_k'], cz['W7_E0_3.0_c'], cz['W7_E0_3.0_s'])}
    for k in ('P5', 'P5b', 'P6a', 'P6b'):
        sets[k] = to_cand(st[k][0], st[k][1], U, has1m)
    # regression vs sigcount
    sc = np.load(CM.SIGCOUNT + '/cand_s2.npz')
    okh = st['n_ranked'] >= SG.MIN_RANKED
    reg = {}
    for k, ref in (('P6a', 'D6_W7_Q0.999'), ('P6b', 'D6_W7_Q0.998'), ('P5', 'D5_W7_p2'), ('P5b', 'D5b_W7_p2')):
        rk, rc, rs = sc[ref + '_k'], sc[ref + '_c'], sc[ref + '_s']
        if k.startswith('P5'):
            m = okh[rk]
            rk, rc, rs = rk[m], rc[m], rs[m]
        ck, cc, cs = sets[k]
        same = len(ck) == len(rk) and bool((ck == rk).all() and (cc == rc).all())
        reg[k] = dict(ref=ref, n=int(len(ck)), n_ref=int(len(rk)), identical=same,
                      max_abs_s=float(np.max(np.abs(cs - rs))) if same and len(cs) else None)
    log.info('REGRESSION vs sigcount %s', json.dumps(reg))
    out = {}
    for k in CM.SETS:
        out[k + '_k'], out[k + '_c'], out[k + '_s'] = [np.asarray(a) for a in sets[k]]
    code = np.unique(np.concatenate([out[k + '_k'] * 10000 + out[k + '_c'] for k in CM.SETS]))
    out['U_k'], out['U_c'] = code // 10000, code % 10000
    for k in CM.SETS:
        out[k + '_cid'] = np.searchsorted(code, out[k + '_k'] * 10000 + out[k + '_c']).astype(np.int64)
    np.savez(CM.WORK + '/cand_s2.npz.tmp.npz', **out)
    os.replace(CM.WORK + '/cand_s2.npz.tmp.npz', CM.WORK + '/cand_s2.npz')
    rowyr = pd.to_datetime(tms, unit='ms').year.values
    nr = st['n_ranked']
    info = dict(regression=reg, union=int(len(code)),
                hours_dropped_lt40={str(y): int(((nr < SG.MIN_RANKED) & (rowyr == y)).sum()) for y in CM.YEARS},
                sets={k: yearly(out[k + '_k'], out[k + '_c'], tms) for k in CM.SETS})
    b1u = set((cz['U_k'] * 10000 + cz['U_c']).tolist())
    info['union_in_b1_exits'] = int(sum(1 for x in code.tolist() if x in b1u))
    with open(CM.OUT + '/cand_s2.json', 'w') as fh:
        json.dump(info, fh, indent=1)
    log.info('cand_s2 done union=%d in_b1=%d %.0fs %s', len(code), info['union_in_b1_exits'], time.time() - t0,
             json.dumps(info['sets']))


if __name__ == '__main__':
    main()
