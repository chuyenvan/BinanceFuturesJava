#!/usr/bin/env python3
"""EDGE_ATTR score (PREREG_EDGE_ATTR 4852f57e) - CHI DO. Doc legs.parquet (edge_attr_build.py).
V1-V4 truoc; Q1 attribution (L x b, nam x L, beta, R1/R2/R3); Q2 impact sqrt + luoi phang.
Usage: python3 edge_attr_score.py out.json
"""
import json
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("eas")
OUT = "/home/ubuntu/claude_master/edge_attr"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
T975_7 = 2.3646
CAP = 35000.0
LB = [(0, 5e6, "<5M"), (5e6, 2e7, "5-20M"), (2e7, 1e8, "20-100M"), (1e8, np.inf, ">=100M")]
BB = [(1, 5, "1-5"), (6, 12, "6-12"), (13, 10**6, "13-24")]
D0, D1 = pd.Timestamp("2021-07-01"), pd.Timestamp("2026-01-01")
H0, H1 = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-01")


def lbin(x):
    out = np.empty(len(x), object)
    for a, b, nm in LB:
        out[(x >= a) & (x < b)] = nm
    return out


def bbin(x):
    out = np.empty(len(x), object)
    for a, b, nm in BB:
        out[(x >= a) & (x <= b)] = nm
    return out


def ms(v):
    v = np.asarray(v, float)
    return {"mean": float(v.mean()), "sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
            "min": float(v.min()), "max": float(v.max()), "per_seed": [float(x) for x in v]}


def ci(v):
    v = np.asarray(v, float)
    h = T975_7 * v.std(ddof=1) / np.sqrt(len(v))
    return [float(v.mean() - h), float(v.mean() + h)]


def cell_stats(g, tot_pnl):
    return {"n": len(g), "pnl": float(g.pnl.sum()), "share": float(g.pnl.sum() / tot_pnl) if tot_pnl else np.nan,
            "pnl_leg": float(g.pnl.mean()) if len(g) else np.nan,
            "roi_med": float(g.roi.median()) if len(g) else np.nan,
            "win": float((g.pnl > 0).mean()) if len(g) else np.nan}


def agg_cells(per_seed):
    keys = sorted({k for d in per_seed.values() for k in d})
    out = {}
    for k in keys:
        out[k] = {}
        for f in ("n", "pnl", "share", "pnl_leg", "roi_med", "win"):
            vals = [per_seed[s].get(k, {}).get(f, 0.0 if f in ("n", "pnl", "share") else np.nan) for s in per_seed]
            vals = np.array(vals, float)
            out[k][f] = [float(np.nanmean(vals)), float(np.nanstd(vals, ddof=1))]
    return out


def maxdd_realized(g, pnl_col):
    x = g.sort_values("t1")[pnl_col].cumsum().to_numpy() + CAP
    peak = np.maximum.accumulate(np.r_[CAP, x])[1:]
    return float((x / peak - 1).min() * 100)


