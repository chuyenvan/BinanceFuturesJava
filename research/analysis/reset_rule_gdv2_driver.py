#!/usr/bin/env python3
"""RESET_RULE_GDV2 — cham G0/G1/G2 theo LUAT 4 TANG §9 + DO DEU (docs/prereg/PREREG_GDV2_EVEN.md).

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-30.
Dung lai ham reset_rule_score.py (load/core_metrics/ci_pair/run_mtm) — KHONG viet lai thuat toan.
4 tang §9 giong gd92r4_driver (T1 MTM phut/UW/qmin/0 nam am/conc · T2 q*/top1% · T3 win%/TSloss% vs G0 ·
T4 n la muc tieu chinh + Calmar_MTM>=0.90xG0 + conc<=G0).
DO DEU (moi): theo quy 2021Q3..2025Q4 — n quy (end-quarter), CV(n), min n, so quy n<40, do lech
ti le pass quy so rho (RMS). So ca G0 va D1 (GD92) de thay GDV2 deu hon that khong.

Usage: python3 reset_rule_gdv2_driver.py [--json OUT] [--report OUT] [--skip-mtm] [--workers 4]
"""
import argparse
import json
import logging
import math
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gdv2")

KOUT = "/home/ubuntu/kaggle_sim/out"
TAGS = ["gdv2-g0", "gdv2-g1", "gdv2-g2"]
B_STAR = "gdv2-g0"
K_INFL = 2
INFL = math.sqrt(2.0 * math.log(K_INFL))   # 1.1774
CALMAR_MULT = 0.90

D1_TAG = "gd92-r4-d1"     # GD92 W90 pct .92 scale 1.55 (doi chieu do deu)

RX_RHO = re.compile(r"GATE-RATIO\s+(\S+)\s+pct=(\S+)\s+days=(\d+)\s+seen=(\d+)\s+pass=(\d+)\s+rho=(\S+)")
RX_RHO_Q = re.compile(r"(\d{4}Q[1-4]):(\d+)/(\d+)")


