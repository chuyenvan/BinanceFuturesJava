#!/usr/bin/env python3
"""ADDENDUM1 dieu tra buoc 2: thu dung 1 nen (s, X) khong kha dung (live thieu/khong kha dung nen X) tren toan
doan va so voi rateDown15MAvg live MOI phut (bit-exact float32). Nen X 'giai thich' neu: sua (fixed) moi phut
lech muc tieu va KHONG lam hong (broken) phut nao dang khop. Dung lai ham cua inv_rdown15.py (runpy),
warm-up dai (WARM_MIN) vi cua so 15 nen dem theo SO NEN KHA DUNG (symbol it giao dich can lich su dai)."""
import os, runpy
os.environ.setdefault("RANGE", "10-21 16:50,10-21 18:00")
os.environ.setdefault("WARM_MIN", "480")
os.environ["TARGETS"] = "10-21 17:37"
g = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "inv_rdown15.py"))
simulate, JG, F32, ms7, f7, data = g["simulate"], g["JG"], g["F32"], g["ms7"], g["f7"], g["data"]
A, B = ms7("10-21 16:55"), ms7("10-21 18:00")
live = {M: F32(JG.at[M, "rateDown15MAvg"]) for M in JG.index if A <= M <= B}
bt = {M: F32(JG.at[M, "r_down15"]) for M in JG.index if A <= M <= B}
base = simulate()
print("doan", f7(A), "->", f7(B), "| tai lap==BT:", sum(base[M][1] == bt[M] for M in live), "/", len(live),
      "| live!=BT:", [f7(M) for M in live if live[M] != bt[M]],
      "| tai lap!=BT:", [f7(M) for M in live if base[M][1] != bt[M]])
bad0 = {M for M in live if base[M][1] != live[M]}
for s, xs in (("RAMUSDT", ("10-21 16:50", "10-21 17:18")), ("RDWUSDT", ("10-21 16:55", "10-21 17:40"))):
    d = data[s]
    for X in range(ms7(xs[0]), ms7(xs[1]) + 60000, 60000):
        if X not in d.index:
            continue
        r = d.loc[X]
        if not ((r.l != r.h) or (r.qv != 0)):
            continue    # nen da khong kha dung tren Vision
        sim = simulate(drop_candle=(s, X))
        bad1 = {M for M in live if sim[M][1] != live[M]}
        print(s, "bo nen", f7(X), "| fixed:", [f7(M) for M in sorted(bad0 - bad1)],
              "| broken:", [f7(M) for M in sorted(bad1 - bad0)], "| con lech:", [f7(M) for M in sorted(bad1)], flush=True)
