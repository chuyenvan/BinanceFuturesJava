"""H1 cong P1 — tai tao p15 (predReturn15M) cua mot doan DEV tu feature store + model ONNX
cua fold tuong ung, roi doi chieu voi claudedata/wfo_gate_pred.csv.

Muc dich: chung minh duong tai tao p15 KHONG can replay Aerospike (replay ~30-45s/ngay).
Nguon: ExportGateDataset -> claudedata/gate_dataset_full.csv.gz (2021-01-01 .. 2026-06-30 21:00 UTC)
Model: claudedata/wfo_models/fold_<k>/Model_Regressor_Return15M.onnx (WFOGateRunner sinh, expanding)

usage: h1_p15_repro.py <fold_idx> <ts_lo_ms> <ts_hi_ms>
vd (2025-12, fold 18 = train[->20251001] OOS[20251001->20260101]):
    h1_p15_repro.py 18 1764547200000 1767225600000
"""
import gzip
import logging
import sys

import numpy as np
import onnxruntime as ort
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("h1p15")

STORE = "/home/ubuntu/claudedata/gate_dataset_full.csv.gz"
GATE_CSV = "/home/ubuntu/claudedata/wfo_gate_pred.csv"
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_%d/Model_Regressor_Return15M.onnx"

# Thu tu V3FULL — copy y nguyen tu java/simulator/train_gate_fold.py (nguon su that).
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


def load_window(lo, hi):
    cols = ["timestamp"] + V3FULL
    parts = []
    with gzip.open(STORE, "rt") as fh:
        for ch in pd.read_csv(fh, usecols=cols, chunksize=400_000):
            m = (ch.timestamp >= lo) & (ch.timestamp < hi)
            if m.any():
                parts.append(ch.loc[m])
            if ch.timestamp.iloc[-1] >= hi:
                break
    if not parts:
        LOG.error("feature store KHONG co dong nao trong [%d, %d)", lo, hi)
        sys.exit(1)
    d = pd.concat(parts, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    LOG.info("feature store: %d dong trong cua so, ts %d .. %d", len(d), d.timestamp.iloc[0], d.timestamp.iloc[-1])
    return d


def predict(fold, d):
    sess = ort.InferenceSession(MODEL % fold, providers=["CPUExecutionProvider"])
    name = sess.get_inputs()[0].name
    x = d[V3FULL].to_numpy(dtype=np.float32)
    out = sess.run(None, {name: x})[0]
    return np.asarray(out, dtype=np.float32).reshape(-1)


def reference(lo, hi):
    ref = pd.read_csv(GATE_CSV, dtype={"timestamp": np.int64})
    ref = ref[(ref.timestamp >= lo) & (ref.timestamp < hi)].reset_index(drop=True)
    LOG.info("wfo_gate_pred.csv: %d dong trong cua so", len(ref))
    return ref


def main():
    fold, lo, hi = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    d = load_window(lo, hi)
    ref = reference(lo, hi)
    j = pd.merge(d[["timestamp"]].assign(p15_new=predict(fold, d)), ref, on="timestamp", how="inner")
    LOG.info("ghep duoc %d dong (store %d / ref %d)", len(j), len(d), len(ref))
    if len(j) == 0:
        LOG.error("**FAIL** khong ghep duoc dong nao")
        sys.exit(1)
    a = j.p15_new.to_numpy(dtype=np.float64)
    b = j.predReturn15M.to_numpy(dtype=np.float64)
    dmax = float(np.max(np.abs(a - b)))
    s_new = pd.Series(a).map(lambda v: "%.8f" % v)
    s_ref = pd.Series(b).map(lambda v: "%.8f" % v)
    exact = int((s_new.to_numpy() == s_ref.to_numpy()).sum())
    rho = float(pd.Series(a).corr(pd.Series(b), method="spearman"))
    LOG.info("n=%d  max|d|=%.3e  chuoi %%.8f trung=%d/%d (%.4f%%)  spearman=%.6f",
             len(j), dmax, exact, len(j), 100.0 * exact / len(j), rho)
    nbig = int((np.abs(a - b) > 1e-6).sum())
    LOG.info("so dong lech THAT (|d| > 1e-6, ngoai nhieu lam tron %%.8f) = %d/%d (%.4f%%)",
             nbig, len(j), 100.0 * nbig / len(j))
    # Cong theo PREREG_H1 muc 2: spearman >= 0.999. Byte-identity bao rieng (lam tron %.8f
    # cua float32 lam ~5-8%% dong lech chu so cuoi — KHONG phai lech mo hinh).
    ok = rho >= 0.999
    LOG.info("CONG P1 fold=%d: %s", fold, "PASS" if ok else "**FAIL**")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
