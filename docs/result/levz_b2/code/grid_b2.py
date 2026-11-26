"""LEVZ B2 step 3 - for each option O: ALL 7 020 B1 configs (grid_b1.all_cfgs, same cfg_id) with B1 port.run_all on the B1 candidate
set filtered by O (opts.py); exit table (levz_b1/work/exits.npz) unchanged. <= 3 fork workers; atomic part files
out/grid_b2_parts/<O>/ => resumable; merged to out/grid_b2_<O>.parquet (same columns as grid_b1; 7 020 unique cfg_id; accounting
invariant asserted via B0 grid.check_acct; and n_trades of every config/fold asserted <= what the candidate set allows: kept cands > 0).
check_none: option NONE on the fixed stratified 300-config sample must reproduce out/grid_b1.parquet EXACTLY (all columns except 'sec').
usage: python3 code/grid_b2.py check_none | <O> [<O> ...] | all"""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2c
sys.path.pop(0)
import glob
import json
import logging
import time
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b2.grid')
CB = b2c.b1('common_b1')
P = b2c.b1('port')
X = b2c.b1('exits')
GB1 = b2c.b1('grid_b1')
O = b2c.b2('opts')
MK = b2c.b2('mkt')
NPROC = 3
SEED300 = 20261126
GRID_B1 = '/home/ubuntu/claude_master/w3/levz_b1/out/grid_b1.parquet'
PARTS = b2c.OUT + '/grid_b2_parts'
G = {}


def all_cfgs():
    return GB1.all_cfgs()


def sample300(cfgs=None, seed=SEED300):
    """fixed sample: 25 configs per stratum W x E x zmin (12 strata), rng seed SEED300, sorted by cfg_id."""
    cfgs = cfgs or all_cfgs()
    rng = np.random.default_rng(seed)
    out = []
    for W, E, z in O.CLASSES:
        ids = [c['cfg_id'] for c in cfgs if c['W'] == W and c['E'] == E and c['zmin'] == z]
        assert len(ids) == 585
        out += sorted(rng.choice(ids, size=25, replace=False).tolist())
    out = sorted(int(i) for i in out)
    assert len(out) == 300 and len(set(out)) == 300
    return out


def classes_for(name, mk=None, cz=None):
    cz = cz if cz is not None else O.load_cz()
    if name != 'NONE':
        mk = mk if mk is not None else MK.load()
    g = O.gate_series(name, mk) if name in O.GATES else None
    return O.filtered_classes(cz, lambda k, c: O.mask_at(name, mk, k, c, gate=g), P)


def work(cfg):
    t0 = time.time()
    cand = G['cand'][(cfg['W'], cfg['E'], cfg['zmin'])]
    xv = P.XView(G['T'], CB.xidx(cfg['SL'], cfg['H'], cfg['arm'], cfg['gap']))
    res = dict(cfg)
    res.update(P.run_all(cfg['K'], cand, xv))
    res['sec'] = time.time() - t0
    return res


def run_option(name, cfgs, parts_dir, nproc=NPROC):
    import multiprocessing as mp
    os.makedirs(parts_dir, exist_ok=True)
    done = set()
    for f in glob.glob(parts_dir + '/*.parquet'):
        done |= set(pd.read_parquet(f, columns=['cfg_id'])['cfg_id'].tolist())
    todo = [c for c in cfgs if c['cfg_id'] not in done]
    log.info('%s todo=%d done=%d', name, len(todo), len(done))
    buf = []
    t0 = time.time()

    def flush():
        if buf:
            fn = '%s/part_%d_%04d.parquet' % (parts_dir, int(time.time() * 1000), buf[0]['cfg_id'])
            pd.DataFrame(buf).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            buf.clear()
    if todo:
        with mp.get_context('fork').Pool(nproc) as pool:
            for i, res in enumerate(pool.imap_unordered(work, todo, chunksize=4)):
                buf.append(res)
                if len(buf) >= 120:
                    flush()
                    log.info('%s %d/%d %.1fs', name, i + 1, len(todo), time.time() - t0)
        flush()
    fs = sorted(glob.glob(parts_dir + '/*.parquet'))
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    return df.sort_values('cfg_id').drop_duplicates('cfg_id').reset_index(drop=True)


