#!/usr/bin/env python3
"""h72_h4_delta.py — Delta GHEP CAP (72h − 4h) tren CUNG tap tick, cung CI block-72h.

Dung per-tick parquet do `h72_s1_measure.py` sinh (`/home/ubuntu/.cache/h{4,72}_s1_<nhan>_ticks.parquet`).
`*` = ngoai CA HAI do rong (nhu model_ruler.decide). khong train, khong sim.
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
LOG = logging.getLogger("h72d")
METRICS = ["ic", "pacc", "dec_mono", "dec_rho", "glift8", "netm8", "auc8", "lift8", "dec_rho_lab"]
B = "/home/ubuntu/.cache"


def load(tag):
    d = pd.read_parquet("%s/h%d_s1_%s_ticks.parquet" % (B, tag[0], tag[1]))
    return d


rows = []
for lab in ("g1lite", "retEnd", "maxFav"):
    a = load((4, "%s_4h" % lab if lab != "g1lite" else "g1lite"))
    b = load((72, "%s_72h" % lab if lab != "g1lite" else "g1lite"))
    # an toan: ghep theo ts
    for m in METRICS:
        if m not in a.columns or m not in b.columns:
            continue
        x = a[["ts", m]].rename(columns={m: "h4"}).merge(
            b[["ts", m]].rename(columns={m: "h72"}), on="ts", how="inner")
        d = (x.h72 - x.h4).to_numpy(np.float64)
        ci = R.ci_mean(d, x.ts.to_numpy(), inflate=C.inflate(2))
        _o1, _o2, both, _ = R.decide(ci)
        rows.append(dict(nhan=lab, metric=m, d=ci["mean"], lo=ci["raw"][0], hi=ci["raw"][1],
                         out_both=both, n=ci["n"]))
T = pd.DataFrame(rows)
pd.set_option("display.width", 200)
LOG.info("=== DELTA (h=72h − h=4h), ghep cap tick, CI block-72h NREP=%d SEED=%d k=2 (%.4f) ===",
         C.NREP, C.SEED, C.inflate(2))
LOG.info("\n%s", T.assign(d=T.d.round(5), lo=T.lo.round(5), hi=T.hi.round(5)).to_string(index=False))
T.to_csv("%s/h72_vs_h4_s1_agg.csv" % B, index=False)
