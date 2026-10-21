"""AUDIT 1021 A1 — dau van (fingerprint) nguong tach cua model fold_20 (md5 8ec99757) so voi cac phien ban du lieu.
CHI DOC. Khong retrain. Nguong split cua XGBoost (hist/approx) = gia tri du lieu train (float32) -> neu 1 phien ban
du lieu chua dung cac gia tri do thi phien ban do (o cot do) = du lieu train that.
Input:
  NEW  = Kaggle gate-dataset-full / bdchain-gate-store: gate_dataset_full.csv (export 08-08, 1-phut)
  OLD  = gate15m_v2_full.csv (06-23, md5 7ef6f92b, nhip 15')
  STORE= ~/marketdump/market.bin (dump market_data_object Oracle 10-14)
"""
import json, logging, struct, sys
import numpy as np, pandas as pd, onnx
from onnx import numpy_helper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a1")
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"
NEW = sys.argv[1]
OLD = "/home/ubuntu/claude_master/v11_settle/raw/gate15m_v2_full.csv"
STORE = "/home/ubuntu/marketdump/market.bin"
OUT = sys.argv[2]
V3 = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
      "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
      "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
      "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
      "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear", "basketMomentum15M", "basketMomentum1H", "basketRsi14",
      "basketVolSpike"]
CUT = pd.Timestamp("2026-04-01").value // 10**6   # cutoff fold_20 (UTC, nhu train_gate_fold.py), purge 0


def read_bin(p):
    b = open(p, "rb").read()
    n = struct.unpack(">i", b[:4])[0]
    a = np.frombuffer(b[4:4 + n * 20], dtype=np.dtype([("ts", ">i8"), ("d", ">f4"), ("u", ">f4"), ("d15", ">f4")]))
    return pd.DataFrame({"ts": a["ts"].astype(np.int64), "d": a["d"].astype(np.float32), "d15": a["d15"].astype(np.float32)})


m = onnx.load(MODEL)
node = [n for n in m.graph.node if n.op_type == "TreeEnsembleRegressor"][0]
att = {a.name: a for a in node.attribute}
fid = np.array(att["nodes_featureids"].ints)
thr = np.array(att["nodes_values"].floats, dtype=np.float32)
modes = [s.decode() for s in att["nodes_modes"].strings]
br = np.array([md != "LEAF" for md in modes])
log.info("model nodes=%d branch=%d modes=%s", len(modes), br.sum(), sorted(set(modes)))
TH = {V3[f]: np.unique(thr[br & (fid == f)]) for f in range(33)}

log.info("load NEW %s", NEW)
N = pd.read_csv(NEW, usecols=["timestamp"] + V3)
log.info("NEW rows=%d", len(N))
O = pd.read_csv(OLD, usecols=["timestamp"] + V3)
log.info("OLD rows=%d", len(O))
S = read_bin(STORE)
res = {"model_md5": "8ec9975726270782692bfe00b39bd37f", "n_branch_nodes": int(br.sum()), "cut_ms": int(CUT),
       "rows_NEW": len(N), "rows_OLD": len(O), "rows_STORE": len(S)}


def f32(x):
    return np.asarray(x, dtype=np.float64).astype(np.float32)


def hits(th, col):
    u = np.unique(f32(col))
    ex = np.isin(th, u)
    mid = np.isin(th, ((u[1:].astype(np.float64) + u[:-1]) / 2).astype(np.float32)) if len(u) > 1 else np.zeros(len(th), bool)
    return ex, mid, len(u)


