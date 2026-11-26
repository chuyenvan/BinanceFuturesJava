"""LEVZ B1 grid (PREREG_LEVZ_B1 sec 3): exactly 7 020 configs, cfg_id = index in itertools.product order
W, E, zmin, K, SL, H, trail (13: off, then arm x gap). Each config: DEV + F1/F2/F3 (independent from 10 000) via port.run_all.
<= 3 fork workers (exit table shared copy-on-write); atomic part files out/grid_b1_parts/ => resumable; merged to
out/grid_b1.parquet (7 020 unique cfg_id asserted; accounting invariant asserted for DEV/F1/F2/F3 via B0 grid.check_acct).
usage: python3 code/grid_b1.py"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]
import glob
import itertools
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

log = logging.getLogger('levz_b1.grid')
PARTS = CB.OUT + '/grid_b1_parts'
NPROC = 3
GRID = dict(W=(14, 7), E=('E0', 'E1'), zmin=(2.5, 3.0, 3.5), K=(3, 5, 10), SL=CB.SLS, H=CB.HS)
PKEYS = ('W', 'E', 'zmin', 'K', 'SL', 'H', 'arm', 'gap')
G = {}


def all_cfgs():
    res = []
    for i, v in enumerate(itertools.product(GRID['W'], GRID['E'], GRID['zmin'], GRID['K'], GRID['SL'], GRID['H'], CB.TRAILS)):
        W, E, z, K, sl, hh, (a, g) = v
        res.append(dict(cfg_id=i, W=W, E=E, zmin=z, K=K, SL=sl, H=hh, arm=a, gap=g))
    assert len(res) == 7020
    return res


def work(cfg):
    t0 = time.time()
    cand = G['cand'][(cfg['W'], cfg['E'], cfg['zmin'])]
    xv = P.XView(G['T'], CB.xidx(cfg['SL'], cfg['H'], cfg['arm'], cfg['gap']))
    res = dict(cfg)
    res.update(P.run_all(cfg['K'], cand, xv))
    res['sec'] = time.time() - t0
    return res


def main():
    import multiprocessing as mp
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    G2 = CB.load_b0('grid')
    G['T'] = X.load_table()
    cz = np.load(CB.WORK + '/cand_b1.npz')
    G['cand'] = {(W, E, z): P.load_class(cz, W, E, z) for W in GRID['W'] for E in GRID['E'] for z in GRID['zmin']}
    os.makedirs(PARTS, exist_ok=True)
    done = set()
    for f in glob.glob(PARTS + '/*.parquet'):
        done |= set(pd.read_parquet(f, columns=['cfg_id'])['cfg_id'].tolist())
    todo = [c for c in all_cfgs() if c['cfg_id'] not in done]
    log.info('grid_b1 todo=%d done=%d', len(todo), len(done))
    buf = []
    t0 = time.time()

    def flush():
        if buf:
            fn = '%s/part_%d_%04d.parquet' % (PARTS, int(time.time() * 1000), buf[0]['cfg_id'])
            pd.DataFrame(buf).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            buf.clear()
    with mp.get_context('fork').Pool(NPROC) as pool:
        for i, res in enumerate(pool.imap_unordered(work, todo, chunksize=4)):
            buf.append(res)
            if len(buf) >= 60:
                flush()
                log.info('grid_b1 %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
    flush()
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(PARTS + '/*.parquet'))], ignore_index=True)
    df = df.sort_values('cfg_id').drop_duplicates('cfg_id')
    assert len(df) == 7020
    G2.check_acct(df)
    df.to_parquet(CB.OUT + '/grid_b1.parquet', index=False)
    log.info('grid_b1 done n=%d', len(df))


if __name__ == '__main__':
    main()