def analyse(d, label):
    R = {"label": label}
    per_lb, per_yr, s0, tot, pl_all, pl_s0, A_alt, A_btc, beta = {}, {}, [], [], [], [], [], [], []
    lowL, lowL_leg = [], []
    for s in SEEDS:
        g = d[d.seed == s]
        if g.empty:
            continue
        T = g.pnl.sum()
        tot.append(T)
        pl_all.append(g.pnl.mean())
        per_lb[s] = {"%s|%s" % (a, b): cell_stats(x, T) for (a, b), x in g.groupby(["Lb", "bb"])}
        per_lb[s].update({"%s|ALL" % a: cell_stats(x, T) for a, x in g.groupby("Lb")})
        per_lb[s].update({"ALL|%s" % b: cell_stats(x, T) for b, x in g.groupby("bb")})
        per_yr[s] = {"%d|%s" % (y, a): cell_stats(x, T) for (y, a), x in g.groupby(["yr", "Lb"])}
        per_yr[s].update({"%d|ALL" % y: cell_stats(x, T) for y, x in g.groupby("yr")})
        q = g[(g.b <= 12) & (g.L24 >= 2e7)]
        s0.append(q.pnl.sum())
        pl_s0.append(q.pnl.mean())
        lo = g[g.L24 < 2e7]
        lowL.append(lo.pnl.sum() / T)
        lowL_leg.append(lo.pnl.mean())
        for col, acc in (("m_alt", A_alt), ("m_btc", A_btc)):
            X = np.c_[np.ones(len(g)), g[col].to_numpy()]
            coef = np.linalg.lstsq(X, g.roi.to_numpy(), rcond=None)[0]
            num = (g.margin * (g.roi - coef[1] * g[col])).sum()
            acc.append(float(num / (g.margin * g.roi).sum()))
            if col == "m_alt":
                beta.append([float(coef[0]), float(coef[1])])
    R["tot_pnl"] = ms(tot)
    R["pnl_leg_all"] = ms(pl_all)
    R["cells_L_b"] = agg_cells(per_lb)
    R["cells_yr_L"] = agg_cells(per_yr)
    R["S0_pnl"] = ms(s0)
    R["S0_ci95"] = ci(s0) if len(s0) > 2 else None
    R["S0_pnl_leg"] = ms(pl_s0)
    R["S0_leg_ratio"] = float(np.mean(pl_s0) / np.mean(pl_all))
    R["R1_edge_rong"] = bool(R["S0_ci95"] and R["S0_ci95"][0] > 0 and R["S0_leg_ratio"] >= 0.5)
    R["beta_alt_alpha_beta"] = beta
    R["A_alt"] = ms(A_alt)
    R["A_btc"] = ms(A_btc)
    R["R2_khong_phai_beta"] = bool(sum(a >= 0.5 for a in A_alt) >= 6)
    R["R3_lowL_share"] = ms(lowL)
    R["R3_lowL_pnl_leg"] = ms(lowL_leg)
    # Q2
    q2 = {}
    for Y in (0.5, 1.0):
        for sc, nm in ((10 / 35, "10k"), (1.0, "35k"), (10.0, "350k")):
            c = Y * d.sig_d * np.sqrt(d.margin * sc / d.L24)
            d["_pp"] = d.pnl - 2 * c * d.margin
            tt, dp, low, dd, cmed = [], [], [], [], []
            for s in SEEDS:
                g = d[d.seed == s]
                if g.empty:
                    continue
                tt.append(g._pp.sum())
                dp.append(100 * (g._pp.sum() / g.pnl.sum() - 1))
                low.append(g[g.L24 < 2e7]._pp.sum())
                dd.append(maxdd_realized(g, "_pp"))
                cmed.append(float(np.median(c[g.index])) * 1e4)
            lbl = {a: [float(d[(d.seed == s) & (d.Lb == a)]._pp.mean()) for s in SEEDS if (d.seed == s).any()] for _, _, a in LB}
            q2["Y%.1f_%s" % (Y, nm)] = {"pnl": ms(tt), "dpct": ms(dp), "lowL_pnl": ms(low), "maxdd_real": ms(dd),
                                        "cost_bps_leg_median": ms(cmed),
                                        "pnl_leg_by_L": {k: [float(np.mean(v)), float(np.std(v, ddof=1))] for k, v in lbl.items()}}
    base_dd = [maxdd_realized(d[d.seed == s], "pnl") for s in SEEDS if (d.seed == s).any()]
    q2["base_maxdd_real"] = ms(base_dd)
    flat = {}
    for bps in (25, 50, 100, 200):
        v = [((d.seed == s) & (d.L24 < 2e7)) for s in SEEDS]
        tt = [float(d[d.seed == s].pnl.sum() - bps / 1e4 * d[m].margin.sum()) for s, m in zip(SEEDS, v) if (d.seed == s).any()]
        lw = [float(d[m].pnl.sum() - bps / 1e4 * d[m].margin.sum()) for s, m in zip(SEEDS, v) if (d.seed == s).any()]
        flat[str(bps)] = {"pnl": ms(tt), "lowL_pnl": ms(lw)}
    be_low = [1e4 * d[(d.seed == s) & (d.L24 < 2e7)].pnl.sum() / d[(d.seed == s) & (d.L24 < 2e7)].margin.sum() for s in SEEDS if (d.seed == s).any()]
    be_half = [1e4 * 0.5 * d[d.seed == s].pnl.sum() / d[(d.seed == s) & (d.L24 < 2e7)].margin.sum() for s in SEEDS if (d.seed == s).any()]
    flat["breakeven_bps_lowL"] = ms(be_low)
    flat["bps_half_total"] = ms(be_half)
    q2["flat_lowL"] = flat
    k = q2["Y1.0_35k"]
    q2["rule_nhay_chi_phi"] = bool(k["dpct"]["mean"] < -30 or k["lowL_pnl"]["mean"] < 0)
    R["Q2"] = q2
    d.drop(columns=["_pp"], inplace=True, errors="ignore")
    return R


