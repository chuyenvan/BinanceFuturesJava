"""Monthly market context 2022-2025 (descriptive): BTC monthly return and equal-weight universe alt (excl. BTC) monthly return
from levz_b1 hourly.npz CLH (1m close at hour marks), plus 2022 signal coverage (share of universe rows with finite z_oi).
Output out/m_market.parquet, out/m_cov.json."""
import sys
import os
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.mkt')


def main():
    A.setup_log('m_market')
    CB, P, X = A.b1()
    syms = A.meta()['syms']
    hz = np.load(CB.WORK + '/hourly.npz')
    CLH, has1m = hz['CLH'], hz['has1m']
    G = A.dense_sig(7, syms)
    tms = A.H0 + np.arange(CLH.shape[0], dtype=np.int64) * A.H
    ym = A.dts(tms).strftime('%Y-%m').values
    first = pd.Series(np.arange(len(ym))).groupby(ym).min()
    b = syms.index('BTCUSDT')
    rows = []
    ks = first.values.tolist() + [CLH.shape[0] - 1]
    for i, m in enumerate(first.index.tolist()):
        a, z = ks[i], ks[i + 1]
        ok = has1m[a] & has1m[z] & G['u'][a]
        ok[b] = False
        r = CLH[z, ok] / CLH[a, ok] - 1
        rows.append(dict(ym=m, btc=float(CLH[z, b] / CLH[a, b] - 1), ew_alt=float(np.mean(r)), ew_alt_med=float(np.median(r)), n=int(ok.sum())))
    pd.DataFrame(rows).to_parquet(A.OUT + '/m_market.parquet', index=False)
    cov = {}
    for y in (2022, 2023, 2024, 2025):
        mk = (A.dts(tms).year.values == y)
        u = G['u'][mk]
        cov[y] = dict(universe_rows=int(u.sum()), frac_zoi_finite=float(np.isfinite(G['z_oi'][mk][u]).mean()),
                      frac_zf_finite=float(np.isfinite(G['z_f'][mk][u]).mean()))
    with open(A.OUT + '/m_cov.json', 'w') as fh:
        json.dump(cov, fh, indent=1)
    log.info('cov %s', cov)


if __name__ == '__main__':
    main()
