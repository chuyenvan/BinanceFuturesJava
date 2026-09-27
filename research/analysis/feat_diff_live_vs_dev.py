#!/usr/bin/env python3
"""
feat_diff_live_vs_dev.py — So 33 feature cua INSTRUMENT LIVE (feat_dump_*.csv.gz) voi EXPORT DEV.

Muc dich: chot gia thuyet (iii) "PIPELINE/FEATURE LIVE KHAC EXPORT DEV" (xem
docs/result/RESULT_P15_SOURCE.md §3.2/§4). Align theo (ts, symbol), so tung feature:
mean/std/quantile/NaN-rate/rank-corr (spearman) => chi ra feature nao lech + muc lech.

NGUON DEV: store offline ma fold_20 dung: ~/claudedata/gate15m_v2_full.csv
(2.846.462 dong 2021-01->2026-06, cot: timestamp + 33 feature + volatilityRegime + label_*).
Luu y: THU TU COT TRONG CSV KHAC thu tu V3FULL — tool nay align theo TEN cot (V3FULL), KHONG theo vi tri.
CSV DEV khong co cot symbol (feature muc THI TRUONG, anchor BTCUSDT) => symbol DEV = --anchor.

Dung:
  python3 feat_diff_live_vs_dev.py --live /path/feat_dump_x.csv.gz \
      --dev ~/claudedata/gate15m_v2_full.csv [--top 12] [--out report.md]
  python3 feat_diff_live_vs_dev.py --self-test        # chay thu offline, KHONG can live dump

Output nho (<= ~60 dong). KHONG doc/ghi gi tren host LIVE.
"""
import argparse
import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# Thu tu V3FULL — COPY tu OnnxInferenceManager.extractFeaturesV3Full:67-80 (nguon su that).
V3FULL = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance",
    "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
assert len(V3FULL) == 33, len(V3FULL)
QS = [0.05, 0.25, 0.50, 0.75, 0.95, 0.99]


def read_live(path, anchor="BTCUSDT"):
    df = pd.read_csv(path, compression="gzip" if path.endswith(".gz") else None)
    need = {"ts", "symbol"} | set(V3FULL)
    miss = need - set(df.columns)
    if miss:
        sys.exit(f"LIVE dump thieu cot: {sorted(miss)}")
    df["ts"] = df["ts"].astype("int64")
    df = df[df["symbol"] == anchor] if anchor else df
    return df.sort_values("ts").reset_index(drop=True)


def read_dev_window(path, ts_want, anchor="BTCUSDT", chunksize=500_000, tol_ms=0):
    """Stream dev CSV, chi giu dong co timestamp khop (hoac trong +-tol) tap ts cua live."""
    want = np.sort(np.asarray(ts_want, dtype="int64"))
    keep, scanned = [], 0
    for ch in pd.read_csv(path, usecols=lambda c: c in ({"timestamp", "symbol"} | set(V3FULL)),
                          chunksize=chunksize):
        scanned += len(ch)
        if tol_ms > 0:
            lo, hi = want.min() - tol_ms, want.max() + tol_ms
            ch = ch[(ch["timestamp"] >= lo) & (ch["timestamp"] <= hi)]
        m = np.isin(ch["timestamp"].to_numpy(dtype="int64"), want)
        if m.any():
            keep.append(ch.loc[m])
    if not keep:
        return pd.DataFrame(columns=["timestamp"] + V3FULL), scanned
    dev = pd.concat(keep, ignore_index=True)
    dev["symbol"] = dev["symbol"] if "symbol" in dev.columns else anchor
    return dev, scanned


def feature_table(live, dev, top):
    n = min(len(live), len(dev))
    rows = []
    for f in V3FULL:
        a = pd.to_numeric(live[f], errors="coerce").to_numpy(dtype="float64")
        b = pd.to_numeric(dev[f], errors="coerce").to_numpy(dtype="float64")
        ok = np.isfinite(a) & np.isfinite(b)
        nan_rate = 1.0 - ok.mean() if len(ok) else 1.0
        if ok.sum() < 3:
            rows.append(dict(feature=f, n=int(ok.sum()), nan=nan_rate, spearman=np.nan,
                             shift_sd=np.nan, qmax_rel=np.nan, score=np.inf))
            continue
        a2, b2 = a[ok], b[ok]
        sd = b2.std()
        shift = abs(a2.mean() - b2.mean()) / (sd + 1e-12)
        qa, qb = np.quantile(a2, QS), np.quantile(b2, QS)
        iqr = np.quantile(b2, 0.75) - np.quantile(b2, 0.25)
        qrel = float(np.max(np.abs(qa - qb)) / (abs(iqr) + 1e-12))
        rho = spearmanr(a2, b2).statistic if (len(a2) > 2 and a2.std() > 0 and b2.std() > 0) else np.nan
        rows.append(dict(feature=f, n=int(ok.sum()), nan=nan_rate, spearman=rho,
                         shift_sd=shift, qmax_rel=qrel,
                         score=float(shift + 0.5 * qrel + (0.0 if np.isfinite(rho) and rho > 0.99 else 1.0))))
    t = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    return t.head(top).assign(rank=range(1, min(top, len(t)) + 1)), t


