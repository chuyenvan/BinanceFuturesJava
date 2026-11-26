"""LEVZ S2 step 3: grid (PREREG_LEVZ_S2 sec 3): 5 sets x K {3,5,10} x 195 B1 exit configs = 2 925 configs, cfg_id = index in
itertools.product(set, K, SL, H, trail) order. Each config: B1 port.run (NOT modified) on folds DEV, Y22, Y23, Y24, Y25 (each from
10 000; fold end kl = start of next period - 1 h, as B1 run_all). Columns <fold>_<B0 metric> as grid_b1. Resumable parts.
LOCKED: real data only with --real I_HAVE_A1_PASS.  usage: python3 code/grid_s2.py --real I_HAVE_A1_PASS [--nproc N]"""
import glob
import itertools
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
S = P.S
log = CM.setup_log('grid_s2')
PKEYS = ('set', 'K', 'SL', 'H', 'arm', 'gap')
FOLDN = tuple(f[0] for f in CM.YFOLDS)
FB = [(n, S.kidx(S.ms(a)), S.kidx(S.ms(b)) - 1) for n, a, b in CM.YFOLDS]
G = {}


def all_cfgs(sets=CM.SETS):
    res = []
    for i, v in enumerate(itertools.product(sets, CM.KS, CB.SLS, CB.HS, CB.TRAILS)):
        s, K, sl, hh, (a, g) = v
        res.append(dict(cfg_id=i, set=s, K=K, SL=sl, H=hh, arm=a, gap=g))
    return res


def run_cfg(cfg, cand, T, folds=FOLDN):
    xv = P.XView(T, CB.xidx(cfg['SL'], cfg['H'], cfg['arm'], cfg['gap']))
    res = dict(cfg)
    for name, k0, kl in FB:
        if name not in folds:
            continue
        tr, eq, m = P.run(int(cfg['K']), cand, xv, k0, kl)
        for kk, v in m.items():
            res['%s_%s' % (name, kk)] = v
    return res


def load_cands(path, sets=CM.SETS):
    cz = np.load(path)
    return {s: P.CandB1(cz[s + '_k'], cz[s + '_c'], cz[s + '_s'], cz[s + '_cid']) for s in sets}


def check_acct(df, tol=1e-6):
    """B0 grid.check_acct invariant (sum trade PnL = equity change) on the S2 fold names."""
    for f in FOLDN:
        v = df[f + '_acct_err'].abs().max()
        assert v <= tol, 'accounting invariant broken in %s: %r' % (f, v)


def grid_df(cands, T, cfgs):
    return pd.DataFrame([run_cfg(c, cands[c['set']], T) for c in cfgs])


def _work(cfg):
    t0 = time.time()
    r = run_cfg(cfg, G['cands'][cfg['set']], G['T'])
    r['sec'] = time.time() - t0
    return r


def run_grid(cands, T, parts, out_path, sets, nproc=1):
    G['cands'], G['T'] = cands, T
    os.makedirs(parts, exist_ok=True)
    done = set()
    for f in glob.glob(parts + '/*.parquet'):
        done |= set(pd.read_parquet(f, columns=['cfg_id'])['cfg_id'].tolist())
    cfgs = all_cfgs(sets)
    todo = [c for c in cfgs if c['cfg_id'] not in done]
    log.info('grid_s2 todo=%d done=%d', len(todo), len(done))
    buf = []
    t0 = time.time()

    def flush():
        if buf:
            fn = '%s/part_%d_%04d.parquet' % (parts, int(time.time() * 1000), buf[0]['cfg_id'])
            pd.DataFrame(buf).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            buf.clear()
    if nproc <= 1:
        it = map(_work, todo)
    else:
        import multiprocessing as mp
        pool = mp.get_context('fork').Pool(nproc)
        it = pool.imap_unordered(_work, todo, chunksize=4)
    for i, res in enumerate(it):
        buf.append(res)
        if len(buf) >= 60:
            flush()
            log.info('grid_s2 %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
    flush()
    if nproc > 1:
        pool.close()
        pool.join()
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(parts + '/*.parquet'))], ignore_index=True)
    df = df.sort_values('cfg_id').drop_duplicates('cfg_id').reset_index(drop=True)
    assert len(df) == len(cfgs)
    check_acct(df)
    df.to_parquet(out_path, index=False)
    log.info('grid_s2 done n=%d -> %s', len(df), out_path)
    return df


def main():
    CM.require_real(sys.argv)
    nproc = int(sys.argv[sys.argv.index('--nproc') + 1]) if '--nproc' in sys.argv else 1
    T = X.load_table(CM.WORK + '/exits_s2.npz')
    cands = load_cands(CM.WORK + '/cand_s2.npz')
    assert len(all_cfgs()) == 2925
    run_grid(cands, T, CM.OUT + '/grid_s2_parts', CM.OUT + '/grid_s2.parquet', CM.SETS, nproc)


if __name__ == '__main__':
    main()
