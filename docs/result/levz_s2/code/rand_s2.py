"""LEVZ S2 step 5: random control (PREREG_LEVZ_S2 sec 4), 100 reps per set. Rep: random (coin, hour) drawn uniformly without
replacement, per CALENDAR YEAR exactly the set's number of episodes (ep72 = B0 rand.episode_starts, gap <= 72 h chaining), from that
year's (k, c) with U and a 1m bar (has1m); s ~ U(0,1) (B0 rand.draw). Exit table for the draw = B1 exits.compute; full 585-config grid
(K x 195) on DEV + Y22..Y25 (grid_s2.run_cfg); stats: max_dev = max over grid of DEV_ret / max(DEV_maxdd_worst, 1e-9) (in-sample,
CHOICES_S2 #6) and wfo_sum = select_s2.wfo_set(...)['wfo_sum_top20']. p_max / p_wfo = share of reps >= real.
Seed default_rng([SEED, set_index, rep]); one part file per rep (out/rand_s2_parts/<set>_<rep>.parquet); resumable.
LOCKED: --real I_HAVE_A1_PASS.  usage: python3 code/rand_s2.py --real I_HAVE_A1_PASS [--nrep 100] [--nproc N] [--shard i/n]  (shard i of n: task index % n == i; seeds per (set, rep) => shards / Kaggle give identical results; summary written when all parts exist)"""
import glob
import json
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_s2 as CM
sys.path.pop(0)
import numpy as np
import pandas as pd
CB, P, X, SIM = CM.b1()
R0 = CB.load_b0('rand')
GR = CM.s2('grid_s2')
SEL = CM.s2('select_s2')
log = CM.setup_log('rand_s2')
SEED = 20261128
NREP = 100
G = {}


def year_pools(U, ok1m, real_ck, real_cc, tms):
    """list of (n, ks, cs) per year 2022..2025 (format of B0 rand.build_pools, consumed by R0.draw)."""
    yr = pd.to_datetime(tms, unit='ms').year.values
    ek, ec = R0.episode_starts(real_ck, real_cc)
    ok = U & ok1m
    pools = []
    for y in CM.YEARS:
        rows = np.flatnonzero(yr == y)
        rk, rc = np.nonzero(ok[rows])
        n = int((yr[ek] == y).sum())
        assert n <= len(rk)
        pools.append((n, rows[rk].astype(np.int64), rc.astype(np.int64)))
    return pools


def rng_for(si, r):
    """seed depends on (set index, rep) only => shards / order give identical draws; different sets -> different streams."""
    return np.random.default_rng([SEED, si, r])


def p_wfo_stat(rows, real_years, real_sum):
    """ERRATA2 F1: a random rep's WFO sum is taken over EXACTLY the real set's scored years; a rep that did not score one of
    them counts as NOT >= real. real set with no scored year => NaN."""
    if not real_years or real_sum is None or not np.isfinite(real_sum):
        return float('nan')
    ge = []
    for r in rows:
        sc = set(str(r['scored']).split('/')) if r['scored'] else set()
        if not set(real_years) <= sc:
            ge.append(False)
            continue
        ge.append(float(sum(r['top20_%s' % Y] for Y in real_years)) >= real_sum)
    return float(np.mean(ge)) if ge else float('nan')


def one_rep(si, s, r):
    rng = rng_for(si, r)
    c0 = R0.draw(G['pools'][s], rng)
    T = G['table_fn'](c0.ck, c0.cc)
    cand = P.CandB1(c0.ck, c0.cc, c0.cs, np.arange(len(c0.ck), dtype=np.int64))
    cfgs = GR.all_cfgs((s,))
    df = GR.grid_df({s: cand}, T, cfgs)
    md = float((df['DEV_ret'] / np.maximum(df['DEV_maxdd_worst'], 1e-9)).max())
    w = SEL.wfo_set(df)
    yr = pd.to_datetime(CB.H0 + c0.ck * CB.H, unit='ms').year.values
    return dict(set=s, si=si, rep=r, seed='%d_%d_%d' % (SEED, si, r), n_cand=int(len(c0.ck)),
                **{'n_%d' % y: int((yr == y).sum()) for y in CM.YEARS}, max_dev=md, wfo_sum=w['wfo_sum_top20'],
                n_scored=w['n_scored'], scored='/'.join(w['scored_years']),
                **{'top20_%s' % Y: w[Y]['top20'].get('median_ret', np.nan) for Y in ('2023', '2024', '2025')})


def _work(t):
    return one_rep(*t)


