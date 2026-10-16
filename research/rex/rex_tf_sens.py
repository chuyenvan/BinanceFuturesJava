"""REX-TF do nhay HAU KIEM (khong doi verdict): chuan hoa trong so theo so coin dang co vi the (gan cach dien giai 'equal-weighted ensemble of open positions')."""
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/rex"))
import rex_tf as T  # noqa: E402

log = logging.getLogger("rextfs")
C, Q, FD = T.load()
W, frac, lev, U, st = T.build(C, Q)
raw = (frac * lev[frac.columns]).where(U[frac.columns], 0.0).fillna(0.0)
nopen = (raw > 0).sum(axis=1).replace(0, np.nan)
W2 = raw.div(nopen, axis=0).fillna(0.0)
g = W2.sum(axis=1); W2 = W2.mul((2.0 / g).clip(upper=1.0).fillna(1.0), axis=0)
W2 = W2.loc["2021-06-01":]
df = T.pnl(W2, C, FD)
for per, a, b in (("DEV", T.S1.DEV0, T.S1.DEV1), ("VAL", T.S1.VAL0, T.S1.VAL1)):
    x = T.stats(df, a, b)
    log.info("SENS open-norm %s Sh %+.2f ann %+.1f%% dd %.2f yr %s alpha %+.1f%% beta %.2f exp %.2f turn %.3f", per, x["sh"], 100 * x["ann"], x["maxdd"],
             x["year_sum"], 100 * x["alpha_ann"], x["beta"], x["exp_avg"], x["turn"])
v = df[(df.index >= "2025-04-01") & (df.index <= "2025-12-31")].net
log.info("SENS open-norm 2025-04..12 (OOS cua paper) Sh %+.2f tong %+.1f%%", v.mean() / v.std() * np.sqrt(365), 100 * v.sum())
v1 = pd.read_csv(T.OUT + "/tf_TF20.csv", index_col=0, parse_dates=True).net
v1 = v1[(v1.index >= "2025-04-01") & (v1.index <= "2025-12-31")]
log.info("TF20 goc 2025-04..12 Sh %+.2f tong %+.1f%%", v1.mean() / v1.std() * np.sqrt(365), 100 * v1.sum())
