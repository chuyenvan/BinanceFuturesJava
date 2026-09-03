"""Kiem lai do phu: printDone ghi gio GMT+7 (sim ep timezone Asia/Ho_Chi_Minh),
ledger dung epoch UTC. Neu toi ghep thang thi lech 7 gio => do phu bi bao thap gia.
Thu day du cac offset, ke ca +-7h."""
import numpy as np, pandas as pd
sm = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); m = dict(zip(sm.symbol, sm.symId))
step, H = 900000, 3600000
for LEDG, nm in [("/home/ubuntu/ledger/cand_dev.parquet", "ledger v1 (p15>=0.008)"),
                 ("/home/ubuntu/ledger/cand_dev3.parquet", "ledger v3 (moi tick)")]:
    L = pd.read_parquet(LEDG, columns=["ts", "sym"])
    pairs = set(map(tuple, L.values)); ticks = set(L.ts.unique())
    print("\n===== %s : %d dong, %d tick =====" % (nm, len(L), len(ticks)))
    for tag, d in [("S1/C2b", "C2b"), ("G015", "C2_g015")]:
        df = pd.read_csv(f"/home/ubuntu/java/devrun/{d}/storage/printDone.csv")
        df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
        df["symid"] = (df["sym"].astype(str) + "USDT").map(m)
        df = df.dropna(subset=["symid"]); df["symid"] = df.symid.astype(int)
        ms = pd.to_datetime(df.start, format="%Y%m%d %H:%M", errors="coerce").astype("int64") // 10**6
        best = (0, -1)
        for off in (0, -7*H, 7*H, -step, -2*step, -7*H-step, -7*H-2*step, -7*H+step):
            tt = ((ms + off) // step) * step
            hit = np.mean([(a, b) in pairs for a, b in zip(tt, df.symid)])
            if hit > best[1]:
                best = (off, hit)
            print("  %-8s off=%+9d (%+5.2fh)  ghep cap=%.3f" % (tag, off, off/H, hit))
        print("  %-8s => TOT NHAT off=%+d (%.2fh) ghep=%.3f  n=%d\n" % (tag, best[0], best[0]/H, best[1], len(df)))
