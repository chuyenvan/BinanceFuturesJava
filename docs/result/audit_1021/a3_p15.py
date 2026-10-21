"""AUDIT 1021 A3/A4 — p15 cua fold_20 (ORT, CHI predict) tren cac phien ban feature + kiem doi chung dau van.
mode 'store': NEW vs NEW-voi-momentum-tu-STORE-hien-tai; doi chieu wfo_gate_pred (08-06) tren OOS fold_20; doi chung fingerprint.
mode 'replay': NEW vs REPLAY (ExportGateDataset tu store Oracle hien tai) — tung cot theo nam + p15.
"""
import json, logging, struct, sys
import numpy as np, pandas as pd, onnx, onnxruntime as ort
from scipy.stats import spearmanr, pearsonr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a3")
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"
V3 = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
      "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
      "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
      "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
      "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear", "basketMomentum15M", "basketMomentum1H", "basketRsi14",
      "basketVolSpike"]
CUT = pd.Timestamp("2026-04-01").value // 10**6
Q = 0.99995
mode, NEW, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])


def p15(df):
    X = df[V3].values.astype(np.float32)
    out = []
    for i in range(0, len(X), 500000):
        out.append(sess.run(None, {"float_input": X[i:i + 500000]})[0].ravel())
    return np.concatenate(out).astype(np.float64)


def year(ts):
    return pd.to_datetime(ts + 7 * 3600000, unit="ms").dt.year.values


def gate_pass(ts, p):
    """proxy gate: nguong ngay D = quantile Q cua p15 trong 90 ngay truoc (1-phut), warm-up 7 ngay."""
    day = (ts + 7 * 3600000) // 86400000
    ud = np.unique(day)
    thr = np.full(len(p), np.nan)
    order = np.argsort(ts); ts_s = ts[order]; p_s = p[order]; day_s = day[order]
    starts = np.searchsorted(day_s, ud)
    for k, D in enumerate(ud):
        lo = np.searchsorted(day_s, D - 90); hi = starts[k]
        if hi - lo < 7 * 1440: continue
        t = np.quantile(p_s[lo:hi], Q)
        e = starts[k + 1] if k + 1 < len(ud) else len(p_s)
        thr[order[starts[k]:e]] = t
    return thr


def compare_p15(ts, pa, pb, tag):
    out = {}
    y = year(pd.Series(ts))
    ta = gate_pass(ts, pa); tb = gate_pass(ts, pb)
    for Y in list(sorted(set(y))) + ["all"]:
        m = (y == Y) if Y != "all" else np.ones(len(y), bool)
        a, b = pa[m], pb[m]
        d = np.abs(a - b)
        va = ~np.isnan(ta[m])
        passA = (a > ta[m]) & va; passB = (b > tb[m]) & va
        passB_onA = (b > ta[m]) & va
        r = {"n": int(m.sum()), "exact_le1e7": round(float((d <= 1e-7).mean()), 5), "absd_med": float(np.median(d)),
             "absd_p99": float(np.quantile(d, 0.99)), "absd_max": float(d.max()),
             "pearson": float(pearsonr(a, b)[0]) if m.sum() > 2 else None,
             "spearman": float(spearmanr(a, b).correlation) if m.sum() > 2 else None,
             "n_pass_A": int(passA.sum()), "n_pass_B": int(passB.sum()), "n_pass_both": int((passA & passB).sum()),
             "n_pass_B_on_thrA": int(passB_onA.sum()), "n_pass_both_thrA": int((passA & passB_onA).sum())}
        out[str(Y)] = r
        log.info("%s %s %s", tag, Y, r)
    return out


