#!/usr/bin/env python3
"""RESET_RULE_CRASHPEN — chấm R4/G2 với phạt "leg sập" theo LUẬT 4 TẦNG §9 + bảng năm.

Docs: docs/prereg/PREREG_CRASH_PENALTY.md (chốt TRƯỚC khi chạy sim).
THUẦN PYTHON OFFLINE. KHÔNG Java/sim. DEV <= 2025-12-30.
Dùng lại reset_rule_score.py (load_legs/load_daily/core_metrics/ci_pair/run_mtm/md5_of) — KHÔNG viết lại thuật toán.

4 tầng §9 giống reset_rule_gdv2_driver (baseline = R4 gốc = cp-r4-parity):
  T1 MTM phút/UW/qmin/0-năm-âm/conc · T2 q*/top1% · T3 win%/TSloss% vs R4 ·
  T4 Calmar_MTM >= 0.90*R4 + conc <= R4 (n là mục tiêu chính).
BẢNG NĂM (mới): n (legs vào/năm) · ROI % (return equity/năm) · TSloss % (SL rate/năm) · maxDD % (MTM phút/năm).
SỐ LEG BỊ PHẠT/NĂM: parse log `[CRASH-PENALTY] SUMMARY … byYear=…`.

Usage: python3 reset_rule_crashpen_driver.py [--json OUT] [--report OUT] [--skip-mtm] [--workers 4]
"""
import argparse
import json
import logging
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("crashpen")

KOUT = "/home/ubuntu/kaggle_sim/out"
TAGS = ["cp-r4-parity", "cp-g2-parity",
        "cp-r4-p069", "cp-r4-p150", "cp-g2-p069", "cp-g2-p150"]
B_STAR = "cp-r4-parity"
K_INFL = 4
INFL = math.sqrt(2.0 * math.log(K_INFL))   # 1.6651
CALMAR_MULT = 0.90

RX_CRASHPEN_SUM = re.compile(
    r"\[CRASH-PENALTY\] SUMMARY penalty=(\S+) total=(\d+) byYear=\{(.*)\}")
RX_BYYEAR = re.compile(r"(\d{4})=(\d+)")


def parse_crashpen(tag):
    """Parse [CRASH-PENALTY] SUMMARY tu sim.out -> (penalty, total, {year:int})."""
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    penalty, total, byyear = None, None, {}
    with open(p, errors="ignore") as fh:
        for line in fh:
            m = RX_CRASHPEN_SUM.search(line)
            if m:
                penalty = float(m.group(1))
                total = int(m.group(2))
                byyear = {int(y): int(c) for y, c in RX_BYYEAR.findall(m.group(3))}
    return penalty, total, byyear


