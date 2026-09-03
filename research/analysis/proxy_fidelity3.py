"""BAN SUA LOI MUI GIO: printDone ghi gio GMT+7 (sim ep Asia/Ho_Chi_Minh), ledger dung epoch UTC.
=> tru 7h roi lam tron xuong luoi 15m. Do phu ledger v1 tang 29.5% -> 75.9% (v3: 97.5%).
Cau hoi: nhan offline nao du bao TOT NHAT ROI that cua sim? Do la nhan nen dung de train selector."""
import numpy as np, pandas as pd
from scipy.stats import spearmanr

H, step = 3600000, 900000
sm = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); m = dict(zip(sm.symbol, sm.symId))
L3 = pd.read_parquet("/home/ubuntu/ledger/cand_dev3.parquet",
                     columns=["ts", "sym", "g1lite", "maxFav_72h", "maxAdv_72h", "retEnd_72h", "p15"])
R = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                    columns=["ts", "sym", "g1_replay", "nH_above_6", "nH_above_3"])
L3 = L3.merge(R, on=["ts", "sym"], how="left")

fr = []
for tag, d in [("S1/C2b", "C2b"), ("G015", "C2_g015")]:
    df = pd.read_csv(f"/home/ubuntu/java/devrun/{d}/storage/printDone.csv")
    df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
    for c in ("margin", "pnl"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df.margin > 0]
    df["roi"] = df.pnl / df.margin
    df["sym"] = (df["sym"].astype(str) + "USDT").map(m)
    ms = pd.to_datetime(df.start, format="%Y%m%d %H:%M", errors="coerce").astype("int64") // 10**6
    df["ts"] = ((ms - 7 * H) // step) * step
    df["run"] = tag
    fr.append(df[["run", "ts", "sym", "roi"]].dropna())
T = pd.concat(fr)
M = T.merge(L3, on=["ts", "sym"], how="left")
print("do phu tren ledger v3: %.1f%% (%d/%d)" % (100 * M.g1lite.notna().mean(), M.g1lite.notna().sum(), len(M)))
M = M.dropna(subset=["g1lite", "g1_replay"])

COLS = ["g1_replay", "g1lite", "maxFav_72h", "maxAdv_72h", "retEnd_72h", "nH_above_6", "nH_above_3"]
print("\n=== NHAN OFFLINE vs ROI THUC cua sim (n=%d) ===" % len(M))
print("%-14s %10s %10s %12s" % ("nhan", "spearman", "pearson", "chenh THANG-THUA"))
M["win"] = M.roi > 0
for c in COLS:
    s = M[[c, "roi"]].dropna()
    d = M[M.win][c].mean() - M[~M.win][c].mean()
    print("%-14s %10.4f %10.4f %12.4f" % (c, spearmanr(s[c], s.roi).correlation,
                                          np.corrcoef(s[c], s.roi)[0, 1], d))

print("\n=== theo tung run ===")
for run, g in M.groupby("run"):
    print("--- %s (n=%d, roi_tb=%+.4f) ---" % (run, len(g), g.roi.mean()))
    for c in ["g1lite", "g1_replay", "maxFav_72h", "retEnd_72h"]:
        print("   %-12s spearman=%+.4f" % (c, spearmanr(g[c], g.roi).correlation))

print("\n=== lenh that xay ra o dai p15 nao (kiem lai gia thiet gate) ===")
M["p15b"] = pd.cut(M.p15, [0, .002, .004, .006, .008, .012, .02, 1])
print(M.groupby(["run", "p15b"], observed=True).agg(n=("roi", "size"), roi=("roi", "mean")).round(4).to_string())
