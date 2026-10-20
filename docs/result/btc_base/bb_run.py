#!/usr/bin/env python3
"""BTC_BASE buoc 2 (PREREG_BTC_BASE 3173e50d): chay DEV moi bien the x 8 seed, ap luat w*, roi HO W9 cho O(w*).
Usage: python3 bb_run.py out.json"""
import copy
import json
import logging
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/btc_base")
import bb_core as C  # noqa: E402  (bb_core import gvz_mtm truoc)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bbrun")
GRID = [0.2, 0.3, 0.4, 0.5]
PREREG = open("/home/ubuntu/claude_master/btc_base/prereg_commit.txt").read().strip()


def variants():
    v = {"B0": {"kind": "B0"}, "O0": {"kind": "O", "w": 0.0}}
    for w in GRID:
        t = "%.1f" % w
        v["S" + t] = {"kind": "S", "w": w}
        v["O" + t] = {"kind": "O", "w": w}
        v["OT" + t] = {"kind": "O", "w": w, "trend": True}
        v["OE" + t] = {"kind": "O", "w": w, "eth": True}
        v["OP" + t] = {"kind": "O", "w": w, "fund": True}
        v["OG" + t] = {"kind": "O", "w": w, "G": 1.5}
    return v


def scramble(P, cut, seed=1):
    rng = np.random.default_rng(seed)
    Q = copy.copy(P)
    for k in ("btc", "eth"):
        x = P[k].copy()
        n = len(x) - cut
        x[cut:] = x[cut] * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
        Q[k] = x
    db = P["daily_btc"].copy()
    m = (P["daily_btc_idx"] >= cut) & (P["daily_btc_idx"] < len(Q["btc"]))
    db[m] = Q["btc"][P["daily_btc_idx"][m]]
    Q["daily_btc"] = db
    return Q


def run_win(win, seeds_data, P, var_names, wbar=None):
    a0 = C.WIN[win]["a0"]
    res = {}
    V = variants()
    for s, S in seeds_data:
        rs = {}
        b0 = C.simulate(S, P, a0, V["B0"])
        rs["B0"] = C.metrics(b0, S, P, win)
        chk = {"V3_O0_maxabs": None, "V4_max_excess": 0.0, "eq_check_max": 0.0}
        o0 = C.simulate(S, P, a0, V["O0"])
        chk["V3_O0_maxabs"] = float(np.max(np.abs(o0["E"] - b0["E"])))
        bm = {}
        for vn in var_names:
            r = C.simulate(S, P, a0, V[vn])
            m = C.metrics(r, S, P, win)
            rs[vn] = m
            chk["V4_max_excess"] = max(chk["V4_max_excess"], r["ev"]["v4_max_excess"])
            chk["eq_check_max"] = max(chk["eq_check_max"], r["ev"]["eq_check_max"])
            if vn.startswith("O") and vn[1].isdigit():
                bm[vn[1:]] = m["b_mean"]
        for t, wb in bm.items():
            w_ = wb if wbar is None else wbar[str(s)][t]
            for nm_, spec in (("SP" + t, {"kind": "S", "w": w_}), ("SB" + t, {"kind": "S", "w": w_, "bh": True})):
                r = C.simulate(S, P, a0, spec)
                rs[nm_] = C.metrics(r, S, P, win)
                rs[nm_]["wbar"] = w_
                chk["eq_check_max"] = max(chk["eq_check_max"], r["ev"]["eq_check_max"])
        if win == "D":
            cut = C.umin("2023-06-01 00:00") - a0
            Q = scramble(P, cut)
            v5 = {}
            for vn in ("O0.5", "OT0.5", "OE0.5", "S0.5"):
                r1 = C.simulate(S, P, a0, V[vn])
                r2 = C.simulate(S, Q, a0, V[vn])
                v5[vn] = bool(np.array_equal(r1["qb"][:cut], r2["qb"][:cut]) and np.array_equal(r1["qe"][:cut], r2["qe"][:cut])
                              and np.array_equal(r1["cash"][:cut], r2["cash"][:cut])
                              and not np.array_equal(r1["qb"][cut:], r2["qb"][cut:]))
            chk["V5"] = v5
        chk["corr"] = C.corr_info(S, P, a0)
        rs["_chk"] = chk
        res[str(s)] = rs
        log.info("%s seed %s chk %s | B0 cagr22 %.2f ddR %.2f | O0.5 cagr22 %.2f ddR %.2f", win, s, chk, rs["B0"]["cagr22"],
                 rs["B0"]["dd_rule"], rs.get("O0.5", rs["B0"])["cagr22"], rs.get("O0.5", rs["B0"])["dd_rule"])
    return res


def agg(res, keys):
    out = {}
    vns = [k for k in res[str(C.SEEDS[0])] if not k.startswith("_")]
    for vn in vns:
        out[vn] = {}
        for k in keys:
            x = [res[str(s)][vn].get(k) for s in C.SEEDS]
            if any(v is None or isinstance(v, str) for v in x):
                continue
            x = np.array(x, float)
            out[vn][k] = [float(np.median(x)), float(np.min(x)), float(np.max(x)), float(np.mean(x))]
    return out


