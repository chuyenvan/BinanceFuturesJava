#!/usr/bin/env python3
"""reaudit_short_fullchain_f1.py — kiem F1 (pool cand_dev_x1: % p15 >= 0,008; tick/nam) + thu tu ts cua fund_cache
(dieu kien cho searchsorted trong audit_short_fullchain_repro.py). CHI DOC, DEV <= 2025."""
import json, logging, sys
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("f1")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
from short_v3_score import Fund  # noqa

d = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet", columns=["ts", "p15"])
out = dict(n_rows=int(len(d)), ts_max=str(pd.Timestamp(int(d.ts.max()), unit="ms")),
           frac_p15_ge_0008=float((d.p15 >= 0.008).mean()), p15_min=float(d.p15.min()),
           n_p15_nan=int(d.p15.isna().sum()), n_tick=int(d.ts.nunique()))
u = pd.Series(np.unique(d.ts.to_numpy()))
for tz in ("UTC", "Asia/Bangkok"):
    yy = pd.to_datetime(u, unit="ms", utc=True).dt.tz_convert(tz).dt.year
    out["ticks_by_year_" + tz] = {int(k): int(v) for k, v in yy.value_counts().sort_index().items()}
tk = d.groupby("ts").p15.min()
out["tick_frac_minp15_ge_0008"] = float((tk >= 0.008).mean())
log.info("F1 %s", out)
F = Fund("/tmp/fund_cache.npz")
bad = 0; dup = 0
for s in range(len(F.syms)):
    t = F.ts[F.bounds[s]:F.bounds[s + 1]]
    bad += int((np.diff(t) < 0).sum()); dup += int((np.diff(t) == 0).sum())
out["fund_cache"] = dict(n_syms=len(F.syms), n_ev=int(len(F.ts)), n_nonmono=bad, n_dup=dup,
                         ts_max=str(pd.Timestamp(int(F.ts.max()), unit="ms")))
log.info("FUND %s", out["fund_cache"])
json.dump(out, open("/home/ubuntu/claude_master/1002/reaudit_sfc_f1.json", "w"), indent=1)