def compare_exact(a, b, skip=('sec',)):
    """row-aligned exact comparison; returns (n_rows_identical, list of differing columns)."""
    assert list(a['cfg_id']) == list(b['cfg_id'])
    cols = [c for c in b.columns if c not in skip]
    assert set(cols) <= set(a.columns), set(cols) - set(a.columns)
    same = np.ones(len(a), dtype=bool)
    bad = []
    for c in cols:
        x, y = a[c].values, b[c].values
        if x.dtype.kind in 'fc' or y.dtype.kind in 'fc':
            x, y = x.astype(np.float64), y.astype(np.float64)
            eq = (x == y) | (np.isnan(x) & np.isnan(y))
        else:
            eq = x == y
        if not eq.all():
            bad.append(c)
        same &= eq
    return int(same.sum()), bad


def check_none(nproc=1):
    G2 = CB.load_b0('grid')
    G['T'] = X.load_table()
    G['cand'], cnt = classes_for('NONE')
    cz = O.load_cz()
    for (W, E, z), cb in G['cand'].items():
        ref = P.load_class(cz, W, E, z)
        assert all((getattr(cb, a) == getattr(ref, a)).all() for a in ('ck', 'cc', 'cs', 'cid')) and cb.by_k == ref.by_k
    ids = set(sample300())
    cfgs = [c for c in all_cfgs() if c['cfg_id'] in ids]
    import shutil
    import tempfile
    pdir = tempfile.mkdtemp(prefix='check300_', dir=b2c.WORK)     # fresh every time (no resume from old parts)
    try:
        df = run_option('NONE', cfgs, pdir, nproc=nproc)
    finally:
        shutil.rmtree(pdir)
    assert len(df) == 300
    G2.check_acct(df)
    ref = pd.read_parquet(GRID_B1)
    ref = ref[ref['cfg_id'].isin(ids)].sort_values('cfg_id').reset_index(drop=True)
    nsame, bad = compare_exact(df, ref)
    res = dict(n=300, identical=nsame, differing_cols=bad, sec_mean=float(df['sec'].mean()), PASS=bool(nsame == 300 and not bad))
    with open(b2c.OUT + '/check_none.json', 'w') as fh:
        json.dump(res, fh, indent=1)
    log.info('check_none identical=%d/300 bad_cols=%s PASS=%s sec/cfg=%.4f', nsame, bad, res['PASS'], res['sec_mean'])
    assert res['PASS'], 'NONE does not reproduce grid_b1'
    return res


def main(names):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if names == ['check_none']:
        check_none()
        return
    if names == ['all']:
        names = list(O.OPTS)
    for n in names:
        assert n in O.OPTS, n
    G2 = CB.load_b0('grid')
    G['T'] = X.load_table()
    mk = MK.load()
    cz = O.load_cz()
    cfgs = all_cfgs()
    for name in names:
        fn = '%s/grid_b2_%s.parquet' % (b2c.OUT, name)
        if os.path.exists(fn):
            log.info('%s exists, skip', fn)
            continue
        G['cand'], cnt = classes_for(name, mk, cz)
        log.info('%s kept cands per class: %s', name, {O.class_key(*k): v for k, v in cnt.items()})
        df = run_option(name, cfgs, '%s/%s' % (PARTS, name))
        assert len(df) == 7020 and df['cfg_id'].tolist() == list(range(7020))
        G2.check_acct(df)
        df['opt'] = name
        df.to_parquet(fn + '.tmp', index=False)
        os.replace(fn + '.tmp', fn)
        log.info('%s done n=%d', name, len(df))


if __name__ == '__main__':
    main(sys.argv[1:])
