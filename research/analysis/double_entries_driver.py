#!/usr/bin/env python3
"""DOUBLE_ENTRIES — cham 6 arm P1..P6 (K x size tren nen G2+FLAT3) theo LUAT 4 TANG §9.

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-31.
Dung lai ham reset_rule_score.py (load_legs/load_daily/core_metrics/ci_pair/run_mtm) — KHONG viet lai.
Cham AS-IS (artifact da chay phi base 0,112 % => khong hieu chinh lai).
T4 theo owner 09-29 (§9.3): n la MUC TIEU CHINH · Calmar_MTM >= 0,90 x P1 · conc <= P1.
k = 5 (so arm doi chieu vs baseline) => inflate = sqrt(2 ln 5).

Usage: python3 double_entries_driver.py [--json OUT] [--skip-mtm] [--workers 4]
"""
import argparse
import json
import logging
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("double_entries")

TAGS = ["de-p1", "de-p2", "de-p3", "de-p4", "de-p5", "de-p6"]
B_STAR = "de-p1"
PARITY_MD5 = "650c386f0d0dfea334af9d55ca2f21d4"
K_INFL = 5
INFL = math.sqrt(2.0 * math.log(K_INFL))     # 1.79407
CALMAR_MULT = 0.90
CALMAR_BRIEF = 1.900                          # so brief (de doi chieu)
KNOB = {"de-p1": (16, 0.015), "de-p2": (24, 0.015), "de-p3": (32, 0.015),
        "de-p4": (24, 0.010), "de-p5": (32, 0.0075), "de-p6": (16, 0.010)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/double_entries_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/double_entries.json")
    a = ap.parse_args()

    # as-is: moi muc phi = LEGACY => adj_pnl/daily_adj = 0 (artifact da chay phi base)
    R.COSTS = {"base": R.LEGACY}
    R.COST_LEVELS = {"base": R.LEGACY}
    R.MTM_COSTS = {"base": R.LEGACY}
    R.K_INFL = K_INFL
    R.INFL = INFL

    log.info("DOUBLE_ENTRIES — %d arm §9 | k=%d inflate=%.5f | as-is (phi base trong artifact)", len(TAGS), K_INFL, INFL)
    legs, daily, md5 = {}, {}, {}
    for t in TAGS:
        legs[t] = R.load_legs(t)
        daily[t] = R.load_daily(t)
        md5[t] = R.md5_of(t)
        log.info("%-7s K=%-2d F=%-6s n=%4d equity=%.0f md5=%s", t, *KNOB[t], len(legs[t]),
                 daily[t]["equity"].iloc[-1], md5[t][:8])

    parity_ok = md5[B_STAR] == PARITY_MD5
    log.info("PARITY P1: md5=%s (want %s) -> %s", md5[B_STAR], PARITY_MD5, "PASS" if parity_ok else "*** FAIL ***")

    m = {t: R.core_metrics(t, legs[t], daily[t], "base") for t in TAGS}
    ci = {}
    for t in TAGS:
        ci[t] = ({k: dict(obs=0.0, lo=0.0, hi=0.0, worse_sig=False) for k in R.RATE_KEYS}
                 if t == B_STAR else R.ci_pair(legs[t], legs[B_STAR]))

    mtm = {}
    if not a.skip_mtm:
        if a.mtm_cache and os.path.exists(a.mtm_cache):
            raw = json.load(open(a.mtm_cache))
            log.info("  [cache] %s", a.mtm_cache)
        else:
            raw = R.run_mtm(legs, workers=a.workers, chunk=30)
            if a.mtm_cache:
                json.dump(raw, open(a.mtm_cache, "w"))
        for t in TAGS:
            mtm[t] = raw[t]["base"]
        log.info("MTM P1: dd_total=%.2f UW=%.1f (ky vong ~ -17,7 / 87 theo FLAT3)",
                 mtm[B_STAR]["dd_total"], mtm[B_STAR]["uw_total_days"])

    def calmar(t):
        dd = mtm[t]["dd_total"]
        return m[t]["cagr"] / abs(dd) if dd not in (0, None) else float("nan")

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
        det = {"win%_d": (dw >= -2.0, dw), "TSloss%_d": (dt <= 2.5, dt),
               "mP|SM_not_worse": (not ci[t]["mP|SM"]["worse_sig"], ci[t]["mP|SM"]["obs"]),
               "mP|SL_not_worse": (not ci[t]["mP|SL"]["worse_sig"], ci[t]["mP|SL"]["obs"])}
        return all(v[0] for v in det.values()), det

    def tier4(t):
        if t == B_STAR:
            return None, {"ref": True}
        cal, calb = calmar(t), calmar(B_STAR)
        ok = {"Calmar>=0.90xP1": (cal >= CALMAR_MULT * calb, (cal, CALMAR_MULT * calb)),
              "Calmar>=1.710(brief)": (cal >= CALMAR_MULT * CALMAR_BRIEF, cal),
              "conc<=P1": (m[t]["conc_max"] <= m[B_STAR]["conc_max"], (m[t]["conc_max"], m[B_STAR]["conc_max"]))}
        return all(v[0] for v in ok.values()), ok

    out = {}
    log.info("")
    log.info("%-6s %3s %5s %4s %8s %7s %7s %7s %6s %6s %7s | %-4s %-4s %-4s %-4s",
             "arm", "K", "F", "n", "equity", "CAGR", "ddPhut", "q*", "top1%", "conc%", "Calmar",
             "T1", "T2", "T3", "T4")
    for t in TAGS:
        t1, t2, t3, t4 = tier1(t), tier2(t), tier3(t), tier4(t)
        f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "ref")
        cal = calmar(t)
        log.info("%-6s %3d %5.3f %4d %8.0f %7.2f %7.2f %7.1f %6.2f %6.2f %7.3f | %-4s %-4s %-4s %-4s",
                 t, *KNOB[t], m[t]["n"], m[t]["equity"], m[t]["cagr"], mtm[t]["dd_total"],
                 m[t]["q_star"] or float("nan"), m[t]["top1_pct"], m[t]["conc_max"], cal,
                 f(t1), f(t2), f(t3), f(t4))
        out[t] = dict(k=KNOB[t][0], f_base=KNOB[t][1], n=m[t]["n"], equity=m[t]["equity"],
                      cagr=m[t]["cagr"], dd_daily=m[t]["maxdd_daily"],
                      mtm_dd_total=mtm[t]["dd_total"], mtm_uw_days=mtm[t]["uw_total_days"],
                      mtm_dd_year=mtm[t]["dd_year"], qmin=m[t]["qmin"], q_star=m[t]["q_star"],
                      top1_pct=m[t]["top1_pct"], conc_max=m[t]["conc_max"],
                      gross_max=m[t]["gross_max"], neg_year=m[t]["neg_year"],
                      rates=m[t]["rates"], calmar_MTM=float(cal), md5=md5[t],
                      ci=ci[t], t1=t1, t2=t2, t3=t3, t4=t4)

    base_n = m[B_STAR]["n"]
    log.info("")
    log.info("Q1: muc tieu n >= 2x P1 = %d", 2 * base_n)
    for t in TAGS:
        log.info("    %-6s n=%4d  = %.2fx P1  %s", t, m[t]["n"], m[t]["n"] / base_n,
                 "DAT 2x" if m[t]["n"] >= 2 * base_n else "")
    log.info("Q3: T3 delta vs P1 (win%%/TSloss%%) + K:")
    for t in TAGS:
        r, rb = m[t]["rates"], m[B_STAR]["rates"]
        log.info("    %-6s K=%-2d n=%4d win%%=%6.2f (d %+5.2f) TSloss%%=%6.2f (d %+5.2f) q*=%.1f top1=%.2f",
                 t, KNOB[t][0], m[t]["n"], r["win%"], r["win%"] - rb["win%"],
                 r["TSloss%"], r["TSloss%"] - rb["TSloss%"], m[t]["q_star"] or float("nan"), m[t]["top1_pct"])

    js = dict(prereg="docs/prereg/PREREG_DOUBLE_ENTRIES.md", k_infl=K_INFL, inflate=INFL,
              calmar_mult=CALMAR_MULT, bstar=B_STAR, parity_md5=PARITY_MD5, parity_ok=parity_ok,
              md5=md5, target_2x=2 * base_n, metrics=out)
    json.dump(js, open(a.json, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s | PARITY_P1=%s", a.json, parity_ok)


if __name__ == "__main__":
    main()
