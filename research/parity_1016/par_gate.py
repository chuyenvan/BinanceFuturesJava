#!/usr/bin/env python3
"""Lat cong gate: p15 offline (feature kieu backtest) vs live, so voi thr cua tung ung vien trong [GATE] log."""
import glob
import gzip
import io
import json
import logging
import os
import re
import sys
import zlib

import numpy as np
import pandas as pd
import onnxruntime as ort

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("gate")
EXP, SHADOW, SINCE_MS, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from par_feat_lib import FEATS, read_live  # noqa: E402

L = read_live(SHADOW, SINCE_MS)
E = pd.read_csv(EXP)
E["min"] = E.ts.astype("int64")
J = L.merge(E, on="min", suffixes=("_l", "_e"))
sess = ort.InferenceSession(SHADOW + "/storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx",
                            providers=["CPUExecutionProvider"])
nm = sess.get_inputs()[0].name
J["p15_off"] = sess.run(None, {nm: J[[f + "_e" for f in FEATS]].astype(np.float32).values})[0].reshape(-1)
# rel diff cho ho breadth
rel = {}
for f in ["advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance",
          "basketMomentum15M", "basketRsi14", "basketVolSpike", "momentum15M", "fundingRateRaw", "volatilityTermStructure"]:
    a, b = J[f + "_l"].astype(float), J[f + "_e"].astype(float)
    r = (a - b).abs() / (b.abs() + 1e-12)
    rel[f] = dict(med_rel=float(r.median()), p95_rel=float(r.quantile(.95)), mean_l=float(a.mean()), mean_e=float(b.mean()))
    log.info("%-24s rel med %.2e p95 %.2e mean live %.5g off %.5g", f, rel[f]["med_rel"], rel[f]["p95_rel"], rel[f]["mean_l"], rel[f]["mean_e"])
# [GATE] log: thr=[min..max] theo phut (dong phut M ung voi nen M-1)
pat = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):\d\d\.\d+ .*\[GATE\] .*thr=\[([0-9.]+)\.\.([0-9.]+)\] n_cand=(\d+) n_rej=(\d+) n_pass=(\d+)")
g = []
with open(SHADOW + "/app/logs/full.log", errors="ignore") as fh:
    for line in fh:
        if "[GATE]" not in line or "thr=[" not in line:
            continue
        m = pat.match(line)
        if not m:
            continue
        d, mo, y, hh, mi = m.group(1, 2, 3, 4, 5)
        t = pd.Timestamp("%s-%s-%s %s:%s" % (y, mo, d, hh, mi), tz="Asia/Ho_Chi_Minh").tz_convert("UTC")
        g.append(dict(min=int(t.value // 10**6) - 60000, thr_min=float(m.group(6)), thr_max=float(m.group(7)),
                      n_pass=int(m.group(10))))
G = pd.DataFrame(g).drop_duplicates("min", keep="last")
K = J.merge(G, on="min")
K["pass_live_any"] = K.p15_out >= K.thr_min
K["pass_off_any"] = K.p15_off >= K.thr_min
K["pass_live_all"] = K.p15_out >= K.thr_max
K["pass_off_all"] = K.p15_off >= K.thr_max
res = dict(n_joined=int(len(J)), n_gate=int(len(K)), rel=rel,
           log_npass_pos=int((K.n_pass > 0).sum()),
           live_any=int(K.pass_live_any.sum()), off_any=int(K.pass_off_any.sum()),
           flip_any=int((K.pass_live_any != K.pass_off_any).sum()),
           flip_all=int((K.pass_live_all != K.pass_off_all).sum()),
           margin_min=float((K.thr_min - K.p15_out).min()),
           p15_abs_diff=dict(med=float((K.p15_off - K.p15_out).abs().median()), p99=float((K.p15_off - K.p15_out).abs().quantile(.99)),
                             max=float((K.p15_off - K.p15_out).abs().max())))
log.info("GATE %s", json.dumps({k: v for k, v in res.items() if k != "rel"}))
top = K.assign(gap=K.thr_min - K.p15_out).nsmallest(5, "gap")[["min", "p15_out", "p15_off", "thr_min", "n_pass"]]
log.info("5 phut gan nguong nhat:\n%s", top.to_string(index=False))
json.dump(res, open(OUT, "w"), indent=1)