def year_tsloss(d):
    """% leg (theo năm VÀO) kết thúc STOP_LOSS_DONE."""
    out = {}
    for y, g in d.groupby(d["ts"].dt.year):
        n = len(g)
        sl = int((g["status"] == "STOP_LOSS_DONE").sum())
        out[int(y)] = (float(100.0 * sl / n) if n else float("nan"), int(n))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/crashpen_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/crash_penalty.json")
    ap.add_argument("--report", default="/home/ubuntu/crash_penalty_report.txt")
    a = ap.parse_args()

    # as-is: phí base + penalty đã nằm TRONG artifact (qua entry price) — KHÔNG điều chỉnh chi phí.
    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}

    legs, daily, md5 = {}, {}, {}
    log.info("CRASHPEN — chấm %d arm §9 + bảng năm | k=%d inflate=%.4f | as-is",
             len(TAGS), K_INFL, INFL)
    for t in TAGS:
        legs[t] = R.load_legs(t)
        daily[t] = R.load_daily(t)
        md5[t] = R.md5_of(t)
        log.info("%-14s n=%d equity=%.0f md5=%s", t, len(legs[t]),
                 daily[t]["equity"].iloc[-1], md5[t][:8])

    parity_r4 = md5[B_STAR] == "06fd6e9aa9c916945b2cf12310b337ff"
    parity_g2 = md5["cp-g2-parity"] == "853aaa086be7d2d811162879df0653f6"
    log.info("PARITY R4: md5=%s (expect 06fd6e9a…) -> %s",
             md5[B_STAR], "PASS" if parity_r4 else "*** FAIL ***")
    log.info("PARITY G2: md5=%s (expect 853aaa…) -> %s",
             md5["cp-g2-parity"], "PASS" if parity_g2 else "*** FAIL ***")

    # số leg bị phạt/năm từ log Java
    cp = {t: parse_crashpen(t) for t in TAGS}
    for t in TAGS:
        p, tot, byy = cp[t]
        if p is not None:
            log.info("%-14s CRASH-PENALTY penalty=%s total=%s byYear=%s", t, p, tot, byy)

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
        log.info("TU KIEM MTM R4: dd_total=%.2f (P2 -16.42) | UW=%.1f (P2 164.7)",
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
        cal = m[t]["cagr"] / abs(mtm[t]["dd_total"]) if mtm[t].get("dd_total") not in (0, None) else float("nan")
        calb = m[B_STAR]["cagr"] / abs(mtm[B_STAR]["dd_total"])
        ok = {"Calmar>=0.90xR4": (cal >= CALMAR_MULT * calb, (cal, CALMAR_MULT * calb)),
              "conc<=R4": (m[t]["conc_max"] <= m[B_STAR]["conc_max"], (m[t]["conc_max"], m[B_STAR]["conc_max"]))}
        return all(v[0] for v in ok.values()), ok

    out = {}
    log.info("")
    log.info("%-14s %5s %8s %7s %8s %7s %7s %6s | %-4s %-4s %-4s %-4s",
             "arm", "n", "equity", "CAGR", "ddPhut", "q*", "top1%", "conc%", "T1", "T2", "T3", "T4")
    yt = {}
    for t in TAGS:
        t1 = tier1(t); t2 = tier2(t); t3 = tier3(t); t4 = tier4(t)
        f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "ref")
        cal = m[t]["cagr"] / abs(mtm[t]["dd_total"]) if mtm[t].get("dd_total") not in (0, None) else float("nan")
        log.info("%-14s %5d %8.0f %7.2f %8.2f %7.1f %7.2f %6.2f | %-4s %-4s %-4s %-4s",
                 t, m[t]["n"], m[t]["equity"], m[t]["cagr"], mtm[t]["dd_total"],
                 m[t]["q_star"] or float("nan"), m[t]["top1_pct"], m[t]["conc_max"],
                 f(t1), f(t2), f(t3), f(t4))
        yt[t] = year_tsloss(legs[t])
        out[t] = dict(n=m[t]["n"], equity=m[t]["equity"], cagr=m[t]["cagr"],
                      mtm_dd_total=mtm[t]["dd_total"], mtm_uw_days=mtm[t]["uw_total_days"],
                      mtm_dd_year=mtm[t]["dd_year"], qmin=m[t]["qmin"], q_star=m[t]["q_star"],
                      top1_pct=m[t]["top1_pct"], conc_max=m[t]["conc_max"], neg_year=m[t]["neg_year"],
                      rates=m[t]["rates"], calmar_MTM=float(cal), ci=ci[t],
                      yr_roi=m[t]["yr"], year_n={int(y): v[1] for y, v in yt[t].items()},
                      year_tsloss={int(y): v[0] for y, v in yt[t].items()},
                      crash_penalty=dict(penalty=cp[t][0], total=cp[t][1], by_year=cp[t][2]),
                      t1=t1, t2=t2, t3=t3, t4=t4)

    js = dict(prereg="docs/prereg/PREREG_CRASH_PENALTY.md", k_infl=K_INFL, inflate=INFL,
              bstar=B_STAR, calmar_mult=CALMAR_MULT, md5=md5,
              parity_r4_ok=parity_r4, parity_g2_ok=parity_g2,
              metrics=out)
    with open(a.json, "w") as fh:
        json.dump(js, fh, indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)
    log.info("PARITY_R4=%s PARITY_G2=%s", parity_r4, parity_g2)


if __name__ == "__main__":
    main()