def fmt(t, n_live, n_dev, matched, anchor, src):
    out = []
    out.append(f"# feat_diff live_vs_dev — live n={n_live} dev n={n_dev} matched={matched} anchor={anchor}")
    out.append(f"# dev source: {src}")
    out.append("rank feature                       n     NaN%    spearman  shift_sd  qmax_rel  score")
    for _, r in t.iterrows():
        out.append(f"{int(r['rank']):>3}  {r['feature']:<28} {int(r['n']):>6} {100*r['nan']:>6.1f} "
                   f"{r['spearman']:>9.4f} {r['shift_sd']:>9.2f} {r['qmax_rel']:>9.2f} {r['score']:>6.2f}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live")
    ap.add_argument("--dev", default=os.path.expanduser("~/claudedata/gate15m_v2_full.csv"))
    ap.add_argument("--anchor", default="BTCUSDT")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--tol-ms", type=int, default=0, help="khop ts trong +-tol ms (0 = khop chinh xac)")
    ap.add_argument("--chunksize", type=int, default=500_000)
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test(a)

    if not a.live or not os.path.exists(a.live):
        sys.exit("Thieu --live <feat_dump_*.csv.gz> (chua thu thap duoc). Dung --self-test de chay thu.")
    live = read_live(a.live, a.anchor)
    dev, scanned = read_dev_window(a.dev, live["ts"].to_numpy(), a.anchor, a.chunksize, a.tol_ms)
    if dev.empty:
        sys.exit(f"KHONG khop ts nao (dev quet {scanned} dong). Kiem cua so thoi gian / --tol-ms.")
    dev = dev.groupby("timestamp", as_index=False).first().rename(columns={"timestamp": "ts"})
    m = live.merge(dev, on="ts", how="inner", suffixes=("_live", "_dev"))
    lv = live.set_index("ts").loc[m["ts"], V3FULL].reset_index(drop=True)
    dv = dev.set_index("ts").loc[m["ts"], V3FULL].reset_index(drop=True)
    top, allt = feature_table(lv, dv, a.top)
    rep = fmt(top, len(live), len(dev), len(m), a.anchor, a.dev)
    suspects = allt[(allt.shift_sd > 0.5) | (allt.qmax_rel > 1.0) | (allt.spearman < 0.9)]["feature"].tolist()
    rep += "\n# NGHI PHAM CHINH (shift_sd>0.5 hoac qmax_rel>1.0 hoac spearman<0.9): " + (", ".join(suspects) or "(khong)")
    print(rep)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(rep + "\n")
    return 0


def self_test(a):
    """Chay thu OFFLINE khong can live dump: lay 1 cua so DEV lam 'live', roi PHA 2 feature co chu dich."""
    dev = pd.read_csv(a.dev, usecols=["timestamp"] + V3FULL, nrows=400_000)
    w = dev[(dev.timestamp >= dev.timestamp.max() - 30 * 24 * 3600 * 1000)].copy()
    if len(w) < 50:
        w = dev.tail(2000).copy()
    fake = w.rename(columns={"timestamp": "ts"})
    fake.insert(1, "symbol", a.anchor)
    fake["p15_out"] = 0.0
    fake["basketVolSpike"] = fake["basketVolSpike"] * 3.0     # PHA co chu y
    fake["fundingRateRaw"] = 0.0                              # PHA co chu y
    p = "/tmp/feat_diff_selftest_live.csv.gz"
    fake.to_csv(p, index=False, compression="gzip")
    a.live, a.top, a.out = p, 8, None
    live = read_live(p, a.anchor)
    dv, _ = read_dev_window(a.dev, live["ts"].to_numpy(), a.anchor, a.chunksize, 0)
    dv = dv.groupby("timestamp", as_index=False).first().rename(columns={"timestamp": "ts"})
    m = live.merge(dv, on="ts", how="inner", suffixes=("_live", "_dev"))
    lv = live.set_index("ts").loc[m["ts"], V3FULL].reset_index(drop=True)
    dv2 = dv.set_index("ts").loc[m["ts"], V3FULL].reset_index(drop=True)
    top, allt = feature_table(lv, dv2, a.top)
    print(fmt(top, len(live), len(dv), len(m), a.anchor, a.dev + " [SELF-TEST]"))
    print("# ky vong: basketVolSpike + fundingRateRaw nam dau bang (da pha co chu y).")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