def q_of(ts):
    return "%sQ%d" % (ts.strftime("%Y"), (ts.month - 1) // 3 + 1)


def quarterly_n(d):
    """n quy theo END-quarter (khớp qstat_r4.py). OrderedDict quarter -> n."""
    out = OrderedDict()
    for te in d["te"]:
        q = q_of(te)
        out[q] = out.get(q, 0) + 1
    return out


def gate_rho(tag):
    """Parse [GATE-RATIO] line tu sim.out -> (rho, dict quarter->(seen, pass))."""
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    rho = float("nan")
    qq = OrderedDict()
    with open(p, errors="ignore") as fh:
        for line in fh:
            if "GATE-RATIO" not in line or "pct=" not in line:
                continue
            m = RX_RHO.search(line)
            if m:
                rho = float(m.group(6))
            for mm in RX_RHO_Q.finditer(line):
                # log Java in "QUARTER:pass/seen" => group(2)=pass, group(3)=seen
                qq[mm.group(1)] = (int(mm.group(3)), int(mm.group(2)))  # (seen, pass)
    return rho, qq


def evenness(d, tag, rho, qq):
    qn = quarterly_n(d)
    ns = list(qn.values())
    n = len(ns)
    mean_n = float(sum(ns)) / n if n else float("nan")
    sd = math.sqrt(sum((x - mean_n) ** 2 for x in ns) / n) if n else float("nan")
    cv = sd / mean_n if mean_n else float("nan")
    min_n = min(ns) if ns else 0
    lt40 = sum(1 for x in ns if x < 40)
    # do lech ti le pass quy so rho (RMS) — chi cac quy co du lieu candidate
    devs = []
    for q, (seen, passed) in qq.items():
        if seen > 0:
            devs.append(passed / seen - rho)
    rms = math.sqrt(sum(x * x for x in devs) / len(devs)) if devs else float("nan")
    return dict(n=n, quarters=list(qn.keys()), n_quarter=list(ns),
                cv_n=cv, min_n=min_n, n_lt40=lt40, rho=rho,
                pass_rate_q={q: (p / s if s else None) for q, (s, p) in qq.items()},
                rms_dev_rho=rms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/gdv2_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/gdv2_even.json")
    ap.add_argument("--report", default="/home/ubuntu/gdv2_even_report.txt")
    a = ap.parse_args()

    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}

    legs, daily, md5 = {}, {}, {}
    log.info("GDV2 — cham %d arm §9 + DO DEU | k=%d inflate=%.4f | as-is (phi base trong artifact)",
             len(TAGS), K_INFL, INFL)
    for t in TAGS:
        legs[t] = R.load_legs(t)
        daily[t] = R.load_daily(t)
        md5[t] = R.md5_of(t)
        log.info("%-10s n=%d equity=%.0f md5=%s", t, len(legs[t]),
                 daily[t]["equity"].iloc[-1], md5[t][:8])

    parity_ok = md5[B_STAR] == "06fd6e9aa9c916945b2cf12310b337ff"
    log.info("PARITY G0: md5=%s (expected 06fd6e9a...) -> %s", md5[B_STAR],
             "PASS" if parity_ok else "*** FAIL ***")

    # rho + pass-rate per quarter
    rho, qq = {}, {}
    for t in TAGS:
        rho[t], qq[t] = gate_rho(t)
        log.info("%-10s rho=%.8f | %d quarter co data", t, rho[t], len(qq[t]))

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
        log.info("TU KIEM MTM G0(=R4): dd_total=%.2f (P2 -16.42) | UW=%.1f (P2 164.7)",
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
        ok = {"Calmar>=0.90xG0": (cal >= CALMAR_MULT * calb, (cal, CALMAR_MULT * calb)),
              "conc<=G0": (m[t]["conc_max"] <= m[B_STAR]["conc_max"], (m[t]["conc_max"], m[B_STAR]["conc_max"]))}
        return all(v[0] for v in ok.values()), ok

    out = {}
    log.info("")
    log.info("%-10s %5s %8s %7s %8s %7s %7s %6s | %-4s %-4s %-4s %-4s | CVn %6s min_n %5s n<40 %3s rmsRho",
             "arm", "n", "equity", "CAGR", "ddPhut", "q*", "top1%", "conc%", "T1", "T2", "T3", "T4",
             "CV%", "", "", "")
    ev = {}
    for t in TAGS:
        t1 = tier1(t); t2 = tier2(t); t3 = tier3(t); t4 = tier4(t)
        f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "ref")
        cal = m[t]["cagr"] / abs(mtm[t]["dd_total"]) if mtm[t].get("dd_total") not in (0, None) else float("nan")
        ev[t] = evenness(legs[t], t, rho[t], qq[t])
        log.info("%-10s %5d %8.0f %7.2f %8.2f %7.1f %7.2f %6.2f | %-4s %-4s %-4s %-4s | %5.2f %5d %4d %.6f",
                 t, m[t]["n"], m[t]["equity"], m[t]["cagr"], mtm[t]["dd_total"],
                 m[t]["q_star"] or float("nan"), m[t]["top1_pct"], m[t]["conc_max"],
                 f(t1), f(t2), f(t3), f(t4),
                 ev[t]["cv_n"] or float("nan"), ev[t]["min_n"], ev[t]["n_lt40"],
                 ev[t]["rms_dev_rho"] or 0.0)
        out[t] = dict(n=m[t]["n"], equity=m[t]["equity"], cagr=m[t]["cagr"],
                      mtm_dd_total=mtm[t]["dd_total"], mtm_uw_days=mtm[t]["uw_total_days"],
                      mtm_dd_year=mtm[t]["dd_year"], qmin=m[t]["qmin"], q_star=m[t]["q_star"],
                      top1_pct=m[t]["top1_pct"], conc_max=m[t]["conc_max"], neg_year=m[t]["neg_year"],
                      rates=m[t]["rates"], calmar_MTM=float(cal), ci=ci[t],
                      t1=t1, t2=t2, t3=t3, t4=t4, evenness=ev[t])

    # ---- doi chieu D1 (GD92) cho DO DEU
    d1 = None
    try:
        d1 = R.load_legs(D1_TAG)
        d1_ev = evenness(d1, D1_TAG, float("nan"), OrderedDict())
        log.info("D1 (GD92) n=%d CVn=%.2f min_n=%d n<40=%d", len(d1),
                 d1_ev["cv_n"], d1_ev["min_n"], d1_ev["n_lt40"])
    except Exception as e:  # noqa: BLE001
        log.warning("khong load duoc D1: %s", e)

    # candidate criteria (ung vien ⇔ PASS 4 tang AND CVn<G0 AND min_n>G0)
    cand = {}
    for t in TAGS:
        if t == B_STAR:
            continue
        tt1 = out[t]["t1"][0]; tt2 = out[t]["t2"][0]; tt3 = out[t]["t3"][0]; tt4 = out[t]["t4"][0]
        pass4 = (tt1 is not False and tt2 is not False and tt3 is not False and tt4 is not False)
        cv_ok = ev[t]["cv_n"] < ev[B_STAR]["cv_n"]
        mn_ok = ev[t]["min_n"] > ev[B_STAR]["min_n"]
        cand[t] = dict(pass4=pass4, cv_ok=cv_ok, mn_ok=mn_ok,
                       candidate=pass4 and cv_ok and mn_ok)
        log.info("CANDIDATE %-10s pass4=%s cv_ok=%s mn_ok=%s => %s",
                 t, pass4, cv_ok, mn_ok, "UNG VIEN" if cand[t]["candidate"] else "-")

    js = dict(prereg="docs/prereg/PREREG_GDV2_EVEN.md", k_infl=K_INFL, inflate=INFL,
              bstar=B_STAR, calmar_mult=CALMAR_MULT, md5=md5, parity_g0_ok=parity_ok,
              rho={t: rho[t] for t in TAGS}, metrics=out,
              d1=dict(n=int(len(d1)) if d1 is not None else None,
                      evenness=d1_ev if d1 is not None else None),
              candidates=cand)
    with open(a.json, "w") as fh:
        json.dump(js, fh, indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)
    log.info("PARITY_G0=%s", parity_ok)


if __name__ == "__main__":
    main()
