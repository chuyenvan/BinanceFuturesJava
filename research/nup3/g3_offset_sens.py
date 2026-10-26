"""Do nhay G3 theo offset equity X chua biet (PnL sleeve 2021H2 bi loai theo luat MASTER; KHONG tinh X).
X la hang so cong vao eq toan danh muc tu 2022-01-01 (moi leg sleeve 2021H2 dong truoc 2022, leg vat moc = 0).
dd%(X) = (T - P) / (P + X) ; X32 = X can de dd = -32 %, X36 = X can de dd = -36 %."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup3")
import score_p1 as P
z = np.load(P.WK + "/eq.npz")
rows = []
for a in P.ARMS:
    for s in P.SEEDS:
        eq = P.dev_full(z["tsx-x14-" + s]) + P.dev_full(z[P.tag(a, s) + "__S"]) - P.CAP0
        seg = eq[P.I0 - 1:P.I1]
        pk = np.maximum.accumulate(seg)
        r = seg / pk - 1
        it = int(r.argmin())
        Pk, T = float(pk[it]), float(seg[it])
        ddu = Pk - T
        rows.append(dict(arm=a, seed=s, eq_2022_start=float(seg[0]), peak=Pk, trough=T, dd_usd=ddu, dd_pct=100 * (T / Pk - 1),
                         X32=ddu / 0.32 - Pk, X36=ddu / 0.36 - Pk,
                         X32_pct_eq0=100 * (ddu / 0.32 - Pk) / float(seg[0]), X36_pct_eq0=100 * (ddu / 0.36 - Pk) / float(seg[0])))
D = pd.DataFrame(rows)
D.to_csv(P.OUTD + "/p1_g3_offset_sens.csv", index=False)
print(D.round(1).to_string())
print(D.groupby("arm")[["X32", "X36", "X32_pct_eq0", "X36_pct_eq0", "eq_2022_start"]].median().round(1).to_string())
