"""AUDIT 1021 A5 — doi chung cho dau van nguong: ti le trung cua nguong THAT vs nguong DICH +-k buoc 1e-8 (gia tri in %.8f
lan can) tren cung du lieu train NEW. Neu trung that ~1 va doi chung << 1 thi bang chung khong do ngau nhien."""
import json, logging, sys
import numpy as np, pandas as pd, onnx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a5")
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"
V3 = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
      "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
      "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
      "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
      "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear", "basketMomentum15M", "basketMomentum1H", "basketRsi14",
      "basketVolSpike"]
NEW, OUT = sys.argv[1], sys.argv[2]
CUT = pd.Timestamp("2026-04-01").value // 10**6
node = [n for n in onnx.load(MODEL).graph.node if n.op_type == "TreeEnsembleRegressor"][0]
att = {a.name: a for a in node.attribute}
fid = np.array(att["nodes_featureids"].ints); thr = np.array(att["nodes_values"].floats, dtype=np.float32)
br = np.array([m.decode() != "LEAF" for m in att["nodes_modes"].strings])
N = pd.read_csv(NEW, usecols=["timestamp"] + V3)
N = N[N.timestamp < CUT]
res = {"n_train_rows": len(N), "per_feature": {}}
tot_real = tot_ctrl = n_real = n_ctrl = 0
for f, c in enumerate(V3):
    th = np.unique(thr[br & (fid == f)])
    if len(th) == 0: continue
    u = np.unique(N[c].values.astype(np.float32))
    real = np.isin(th, u).mean()
    base = np.round(th.astype(np.float64), 8)
    ctrl = []
    for k in (-3, -2, -1, 1, 2, 3):
        cand = (base + k * 1e-8).astype(np.float32)
        ctrl.append(np.isin(cand, u).mean())
    res["per_feature"][c] = {"n_thr": int(len(th)), "hit_real": round(float(real), 4), "hit_ctrl_mean": round(float(np.mean(ctrl)), 4),
                             "n_unique_train": int(len(u))}
    tot_real += real * len(th); n_real += len(th); tot_ctrl += np.mean(ctrl) * len(th)
    log.info("%-24s thr=%3d real=%.3f ctrl=%.3f", c, len(th), real, np.mean(ctrl))
res["pooled"] = {"n_thr": int(n_real), "hit_real": round(float(tot_real / n_real), 4), "hit_ctrl": round(float(tot_ctrl / n_real), 4)}
log.info("POOLED %s", res["pooled"])
json.dump(res, open(OUT, "w"), indent=1)
