"""Hieu ung 'p15 qua nong -> ROI ~ 0' co BEN qua tung nam khong?
Neu chi xuat hien 1 nam => la giai doan, khong phai co che => KHONG chay sim.
Luu y trung thuc: nguong 0.02 do CHINH toi nhin vao DEV ma chon => chay lai tren DEV la vong tron.
Vi vay o day dung nguong theo QUY TAC (decile cua p15) chu khong go tay, va tach theo nam."""
import numpy as np, pandas as pd
H, step = 3600000, 900000
sm = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); m = dict(zip(sm.symbol, sm.symId))
L = pd.read_parquet("/home/ubuntu/ledger/cand_dev3.parquet", columns=["ts", "sym", "p15"])

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
    fr.append(df[["run", "ts", "sym", "roi", "pnl", "margin"]].dropna())
M = pd.concat(fr).merge(L, on=["ts", "sym"], how="inner")
M["nam"] = pd.to_datetime(M.ts, unit="ms").dt.year
print("ghep duoc:", len(M))

print("\n=== 1. Nguong theo QUY TAC: decile 10 cua p15 TRONG TUNG NAM (khong go tay) ===")
for run, g in M.groupby("run"):
    print("--- %s ---" % run)
    for y, gy in g.groupby("nam"):
        thr = gy.p15.quantile(0.9)
        hot, cold = gy[gy.p15 >= thr], gy[gy.p15 < thr]
        print("   %d  thr_d10=%.4f | NONG n=%3d roi=%+.4f pnl=%+8.0f | CON LAI n=%4d roi=%+.4f pnl=%+8.0f"
              % (y, thr, len(hot), hot.roi.mean(), hot.pnl.sum(), len(cold), cold.roi.mean(), cold.pnl.sum()))

print("\n=== 2. Nguong CO DINH 0.02 (cai toi nhin thay) tach theo nam ===")
for run, g in M.groupby("run"):
    print("--- %s ---" % run)
    for y, gy in g.groupby("nam"):
        hot, cold = gy[gy.p15 > 0.02], gy[gy.p15 <= 0.02]
        if len(hot) == 0:
            print("   %d  khong co lenh p15>0.02" % y); continue
        print("   %d  NONG n=%3d roi=%+.4f pnl=%+8.0f | CON LAI n=%4d roi=%+.4f pnl=%+8.0f"
              % (y, len(hot), hot.roi.mean(), hot.pnl.sum(), len(cold), cold.roi.mean(), cold.pnl.sum()))

print("\n=== 3. Neu BO het lenh p15>0.02 thi mat/duoc bao nhieu PnL (tho, chua tinh tai dau tu) ===")
for run, g in M.groupby("run"):
    hot = g[g.p15 > 0.02]
    print("   %-8s bo %d lenh, pnl cua chung = %+.0f USDT (tong ca run %+.0f => %+.1f%%)"
          % (run, len(hot), hot.pnl.sum(), g.pnl.sum(), 100 * hot.pnl.sum() / g.pnl.sum()))

print("\n=== 4. Kiem doc lap: tuong quan p15 vs roi trong tung nam (S1) ===")
from scipy.stats import spearmanr
g = M[M.run == "S1/C2b"]
for y, gy in g.groupby("nam"):
    r, p = spearmanr(gy.p15, gy.roi)
    print("   %d n=%4d spearman=%+.4f p=%.3g" % (y, len(gy), r, p))
r, p = spearmanr(g.p15, g.roi)
print("   TONG n=%4d spearman=%+.4f p=%.3g" % (len(g), r, p))
