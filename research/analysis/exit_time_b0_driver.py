#!/usr/bin/env python3
"""EXIT_TIME_B0 — cham B0(=P0)/A1/A2 theo docs/prereg/PREREG_EXIT_TIME_B0.md (commit b4b22ddb, chot TRUOC).

A1 = SIM_LOSER_TIME_STOP_HOURS=72 ; A2 = SIM_COND_EXIT_HOURS=72 x SIM_COND_EXIT_MIN_FAV=0.05 (LOSER giu 168).
THUAN PYTHON OFFLINE, 0 Java/sim. DEV <= 2025-12-30. AS-IS (phi base nam trong artifact).
Khung = research/analysis/flat3_crashpen_driver.py (FLAT3_CRASHPEN, d439a206): reset_rule_score (load_legs/load_daily/
core_metrics/ci_pair/run_mtm); cua so 2022+ cua feat_add_v1_score; ghep cap theo long_levers_paired_ruler (sym|start|level).
k = 2 arm so B0 => inflate = sqrt(2 ln 2) = 1.1774.
Luat GO-nghien-cuu (pre-reg §5, tung arm): (1) dPnL>0 va can duoi CI raw>0 va CI infl>0; (2) dPnL theo nam vao >0 o
>=3/4 nam 2022-2025; (3) Calmar_MTM >= B0 ca toan ky va 2022+; (4) T1 PASS. T3 CHI THONG TIN.
Usage: python3 exit_time_b0_driver.py [--parity-only] [--json OUT] [--workers 3] [--mtm-cache PATH]
"""
import argparse
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402
import feat_add_v1_score as F  # noqa: E402,F401  (side effect: R.MTMState co cua so 2022+ -> dd_win/uw_win_days)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("exit_time_b0")

ARMS = ["P0", "A1", "A2"]
TAGS = {"P0": "exit-time-p0", "A1": "exit-time-a1", "A2": "exit-time-a2"}
DESC = {"P0": "B0 (LOSER 168)", "A1": "LOSER_TS 72h", "A2": "COND_EXIT 72h x MFE<5%"}
PARITY_MD5, PARITY_N, PARITY_EQ = "650c386f0d0dfea334af9d55ca2f21d4", 2517, 131908
JAR_SHA = "7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a"
K_INFL = 2
INFL = math.sqrt(2.0 * math.log(K_INFL))      # 1.17741
NREP, SEED, BLOCK_H = 2000, 20260905, 72
ANCHOR = pd.Timestamp("2021-07-01")
WIN0, PRE = pd.Timestamp("2022-01-01"), pd.Timestamp("2021-12-31")
CAL_MULT = 0.90
GO_YEARS = [2022, 2023, 2024, 2025]
SL, SM = "STOP_LOSS_DONE", "STOP_MARKET_DONE"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"


