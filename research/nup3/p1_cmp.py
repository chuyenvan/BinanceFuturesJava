"""NUP3 P1: so kiem tay doc lap (indep_p1.py) voi score_p1 + ngay dinh/day DD (mo ta)."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup3")
import score_p1 as P
OUT = P.OUTD
R = pd.read_csv(OUT + "/p1_runs.csv").set_index("tag")
Y = pd.read_csv(OUT + "/p1_years.csv")
ind = json.load(open(P.WK + "/indep_v1_s21.json"))
t = "nup3-v1-s21"
y = Y[Y.tag == t].set_index("year")
cmp = dict(S_ncl=[[ind["S"]["n_cl"][str(k)] for k in P.YEARS], [int(y.loc[k, "S_n_cl"]) for k in P.YEARS]],
           P_ncl=[[ind["P"]["n_cl"][str(k)] for k in P.YEARS], [int(y.loc[k, "P_n_cl"]) for k in P.YEARS]],
           S_pnl=[ind["S"]["pnl"], float(R.loc[t, "S_pnl"])], P_pnl=[ind["P"]["pnl"], float(R.loc[t, "P_pnl"])])
cmp["ok"] = bool(cmp["S_ncl"][0] == cmp["S_ncl"][1] and cmp["P_ncl"][0] == cmp["P_ncl"][1]
                 and abs(cmp["S_pnl"][0] - cmp["S_pnl"][1]) < 1e-6 and abs(cmp["P_pnl"][0] - cmp["P_pnl"][1]) < 1e-6)
print(json.dumps(cmp))
V = json.load(open(OUT + "/p1_validate.json"))
V["indep_v1_s21"] = cmp
# ngay dinh / day DD toan danh muc (mo ta)
z = np.load(P.WK + "/eq.npz")
dd = {}
for s in P.SEEDS:
    eqB = P.dev_full(z["tsx-x14-" + s])
    for a in [None] + P.ARMS:
        eq = eqB if a is None else eqB + P.dev_full(z[P.tag(a, s) + "__S"]) - P.CAP0
        seg = eq[P.I0 - 1:P.I1]
        pk = np.maximum.accumulate(seg)
        r = seg / pk - 1
        it = int(r.argmin())
        ip = int(seg[:it + 1].argmax())
        f = lambda i: str(P.L0 + (P.I0 - 1 + i) * P.MIN)  # noqa: E731
        dd[("b0" if a is None else a) + "-" + s] = dict(dd=float(100 * r.min()), peak=f(ip), trough=f(it))
V["dd_dates"] = dd
json.dump(V, open(OUT + "/p1_validate.json", "w"), indent=1, default=float)
for k, v in dd.items():
    print(k, round(v["dd"], 3), v["peak"], v["trough"])
print(R[["S_pnl", "S_n_leg", "S_n_cl", "S_pnl_per_cl", "B0_npos_max", "B0_u_mark_max", "P_u_mark_gt1_min", "P_u_marg_gt1_min"]].to_string())
