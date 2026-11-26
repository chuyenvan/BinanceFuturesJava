"""LEVZ T1 random control (PREREG_LEVZ_T1 sec 4 (iii) + MASTER: every family x every gate mode, 100 reps, full family grid, no reduction).
Class W7 E0 zmin 3.0. Rep r: random candidates exactly as B1 rand_b1 (B0 rand.build_pools / draw on the real class episodes; pool =
(coin, hour) in universe with a 1m bar at T_k; s ~ U(0,1)); rng = default_rng([SEED, r]) - the SAME draw for every family and both gate
modes (G_EW14 then masks the random candidates by the gate of their entry hour, as for real ones). Exit tables of the random candidates
are computed with exits_t1.compute (HEDGE also B1 exits.compute for the B1 reference bases). Then the family's full exit grid x K (3, 5, 10)
is run; statistic = max over those configs of the B1 maximin score (B0 select.score_of) + number of valid configs (B0 valid_of).
p = share of reps with max score >= real max score (same family / gate / zmin 3.0 rows of out/grid_t1.parquet).
Order: gate NONE (all families) first, then G_EW14. Resumable: one part file per (fam, gate, rep).
REAL DATA LOCK: python3 code/rand_t1.py --real I_HAVE_A1_PASS [nrep] [FAM ...]"""
import os
import sys
import glob
import json
import logging
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t1 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_t1.rand')
CB = C.CB
P = C.b1('port')
XB1 = C.b1('exits')
E = C.load('exits_t1')
G = C.load('grid_t1')
R0 = CB.load_b0('rand')
SEL0 = CB.load_b0('select')
SEED = 20261128
NREP = 100
ZCLS = 3.0
NPROC = 3
FAMS = ('BRK', 'VOL', 'PART', 'STATE', 'HEDGE')
RC = {}


class RCtx:
    """st (exits Store), pools, CL, conds (STATE), legs, gate_fn(k, c)."""
    pass


def family_cfgs(fam, gate):
    return [c for c in C.all_cfgs() if c['fam'] == fam and c['gate'] == gate and c['zmin'] == ZCLS]


def build_real(flag):
    assert flag == G.LOCK, 'real-data random control locked'
    rc = RCtx()
    Rb1 = C.b1('rand_b1')
    I = Rb1.make_shim()
    cz = np.load(CB.WORK + '/cand_b1.npz')
    rc.pools = R0.build_pools(I, Rb1.real_cand(cz, 7, 'E0', ZCLS))
    rc.st = XB1.Store()
    rc.CL = E.load_CL()
    sig = E.load_sig()
    rc.conds = {zo: E.state_cond(sig, zo) for zo in C.STATE_Z}
    rc.legs = {ins: C.load('hedge_t1').make_legs(ins) for ins in C.HEDGE_INST}
    O = C.b2('opts')
    mk = C.b2('mkt').load()
    g = O.gate_series('G_EW14', mk)
    rc.gate_fn = lambda k, c: O.mask_at('G_EW14', mk, k, c, gate=g)
    return rc


def build_fake(F):
    rc = RCtx()

    class I:
        pass
    I.tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    ns = F.mm.shape[0]
    I.U = np.zeros((CB.NH, ns), dtype=bool)
    I.U[:, 2:] = True
    I.px = {'CL': np.ones((CB.NH, ns))}

    class Real:
        pass
    ck, cc, cs, cid = F.cz[ZCLS]
    Real.ck, Real.cc = ck, cc
    rc.pools = R0.build_pools(I, Real)
    rc.st = XB1.Store(mm=F.mm, gaps=F.gaps, FR=F.FR)
    rc.CL = F.CL
    rc.conds = {zo: E.state_cond(F.sig, zo) for zo in C.STATE_Z}
    rc.legs = {'BTC': [C.load('hedge_t1').Leg(F.mm[0], F.FR[:, 0], 1.0)],
               'BTCETH': [C.load('hedge_t1').Leg(F.mm[0], F.FR[:, 0], 0.5), C.load('hedge_t1').Leg(F.mm[1], F.FR[:, 1], 0.5)]}
    rc.gate_fn = lambda k, c: F.gate[np.asarray(k)]
    return rc


