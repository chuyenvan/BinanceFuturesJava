"""LEVZ2 grid (PREREG_LEVZ2 sec 3): exactly 1 296 configs (sim.all_cfgs, fixed order => cfg_id), each run on DEV + F1/F2/F3
(independent, from 10 000). <= 3 worker processes (fork, inputs shared copy-on-write). Results are appended in small atomic
part files (out/grid_parts/) => resumable; at the end merged to out/grid.parquet (1 296 unique cfg_id asserted).
usage: python3 code/grid.py"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]  # code/select.py must not shadow stdlib select
import glob
import importlib.util
import logging
import time
sys.dont_write_bytecode = True
import pandas as pd

log = logging.getLogger('levz2.grid')
BASE = '/home/ubuntu/claude_master/w3/levz2'
PARTS = BASE + '/out/grid_parts'
NPROC = 3


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
G = {}


def check_acct(df, tol=1e-6):
    """ADDENDUM2 G5: accounting invariant (sum trade PnL = equity change) for DEV, F1, F2, F3."""
    for f in ('DEV', 'F1', 'F2', 'F3'):
        v = df[f + '_acct_err'].abs().max()
        assert v <= tol, 'accounting invariant broken in %s: %r' % (f, v)


def work(cfg):
    t0 = time.time()
    res = dict(cfg)
    res.update(S.run_all(cfg, G['I']))
    res['sec'] = time.time() - t0
    return res


def main():
    import multiprocessing as mp
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    G['I'] = S.load_inputs()
    os.makedirs(PARTS, exist_ok=True)
    done = set()
    for f in glob.glob(PARTS + '/*.parquet'):
        done |= set(pd.read_parquet(f, columns=['cfg_id'])['cfg_id'].tolist())
    todo = [c for c in S.all_cfgs() if c['cfg_id'] not in done]
    log.info('grid todo=%d done=%d', len(todo), len(done))
    buf = []
    t0 = time.time()

    def flush():
        if buf:
            fn = '%s/part_%d_%04d.parquet' % (PARTS, int(time.time() * 1000), buf[0]['cfg_id'])
            pd.DataFrame(buf).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            buf.clear()
    with mp.get_context('fork').Pool(NPROC) as pool:
        for i, res in enumerate(pool.imap_unordered(work, todo, chunksize=2)):
            buf.append(res)
            if len(buf) >= 24:
                flush()
                log.info('grid %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
    flush()
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(PARTS + '/*.parquet'))], ignore_index=True)
    df = df.sort_values('cfg_id').drop_duplicates('cfg_id')
    assert len(df) == 1296
    check_acct(df)
    df.to_parquet(BASE + '/out/grid.parquet', index=False)
    log.info('grid done n=%d', len(df))


if __name__ == '__main__':
    main()
