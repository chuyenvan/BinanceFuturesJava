"""LEVZ2 random control (PREREG_LEVZ2 sec 6) for the CHOSEN config (out/select.json).
500 reps; keep every exit/size/K_max mechanism of the chosen config; replace the candidate set: for each month of DEV,
draw exactly as many (coin, hour) as the chosen config has real EPISODES starting in that month (ADDENDUM2 G1), uniformly
WITHOUT replacement from that month's (coin, hour) pairs that are in the universe AND have a store price; random score s ~ U(0,1).
p_rand = share of reps whose sec-5 score (maximin fold ret / fold maxDD worst) >= chosen score.
Seed: SEED below; rep r uses np.random.default_rng([SEED, r]) => independent of process / order; resumable.
usage: python3 code/rand.py   -> out/rand_parts/*.parquet, out/rand.parquet, out/rand.json"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]  # code/select.py must not shadow stdlib select
import glob
import importlib.util
import json
import logging
import time
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

log = logging.getLogger('levz2.rand')
BASE = '/home/ubuntu/claude_master/w3/levz2'
SEED = 20261126
NREP = 500
NPROC = 3
PARTS = BASE + '/out/rand_parts'


def _load(name):
    mn = 'levz2_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(_HERE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod


S = _load('sim')
SEL = _load('select')
G = {}


def month_keys(tms):
    d = pd.to_datetime(tms, unit='ms')
    return (d.year.values * 100 + d.month.values).astype(np.int64)


EP_GAP = 72


def episode_starts(ck, cc, gap=EP_GAP):
    """ADDENDUM2 G1: per coin, merge candidate hours whose consecutive gap <= 72 h; return first hour of each episode (k, c).
    Chaining runs over the whole candidate series (from 2021-12), starts are then counted by month."""
    ck = np.asarray(ck, dtype=np.int64)
    cc = np.asarray(cc, dtype=np.int64)
    if len(ck) == 0:
        return ck, cc
    o = np.lexsort((ck, cc))
    k, c = ck[o], cc[o]
    new = np.ones(len(k), dtype=bool)
    new[1:] = ~((c[1:] == c[:-1]) & (k[1:] - k[:-1] <= gap))
    return k[new], c[new]


def build_pools(I, real, a='2022-01-01', b='2026-01-01'):
    """per-month: number of real EPISODES (G1) starting in the month and pool of (k, c) in universe with price.
    Returns list of (n, ks, cs)."""
    k0, k1 = S.kidx(S.ms(a)), S.kidx(S.ms(b))
    mk = month_keys(I.tms)
    ok = I.U & np.isfinite(I.px['CL'])
    ek, ec = episode_starts(real.ck, real.cc)
    rm = (ek >= k0) & (ek < k1)
    cnt = pd.Series(mk[ek[rm]]).value_counts().to_dict()
    pools = []
    for m in np.unique(mk[k0:k1]):
        rows = np.flatnonzero(mk == m)
        rows = rows[(rows >= k0) & (rows < k1)]
        rk, rc = np.nonzero(ok[rows])
        n = int(cnt.get(int(m), 0))
        assert n <= len(rk), 'pool smaller than real count in month %d' % m
        pools.append((n, rows[rk].astype(np.int64), rc.astype(np.int64)))
    return pools


def draw(pools, rng):
    ks, cs = [], []
    for n, pk, pc in pools:
        if n == 0:
            continue
        j = rng.choice(len(pk), size=n, replace=False)
        ks.append(pk[j])
        cs.append(pc[j])
    ck = np.concatenate(ks) if ks else np.zeros(0, dtype=np.int64)
    cc = np.concatenate(cs) if cs else np.zeros(0, dtype=np.int64)
    sc = rng.random(len(ck))
    o = np.lexsort((cc, -sc, ck))
    return S.Cand(ck[o], cc[o], sc[o])


def work(r):
    rng = np.random.default_rng([SEED, r])
    cand = draw(G['pools'], rng)
    res = S.run_all(G['cfg'], G['I'], cand)
    res['rep'] = r
    res['n_cand'] = int(len(cand.ck))
    res['score'] = SEL.score_of(res)
    res['valid'] = SEL.valid_of(res)
    return res


def main():
    import multiprocessing as mp
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    with open(BASE + '/out/select.json') as fh:
        sel = json.load(fh)
    if sel.get('chosen') is None:
        with open(BASE + '/out/rand.json', 'w') as fh:
            json.dump({'verdict': 'KHONG CO CAU HINH - khong chay doi chung'}, fh)
        log.info('no chosen config; skip')
        return
    cfg = {p: sel['chosen'][p] for p in S.PKEYS}
    I = S.load_inputs()
    real = I.cand[(int(cfg['W']), cfg['E'], float(cfg['zmin']))]
    G.update(I=I, cfg=cfg, pools=build_pools(I, real))
    os.makedirs(PARTS, exist_ok=True)
    done = set()
    for f in glob.glob(PARTS + '/*.parquet'):
        done |= set(pd.read_parquet(f, columns=['rep'])['rep'].tolist())
    todo = [r for r in range(NREP) if r not in done]
    log.info('rand cfg=%s todo=%d done=%d', cfg, len(todo), len(done))
    buf = []
    t0 = time.time()

    def flush():
        if buf:
            fn = '%s/part_%d_%05d.parquet' % (PARTS, int(time.time() * 1000), buf[0]['rep'])
            pd.DataFrame(buf).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            buf.clear()
    with mp.get_context('fork').Pool(NPROC) as pool:
        for i, res in enumerate(pool.imap_unordered(work, todo, chunksize=2)):
            buf.append(res)
            if len(buf) >= 20:
                flush()
                log.info('rand %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
    flush()
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(PARTS + '/*.parquet'))], ignore_index=True)
    df = df.sort_values('rep').drop_duplicates('rep')
    assert len(df) == NREP
    df.to_parquet(BASE + '/out/rand.parquet', index=False)
    sc = float(sel['chosen']['score'])
    out = dict(cfg=cfg, seed=SEED, nrep=NREP, chosen_score=sc, p_rand=float((df['score'] >= sc).mean()),
               rand_score_q=[float(x) for x in np.quantile(df['score'], [0.05, 0.25, 0.5, 0.75, 0.95])],
               rand_frac_valid=float(df['valid'].mean()), n_real_episodes_dev=int(sum(p[0] for p in G['pools'])))
    with open(BASE + '/out/rand.json', 'w') as fh:
        json.dump(out, fh, indent=1)
    log.info('rand p_rand=%.4f chosen_score=%.4f', out['p_rand'], sc)


if __name__ == '__main__':
    main()
