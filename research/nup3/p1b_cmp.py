"""NUP3b P1: (1) so kiem tay doc lap indep_p1.py (nup3b-s1x-s7) voi score_p1b; (2) U mark toan ky voi eq da sua bug
month-boundary vs so sim tu do (giai thich lech u_mark <= 0.0014)."""
import json
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup3")
import score_p1 as P
import score_p1b as SB
OUT = P.OUTD
Rn = pd.read_csv(OUT + "/p1b_runs.csv").set_index("tag")
Y = pd.read_csv(OUT + "/p1b_years.csv")
ind = json.load(open(SB.WK + "/indep_s1x_s7.json"))
t = "nup3b-s1x-s7"
y = Y[Y.tag == t].set_index("year")
cmp = dict(S_ncl=[[ind["S"]["n_cl"][str(k)] for k in P.YEARS], [int(y.loc[k, "S_n_cl"]) for k in P.YEARS]],
           B_ncl=[[ind["B"]["n_cl"][str(k)] for k in P.YEARS], [int(y.loc[k, "base_n_cl"]) for k in P.YEARS]],
           P_ncl=[[ind["P"]["n_cl"][str(k)] for k in P.YEARS], [int(y.loc[k, "P_n_cl"]) for k in P.YEARS]],
           S_pnl=[ind["S"]["pnl"], float(Rn.loc[t, "S_pnl"])], B_pnl=[ind["B"]["pnl"], float(Rn.loc[t, "base_pnl"])],
           P_pnl=[ind["P"]["pnl"], float(Rn.loc[t, "P_pnl"])])
cmp["ok"] = bool(cmp["S_ncl"][0] == cmp["S_ncl"][1] and cmp["B_ncl"][0] == cmp["B_ncl"][1] and cmp["P_ncl"][0] == cmp["P_ncl"][1]
                 and all(abs(cmp[k][0] - cmp[k][1]) < 1e-6 for k in ("S_pnl", "B_pnl", "P_pnl")))
print(json.dumps(cmp))
z = np.load(SB.WK + "/eq.npz")
chk = json.load(open(SB.WK + "/check.json"))["runs"]
ux = {}
for a in SB.ARMS:
    for s in SB.SEEDS:
        t = SB.tag(a, s)
        hdr, base, slv = SB.books(t)
        dS = P.parse(hdr + b"".join(slv), "S")[0]
        if a == "s1x":
            dB = P.parse(hdr + b"".join(base), "B")[0]
            eqB = P.dev_full(z[t + "__B"])
        else:
            dB = P.load_b0(s)
            eqB = P.dev_full(z["tsx-x14-" + s])
        eqS = P.dev_full(z[t + "__S"])
        d = pd.concat([dB, dS], ignore_index=True)
        eq = eqB + eqS - P.CAP0
        eqf = P.month_fix(dB, eqB)[0] + P.month_fix(dS, eqS)[0] - P.CAP0
        bal = P.realized_bal(d, P.NDEV)
        on = P.Q.sweep(d["si"].to_numpy(), d["ei"].to_numpy(), d["notional"].to_numpy(float), P.NDEV)
        w = slice(0, P.I1)
        um = ((on + eq - bal) / eq)[w].max()
        umf = ((on + eqf - bal) / eqf)[w].max()
        ux[t] = dict(pipeline=float(um), fixed=float(umf), sim=chk[t]["sim"]["u_total_max"])
        print(t, ux[t])
V = json.load(open(OUT + "/p1b_validate.json"))
V["indep_s1x_s7"] = cmp
V["u_mark_full_fix_vs_sim"] = ux
V["u_mark_fix_maxdiff"] = max(abs(x["fixed"] - x["sim"]) for x in ux.values())
json.dump(V, open(OUT + "/p1b_validate.json", "w"), indent=1, default=str)
print("maxdiff fixed vs sim", V["u_mark_fix_maxdiff"])
