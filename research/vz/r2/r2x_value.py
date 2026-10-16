"""MO TA (khong cham): gia tri tien cua F2 imb1 trong dot, DEV 2023-2025 (2024 tu R2, 2023+2025 tu R2X sau loc)."""
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("r2v")
a = pd.read_parquet("/home/ubuntu/vz_bd/r2_legs_2024.parquet")
b = pd.read_parquet("/home/ubuntu/vz_bd/r2x_legs_2023_2025.parquet")
d = pd.concat([a, b], ignore_index=True)
d["year"] = d.t0.dt.year
d = d.dropna(subset=["F2"])
d["n_f"] = d.groupby("t0").F2.transform("size")
d = d[d.n_f >= 6].copy()
d["med"] = d.groupby("t0").F2.transform("median")
d["hi"] = d.F2 >= d.med
d["rk"] = d.groupby("t0").F2.rank(pct=True)
log.info("chan %d, dot %d, theo nam %s", len(d), d.t0.nunique(), d.groupby("year").t0.nunique().to_dict())
for y, g in list(d.groupby("year")) + [("all", d)]:
    hi, lo = g[g.hi], g[~g.hi]
    log.info("%s: nua cao F2 ret TB %+.4f (PnL %+.0f, margin %.0f) | nua thap ret TB %+.4f (PnL %+.0f, margin %.0f) | ret/margin cao %+.4f thap %+.4f",
             y, hi.ret.mean(), hi.pnl.sum(), hi.margin.sum(), lo.ret.mean(), lo.pnl.sum(), lo.margin.sum(),
             hi.pnl.sum() / hi.margin.sum(), lo.pnl.sum() / lo.margin.sum())
# theo tu phan vi trong dot
d["q"] = pd.cut(d.rk, [0, .25, .5, .75, 1.0], labels=["Q1 thap", "Q2", "Q3", "Q4 cao"])
log.info("theo tu phan vi F2 trong dot (ret TB, PnL/margin, n):\n%s",
         d.groupby("q", observed=True).apply(lambda g: pd.Series({"ret_mean": g.ret.mean(), "pnl_per_margin": g.pnl.sum() / g.margin.sum(), "n": len(g)})).round(4).to_string())
log.info("F2 phan bo: q10 %.3f q50 %.3f q90 %.3f; ty le F2<0 %.2f", *d.F2.quantile([.1, .5, .9]), (d.F2 < 0).mean())
neg, pos = d[d.F2 < 0], d[d.F2 >= 0]
log.info("F2<0 (ask day hon bid): ret TB %+.4f PnL %+.0f n %d | F2>=0: ret TB %+.4f PnL %+.0f n %d", neg.ret.mean(), neg.pnl.sum(), len(neg), pos.ret.mean(), pos.pnl.sum(), len(pos))
