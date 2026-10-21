#!/usr/bin/env python3
"""B15_V11 scorer (PREREG_B15_V11 6cf67a58). P = X14 (tsx-*), S15 = X14 + SIM_F_BASE 0.0225 (b15-*).
dev : gvz_mtm (import TRUOC, assert _work Vision, missing=0) + n700_driver.arm_metrics; stress impact EDGE_ATTR §4
      qua cot chi phi trong run_mtm (MTM_COSTS legacy + imp) va equity ngay - chi phi luy ke.
ho  : ham ho4_score_a nhu ecm_mtm_h.py (W9/Q1/Q2/Q3), eq_imp = eq - chi phi luy ke tai phut dong.
Usage: python3 b15_score.py dev|ho [--ponly]
"""
import json
import logging
import math
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  (PHAI import truoc: patch R -> Vision)

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import reset_rule_score as R  # noqa: E402
import flat3_crashpen_driver as F3  # noqa: E402
import n700_driver as N  # noqa: E402

assert R._work is MT._work_vision
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("b15s")
W = "/home/ubuntu/claude_master/b15"
O = "/home/ubuntu/kaggle_sim/out/"
DEV_SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
HO_SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
SCEN = {"I10": (1.0, 10000.0), "I20": (1.0, 20000.0), "I20Y2": (2.0, 20000.0)}
H7 = pd.Timedelta(hours=7)
U_THR = 0.9 * 0.60
FEAT = None


def feat():
    global FEAT
    if FEAT is None:
        c = pd.read_parquet(W + "/feat_cache.parquet")
        FEAT = {(v, int(m)): (l, s, n) for v, m, l, s, n in zip(c["vs"], c["M"], c["L24"], c["sig_d"], c["nbar"])}
    return FEAT