def main():
    d = pd.read_parquet(OUT + "/legs.parquet")
    d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
    d["t1"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d["roi"] = d.pnl / d.margin
    d["yr"] = d.t0.dt.year
    V = {}
    # V2: SigmaPnL theo end trong DFULL (nhu ecm_score)
    v2 = {}
    for s in SEEDS:
        g = d[(d.win == "D") & (d.seed == s)]
        v2[str(s)] = {"sum_pnl_end": float(g[(g.t1 >= D0) & (g.t1 < D1)].pnl.sum()), "n_start": int(((g.t0 >= D0) & (g.t0 < D1)).sum())}
    V["V2_recomputed"] = v2
    out = {"prereg": "4852f57e", "validation": V}
    for win, a, b in (("D", D0, D1), ("H", H0, H1)):
        x = d[(d.win == win) & (d.t0 >= a) & (d.t0 < b)].copy()
        if x.empty:
            continue
        v1 = np.abs(x.entry / x.closeM - 1)
        good = (x.nbar >= 1368) & np.isfinite(x.L24) & (x.L24 > 0) & np.isfinite(x.sig_d) & x.hasM_alt & x.hasE_alt & x.hasM_btc & x.hasE_btc & x.t1.notna()
        V["%s_V1_frac_le_0035" % win] = float((v1 <= 0.0035).mean())
        V["%s_V1_nan_closeM" % win] = int(x.closeM.isna().sum())
        V["%s_V3_frac_full" % win] = float(((x.nbar >= 1368) & (x.L24 > 0)).mean())
        V["%s_V3_frac_index_ME" % win] = float((x.hasM_alt & x.hasE_alt).mean())
        V["%s_excluded" % win] = {"n": int((~good).sum()), "pnl": float(x[~good].pnl.sum()), "n_total": int(len(x))}
        x = x[good].copy()
        if x.empty:
            log.warning('%s: 0 chan du du lieu sau loc (kline thieu) -> bo qua', win)
            continue
        x["Lb"] = lbin(x.L24.to_numpy())
        x["bb"] = bbin(x.b.to_numpy())
        tot = x.groupby("seed").pnl.sum()
        sumc = sum(x[x.Lb == a_].groupby("seed").pnl.sum().reindex(tot.index, fill_value=0) for _, _, a_ in LB)
        V["%s_V4_maxrel" % win] = float((np.abs(sumc - tot) / np.abs(tot)).max())
        out[win] = analyse(x, win)
    json.dump(out, open(sys.argv[1], "w"), indent=1, default=float)
    log.info(json.dumps(V, indent=1, default=float))
    for win in ("D", "H"):
        if win not in out:
            continue
        R = out[win]
        log.info("== %s tot_pnl %.0f+-%.0f | S0 %.0f CI %s leg_ratio %.2f R1=%s | A_alt %.2f+-%.2f R2=%s | lowL share %.2f leg %.1f",
                 win, R["tot_pnl"]["mean"], R["tot_pnl"]["sd"], R["S0_pnl"]["mean"], R["S0_ci95"], R["S0_leg_ratio"], R["R1_edge_rong"],
                 R["A_alt"]["mean"], R["A_alt"]["sd"], R["R2_khong_phai_beta"], R["R3_lowL_share"]["mean"], R["R3_lowL_pnl_leg"]["mean"])
        for k, c in sorted(R["cells_L_b"].items()):
            log.info("  %-14s n %6.1f pnl %9.0f+-%6.0f share %6.3f leg %7.2f roi_med %7.4f win %.3f", k, c["n"][0], c["pnl"][0], c["pnl"][1],
                     c["share"][0], c["pnl_leg"][0], c["roi_med"][0], c["win"][0])
        for k, c in sorted(R["cells_yr_L"].items()):
            log.info("  yr %-12s n %6.1f pnl %9.0f+-%6.0f share %6.3f leg %7.2f", k, c["n"][0], c["pnl"][0], c["pnl"][1], c["share"][0], c["pnl_leg"][0])
        for k, q in R["Q2"].items():
            if k.startswith("Y"):
                log.info("  Q2 %-9s pnl %9.0f dpct %6.1f%% lowL %9.0f maxddR %6.2f costbps_med %6.1f byL %s", k, q["pnl"]["mean"], q["dpct"]["mean"],
                         q["lowL_pnl"]["mean"], q["maxdd_real"]["mean"], q["cost_bps_leg_median"]["mean"],
                         {a: round(v[0], 1) for a, v in q["pnl_leg_by_L"].items()})
        log.info("  Q2 base maxddR %.2f | flat %s | rule_nhay=%s", R["Q2"]["base_maxdd_real"]["mean"],
                 {k: (round(v["mean"], 1) if "mean" in v else (round(v["pnl"]["mean"]), round(v["lowL_pnl"]["mean"]))) for k, v in R["Q2"]["flat_lowL"].items()},
                 R["Q2"]["rule_nhay_chi_phi"])


if __name__ == "__main__":
    main()
