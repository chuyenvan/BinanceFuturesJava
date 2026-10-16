#!/usr/bin/env python3
"""Parity shadow <-> offline (devexport, cung cong thuc DEV) + ORT gate model. Audit-only."""
import glob
import gzip
import io
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("par")
EXP = sys.argv[1]
SHADOW = sys.argv[2]            # ~/shadow_c3b
SINCE_MS = int(sys.argv[3])     # epoch ms
OUT = sys.argv[4]
FEATS = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
         "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
         "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown",
         "marketBreadthStrength", "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw",
         "fundingRateAvg24H", "fundingRateTrend", "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
         "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"]


def read_gz_tolerant(p):
    raw = b""
    try:
        with gzip.open(p, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                raw += b
    except Exception:
        pass
    if not raw:
        return None
    txt = raw.decode(errors="ignore")
    lines = txt.splitlines()
    if len(lines) < 2:
        return None
    if not txt.endswith("\n"):
        lines = lines[:-1]
    return pd.read_csv(io.StringIO("\n".join(lines)))


live = []
for p in sorted(glob.glob(SHADOW + "/app/feat_dump/feat_dump_*.csv.gz")):
    d = read_gz_tolerant(p)
    if d is not None:
        live.append(d[d.ts >= SINCE_MS])
L = pd.concat(live, ignore_index=True)
L["min"] = (L.ts // 60000) * 60000
L = L.drop_duplicates("min", keep="last")
log.info("live rows=%d minutes %s -> %s", len(L), pd.to_datetime(L["min"].min(), unit="ms"), pd.to_datetime(L["min"].max(), unit="ms"))

E = pd.read_csv(EXP)
log.info("export cols: %s ...; rows=%d; ts sample=%s", list(E.columns)[:5], len(E), E.iloc[0, 0])
tcol = E.columns[0]
if np.issubdtype(E[tcol].dtype, np.number):
    E["min"] = E[tcol].astype("int64")
else:
    E["min"] = (pd.to_datetime(E[tcol]).dt.tz_localize("Asia/Ho_Chi_Minh", ambiguous="NaT").dt.tz_convert("UTC")
                .astype("int64") // 10**6)
res = {"n_live": int(len(L)), "align": {}}
best = None
for off in (-60000, 0, 60000):
    J = L.merge(E.assign(min=E["min"] + off), on="min", suffixes=("_l", "_e"))
    ok = int((np.abs(J["momentum24H_l"] - J["momentum24H_e"]) <= 1e-6 * (1 + np.abs(J["momentum24H_e"]))).sum()) if len(J) else 0
    res["align"][off] = dict(n=int(len(J)), m24_match=ok)
    if best is None or ok > best[1]:
        best = (off, ok, J)
off, _, J = best
log.info("align %s -> chon off=%d n=%d", res["align"], off, len(J))
rows = {}
for f in FEATS:
    a, b = J[f + "_l"].astype(float), J[f + "_e"].astype(float)
    m = a.notna() & b.notna()
    d = (a[m] - b[m]).abs()
    tol = 1e-6 * (1 + b[m].abs())
    rows[f] = dict(n=int(m.sum()), max_abs=float(d.max()) if m.any() else None, med_abs=float(d.median()) if m.any() else None,
                   frac_match=float((d <= tol).mean()) if m.any() else None,
                   rank_corr=float(a[m].rank().corr(b[m].rank())) if m.sum() > 5 else None)
    log.info("%-24s n=%5d match=%.4f max|d|=%.3g corr=%s", f, rows[f]["n"], rows[f]["frac_match"] or 0, rows[f]["max_abs"] or 0,
             None if rows[f]["rank_corr"] is None else round(rows[f]["rank_corr"], 5))
res["offset_ms"] = off
res["features"] = rows
res["n_joined"] = int(len(J))

# ORT gate model
import onnxruntime as ort  # noqa: E402
mdir = os.path.join(SHADOW, "storage/ai_ml_data/ai_models_reg_v3")
cands = sorted(glob.glob(mdir + "/*15M*.onnx")) + sorted(glob.glob(mdir + "/*eturn*.onnx"))
mp = [c for c in cands if "Scaler" not in os.path.basename(c)]
log.info("model candidates %s", [os.path.basename(c) for c in mp])
if mp:
    sess = ort.InferenceSession(mp[0], providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    log.info("model %s input %s %s", os.path.basename(mp[0]), inp.name, inp.shape)
    def pred(df, suf):
        X = df[[f + suf for f in FEATS]].astype(np.float32).values
        out = sess.run(None, {inp.name: X})[0]
        return np.asarray(out).reshape(-1)
    pl = pred(J, "_l")
    pe = pred(J, "_e")
    p15 = J["p15_out"].astype(float).values
    res["ort_on_live_vs_p15_out"] = dict(max_abs=float(np.nanmax(np.abs(pl - p15))), med=float(np.nanmedian(np.abs(pl - p15))))
    res["ort_on_offline_vs_p15_out"] = dict(max_abs=float(np.nanmax(np.abs(pe - p15))), med=float(np.nanmedian(np.abs(pe - p15))),
                                             p95=float(np.nanpercentile(np.abs(pe - p15), 95)),
                                             corr=float(pd.Series(pe).corr(pd.Series(p15))),
                                             mean_live=float(np.nanmean(p15)), mean_off=float(np.nanmean(pe)))
    log.info("ORT(live feat) vs p15_out %s", res["ort_on_live_vs_p15_out"])
    log.info("ORT(offline feat) vs p15_out %s", res["ort_on_offline_vs_p15_out"])
json.dump(res, open(OUT, "w"), indent=1, default=str)
log.info("JSON -> %s", OUT)