def one_rep(rc, fam, gate, r):
    t0 = time.time()
    rng = np.random.default_rng([SEED, r])
    c0 = R0.draw(rc.pools, rng)
    n = len(c0.ck)
    cid = np.arange(n, dtype=np.int64)
    tf = ('BRK',) if fam == 'HEDGE' else (fam,)
    out = E.compute(rc.st, c0.ck, c0.cc, fams=tf, CL=rc.CL, conds=rc.conds)
    ctx = G.Ctx()
    ctx.T = {f: E.with_hourly(out[f], out['hourly']) for f in tf}
    ctx.Tb1 = XB1.compute(rc.st, c0.ck, c0.cc) if fam == 'HEDGE' else None
    m = np.ones(n, dtype=bool) if gate == 'NONE' else np.asarray(rc.gate_fn(c0.ck, c0.cc), dtype=bool)
    ctx.cand = {(ZCLS, gate): P.CandB1(c0.ck[m], c0.cc[m], c0.cs[m], cid[m])}
    ctx.legs = rc.legs
    G._VC.clear()
    best, bid, nv = -np.inf, None, 0
    for cfg in family_cfgs(fam, gate):
        res = G.run_cfg(ctx, cfg)
        s = SEL0.score_of(res)
        nv += int(SEL0.valid_of(res))
        if s > best:
            best, bid = s, cfg['cfg_id']
    G._VC.clear()
    return dict(fam=fam, gate=gate, rep=r, n_cand=int(n), n_cand_gate=int(m.sum()), max_score=float(best), n_valid=nv,
                best_cfg_id=int(bid), sec=time.time() - t0)


def _work(t):
    return one_rep(RC['rc'], *t)


def run_reps(rc, jobs, parts_dir, nproc=NPROC):
    import multiprocessing as mp
    os.makedirs(parts_dir, exist_ok=True)
    done = set()
    for f in glob.glob(parts_dir + '/*.parquet'):
        d = pd.read_parquet(f, columns=['fam', 'gate', 'rep'])
        done |= set(zip(d['fam'], d['gate'], d['rep']))
    todo = [j for j in jobs if j not in done]
    log.info('rand_t1 todo=%d done=%d', len(todo), len(done))
    RC['rc'] = rc
    t0 = time.time()

    def save(res):
        fn = '%s/part_%s_%s_%03d.parquet' % (parts_dir, res['fam'], res['gate'], res['rep'])
        pd.DataFrame([res]).to_parquet(fn + '.tmp', index=False)
        os.replace(fn + '.tmp', fn)
    if todo:
        if nproc <= 1:
            for i, t in enumerate(todo):
                save(_work(t))
        else:
            with mp.get_context('fork').Pool(nproc) as pool:
                for i, res in enumerate(pool.imap_unordered(_work, todo, chunksize=1)):
                    save(res)
                    log.info('rand_t1 %d/%d %s %s rep %d %.1fs (%.1fs)', i + 1, len(todo), res['fam'], res['gate'], res['rep'],
                             res['sec'], time.time() - t0)
    fs = sorted(glob.glob(parts_dir + '/*.parquet'))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True).drop_duplicates(['fam', 'gate', 'rep'])


def jobs_for(fams, nrep):
    return [(f, g, r) for g in C.GATES for r in range(nrep) for f in fams]


def summarize(rd, grid, fams):
    res = {}
    for fam in fams:
        for g in C.GATES:
            gg = grid[(grid['fam'] == fam) & (grid['gate'] == g) & (grid['zmin'] == ZCLS)]
            if not len(gg):
                continue
            rs = [SEL0.score_of(r) for r in gg.to_dict('records')]
            real = float(max(rs))
            dd = rd[(rd['fam'] == fam) & (rd['gate'] == g)]
            if not len(dd):
                continue
            res['%s|%s' % (fam, g)] = dict(real_max_score=real, real_n_valid=int(sum(SEL0.valid_of(r) for r in gg.to_dict('records'))),
                                           nrep=int(len(dd)), p=float((dd['max_score'] >= real).mean()),
                                           rand_max_q=[float(x) for x in np.quantile(dd['max_score'], [0.05, 0.5, 0.95])],
                                           rand_n_valid_median=float(dd['n_valid'].median()),
                                           label='gate hau kiem' if g == 'G_EW14' else '')
    return res


def main(argv):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if len(argv) < 2 or argv[0] != '--real':
        raise SystemExit('usage: rand_t1.py --real %s [nrep] [FAM ...]' % G.LOCK)
    rc = build_real(argv[1])
    rest = argv[2:]
    nrep = int(rest[0]) if rest and rest[0].isdigit() else NREP
    assert nrep >= 100
    fams = [a for a in rest if not a.isdigit()] or list(FAMS)
    rd = run_reps(rc, jobs_for(fams, nrep), C.OUT + '/rand_t1_parts')
    rd.to_parquet(C.OUT + '/rand_t1.parquet', index=False)
    grid = pd.read_parquet(C.OUT + '/grid_t1.parquet')
    with open(C.OUT + '/rand_t1.json', 'w') as fh:
        json.dump(dict(seed=SEED, zmin=ZCLS, res=summarize(rd, grid, fams)), fh, indent=1)
    log.info('rand_t1 done (CHUA AUDIT)')


if __name__ == '__main__':
    main(sys.argv[1:])
