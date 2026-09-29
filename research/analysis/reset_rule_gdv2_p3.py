#!/usr/bin/env python3
"""RESET_RULE_GDV2_P3 (TASK GDV2_P3) — @stress 4-tang + do ben P3 (G2 vs G0, base & stress).

Thuc thi DUNG docs/prereg/PREREG_GDV2_P3.md (chot TRUOC; commit 100c907) + §6 PREREG_GDV2_EVEN.
Khuon = reset_rule_gd92r4_p3.py (da chay cho D1), doi tag G2/G0.

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-30.

Phan 1 — 4 tang @stress (dung lai §9 tiers CUNG nhu driver @base reset_rule_gdv2_driver.py):
  TAGS = {gdv2-g0-stress, gdv2-g2-stress}; B_STAR = gdv2-g0-stress; cham "as-is".

Phan 2 — P3 (G2 vs G0) o CA base va stress:
  T1 episode jackknife bo top-1/3/5. "G2 khong te hon G0" tai k <=> sum_rem(G2,k)>0 VA
      calmar_rem(G2,k) >= calmar_rem(G0,k).
  T2 bootstrap cum episode 5000 rep seed 20260928, paired luoi khoi chung:
      CI95 dCalmar, dCAGR, dn, dSumPnL. "CI chenh Calmar khong am ngoai 0" <=> lo(dCalmar)>0.

Usage:
  python3 reset_rule_gdv2_p3.py [--skip-mtm] [--workers 4] \
      --json docs/result/gdv2_p3.json [--mtm-cache /tmp/gdv2_p3_mtm.json]
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

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gdv2p3")

KOUT = "/home/ubuntu/kaggle_sim/out"
CAP0 = 35000.0
K_INFL = 2
INFL = math.sqrt(2.0 * math.log(K_INFL))   # 1.1774
CALMAR_MULT = 0.90
NREP_BOOT = 5000
SEED_BOOT = 20260928

TAGS_STRESS = ["gdv2-g0-stress", "gdv2-g2-stress"]
B_STAR_STRESS = "gdv2-g0-stress"
PARITY_G0S_MD5 = "84402b57c2fa43b72f86a918e3e54e11"

# cap (G2 vs G0) o ca base va stress
PAIR = {"base": ("gdv2-g2", "gdv2-g0"),
        "stress": ("gdv2-g2-stress", "gdv2-g0-stress")}


# =============================================================== P3 helpers (khuon reset_rule_p3.py)
def build_episodes(d):
    """tra list[set(day)] — episode = ngay-vao lien tiep cach <=2 ngay trong."""
    days = pd.Series(d["ts"].dt.normalize().drop_duplicates().sort_values().to_numpy())
    vals = days.to_numpy()
    eps, cur = [], [vals[0]]
    for x in vals[1:]:
        if (x - cur[-1]) / np.timedelta64(1, "D") > 2:
            eps.append(cur)
            cur = [x]
        else:
            cur.append(x)
    eps.append(cur)
    return [set(e) for e in eps]


def _equity(d, mask, span_days):
    dd = d[mask]
    if len(dd) == 0:
        return CAP0, 0.0
    te = dd["te"].dt.normalize()
    g = dd.groupby(te)["pnl"].sum().sort_index()
    eq = CAP0 + g.cumsum()
    ddv = (eq / eq.cummax() - 1) * 100.0
    return float(eq.iloc[-1]), float(ddv.min())


def episode_jackknife(d, span_days):
    eps = build_episodes(d)
    day2ep = {}
    for i, e in enumerate(eps):
        for x in e:
            day2ep[x] = i
    leg_ep = np.array([day2ep.get(np.datetime64(x), -1) for x in d["ts"].dt.normalize().to_numpy()])
    ap = d["pnl"].to_numpy(float)
    ep_sum = np.array([ap[leg_ep == i].sum() for i in range(len(eps))])
    order = np.argsort(-ep_sum)
    tot = float(ap.sum())
    out = {"n_ep": len(eps), "sum_pnl": tot}
    for k in (1, 3, 5, 10):
        top = set(order[:k].tolist())
        m = ~np.isin(leg_ep, list(top))
        rem = float(ap[m].sum())
        eqf, mdd = _equity(d, m, span_days)
        cagr = ((eqf / CAP0) ** (1 / span_days) - 1) * 100 if span_days > 0 else float("nan")
        cal = cagr / abs(mdd) if mdd != 0 else float("nan")
        out["drop%d" % k] = dict(pct_top=float(100.0 * ep_sum[order[:k]].sum() / tot) if tot else float("nan"),
                                 sum_pnl_rem=rem, cagr_rem=float(cagr), maxdd_rem=mdd, calmar_rem=float(cal))
    return out


def _block_days(eps, d_end):
    starts = [min(e) for e in eps]
    out = []
    for i, s in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else np.datetime64(d_end) + np.timedelta64(1, "D")
        out.append(max(1, int((nxt - s) / np.timedelta64(1, "D"))))
    return np.array(out, float)


def _prep_pair(dr, db, d_end):
    both = pd.concat([dr[["ts"]], db[["ts"]]], ignore_index=True)
    eps = build_episodes(both)
    day2ep = {}
    for i, e in enumerate(eps):
        for x in e:
            day2ep[x] = i
    K = len(eps)
    blk_days = _block_days(eps, d_end)

    def prep(d):
        ld = d["ts"].dt.normalize().to_numpy()
        le = np.array([day2ep.get(np.datetime64(x), -1) for x in ld])
        ap = d["pnl"].to_numpy(float)
        return np.array([ap[le == i].sum() for i in range(K)]), \
            np.array([np.sum(le == i) for i in range(K)])   # n leg moi episode

    br, nr = prep(dr)
    bb, nb = prep(db)
    return br, bb, nr, nb, blk_days, K


def boot_pair(dr, db, d_end, nrep=NREP_BOOT, seed=SEED_BOOT):
    """paired tren luoi khoi CHUNG -> dict mang dCalmar, dCagr, dn, dSum (G2 - G0)."""
    br, bb, nr, nb, blk_days, K = _prep_pair(dr, db, d_end)
    rng = np.random.default_rng(seed)
    dcal = np.empty(nrep)
    dcagr = np.empty(nrep)
    dn = np.empty(nrep)
    dsum = np.empty(nrep)
    for r in range(nrep):
        pick = rng.integers(0, K, size=K)
        ndays = float(blk_days[pick].sum())
        vals = []
        for b in (br, bb):
            p = b[pick]
            eq = CAP0 + np.cumsum(p)
            peak = np.maximum.accumulate(np.concatenate(([CAP0], eq)))
            ddv = (np.concatenate(([CAP0], eq)) / peak - 1) * 100.0
            mdd = float(ddv.min())
            s = float(p.sum())
            cagr = (((CAP0 + s) / CAP0) ** (365.25 / ndays) - 1) if ndays > 0 and (CAP0 + s) > 0 else -1.0
            vals += [((cagr * 100) / abs(mdd) if mdd != 0 else np.nan), cagr * 100, s]
        dcal[r] = vals[0] - vals[3]
        dcagr[r] = vals[1] - vals[4]
        dsum[r] = vals[2] - vals[5]
        dn[r] = float(nr[pick].sum() - nb[pick].sum())
    return dict(cal=dcal, cagr=dcagr, n=dn, sum=dsum, K=K)


def boot_one(d, d_end, nrep=NREP_BOOT, seed=SEED_BOOT):
    eps = build_episodes(d)
    day2ep = {}
    for i, e in enumerate(eps):
        for x in e:
            day2ep[x] = i
    leg_day = d["ts"].dt.normalize().to_numpy()
    leg_ep = np.array([day2ep.get(np.datetime64(x), -1) for x in leg_day])
    ap = d["pnl"].to_numpy(float)
    K = len(eps)
    bk_days = _block_days(eps, d_end)
    bpnl = np.array([ap[leg_ep == i].sum() for i in range(K)])
    rng = np.random.default_rng(seed)
    sums = np.empty(nrep)
    cagrs = np.empty(nrep)
    cals = np.empty(nrep)
    for r in range(nrep):
        pick = rng.integers(0, K, size=K)
        p = bpnl[pick]
        eq = CAP0 + np.cumsum(p)
        peak = np.maximum.accumulate(np.concatenate(([CAP0], eq)))
        ddv = (np.concatenate(([CAP0], eq)) / peak - 1) * 100.0
        mdd = float(ddv.min())
        s = float(p.sum())
        ndays = float(bk_days[pick].sum())
        cagr = ((CAP0 + s) / CAP0) ** (365.25 / ndays) - 1 if ndays > 0 and (CAP0 + s) > 0 else -1.0
        sums[r] = s
        cagrs[r] = cagr * 100
        cals[r] = (cagr * 100) / abs(mdd) if mdd != 0 else np.nan
    return dict(sum=sums, cagr=cagrs, calmar=cals)


def ci95(a, lo=2.5, hi=97.5):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return (float(np.percentile(a, lo)), float(np.percentile(a, hi))) if len(a) else (float("nan"), float("nan"))


# =============================================================== §9 tiers (same as @base driver)
def tier1(m, mtm):
    worst_y = min(mtm["dd_year"].values()) if mtm["dd_year"] else float("nan")
    ok = {"maxDD_phut_nam": (worst_y >= -40.0, worst_y),
          "UW": (mtm["uw_total_days"] <= 250.0, mtm["uw_total_days"]),
          "qmin": (m["qmin"] >= -20.0, m["qmin"]),
          "0_nam_am": (len(m["neg_year"]) == 0, m["neg_year"]),
          "conc": (m["conc_max"] <= 15.0, m["conc_max"])}
    return all(v[0] for v in ok.values()), ok


def tier2(m):
    ok = {"q*": (m["q_star"] is not None and m["q_star"] >= 15.0, m["q_star"]),
          "top1%": (m["top1_pct"] <= 25.0, m["top1_pct"])}
    return all(v[0] for v in ok.values()), ok


def tier3(m, mb):
    dw = m["rates"]["win%"] - mb["rates"]["win%"]
    dt = m["rates"]["TSloss%"] - mb["rates"]["TSloss%"]
    det = {"win%_d": (dw >= -2.0, dw), "TSloss%_d": (dt <= 2.5, dt)}
    return all(v[0] for v in det.values()), det


def tier4(m, mb, mtm, mtmb):
    cal = m["cagr"] / abs(mtm["dd_total"]) if mtm["dd_total"] not in (0, None) else float("nan")
    calb = mb["cagr"] / abs(mtmb["dd_total"]) if mtmb["dd_total"] not in (0, None) else float("nan")
    ok = {"Calmar>=0.90xG0": (cal >= CALMAR_MULT * calb, (cal, CALMAR_MULT * calb)),
          "conc<=G0": (m["conc_max"] <= mb["conc_max"], (m["conc_max"], mb["conc_max"]))}
    return all(v[0] for v in ok.values()), ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/gdv2_p3_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/gdv2_p3.json")
    a = ap.parse_args()

    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.K_INFL = K_INFL
    R.INFL = INFL

    all_tags = list(dict.fromkeys(TAGS_STRESS + [t for p in PAIR.values() for t in p]))
    legs, daily, md5 = {}, {}, {}
    log.info("GDV2_P3 — nap %d tag | k=%d inflate=%.4f | as-is", len(all_tags), K_INFL, INFL)
    for t in all_tags:
        legs[t] = R.load_legs(t)
        daily[t] = R.load_daily(t)
        md5[t] = R.md5_of(t)
        log.info("  %-20s n=%d equity=%.0f md5=%s", t, len(legs[t]), daily[t]["equity"].iloc[-1], md5[t][:8])

    # ---- parity G0s
    parity = md5[B_STAR_STRESS] == PARITY_G0S_MD5
    log.info("PARITY G0s: md5=%s (expected %s) -> %s", md5[B_STAR_STRESS], PARITY_G0S_MD5[:8],
             "PASS" if parity else "*** FAIL ***")

    # ---- core metrics (as-is)
    m = {t: R.core_metrics(t, legs[t], daily[t], "legacy") for t in all_tags}

    # ---- MTM phut (as-is)
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
        for t in all_tags:
            mtm[t] = raw[t]["legacy"]
    else:
        for t in all_tags:
            mtm[t] = {"dd_total": 0.0, "uw_total_days": 0.0, "dd_year": {}}

    # ---- §9 4 tang @stress
    log.info("")
    log.info("== 4 TANG @stress (G2s vs G0s) ==")
    log.info("%-20s %5s %8s %7s %8s %7s %7s %6s | %-4s %-4s %-4s %-4s",
             "arm", "n", "equity", "CAGR", "ddPhut", "q*", "top1%", "conc%", "T1", "T2", "T3", "T4")
    out = {}
    for t in TAGS_STRESS:
        mt = mtm[t]
        cal = m[t]["cagr"] / abs(mt["dd_total"]) if mt["dd_total"] not in (0, None) else float("nan")
        if t == B_STAR_STRESS:
            t1 = tier1(m[t], mt); t2 = tier2(m[t])
            t3 = (None, {"ref": True}); t4 = (None, {"ref": True})
        else:
            t1 = tier1(m[t], mt); t2 = tier2(m[t])
            t3 = tier3(m[t], m[B_STAR_STRESS])
            t4 = tier4(m[t], m[B_STAR_STRESS], mt, mtm[B_STAR_STRESS])
        f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "ref")
        log.info("%-20s %5d %8.0f %7.2f %8.2f %7.1f %7.2f %6.2f | %-4s %-4s %-4s %-4s",
                 t, m[t]["n"], m[t]["equity"], m[t]["cagr"], mt["dd_total"],
                 m[t]["q_star"] or float("nan"), m[t]["top1_pct"], m[t]["conc_max"],
                 f(t1), f(t2), f(t3), f(t4))
        out[t] = dict(n=m[t]["n"], equity=m[t]["equity"], cagr=m[t]["cagr"],
                      mtm_dd_total=mt["dd_total"], mtm_uw_days=mt["uw_total_days"],
                      mtm_dd_year=mt["dd_year"], qmin=m[t]["qmin"], q_star=m[t]["q_star"],
                      top1_pct=m[t]["top1_pct"], conc_max=m[t]["conc_max"],
                      neg_year=m[t]["neg_year"], rates=m[t]["rates"], calmar_MTM=float(cal),
                      t1=t1, t2=t2, t3=t3, t4=t4)

    # ---- CI tang 3 (paired block-72h) cho G2s vs G0s
    ci = R.ci_pair(legs["gdv2-g2-stress"], legs[B_STAR_STRESS])
    out["gdv2-g2-stress"]["ci"] = ci

    # ---- P3
    log.info("")
    log.info("== P3 — jackknife top-1/3/5 (G2 vs G0) ==")
    p3 = {}
    for cost, (gtag, g0tag) in PAIR.items():
        span_0 = (daily[g0tag].index[-1] - daily[g0tag].index[0]).days / 365.25
        span_2 = (daily[gtag].index[-1] - daily[gtag].index[0]).days / 365.25
        j2 = episode_jackknife(legs[gtag], span_2)
        j0 = episode_jackknife(legs[g0tag], span_0)
        log.info("  [%s] G2 ne=%d sum=%.0f | G0 ne=%d sum=%.0f", cost, j2["n_ep"], j2["sum_pnl"], j0["n_ep"], j0["sum_pnl"])
        for k in (1, 3, 5):
            ok_k = (j2["drop%d" % k]["sum_pnl_rem"] > 0
                    and j2["drop%d" % k]["calmar_rem"] >= j0["drop%d" % k]["calmar_rem"])
            log.info("    k=%d: G2 rem=%.0f cal=%.2f | G0 rem=%.0f cal=%.2f | G2>=G0 & rem>0 -> %s",
                     k, j2["drop%d" % k]["sum_pnl_rem"], j2["drop%d" % k]["calmar_rem"],
                     j0["drop%d" % k]["sum_pnl_rem"], j0["drop%d" % k]["calmar_rem"], ok_k)
        p3[cost] = dict(jack_g2=j2, jack_g0=j0,
                        jack_ok={str(k): bool(j2["drop%d" % k]["sum_pnl_rem"] > 0
                                             and j2["drop%d" % k]["calmar_rem"] >= j0["drop%d" % k]["calmar_rem"])
                                 for k in (1, 3, 5)})

    log.info("")
    log.info("== P3 — bootstrap cum episode (5000, seed 20260928) paired G2-G0 ==")
    for cost, (gtag, g0tag) in PAIR.items():
        de = daily[g0tag].index[-1]
        bp = boot_pair(legs[gtag], legs[g0tag], de)
        ccal = ci95(bp["cal"]); ccagr = ci95(bp["cagr"]); cnn = ci95(bp["n"]); csum = ci95(bp["sum"])
        p3[cost]["boot"] = dict(
            dCalmar=dict(mean=float(np.mean(bp["cal"])), ci=ccal, lo_gt0=bool(ccal[0] > 0), K=bp["K"]),
            dCAGR=dict(mean=float(np.mean(bp["cagr"])), ci=ccagr),
            dn=dict(mean=float(np.mean(bp["n"])), ci=cnn),
            dSumPnL=dict(mean=float(np.mean(bp["sum"])), ci=csum))
        log.info("  [%s] K=%d  dCalmar mean=%.2f CI[%.2f,%.2f] lo>0=%s | dCAGR mean=%.3f CI[%.3f,%.3f] | dn mean=%.1f CI[%.1f,%.1f] | dSum mean=%.0f CI[%.0f,%.0f]",
                 cost, bp["K"], p3[cost]["boot"]["dCalmar"]["mean"], ccal[0], ccal[1],
                 p3[cost]["boot"]["dCalmar"]["lo_gt0"], p3[cost]["boot"]["dCAGR"]["mean"],
                 ccagr[0], ccagr[1], p3[cost]["boot"]["dn"]["mean"], cnn[0], cnn[1],
                 p3[cost]["boot"]["dSumPnL"]["mean"], csum[0], csum[1])

    # ---- boot_one single-object (tham chieu)
    for cost, (gtag, g0tag) in PAIR.items():
        de2 = daily[gtag].index[-1]
        de0 = daily[g0tag].index[-1]
        b2 = boot_one(legs[gtag], de2)
        b0 = boot_one(legs[g0tag], de0)
        p3[cost]["boot_one_g2"] = dict(calmar_ci=ci95(b2["calmar"]), sum_ci=ci95(b2["sum"]), cagr_ci=ci95(b2["cagr"]))
        p3[cost]["boot_one_g0"] = dict(calmar_ci=ci95(b0["calmar"]), sum_ci=ci95(b0["sum"]), cagr_ci=ci95(b0["cagr"]))

    # ---- verdict theo §6
    g2s_pass4 = out["gdv2-g2-stress"]["t1"][0] and out["gdv2-g2-stress"]["t2"][0] \
        and out["gdv2-g2-stress"]["t3"][0] and out["gdv2-g2-stress"]["t4"][0]
    jack_all = all(all(p3[c]["jack_ok"].values()) for c in ("base", "stress"))
    cal_gt0 = all(p3[c]["boot"]["dCalmar"]["lo_gt0"] for c in ("base", "stress"))
    verdict = bool(g2s_pass4 and jack_all and cal_gt0)
    log.info("")
    log.info("VERDICT §6: (i) PASS4@stress=%s (base da PASS o RESULT_GDV2_EVEN) (ii) jackknife ok=%s (iii) CI dCalmar lo>0=%s -> %s",
             g2s_pass4, jack_all, cal_gt0,
             "G2 THAY R4" if verdict else "G2 ~ R4, KHONG THAY")

    js = dict(prereg="docs/prereg/PREREG_GDV2_P3.md", k_infl=K_INFL, inflate=INFL,
              bstar_stress=B_STAR_STRESS, parity_g0s=parity, parity_g0s_md5=PARITY_G0S_MD5,
              md5=md5, stress_4tier=out, p3=p3,
              verdict=dict(g2s_pass4_stress=g2s_pass4, jackknife_ok=jack_all,
                           ci_dcalmar_lo_gt0=cal_gt0, propose=verdict))
    with open(a.json, "w") as fh:
        json.dump(js, fh, indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)


if __name__ == "__main__":
    main()
