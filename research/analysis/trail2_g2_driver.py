#!/usr/bin/env python3
"""TRAIL_G2 — cham 5 arm theo docs/prereg/PREREG_TRAIL2_G2.md (chot TRUOC, md5 9f791a25c0d764d9cb78a5a3b4665002...).

THUAN PYTHON OFFLINE (research script). KHONG Java/sim. DEV <= 2025-12-30.
Tai dung reset_rule_score.py (load_legs/load_daily/core_metrics/run_mtm/md5_of) + tier1 §9 nhu reset_rule_gdv2_driver.py.
Cong parity: T0 md5 = 853aaa08..., n 2509, eq 131374 (sai => DUNG).
Bootstrap dCalmar (PRIMARY, theo pre-reg): PAIRED block-72h (luoi khoi CHUNG blk2 cua reset_rule_score), NREP 2000,
  seed 20260905, Calmar/CAGR/maxDD tinh tren equity dong (cum pnl theo thu tu khoi rut) nhu boot_pair cua GDV2_P3,
  CI95 percentile roi inflate quanh tam theo k=4 (1.6651).
Sensitivity: boot_pair (episode-cluster) cua reset_rule_gdv2_p3 voi NREP 2000, seed 20260905.
Usage: python3 trail_g2_driver.py [--json OUT] [--mtm-cache F] [--workers 4]
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
import reset_rule_gdv2_p3 as P  # noqa: E402  (boot_pair episode-cluster: sensitivity)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("trailg2")

ARMS = ["t0", "prop50", "prop30", "flat3", "flat5"]
TAGS = ["trail2-g2-" + a for a in ARMS]
B_STAR = "trail2-g2-t0"
PARITY_MD5, PARITY_N, PARITY_EQ = "853aaa086be7d2d811162879df0653f6", 2509, 131374
K_INFL = 4
INFL = math.sqrt(2.0 * math.log(K_INFL))   # 1.6651
NREP, SEED, CAP0 = 2000, 20260905, 35000.0


def block_boot(dr, db, nrep=NREP, seed=SEED):
    """PAIRED block-72h (luoi khoi chung, theo ts vao lenh, pnl dong) -> dCalmar/dCAGR/dSum (arm - T0)."""
    blocks = np.union1d(dr["blk2"].unique(), db["blk2"].unique())
    idx = {int(b): i for i, b in enumerate(blocks)}
    nb = len(blocks)

    def agg(d):
        bi = np.array([idx[int(b)] for b in d["blk2"].to_numpy()], dtype=np.int64)
        return np.bincount(bi, weights=d["pnl"].to_numpy(float), minlength=nb)

    br, bb = agg(dr), agg(db)
    rng = np.random.default_rng(seed)
    dcal, dcagr, dsum = np.empty(nrep), np.empty(nrep), np.empty(nrep)
    ndays = 3.0 * nb
    for r in range(nrep):
        pick = rng.integers(0, nb, size=nb)
        vals = []
        for b in (br, bb):
            p = b[pick]
            eq = np.concatenate(([CAP0], CAP0 + np.cumsum(p)))
            mdd = float(((eq / np.maximum.accumulate(eq) - 1) * 100.0).min())
            s = float(p.sum())
            cagr = ((CAP0 + s) / CAP0) ** (365.25 / ndays) - 1 if (CAP0 + s) > 0 else -1.0
            vals += [(cagr * 100) / abs(mdd) if mdd != 0 else np.nan, cagr * 100, s]
        dcal[r], dcagr[r], dsum[r] = vals[0] - vals[3], vals[1] - vals[4], vals[2] - vals[5]
    return dict(cal=dcal, cagr=dcagr, sum=dsum, K=nb)


def infl_ci(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    lo, hi = np.percentile(a, [2.5, 97.5])
    ctr = (lo + hi) / 2.0
    return (float(ctr - (ctr - lo) * INFL), float(ctr + (hi - ctr) * INFL)), (float(lo), float(hi))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mtm-cache", default="/tmp/trail2_g2_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/trail2_g2.json")
    a = ap.parse_args()

    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.K_INFL, R.INFL = K_INFL, INFL

    legs, daily, md5 = {}, {}, {}
    for t in TAGS:
        legs[t], daily[t], md5[t] = R.load_legs(t), R.load_daily(t), R.md5_of(t)
        log.info("%-14s n=%d equity=%.0f md5=%s", t, len(legs[t]), daily[t]["equity"].iloc[-1], md5[t][:8])
    n0, eq0 = len(legs[B_STAR]), float(daily[B_STAR]["equity"].iloc[-1])
    par = (md5[B_STAR] == PARITY_MD5 and n0 == PARITY_N and round(eq0) == PARITY_EQ)
    log.info("PARITY T0: md5=%s n=%d eq=%.0f -> %s", md5[B_STAR], n0, eq0, "PASS" if par else "*** FAIL ***")
    if not par:
        log.info("DUNG: parity T0 FAIL (profile/jar sai) — khong cham tiep")
        json.dump(dict(parity_ok=False, md5=md5), open(a.json + ".parity_fail", "w"), indent=1)
        sys.exit(3)

    m = {t: R.core_metrics(t, legs[t], daily[t], "legacy") for t in TAGS}
    if os.path.exists(a.mtm_cache):
        raw = json.load(open(a.mtm_cache))
        log.info("[cache] %s", a.mtm_cache)
    else:
        raw = R.run_mtm(legs, workers=a.workers, chunk=30)
        json.dump(raw, open(a.mtm_cache, "w"))
    mtm = {t: raw[t]["legacy"] for t in TAGS}

    def tier1(t):
        x = mtm[t]
        worst_y = min(x["dd_year"].values()) if x["dd_year"] else float("nan")
        ok = {"maxDD_phut_nam": (bool(worst_y >= -40.0), worst_y),
              "UW": (bool(x["uw_total_days"] <= 250.0), x["uw_total_days"]),
              "qmin": (bool(m[t]["qmin"] >= -20.0), m[t]["qmin"]),
              "0_nam_am": (len(m[t]["neg_year"]) == 0, m[t]["neg_year"]),
              "conc": (bool(m[t]["conc_max"] <= 15.0), m[t]["conc_max"])}
        return all(v[0] for v in ok.values()), ok

    cal = {t: m[t]["cagr"] / abs(mtm[t]["dd_total"]) if mtm[t].get("dd_total") else float("nan") for t in TAGS}
    out = {}
    for t in TAGS:
        t1 = tier1(t)
        rec = dict(n=m[t]["n"], equity=m[t]["equity"], cagr=m[t]["cagr"], mtm_dd_total=mtm[t]["dd_total"],
                   mtm_dd_year=mtm[t]["dd_year"], mtm_uw_days=mtm[t]["uw_total_days"], qmin=m[t]["qmin"],
                   qr=m[t]["qr"], yr=m[t]["yr"], neg_year=m[t]["neg_year"], conc_max=m[t]["conc_max"],
                   rates=m[t]["rates"], calmar_MTM=float(cal[t]), t1_pass=bool(t1[0]), t1=t1[1],
                   md5=md5[t], dn_vs_t0=m[t]["n"] - n0, dn_pct_vs_t0=100.0 * (m[t]["n"] - n0) / n0)
        if t != B_STAR:
            b = block_boot(legs[t], legs[B_STAR])
            ci, raw_ci = infl_ci(b["cal"])
            cia, _ = infl_ci(b["cagr"])
            e = P.boot_pair(legs[t], legs[B_STAR], "2025-12-30", nrep=NREP, seed=SEED)
            cie, _ = infl_ci(e["cal"])
            rec.update(dCalmar_MTM_obs=float(cal[t] - cal[B_STAR]),
                       dCAGR_obs=float(m[t]["cagr"] - m[B_STAR]["cagr"]),
                       boot_block72=dict(K=b["K"], dCalmar_mean=float(np.nanmean(b["cal"])), ci_infl=ci, ci_raw=raw_ci,
                                         contains0=bool(ci[0] <= 0 <= ci[1]), dCAGR_ci_infl=cia,
                                         dSum_mean=float(np.mean(b["sum"]))),
                       boot_episode_sens=dict(K=e["K"], dCalmar_mean=float(np.nanmean(e["cal"])), ci_infl=cie,
                                              contains0=bool(cie[0] <= 0 <= cie[1])))
            win = bool(t1[0] and cal[t] > cal[B_STAR] and not rec["boot_block72"]["contains0"])
            rec["verdict"] = "THANG G2" if win else "approx G2 / khong thang"
        out[t] = rec

    log.info("")
    log.info("%-14s %5s %8s %6s %8s %5s %7s %8s | T1 | dCalMTM  CI(infl, block72)   contains0 | episode-sens",
             "arm", "n", "eq", "CAGR", "ddMTM", "UW", "qmin", "CalMTM")
    for t in TAGS:
        r = out[t]
        s = ""
        if t != B_STAR:
            bb, ee = r["boot_block72"], r["boot_episode_sens"]
            s = "%+7.2f [%+7.2f,%+7.2f] %-5s | [%+.2f,%+.2f] %s => %s" % (
                r["dCalmar_MTM_obs"], bb["ci_infl"][0], bb["ci_infl"][1], bb["contains0"],
                ee["ci_infl"][0], ee["ci_infl"][1], ee["contains0"], r["verdict"])
        log.info("%-14s %5d %8.0f %6.2f %8.2f %5.0f %7.2f %8.3f | %s | %s", t, r["n"], r["equity"], r["cagr"],
                 r["mtm_dd_total"], r["mtm_uw_days"], r["qmin"], r["calmar_MTM"],
                 "PASS" if r["t1_pass"] else "FAIL", s)
    js = dict(prereg="docs/prereg/PREREG_TRAIL2_G2.md", prereg_md5="9f791a25c0d764d9cb78a5a3b4665002",
              k_infl=K_INFL, inflate=INFL, nrep=NREP, seed=SEED, bstar=B_STAR, parity_ok=True,
              md5=md5, metrics=out)
    json.dump(js, open(a.json, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)


if __name__ == "__main__":
    main()
