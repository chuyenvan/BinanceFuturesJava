#!/usr/bin/env python3
"""Chan doan P1: feature nao gay lech p15; lech theo thoi gian; lech do lag phut?"""
import glob, json, sys
import numpy as np, pandas as pd, onnxruntime as ort
sys.path.insert(0, "/home/ubuntu/claude_master/parity_1020")
W = "/home/ubuntu/claude_master/parity_1020"
exec(open(W + "/par_a.py").read().split("res = {}")[0])  # import helpers + FEATS
L = pd.concat([d for d in (read_gz(p) for p in sorted(glob.glob(W + "/raw242/dumps/feat_dump_*.csv.gz"))) if d is not None], ignore_index=True)
L["min"] = (L.ts // 60000) * 60000
L = L.drop_duplicates("min", keep="last"); L = L[L["min"] >= T0]
E = pd.read_csv(W + "/devexport_1016_1020_md.csv.gz"); E["min"] = E.ts.astype("int64")
J = L.merge(E, on="min", suffixes=("_l", "_e"))
sess = ort.InferenceSession(W + "/raw242/models/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx", providers=["CPUExecutionProvider"])
nm = sess.get_inputs()[0].name
def pred(X): return sess.run(None, {nm: X.astype(np.float32)})[0].reshape(-1)
Xl = J[[f + "_l" for f in FEATS]].values; Xe = J[[f + "_e" for f in FEATS]].values
pl = J.p15_out.values; pe = pred(Xe)
def mrel(p): r = np.abs(pl - p) / np.abs(p); return float(np.median(r)), float((r <= 1e-3).mean())
print("base off", mrel(pe))
groups = {"breadth": ["advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance"],
          "basket": ["basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"],
          "funding": ["fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend"],
          "mom15": ["momentum15M", "momentumAcceleration"],
          "mom1m": ["momentum1M"]}
out = {}
for g, fs in groups.items():
    X = Xe.copy()
    for f in fs: X[:, FEATS.index(f)] = Xl[:, FEATS.index(f)]
    out["swap_" + g] = mrel(pred(X)); print("swap live->off", g, out["swap_" + g])
for g, fs in groups.items():
    X = Xl.copy()
    for f in fs: X[:, FEATS.index(f)] = Xe[:, FEATS.index(f)]
    r = np.abs(pl - pred(X)) / np.abs(pl); out["only_" + g] = (float(np.median(r)), float((r <= 1e-3).mean())); print("only off group in live", g, out["only_" + g])
# single-feature importance (only this feature from offline)
imp = {}
for f in FEATS:
    X = Xl.copy(); X[:, FEATS.index(f)] = Xe[:, FEATS.index(f)]
    r = np.abs(pl - pred(X)) / np.abs(pl); imp[f] = float(np.median(r))
print("single-feature offline-in-live median rel:", {k: "%.2e" % v for k, v in sorted(imp.items(), key=lambda x: -x[1])[:12]})
# theo ngay / gio
J["rel"] = np.abs(pl - pe) / np.abs(pe)
J["day"] = pd.to_datetime(J["min"] + 7 * 3600000, unit="ms").dt.strftime("%m-%d")
J["hr"] = pd.to_datetime(J["min"] + 7 * 3600000, unit="ms").dt.strftime("%m-%d %H")
print(J.groupby("day").rel.agg(["median", lambda x: (x <= 1e-3).mean(), "size"]))
hh = J.groupby("hr").rel.median()
print("hours med rel: first 12", hh.head(12).round(5).to_dict())
# lag test cac feature lech
Eidx = E.set_index("min")
for f in ["advanceDeclineRatio", "percentAboveMA20", "marketBreadthStrength", "btcDominance", "basketVolSpike", "basketRsi14", "fundingRateRaw", "momentum15M", "volumeRatioUpDown"]:
    rr = {}
    for k in (-2, -1, 0, 1, 2):
        e = Eidx[f].reindex(J["min"] + k * 60000).values
        a = J[f + "_l"].values
        d = np.abs(a - e) / (np.abs(e) + 1e-12)
        rr[k] = "%.2e/%.3f" % (np.nanmedian(d), np.nanmean(d <= 1e-6))
    print("LAG", f, rr)
# vi du vai phut
s = J.iloc[[0, 1000, 3000, 5000]]
for _, r in s.iterrows():
    print(f7(int(r["min"])), {f: (round(r[f + "_l"], 6), round(r[f + "_e"], 6)) for f in ["advanceDeclineRatio", "percentAboveMA20", "btcDominance", "basketVolSpike", "fundingRateRaw", "fundingRateAvg24H"]})
json.dump(dict(groups=out, single=imp), open(W + "/diag1.json", "w"), indent=1)
