"""CVX chan doan du lieu (khong phai phep thu): KPd range; ghep sai token Upbit-Binance."""
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/cvx"))
import cv_run as R  # noqa: E402

log = logging.getLogger("cvdiag")
U = pd.read_parquet(R.W + "/upbit_1d.parquet")
U["px"] = U.close_krw * U.fac
P = U.pivot(index="day", columns="sym", values="px").reindex(R.C.index)
ub = P["BTCUSDT"]; fx = ub / R.C["BTCUSDT"]
KP = np.log(fx); KPd = KP - KP.shift(1).rolling(30, min_periods=25).median()
log.info("KPd range [-10%%,+25%%]: %.4f | KPd q01 %.4f q99 %.4f", float(((KPd > -0.10) & (KPd < 0.25))[KPd.notna()].mean()), KPd.quantile(0.01), KPd.quantile(0.99))
syms = [s for s in P.columns if s in R.C.columns]
lr = np.log(P[syms] / R.C[syms]).sub(np.log(fx), axis=0)
ru = np.log(P[syms]).diff(); rb = np.log(R.C[syms]).diff()
rows = []
for s in syms:
    j = pd.concat([ru[s], rb[s]], axis=1).dropna()
    rows.append((s, float(lr[s].abs().median()), float(lr[s].abs().quantile(0.95)), float(j.iloc[:, 0].corr(j.iloc[:, 1])) if len(j) > 30 else np.nan, int(lr[s].notna().sum())))
T = pd.DataFrame(rows, columns=["sym", "med_abs", "p95_abs", "ret_corr", "n"]).sort_values("med_abs", ascending=False)
log.info("so sym %d; med_abs>5%%: %d; ret_corr<0.9: %d", len(T), int((T.med_abs > 0.05).sum()), int((T.ret_corr < 0.9).sum()))
log.info("TOP lech:\n%s", T.head(25).to_string())
log.info("ret_corr thap:\n%s", T.sort_values("ret_corr").head(15).to_string())
T.to_csv(R.W + "/upbit_match_diag.csv", index=False)
