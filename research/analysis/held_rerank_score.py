#!/usr/bin/env python3
"""HELD_RERANK_SCORE — so ON (hldrr-*) vs OFF (n700-a1/gabl-seed7/gsb-*) theo pre-reg PREREG_HELD_RERANK.md §6.
Chi tinh tu output Kaggle da fetch (~/kaggle_sim/out): 0 sim, 0 Java. Metric daily-level (MTM phut de phan sau)."""
import json
import sys
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/analysis")
import reset_rule_score as R  # noqa: E402

SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
OFF = {"A1": "n700-a1", "S7": "gabl-seed7", **{s: "gsb-" + s.lower() for s in SEEDS[2:]}}
ON = {s: "hldrr-" + s.lower() for s in SEEDS}
W0 = pd.Timestamp("2021-12-31")
W_START = pd.Timestamp("2022-01-01")
W_END = pd.Timestamp("2025-12-30")

R.MTM_COSTS = {"legacy": R.LEGACY}


def load(tag):
    legs = R.load_legs(tag)
    daily = R.load_daily(tag)
    eq = R.daily_adj(legs, daily, R.LEGACY)
    return legs, daily, eq


def metrics(tag):
    legs, daily, eq = load(tag)
    # n/năm: lệnh đóng trong 2022-2025 / 4
    te = legs["te"]
    cl = legs[(te >= "2022-01-01") & (te < "2026-01-01")]
    n_yr = len(cl) / 4.0
    # equity trong cửa sổ 2022+
    e = eq[eq.index >= W_START]
    e = e[e.index <= W_END]
    if len(e) < 2:
        return None
    yrs = (e.index[-1] - W0).days / 365.25
    cagr22 = ((e.iloc[-1] / e.iloc[0]) ** (1 / ((e.index[-1] - e.index[0]).days / 365.25)) - 1) * 100
    dd = (e / e.cummax() - 1) * 100
    maxdd22 = dd.min()
    calmar22 = cagr22 / abs(maxdd22) if maxdd22 != 0 else float("nan")
    # full-period (daily)
    ef = eq
    yf = (ef.index[-1] - ef.index[0]).days / 365.25
    cagr_all = ((ef.iloc[-1] / ef.iloc[0]) ** (1 / yf) - 1) * 100
    ddf = (ef / ef.cummax() - 1) * 100
    return dict(n_yr=n_yr, cagr22=cagr22, maxdd22=maxdd22, calmar22=calmar22,
                cagr_all=cagr_all, maxdd_all=ddf.min(), eq_final=float(ef.iloc[-1]))


def summ(name, a):
    a = np.array(a, float)
    return dict(mean=float(a.mean()), sd=float(a.std(ddof=1)), min=float(a.min()), max=float(a.max()))


def main():
    off_m = {s: metrics(OFF[s]) for s in SEEDS}
    on_m = {s: metrics(ON[s]) for s in SEEDS}
    for s in SEEDS:
        if off_m[s] is None or on_m[s] is None:
            print("MISSING metric", s, "off", off_m[s], "on", on_m[s])
            sys.exit(1)

    rows = {}
    for s in SEEDS:
        o, n = off_m[s], on_m[s]
        rows[s] = dict(
            n_yr=[round(o["n_yr"], 1), round(n["n_yr"], 1)],
            cagr22=[round(o["cagr22"], 2), round(n["cagr22"], 2)],
            maxdd22=[round(o["maxdd22"], 2), round(n["maxdd22"], 2)],
            calmar22=[round(o["calmar22"], 3), round(n["calmar22"], 3)],
            eq_final=[round(o["eq_final"]), round(n["eq_final"])],
        )

    dn = np.array([on_m[s]["n_yr"] - off_m[s]["n_yr"] for s in SEEDS])
    dc = np.array([on_m[s]["cagr22"] - off_m[s]["cagr22"] for s in SEEDS])
    dcal = np.array([on_m[s]["calmar22"] - off_m[s]["calmar22"] for s in SEEDS])

    # paired t, df=7
    tc = 2.364624  # t 0.975 df 7
    def paired_ci(d):
        m = d.mean()
        se = d.std(ddof=1) / np.sqrt(len(d))
        return m, m - tc * se, m + tc * se

    mn, lo_n, hi_n = paired_ci(dn)
    mc, lo_c, hi_c = paired_ci(dc)

    cal_on_mean = np.mean([on_m[s]["calmar22"] for s in SEEDS])
    cal_off_mean = np.mean([off_m[s]["calmar22"] for s in SEEDS])
    dd_on_worst = min(min(on_m[s]["maxdd22"], on_m[s]["maxdd_all"]) for s in SEEDS)

    rule = {
        "C1_dn_mean": float(mn), "C1_ci": [float(lo_n), float(hi_n)],
        "C1_ok": bool(mn > 0),
        "C2_dcagr_mean": float(mc), "C2_ci": [float(lo_c), float(hi_c)],
        "C2_ok": bool(mc >= -0.5),
        "C3_dd_worst": float(dd_on_worst), "C3_ok": bool(abs(dd_on_worst) <= 40),
        "C4_cal_on_mean": float(cal_on_mean), "C4_thr": float(0.95 * cal_off_mean),
        "C4_cal_off_mean": float(cal_off_mean), "C4_ok": bool(cal_on_mean >= 0.95 * cal_off_mean),
    }
    rule["GO"] = bool(all(rule[c] for c in ("C1_ok", "C2_ok", "C3_ok", "C4_ok")))

    out = dict(rows=rows, off=off_m, on=on_m, dn=dn.tolist(), dc=dc.tolist(), rule=rule)
    json.dump(out, open(REPO + "/docs/result/held_rerank.json", "w"), indent=1, default=str)
    print(json.dumps({"rule": rule, "dn_per_seed": {s: round(dn[i], 1) for i, s in enumerate(SEEDS)},
                      "dcagr_per_seed": {s: round(dc[i], 2) for i, s in enumerate(SEEDS)}}, indent=1))


if __name__ == "__main__":
    main()