res = {"mode": mode, "model_md5": "8ec99757", "Q": Q}
if mode == "store":
    N = pd.read_csv(NEW, usecols=["timestamp"] + V3)
    pN = p15(N)
    # 1) doi chieu wfo_gate_pred 08-06 (Kaggle funding-gate-wfo-pred)
    W = pd.read_csv("/home/ubuntu/claude_master/audit_1021/kg/funding-gate-wfo-pred/wfo_gate_pred.csv")
    J = pd.DataFrame({"timestamp": N.timestamp, "p": pN}).merge(W, on="timestamp")
    J["yq"] = pd.to_datetime(J.timestamp, unit="ms").dt.to_period("Q").astype(str)
    g = {}
    for q_, gg in J.groupby("yq"):
        d = np.abs(gg.p - gg.predReturn15M)
        g[q_] = {"n": int(len(gg)), "exact_le1e7": round(float((d <= 1e-7).mean()), 5), "absd_max": float(d.max()),
                 "pearson": float(pearsonr(gg.p, gg.predReturn15M)[0])}
    res["fold20_on_NEW_vs_wfo_gate_pred_0806_by_quarter_UTC"] = g
    log.info("vs wfo_gate_pred 08-06: %s", {k: (v["exact_le1e7"], round(v["pearson"], 5)) for k, v in g.items()})
    # 2) thay momentum tu STORE hien tai
    b = open("/home/ubuntu/marketdump/market.bin", "rb").read(); n = struct.unpack(">i", b[:4])[0]
    a = np.frombuffer(b[4:4 + n * 20], dtype=np.dtype([("ts", ">i8"), ("d", ">f4"), ("u", ">f4"), ("d15", ">f4")]))
    S = pd.DataFrame({"timestamp": a["ts"].astype(np.int64), "sd": a["d"].astype(np.float32), "sd15": a["d15"].astype(np.float32)})
    M = N.merge(S, on="timestamp", how="left")
    has = M.sd.notna().values
    M2 = M.copy()
    M2.loc[has, "momentum1M"] = M2.loc[has, "sd"].astype(np.float64)
    M2.loc[has, "momentum15M"] = M2.loc[has, "sd15"].astype(np.float64)
    m5 = M2.momentum5M.values.astype(np.float32); m15 = M2.momentum15M.values.astype(np.float32)
    acc = (m5 - m15).astype(np.float32)
    M2.loc[has, "momentumAcceleration"] = acc[has].astype(np.float64)
    pS = p15(M2)
    tr = (N.timestamp.values < CUT)
    res["rows_NEW_in_store"] = int(has.sum()); res["rows_NEW"] = len(N)
    res["NEW_vs_NEWmomSTORE"] = compare_p15(N.timestamp.values, pN, pS, "NEWvsSTOREmom")
    res["NEW_vs_NEWmomSTORE_train_window_only"] = compare_p15(N.timestamp.values[tr], pN[tr], pS[tr], "NEWvsSTOREmom_train")
    np.save(OUT.replace(".json", "_pNEW.npy"), pN.astype(np.float32))
elif mode == "replay":
    RP = sys.argv[4]
    N = pd.read_csv(NEW, usecols=["timestamp"] + V3)
    P = pd.read_csv(RP, usecols=["timestamp"] + V3)
    log.info("NEW=%d REPLAY=%d", len(N), len(P))
    J = N.merge(P, on="timestamp", suffixes=("_n", "_r"))
    res["rows_join"] = len(J); res["rows_NEW_window"] = int(((N.timestamp >= P.timestamp.min()) & (N.timestamp <= P.timestamp.max())).sum())
    res["rows_REPLAY"] = len(P)
    y = year(J.timestamp)
    cols = {}
    for Y in sorted(set(y)):
        m = y == Y; r = {"n": int(m.sum())}; allok = np.ones(m.sum(), bool)
        for c in V3:
            a = J[c + "_n"].values[m]; bb = J[c + "_r"].values[m]
            d = np.abs(a - bb); ok = d <= 1e-6 * np.maximum(1.0, np.abs(a)); allok &= ok
            rel = d / np.maximum(np.abs(a), 1e-12)
            r[c] = {"ok": round(float(ok.mean()), 5), "rel_med": float(np.median(rel)), "rel_p99": float(np.quantile(rel, 0.99))}
        r["row_all_33_ok"] = round(float(allok.mean()), 5)
        cols[int(Y)] = r
        log.info("NEWvsREPLAY %d n=%d row_all=%.5f lech=%s", Y, m.sum(), r["row_all_33_ok"],
                 {c: r[c]["ok"] for c in V3 if r[c]["ok"] < 0.9999})
    res["NEW_vs_REPLAY_by_year"] = cols
    pN = p15(J.rename(columns={c + "_n": c for c in V3}))
    pR = p15(J.rename(columns={c + "_r": c for c in V3}))
    res["p15_NEW_vs_REPLAY"] = compare_p15(J.timestamp.values, pN, pR, "p15 NEWvsREPLAY")
json.dump(res, open(OUT, "w"), indent=1, default=str)
log.info("WROTE %s", OUT)
