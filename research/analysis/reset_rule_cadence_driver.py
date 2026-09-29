#!/usr/bin/env python3
"""RESET_RULE_R4_CADENCE — cham C0/C1 theo LUAT 4 TANG §9 (RISK_APPETITE, owner 09-29).

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-30.
Dung lai ham cua reset_rule_score.py (load/core_metrics/ci_pair/run_mtm) — KHONG viet lai thuat toan.
- T1 bo tran gross<=70 — giu MTM phut / UW / qmin / 0 nam am / conc 15.
- T2 bo "bo top-3 episode" — giu q*>=15 + top-1%<=25.
- T3 bo mP|SM/mP|SL — giu win%>=-2.0pp & TSloss%<=+2.5pp (diem, so C0).
- T4 MOI: n la muc tieu chinh (bao cao, KHONG gate); Calmar_MTM >= 0.90 x C0; conc <= C0.
- k=1 ung vien => INFL=1.0 (single comparison, khong hieu chinh da so sanh).

Artifact C0/C1 chay o phi base (0.1116%/vong) => cham "as-is" (cost=legacy = khong hieu chinh pnl).

Usage: python3 reset_rule_cadence_driver.py [--json OUT] [--report OUT] [--skip-mtm]
"""
import argparse
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("r4cad")

KOUT = "/home/ubuntu/kaggle_sim/out"
TAGS = ["r4-cad-c0", "r4-cad-c1"]
B_STAR = "r4-cad-c0"
K_INFL = 1
INFL = 1.0                     # k=1 => single comparison, khong hieu chinh (sqrt(2 ln k) chi dung k>=2)

CALMAR_MULT = 0.90             # T4 moi: Calmar_MTM >= 0.90 x C0
CONC_LE = True                 # T4: conc <= C0
PARITY_MD5 = "06fd6e9aa9c916945b2cf12310b337ff"


