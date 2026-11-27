"""LEVZ B4 grid (PREREG_X3_1127 A4): 540 cfgs = 60 exit cfgs (DCA x SL x exit x H) x zmin (3) x K (3), each DEV + F1 / F2 / F3 via B1
port.run_all UNCHANGED (exits_b4.view = port.XView with the DCA kind's effective hourly arrays). Candidate class W7_E0 zmin of cand_b1;
port cid = row of exits_b4 table (rows = sorted union ucid).
REAL DATA LOCK: python3 code/grid_b4.py --real I_HAVE_A1_PASS [--nproc 2]          -> out/grid_b4.parquet
FAKE (end-to-end test): python3 code/grid_b4.py --fake pump|rand --seed S [--nproc 1] -> out/fake/grid_<kind>_<S>.parquet"""
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_b4 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = C.setup_log('grid')
CB = C.CB
P = C.b1('port')
X = C.load('exits_b4')
CTX = {}


class Ctx:
    pass


def make_ctx(T, HK, cls):
    """cls: {zmin: (k, c, s, row)} with row = index into T."""
    ctx = Ctx()
    ctx.T, ctx.HK, ctx.cand = T, HK, {}
    for z, (ck, cc, cs, rr) in cls.items():
        rr = np.asarray(rr, dtype=np.int64)
        assert (T['k'][rr] == ck).all() and (T['c'][rr] == cc).all()
        ctx.cand[float(z)] = P.CandB1(np.asarray(ck, dtype=np.int64), np.asarray(cc), np.asarray(cs), rr)
    return ctx


def build_real(flag):
    assert flag == C.REAL_KEY, 'real-data grid locked: needs --real %s (after A1 PASS)' % C.REAL_KEY
    cls, ucid, uk, uc = C.cand_classes()
    T, HK = X.load_table(ucid=ucid)
    assert np.array_equal(T['ucid'], ucid)
    cl2 = {z: (k, c, s, np.searchsorted(ucid, cid)) for z, (k, c, s, cid) in cls.items()}
    return make_ctx(T, HK, cl2)


def build_fake(kind, seed):
    F = C.load('fake_b4')
    T, HK, cls = F.build(kind, seed)
    return make_ctx(T, HK, cls)


_VC = {}


def xview(ctx, xi):
    key = (id(ctx), int(xi))
    if key not in _VC:
        _VC.clear()
        _VC[key] = X.view(ctx.T, ctx.HK, int(xi))
    return _VC[key]


def run_cfg(ctx, cfg):
    t0 = time.time()
    r = P.run_all(int(cfg['K']), ctx.cand[float(cfg['zmin'])], xview(ctx, cfg['xi']))
    res = dict(cfg)
    res.update(r)
    res['sec'] = time.time() - t0
    return res


def _work(cfg):
    return run_cfg(CTX['ctx'], cfg)


def run_grid(ctx, cfgs=None, nproc=1):
    import multiprocessing as mp
    cfgs = C.all_cfgs() if cfgs is None else cfgs
    todo = sorted(cfgs, key=lambda d: (d['xi'], d['zmin'], d['K']))
    CTX['ctx'] = ctx
    t0 = time.time()
    if nproc <= 1:
        res = list(map(_work, todo))
    else:
        with mp.get_context('fork').Pool(nproc) as pool:
            res = list(pool.imap(_work, todo, chunksize=9))
    df = pd.DataFrame(res).sort_values('cfg_id').reset_index(drop=True)
    CB.load_b0('grid').check_acct(df)
    log.info('grid_b4 n=%d %.1fs', len(df), time.time() - t0)
    return df


def main(argv):
    nproc = int(argv[argv.index('--nproc') + 1]) if '--nproc' in argv else 1
    if '--fake' in argv:
        kind, seed = argv[argv.index('--fake') + 1], int(argv[argv.index('--seed') + 1])
        os.makedirs(C.OUT + '/fake', exist_ok=True)
        df = run_grid(build_fake(kind, seed), nproc=nproc)
        df.to_parquet(C.OUT + '/fake/grid_%s_%d.parquet' % (kind, seed), index=False)
        return
    C.require_real(argv)
    df = run_grid(build_real(argv[argv.index('--real') + 1]), nproc=nproc)
    assert len(df) == C.N_TOTAL
    df.to_parquet(C.OUT + '/grid_b4.parquet.tmp', index=False)
    os.replace(C.OUT + '/grid_b4.parquet.tmp', C.OUT + '/grid_b4.parquet')
    log.info('grid_b4 done n=%d (CHUA AUDIT)', len(df))


if __name__ == '__main__':
    main(sys.argv[1:])
