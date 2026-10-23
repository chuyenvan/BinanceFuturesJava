#!/usr/bin/env python3
"""PAIRS_T1 report: metrics, V3 control gate, tier-1 criteria (pre-reg sec.5), crash-buy correlation, episodes.
Reads ~/claude_master/pairs/out/{pairs_main,m4_main,controls}.pkl, valid.json, v5.json. Writes report.json."""
import json
import logging
import os
import pickle
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pairs_t1_core as K  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("pairs_t1_report")
OUT = os.path.expanduser("~/claude_master/pairs/out")
CB = os.path.expanduser("~/claude_master/tsx/deep_cache/eq_dev.npz")
CB_DAY0 = pd.Timestamp("2021-07-01")
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
C_START = pd.Timestamp("2024-01-01")
EPISODES = {"2021-05 crash": ("2021-05-12", "2021-05-23"), "2021-12-04": ("2021-12-03", "2021-12-05"),
            "LUNA 2022-05": ("2022-05-07", "2022-05-14"), "3AC 2022-06": ("2022-06-10", "2022-06-19"),
            "FTX 2022-11": ("2022-11-06", "2022-11-13"), "2024-04": ("2024-04-12", "2024-04-17"),
            "2024-08-05": ("2024-08-02", "2024-08-06"), "2025-02-03": ("2025-02-02", "2025-02-04"),
            "2025-03": ("2025-03-03", "2025-03-11"), "2025-10-10": ("2025-10-10", "2025-10-11")}


def sharpe(r):
    r = np.asarray(r)
    return float(r.mean() / r.std(ddof=1) * np.sqrt(365)) if len(r) > 2 and r.std() > 0 else 0.0


def maxdd(eq):
    eq = np.asarray(eq)
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def cagr(eq0, eq1, ndays):
    return float((eq1 / eq0) ** (365.0 / ndays) - 1) if eq1 > 0 else -1.0


def series_pairs(wins, m, c, mode="net"):
    E = 1.0
    eqh, eqd, wk = [1.0], [1.0], []
    for w in wins:
        r = w["res"][m]
        path = r["g"] if mode == "gross" else r["g"] + r["f"] - c * r["u"]
        eqh.extend(E * (1 + path[1:]))
        eqd.extend(E * (1 + path[24::24]))
        wk.append(float(path[-1]))
        E *= 1 + path[-1]
    return np.array(eqh), np.array(eqd), np.array(wk)


def series_m4(res):
    eq = res["eq"]
    eqd = eq[::24].copy()
    eqd[-1] = eq[-1]
    eqw = eq[::K.TRAD].copy()
    eqw[-1] = eq[-1]
    return eq, eqd, eqw[1:] / eqw[:-1] - 1


def period_stats(eqd, dates):
    r = eqd[1:] / eqd[:-1] - 1
    s = pd.Series(r, index=dates)
    out = {}
    for nm, msk in (("E", s.index < C_START), ("C", s.index >= C_START), ("ALL", np.ones(len(s), bool))):
        x = s[msk]
        eq = np.cumprod(1 + x.values)
        out[nm] = dict(sharpe=sharpe(x.values), cagr=cagr(1.0, eq[-1], len(x)), ret=float(eq[-1] - 1), ndays=int(len(x)))
    mon = (1 + s[s.index >= C_START]).groupby(s[s.index >= C_START].index.to_period("M")).prod() - 1
    out["C_months_pos"] = float((mon > 0).mean())
    out["C_n_months"] = int(len(mon))
    out["daily"] = s
    return out


