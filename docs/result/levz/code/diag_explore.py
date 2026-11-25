"""Diagnostic (explore only, no outcomes): signal coverage by year/half-year."""
import logging
import numpy as np
import pandas as pd
import common as C
import levz as L
C.setup_log()
log = logging.getLogger('diag')
D = L.Data('2024-01')
yr = pd.to_datetime(D.tms, unit='ms')
lab = np.array(['%d-H%d' % (t.year, 1 + (t.month > 6)) for t in yr])
for W in (14,):
    g = L.signals(D, W)
    for p in ['2022-H1', '2022-H2', '2023-H1', '2023-H2']:
        m = lab == p
        U = D.U[m]
        nu = U.sum()
        log.info('%s W%d univ_hours=%d zoi_fin=%.3f zf_fin=%.3f f_fin=%.3f f>1e-4=%.4f zf>2.5=%.5f zoi>2.5=%.4f f>3e-4=%.5f ih4share=%.3f',
                 p, W, nu, np.isfinite(g['zoi'][m])[U].mean(), np.isfinite(g['zf'][m])[U].mean(), np.isfinite(g['f'][m])[U].mean(),
                 (g['f'][m][U] > 1e-4).mean(), (g['zf'][m][U] > 2.5).mean(), (g['zoi'][m][U] > 2.5).mean(), (g['f'][m][U] > 3e-4).mean(), 0.0)
fr = pd.concat([C.read_funding(y, L.ms('2024-01-01')) for y in (2022, 2023)])
fr['y'] = pd.to_datetime(fr.ts, unit='ms').dt.year
log.info('funding interval_h by year:\n%s', fr.groupby(['y', 'interval_h']).size())
