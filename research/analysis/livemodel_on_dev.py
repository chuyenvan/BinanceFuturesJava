#!/usr/bin/env python3
"""LIVEMODEL_ON_DEV — chạy model LIVE (fold_20 ONNX) trên feature DEV (gate_dataset_full) để tách
nguyên nhân p15 live != DEV: model hay feature?

Logic: nếu fold_20 trên feature DEV cho ra đuôi p15 (max ~11.95%, >=2.947% co mau) GIỐNG pred.bin DEV
=> model OK, thu pham la FEATURE (pipeline live tinh feature khac DEV). Neu fold_20 van phang ~2%
=> model (fold_20) la thu pham.
Doi chieu: (a) pred.bin DEV (p15 thuc te backtest) theo nam; (b) fold_20 tren feature DEV theo nam.
"""
import os, sys, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STORE = os.path.expanduser("~/claudedata/gate_dataset_full.csv.gz")
ONNX = os.path.expanduser("~/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx")
PREDBIN = "/home/ubuntu/wfo_ds_x1_2021/pred.bin"
SEAL = pd.Timestamp("2026-01-01", tz="Asia/Ho_Chi_Minh").value // 10**6

V3FULL = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
    "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance",
    "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
TAIL = 2.947  # % (nguong duoi DEV, PASS1 §4)


def load_predbin():
    raw = open(PREDBIN, "rb").read()
    n = int.from_bytes(raw[:4], "big")
    a = np.frombuffer(raw[4:4 + n * 16], dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")]))
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "p15": a["p15"].astype(np.float64)})
    df = df[df["ts"] < SEAL]
    return df


def main():
    import onnxruntime as ort
    sess = ort.InferenceSession(ONNX, providers=["CPUExecutionProvider"])
    nm = sess.get_inputs()[0].name

    # 1) fold_20 tren feature DEV
    ts_all, p_all = [], []
    for ch in pd.read_csv(STORE, usecols=["timestamp"] + V3FULL, chunksize=500_000):
        ch = ch[ch["timestamp"] < SEAL]
        if not len(ch):
            continue
        X = ch[V3FULL].to_numpy(dtype="float32")
        y = sess.run(None, {nm: X})[0].reshape(-1).astype(np.float64)
        ts_all.append(ch["timestamp"].to_numpy(np.int64))
        p_all.append(y)
    ts = np.concatenate(ts_all)
    p = np.concatenate(p_all) * 100.0  # %
    lm = pd.DataFrame({"ts": ts, "p15": p})
    lm["yr"] = pd.to_datetime(lm["ts"], unit="ms").dt.year

    # 2) pred.bin DEV
    dev = load_predbin()
    dev["yr"] = pd.to_datetime(dev["ts"], unit="ms").dt.year

    def summ(df, tag):
        out = {"tag": tag, "n": int(len(df)),
               "p50": float(np.median(df["p15"])), "p99": float(np.quantile(df["p15"], 0.99)),
               "max": float(df["p15"].max()), "n_tail": int((df["p15"] >= TAIL).sum())}
        byyr = {}
        for y, g in df.groupby("yr"):
            byyr[int(y)] = dict(n=int(len(g)), p50=float(np.median(g["p15"])), p99=float(np.quantile(g["p15"], 0.99)),
                                max=float(g["p15"].max()), n_tail=int((g["p15"] >= TAIL).sum()))
        out["by_year"] = byyr
        return out

    s1 = summ(lm, "fold20_on_DEV_features")
    s2 = summ(dev, "predbin_DEV")
    print(json.dumps(s1, indent=1))
    print(json.dumps(s2, indent=1))

    # overlap check: pearson fold20(dev feat) vs predbin p15 tren cung ts
    m = pd.merge(lm[["ts", "p15"]], dev[["ts", "p15"]], on="ts", suffixes=("_lm", "_dev"), how="inner")
    if len(m):
        print("pearson(fold20_on_DEV, predbin_DEV) =", round(float(np.corrcoef(m["p15_lm"], m["p15_dev"])[0, 1]), 5),
              "n=", len(m))
        print("max fold20_on_DEV =", round(float(m["p15_lm"].max()), 4), " max predbin_DEV =", round(float(m["p15_dev"].max()), 4))


if __name__ == "__main__":
    main()
