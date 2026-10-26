#!/usr/bin/env python3
"""NUP3 P1 — ADDENDUM phuong an (c) (MASTER 2026-10-27): V2 chet o G1 => mo 2021H2 cho V0/V1 (KHONG V2).
Equity toan danh muc = eq_B0 + eq_sleeve_FULL - von (sleeve gom ca 2021H2, dung equity sim dung de size).
Luat/nguong khong doi. Them mo ta: maxDD toan ky 2021-07 -> 2025-12; uoc luong tuyen tinh he so size sleeve s*
(eq(s) = eq_B0 + s*(eq_sleeve - von)) de maxDD median 2022-25 = -30 %.
Stage: mtm | score"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup3")
import score_p1 as P  # noqa: E402

M, Q, R = P.M, P.Q, P.R
WK = "/home/ubuntu/claude_master/nup3_p1c_wk"
ARMS = ["v0", "v1"]        # V2 KHONG mo 2021H2
OUTD = P.OUTD


def load_sleeve_full(t):
    hdr, _, slv = P.split_run(t)
    return P.parse(hdr + b"".join(slv), "S")[0]


def stage_mtm():
    FR = {}
    for a in ARMS:
        for s in P.SEEDS:
            d = load_sleeve_full(P.tag(a, s))
            FR[P.tag(a, s) + "#F"] = d[["sym", "quantity", "entry", "margin", "pnl", "ts", "te", "notional"]].copy()
    o_ll = R.load_legs
    R.load_legs = lambda t: FR[t].copy() if t in FR else o_ll(t)
    b0 = ["tsx-x14-" + s for s in P.SEEDS]
    out, miss = M.build(b0 + sorted(FR), None)
    print("missing", miss)
    assert all(v == 0 for v in miss.values()), miss
    np.savez(WK + "/eq.npz", **{k.replace("#", "__"): v for k, v in out.items()})
    json.dump(dict(missing=miss), open(WK + "/mtm.json", "w"), indent=1)


def dd_of(eq, a, b):
    return Q.ddx(eq[a:b])


def stage_score():
    z = np.load(WK + "/eq.npz")
    old = pd.read_csv(OUTD + "/p1_runs.csv").set_index("tag")
    chk = json.load(open(OUTD + "/p1_check.json"))["runs"]
    rows, curves = [], {}
    for a in ARMS:
        for s in P.SEEDS:
            t = P.tag(a, s)
            dB = P.load_b0(s)
            dS = load_sleeve_full(t)
            eqB = P.dev_full(z["tsx-x14-" + s])
            eqS = P.dev_full(z[t + "__F"])
            balB, balS = P.realized_bal(dB, P.NDEV), P.realized_bal(dS, P.NDEV)
            dP = pd.concat([dB, dS], ignore_index=True)
            eqP, balP = eqB + eqS - P.CAP0, balB + balS - P.CAP0
            cp = P.core(dP, eqP)
            cb = P.core(dB, eqB)
            xp = P.expo(dP, cp["c"], eqP, balP)
            X = float(dS.loc[dS["ei"] < P.I0, "pnl"].sum())
            Xst = float((dS.loc[dS["ei"] < P.I0, "pnl"] - 0.002 * dS.loc[dS["ei"] < P.I0, "notional"]).sum())
            B21 = float(dB.loc[dB["ei"] < P.I0, "pnl"].sum())
            sl_open = dS[(dS["si"] >= P.I0) & (dS["si"] < P.I1)]
            n_rej = int((xp["ug"][sl_open["si"].to_numpy()] > 1.0).sum())
            full = slice(0, P.I1)
            eqPf = P.month_fix(dB, eqB)[0] + P.month_fix(dS, eqS)[0] - P.CAP0
            # kiem cheo voi do luong rieng cua sim (toan ky): U mark/margin max, so ve the max
            sc = chk[t]["sim_counts"]
            o = old.loc[t]
            row = dict(tag=t, arm=a, seed=s, X_sleeve_2021H2=X, X_stress_2021H2=Xst, B0_pnl_2021H2=B21,
                       n_sleeve_legs_2021H2=int((dS["ei"] < P.I0).sum()),
                       bal0_2022=cp["bal0"], bal0_2022_old=float(o.B0_n_cl * 0 + cb["bal0"]),
                       P_n_cl=cp["n_cl"], r_ncl=cp["n_cl"] / cb["n_cl"], P_pnl=cp["pnl"], r_pnl=cp["pnl"] / cb["pnl"],
                       r_stress=cp["stress"] / cb["stress"], G12_same=bool(cp["n_cl"] == o.P_n_cl and abs(cp["pnl"] - o.P_pnl) < 1e-6
                                                                          and all(cp["yr"][y]["n_cl"] == int(o["P_ncl_%d" % y]) for y in P.YEARS)),
                       P_dd=cp["dd"], P_dd_old=float(o.P_dd), P_dd_fix=Q.ddx(eqPf[P.I0 - 1:P.I1]),
                       P_cagr=cp["cagr"], P_cagr_old=float(o.P_cagr), P_calmar=cp["calmar"], P_calmar_old=float(o.P_calmar),
                       B0_dd=cb["dd"], B0_cagr=cb["cagr"], B0_calmar=cb["calmar"],
                       P_u_mark_max=xp["u_mark_max"], P_u_mark_max_old=float(o.P_u_mark_max), P_u_marg_max=xp["u_marg_max"],
                       P_u_marg_max_old=float(o.P_u_marg_max), P_u_marg_gt1_min=xp["u_marg_gt1_min"],
                       S_legs_marg_gt1=n_rej, S_legs_marg_gt1_old=int(o.S_legs_open_marg_gt1),
                       S_pct_legs_marg_gt1=100 * n_rej / len(sl_open), P_npos_max=xp["npos_max"],
                       # toan ky 2021-07 -> 2025-12 (mo ta)
                       P_dd_full=dd_of(eqP, 0, P.I1), P_dd_full_fix=dd_of(eqPf, 0, P.I1), B0_dd_full=dd_of(eqB, 0, P.I1),
                       P_u_mark_max_full=float(xp["um"][full].max()), P_u_marg_max_full=float(xp["ug"][full].max()),
                       P_npos_max_full=int(xp["npos"][full].max()),
                       sim_u_mark_max=sc["u_total_max"], sim_u_marg_max=sc["u_total_margin_max"], sim_npos_max=sc["max_pos_total"],
                       S_pnl_dev=float(cp["pnl"] - cb["pnl"]))
            pk = np.maximum.accumulate(eqP[0:P.I1])
            it = int((eqP[0:P.I1] / pk - 1).argmin())
            row["P_dd_full_trough"] = str(P.L0 + it * P.MIN)
            rows.append(row)
            curves[t] = (eqB, eqS, cb["pnl"], float(cp["pnl"] - cb["pnl"]), cb["dd"])
            print(t, "done")
    D = pd.DataFrame(rows)
    D.to_csv(OUTD + "/p1c_runs.csv", index=False)
    # G3 lai (luat khong doi)
    arms = []
    for a in ARMS:
        g = D[D.arm == a]
        o = dict(arm=a, X_med=float(g.X_sleeve_2021H2.median()), B0_2021H2_med=float(g.B0_pnl_2021H2.median()),
                 P_dd_med=float(g.P_dd.median()), P_dd_worst=float(g.P_dd.min()), P_dd_fix_med=float(g.P_dd_fix.median()),
                 P_dd_med_old=float(g.P_dd_old.median()), P_dd_worst_old=float(g.P_dd_old.min()),
                 P_cagr=float(g.P_cagr.median()), P_cagr_old=float(g.P_cagr_old.median()), P_calmar=float(g.P_calmar.median()),
                 P_calmar_old=float(g.P_calmar_old.median()), B0_calmar=float(g.B0_calmar.median()),
                 P_u_mark_max_med=float(g.P_u_mark_max.median()), P_u_mark_max_worst=float(g.P_u_mark_max.max()),
                 P_u_marg_max_med=float(g.P_u_marg_max.median()), P_u_marg_max_worst=float(g.P_u_marg_max.max()),
                 S_legs_marg_gt1_med=float(g.S_legs_marg_gt1.median()), S_legs_marg_gt1_max=int(g.S_legs_marg_gt1.max()),
                 r_ncl=float(g.r_ncl.median()), r_pnl=float(g.r_pnl.median()), G12_same=bool(g.G12_same.all()),
                 P_dd_full_med=float(g.P_dd_full.median()), P_dd_full_worst=float(g.P_dd_full.min()),
                 B0_dd_full_med=float(g.B0_dd_full.median()), B0_dd_med=float(g.B0_dd.median()))
        o["G3"] = bool(o["P_dd_med"] >= -32 and o["P_dd_worst"] >= -36 and o["P_u_mark_max_worst"] <= 1.0)
        # s*: maxDD median 2022-25 = -30 % (tren chinh duong equity, scale PnL sleeve ca ky theo s)
        tags = list(g.tag)

        def med_dd(sv):
            return float(np.median([Q.ddx((curves[t][0] + sv * (curves[t][1] - P.CAP0))[P.I0 - 1:P.I1]) for t in tags]))
        lo, hi = 0.0, 1.0
        assert med_dd(0.0) > -30 > med_dd(1.0)
        for _ in range(60):
            mid = (lo + hi) / 2
            if med_dd(mid) > -30:
                lo = mid
            else:
                hi = mid
        ss = (lo + hi) / 2
        o["s_star"] = ss
        o["dd_med_at_s"] = med_dd(ss)
        o["dd_worst_at_s"] = float(min(Q.ddx((curves[t][0] + ss * (curves[t][1] - P.CAP0))[P.I0 - 1:P.I1]) for t in tags))
        o["dd_full_med_at_s"] = float(np.median([Q.ddx((curves[t][0] + ss * (curves[t][1] - P.CAP0))[0:P.I1]) for t in tags]))
        o["r_pnl_at_s"] = float(np.median([(curves[t][2] + ss * curves[t][3]) / curves[t][2] for t in tags]))
        o["s_lin_formula"] = float((-30 - o["B0_dd_med"]) / (o["P_dd_med"] - o["B0_dd_med"]))
        o["r_ncl_at_s_count"] = o["r_ncl"]
        arms.append(o)
    A = pd.DataFrame(arms)
    A.to_csv(OUTD + "/p1c_arms.csv", index=False)
    pd.set_option("display.width", 250)
    print(D.drop(columns=["tag"]).T.to_string())
    print(A.T.to_string())


if __name__ == "__main__":
    os.makedirs(WK, exist_ok=True)
    {"mtm": stage_mtm, "score": stage_score}[sys.argv[1]]()