def result_json(tag):
    p = OUT % tag + "result.json"
    return json.load(open(p)) if os.path.exists(p) else {}


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
    gb = "B0_" + b["status"].str.replace("_DONE", "")
    t = pd.concat([pd.DataFrame({"t0": b.loc[common, "t0"], "v": dm, "g": gb.loc[common]}),
                   pd.DataFrame({"t0": b.loc[ob, "t0"], "v": db, "g": "only_b0"}),
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
                halfwidth_raw=float((hi - lo) / 2),
                d_matched=float(dm.sum()), frac_matched_changed=float((dm.abs() > 1e-6).mean()),
                by_year=by_year, by_group=by_grp,
                sum_profit_x_notional_b0=float((b.profit / 100 * b.notional).sum()))


def cut_stats(b, x):
    """mo ta lenh bi luat moi cat: arm STOP_LOSS_DONE voi time_order < 167h; thang muon bi cat (B0 SM -> arm SL)."""
    cut = x[(x["status"] == SL) & (x["time_order"] < 167)]
    cc = cut.index.intersection(b.index)
    common = b.index.intersection(x.index)
    late = common[(b.loc[common, "status"] == SM).values & (x.loc[common, "status"] == SL).values]
    d_late = (x.loc[late, "profit"] - b.loc[late, "profit"]) / 100 * b.loc[late, "notional"]
    saved = common[(b.loc[common, "status"] == SL).values & (x.loc[common, "status"] == SL).values
                   & (x.loc[common, "time_order"] < 167).values]
    d_saved = (x.loc[saved, "profit"] - b.loc[saved, "profit"]) / 100 * b.loc[saved, "notional"]
    return dict(n_cut=int(len(cut)), mean_profit_cut_arm=float(cut["profit"].mean()) if len(cut) else None,
                n_cut_in_b0=int(len(cc)),
                mean_profit_same_trades_b0=float(b.loc[cc, "profit"].mean()) if len(cc) else None,
                b0_status_of_cut=b.loc[cc, "status"].value_counts().to_dict(),
                n_late_winner_cut=int(len(late)), dPnL_late_winner_cut=float(d_late.sum()),
                n_b0loser_cut_early=int(len(saved)), dPnL_b0loser_cut_early=float(d_saved.sum()),
                max_time_order_SL=float(x.loc[x["status"] == SL, "time_order"].max()) if (x["status"] == SL).any() else None,
                n_SL_gt73h=int(((x["status"] == SL) & (x["time_order"] > 73)).sum()))


def per_year(d):
    y = d["ts"].dt.year
    return {int(k): dict(n=int(len(g)), pnl=float(g["pnl"].sum()),
                         tsloss=100 * float((g["status"] == SL).mean())) for k, g in d.groupby(y)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parity-only", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--mtm-cache", default="/home/ubuntu/claude_master/1003/et_mtm.json")
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/exit_time_b0.json")
    a = ap.parse_args()
    R.MTM_COSTS = {"legacy": R.LEGACY}        # as-is: khong hieu chinh phi
    R.K_INFL, R.INFL = K_INFL, INFL           # ci_pair (T3) dung inflate k=2

    arms = ["P0"] if a.parity_only else ARMS
    legs, daily, md5, rj = {}, {}, {}, {}
    for k in arms:
        t = TAGS[k]
        rj[k] = result_json(t)
        legs[k], daily[k], md5[k] = R.load_legs(t), R.load_daily(t), R.md5_of(t)
        log.info("%s %-13s n=%d eq=%.0f md5=%s jar=%s mapper=%s ok=%s phash=%s", k, t, len(legs[k]),
                 daily[k]["equity"].iloc[-1], md5[k], str(rj[k].get("jar_sha256"))[:8], rj[k].get("symbol_mapper"),
                 rj[k].get("ok"), rj[k].get("profile_hash"))
    jar_ok = {k: rj[k].get("jar_sha256") == JAR_SHA for k in arms}
    map_ok = {k: (rj[k].get("symbol_mapper") or 0) >= 800 for k in arms}
    n0, eq0 = len(legs["P0"]), float(daily["P0"]["equity"].iloc[-1])
    par = bool(md5["P0"] == PARITY_MD5 and n0 == PARITY_N and round(eq0) == PARITY_EQ and jar_ok["P0"] and map_ok["P0"])
    log.info("PARITY P0: md5=%s n=%d eq=%.0f jar_ok=%s mapper_ok=%s -> %s", md5["P0"], n0, eq0, jar_ok["P0"],
             map_ok["P0"], "PASS" if par else "*** FAIL => VOID ***")
    if a.parity_only or not par:
        json.dump(dict(parity_ok=par, md5=md5, n=n0, eq=eq0, jar_ok=jar_ok), open(a.json + ".parity", "w"), indent=1)
        sys.exit(0 if par else 3)
    if not all(jar_ok.values()) or not all(map_ok.values()):
        log.info("*** jar/mapper sai o arm %s => DUNG", [k for k in arms if not (jar_ok[k] and map_ok[k])])
        sys.exit(4)

    bp = ld_pair(TAGS["P0"])
    xp = {k: ld_pair(TAGS[k]) for k in ARMS[1:]}
    # ---- Cong 1: key co hieu luc
    gate1 = {}
    for k in ARMS[1:]:
        cs = cut_stats(bp, xp[k])
        g = {"phash_diff": rj[k].get("profile_hash") != rj["P0"].get("profile_hash"), "md5_diff": md5[k] != md5["P0"]}
        if k == "A1":
            g["no_SL_gt73h"] = cs["n_SL_gt73h"] == 0
        gate1[k] = [all(g.values()), g, cs]
        log.info("CONG1 %s %s %s | cut %s", k, "PASS" if gate1[k][0] else "*** FAIL => VOID arm ***", g, cs)
    arms_ok = ["P0"] + [k for k in ARMS[1:] if gate1[k][0]]

    # ---- MTM phut (toan ky + cua so reset 2022-01-01), cache theo md5
    raw = json.load(open(a.mtm_cache)) if os.path.exists(a.mtm_cache) else {}
    miss = {k: legs[k] for k in arms_ok if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(a.mtm_cache, "w"))
    mtm = {k: raw[k]["legacy"] for k in arms_ok}
    for k in mtm:
        for f in ("dd_year", "uw_year"):
            mtm[k][f] = {int(y): float(v) for y, v in mtm[k][f].items()}

    M = {}
    for k in arms_ok:
        m = R.core_metrics(k, legs[k], daily[k], "legacy")
        lw = legs[k][legs[k]["ts"] >= WIN0].reset_index(drop=True)
        m22 = R.core_metrics(k, lw, daily[k].loc[PRE:], "legacy")
        M[k] = dict(tag=TAGS[k], desc=DESC[k], md5=md5[k], n=m["n"], equity=m["equity"],
                    sum_pnl=float(legs[k]["pnl"].sum()),
                    cagr=m["cagr"], dd_mtm=mtm[k]["dd_total"], uw_mtm=mtm[k]["uw_total_days"],
                    calmar=m["cagr"] / abs(mtm[k]["dd_total"]),
                    n22=int(len(lw)), cagr22=m22["cagr"], dd_mtm22=mtm[k]["dd_win"], uw_mtm22=mtm[k]["uw_win_days"],
                    calmar22=m22["cagr"] / abs(mtm[k]["dd_win"]),
                    dd_daily=m["maxdd_daily"], qmin=m["qmin"], yr=m["yr"], qr=m["qr"], neg_year=m["neg_year"],
                    dd_mtm_year=mtm[k]["dd_year"], q_star=m["q_star"], top1_pct=m["top1_pct"],
                    conc_max=m["conc_max"], gross_max=m["gross_max"], rates=m["rates"],
                    year=per_year(legs[k]), result_json=rj[k])

    B = M["P0"]
    for k in arms_ok:
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
            x["go"] = [None, "ref"]
            continue
        ci = R.ci_pair(legs[k], legs["P0"])
        dw = x["rates"]["win%"] - B["rates"]["win%"]
        dt = x["rates"]["TSloss%"] - B["rates"]["TSloss%"]
        t3 = {"dwin>=-2": (dw >= -2.0, dw), "dTSloss<=2.5": (dt <= 2.5, dt),
              "mP|SM_not_worse": (not ci["mP|SM"]["worse_sig"], ci["mP|SM"]),
              "mP|SL_not_worse": (not ci["mP|SL"]["worse_sig"], ci["mP|SL"])}
        t4 = {"Calmar_full>=0.9xB0": (x["calmar"] >= CAL_MULT * B["calmar"], [x["calmar"], CAL_MULT * B["calmar"]]),
              "Calmar_2022>=0.9xB0": (x["calmar22"] >= CAL_MULT * B["calmar22"], [x["calmar22"], CAL_MULT * B["calmar22"]]),
              "conc<=B0": (x["conc_max"] <= B["conc_max"], [x["conc_max"], B["conc_max"]])}
        x["t3"] = [all(v[0] for v in t3.values()), t3]
        x["t4"] = [all(v[0] for v in t4.values()), t4]
        x["ci_rates"] = ci
        p = paired(bp, xp[k])
        x["paired"] = p
        x["gate1"] = gate1[k]
        npos = sum(1 for y in GO_YEARS if p["by_year"].get(y, 0.0) > 0)
        go = {"(1)dPnL>0_ngoai_CI_raw_va_infl": (p["dPnL"] > 0 and p["ci_raw"][0] > 0 and p["ci_infl"][0] > 0,
                                                [p["dPnL"], p["ci_raw"], p["ci_infl"]]),
              "(2)>=3/4_nam_2022-25_duong": (npos >= 3, npos),
              "(3)Calmar_MTM>=B0_toanky_va_2022+": (x["calmar"] >= B["calmar"] and x["calmar22"] >= B["calmar22"],
                                                   [x["calmar"], B["calmar"], x["calmar22"], B["calmar22"]]),
              "(4)T1_PASS": (x["t1"][0], None)}
        x["go"] = [all(v[0] for v in go.values()), go]
        x["frac_sum_pnl_vs_b0"] = x["sum_pnl"] / B["sum_pnl"]
    gos = [k for k in arms_ok[1:] if M[k]["go"][0]]
    pick = max(gos, key=lambda k: M[k]["paired"]["ci_infl"][0]) if gos else None
    verdict = ("GO-nghien-cuu: %s" % pick) if pick else "NO-GO"

    f = lambda v: "PASS" if v is True else ("FAIL" if v is False else "ref")
    log.info("")
    log.info("%-3s %4s %7s %7s %6s %7s %6s %6s | %6s %7s %6s %6s | %6s %6s | %-4s %-4s %-4s %-4s %-4s",
             "arm", "n", "equity", "SumPnL", "CAGR", "ddMTM", "UW", "Calm", "CAGR22", "ddMTM22", "UW22", "Cal22",
             "win%", "TSl%", "T1", "T2", "T3", "T4", "GO")
    for k in arms_ok:
        x = M[k]
        log.info("%-3s %4d %7.0f %7.0f %6.2f %7.2f %6.1f %6.3f | %6.2f %7.2f %6.1f %6.3f | %6.2f %6.2f | %-4s %-4s %-4s %-4s %-4s",
                 k, x["n"], x["equity"], x["sum_pnl"], x["cagr"], x["dd_mtm"], x["uw_mtm"], x["calmar"],
                 x["cagr22"], x["dd_mtm22"], x["uw_mtm22"], x["calmar22"], x["rates"]["win%"], x["rates"]["TSloss%"],
                 f(x["t1"][0]), f(x["t2"][0]), f(x["t3"][0]), f(x["t4"][0]), f(x["go"][0]))
    for k in arms_ok:
        log.info("%s ROI/nam %s | ddMTM/nam %s | qmin %.2f", k, {y: round(v, 1) for y, v in M[k]["yr"].items()},
                 {y: round(v, 1) for y, v in M[k]["dd_mtm_year"].items()}, M[k]["qmin"])
    for k in arms_ok[1:]:
        p = M[k]["paired"]
        log.info("%s dPnL %+.0f CI raw [%+.0f; %+.0f] infl [%+.0f; %+.0f] common %d only_b0 %d only_arm %d | nam %s | nhom %s",
                 k, p["dPnL"], *p["ci_raw"], *p["ci_infl"], p["n_common"], p["n_only_b0"], p["n_only_arm"],
                 {y: round(v) for y, v in p["by_year"].items()}, {g: round(v) for g, v in p["by_group"].items()})
        log.info("%s GO %s", k, {g: v[0] for g, v in M[k]["go"][1].items()})
        log.info("%s T3 %s", k, {g: (v[0], round(v[1], 2) if isinstance(v[1], float) else None) for g, v in M[k]["t3"][1].items()})
    log.info("VERDICT: %s", verdict)
    js = dict(prereg="docs/prereg/PREREG_EXIT_TIME_B0.md", prereg_commit="b4b22ddb", jar_sha256=JAR_SHA, k_infl=K_INFL,
              inflate=INFL, nrep=NREP, seed=SEED, parity=dict(ok=par, md5=md5["P0"], n=n0, eq=eq0),
              gate1={k: v[:2] for k, v in gate1.items()}, verdict=verdict, pick=pick, metrics=M)
    json.dump(js, open(a.json, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)


if __name__ == "__main__":
    main()
