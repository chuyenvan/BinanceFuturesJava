#!/usr/bin/env python3
"""HOLDTODIE — cham 2 arm H0/H1 (tat TS 168h tren nen G2+FLAT3) theo LUAT 4 TANG §9.

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-31.
Dung lai ham reset_rule_score.py (load_legs/load_daily/core_metrics/ci_pair/run_mtm) — KHONG viet lai.
Cham AS-IS (artifact da chay phi base 0,112 %). k=1 (1 arm doi chieu) => INFL=1.0.
T4 (owner 09-29 §9.3): n la MUC TIEU CHINH (bao cao) · Calmar_MTM >= 0,90 x H0 · conc <= H0.

Usage: python3 holdtodie_driver.py [--json OUT] [--skip-mtm] [--workers 4]
"""
import argparse
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("holdtodie")

TAGS = ["htd-h0", "htd-h1"]
B_STAR = "htd-h0"
PARITY_MD5 = "650c386f0d0dfea334af9d55ca2f21d4"
K_INFL = 1
INFL = 1.0                      # k=1 => single comparison, khong hieu chinh da so sanh
CALMAR_MULT = 0.90
JAR_SHA_WANT = "7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a"


def yq_table(d):
    """theo NAM va QUY: n, sum_pnl, win% (theo thoi diem VAO lenh `ts`)."""
    out = {}
    for key, grp in [("Y", d["ts"].dt.year), ("Q", d["ts"].dt.to_period("Q").astype(str))]:
        tab = {}
        for k, g in d.groupby(grp):
            tab[str(k)] = dict(n=int(len(g)), sum_pnl=float(g["pnl"].sum()),
                               win=float(100.0 * (g["pnl"] > 0).mean()))
        out[key] = tab
    return out


