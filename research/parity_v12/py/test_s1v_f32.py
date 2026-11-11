#!/usr/bin/env python3
"""[ADD20] test S1V close float32: tinh lai feature tu closes_cache (gia Vision float64 cu) qua sim_close, so voi live.
argv: day h7_from h7_to [expect_zero]  (gio +07, vd 2026-11-09 19:00 19:59 1). In so dong lech f0..f6 truoc/sau."""
import os
import pickle
import sys
day, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
expect0 = len(sys.argv) > 4 and sys.argv[4] == "1"
os.environ["PV_DAY"] = day
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import day_s1v as M  # noqa: E402
W = M.C["WORK"]
C1 = pickle.load(open(W + "/closes_cache.pkl", "rb"))
D = pd.read_csv(W + "/s1v_rows.csv.gz")
eq = lambda x, y: (np.abs(x - y) <= 1e-6 * (1 + np.abs(y))) | (np.isnan(x) & np.isnan(y))
res = {}
for tag, cast in (("f64_cu", lambda v: np.asarray(v, np.float64)), ("f32_ADD20", M.sim_close)):
    n = {i: 0 for i in range(7)}
    nm = 0
    for h in sorted(D.ts.unique()):
        t7 = pd.to_datetime(h + 7 * 3600000, unit="ms").strftime("%H:%M")
        if not (a <= t7 <= b):
            continue
        nm += 1
        g = D[D.ts == h].set_index("symbol")
        F = {}
        for s in g.index:
            if s in C1:
                th, cv = C1[s]
                try:
                    f = M.feats_time(th, cast(cv), h)
                except M.KDD:
                    f = None
                if f is not None:
                    F[s] = f
        names = list(F)
        X = np.full((len(names), 7), np.nan)
        for j, s in enumerate(names):
            X[j, 0], X[j, 1], X[j, 3], X[j, 4], X[j, 6] = F[s]
        X[:, 2] = M.rank_pct(X[:, 1]); X[:, 5] = M.rank_pct(X[:, 4])
        for i in range(7):
            n[i] += int((~eq(X[:, i], g.loc[names, "l%d" % i].values)).sum())
    res[tag] = n
print(day, a, b, "phut", nm, res)
ok = (not expect0) or all(v == 0 for v in res["f32_ADD20"].values())
ok = ok and sum(res["f32_ADD20"].values()) <= sum(res["f64_cu"].values())
print("TEST_S1V_F32", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