def run_reps(sets, nrep, parts, nproc=1, shard=(0, 1)):
    os.makedirs(parts, exist_ok=True)
    done = set()
    for f in glob.glob(parts + '/*.parquet'):
        d = pd.read_parquet(f, columns=['set', 'rep'])
        done |= set(zip(d['set'], d['rep']))
    allt = [(si, s, r) for r in range(nrep) for si, s in enumerate(sets)]
    si_, sn_ = shard
    todo = [t for i, t in enumerate(allt) if i % sn_ == si_ and (t[1], t[2]) not in done]   # seed depends only on (set, rep)
    log.info('rand_s2 todo=%d done=%d', len(todo), len(done))
    t0 = time.time()
    if nproc <= 1:
        it = map(_work, todo)
    else:
        import multiprocessing as mp
        pool = mp.get_context('fork').Pool(nproc)
        it = pool.imap_unordered(_work, todo, chunksize=1)
    for i, res in enumerate(it):
        fn = '%s/%s_%04d.parquet' % (parts, res['set'], res['rep'])
        pd.DataFrame([res]).to_parquet(fn + '.tmp', index=False)
        os.replace(fn + '.tmp', fn)
        log.info('rand_s2 %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
    if nproc > 1:
        pool.close()
        pool.join()
    return len(todo)


def summarize(sets, parts, real_df, real_sel, nrep):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(parts + '/*.parquet'))], ignore_index=True)
    df = df.drop_duplicates(['set', 'rep'])
    res = {}
    for s in sets:
        d = df[df['set'] == s]
        g = real_df[real_df['set'] == s]
        rmax = float((g['DEV_ret'] / np.maximum(g['DEV_maxdd_worst'], 1e-9)).max())
        rw = float(real_sel[s]['wfo_sum_top20'])
        # p_wfo: rand reps with no scored year (wfo_sum NaN) count as NOT >= real; real NaN => p_wfo NaN (cannot score)
        pw = p_wfo_stat(d.to_dict('records'), real_sel[s]['scored_years'], rw)
        res[s] = dict(nrep=int(len(d)), real_max_dev_insample=rmax, real_wfo_sum=rw, real_n_scored=real_sel[s]['n_scored'],
                      real_scored_years=real_sel[s]['scored_years'],
                      p_max_insample=float((d['max_dev'] >= rmax).mean()), p_wfo=pw,
                      rand_n_scored_counts={str(k): int(v) for k, v in d['n_scored'].value_counts().items()},
                      rand_wfo_q=[float(x) for x in np.nanquantile(d['wfo_sum'], [0.05, 0.5, 0.95])] if d['wfo_sum'].notna().any() else None)
        assert len(d) == nrep, (s, len(d))
    return res


def real_pools(sets=CM.SETS):
    """pools from the REAL universe U (levz2 inputs.npz) AND has1m (B1 hourly.npz); counts = ep72 of cand_s2 sets."""
    U = np.load(CB.L2 + '/work/inputs.npz')['U']
    has1m = np.load(CB.WORK + '/hourly.npz')['has1m']
    cz = np.load(CM.WORK + '/cand_s2.npz')
    tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    return {s: year_pools(U, has1m, cz[s + '_k'], cz[s + '_c'], tms) for s in sets}, U, has1m


def main():
    CM.require_real(sys.argv)
    nrep = int(sys.argv[sys.argv.index('--nrep') + 1]) if '--nrep' in sys.argv else NREP
    nproc = int(sys.argv[sys.argv.index('--nproc') + 1]) if '--nproc' in sys.argv else 1
    assert nrep >= 100
    G['pools'] = real_pools()[0]
    st = X.Store()
    G['table_fn'] = lambda ck, cc: X.compute(st, ck, cc)
    shard = (0, 1)
    if '--shard' in sys.argv:
        a, b = sys.argv[sys.argv.index('--shard') + 1].split('/')
        shard = (int(a), int(b))
        assert 0 <= shard[0] < shard[1]
    run_reps(CM.SETS, nrep, CM.OUT + '/rand_s2_parts', nproc, shard)
    if len(glob.glob(CM.OUT + '/rand_s2_parts/*.parquet')) < nrep * len(CM.SETS):
        log.info('rand_s2 shard %s done; other shards pending -> no summary yet', shard)
        return
    real = pd.read_parquet(CM.OUT + '/grid_s2.parquet')
    with open(CM.OUT + '/select_s2.json') as fh:
        sel = json.load(fh)
    res = summarize(CM.SETS, CM.OUT + '/rand_s2_parts', real, sel, nrep)
    with open(CM.OUT + '/rand_s2.json', 'w') as fh:
        json.dump(dict(seed=SEED, nrep=nrep, res=res), fh, indent=1)
    log.info('rand_s2 done (CHUA AUDIT)')


if __name__ == '__main__':
    main()
