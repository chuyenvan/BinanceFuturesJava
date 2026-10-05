#!/usr/bin/env python3
"""FLAT3_CRASHPEN — cham B0(=P0)/P1/P2 theo docs/prereg/PREREG_FLAT3_CRASHPEN.md (commit 6362bd18, chot TRUOC).

THUAN PYTHON OFFLINE, 0 Java/sim. DEV <= 2025-12-30. AS-IS (phi base + phat da nam trong artifact).
Tai dung: reset_rule_score (load_legs/load_daily/core_metrics/ci_pair/run_mtm); cua so 2022+ cua feat_add_v1_score
(MTMStateW reset 2022-01-01 UTC, import => monkeypatch R); ghep cap theo long_levers_paired_ruler (sym|start|level);
episode theo audit_g2flat3_20261002_stats (cum ngay dong lenh, khoang trong <= 2 ngay).
k = 2 arm so B0 => inflate = sqrt(2 ln 2) = 1.1774.
Usage: python3 flat3_crashpen_driver.py [--parity-only] [--json OUT] [--workers 3] [--mtm-cache PATH]
"""
import argparse
import json
import logging
import math
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402
import feat_add_v1_score as F  # noqa: E402,F401  (side effect: R.MTMState co cua so 2022+ -> dd_win/uw_win_days)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("flat3_crashpen")

ARMS = ["P0", "P1", "P2"]
TAGS = {"P0": "flat3-cp-p0", "P1": "flat3-cp-p1", "P2": "flat3-cp-p2"}
PEN = {"P0": 0.0, "P1": 0.0069, "P2": 0.0138}
PARITY_MD5, PARITY_N, PARITY_EQ = "650c386f0d0dfea334af9d55ca2f21d4", 2517, 131908
JAR_SHA = "d944bea5f90a3c2cc4fa5bd45ee488b168459a9782719e909f5eb11f3c95ce89"
K_INFL = 2
INFL = math.sqrt(2.0 * math.log(K_INFL))      # 1.17741
NREP, SEED, BLOCK_H = 2000, 20260905, 72
ANCHOR = pd.Timestamp("2021-07-01")
WIN0, PRE = pd.Timestamp("2022-01-01"), pd.Timestamp("2021-12-31")
CAL_MULT = 0.90
WARN_CAL22, WARN_PNL_FRAC = 1.2, 0.60
YEARS = [2021, 2022, 2023, 2024, 2025]
RX_CP = re.compile(r"\[CRASH-PENALTY\] SUMMARY penalty=(\S+) total=(\d+) byYear=\{(.*)\}")
OUT = "/home/ubuntu/kaggle_sim/out/%s/"


def result_json(tag):
    p = OUT % tag + "result.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def crashpen(tag):
    """[CRASH-PENALTY] SUMMARY tu sim.out -> (total, {year: n}); vang => (0, {})."""
    tot, byy = 0, {}
    with open(OUT % tag + "logs/sim.out", errors="ignore") as fh:
        for line in fh:
            m = RX_CP.search(line)
            if m:
                tot = int(m.group(2))
                byy = {int(k): int(v) for k, v in (kv.split("=") for kv in m.group(3).replace(" ", "").split(",") if kv)}
    return tot, byy