def main():
    wins = pickle.load(open(os.path.join(OUT, "pairs_main.pkl"), "rb"))
    m4 = pickle.load(open(os.path.join(OUT, "m4_main.pkl"), "rb"))
    ctrl = pickle.load(open(os.path.join(OUT, "controls.pkl"), "rb"))
    valid = json.load(open(os.path.join(OUT, "valid.json")))
    v5 = json.load(open(os.path.join(OUT, "v5.json"))) if os.path.exists(os.path.join(OUT, "v5.json")) else None
    P = K.Panel()
    NW = len(wins)
    ndays = NW * 7
    years = ndays / 365.0
    dates = pd.date_range(pd.Timestamp(K.H0_MS + K.W0 * 3600000, unit="ms").normalize(), periods=ndays, freq="D")
    rep = dict(meta=dict(NW=NW, first_window=str(dates[0].date()), last_day=str(dates[-1].date()), years=years))
    # ---------------- crash-buy daily (P0 = OFF_*, X14_*), mean of 8 seeds
    z = np.load(CB)
    cbd = {}
    for grp in ("OFF", "X14"):
        rs = []
        for s in SEEDS:
            a, m0 = z["%s_%s" % (grp, s)], int(z["%s_%s__m0" % (grp, s)][0])
            nday = (m0 + len(a)) // 1440
            idx = np.arange(m0 // 1440 + 1, nday) * 1440 + 1439 - m0
            idx = idx[(idx >= 0) & (idx < len(a))]
            eqd = a[idx].astype(float)
            dd = CB_DAY0 + pd.to_timedelta((idx + m0) // 1440, unit="D")
            rs.append(pd.Series(eqd[1:] / eqd[:-1] - 1, index=dd[1:]))
        cbd[grp] = pd.concat(rs, axis=1).mean(1)
    rep["crashbuy"] = {g: dict(first=str(v.index[0].date()), last=str(v.index[-1].date()), n=int(len(v)),
                               sharpe=sharpe(v.values)) for g, v in cbd.items()}
    # ---------------- per method
    M = {}
    syms = P.syms
    for m in ("M1", "M2", "M3", "M4"):
        R = {}
        for cv in ("base", "x2", "maker", "gross"):
            if m == "M4":
                eqh, eqd, wk = series_m4(m4[cv])
            else:
                eqh, eqd, wk = series_pairs(wins, m, K.COSTS[cv], mode="gross" if cv == "gross" else "net")
            ps = period_stats(eqd, dates)
            R[cv] = dict(E=ps["E"], C=ps["C"], ALL=ps["ALL"], C_months_pos=ps["C_months_pos"], maxdd_h=maxdd(eqh),
                         worst_week=float(wk.min()), worst_week_idx=int(wk.argmin()), daily=ps["daily"], wk=wk)
        base = R["base"]
        info = {}
        if m != "M4":
            contrib = defaultdict(float)
            ntr, turn, fund, expo, part, why = 0, 0.0, 0.0, 0.0, [], defaultdict(int)
            for w in wins:
                t = w["t"]
                for tr in w["res"][m]["trades"]:
                    key = "-".join(sorted(str(syms[s]) for s, _ in tr["legs"]))
                    contrib[key] += tr["gross"] + tr["fund"] - K.COSTS["base"] * tr["turn"]
                    ntr += 1
                    turn += tr["turn"]
                    fund += tr["fund"]
                    why[tr["why"]] += 1
                    expo += K.G_PAIR * (min(tr["x"], t + K.TRAD) - tr["e"])
                    for s, wv in tr["legs"]:
                        adv = P.Q[t - K.FORM:t, s].sum() / 30.0
                        if adv > 0:
                            part.append(abs(wv) * 1e6 / adv)
            top = sorted(contrib.items(), key=lambda kv: -kv[1])
            tot = sum(contrib.values())
            part = np.array(part)
            info = dict(n_trades=ntr, trades_per_month=ntr / (ndays / 30.4375), turnover_x_per_year=turn / years,
                        funding_per_year=fund / years, avg_gross_exposure=expo / (NW * K.TRAD), exit_reasons=dict(why),
                        n_pairs_distinct=len(contrib), top3=top[:3], sum_contrib=tot, sum_ex_top3=tot - sum(v for _, v in top[:3]),
                        part_p50=float(np.median(part)), part_p95=float(np.percentile(part, 95)),
                        cap_usd_at_p95_1pct=float(1e6 * 0.01 / np.percentile(part, 95)),
                        m1_ntest_mean=float(np.mean([w["ntest"] for w in wins])),
                        m1_npass_mean=float(np.mean([w["npass"] for w in wins])),
                        m1_windows_lt10=int(sum(len(w["p1"]) < K.NPAIR for w in wins)))
        else:
            r = m4["base"]
            attr = r["attr"]
            top = np.argsort(-attr)[:3]
            part = r["part"]
            info = dict(n_trades=int(r["n_entries"].sum()), trades_per_month=float(r["n_entries"].sum() / (ndays / 30.4375)),
                        turnover_x_per_year=float(r["turn"] / np.mean(r["eq"]) / years),
                        ann_price=r["gsum"] / years, ann_funding=r["fsum"] / years, ann_cost=r["csum"] / years,
                        avg_gross_exposure=float(r["gross_exp"].mean()), frac_hours_invested=float((r["gross_exp"] > 0).mean()),
                        top3=[(str(syms[j]), float(attr[j])) for j in top], sum_contrib=float(attr.sum()),
                        sum_ex_top3=float(attr.sum() - attr[top].sum()),
                        part_p50=float(np.median(part)), part_p95=float(np.percentile(part, 95)),
                        cap_usd_at_p95_1pct=float(1e6 * 0.01 / np.percentile(part, 95)))
        # crash-buy correlation + episodes
        d = base["daily"]
        cor = {}
        for g, v in cbd.items():
            j = pd.concat([d, v], axis=1, join="inner").dropna()
            jw = (1 + j).resample("W-TUE").prod() - 1
            worst = j.iloc[:, 1] <= j.iloc[:, 1].quantile(0.05)
            cor[g] = dict(corr_daily=float(j.corr().iloc[0, 1]), corr_weekly=float(jw.corr().iloc[0, 1]), n=int(len(j)),
                          mean_on_cb_worst5pct=float(j.iloc[:, 0][worst].mean()), cb_mean_worst5pct=float(j.iloc[:, 1][worst].mean()))
        ep = {}
        for nm, (a, b) in EPISODES.items():
            x = d[(d.index >= a) & (d.index <= b)]
            y = cbd["X14"][(cbd["X14"].index >= a) & (cbd["X14"].index <= b)]
            ep[nm] = dict(ret=float((1 + x).prod() - 1), cb_x14=float((1 + y).prod() - 1) if len(y) else None)
        # criteria (pre-reg sec.5)
        crit = dict(
            G1_sharpe_E=base["E"]["sharpe"] >= 1.0, G1_sharpe_C=base["C"]["sharpe"] >= 1.0,
            G2_maxdd=base["maxdd_h"] >= -0.20,
            G3_x2_pos_E=R["x2"]["E"]["ret"] > 0, G3_x2_pos_C=R["x2"]["C"]["ret"] > 0,
            G4_months_C=base["C_months_pos"] >= 0.60,
            G5_worst_week=base["worst_week"] >= -0.10,
            G6_ex_top3=info["sum_ex_top3"] > 0)
        alive = all(crit.values())
        M[m] = dict(stats={cv: {k: v for k, v in R[cv].items() if k not in ("daily", "wk")} for cv in R},
                    info=info, crashbuy_corr=cor, episodes=ep, criteria={k: bool(v) for k, v in crit.items()},
                    n_pass=int(sum(crit.values())), ALIVE_T1=bool(alive))
        log.info("%s base E %.2f C %.2f | gross E %.2f C %.2f | maxdd %.3f wk %.3f | x2 E %.3f C %.3f | alive %s",
                 m, base["E"]["sharpe"], base["C"]["sharpe"], R["gross"]["E"]["sharpe"], R["gross"]["C"]["sharpe"],
                 base["maxdd_h"], base["worst_week"], R["x2"]["E"]["ret"], R["x2"]["C"]["ret"], alive)
    # ---------------- V3 controls
    v3 = {}
    for m in ("M1", "M2", "M3"):
        for flip, tag in ((1, "C1_flip"), (0, "C2_noflip")):
            reps = [tot[m] for rp, fl, tot in ctrl["pairs"] if fl == flip]
            g = np.array([x[:, 0].sum() / years for x in reps])
            u = np.array([K.COSTS["base"] * x[:, 1].sum() / years for x in reps])
            f = np.array([x[:, 2].sum() / years for x in reps])
            net = g + f - u
            se = g.std(ddof=1) / np.sqrt(len(g))
            v3.setdefault(m, {})[tag] = dict(n=len(g), gross_mean=float(g.mean()), gross_sd=float(g.std(ddof=1)),
                                             gross_t=float(g.mean() / se) if se > 0 else 0.0, cost_mean=float(u.mean()),
                                             fund_mean=float(f.mean()), net_mean=float(net.mean()))
        wtot = [w["res"][m] for w in wins]
        v3[m]["method_gross_ann"] = float(sum(r["g"][-1] for r in wtot) / years)
        v3[m]["PASS"] = abs(v3[m]["C1_flip"]["gross_t"]) < 2.5
    g4 = np.array([r["gsum"] / years for _, r in ctrl["m4"]])
    f4 = np.array([r["fsum"] / years for _, r in ctrl["m4"]])
    c4 = np.array([r["csum"] / years for _, r in ctrl["m4"]])
    se4 = g4.std(ddof=1) / np.sqrt(len(g4))
    v3["M4"] = dict(C1_flip=dict(n=len(g4), gross_mean=float(g4.mean()), gross_sd=float(g4.std(ddof=1)),
                                 gross_t=float(g4.mean() / se4), cost_mean=float(c4.mean()), fund_mean=float(f4.mean()),
                                 net_mean=float((g4 + f4 - c4).mean())),
                    method_gross_ann=float(m4["base"]["gsum"] / years))
    v3["M4"]["PASS"] = abs(v3["M4"]["C1_flip"]["gross_t"]) < 2.5
    v3["PASS"] = all(v3[m]["PASS"] for m in ("M1", "M2", "M3", "M4"))
    # ---------------- deflated Sharpe (report only), N = 4 trials
    srs, info_d = [], {}
    for m in ("M1", "M2", "M3", "M4"):
        eqd = None
    dailies = {}
    for m in ("M1", "M2", "M3", "M4"):
        if m == "M4":
            _, eqd, _ = series_m4(m4["base"])
        else:
            _, eqd, _ = series_pairs(wins, m, K.COSTS["base"])
        dailies[m] = eqd[1:] / eqd[:-1] - 1
        srs.append(dailies[m].mean() / dailies[m].std(ddof=1))
    vsr = float(np.var(srs, ddof=1))
    gam = 0.5772156649
    sr0 = np.sqrt(vsr) * ((1 - gam) * norm.ppf(1 - 1 / 4) + gam * norm.ppf(1 - 1 / (4 * np.e)))
    for m, sr in zip(("M1", "M2", "M3", "M4"), srs):
        x = dailies[m]
        T = len(x)
        den = np.sqrt(1 - skew(x) * sr + (kurtosis(x, fisher=False) - 1) / 4 * sr ** 2)
        M[m]["DSR"] = float(norm.cdf((sr - sr0) * np.sqrt(T - 1) / den))
    rep.update(methods=M, V3=v3, V1=valid["V1"], V2=valid["V2"], V4={k: v for k, v in valid["V4"].items()}, V5=v5)
    json.dump(rep, open(os.path.join(OUT, "report.json"), "w"), indent=1, default=str)
    log.info("V3 %s", json.dumps({m: (v3[m]["C1_flip"]["gross_mean"], v3[m]["C1_flip"]["gross_t"], v3[m]["PASS"])
                                  for m in ("M1", "M2", "M3", "M4")}))


if __name__ == "__main__":
    main()