def tagdir(tag):
    return os.path.join(KOUT, tag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/r4cad_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/r4_cadence.json")
    ap.add_argument("--report", default="/home/ubuntu/r4_cadence_report.txt")
    a = ap.parse_args()

    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}

    legs, daily, md5 = {}, {}, {}
    log.info("R4_CADENCE — cham %d arm theo §9 | k=%d INFL=%.2f | as-is (phi base trong artifact)",
             len(TAGS), K_INFL, INFL)
    for t in TAGS:
        legs[t] = R.load_legs(t)
        daily[t] = R.load_daily(t)
        md5[t] = R.md5_of(t)
        log.info("%-12s n=%d equity=%.0f md5=%s", t, len(legs[t]),
                 daily[t]["equity"].iloc[-1], md5[t][:8])

    parity_ok = md5[B_STAR] == PARITY_MD5
    log.info("PARITY C0: md5=%s (expected 06fd6e9a...) -> %s", md5[B_STAR],
             "PASS" if parity_ok else "*** FAIL ***")

    m = {t: R.core_metrics(t, legs[t], daily[t], "legacy") for t in TAGS}

    R.K_INFL = K_INFL
    R.INFL = INFL
    ci = {}
    for t in TAGS:
        if t == B_STAR:
            ci[t] = {k: dict(obs=0.0, lo=0.0, hi=0.0, worse_sig=False) for k in R.RATE_KEYS}
        else:
            ci[t] = R.ci_pair(legs[t], legs[B_STAR])

    mtm = {}
    if not a.skip_mtm:
        if a.mtm_cache and os.path.exists(a.mtm_cache):
            with open(a.mtm_cache) as fh:
                raw = json.load(fh)
            log.info("  [cache] %s", a.mtm_cache)
        else:
            raw = R.run_mtm(legs, workers=a.workers, chunk=30)
            if a.mtm_cache:
                with open(a.mtm_cache, "w") as fh:
                    json.dump(raw, fh)
        for t in TAGS:
            mtm[t] = raw[t]["legacy"]
        log.info("TU KIEM MTM C0(=R4): dd_total=%.2f (P2 -16.42) | UW=%.1f ngay (P2 164.7)",
                 mtm[B_STAR]["dd_total"], mtm[B_STAR]["uw_total_days"])

    def tier1(t):
        x = mtm[t]
        worst_y = min(x["dd_year"].values()) if x["dd_year"] else float("nan")
        ok = {"maxDD_phut_nam": (worst_y >= -40.0, worst_y),
              "UW": (x["uw_total_days"] <= 250.0, x["uw_total_days"]),
              "qmin": (m[t]["qmin"] >= -20.0, m[t]["qmin"]),
              "0_nam_am": (len(m[t]["neg_year"]) == 0, m[t]["neg_year"]),
              "conc": (m[t]["conc_max"] <= 15.0, m[t]["conc_max"])}
        return all(v[0] for v in ok.values()), ok

    def tier2(t):
        ok = {"q*": (m[t]["q_star"] is not None and m[t]["q_star"] >= 15.0, m[t]["q_star"]),
              "top1%": (m[t]["top1_pct"] <= 25.0, m[t]["top1_pct"])}
        return all(v[0] for v in ok.values()), ok

    def tier3(t):
        if t == B_STAR:
            return None, {"ref": True}
        r, rb = m[t]["rates"], m[B_STAR]["rates"]
        dw = r["win%"] - rb["win%"]
        dt = r["TSloss%"] - rb["TSloss%"]
        det = {"win%_d": (dw >= -2.0, dw), "TSloss%_d": (dt <= 2.5, dt)}
        return all(v[0] for v in det.values()), det

    def tier4(t):
        if t == B_STAR:
            return None, {"ref": True}
        cal = m[t]["cagr"] / abs(mtm[t]["dd_total"]) if mtm[t]["dd_total"] not in (0, None) else float("nan")
        calb = m[B_STAR]["cagr"] / abs(mtm[B_STAR]["dd_total"])
        ok = {"Calmar>=0.90xC0": (cal >= CALMAR_MULT * calb, (cal, CALMAR_MULT * calb)),
              "conc<=C0": (m[t]["conc_max"] <= m[B_STAR]["conc_max"],
                           (m[t]["conc_max"], m[B_STAR]["conc_max"]))}
        return all(v[0] for v in ok.values()), ok

    out = {}
    log.info("")
    log.info("%-12s %5s %8s %7s %8s %7s %7s %6s | %-4s %-4s %-4s %-4s",
             "arm", "n", "equity", "CAGR", "ddPhut", "q*", "top1%", "conc%", "T1", "T2", "T3", "T4")
    for t in TAGS:
        t1 = tier1(t); t2 = tier2(t); t3 = tier3(t); t4 = tier4(t)
        f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "ref")
        cal = m[t]["cagr"] / abs(mtm[t]["dd_total"]) if mtm[t].get("dd_total") not in (0, None) else float("nan")
        log.info("%-12s %5d %8.0f %7.2f %8.2f %7.1f %7.2f %6.2f | %-4s %-4s %-4s %-4s",
                 t, m[t]["n"], m[t]["equity"], m[t]["cagr"], mtm[t]["dd_total"],
                 m[t]["q_star"] or float("nan"), m[t]["top1_pct"], m[t]["conc_max"],
                 f(t1), f(t2), f(t3), f(t4))
        out[t] = dict(n=m[t]["n"], equity=m[t]["equity"], cagr=m[t]["cagr"],
                      mtm_dd_total=mtm[t]["dd_total"], mtm_uw_days=mtm[t]["uw_total_days"],
                      mtm_dd_year=mtm[t]["dd_year"], qmin=m[t]["qmin"], q_star=m[t]["q_star"],
                      top1_pct=m[t]["top1_pct"], conc_max=m[t]["conc_max"],
                      neg_year=m[t]["neg_year"], rates=m[t]["rates"],
                      calmar_MTM=float(cal), ci=ci[t], t1=t1, t2=t2, t3=t3, t4=t4)

    # % giu lai cua C1 so C0
    if len(legs[B_STAR]):
        retain = dict(
            n_pct=100.0 * m[TAGS[1]]["n"] / m[B_STAR]["n"],
            calmar_pct=100.0 * out[TAGS[1]]["calmar_MTM"] / out[B_STAR]["calmar_MTM"],
            cagr_pct=100.0 * m[TAGS[1]]["cagr"] / m[B_STAR]["cagr"],
            equity_pct=100.0 * m[TAGS[1]]["equity"] / m[B_STAR]["equity"],
        )
        out["retain"] = retain
        log.info("RETAIN C1/C0: n=%.1f%% Calmar=%.1f%% CAGR=%.1f%% equity=%.1f%%",
                 retain["n_pct"], retain["calmar_pct"], retain["cagr_pct"], retain["equity_pct"])

    js = dict(prereg="docs/prereg/PREREG_R4_CADENCE.md", k_infl=K_INFL, inflate=INFL,
              bstar=B_STAR, calmar_mult=CALMAR_MULT, md5=md5, parity_c0_ok=parity_ok, metrics=out)
    with open(a.json, "w") as fh:
        json.dump(js, fh, indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)
    log.info("PARITY_C0=%s", parity_ok)


if __name__ == "__main__":
    main()
