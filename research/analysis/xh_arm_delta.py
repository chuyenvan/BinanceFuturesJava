#!/usr/bin/env python3
"""xh_arm_delta.py — Δ(A44 − A45) ở **cross-horizon** (điểm 4h × nhãn `*_72h`) + Δ so 2 đối chứng.

Đọc per-tick parquet do `model_ruler.py ruler --horizon 4h --label-horizon 72h --per-tick` sinh.
CI block-72h NREP/SEED của `c3_rates`, `inflate(k=2)`. KHÔNG train, KHÔNG sim.
BẮT BUỘC gọi đúng tên: "cross-horizon (điểm 4h × nhãn 72h)" — KHÔNG phải "đầu 72h của arm".
"""
import logging
import sys

import numpy as np
import pandas as pd

HERE = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
sys.path.insert(0, HERE)
import model_ruler as R      # noqa: E402
import c3_rates as C         # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("xhd")
CACHE = "/home/ubuntu/.cache"
METRICS = ["ic", "pacc", "dec_mono", "dec_rho", "glift8", "netm8", "auc8", "auc8c",
           "lift8", "lift12", "lift16", "dec_rho_lab", "prec8"]


def load(p):
    d = pd.read_parquet(p)
    d["ts"] = d.ts.astype(np.int64)
    return d


def delta(da, db, metrics):
    m = da[["ts"] + [x for x in metrics if x in da.columns]].merge(
        db[["ts"] + [x for x in metrics if x in db.columns]], on="ts", suffixes=("_a", "_b"))
    rows = []
    for x in metrics:
        if x + "_a" not in m.columns:
            continue
        d = (m[x + "_a"] - m[x + "_b"]).to_numpy(np.float64)
        ci = R.ci_mean(d, m.ts.to_numpy(), inflate=C.inflate(2))
        _o1, _o2, both, _ = R.decide(ci)
        rows.append(dict(metric=x, delta=ci["mean"], lo=ci["raw"][0], hi=ci["raw"][1],
                         out_both=both, n=ci["n"]))
    return pd.DataFrame(rows)


def level(p, metrics):
    d = load(p)
    return pd.DataFrame([dict(metric=x, mean=R.ci_mean(d[x].to_numpy(), d.ts.to_numpy(),
                                                      inflate=C.inflate(2))["mean"])
                         for x in metrics if x in d.columns]), len(d)


import glob  # noqa: E402
for LAY, suf in (("TIEN (retEnd_72h)", "retend72"), ("NHAN (maxFav_72h)", "maxfav72")):
    pa = "%s/xh_A45_%s_ticks.parquet" % (CACHE, suf)
    pb = "%s/xh_A44_%s_ticks.parquet" % (CACHE, suf)
    if not (glob.glob(pa) and glob.glob(pb)):
        LOG.info("### [%s] THIEU per-tick (%s / %s) => BO QUA", LAY, pa, pb)
        continue
    A, B = load(pa), load(pb)
    LOG.info("### CROSS-HORIZON (điểm 4h × nhãn %s) | n_tick A45=%d A44=%d | k=2 inflate=%.4f",
             LAY, len(A), len(B), C.inflate(2))
    for nm, d in (("A45(4h score)", A), ("A44(4h score)", B)):
        t, n = level(pa if nm.startswith("A45") else pb, METRICS)
        LOG.info("  [%s] %s", nm, " | ".join("%s=%+.5f" % (r[1], r[2]) for r in t.itertuples()))
    D = delta(B, A, METRICS)          # A44 − A45
    LOG.info("\n=== Δ = A44 − A45 (cross-horizon %s) — `*` = ngoài CA HAI độ rộng ===", LAY)
    LOG.info("\n%s", D.assign(delta=D.delta.round(6), lo=D.lo.round(6), hi=D.hi.round(6))
             .to_string(index=False))
    LOG.info("  SO CHI SO Δ<0 out_both: %d/%d | Δ>0 out_both: %d/%d",
             int(((D.delta < 0) & D.out_both).sum()), len(D),
             int(((D.delta > 0) & D.out_both).sum()), len(D))
    D.to_csv("%s/xh_A44_minus_A45_%s.csv" % (CACHE, suf), index=False)
    # Y1 check: base cua nhan cua CONG (khong loc) — in de thay "base 72h cao"
    LOG.info("  base(yb) mean: A45=%.5f A44=%.5f",
             A["base"].mean() if "base" in A else float("nan"),
             B["base"].mean() if "base" in B else float("nan"))
