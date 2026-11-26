"""LEVZ B1 random control (PREREG_LEVZ_B1 sec 4 (vi)). For a class (W, E, zmin): each rep replaces the candidates by random
(coin, hour): per month exactly the number of real EPISODES of the class (ADDENDUM2 G1; B0 rand.episode_starts / build_pools /
draw, imported) drawn uniformly without replacement from that month's (coin, hour) in universe with a 1m bar at T_k; s ~ U(0,1).
Then the FULL exit grid x K (195 x 3 = 585 configs, DEV + F1..F3 each) is run; statistic = max over the 585 of the maximin
score (B0 select.score_of) and the number of valid configs (B0 select.valid_of). p_max = share of reps with max score >= real
max score of the class (from out/grid_b1.parquet). Seed: default_rng([SEED, class_index, rep]).
usage: python3 code/rand_b1.py [reduced] [nrep]   (reduced = classes (W7,E0,z) and (W14,E0,z), z in {2.5,3.0,3.5})"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]
import glob
import json
import logging
import time
sys.dont_write_bytecode = True
sys.path.insert(0, _HERE)
import common_b1 as CB
sys.path.pop(0)
import numpy as np
import pandas as pd

P = CB.load('port')
X = CB.load('exits')

log = logging.getLogger('levz_b1.rand')
SEED = 20261127
NREP = 100
NPROC = 3
PARTS = CB.OUT + '/rand_b1_parts'
R0 = CB.load_b0('rand')
SEL0 = CB.load_b0('select')
CLASSES = [(W, E, z) for W in (14, 7) for E in ('E0', 'E1') for z in (2.5, 3.0, 3.5)]
REDUCED = [(W, 'E0', z) for W in (7, 14) for z in (2.5, 3.0, 3.5)]
G = {}


class Shim:
    pass


def make_shim():
    I = Shim()
    I.tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    I.U = np.load(CB.L2 + '/work/inputs.npz')['U']
    has1m = np.load(CB.WORK + '/hourly.npz')['has1m']
    I.px = {'CL': np.where(has1m, 1.0, np.nan)}
    return I


def real_cand(cz, W, E, z):
    key = 'W%d_%s_%.1f' % (W, E, z)
    o = Shim()
    o.ck, o.cc = cz[key + '_k'], cz[key + '_c']
    return o


def score_grid(cand, T):
    """run 3 K x 195 exits; return (max score, n_valid, argmax (K, xi), seconds)."""
    t0 = time.time()
    best, bk, nv = -np.inf, None, 0
    for xi in range(len(CB.XCFGS)):
        xv = P.XView(T, xi)
        for K in (3, 5, 10):
            r = P.run_all(K, cand, xv)
            s = SEL0.score_of(r)
            nv += int(SEL0.valid_of(r))
            if s > best:
                best, bk = s, (K, xi)
    return best, nv, bk, time.time() - t0


def one_rep(ci, r):
    W, E, z = G['classes'][ci]
    rng = np.random.default_rng([SEED, ci, r])
    c0 = R0.draw(G['pools'][ci], rng)
    T = X.compute(G['st'], c0.ck, c0.cc)
    cand = P.CandB1(c0.ck, c0.cc, c0.cs, np.arange(len(c0.ck), dtype=np.int64))
    best, nv, bk, sec = score_grid(cand, T)
    return dict(ci=ci, W=W, E=E, zmin=z, rep=r, n_cand=int(len(c0.ck)), max_score=float(best), n_valid=nv,
                best_K=bk[0], best_xi=bk[1], sec=sec)


def setup(classes):
    I = make_shim()
    cz = np.load(CB.WORK + '/cand_b1.npz')
    G['classes'] = classes
    G['pools'] = [R0.build_pools(I, real_cand(cz, *c)) for c in classes]
    G['st'] = X.Store()
    return [int(sum(p[0] for p in pl)) for pl in G['pools']]


def _work(t):
    return one_rep(*t)


def main():
    import multiprocessing as mp
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    classes = REDUCED if 'reduced' in sys.argv[1:] else CLASSES
    nrep = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[1:]) else NREP
    assert nrep >= 100
    neps = setup(classes)
    log.info('rand_b1 classes=%s episodes=%s nrep=%d', classes, neps, nrep)
    os.makedirs(PARTS, exist_ok=True)
    done = set()
    for f in glob.glob(PARTS + '/*.parquet'):
        d = pd.read_parquet(f, columns=['W', 'E', 'zmin', 'rep'])
        done |= set(zip(d['W'], d['E'], d['zmin'], d['rep']))
    todo = [(ci, r) for r in range(nrep) for ci, c in enumerate(classes) if (c[0], c[1], c[2], r) not in done]
    buf = []
    t0 = time.time()

    def flush():
        if buf:
            fn = '%s/part_%d.parquet' % (PARTS, int(time.time() * 1000))
            pd.DataFrame(buf).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            buf.clear()
    with mp.get_context('fork').Pool(NPROC) as pool:
        for i, res in enumerate(pool.imap_unordered(_work, todo, chunksize=1)):
            buf.append(res)
            if len(buf) >= 3:
                flush()
                log.info('rand_b1 %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
    flush()
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(PARTS + '/*.parquet'))], ignore_index=True)
    df = df.drop_duplicates(['W', 'E', 'zmin', 'rep'])
    df.to_parquet(CB.OUT + '/rand_b1.parquet', index=False)
    g = pd.read_parquet(CB.OUT + '/grid_b1.parquet')
    res = {}
    for (W, E, z) in classes:
        gg = g[(g['W'] == W) & (g['E'] == E) & (g['zmin'] == z)]
        assert len(gg) == 585
        rs = [SEL0.score_of(r) for r in gg.to_dict('records')]
        rv = int(sum(SEL0.valid_of(r) for r in gg.to_dict('records')))
        dd = df[(df['W'] == W) & (df['E'] == E) & (df['zmin'] == z)]
        real = float(max(rs))
        res['W%d_%s_%.1f' % (W, E, z)] = dict(real_max_score=real, real_n_valid=rv, nrep=int(len(dd)),
                                               p_max=float((dd['max_score'] >= real).mean()),
                                               rand_max_q=[float(x) for x in np.quantile(dd['max_score'], [0.05, 0.5, 0.95])],
                                               rand_n_valid_median=float(dd['n_valid'].median()))
    with open(CB.OUT + '/rand_b1.json', 'w') as fh:
        json.dump(dict(seed=SEED, classes=[list(c) for c in classes], res=res), fh, indent=1)
    log.info('rand_b1 done (CHUA AUDIT)')


if __name__ == '__main__':
    main()
