"""LEVZ B2 step 5 - placebo (PREREG_LEVZ_B2 sec 4e), ONLY for an option given on the command line that passed (a)-(d) in
out/report_b2.json (refused otherwise unless --force, which is for tests and is logged).
Fixed sample: grid_b2.sample300() (seed 20261126; 25 configs per W x E x zmin stratum). Statistic = fraction of the 300 configs with
F2 ret > 0 (F2 fold only, B1 port.run). Real value = same routine with the real mask (cross-checked == grid_b2_<O>.parquet F2_ret).
Placebo r (r = 0..nrep-1, rng = default_rng([SEED_PL, index of O in OPTS, r])): GATE -> gate series circularly shifted by
d ~ U{720 .. NH-720} h; FILTER -> per-month coin permutation (opts.placebo_mask). p = #(stat_r >= stat_real) / nrep;
PASS if p <= 0.05 / 12. FILTER (ADDENDUM1 B): exclusion rate on the pooled candidate set of the 12 classes per draw; a draw
deviating > 20 % (relative) from the real rate is redrawn from the same rng stream (n_redraw recorded per run and in total). <= 3 fork workers; one json per run in out/placebo_b2_<O>/ => resumable.
usage: python3 code/placebo_b2.py <O> [nrep=500] [--force]"""
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

log = logging.getLogger('levz_b2.placebo')
GR = b2c.b2('grid_b2')
O = GR.O
P = GR.P
X = GR.X
CB = GR.CB
SEED_PL = 20261128
NREP = 500
ALPHA = 0.05 / 12
NPROC = 3
G = {}


def f2_bounds():
    S = P.S
    for name, a, b in S.FOLDS:
        if name == 'F2':
            return S.kidx(S.ms(a)), S.kidx(S.ms(b)) - 1
    raise KeyError('F2')


def stat_for(classes, cfgs, T):
    k0, kl = f2_bounds()
    rets = []
    for cfg in cfgs:
        cand = classes[(cfg['W'], cfg['E'], cfg['zmin'])]
        xv = P.XView(T, CB.xidx(cfg['SL'], cfg['H'], cfg['arm'], cfg['gap']))
        _, _, m = P.run(cfg['K'], cand, xv, k0, kl)
        rets.append(m['ret'])
    rets = np.array(rets)
    return float((rets > 0).mean()), rets


def one_rep(r):
    name = G['name']
    rng = np.random.default_rng([SEED_PL, O.OPTS.index(name), int(r)])
    if name in O.GATES:
        # ONE shift per placebo run, shared by all classes
        d = O.draw_shift(rng, len(G['g']))
        gs = O.gate_shift(G['g'], d)
        classes, cnt = O.filtered_classes(G['cz'], lambda k, c: gs[k], P)
        info = dict(shift=d, open_frac=float(gs.mean()))
    else:
        # ONE coin permutation per month per placebo run, shared by all classes; ADDENDUM1 B: redraw if the pooled exclusion rate on the
        # candidate set deviates > 20 % (relative) from the real one
        def ex_fn(mp):
            m = O.filter_at(name, G['mk'], G['pk'], mp[G['mid'][G['pk']], G['pc']])
            return 1.0 - float(m.mean())
        mp, ex, nred = O.draw_filter_perm(G['U'], G['mid'], rng, ex_fn, G['real_ex'])
        classes, cnt = O.filtered_classes(G['cz'], lambda k, c: O.filter_at(name, G['mk'], k, mp[G['mid'][k], c]), P)
        info = dict(ex_rate=ex, n_redraw=int(nred), moved_coins=int((mp != np.arange(mp.shape[1])[None, :]).sum()))
    st, rets = stat_for(classes, G['cfgs'], G['T'])
    kept = sum(v[1] for v in cnt.values()) / max(sum(v[0] for v in cnt.values()), 1)
    res = dict(r=int(r), stat=st, kept_frac=kept, **info)
    fn_out = '%s/run_%04d.json' % (G['dir'], r)
    with open(fn_out + '.tmp', 'w') as fh:
        json.dump(res, fh)
    os.replace(fn_out + '.tmp', fn_out)
    return res