def ld_pair(tag):
    """dung y logic long_levers_paired_ruler.ld (doc printDone tho, khoa sym|start|level, bo trung)."""
    d = pd.read_csv(OUT % tag + "storage/printDone.csv")
    d["t0"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    d["notional"] = d.quantity * d.entry
    d["key"] = d.sym + "|" + d.start + "|" + d.level
    d = d.drop_duplicates("key")
    return d.set_index("key")


def paired(b, x):
    """dPnL size-neutral ghep cap vs B0; CI block-72h theo gio vao, NREP 2000, seed 20260905 (rng moi moi arm)."""
    common = b.index.intersection(x.index)
    ob, oa = b.index.difference(x.index), x.index.difference(b.index)
    dm = (x.loc[common, "profit"] - b.loc[common, "profit"]) / 100 * b.loc[common, "notional"]
    db = -(b.loc[ob, "profit"] / 100 * b.loc[ob, "notional"])
    da = x.loc[oa, "profit"] / 100 * x.loc[oa, "notional"]
    grp_b = np.where(b["time_order"] <= 0, "B0_0h", "B0_gt0h")
    gb = pd.Series(grp_b, index=b.index)
    t = pd.concat([pd.DataFrame({"t0": b.loc[common, "t0"], "v": dm, "g": gb.loc[common]}),
                   pd.DataFrame({"t0": b.loc[ob, "t0"], "v": db, "g": gb.loc[ob]}),
                   pd.DataFrame({"t0": x.loc[oa, "t0"], "v": da, "g": "only_arm"})])
    t["blk"] = ((t.t0 - ANCHOR).dt.total_seconds() // (BLOCK_H * 3600)).astype(int)
    s = t.groupby("blk").v.sum().values
    rng = np.random.default_rng(SEED)
    bs = np.array([s[rng.integers(0, len(s), len(s))].sum() for _ in range(NREP)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    obs = float(t.v.sum())
    ilo, ihi = obs - (obs - lo) * INFL, obs + (hi - obs) * INFL
    by_year = {int(y): float(v) for y, v in t.groupby(t.t0.dt.year).v.sum().items()}
    by_grp = {str(g): float(v) for g, v in t.groupby("g").v.sum().items()}
    return dict(n_arm=int(len(x)), n_common=int(len(common)), n_only_b0=int(len(ob)), n_only_arm=int(len(oa)),
                dPnL=obs, ci_raw=[float(lo), float(hi)], ci_infl=[float(ilo), float(ihi)],
                d_matched=float(dm.sum()), frac_matched_changed=float((dm.abs() > 1e-6).mean()),
                by_year=by_year, by_group=by_grp,
                sum_profit_x_notional_b0=float((b.profit / 100 * b.notional).sum()))


def episodes_top5(d):
    """cum ngay DONG lenh (khoang trong <= 2 ngay) -> top-5 theo SumPnL / SumPnL toan ky (audit_g2flat3 logic)."""
    days = pd.to_datetime(d["end"].str[:8], format="%Y%m%d")
    ud = np.sort(days.unique())
    eid, cur = {}, 0
    for i, x in enumerate(ud):
        if i and (x - ud[i - 1]) / np.timedelta64(1, "D") > 2:
            cur += 1
        eid[x] = cur
    ep = d.assign(ep=days.map(eid)).groupby("ep").agg(a=("end", "min"), b=("end", "max"), s=("pnl", "sum"))
    ep = ep.sort_values("s", ascending=False)
    tot = float(d["pnl"].sum())
    top = [(str(r.a)[:8], str(r.b)[:8], round(float(r.s)), round(100 * float(r.s) / tot, 1)) for r in ep.head(5).itertuples()]
    return dict(n_episodes=int(len(ep)), top5=top, top5_share=round(100 * float(ep.s.head(5).sum()) / tot, 2))


def hour0(d):
    """lenh dong TRONG GIO VAO = time_order <= 0 (bucket '0h' cua AUDIT_LONG_LEVERS)."""
    tot = float(d["pnl"].sum())
    h = d[d["time_order"] <= 0]
    r = d[d["time_order"] > 0]
    return dict(n0=int(len(h)), pnl0=float(h["pnl"].sum()), share0=100 * float(h["pnl"].sum()) / tot,
                n_rest=int(len(r)), pnl_rest=float(r["pnl"].sum()), sum_pnl=tot)


def per_year(d):
    y = d["ts"].dt.year
    return {int(k): dict(n=int(len(g)), pnl=float(g["pnl"].sum()),
                         tsloss=100 * float((g["status"] == "STOP_LOSS_DONE").mean())) for k, g in d.groupby(y)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parity-only", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--mtm-cache", default="/home/ubuntu/claude_master/1002/flat3cp_mtm.json")
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/flat3_crashpen.json")
    a = ap.parse_args()
    R.MTM_COSTS = {"legacy": R.LEGACY}        # as-is: khong hieu chinh phi
    R.K_INFL, R.INFL = K_INFL, INFL           # ci_pair (T3) dung inflate k=2

    arms = ["P0"] if a.parity_only else ARMS
    legs, daily, md5, rj = {}, {}, {}, {}
    for k in arms:
        t = TAGS[k]
        rj[k] = result_json(t)
        legs[k], daily[k], md5[k] = R.load_legs(t), R.load_daily(t), R.md5_of(t)
        log.info("%s %-12s n=%d eq=%.0f md5=%s jar=%s mapper=%s ok=%s", k, t, len(legs[k]), daily[k]["equity"].iloc[-1],
                 md5[k], str(rj[k].get("jar_sha256"))[:8], rj[k].get("symbol_mapper"), rj[k].get("ok"))
    jar_ok = {k: rj[k].get("jar_sha256") == JAR_SHA for k in arms}
    n0, eq0 = len(legs["P0"]), float(daily["P0"]["equity"].iloc[-1])
    par = bool(md5["P0"] == PARITY_MD5 and n0 == PARITY_N and round(eq0) == PARITY_EQ and jar_ok["P0"])
    log.info("PARITY P0: md5=%s n=%d eq=%.0f jar_ok=%s -> %s", md5["P0"], n0, eq0, jar_ok["P0"],
             "PASS" if par else "*** FAIL => VOID ***")
    if a.parity_only or not par:
        json.dump(dict(parity_ok=par, md5=md5, n=n0, eq=eq0, jar_ok=jar_ok), open(a.json + ".parity", "w"), indent=1)
        sys.exit(0 if par else 3)
    if not all(jar_ok.values()):
        log.info("*** jar sai o arm %s => DUNG", [k for k, v in jar_ok.items() if not v])
        sys.exit(4)

    # ---- MTM phut (toan ky + cua so reset 2022-01-01), cache theo md5
    raw = json.load(open(a.mtm_cache)) if os.path.exists(a.mtm_cache) else {}
    miss = {k: legs[k] for k in arms if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(a.mtm_cache, "w"))
    mtm = {k: raw[k]["legacy"] for k in arms}
    for k in mtm:
        for f in ("dd_year", "uw_year"):
            mtm[k][f] = {int(y): float(v) for y, v in mtm[k][f].items()}

    M = {}
    for k in arms:
        m = R.core_metrics(k, legs[k], daily[k], "legacy")
        lw = legs[k][legs[k]["ts"] >= WIN0].reset_index(drop=True)
        m22 = R.core_metrics(k, lw, daily[k].loc[PRE:], "legacy")
        cp_tot, cp_y = crashpen(TAGS[k])
        M[k] = dict(tag=TAGS[k], penalty=PEN[k], md5=md5[k], n=m["n"], equity=m["equity"], sum_pnl=float(legs[k]["pnl"].sum()),
                    cagr=m["cagr"], dd_mtm=mtm[k]["dd_total"], uw_mtm=mtm[k]["uw_total_days"],
                    calmar=m["cagr"] / abs(mtm[k]["dd_total"]),
                    n22=int(len(lw)), cagr22=m22["cagr"], dd_mtm22=mtm[k]["dd_win"], uw_mtm22=mtm[k]["uw_win_days"],
                    calmar22=m22["cagr"] / abs(mtm[k]["dd_win"]),
                    dd_daily=m["maxdd_daily"], qmin=m["qmin"], yr=m["yr"], qr=m["qr"], neg_year=m["neg_year"],
                    dd_mtm_year=mtm[k]["dd_year"], q_star=m["q_star"], top1_pct=m["top1_pct"],
                    conc_max=m["conc_max"], gross_max=m["gross_max"], rates=m["rates"],
                    episodes=episodes_top5(legs[k]), hour0=hour0(legs[k]), year=per_year(legs[k]),
                    crash_total=cp_tot, crash_by_year=cp_y, result_json=rj[k])

    B = M["P0"]
    bp = ld_pair(TAGS["P0"])
    for k in arms:
        x = M[k]
        worst = min(x["dd_mtm_year"].values())
        t1 = {"maxDD_phut_nam>=-40": (worst >= -40.0, worst), "UW<=250": (x["uw_mtm"] <= 250.0, x["uw_mtm"]),
              "qmin>=-20": (x["qmin"] >= -20.0, x["qmin"]), "0_nam_am": (len(x["neg_year"]) == 0, x["neg_year"]),
              "conc<=15": (x["conc_max"] <= 15.0, x["conc_max"])}
        t2 = {"q*>=15": (x["q_star"] is not None and x["q_star"] >= 15.0, x["q_star"]),
              "top1%<=25": (x["top1_pct"] <= 25.0, x["top1_pct"])}
        x["t1"] = [all(v[0] for v in t1.values()), t1]
        x["t2"] = [all(v[0] for v in t2.values()), t2]
        if k == "P0":
            x["t3"] = x["t4"] = [None, "ref"]
            continue
        ci = R.ci_pair(legs[k], legs["P0"])
        dw = x["rates"]["win%"] - B["rates"]["win%"]
        dt = x["rates"]["TSloss%"] - B["rates"]["TSloss%"]
        t3 = {"dwin>=-2": (dw >= -2.0, dw), "dTSloss<=2.5": (dt <= 2.5, dt),
              "mP|SM_not_worse": (not ci["mP|SM"]["worse_sig"], ci["mP|SM"]), "mP|SL_not_worse": (not ci["mP|SL"]["worse_sig"], ci["mP|SL"])}
        t4 = {"Calmar_full>=0.9xB0": (x["calmar"] >= CAL_MULT * B["calmar"], [x["calmar"], CAL_MULT * B["calmar"]]),
              "Calmar_2022>=0.9xB0": (x["calmar22"] >= CAL_MULT * B["calmar22"], [x["calmar22"], CAL_MULT * B["calmar22"]]),
              "conc<=B0": (x["conc_max"] <= B["conc_max"], [x["conc_max"], B["conc_max"]])}
        x["t3"] = [all(v[0] for v in t3.values()), t3]
        x["t4"] = [all(v[0] for v in t4.values()), t4]
        x["ci_rates"] = ci
        x["paired"] = paired(bp, ld_pair(TAGS[k]))
        x["frac_sum_pnl_vs_b0"] = x["sum_pnl"] / B["sum_pnl"]
    p1 = M["P1"]
    warn = bool(p1["calmar22"] < WARN_CAL22 or p1["sum_pnl"] < WARN_PNL_FRAC * B["sum_pnl"])

    f = lambda v: "PASS" if v is True else ("FAIL" if v is False else "ref")
    log.info("")
    log.info("%-3s %5s %4s %7s %7s %6s %7s %6s %6s | %6s %7s %6s %6s | %5s %5s %5s | %-4s %-4s %-4s %-4s",
             "arm", "pen", "n", "equity", "SumPnL", "CAGR", "ddMTM", "UW", "Calm", "CAGR22", "ddMTM22", "UW22",
             "Cal22", "top5e", "h0%", "#phat", "T1", "T2", "T3", "T4")
    for k in arms:
        x = M[k]
        log.info("%-3s %5.4f %4d %7.0f %7.0f %6.2f %7.2f %6.1f %6.3f | %6.2f %7.2f %6.1f %6.3f | %5.1f %5.1f %5d | %-4s %-4s %-4s %-4s",
                 k, x["penalty"], x["n"], x["equity"], x["sum_pnl"], x["cagr"], x["dd_mtm"], x["uw_mtm"], x["calmar"],
                 x["cagr22"], x["dd_mtm22"], x["uw_mtm22"], x["calmar22"], x["episodes"]["top5_share"],
                 x["hour0"]["share0"], x["crash_total"], f(x["t1"][0]), f(x["t2"][0]), f(x["t3"][0]), f(x["t4"][0]))
    for k in arms[1:]:
        p = M[k]["paired"]
        log.info("%s dPnL %+.0f CI raw [%+.0f; %+.0f] infl [%+.0f; %+.0f] common %d only_b0 %d only_arm %d | nam %s | nhom %s",
                 k, p["dPnL"], *p["ci_raw"], *p["ci_infl"], p["n_common"], p["n_only_b0"], p["n_only_arm"],
                 {y: round(v) for y, v in p["by_year"].items()}, {g: round(v) for g, v in p["by_group"].items()})
        log.info("%s h0: n %d SumPnL %.0f (%.1f%%) | rest %.0f | SumPnL/B0 %.3f | #phat/nam %s", k, M[k]["hour0"]["n0"],
                 M[k]["hour0"]["pnl0"], M[k]["hour0"]["share0"], M[k]["hour0"]["pnl_rest"], M[k]["frac_sum_pnl_vs_b0"],
                 M[k]["crash_by_year"])
    log.info("P0 h0: n %d SumPnL %.0f (%.1f%%)", B["hour0"]["n0"], B["hour0"]["pnl0"], B["hour0"]["share0"])
    log.info("CANH BAO (P1 Calmar22 < %.1f hoac SumPnL < %.0f%% B0): %s", WARN_CAL22, 100 * WARN_PNL_FRAC,
             "KICH — B0 KHONG du ben voi gia khop that" if warn else "khong kich")
    js = dict(prereg="docs/prereg/PREREG_FLAT3_CRASHPEN.md", prereg_commit="6362bd18", jar_sha256=JAR_SHA, k_infl=K_INFL,
              inflate=INFL, nrep=NREP, seed=SEED, parity=dict(ok=par, md5=md5["P0"], n=n0, eq=eq0),
              warn_rule=dict(cal22_lt=WARN_CAL22, sum_pnl_frac_lt=WARN_PNL_FRAC), warn=warn, metrics=M)
    json.dump(js, open(a.json, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)


if __name__ == "__main__":
    main()
