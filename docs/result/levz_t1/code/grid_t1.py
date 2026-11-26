"""LEVZ T1 grid (PREREG_LEVZ_T1 sec 3 + ADD1): 9 468 configs = family x exit cfg x zmin x K x gate (W7 E0), each DEV + F1/F2/F3 from
10 000 via B1 port.run_all (BRK / VOL / PART / STATE; exit tables of exits_t1) or hedge_t1.run_all (HEDGE). Output columns = grid_b1
fold columns + family parameter columns. Gate G_EW14 = B2 opts.mask_at (unchanged) on the W7 E0 candidate classes.
REAL DATA LOCK: python3 code/grid_t1.py --real I_HAVE_A1_PASS [FAM ...]   (refuses otherwise)
FAKE (pipeline test f): grid_t1.run_grid(ctx, cfgs, out_path) with ctx = build_fake(fake_t1.make(...))."""
import os
import sys
import glob
import logging
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t1 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_t1.grid')
CB = C.CB
P = C.b1('port')
XB1 = C.b1('exits')
E = C.load('exits_t1')
HG = C.load('hedge_t1')
NPROC = 3
LOCK = 'I_HAVE_A1_PASS'
CTX = {}


class Ctx:
    """T[fam] (exit table + hourly), Tb1 (B1 exit table), cand[(zmin, gate)] = CandB1, legs[inst]."""
    pass


def classes_from(cz, gate_fn):
    out = {}
    for z in C.ZS:
        ck, cc, cs, cid = cz[z]
        out[(z, 'NONE')] = P.CandB1(ck, cc, cs, cid)
        m = np.asarray(gate_fn(ck, cc), dtype=bool)
        out[(z, 'G_EW14')] = P.CandB1(ck[m], cc[m], cs[m], cid[m])
    return out


def build_real(flag):
    assert flag == LOCK, 'real-data grid locked: needs --real %s (after A1 PASS)' % LOCK
    ctx = Ctx()
    zt = XB1.load_table()
    hourly = {kk: zt[kk] for kk in ('mk', 'hm', 'fh', 'fc', 'p0')}
    ctx.Tb1 = zt
    ctx.T = {f: E.load_family(f, hourly) for f in E.FAMS}
    for f in E.FAMS:
        assert (ctx.T[f]['k'] == zt['k']).all() and (ctx.T[f]['c'] == zt['c']).all()
    czf = np.load(CB.WORK + '/cand_b1.npz')
    cz = {z: tuple(czf['W7_E0_%.1f_%s' % (z, s)] for s in ('k', 'c', 's', 'cid')) for z in C.ZS}
    O = C.b2('opts')
    MK = C.b2('mkt')
    mk = MK.load()
    g = O.gate_series('G_EW14', mk)
    ctx.cand = classes_from(cz, lambda k, c: O.mask_at('G_EW14', mk, k, c, gate=g))
    ctx.legs = {ins: HG.make_legs(ins) for ins in C.HEDGE_INST}
    return ctx


def build_fake(F):
    ctx = Ctx()
    st = XB1.Store(mm=F.mm, gaps=F.gaps, FR=F.FR)
    out = E.compute(st, F.U_k, F.U_c, CL=F.CL, sig=F.sig)
    ctx.T = {f: E.with_hourly(out[f], out['hourly']) for f in E.FAMS}
    ctx.Tb1 = XB1.compute(st, F.U_k, F.U_c)
    ctx.cand = classes_from(F.cz, lambda k, c: F.gate[k])
    ctx.legs = {'BTC': [HG.Leg(F.mm[0], F.FR[:, 0], 1.0)],
                'BTCETH': [HG.Leg(F.mm[0], F.FR[:, 0], 0.5), HG.Leg(F.mm[1], F.FR[:, 1], 0.5)]}
    return ctx


_VC = {}


def xview(ctx, fam, xi):
    """cached view (PART views are large: cache only the last one)."""
    key = (id(ctx), fam, xi)
    if key not in _VC:
        if fam == 'PART':
            for kk in [kk for kk in _VC if kk[1] == 'PART']:
                del _VC[kk]
        _VC[key] = E.view(fam, ctx.T[fam], xi) if fam != 'B1' else P.XView(ctx.Tb1, xi)
    return _VC[key]


def run_cfg(ctx, cfg):
    t0 = time.time()
    cand = ctx.cand[(cfg['zmin'], cfg['gate'])]
    if cfg['fam'] == 'HEDGE':
        X = xview(ctx, cfg['base'], cfg['bxi'])
        r = HG.run_all(cfg['K'], cand, X, cfg['h'], ctx.legs[cfg['inst']])
    else:
        r = P.run_all(cfg['K'], cand, xview(ctx, cfg['fam'], cfg['xi']))
    res = dict(cfg)
    res.update(r)
    res['sec'] = time.time() - t0
    return res


def _work(cfg):
    return run_cfg(CTX['ctx'], cfg)


def run_grid(ctx, cfgs, parts_dir, nproc=NPROC):
    """resumable (atomic part files); returns merged DataFrame sorted by cfg_id."""
    import multiprocessing as mp
    os.makedirs(parts_dir, exist_ok=True)
    done = set()
    for f in glob.glob(parts_dir + '/*.parquet'):
        done |= set(pd.read_parquet(f, columns=['cfg_id'])['cfg_id'].tolist())
    todo = [c for c in cfgs if c['cfg_id'] not in done]
    log.info('grid_t1 todo=%d done=%d', len(todo), len(done))
    CTX['ctx'] = ctx
    buf = []
    t0 = time.time()

    def flush():
        if buf:
            fn = '%s/part_%d_%05d.parquet' % (parts_dir, int(time.time() * 1000), buf[0]['cfg_id'])
            pd.DataFrame(buf).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            buf.clear()
    if todo:
        if nproc <= 1:
            it = map(_work, todo)
            pool = None
        else:
            pool = mp.get_context('fork').Pool(nproc)
            it = pool.imap(_work, todo, chunksize=4)
        try:
            for i, res in enumerate(it):
                buf.append(res)
                if len(buf) >= 120:
                    flush()
                    log.info('grid_t1 %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
        finally:
            if pool is not None:
                pool.close()
                pool.join()
        flush()
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(parts_dir + '/*.parquet'))], ignore_index=True)
    df = df.sort_values('cfg_id').drop_duplicates('cfg_id').reset_index(drop=True)
    C.CB.load_b0('grid').check_acct(df)
    return df


def main(argv):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if len(argv) < 2 or argv[0] != '--real':
        raise SystemExit('usage: grid_t1.py --real %s [FAM ...]  (real data only after A1 PASS)' % LOCK)
    ctx = build_real(argv[1])
    fams = argv[2:] or ['BRK', 'VOL', 'PART', 'STATE', 'HEDGE']
    cfgs = [c for c in C.all_cfgs() if c['fam'] in fams]
    df = run_grid(ctx, cfgs, C.OUT + '/grid_t1_parts')
    if set(fams) == {'BRK', 'VOL', 'PART', 'STATE', 'HEDGE'}:
        assert len(df) == C.n_total()
    df.to_parquet(C.OUT + '/grid_t1.parquet.tmp', index=False)
    os.replace(C.OUT + '/grid_t1.parquet.tmp', C.OUT + '/grid_t1.parquet')
    log.info('grid_t1 done n=%d (CHUA AUDIT)', len(df))


if __name__ == '__main__':
    main(sys.argv[1:])
