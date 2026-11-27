"""LEVZ T2 grid (PREREG_LEVZ_T2 sec 3 + ADD1 M2): 13 293 configs = entry (7) x zmin (3) x K (3) x exit (211), each DEV + F1/F2/F3 from
10 000 via B1 port.run_all UNCHANGED. Per entry type e: candidate class (W7_E0, zmin) restricted to the candidates FILLED for e;
port candidate = (hour kb = floor(m / 60), coin, s = original signal score, cid = row of exits_t2_<e>) => decisions / slot / size /
cooldown at hour kb; unfilled (waiting) candidates never occupy a slot. Exits = exits_t2 views (B1 / STATE: port.XView, PART:
exits_t1.PartView). Fold membership by entry hour kb (port filters k0 <= kb < kl).
Resumable (atomic part files out/grid_t2_parts), --shard i/n (task index % n == i), --entries E0,EL_1,... (subset).
REAL DATA LOCK: python3 code/grid_t2.py --real I_HAVE_A1_PASS [--shard i/n] [--nproc 3] [--entries ...]
Fake / test: run_grid(build_ctx(tables, en, cz), cfgs, parts_dir)."""
import glob
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = C.setup_log('grid')
CB = C.CB
P = C.b1('port')
XT = C.load('exits_t2')
PARTS = C.OUT + '/grid_t2_parts'
CTX = {}


class Ctx:
    """TT[e] = exits_t2.tables(...), cand[(e, zmin)] = CandB1."""
    pass


def classes_for(t, cls):
    """t: exit table of one entry type (needs cid_b1, kb, c rows); cls: {zmin: (k, c, s, cid_b1)} -> {zmin: CandB1}."""
    pos = {int(x): i for i, x in enumerate(t['cid_b1'])}
    out = {}
    for z, (ck, cc, cs, cid) in cls.items():
        rows = np.array([pos.get(int(x), -1) for x in cid], dtype=np.int64)
        ok = rows >= 0
        r = rows[ok]
        assert (t['c'][r] == cc[ok]).all() and (t['k'][r] == ck[ok]).all()
        out[z] = P.CandB1(t['kb'][r].astype(np.int64), cc[ok], cs[ok], r)
    return out


def build_ctx(tabs, cls, entries=C.ENTRIES):
    """tabs: {e: raw exit table dict (exits_t2.compute output + k, cid_b1)}; cls: cand classes {zmin: (k, c, s, cid_b1)}."""
    ctx = Ctx()
    ctx.TT, ctx.cand = {}, {}
    for e in entries:
        ctx.TT[e] = XT.tables(tabs[e])
        for z, cb in classes_for(tabs[e], cls).items():
            ctx.cand[(e, z)] = cb
    return ctx


def build_real(flag, entries=C.ENTRIES):
    assert flag == C.REAL_KEY, 'real-data grid locked: needs --real %s (after A1 PASS)' % C.REAL_KEY
    cls = C.cand_classes()[0]
    return build_ctx({e: XT.load_table(e) for e in entries}, cls, entries)


_VC = {}


def xview(ctx, e, xfam, xi):
    key = (id(ctx), e, xfam, int(xi))
    if key not in _VC:
        _VC.clear()                       # one view at a time (PartView is large); tasks are ordered by exit
        _VC[key] = XT.view(ctx.TT[e], xfam, xi)
    return _VC[key]


def run_cfg(ctx, cfg):
    t0 = time.time()
    r = P.run_all(int(cfg['K']), ctx.cand[(cfg['entry'], float(cfg['zmin']))], xview(ctx, cfg['entry'], cfg['xfam'], cfg['xi']))
    res = dict(cfg)
    res.update(r)
    res['sec'] = time.time() - t0
    return res


def _work(cfg):
    return run_cfg(CTX['ctx'], cfg)


def task_order(cfgs):
    """group by (entry, exit) so a worker reuses its view; deterministic."""
    return sorted(cfgs, key=lambda d: (C.ENTRIES.index(d['entry']), C.XFAMS.index(d['xfam']), d['xi'], d['zmin'], d['K']))


def run_grid(ctx, cfgs, parts_dir, nproc=3, shard=(0, 1), merge=True):
    import multiprocessing as mp
    os.makedirs(parts_dir, exist_ok=True)
    done = set()
    for f in glob.glob(parts_dir + '/*.parquet'):
        done |= set(pd.read_parquet(f, columns=['cfg_id'])['cfg_id'].tolist())
    allt = task_order(cfgs)
    todo = [c for i, c in enumerate(allt) if i % shard[1] == shard[0] and c['cfg_id'] not in done]
    log.info('grid_t2 todo=%d done=%d shard=%s', len(todo), len(done), shard)
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
        pool = None
        if nproc <= 1:
            it = map(_work, todo)
        else:
            pool = mp.get_context('fork').Pool(nproc)
            it = pool.imap(_work, todo, chunksize=9)
        try:
            for i, res in enumerate(it):
                buf.append(res)
                if len(buf) >= 120:
                    flush()
                    log.info('grid_t2 %d/%d %.1fs', i + 1, len(todo), time.time() - t0)
        finally:
            if pool is not None:
                pool.close()
                pool.join()
        flush()
    if not merge:
        return None
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(parts_dir + '/*.parquet'))], ignore_index=True)
    df = df.sort_values('cfg_id').drop_duplicates('cfg_id').reset_index(drop=True)
    CB.load_b0('grid').check_acct(df)
    return df


def main(argv):
    C.require_real(argv)
    entries = tuple(argv[argv.index('--entries') + 1].split(',')) if '--entries' in argv else C.ENTRIES
    nproc = int(argv[argv.index('--nproc') + 1]) if '--nproc' in argv else 3
    shard = C.shard_arg(argv)
    ctx = build_real(argv[argv.index('--real') + 1], entries)
    cfgs = C.all_cfgs(entries)
    df = run_grid(ctx, cfgs, PARTS, nproc, shard)
    if len(df) == C.N_TOTAL:
        df.to_parquet(C.OUT + '/grid_t2.parquet.tmp', index=False)
        os.replace(C.OUT + '/grid_t2.parquet.tmp', C.OUT + '/grid_t2.parquet')
        log.info('grid_t2 done n=%d (CHUA AUDIT)', len(df))
    else:
        log.info('grid_t2 partial n=%d / %d (other shards / entries pending)', len(df), C.N_TOTAL)


if __name__ == '__main__':
    main(sys.argv[1:])