Ntr = N[N.timestamp < CUT]
O15 = O[O.timestamp < CUT]
N15 = Ntr[Ntr.timestamp.isin(O15.timestamp)]
yr = pd.to_datetime(Ntr.timestamp, unit="ms").dt.year.values
fp = {}
for c in V3:
    th = TH[c]
    if len(th) == 0:
        fp[c] = {"n_thr": 0}; continue
    exN, midN, nuN = hits(th, Ntr[c].values)
    exN15, _, _ = hits(th, N15[c].values)
    exO15, _, _ = hits(th, O15[c].values)
    # nam cua dong chua gia tri nguong (NEW full)
    vals = f32(Ntr[c].values)
    yh = {}
    for t in th[exN]:
        ys = np.unique(yr[vals == t])
        for y in ys: yh[int(y)] = yh.get(int(y), 0) + 1
    fp[c] = {"n_thr": int(len(th)), "n_unique_NEW": int(nuN),
             "hit_exact_NEW_full": round(float(exN.mean()), 4), "hit_mid_NEW_full": round(float(midN.mean()), 4),
             "hit_exact_NEW_on15grid": round(float(exN15.mean()), 4), "hit_exact_OLD_on15grid": round(float(exO15.mean()), 4),
             "n_thr_only_OLD15": int((exO15 & ~exN15).sum()), "n_thr_only_NEW15": int((exN15 & ~exO15).sum()),
             "years_of_hit_rows_NEW": yh}
    log.info("FP %-24s thr=%3d hitNEW=%.3f mid=%.3f | 15grid NEW=%.3f OLD=%.3f onlyOLD=%d onlyNEW=%d yrs=%s", c, len(th),
             exN.mean(), midN.mean(), exN15.mean(), exO15.mean(), fp[c]["n_thr_only_OLD15"], fp[c]["n_thr_only_NEW15"], yh)
res["fingerprint"] = fp

# so cot theo nam: NEW vs OLD (cung ts 15'), NEW vs STORE (momentum)
def cmp_cols(A, B, cols, tag):
    J = A.merge(B, on="timestamp", suffixes=("_a", "_b"))
    J["yr"] = pd.to_datetime(J.timestamp, unit="ms").dt.year
    out = {}
    for y, g in J.groupby("yr"):
        r = {"n": int(len(g))}
        allok = np.ones(len(g), bool)
        for c in cols:
            a = g[c + "_a"].values.astype(np.float64); b = g[c + "_b"].values.astype(np.float64)
            d = np.abs(a - b)
            ok = d <= 1e-6 * np.maximum(1.0, np.abs(b))
            allok &= ok
            rel = d / np.maximum(np.abs(b), 1e-12)
            r[c] = {"ok": round(float(ok.mean()), 5), "rel_med": float(np.median(rel)), "rel_p99": float(np.quantile(rel, 0.99)),
                    "abs_p99": float(np.quantile(d, 0.99))}
        r["row_all_ok"] = round(float(allok.mean()), 5)
        out[int(y)] = r
        bad = [c for c in cols if r[c]["ok"] < 0.999]
        log.info("%s %d n=%d row_all_ok=%.4f cot_lech(<99.9%%)=%s", tag, y, len(g), r["row_all_ok"],
                 {c: r[c]["ok"] for c in bad})
    return out

res["NEW_vs_OLD_15grid"] = cmp_cols(N, O, V3, "NEWvsOLD")
St = S.rename(columns={"ts": "timestamp", "d": "momentum1M", "d15": "momentum15M"})
res["NEW_vs_STORE_mom"] = cmp_cols(N[["timestamp", "momentum1M", "momentum15M"]], St, ["momentum1M", "momentum15M"], "NEWvsSTORE")
res["OLD_vs_STORE_mom"] = cmp_cols(O[["timestamp", "momentum1M", "momentum15M"]], St, ["momentum1M", "momentum15M"], "OLDvsSTORE")
# do phu: dong NEW khong co trong store
miss = ~N.timestamp.isin(S.ts)
res["NEW_rows_not_in_store"] = int(miss.sum())
res["NEW_rows_not_in_store_mom1M_zero_frac"] = float((N.momentum1M[miss] == 0).mean()) if miss.any() else None
json.dump(res, open(OUT, "w"), indent=1, default=str)
log.info("WROTE %s", OUT)
