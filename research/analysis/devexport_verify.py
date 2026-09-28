#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Doi chieu EXPORT PORT vs BAN DEV GOC (`gate15m_v2_full.csv`) tren VUNG GIAO NHAU.

Pre-reg: docs/prereg/PREREG_DEVEXPORT_202609_AUDIT.md §5
  python3 devexport_verify.py --mine <out.csv[.gz]> --dev ~/claudedata/gate15m_v2_full.csv \
      --lo <ms> --hi <ms> [--json out.json]
"""
import argparse
import gzip
import json
import sys

import numpy as np
import pandas as pd

CSV_FEAT_NAMES = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "volatilityRegime",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
    "btcDominance", "rsi14", "volumeSpike", "distMA20",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
]
NUM = [c for c in CSV_FEAT_NAMES if c != "volatilityRegime"]


def load_mine(path, lo, hi):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as fh:
        d = pd.read_csv(fh)
    d = d[(d.ts >= lo) & (d.ts < hi)]
    return d


def load_dev(path, lo, hi):
    cols = ["timestamp"] + CSV_FEAT_NAMES
    parts = []
    with open(path, "rt") as fh:
        for ch in pd.read_csv(fh, usecols=lambda c: c in set(cols), chunksize=500_000):
            m = (ch.timestamp >= lo) & (ch.timestamp < hi)
            if m.any():
                parts.append(ch.loc[m])
            if len(ch) and ch.timestamp.iloc[-1] >= hi:
                break
    if not parts:
        return pd.DataFrame(columns=cols)
    return pd.concat(parts, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mine", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--lo", type=int, required=True)
    ap.add_argument("--hi", type=int, required=True)
    ap.add_argument("--json")
    a = ap.parse_args()

    mi = load_mine(a.mine, a.lo, a.hi)
    dv = load_dev(a.dev, a.lo, a.hi)
    if len(dv):
        dv = dv.rename(columns={"timestamp": "ts"})
    print("mine rows=%d  dev rows=%d" % (len(mi), len(dv)))
    m = mi.merge(dv, on="ts", suffixes=("_m", "_d"), how="inner")
    print("joined rows=%d" % len(m))
    rep = {"mine_rows": int(len(mi)), "dev_rows": int(len(dv)), "joined": int(len(m)),
           "feats": {}}
    nbad = 0
    for c in NUM:
        x = m[c + "_m"].to_numpy(dtype=np.float64)
        y = m[c + "_d"].to_numpy(dtype=np.float64)
        bad = ~(np.isfinite(x) & np.isfinite(y))
        x = np.where(bad, 0.0, x); y = np.where(bad, 0.0, y)
        ad = np.abs(x - y)
        den = np.maximum(np.abs(y), 1e-12)
        rd = ad / den
        r = np.corrcoef(x, y)[0, 1] if len(x) > 2 and np.std(x) > 0 and np.std(y) > 0 else float("nan")
        ok = (ad.max() <= 1e-6) or (rd.max() <= 1e-4)
        if not ok:
            nbad += 1
        rep["feats"][c] = {"max_abs": float(ad.max()), "max_rel": float(rd.max()),
                           "corr": float(r), "mean_m": float(x.mean()), "mean_d": float(y.mean()),
                           "pass": bool(ok)}
        flag = "" if ok else "  <-- LECH"
        print("%-24s max|d|=%.3e max_rel=%.3e corr=%.9f meanM=%.8f meanD=%.8f%s"
              % (c, ad.max(), rd.max(), r, x.mean(), y.mean(), flag))
    # volatilityRegime chuoi
    if "volatilityRegime_m" in m and "volatilityRegime_d" in m:
        eq = (m["volatilityRegime_m"].astype(str) == m["volatilityRegime_d"].astype(str)).mean()
        rep["regime_match"] = float(eq)
        print("volatilityRegime match = %.4f" % eq)
    rep["n_feat_lech"] = int(nbad)
    rep["verdict"] = "PASS" if nbad == 0 else "FAIL"
    print("VERDICT: %s (feature lech: %d/%d)" % (rep["verdict"], nbad, len(NUM)))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(rep, fh, indent=1)
    return 0 if nbad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
