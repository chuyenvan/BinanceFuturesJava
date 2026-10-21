"""AUDIT 1021 A4 — so 33 cot feature cua file train (NEW = gate_dataset_full 08-08) voi REPLAY ExportGateDataset tu store
Oracle hien tai (cac cua so + doan lien tuc), theo nam; p15 fold_20 tren 2 phien ban; nguong proxy gate q=0.99995 (90 ngay
truoc, tinh tren chuoi p15 NEW day du) ap cho ca 2 -> doi PASS. CHI DOC / predict."""
import glob, json, logging, sys
import numpy as np, pandas as pd, onnxruntime as ort
from scipy.stats import spearmanr, pearsonr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a4")
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"
V3 = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
      "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
      "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
      "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
      "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear", "basketMomentum15M", "basketMomentum1H", "basketRsi14",
      "basketVolSpike"]
Q = 0.99995
sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])


def p15(df):
    X = df[V3].values.astype(np.float32)
    return np.concatenate([sess.run(None, {"float_input": X[i:i + 500000]})[0].ravel()
                           for i in range(0, len(X), 500000)]).astype(np.float64)


def gate_pass(ts, p):
    """nguong proxy ngay D = quantile Q cua p15 trong 90 ngay truoc (1-phut), warm-up 7 ngay (giong a3_p15)."""
    day = (ts + 7 * 3600000) // 86400000
    order = np.argsort(ts); p_s = p[order]; day_s = day[order]
    ud = np.unique(day_s); starts = np.searchsorted(day_s, ud)
    thr = np.full(len(p), np.nan)
    for k, D in enumerate(ud):
        lo = np.searchsorted(day_s, D - 90); hi = starts[k]
        if hi - lo < 7 * 1440: continue
        e = starts[k + 1] if k + 1 < len(ud) else len(p_s)
        thr[order[starts[k]:e]] = np.quantile(p_s[lo:hi], Q)
    return thr

NEW, OUT = sys.argv[1], sys.argv[2]
FILES = sys.argv[3:]
LAB = "label_oldbasket"
N = pd.read_csv(NEW, usecols=["timestamp"] + V3 + [LAB])
pN = p15(N)
thr = gate_pass(N.timestamp.values, pN)
NN = N.assign(pN=pN, thr=thr)
res = {"new_rows": len(N), "files": {}}
allJ = []
for f in FILES:
    P = pd.read_csv(f, usecols=["timestamp"] + V3 + [LAB], on_bad_lines="skip").dropna()
    P = P.drop_duplicates("timestamp")
    # bo 1 dong cuoi neu file dang ghi do dang
    J = NN.merge(P, on="timestamp", suffixes=("_n", "_r"))
    J["src"] = f.split("/")[-1]
    allJ.append(J)
    res["files"][f.split("/")[-1]] = {"rows_replay": len(P), "rows_join": len(J),
        "ts_min": int(P.timestamp.min()), "ts_max": int(P.timestamp.max())}
J = pd.concat(allJ, ignore_index=True)
J["yr"] = pd.to_datetime(J.timestamp + 7 * 3600000, unit="ms").dt.year
pR = p15(J.rename(columns={c + "_r": c for c in V3}))
J["pR"] = pR


def table(G, tag):
    r = {"n": int(len(G))}
    allok = np.ones(len(G), bool)
    for c in V3:
        a = G[c + "_n"].values; b = G[c + "_r"].values
        d = np.abs(a - b); ok = d <= 1e-6 * np.maximum(1.0, np.abs(a)); allok &= ok
        rel = d / np.maximum(np.abs(a), 1e-12)
        r[c] = {"ok": round(float(ok.mean()), 6), "rel_med": float(np.median(rel)), "rel_p99": float(np.quantile(rel, 0.99)),
                "absd_max": float(d.max())}
    r["row_all_33_ok"] = round(float(allok.mean()), 6)
    a, b = G[LAB + "_n"].values, G[LAB + "_r"].values; d = np.abs(a - b)
    r[LAB] = {"ok": round(float((d <= 1e-6 * np.maximum(1.0, np.abs(a))).mean()), 6), "absd_max": float(d.max())}
    a, b = G.pN.values, G.pR.values; d = np.abs(a - b); v = ~np.isnan(G.thr.values)
    pa = (a > G.thr.values) & v; pb = (b > G.thr.values) & v
    r["p15"] = {"exact_le1e7": round(float((d <= 1e-7).mean()), 6), "absd_p99": float(np.quantile(d, 0.99)),
                "absd_max": float(d.max()), "pearson": float(pearsonr(a, b)[0]), "spearman": float(spearmanr(a, b).correlation),
                "n_pass_train": int(pa.sum()), "n_pass_replay": int(pb.sum()), "n_pass_both": int((pa & pb).sum()),
                "n_with_thr": int(v.sum())}
    log.info("%s n=%d row_all=%.6f p15=%s lech=%s", tag, len(G), r["row_all_33_ok"], r["p15"],
             {c: r[c]["ok"] for c in V3 if r[c]["ok"] < 0.9999})
    return r

res["by_year"] = {int(y): table(g, "year %d" % y) for y, g in J.groupby("yr")}
res["by_file"] = {s: table(g, s) for s, g in J.groupby("src")}
res["all"] = table(J, "ALL")
json.dump(res, open(OUT, "w"), indent=1, default=str)
log.info("WROTE %s", OUT)
