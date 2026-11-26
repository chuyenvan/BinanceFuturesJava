"""LEVZ B1 mandatory cross-check vs B0 (task item 6) - ONLY X1 and X2, NO profit numbers written.
X1 = W14 E0 z2.5 K10 SL50 H24 trailing off; X2 = W7 E0 z3.0 K3 SL15 H24 trailing off (B0: same, DCA off).
Compares per fold: #trades, exit-reason shares (B0 grid.parquet row); DEV: set of (sym, entry hour) vs B0 trades (B0 sim.run re-run
for the same two configs on B0 inputs, read-only), reason cross-tab on matched trades, entry-price difference, candidate sets.
Also timing: exits (s / candidate, all 195 exit cfgs) and port (s / fold-run) -> estimates for grid 7 020 and random control.
usage: python3 code/x12.py  -> out/x12.json"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]
import json
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
log = logging.getLogger('levz_b1.x12')
XS = {'X1': dict(W=14, E='E0', zmin=2.5, K=10, SL=0.50, H=24), 'X2': dict(W=7, E='E0', zmin=3.0, K=3, SL=0.15, H=24)}
KEEP = ('n', 'x_sl', 'x_trail', 'x_time', 'x_miss', 'x_eod', 'n_flag', 'acct_err', 'eq_end_ledger_minus_eq')
KEEP0 = ('n', 'x_sl', 'x_trail', 'x_time', 'x_time_sub', 'x_gap', 'x_eod', 'n_flag')


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    S = P.S
    R0 = CB.load_b0('rand')
    I = S.load_inputs()
    g0 = pd.read_parquet(CB.L2 + '/out/grid.parquet')
    cz = np.load(CB.WORK + '/cand_b1.npz')
    syms = CB.meta()['syms']
    st = X.Store()
    rep = {}
    for name, c in XS.items():
        key = 'W%d_%s_%.1f' % (c['W'], c['E'], c['zmin'])
        ks, cs, ss = cz[key + '_k'], cz[key + '_c'], cz[key + '_s']
        t0 = time.time()
        T = X.compute(st, ks, cs)
        t_ex = time.time() - t0
        cand = P.CandB1(ks, cs, ss, np.arange(len(ks)))
        xv = P.XView(T, CB.xidx(c['SL'], c['H'], 0.0, 0.0))
        o = dict(cfg=c, n_cand_b1=int(len(ks)), exits_sec=t_ex, exits_sec_per_cand=t_ex / len(ks), folds={})
        secs = []
        for fname, a, b in P.FOLDS:
            k0, kl = S.kidx(S.ms(a)), S.kidx(S.ms(b)) - 1
            t1 = time.time()
            tr, eq, m = P.run(c['K'], cand, xv, k0, kl)
            secs.append(time.time() - t1)
            o['folds'][fname] = {kk: m.get(kk) for kk in KEEP}
            if fname == 'DEV':
                trB1 = tr
        o['port_sec_per_fold_run'] = secs
        cfg0 = dict(c, trail=0, dca=0)
        row = g0[(g0['W'] == c['W']) & (g0['E'] == c['E']) & (g0['zmin'] == c['zmin']) & (g0['K'] == c['K']) & (g0['SL'] == c['SL'])
                 & (g0['H'] == c['H']) & (g0['trail'] == 0) & (g0['dca'] == 0)]
        assert len(row) == 1
        row = row.iloc[0]
        o['b0_cfg_id'] = int(row['cfg_id'])
        o['b0_folds'] = {f: {kk: (float(row['%s_%s' % (f, kk)]) if pd.notna(row['%s_%s' % (f, kk)]) else None) for kk in KEEP0}
                         for f in ('DEV', 'F1', 'F2', 'F3')}
        c0 = I.cand[(c['W'], c['E'], c['zmin'])]
        tr0, _, m0 = S.run(cfg0, c0, I.px, I.FR, '2022-01-01', '2026-01-01')
        assert len(tr0) == int(row['DEV_n'])
        b0 = pd.DataFrame({'sym': [I.syms[x] for x in tr0['c']], 'ke': tr0['ke'].values, 'reason0': tr0['reason'].values,
                           'p0_b0': tr0['p0'].values})
        b1 = pd.DataFrame({'sym': [syms[x] for x in trB1['c']], 'ke': trB1['ke'].values, 'reason1': trB1['reason'].values,
                           'p0_b1': T['p0'][trB1['cid'].values], 'j': trB1['j'].values})
        j = b0.merge(b1, on=['sym', 'ke'], how='outer', indicator=True)
        both = j[j['_merge'] == 'both']
        o['dev_set'] = dict(n_b0=int(len(b0)), n_b1=int(len(b1)), n_both=int(len(both)),
                            frac_of_b0=float(len(both) / max(len(b0), 1)), frac_of_b1=float(len(both) / max(len(b1), 1)))
        o['dev_reason_crosstab_matched'] = {'%s->%s' % (a, b): int(v) for (a, b), v in both.groupby(['reason0', 'reason1']).size().items()}
        rd = (both['p0_b1'] / both['p0_b0'] - 1.0).abs()
        o['entry_px_reldiff_abs'] = dict(median=float(rd.median()), q95=float(rd.quantile(0.95)), max=float(rd.max()))
        ck0 = set(zip(c0.ck.tolist(), c0.cc.tolist()))
        ck1 = set(zip(ks.tolist(), cs.tolist()))
        o['cand_sets_all_hours'] = dict(n_b0=len(ck0), n_b1=len(ck1), n_both=len(ck0 & ck1), only_b0=len(ck0 - ck1), only_b1=len(ck1 - ck0))
        ek, ec = R0.episode_starts(ks, cs)
        o['n_episodes_dev'] = int(((ek >= S.kidx(S.ms('2022-01-01')))).sum())
        rep[name] = o
        log.info('%s done exits %.1fs port %s', name, t_ex, ['%.3f' % s for s in secs])
    eps = {}
    for W in (14, 7):
        for E in ('E0', 'E1'):
            for z in (2.5, 3.0, 3.5):
                key = 'W%d_%s_%.1f' % (W, E, z)
                ek, ec = R0.episode_starts(cz[key + '_k'], cz[key + '_c'])
                eps[key] = dict(n_cand=int(len(cz[key + '_k'])), n_episodes_dev=int((ek >= S.kidx(S.ms('2022-01-01'))).sum()))
    rep['class_sizes'] = eps
    rep['n_union'] = int(len(cz['U_k']))
    with open(CB.OUT + '/x12.json', 'w') as fh:
        json.dump(rep, fh, indent=1, default=float)
    log.info('x12 written (no profit fields)')


if __name__ == '__main__':
    main()
