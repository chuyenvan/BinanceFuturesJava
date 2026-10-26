#!/usr/bin/env python3
"""NUP3-S0 validate V1 (them+chung = cum A2; chung+mat = cum B0), V2 (NUP audit a1 998/6434/1936), V5 (TRONG+NGOAI = EXTRA)."""
import pandas as pd
D = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/nup3_s0/"
M = pd.read_csv(D + "match_counts.csv", dtype={"seed": str})
G = pd.read_csv(D + "groups_by_seed.csv", dtype={"seed": str})
rows = []
for r in M.itertuples():
    rows.append(dict(check="V1_extra+common=a2_cl", phase=r.phase, seed=r.seed, val=r.extra + r.common, ref=r.a2_cl, ok=r.extra + r.common == r.a2_cl))
    rows.append(dict(check="V1_common+lost=b0_cl", phase=r.phase, seed=r.seed, val=r.common + r.lost, ref=r.b0_cl, ok=r.common + r.lost == r.b0_cl))
a = M[(M.phase == "DEV") & (M.seed == "a1")].iloc[0]
rows.append(dict(check="V2_NUP_leg_match_a1", phase="DEV", seed="a1", val="%d/%d/%d" % (a.leg_common, a.leg_new, a.leg_lost), ref="998/6434/1936",
                 ok=(a.leg_common, a.leg_new, a.leg_lost) == (998, 6434, 1936)))
mx_n, mx_p = 0, 0.0
for (ph, sd, per), g in G.groupby(["phase", "seed", "period"]):
    ex = g[g.W == "EXTRA"].iloc[0]
    tot = g[g.W == "EXTRA"].n.iloc[0]
    if per == "DEV_T":
        mm = M[(M.phase == ph) & (M.seed == sd)].iloc[0]
        rows.append(dict(check="V1_extra_period=match", phase=ph, seed=sd, val=int(tot), ref=int(mm.extra), ok=int(tot) == int(mm.extra)))
    if ph == "HO":
        mm = M[(M.phase == ph) & (M.seed == sd)].iloc[0]
        rows.append(dict(check="V1_extra_period=match", phase=ph, seed=sd, val=int(tot), ref=int(mm.extra), ok=int(tot) == int(mm.extra)))
    for W in ["W_burst", "W_mkt", "W_book", "W_quiet"]:
        t, o = g[(g.W == W) & (g.group == "TRONG")].iloc[0], g[(g.W == W) & (g.group == "NGOAI")].iloc[0]
        dn = t.n + o.n - ex.n
        dp = max(abs(t.pnl + o.pnl - ex.pnl), abs(t.pnl_s + o.pnl_s - ex.pnl_s))
        mx_n, mx_p = max(mx_n, abs(dn)), max(mx_p, dp)
rows.append(dict(check="V5_TRONG+NGOAI=EXTRA (n, pnl, pnl_s) max diff", phase="ALL", seed="ALL", val="%d / %.2e" % (mx_n, mx_p), ref="0 / <1e-6", ok=mx_n == 0 and mx_p < 1e-6))
# tong nam = DEV_T
mxy = 0.0
for (sd, W, grp), g in G[G.phase == "DEV"].groupby(["seed", "W", "group"]):
    y = g[g.period != "DEV_T"].pnl_s.sum()
    mxy = max(mxy, abs(y - g[g.period == "DEV_T"].pnl_s.iloc[0]))
rows.append(dict(check="V5b_sum_years=DEV_T pnl_s max diff", phase="DEV", seed="ALL", val="%.2e" % mxy, ref="<1e-6", ok=mxy < 1e-6))
V = pd.DataFrame(rows)
V.to_csv(D + "validate.csv", index=False)
print(V[~V.ok].to_string() if (~V.ok).any() else "all rows ok")
print(V[V.check.str.startswith(("V2", "V5"))].to_string(index=False))
print("VALIDATE_OK", bool(V.ok.all()), len(V))
