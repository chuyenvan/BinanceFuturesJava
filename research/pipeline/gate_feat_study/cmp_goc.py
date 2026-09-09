#!/usr/bin/env python3
"""So sanh p15 cua 1 tag voi p15 GOC (wfo_gate_pred.csv) theo fold."""
import datetime, logging, os, sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("cmp")
OUTDIR = "/home/ubuntu/gate_feat_study"
GATE_CSV = "/home/ubuntu/claudedata/wfo_gate_pred.csv"
TZ = datetime.timezone(datetime.timedelta(hours=7))


def add_months(dt, k):
    mo = dt.month - 1 + k
    y = dt.year + mo // 12
    mo = mo % 12 + 1
    return dt.replace(year=y, month=mo)


def build_folds():
    base = datetime.datetime(2021, 4, 1, tzinfo=TZ)
    dev_end = int(datetime.datetime(2026, 1, 1, tzinfo=TZ).timestamp() * 1000)
    folds, k = [], 0
    while True:
        a = add_months(base, 3 * k)
        b = add_months(base, 3 * (k + 1))
        if a.timestamp() * 1000 >= dev_end:
            break
        folds.append((int(a.timestamp() * 1000), int(b.timestamp() * 1000), k))
        k += 1
    return folds


def main():
    tag = sys.argv[1]
    p = pd.read_csv(os.path.join(OUTDIR, f"p15_{tag}.csv"))
    g = pd.read_csv(GATE_CSV).rename(columns={"predReturn15M": "pred_goc"})
    m = pd.merge(p, g, on="timestamp")
    rho = spearmanr(m.pred, m.pred_goc).correlation
    LOG.info("=== %s vs p15 GOC: n=%d spearman=%.6f max|d|=%.3e ===", tag, len(m), rho,
             float(np.max(np.abs(m.pred - m.pred_goc))))
    for lo, hi, k in build_folds():
        s = m[(m.timestamp >= lo) & (m.timestamp < hi)]
        if len(s) > 100:
            r = spearmanr(s.pred, s.pred_goc).correlation
            md = float(np.max(np.abs(s.pred - s.pred_goc)))
            LOG.info("  fold %2d: n=%d spearman=%.6f max|d|=%.3e", k, len(s), r, md)


if __name__ == "__main__":
    main()
