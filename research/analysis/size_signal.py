"""Truoc khi bat BAT KY co che sizing nao: bien dung de size co mang tin hieu khong?
Test offline tren printDone.csv cua C2b (DEV) — khong ton mot lan chay sim nao.
Neu spearman ~ 0 va roi_w <= roi goc => sizing theo bien do la sizing tren NHIEU."""
import numpy as np, pandas as pd
from scipy.stats import spearmanr

df = pd.read_csv("/home/ubuntu/java/devrun/C2b/storage/printDone.csv")
df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
for c in ["symbolPred", "margin", "pnl", "pred15m", "risk4h", "dow", "up", "dow15m", "funding", "volume"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df[df.margin > 0].copy()
df["roi"] = df.pnl / df.margin
df["p6"] = 1 - df.symbolPred
df["inv_risk4h"] = -df.risk4h          # risk thap -> size to
df["inv_vol"] = -df.dow15m.abs()       # bien dong 15m thap -> size to
base = df.roi.mean()
print("n=%d  roi_mean_goc=%+.5f  winrate=%.3f\n" % (len(df), base, (df.roi > 0).mean()))

print("%-14s %8s %8s   %10s %10s %10s" % ("bien", "rho", "p", "roi_w(top-tilt)", "delta", "monotone?"))
for c in ["p6", "pred15m", "risk4h", "inv_risk4h", "dow", "up", "dow15m", "inv_vol", "funding", "volume"]:
    s = df[[c, "roi"]].dropna()
    if len(s) < 100:
        continue
    rho, pv = spearmanr(s[c], s.roi)
    # trong so tuyen tinh theo rank cua bien, trung tinh don bay (mean w = 1)
    r = s[c].rank(pct=True)
    w = 0.5 + r                      # 0.5x .. 1.5x, mean ~ 1
    w = w / w.mean()
    roi_w = (s.roi * w).mean()
    # kiem don dieu tho: roi trung binh cua 5 ngu phan
    qs = pd.qcut(s[c], 5, labels=False, duplicates="drop")
    m = s.groupby(qs).roi.mean().values
    mono = "TANG" if np.all(np.diff(m) > -0.005) else ("GIAM" if np.all(np.diff(m) < 0.005) else "khong")
    print("%-14s %+8.4f %8.3g   %10.5f %+10.5f %10s" % (c, rho, pv, roi_w, roi_w - base, mono))

print("\n=== ngu phan roi theo tung bien (de nhin bang mat) ===")
for c in ["p6", "pred15m", "risk4h", "dow15m", "funding"]:
    s = df[[c, "roi"]].dropna()
    qs = pd.qcut(s[c], 5, labels=False, duplicates="drop")
    m = s.groupby(qs).roi.mean().round(4).tolist()
    print("%-10s %s" % (c, m))
