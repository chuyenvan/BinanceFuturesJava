"""A step 3: where does 2024 fail across the WHOLE B1 grid (7 020 existing configs, no new params).
Re-runs port DEV contiguous per config; stores monthly MTM returns (2022-01..2025-12) + 2024 per-config trade stats;
accumulates 2024 per-coin contribution (ret x 0.6/K) over configs. Single process; resumable is unnecessary (~minutes).
Outputs out/a_grid_monthly.parquet, out/a_grid_2024cfg.parquet, out/a_grid_2024coin.parquet."""
import sys
import os
import logging
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.grid2024')


def main():
    A.setup_log('a_grid2024')
    CB, P, X = A.b1()
    g = pd.read_parquet('/home/ubuntu/claude_master/w3/levz_b1/out/grid_b1_scored.parquet')
    T = X.load_table()
    cz = np.load(CB.WORK + '/cand_b1.npz')
    k0, kl = A.dev_k()
    tms = A.H0 + np.arange(k0, kl + 1, dtype=np.int64) * A.H
    ym = A.dts(tms).strftime('%Y-%m').values
    # index of last hour of each month (t = month end boundary)
    last = pd.Series(np.arange(len(ym))).groupby(ym).max()
    months = last.index.tolist()
    syms = A.meta()['syms']
    cache = {}
    rows, cfgrows = [], []
    coin = {}
    t0 = time.time()
    for i, r in enumerate(g.itertuples(index=False)):
        key = (int(r.W), r.E, float(r.zmin))
        if key not in cache:
            cache[key] = P.load_class(cz, *key)
        xv = P.XView(T, CB.xidx(r.SL, r.H, r.arm, r.gap))
        tr, eq, met = P.run(int(r.K), cache[key], xv, k0, kl)
        e = eq['eq'].values[last.values]
        prev = np.concatenate([[10000.0], e[:-1]])
        rows.append(np.concatenate([[r.cfg_id], e / prev - 1.0]))
        tx = A.H0 + tr['ke'].values * A.H + tr['j'].values * A.M
        s = tr[(tx >= 1704067200000) & (tx < 1735689600000)]
        cfgrows.append(dict(cfg_id=int(r.cfg_id), n24=len(s), nsl24=int((s['reason'] == 'sl').sum()), ntr24=int((s['reason'] == 'trail').sum()),
                            net24=float(s['net'].sum()), sl_net24=float(s.loc[s['reason'] == 'sl', 'net'].sum()),
                            other_net24=float(s.loc[s['reason'] != 'sl', 'net'].sum()),
                            ret24_contig=float(eq['eq'].values[last.values[months.index('2024-12')]] / eq['eq'].values[last.values[months.index('2023-12')]] - 1)))
        cb = s.groupby('c')['ret'].sum() * 0.60 / int(r.K)
        for c, v in cb.items():
            a = coin.setdefault(int(c), [0.0, 0, 0.0])
            a[0] += float(v)
            a[1] += 1
            a[2] += float(v) if v < 0 else 0.0
        if (i + 1) % 500 == 0:
            log.info('%d/%d %.0fs', i + 1, len(g), time.time() - t0)
    M = pd.DataFrame(rows, columns=['cfg_id'] + months)
    M['cfg_id'] = M['cfg_id'].astype(int)
    M.to_parquet(A.OUT + '/a_grid_monthly.parquet', index=False)
    pd.DataFrame(cfgrows).to_parquet(A.OUT + '/a_grid_2024cfg.parquet', index=False)
    C = pd.DataFrame([(syms[c], v[0], v[1], v[2]) for c, v in coin.items()], columns=['sym', 'contrib_sum', 'n_cfg', 'neg_sum'])
    C.to_parquet(A.OUT + '/a_grid_2024coin.parquet', index=False)
    log.info('grid2024 done %.0fs', time.time() - t0)


if __name__ == '__main__':
    main()
