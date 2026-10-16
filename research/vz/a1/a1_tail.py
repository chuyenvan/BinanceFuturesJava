"""Mo ta (KHONG cham) duoi phai F1 tren nam kham pha 2022+2024 — de quyet co viet pre-reg xac nhan duoi hay khong."""
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("tail")
d = pd.read_csv(os.path.expanduser("~/kaggle_sim/out/gqsf-a1/storage/printDone.csv"), index_col=False)
d = d[d.level != "DCA_LEVEL1"].copy()
d["t0"] = (pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)).astype("int64") // 10**6
d["n"] = d.groupby("t0").sym.transform("size")
d["year"] = pd.to_datetime(d.t0, unit="ms").dt.year
d = d[(d.n >= 6) & d.year.isin([2022, 2024])]
F = pd.read_csv(os.path.expanduser("~/claude_master/1016/a1/out/a1_feat_v3.csv"))
m = d.merge(F[["sym", "t0", "F1", "F2"]], on=["sym", "t0"])
B = m.groupby("t0").agg(pnl=("pnl", "sum"), margin=("margin", "sum"), F1=("F1", "median"), F2=("F2", "median"),
                        year=("year", "first"), n=("sym", "size")).reset_index()
B["ret"] = B.pnl / B.margin
B["t"] = pd.to_datetime(B.t0, unit="ms")
log.info("F1 dot: q50 %.4f q75 %.4f q90 %.4f q95 %.4f", *B.F1.quantile([.5, .75, .9, .95]))
for thr in (0.002, 0.003, 0.004, 0.005):
    hi = B[B.F1 > thr]; lo = B[B.F1 <= thr]
    log.info("F1>%.3f: %d dot, ret TB %+.3f (trung vi %+.3f), PnL %+.0f | con lai %d dot ret TB %+.3f, PnL %+.0f",
             thr, len(hi), hi.ret.mean(), hi.ret.median(), hi.pnl.sum(), len(lo), lo.ret.mean(), lo.pnl.sum())
log.info("cac dot F1>0.003:\n%s", B[B.F1 > 0.003].sort_values("t")[["t", "n", "ret", "pnl", "F1", "F2"]].round(4).to_string(index=False))
log.info("tong PnL 69 dot %+.0f", B.pnl.sum())