def main():
    outp = sys.argv[1]
    d = C.dev_legs()
    arrs = C.dev_closes(d)
    nmD = C.WIN["D"]["a1"] - C.WIN["D"]["a0"]
    PD = C.load_px("D")
    seedsD = []
    for s in C.SEEDS:
        x = d[d.seed == s].reset_index(drop=True)
        seedsD.append((s, C.Seed(x, [arrs[k] for k in x.key], C.CAP, nmD, lim=60)))
    del arrs
    allv = [k for k in variants() if k not in ("B0", "O0")]
    dev = run_win("D", seedsD, PD, allv)
    del seedsD
    chk = {s: dev[s]["_chk"] for s in dev}
    v_ok = dict(V3=all(c["V3_O0_maxabs"] <= 1e-6 for c in chk.values()),
                V4=all(c["V4_max_excess"] <= 1e-3 for c in chk.values()),
                V5=all(all(c["V5"].values()) for c in chk.values()),
                EQ=all(c["eq_check_max"] <= 1e-9 for c in chk.values()))
    log.info("DEV checks %s", v_ok)
    # luat w*
    rule = {}
    wstar = None
    for w in GRID:
        t = "%.1f" % w
        worst = min(dev[str(s)]["O" + t]["dd_rule"] for s in C.SEEDS)
        dc = [dev[str(s)]["O" + t]["cagr22"] - dev[str(s)]["B0"]["cagr22"] for s in C.SEEDS]
        ok = worst >= -40.0 and all(x > 0 for x in dc)
        rule[t] = dict(worst_dd_rule=worst, dcagr=dc, n_pos=int(sum(x > 0 for x in dc)), eligible=ok)
        if ok:
            wstar = t
    q2 = None
    if wstar is not None:
        o, sp, sw = "O" + wstar, "SP" + wstar, "S" + wstar
        beat = [dev[str(s)][o]["cagr22"] > dev[str(s)][sp]["cagr22"] for s in C.SEEDS]
        wo = min(dev[str(s)][o]["dd_rule"] for s in C.SEEDS)
        wsp = min(dev[str(s)][sp]["dd_rule"] for s in C.SEEDS)
        q2 = dict(n_beat_Sprime=int(sum(beat)), worst_dd_O=wo, worst_dd_Sprime=wsp,
                  dcagr_vs_Sprime=[dev[str(s)][o]["cagr22"] - dev[str(s)][sp]["cagr22"] for s in C.SEEDS],
                  dcagr_vs_S=[dev[str(s)][o]["cagr22"] - dev[str(s)][sw]["cagr22"] for s in C.SEEDS],
                  n_beat_S=int(sum(dev[str(s)][o]["cagr22"] > dev[str(s)][sw]["cagr22"] for s in C.SEEDS)),
                  wbar=[dev[str(s)][sp]["wbar"] for s in C.SEEDS])
        q2["fill_has_value"] = q2["n_beat_Sprime"] >= 7 and wo >= wsp - 2.0
    verdict_dev = "GO" if wstar is not None else "NO-GO"
    log.info("DEV rule %s wstar %s verdict %s q2 %s", rule, wstar, verdict_dev, q2)
    out = dict(prereg=PREREG, dev=dev, dev_checks=v_ok, rule=rule, wstar=wstar, verdict_dev=verdict_dev, q2=q2)
    keys = ["cagr22", "cagr_full", "dd_rule", "dd_hour_full", "dd_day_full", "dd_min_full", "dd_min_22", "calmar22",
            "calmar_rule", "worst_month", "util_mean", "n_mean", "b_mean", "gross_max", "pnl_total", "pnl_cb", "pnl_btc",
            "btc_sleeve_dd_twr_hour", "btc_sleeve_twr", "ev_ra_n", "ev_ra_usd", "ev_ra_pnl", "ev_ck_buy", "ev_ck_sell",
            "ev_fees", "ev_funding", "ev_trend_off_days", "ev_trend_switch", "pnl22_total", "pnl22_cb", "pnl22_btc",
            "dd22_min", "dd22_hour", "roi", "wbar"]
    out["dev_agg"] = agg(dev, keys)
    json.dump(out, open(outp, "w"), indent=1, default=float)
    # HO W9: xac nhan O(w*) (+ bao cao moi bien the de mo ta)
    nmH = C.WIN["H"]["a1"] - C.WIN["H"]["a0"]
    PH = C.load_px("H")
    seedsH = []
    for s in C.SEEDS:
        x, eq0 = C.ho_legs(s)
        x = x[x.m0 < nmH].reset_index(drop=True)
        seedsH.append((s, C.Seed(x, C.ho_closes(x, nmH), eq0, nmH, lim=None)))
    ho = run_win("H", seedsH, PH, allv)
    hchk = {s: ho[s]["_chk"] for s in ho}
    h_ok = dict(V3=all(c["V3_O0_maxabs"] <= 1e-6 for c in hchk.values()),
                V4=all(c["V4_max_excess"] <= 1e-3 for c in hchk.values()),
                EQ=all(c["eq_check_max"] <= 1e-9 for c in hchk.values()))
    hrule = None
    if wstar is not None:
        o = "O" + wstar
        dr = [ho[str(s)][o]["roi"] - ho[str(s)]["B0"]["roi"] for s in C.SEEDS]
        wdd = min(ho[str(s)][o]["dd_rule"] for s in C.SEEDS)
        hrule = dict(droi=dr, n_pos=int(sum(x > 0 for x in dr)), worst_dd_rule=wdd,
                     confirm=bool(sum(x > 0 for x in dr) >= 6 and wdd >= -40.0))
    z = np.load(C.W + "/px_btceth.npz")
    t0 = int(z["t0"])
    bh = z["btc"][C.WIN["H"]["a0"] - t0:C.WIN["H"]["a1"] - t0]
    out.update(ho=ho, ho_checks=h_ok, ho_rule=hrule, ho_agg=agg(ho, keys),
               btc_ho=dict(ret=float(100 * (bh[-1] / bh[0] - 1)), dd_hour=C.dd_of(bh[59::60])[0], dd_day=C.dd_of(bh[1439::1440])[0]))
    json.dump(out, open(outp, "w"), indent=1, default=float)
    log.info("HO checks %s rule %s", h_ok, hrule)
    log.info("RUN_DONE")


if __name__ == "__main__":
    main()