def conc_hold(d):
    """so vi the dong thoi (max) + thoi gian giu TB (gio) + so dong thoi TB."""
    hold_h = ((d["te"] - d["ts"]).dt.total_seconds() / 3600.0)
    starts = d["ts"].astype("int64").to_numpy() / 1e9
    ends = d["te"].astype("int64").to_numpy() / 1e9
    t_ev = []
    for s0, e0 in zip(starts, ends):
        t_ev.append((s0, 1)); t_ev.append((e0, -1))
    t_ev.sort(key=lambda x: (x[0], -x[1]))
    mx, cur, prev, area = 0, 0, None, 0.0
    for t, dt in t_ev:
        if prev is not None:
            area += cur * (t - prev)
        cur += dt
        mx = max(mx, cur)
        prev = t
    span_s = ends.max() - starts.min()
    return dict(max_concurrent=int(mx), mean_hold_h=float(hold_h.mean()),
                median_hold_h=float(hold_h.median()),
                mean_concurrent=round(float(area / span_s), 3) if span_s > 0 else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/holdtodie_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/holdtodie.json")
    a = ap.parse_args()

    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.K_INFL = K_INFL
    R.INFL = INFL

    log.info("HOLDTODIE — cham %d arm §9 | k=%d INFL=%.2f | as-is (phi base trong artifact)", len(TAGS), K_INFL, INFL)
    legs, daily, md5 = {}, {}, {}
    for t in TAGS:
        legs[t] = R.load_legs(t)
        daily[t] = R.load_daily(t)
        md5[t] = R.md5_of(t)
        log.info("%-8s n=%4d equity=%.0f md5=%s", t, len(legs[t]),
                 daily[t]["equity"].iloc[-1], md5[t][:8])

    parity_ok = md5[B_STAR] == PARITY_MD5
    log.info("PARITY H0: md5=%s (want %s) -> %s", md5[B_STAR], PARITY_MD5, "PASS" if parity_ok else "*** FAIL ***")

    m = {t: R.core_metrics(t, legs[t], daily[t], "legacy") for t in TAGS}
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
            mtm[t] = raw[t]["legacy"]
        log.info("MTM H0: dd_total=%.2f UW=%.1f (ky vong ~ -17,7 / 87 theo FLAT3)",
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
        det = {"win%_d": ((r["win%"] - rb["win%"]) >= -2.0, r["win%"] - rb["win%"]),
               "TSloss%_d": ((r["TSloss%"] - rb["TSloss%"]) <= 2.5, r["TSloss%"] - rb["TSloss%"])}
        return all(v[0] for v in det.values()), det

    def tier4(t):
        if t == B_STAR:
            return None, {"ref": True}
        ok = {"Calmar>=0.90xH0": (calmar(t) >= CALMAR_MULT * calmar(B_STAR), (calmar(t), CALMAR_MULT * calmar(B_STAR))),
              "conc<=H0": (m[t]["conc_max"] <= m[B_STAR]["conc_max"], (m[t]["conc_max"], m[B_STAR]["conc_max"]))}
        return all(v[0] for v in ok.values()), ok

    out = {}
    log.info("")
    log.info("%-8s %5s %8s %7s %8s %7s %7s %6s %6s %7s | %-4s %-4s %-4s %-4s",
             "arm", "n", "equity", "CAGR", "ddPhut", "UW", "q*", "top1%", "conc%", "Calmar",
             "T1", "T2", "T3", "T4")
    for t in TAGS:
        t1, t2, t3, t4 = tier1(t), tier2(t), tier3(t), tier4(t)
        f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "ref")
        log.info("%-8s %5d %8.0f %7.2f %8.2f %7.1f %7.1f %6.2f %6.2f %7.3f | %-4s %-4s %-4s %-4s",
                 t, m[t]["n"], m[t]["equity"], m[t]["cagr"], mtm[t]["dd_total"], mtm[t]["uw_total_days"],
                 m[t]["q_star"] or float("nan"), m[t]["top1_pct"], m[t]["conc_max"], calmar(t),
                 f(t1), f(t2), f(t3), f(t4))
        out[t] = dict(n=m[t]["n"], equity=m[t]["equity"], cagr=m[t]["cagr"],
                      mtm_dd_total=mtm[t]["dd_total"], mtm_uw_days=mtm[t]["uw_total_days"],
                      mtm_dd_year=mtm[t]["dd_year"], qmin=m[t]["qmin"], q_star=m[t]["q_star"],
                      top1_pct=m[t]["top1_pct"], conc_max=m[t]["conc_max"],
                      neg_year=m[t]["neg_year"], rates=m[t]["rates"],
                      calmar_MTM=float(calmar(t)), md5=md5[t], ci=ci[t],
                      t1=t1, t2=t2, t3=t3, t4=t4, yq=yq_table(legs[t]), conc=conc_hold(legs[t]))

    h0, h1 = out[B_STAR], out[TAGS[1]]
    d = dict(dn=h1["n"] - h0["n"], dn_pct=100.0 * (h1["n"] - h0["n"]) / h0["n"],
             d_uw=h1["mtm_uw_days"] - h0["mtm_uw_days"], d_dd=h1["mtm_dd_total"] - h0["mtm_dd_total"],
             d_win=h1["rates"]["win%"] - h0["rates"]["win%"],
             d_tsloss=h1["rates"]["TSloss%"] - h0["rates"]["TSloss%"],
             d_equity=h1["equity"] - h0["equity"], d_cagr=h1["cagr"] - h0["cagr"])
    out["delta"] = d
    log.info("")
    log.info("DELTA H1-H0: dn=%+d (%+.2f%%) dEquity=%+.0f dCAGR=%+.2fpp dUW=%+.1fd dddPhut=%+.2f dWin=%+.2fpp dTSloss=%+.2fpp",
             d["dn"], d["dn_pct"], d["d_equity"], d["d_cagr"], d["d_uw"], d["d_dd"], d["d_win"], d["d_tsloss"])
    log.info("CONC/HOLD: H0 max_concur=%s mean_hold=%.1fh | H1 max_concur=%s mean_hold=%.1fh",
             h0["conc"]["max_concurrent"], h0["conc"]["mean_hold_h"],
             h1["conc"]["max_concurrent"], h1["conc"]["mean_hold_h"])

    js = dict(prereg="docs/prereg/PREREG_HOLDTODIE.md", k_infl=K_INFL, inflate=INFL,
              calmar_mult=CALMAR_MULT, bstar=B_STAR, parity_md5=PARITY_MD5, parity_ok=parity_ok,
              jar_sha_want=JAR_SHA_WANT, md5=md5, metrics=out)
    json.dump(js, open(a.json, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s | PARITY_H0=%s", a.json, parity_ok)


if __name__ == "__main__":
    main()
