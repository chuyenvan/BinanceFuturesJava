#!/usr/bin/env python3
"""
GATEFEAT scorer — cham diem chuoi p15 cua 1 chu trinh so voi Stage 0 / p15 goc.

Metric (theo PREREG_GATEFEAT muc 5):
- Spearman IC(pred, realized) de-overlap 15m (lay moi moc 15 phut) — realized = label_oldbasket
  (max gain TB 15 phut toi cua ro) tu feature store.
- Lift top-decile +1%/+2%/+3%: tan suat realized > nguong trong top 10% pred / base.
- So sanh tung chu trinh vs STAGE0 (paired theo fold) + bao ca parity vs p15 goc (wfo_gate_pred.csv).

Usage:
  python3 gate_feat_study/score_cycle.py --tag STAGE0 --ref STAGE0
  python3 gate_feat_study/score_cycle.py --tag CYC1 --ref STAGE0
"""
import argparse, datetime, gzip, logging, os, sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("gatefeat-score")

STORE = "/home/ubuntu/claudedata/gate_dataset_full.csv.gz"
GATE_CSV = "/home/ubuntu/claudedata/wfo_gate_pred.csv"
OUTDIR = "/home/ubuntu/gate_feat_study"
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
        folds.append((int(a.timestamp() * 1000), int(b.timestamp() * 1000)))
        k += 1
    return folds


def load_realized():
    """label_oldbasket tai moi moc (realized cua gate)."""
    df = pd.read_csv(STORE, usecols=["timestamp", "label_oldbasket"])
    return df.rename(columns={"label_oldbasket": "realized"})


def ic_lift(ts, pred, realized, fold_bounds=None):
    """IC spearman + lift top-decile, de-overlap 15m (giu moc %900000==0)."""
    d = pd.DataFrame({"ts": ts, "pred": pred, "realized": realized})
    d = d[d.ts % 900000 == 0].reset_index(drop=True)  # de-overlap 15m
    if len(d) < 100:
        return None
    ic = spearmanr(d.pred, d.realized).correlation
    rows = {"n": len(d), "ic": ic}
    for thr in (0.01, 0.02, 0.03):
        base = (d.realized > thr).mean()
        cut = np.percentile(d.pred, 90)
        top = d[d.pred >= cut]
        lift = ((top.realized > thr).mean() / base) if base > 0 and len(top) > 0 else np.nan
        rows[f"lift+{int(thr*100)}%"] = lift
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ref", default="STAGE0")
    a = ap.parse_args()

    p = pd.read_csv(os.path.join(OUTDIR, f"p15_{a.tag}.csv"))
    ref = pd.read_csv(os.path.join(OUTDIR, f"p15_{a.ref}.csv"))
    # merge theo timestamp de so sanh paired
    m = pd.merge(p, ref, on="timestamp", suffixes=("", "_ref"))
    rho = spearmanr(m.pred, m.pred_ref).correlation
    md = float(np.max(np.abs(m.pred - m.pred_ref)))
    LOG.info("=== %s vs %s: n=%d spearman=%.6f max|d|=%.3e ===", a.tag, a.ref, len(m), rho, md)

    real = load_realized()
    j = pd.merge(p, real, on="timestamp")
    folds = build_folds()
    per_fold = []
    for lo, hi in folds:
        s = j[(j.timestamp >= lo) & (j.timestamp < hi)]
        if len(s) == 0:
            continue
        r = ic_lift(s.timestamp, s.pred, s.realized)
        if r:
            per_fold.append(r)
    agg = pd.DataFrame(per_fold)
    LOG.info("IC per fold: mean=%.4f  min=%.4f max=%.4f  (n_fold=%d)",
             agg.ic.mean(), agg.ic.min(), agg.ic.max(), len(agg))
    LOG.info("lift+1%%: mean=%.3f  lift+2%%: mean=%.3f  lift+3%%: mean=%.3f",
             agg["lift+1%"].mean(), agg["lift+2%"].mean(), agg["lift+3%"].mean())
    LOG.info("n de-overlap tong: %d", int(agg.n.sum()))
    agg.to_csv(os.path.join(OUTDIR, f"perfold_{a.tag}.csv"), index=False)


if __name__ == "__main__":
    main()
