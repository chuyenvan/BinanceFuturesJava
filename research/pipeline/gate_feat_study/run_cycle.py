#!/usr/bin/env python3
"""
GATEFEAT harness — Stage 0 (control, 33 feature) va tung chu trinh bot feature.

Train 21 fold WFO (expanding, OOS=3 thang, anchor 2021-01-01 + minTrain 3 thang => fold 0 OOS
bat dau 2021-04-01) DUNG hyperparam ml/gate/train_gate_fold.py (XGBRegressor depth4 n150 lr0.05
sub0.8 col0.8 mw10 seed42, purge 15 phut). Predict OOS tu feature store (KHONG replay).
Ghep chuoi OOS 19 fold DEV -> luu p15 csv + cham IC/lift.

Usage:
  python3 gate_feat_study/run_cycle.py --tag STAGE0
  python3 gate_feat_study/run_cycle.py --tag CYC1_BASKETVOLSPIKE --drop basketVolSpike
  (--drop them nhieu: --drop a --drop b ...)
"""
import argparse, datetime, gzip, json, logging, os, sys, time
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("gatefeat")

STORE = "/home/ubuntu/claudedata/gate_dataset_full.csv.gz"
OUTDIR = "/home/ubuntu/gate_feat_study"
DEV_END_MS = int(datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone(datetime.timedelta(hours=7))).timestamp() * 1000)

V3FULL = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
    "btcDominance", "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
assert len(V3FULL) == 33
LABEL = "label_oldbasket"
PURGE_MS = 15 * 60_000

PARAMS = dict(objective="reg:squarederror", max_depth=4, n_estimators=150, learning_rate=0.05,
              subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=42, n_jobs=4)


def add_months(dt, k):
    mo = dt.month - 1 + k
    y = dt.year + mo // 12
    mo = mo % 12 + 1
    return dt.replace(year=y, month=mo)


def build_folds():
    base = datetime.datetime(2021, 4, 1, tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
    folds = []
    k = 0
    while True:
        a = add_months(base, 3 * k)
        b = add_months(base, 3 * (k + 1))
        if a.timestamp() * 1000 >= DEV_END_MS:
            break
        folds.append((int(a.timestamp() * 1000), int(b.timestamp() * 1000), k))
        k += 1
    return folds


def load_store():
    t0 = time.time()
    df = pd.read_csv(STORE, usecols=["timestamp"] + V3FULL + [LABEL])
    df = df[df.timestamp < DEV_END_MS].reset_index(drop=True)
    LOG.info("store loaded: %d rows (DEV, < %d), %.1fs", len(df), DEV_END_MS, time.time() - t0)
    return df


def train_fold(df, feats, cutoff_ms):
    tr = df[df.timestamp < cutoff_ms - PURGE_MS]
    if len(tr) < 1000:
        return None
    X = tr[feats].values.astype(np.float32)
    y = tr[LABEL].values.astype(np.float32)
    m = xgb.XGBRegressor(**PARAMS)
    m.fit(X, y)
    return m


def run_cycle(tag, drop):
    feats = [f for f in V3FULL if f not in drop]
    LOG.info("CYCLE %s: %d feature (drop=%s)", tag, len(feats), drop or "-")
    df = load_store()
    folds = build_folds()
    LOG.info("%d fold DEV", len(folds))
    parts = []
    for cutoff_ms, oos_end_ms, k in folds:
        m = train_fold(df, feats, cutoff_ms)
        oos = df[(df.timestamp >= cutoff_ms) & (df.timestamp < oos_end_ms)]
        pred = m.predict(oos[feats].values.astype(np.float32)).astype(np.float64)
        sub = pd.DataFrame({"timestamp": oos.timestamp.values, "pred": pred})
        parts.append(sub)
        LOG.info("fold %d done: OOS %d rows", k, len(sub))
    out = pd.concat(parts, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    out.to_csv(os.path.join(OUTDIR, f"p15_{tag}.csv"), index=False)
    LOG.info("saved p15_%s.csv (%d rows)", tag, len(out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--drop", action="append", default=[])
    a = ap.parse_args()
    run_cycle(a.tag, a.drop)


if __name__ == "__main__":
    main()