def main(argv):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    name = argv[0]
    assert name in O.OPTS, name
    nrep = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else NREP
    force = '--force' in argv
    rp = b2c.OUT + '/report_b2.json'
    ok = False
    if os.path.exists(rp):
        with open(rp) as fh:
            ok = bool(json.load(fh)['opts'].get(name, {}).get('criteria', {}).get('pass_a_to_d', False))
    if not ok:
        assert force, '%s did not pass (a)-(d) in report_b2.json: placebo not allowed (prereg 4e)' % name
        log.warning('--force: running placebo for %s WITHOUT (a)-(d) pass (test use only)', name)
    import multiprocessing as mp
    G['name'] = name
    G['T'] = X.load_table()
    G['mk'] = GR.MK.load()
    G['cz'] = O.load_cz()
    G['U'] = np.load(CB.L2 + '/work/inputs.npz')['U']
    G['mid'] = O.month_id(CB.NH, CB.H0)
    G['g'] = O.gate_series(name, G['mk']) if name in O.GATES else None
    ids = set(GR.sample300())
    G['cfgs'] = [c for c in GR.all_cfgs() if c['cfg_id'] in ids]
    G['dir'] = '%s/placebo_b2_%s%s' % (b2c.OUT, name, '_FORCE' if not ok else '')
    os.makedirs(G['dir'], exist_ok=True)
    classes, cnt = GR.classes_for(name, G['mk'], G['cz'])
    real, rets = stat_for(classes, G['cfgs'], G['T'])
    gfn = '%s/grid_b2_%s.parquet' % (b2c.OUT, name)
    if os.path.exists(gfn):
        g = pd.read_parquet(gfn).set_index('cfg_id').loc[[c['cfg_id'] for c in G['cfgs']], 'F2_ret'].values
        assert np.array_equal(g, rets), 'placebo real stat does not match grid_b2 F2_ret'
    real_kept = sum(v[1] for v in cnt.values()) / max(sum(v[0] for v in cnt.values()), 1)
    # pooled candidate rows of the 12 classes (for the ADDENDUM1 B exclusion-rate check)
    G['pk'] = np.concatenate([G['cz'][O.class_key(*c) + '_k'] for c in O.CLASSES])
    G['pc'] = np.concatenate([G['cz'][O.class_key(*c) + '_c'] for c in O.CLASSES])
    G['real_ex'] = 1.0 - real_kept
    done = {int(os.path.basename(f)[4:8]) for f in glob.glob(G['dir'] + '/run_*.json')}
    todo = [r for r in range(nrep) if r not in done]
    log.info('placebo %s real_stat=%.4f real_kept=%.4f todo=%d', name, real, real_kept, len(todo))
    t0 = time.time()
    if todo:
        with mp.get_context('fork').Pool(NPROC) as pool:
            for i, res in enumerate(pool.imap_unordered(one_rep, todo)):
                if (i + 1) % 25 == 0:
                    log.info('%s %d/%d %.1fs', name, i + 1, len(todo), time.time() - t0)
    runs = []
    for f in sorted(glob.glob(G['dir'] + '/run_*.json')):
        with open(f) as fh:
            runs.append(json.load(fh))
    runs = [x for x in runs if x['r'] < nrep]
    st = np.array([x['stat'] for x in runs])
    p = float((st >= real).mean())
    out = dict(opt=name, forced=not ok, nrep=len(runs), real_stat=real, real_kept_frac=real_kept, p=p, alpha=ALPHA,
               PASS=bool(len(runs) == nrep and p <= ALPHA and ok), placebo_stat_mean=float(st.mean()),
               placebo_stat_q=[float(np.quantile(st, q)) for q in (0.05, 0.5, 0.95)],
               placebo_kept_mean=float(np.mean([x['kept_frac'] for x in runs])), real_ex_rate=G['real_ex'],
               n_redraw_total=int(sum(x.get('n_redraw', 0) for x in runs)),
               ex_rate_minmax=[float(min(x['ex_rate'] for x in runs)), float(max(x['ex_rate'] for x in runs))] if runs and 'ex_rate' in runs[0] else None)
    with open('%s/placebo_b2_%s%s.json' % (b2c.OUT, name, '_FORCE' if not ok else ''), 'w') as fh:
        json.dump(out, fh, indent=1)
    log.info('placebo %s p=%.4f PASS=%s', name, p, out['PASS'])
    return out


if __name__ == '__main__':
    main(sys.argv[1:])
