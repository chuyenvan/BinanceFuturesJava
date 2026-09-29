#!/usr/bin/env python3
"""RESET_RULE_GD92_R4 — cham D0/D1/D2 theo LUAT 4 TANG §9 (RISK_APPETITE, owner 09-29).

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-30.
Dung lai ham cua reset_rule_score.py (load/core_metrics/ci_pair/run_mtm) — KHONG viet lai thuat toan.
Khac biet vs tool CUNG:
  - T1 bo tran gross<=70 (0/20 bind) — giu MTM phut / UW / qmin / 0 nam am / conc 15.
  - T2 bo "bo top-3 episode" — giu q*>=15 + top-1%<=25.
  - T3 bo mP|SM/mP|SL (CI qua rong) — giu win%>=-2.0pp & TSloss%<=+2.5pp (diem, so D0).
  - T4 MOI (uu tien SO LENH): n la muc tieu chinh; Calmar_MTM >= 0.90 x D0; conc <= D0.
Artifact D0/D1/D2 da chay o phi base (0.1116%/vong) => cham "as-is" (cost=legacy = khong hieu chinh pnl).

Usage: python3 reset_rule_gd92r4_driver.py [--json OUT] [--report OUT] [--skip-mtm]
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
log = logging.getLogger("gd92r4")

KOUT = "/home/ubuntu/kaggle_sim/out"
TAGS = ["gd92-r4-d0", "gd92-r4-d1", "gd92-r4-d2"]
B_STAR = "gd92-r4-d0"
K_INFL = 2
INFL = math.sqrt(2.0 * math.log(K_INFL))   # 1.1774

CALMAR_MULT = 0.90          # T4 moi: Calmar_MTM >= 0.90 x D0
CONC_LE = True              # T4: conc <= D0


def tagdir(tag):
    return os.path.join(KOUT, tag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/gd92r4_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/gd92_r4.json")
    ap.add_argument("--report", default="/home/ubuntu/gd92_r4_report.txt")
    a = ap.parse_args()

    # chuyen doi tuong sang as-is (cost legacy = khong hieu chinh)
    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}

    legs, daily, md5 = {}, {}, {}
    log.info("GD92_R4 — cham %d arm theo §9 | k=%d inflate=%.4f | as-is (phi base trong artifact)",
             len(TAGS), K_INFL, INFL)
    for t in TAGS:
        legs[t] = R.load_legs(t)
        daily[t] = R.load_daily(t)
        md5[t] = R.md5_of(t)
        log.info("%-14s n=%d equity=%.0f md5=%s", t, len(legs[t]),
                 daily[t]["equity"].iloc[-1], md5[t][:8])

    # parity D0
    parity_ok = md5[B_STAR] == "06fd6e9aa9c916945b2cf12310b337ff"
    log.info("PARITY D0: md5=%s (expected 06fd6e9a...) -> %s", md5[B_STAR],
             "PASS" if parity_ok else "*** FAIL ***")

    # core metrics (as-is)
    m = {t: R.core_metrics(t, legs[t], daily[t], "legacy") for t in TAGS}

    # CI tang 3 (paired block-72h, profit %)
    R.K_INFL = K_INFL
    R.INFL = INFL
    ci = {}
    for t in TAGS:
        if t == B_STAR:
            ci[t] = {k: dict(obs=0.0, lo=0.0, hi=0.0, worse_sig=False) for k in R.RATE_KEYS}
        else:
            ci[t] = R.ci_pair(legs[t], legs[B_STAR])

    # MTM phut
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
            mtm[t] = raw[t]["legacy"]    # as-is
        # tu kiem D0 = R4: mtm_dd_total ~ -16.42 (P2)
        log.info("TU KIEM MTM D0(=R4): dd_total=%.2f (P2 -16.42) | UW=%.1f ngay (P2 164.7)",
                 mtm[B_STAR]["dd_total"], mtm[B_STAR]["uw_total_days"])

    # ---- §9 tiers
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
        ok = {"Calmar>=0.90xD0": (cal >= CALMAR_MULT * calb, (cal, CALMAR_MULT * calb)),
              "conc<=D0": (m[t]["conc_max"] <= m[B_STAR]["conc_max"],
                           (m[t]["conc_max"], m[B_STAR]["conc_max"]))}
        return all(v[0] for v in ok.values()), ok

    out = {}
    log.info("")
    log.info("%-14s %5s %8s %7s %8s %7s %7s %6s | %-4s %-4s %-4s %-4s",
             "arm", "n", "equity", "CAGR", "ddPhut", "q*", "top1%", "conc%", "T1", "T2", "T3", "T4")
    for t in TAGS:
        t1 = tier1(t); t2 = tier2(t); t3 = tier3(t); t4 = tier4(t)
        f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "ref")
        cal = m[t]["cagr"] / abs(mtm[t]["dd_total"]) if mtm[t].get("dd_total") not in (0, None) else float("nan")
        log.info("%-14s %5d %8.0f %7.2f %8.2f %7.1f %7.2f %6.2f | %-4s %-4s %-4s %-4s",
                 t, m[t]["n"], m[t]["equity"], m[t]["cagr"], mtm[t]["dd_total"],
                 m[t]["q_star"] or float("nan"), m[t]["top1_pct"], m[t]["conc_max"],
                 f(t1), f(t2), f(t3), f(t4))
        out[t] = dict(n=m[t]["n"], equity=m[t]["equity"], cagr=m[t]["cagr"],
                      mtm_dd_total=mtm[t]["dd_total"], mtm_uw_days=mtm[t]["uw_total_days"],
                      mtm_dd_year=mtm[t]["dd_year"], qmin=m[t]["qmin"], q_star=m[t]["q_star"],
                      top1_pct=m[t]["top1_pct"], conc_max=m[t]["conc_max"],
                      neg_year=m[t]["neg_year"], rates=m[t]["rates"],
                      calmar_MTM=float(cal), ci=ci[t], t1=t1, t2=t2, t3=t3, t4=t4)

    js = dict(prereg="docs/prereg/PREREG_GD92_R4.md", k_infl=K_INFL, inflate=INFL,
              bstar=B_STAR, calmar_mult=CALMAR_MULT, md5=md5, parity_d0_ok=parity_ok, metrics=out)
    with open(a.json, "w") as fh:
        json.dump(js, fh, indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)
    log.info("PARITY_D0=%s", parity_ok)


if __name__ == "__main__":
    main()