def cost_frac(sym, start, notional, Y, sc):
    """c moi leg (EDGE_ATTR): Y*sig_d*sqrt(N*sc/L24); leg thieu dac trung -> p99 cua leg hop le."""
    F = feat()
    t0 = pd.to_datetime(pd.Series(start).astype(str).str.strip(), format="%Y%m%d %H:%M")
    M = ((t0 - H7).astype("int64") // 10 ** 6).to_numpy(np.int64)
    vs = pd.Series(sym).astype(str).str.strip().to_numpy() + "USDT"
    L, S, NB = (np.array([F.get((v, int(m)), (np.nan, np.nan, np.nan))[i] for v, m in zip(vs, M)], float) for i in range(3))
    nf = int(np.sum([(v, int(m)) not in F for v, m in zip(vs, M)]))
    ok = np.isfinite(L) & (L > 0) & np.isfinite(S) & np.isfinite(NB) & (NB >= 60)
    N_ = np.asarray(notional, float)
    sc = np.broadcast_to(np.asarray(sc, float), N_.shape)
    c = np.full(len(N_), np.nan)
    c[ok] = Y * S[ok] * np.sqrt(N_[ok] * sc[ok] / L[ok])
    p99 = float(np.percentile(c[ok], 99)) if ok.any() else 0.0
    c[~ok] = p99
    return c, dict(n=int(len(N_)), n_invalid=int((~ok).sum()), n_nofeat=nf, p99=p99,
                   med_bps=float(np.median(c) * 1e4), mean_bps=float(np.mean(c) * 1e4))


def near_cap(legs, eqd, t_lo=None, t_hi=None):
    """U_hat = sum margin leg mo / equity ngay (xap xi, mo ta): so leg vao khi U_hat>=0.9*U_MAX, max U_hat."""
    ts = legs["ts"].to_numpy("datetime64[m]").astype(np.int64)
    te = legs["te"].to_numpy("datetime64[m]").astype(np.int64)
    m = legs["margin"].to_numpy(float)
    t = np.concatenate([ts, te])
    v = np.concatenate([m, -m])
    o = np.lexsort((v, t))    # dong truoc mo trong cung phut
    tt, cum = t[o], np.cumsum(v[o])
    dn = eqd.index.to_numpy("datetime64[m]").astype(np.int64)
    ev = eqd.to_numpy(float)
    j = np.clip(np.searchsorted(dn, tt, side="right") - 1, 0, len(ev) - 1)
    u = cum / ev[j]
    isent = v[o] > 0
    pre = u - np.where(isent, v[o] / ev[j], 0.0)
    sel = np.ones(len(tt), bool)
    if t_lo is not None:
        sel &= (tt >= t_lo) & (tt < t_hi)
    return dict(n_entry_near=int((isent & sel & (pre >= U_THR)).sum()), n_entry=int((isent & sel).sum()),
                umax=float(u[sel].max() * 100) if sel.any() else None)


def pc_skips(tag, lo=None, hi=None):
    p = O + tag + "/logs/sim.out"
    tot = sm = None
    n = 0
    if os.path.exists(p):
        with open(p, errors="ignore") as f:
            for line in f:
                if "[CONC-PC]" not in line:
                    continue
                m = re.search(r"SKIP leg .* t=(\S+)", line)
                if m:
                    d = m.group(1)[:8]
                    if lo is None or lo <= d < hi:
                        n += 1
                m2 = re.search(r"SUMMARY blocked=(\d+)", line)
                if m2:
                    sm = int(m2.group(1))
        tot = n
    return dict(skip_lines=tot, summary=sm)


def dev(ponly):
    keys = {}
    for s in DEV_SEEDS:
        keys["P_" + s] = "tsx-x14-" + s.lower()
        t = "b15-x14-" + s.lower()
        if not ponly:
            rp = W + "/res_%s.json" % t
            assert os.path.exists(rp) and json.load(open(rp))["passed"], "S15 %s chua PASS parity" % t
            keys["S_" + s] = t
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "B15_V11 " + k
    legs = {k: R.load_legs(t) for k, t in keys.items()}
    daily = {k: R.load_daily(t) for k, t in keys.items()}
    md5 = {k: R.md5_of(t) for k, t in keys.items()}
    R.MTM_COSTS = {"legacy": R.LEGACY, "imp": R.LEGACY - 1.0}
    cost, cinfo, mk = {}, {}, {}
    for k in keys:
        for sc_name, (Y, cap) in SCEN.items():
            c, info = cost_frac(legs[k]["sym"], legs[k]["start"], legs[k]["margin"], Y, cap / 35000.0)
            cost[(k, sc_name)] = 2.0 * c * legs[k]["margin"].to_numpy(float)
            cinfo["%s|%s" % (k, sc_name)] = dict(info, total_usd=float(cost[(k, sc_name)].sum()))
            x = legs[k].copy()
            x["notional"] = -cost[(k, sc_name)]
            mk["%s|%s" % (k, sc_name)] = x
    cf = W + "/mtm_dev.json"
    raw = json.load(open(cf)) if os.path.exists(cf) else {}
    miss = {kk: v for kk, v in mk.items() if raw.get(kk, {}).get("md5") != md5[kk.split("|")[0]]}
    log.info("MTM can tinh %d key", len(miss))
    if miss:
        new = R.run_mtm(miss, workers=3, chunk=30)
        for kk, v in new.items():
            v["md5"] = md5[kk.split("|")[0]]
            raw[kk] = v
        json.dump(raw, open(cf, "w"))
    V = {}
    V["V5_missing0"] = all(raw[kk]["legacy"]["missing"] == 0 and raw[kk]["imp"]["missing"] == 0 for kk in mk)
    # V6a: legacy giong nhau giua kich ban, va P trung cache TS_MKT_EXT
    tsxc = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    v6 = []
    for k in keys:
        a = [raw["%s|%s" % (k, s_)]["legacy"] for s_ in SCEN]
        for f_ in ("dd_total", "dd_win", "uw_total_days", "uw_win_days"):
            v6.append(max(abs(x[f_] - a[0][f_]) for x in a))
        if k.startswith("P_"):
            ref = tsxc.get("X14_" + k[2:], {}).get("legacy")
            if ref:
                for f_ in ("dd_total", "dd_win"):
                    v6.append(abs(ref[f_] - a[0][f_]))
    V["V6a_legacy_maxdiff"] = float(max(v6))
    M, MS = {}, {}
    W0 = N.W0
    v6b = []
    for k in keys:
        M[k] = N.arm_metrics(R, F3, k, legs[k], daily[k], raw["%s|I20" % k]["legacy"])
        dq = daily[k]
        e22 = dq.loc[W0:]
        yrs = (e22.index[-1] - e22.index[0]).days / 365.25
        x = legs[k].copy()
        x["notional"] = 0.0
        e0 = R.daily_adj(x, dq, R.LEGACY + 1.0).loc[W0:]
        cg0 = ((e0.iloc[-1] / e0.iloc[0]) ** (1 / yrs) - 1) * 100
        v6b.append(abs(cg0 - M[k]["cagr22"]))
        MS[k] = {}
        for s_ in SCEN:
            x["notional"] = cost[(k, s_)]
            ei = R.daily_adj(x, dq, R.LEGACY + 1.0)
            e = ei.loc[W0:]
            cg = ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) * 100
            mm = raw["%s|%s" % (k, s_)]["imp"]
            MS[k][s_] = dict(cagr22=float(cg), dd_mtm22=float(mm["dd_win"]), dd_mtm=float(mm["dd_total"]),
                             calmar22=float(cg / abs(mm["dd_win"])), uw_mtm22=float(mm["uw_win_days"]),
                             sum_pnl=float(M[k]["sum_pnl"] - cost[(k, s_)].sum()))
        M[k]["near_cap"] = near_cap(legs[k], dq["equity"].astype(float))
        M[k]["pc"] = pc_skips(keys[k])
        M[k]["pnl_per_notional_bps"] = float(1e4 * legs[k]["pnl"].sum() / legs[k]["margin"].sum())
        M[k]["sum_notional"] = float(legs[k]["margin"].sum())
    V["V6b_cagr0_maxdiff"] = float(max(v6b))
    pm = {f_: float(np.mean([M["P_" + s][f_] for s in DEV_SEEDS])) for f_ in ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "sum_pnl")}
    V["V1_P_dev"] = dict(pm, ok=bool(abs(pm["cagr22"] - 39.49) <= 0.1 and abs(pm["dd_mtm22"] + 22.55) <= 0.1))
    log.info("VALIDATE %s", json.dumps(V))
    out = dict(prereg="6cf67a58", validate=V, cost_info=cinfo, rows={}, stress={})
    F = ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "sum_pnl", "n", "n_per_year", "gross_max", "conc_coin_max",
         "pnl_per_notional_bps", "sum_notional")
    for k in keys:
        out["rows"][k] = {f_: M[k][f_] for f_ in F}
        out["rows"][k].update(near_cap=M[k]["near_cap"], pc=M[k]["pc"], per_year={
            y: dict(sum_pnl=v["sum_pnl"], roi_year=v["roi_year"], dd=v["dd_mtm_year"],
                    calmar=(v["roi_year"] / abs(v["dd_mtm_year"])) if v["roi_year"] is not None and v["dd_mtm_year"] else None,
                    n=v["n"]) for y, v in M[k]["per_year"].items()})
        out["stress"][k] = MS[k]
    if not ponly:
        def rule(get):
            dc = [get("S_" + s, "cagr22") - get("P_" + s, "cagr22") for s in DEV_SEEDS]
            dk = [get("S_" + s, "calmar22") - get("P_" + s, "calmar22") for s in DEV_SEEDS]
            wd = min(get("S_" + s, "dd_mtm") for s in DEV_SEEDS)
            r = dict(dcagr=dc, dcalmar=dk, worst_dd=wd, n_dcagr_pos=int(sum(v > 0 for v in dc)),
                     n_dcal_ge0=int(sum(v >= 0 for v in dk)))
            r["D1"], r["D2"], r["D3"] = r["n_dcagr_pos"] == 8, abs(wd) <= 40, r["n_dcal_ge0"] >= 6
            return r
        base = rule(lambda k, f_: M[k][f_])
        st = {s_: rule(lambda k, f_, s_=s_: MS[k][s_][f_]) for s_ in SCEN}
        base["D4"] = bool(st["I20"]["D1"] and st["I20"]["D2"] and st["I20"]["D3"])
        base["GO"] = bool(base["D1"] and base["D2"] and base["D3"] and base["D4"])
        out["rule"] = dict(base=base, stress=st)
        log.info("RULE DEV %s", json.dumps({k: v for k, v in base.items() if not isinstance(v, list)}))
        for s_ in SCEN:
            log.info("RULE DEV %s %s", s_, json.dumps({k: v for k, v in st[s_].items() if not isinstance(v, list)}))
    for arm in ("P", "S"):
        ks_ = [arm + "_" + s for s in DEV_SEEDS if arm + "_" + s in M]
        if ks_:
            log.info("AGG %s %s", arm, {f_: round(float(np.mean([M[k][f_] for k in ks_])), 3) for f_ in F[:12]})
            for s_ in SCEN:
                log.info("AGG %s %s %s", arm, s_, {f_: round(float(np.mean([MS[k][s_][f_] for k in ks_])), 3) for f_ in MS[ks_[0]][s_]})
    json.dump(out, open(W + ("/b15_dev_ponly.json" if ponly else "/b15_dev.json"), "w"), indent=1, default=float)


