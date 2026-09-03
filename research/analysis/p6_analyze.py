"""Pre-check CONF_SIZE: p6 co thuc su lien he voi ket qua lenh khong?
Neu KHONG co lien he don dieu -> sizing theo p6 chi la nhieu, KHONG chay.
Doc printDone.csv cua C2b (DEV 2022-01..2024-06)."""
import numpy as np, pandas as pd

D = "/home/ubuntu/java/devrun/C2b/storage/printDone.csv"
df = pd.read_csv(D)
print("rows:", len(df), "| cot:", list(df.columns)[:6], "...")

df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
df["symbolPred"] = pd.to_numeric(df.symbolPred, errors="coerce")
df = df.dropna(subset=["symbolPred"])
df["p6"] = 1.0 - df.symbolPred
# ROI cua lenh = pnl / margin (chuan hoa theo von thuc dung, khong bi size lam nhieu)
df["margin"] = pd.to_numeric(df.margin, errors="coerce")
df["pnl"] = pd.to_numeric(df.pnl, errors="coerce")
df = df[df.margin > 0]
df["roi"] = df.pnl / df.margin
print("n lenh selector:", len(df))

q = [0, 1, 5, 10, 20, 30, 50, 70, 80, 90, 95, 99, 100]
print("\n=== phan phoi p6 (=1-symbolPred) ===")
for p in q:
    print("  p%-3d = %.4f" % (p, np.percentile(df.p6, p)))

print("\n=== ROI theo decile p6 (thap -> cao) ===")
df["dec"] = pd.qcut(df.p6, 10, labels=False, duplicates="drop")
g = df.groupby("dec").agg(n=("roi", "size"), roi_mean=("roi", "mean"),
                          roi_med=("roi", "median"), winrate=("roi", lambda s: (s > 0).mean()),
                          p6_lo=("p6", "min"), p6_hi=("p6", "max"))
print(g.round(4).to_string())

from scipy.stats import spearmanr
rho, pv = spearmanr(df.p6, df.roi)
print("\nspearman(p6, roi) = %.4f  (p=%.3g)  n=%d" % (rho, pv, len(df)))

# so sanh 2 nua
lo_h = df[df.p6 <= df.p6.median()].roi
hi_h = df[df.p6 > df.p6.median()].roi
print("nua p6 THAP : n=%d roi_mean=%+.4f winrate=%.3f" % (len(lo_h), lo_h.mean(), (lo_h > 0).mean()))
print("nua p6 CAO  : n=%d roi_mean=%+.4f winrate=%.3f" % (len(hi_h), hi_h.mean(), (hi_h > 0).mean()))

print("\n=== confFactor trung binh voi cac cau hinh ung vien ===")
print("(muon TRUNG TINH ve don bay thi mean(confFactor) ~ 1.0; khac 1 = tron lan hieu ung tilt voi hieu ung leverage)")
p20, p80 = np.percentile(df.p6, 20), np.percentile(df.p6, 80)
p10, p90 = np.percentile(df.p6, 10), np.percentile(df.p6, 90)
cands = [
    ("MAC DINH  LO.68 HI.95 F.3-3.0", 0.68, 0.95, 0.3, 3.0),
    ("NEUTRAL-A p20/p80  F0.6-1.4",   p20,  p80,  0.6, 1.4),
    ("NEUTRAL-B p20/p80  F0.4-1.6",   p20,  p80,  0.4, 1.6),
    ("NEUTRAL-C p10/p90  F0.5-1.5",   p10,  p90,  0.5, 1.5),
]
for name, LO, HI, FMIN, FMAX in cands:
    f = np.where(df.p6 <= LO, FMIN,
        np.where(df.p6 >= HI, FMAX,
                 FMIN + (FMAX - FMIN) * (df.p6 - LO) / (HI - LO)))
    # ROI co trong so size (uoc luong tho hieu qua, chua tinh tuong tac margin/breaker)
    w = f / f.mean()
    print("%-32s LO=%.4f HI=%.4f  mean_f=%.3f  roi_w=%+.5f (goc %+.5f)"
          % (name, LO, HI, f.mean(), (df.roi * w).mean(), df.roi.mean()))