def ho(ponly):
    sys.path.insert(0, REPO + "/research/analysis")
    import ho4_score_a as SA
    WINS = {"W9": ("2026-01-01 00:00", "2026-10-01 00:00"), "Q1": ("2026-01-01 00:00", "2026-04-01 00:00"),
            "Q2": ("2026-04-01 00:00", "2026-07-01 00:00"), "Q3": ("2026-07-01 00:00", "2026-10-01 00:00")}
    SA.PX = "/home/ubuntu/claude_master/1013/ecm/ecm_px"
    Wd = SA.W
    Wd["dry"], Wd["DL"] = False, "20260930"
    Wd["T0"] = min(SA.ms_local(v[0]) for v in WINS.values())
    Wd["NW"] = (max(SA.ms_local(v[1]) for v in WINS.values()) - Wd["T0"]) // 60000
    Wd["win"] = {k: (int((SA.ms_local(a) - Wd["T0"]) // 60000), int((SA.ms_local(b) - SA.ms_local(a)) // 60000),
                     int((SA.ms_local(b) - SA.ms_local(a)) // 86400000), SA.pd.Timestamp(a).normalize())
                 for k, (a, b) in WINS.items()}
    tags = {}
    for s in HO_SEEDS:
        tags["P_%d" % s] = "tsx-ho-x14-s%d" % s
        if not ponly:
            t = "b15-ho-x14-s%d" % s
            rp = W + "/res_%s.json" % t
            assert os.path.exists(rp) and json.load(open(rp))["passed"], "S15 %s chua PASS" % t
            tags["S_%d" % s] = t
    tl = list(tags.values())
    D, UPS, RJ = {}, {}, {}
    for t in tl:
        D[t], _ = SA.load(t)
        UPS[t] = SA.updates(t)
        RJ[t] = json.load(open(SA.OUT + t + "/result.json"))
    NE = Wd["NW"]
    for t in tl:
        ls = [u for u in UPS[t] if u[0][:8] == str(RJ[t].get("date_last"))]
        if ls:
            NE = max(NE, (ls[-1][1] - Wd["T0"]) // 60000 + 1)
    Wd["NE"] = int(min(NE, Wd["NW"] + 2 * 1440))
    U, mt = SA.build(tl, D, 8)
    rows, cinfo = {}, {}
    for i, (k, t) in enumerate(tags.items()):
        d = D[t]
        eq = SA.equity(d, RJ[t]["equity_start"], U[i])
        ec = SA.eqcheck(eq, UPS[t], RJ[t])
        r = {"eqcheck": ec, "base": {}, "stress": {}}
        for wk in WINS:
            m, _ = SA.metr(d, eq, wk)
            r["base"][wk] = dict(roi=m["roi"], maxdd=m["maxdd"], cagr_ann=m["cagr_ann"], sum_pnl=m["sum_pnl"], n=m["n"],
                                 eq0=m["eq0"], calmar=m["cagr_ann"] / abs(m["maxdd"]) if m["maxdd"] else None)
        eq0 = r["base"]["W9"]["eq0"]
        e = d["e"].to_numpy()
        act = e >= 0
        for s_, (Y, cap) in SCEN.items():
            c, info = cost_frac(d["sym"], d["start"], d["margin"], Y, cap / eq0)
            cu = np.where(act, 2.0 * c * d["margin"].to_numpy(float), 0.0)
            cinfo["%s|%s" % (k, s_)] = dict(info, total_usd=float(cu.sum()), total_pct_eq0=float(100 * cu.sum() / eq0))
            add = np.zeros(Wd["NE"])
            np.add.at(add, np.clip(e[act], 0, Wd["NE"] - 1), cu[act])
            eqi = eq - np.cumsum(add)
            di = d.copy()
            di["pnl"] = d["pnl"].to_numpy(float) - cu
            r["stress"][s_] = {}
            for wk in WINS:
                m, _ = SA.metr(di, eqi, wk)
                r["stress"][s_][wk] = dict(roi=m["roi"], maxdd=m["maxdd"], cagr_ann=m["cagr_ann"], sum_pnl=m["sum_pnl"],
                                           calmar=m["cagr_ann"] / abs(m["maxdd"]) if m["maxdd"] else None)
        lg = R.load_legs(t)
        dq = R.load_daily(t)
        lo, hi = np.datetime64("2026-01-01T00:00", "m").astype(np.int64), np.datetime64("2026-10-01T00:00", "m").astype(np.int64)
        r["near_cap_W9"] = near_cap(lg, dq["equity"].astype(float), lo, hi)
        w9 = lg[(lg["te"] >= "2026-01-01") & (lg["ts"] < "2026-10-01")]
        r["gc_W9"] = R.gross_conc(w9, dq["equity"].astype(float)) if len(w9) else None
        r["pc_W9"] = pc_skips(t, "20260101", "20261001")
        cl = lg[(lg["te"] >= "2026-01-01") & (lg["te"] < "2026-10-01")]
        r["pnl_per_notional_bps_W9"] = float(1e4 * cl["pnl"].sum() / cl["margin"].sum())
        r["sum_notional_W9"] = float(cl["margin"].sum())
        rows[k] = r
        log.info("HO %s %s W9 roi %.2f dd %.2f cal %.2f | I20 roi %.2f dd %.2f eqchk %s", k, t, r["base"]["W9"]["roi"],
                 r["base"]["W9"]["maxdd"], r["base"]["W9"]["calmar"], r["stress"]["I20"]["W9"]["roi"],
                 r["stress"]["I20"]["W9"]["maxdd"], ec.get("final_ok"))
    V = dict(mtm_check={kk: vv for kk, vv in mt.items() if kk != "nofile_list"},
             eqcheck_all=all(rows[k]["eqcheck"].get("final_ok") for k in rows))
    pr = float(np.mean([rows["P_%d" % s]["base"]["W9"]["roi"] for s in HO_SEEDS]))
    V["V2_P_ho_roi"] = dict(mean=pr, ok=bool(abs(pr - 12.49) <= 0.1))
    log.info("VALIDATE HO %s", json.dumps(V, default=str))
    out = dict(prereg="6cf67a58", validate=V, cost_info=cinfo, rows=rows)
    if not ponly:
        def rule(get):
            dr = [get("S_%d" % s, "roi") - get("P_%d" % s, "roi") for s in HO_SEEDS]
            dk = [get("S_%d" % s, "calmar") - get("P_%d" % s, "calmar") for s in HO_SEEDS]
            wd = min(get("S_%d" % s, "maxdd") for s in HO_SEEDS)
            r = dict(droi=dr, dcalmar=dk, worst_dd=wd, n_droi_pos=int(sum(v > 0 for v in dr)), n_dcal_ge0=int(sum(v >= 0 for v in dk)))
            r["H1"], r["H2"], r["H3"] = r["n_droi_pos"] >= 6, abs(wd) <= 40, r["n_dcal_ge0"] >= 5
            return r
        base = rule(lambda k, f_: rows[k]["base"]["W9"][f_])
        st = {s_: rule(lambda k, f_, s_=s_: rows[k]["stress"][s_]["W9"][f_]) for s_ in SCEN}
        base["H4"] = bool(st["I20"]["H1"] and st["I20"]["H2"] and st["I20"]["H3"])
        base["CONFIRM"] = bool(base["H1"] and base["H2"] and base["H3"] and base["H4"])
        out["rule"] = dict(base=base, stress=st)
        log.info("RULE HO %s", json.dumps({k: v for k, v in base.items() if not isinstance(v, list)}))
        for s_ in SCEN:
            log.info("RULE HO %s %s", s_, json.dumps({k: v for k, v in st[s_].items() if not isinstance(v, list)}))
    json.dump(out, open(W + ("/b15_ho_ponly.json" if ponly else "/b15_ho.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    po = "--ponly" in sys.argv
    {"dev": dev, "ho": ho}[sys.argv[1]](po)
