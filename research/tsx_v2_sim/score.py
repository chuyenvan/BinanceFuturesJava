#!/usr/bin/env python3
"""TSX_V2_SIM (PREREG_TSX_V2_SIM bfa59d4a) - cham DEV 8 seed: 4 bien the vs X14 (sim Java day du).
MTM phut moi cho X14 + bien the (gvz_mtm import TRUOC, missing=0) -> n700.arm_metrics (CAGR22/DD22/Calmar22/UW22);
mo ta kieu DEEP (cum/dot vao/leg, notional, phoi nhiem, cum hoan + von giam, crash-buy lo so X14 theo 25 dot Phase A);
phan ra dPnL = direct (replay phaseB) + phan con lai; luat ung vien v1.2 (C1-C5). Out: docs/result/tsx_v2_sim/.
Usage: python3 score.py [--arms V336,V420,VT25,VL45] [--smoke]
"""
import argparse
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402,F401  (path src/research/analysis)
sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  (PHAI truoc R)
import reset_rule_score as R  # noqa: E402
import flat3_crashpen_driver as F3  # noqa: E402
import n700_driver as N  # noqa: E402

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
sys.path.insert(0, REPO + "/docs/result/ts_mkt_ext/deep")
import deep_analysis as DA  # noqa: E402
sys.path.insert(0, REPO + "/research/tsx_v2")
import common as CM  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx2score")
W = "/home/ubuntu/claude_master/tsx2sim"
OUTD = REPO + "/docs/result/tsx_v2_sim"
KS = "/home/ubuntu/kaggle_sim/out/"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
FL = json.load(open(W + "/flags_variants.json"))["arms"]
CELL = {"V336": "B1a_336h", "V420": "B1b_420h", "VT25": "B4_-0.25_30", "VL45": "B4_-0.30_45", "CTL": "BASE"}
H7 = pd.Timedelta(hours=7)
TS_MIN = 168 * 60
REG = []
FIELDS = ("cagr22", "sum_pnl", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year")
PFIELDS = ("n_cl", "n_batch", "n_leg", "pnl", "roi", "dd", "dd_day", "calmar", "exp_mean", "exp_max", "notional", "hold_mean",
           "n168", "ncut")


class Rec(MT.MTMStateD):
    def __init__(self):
        super().__init__()
        self.rec = {}
        REG.append(self)

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        self.rec[int(m_global)] = np.asarray(eq["legacy"], np.float32).copy()


def tag_of(arm, s):
    if arm == "X14":
        return "tsx-x14-" + s.lower()
    if arm == "CTL":
        return "tsx2-ctl-" + s.lower()
    return "tsx2-%s-%s" % (arm.lower(), s.lower())


def mmm(v):
    v = np.asarray([x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))], float)
    return [float(np.median(v)), float(v.min()), float(v.max())] if len(v) else [float("nan")] * 3


def base_arm(arm):
    return "X14" if arm == "CTL" else arm


def days_set(arm):
    a = base_arm(arm)
    out = set()
    for r in FL[a]["dev"]["ranges"].split(","):
        x, y = r.split("-")
        out |= set(pd.date_range(pd.Timestamp(x), pd.Timestamp(y), freq="D"))
    assert len(out) == FL[a]["dev"]["n_days"]
    return out


def cap_min(arm):
    return (168 + FL[base_arm(arm)]["ext_hours"]) * 60


def deferred(run, p0c, fl, capm):
    """= DEEP deferred() (quy uoc §1) voi co + tran cua bien the; khong tinh PnL@168h (direct lay tu replay)."""
    c = run["c"]
    cand = c[(c["age_min"] > TS_MIN + 1) & c["mark_day"].isin(fl)].copy()
    pm = p0c.set_index(["sym", "t0"])
    armed = []
    for s, t0 in zip(cand["sym"], cand["t0"]):
        if (s, t0) in pm.index:
            r = pm.loc[(s, t0)]
            r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
            armed.append(bool(r["age_min"] > TS_MIN + 1 and r["st"] != "STOP_LOSS_DONE"))
        else:
            armed.append(False)
    cand["armed_pre"] = armed
    df = cand[~cand["armed_pre"]].copy().reset_index(drop=True)
    teu = df["te"] - H7
    off = teu.dt.normalize()
    df["exit"] = np.where(df["st"] != "STOP_LOSS_DONE", "arm_trail",
                          np.where(df["age_min"] >= capm, "cut_cap",
                                   np.where((teu == off) & ~off.isin(fl), "cut_flag_off", "sl_other")))
    df["extra_h"] = (df["age_min"] - TS_MIN) / 60.0
    return df


def mtm_all(keys):
    assert R._work is MT._work_vision, "gvz_mtm chua patch R"
    R.MTMState = Rec
    legs = {k: R.load_legs(t) for k, t in keys.items()}
    daily = {k: R.load_daily(t) for k, t in keys.items()}
    out = R.run_mtm(legs, workers=3, chunk=30)
    assert len(REG) == len(keys), (len(REG), len(keys))
    eq = {}
    for k, st in zip(legs, REG):
        ms = sorted(st.rec)
        assert all(b - a == 1440 for a, b in zip(ms, ms[1:])), "ngay khong lien tuc"
        eq[k] = (np.concatenate([st.rec[m] for m in ms]).astype(np.float64), DA.DAY0 + pd.Timedelta(minutes=ms[0]))
    return legs, daily, out, eq


def seed_row(arm, s, keys, M, runs, par, p0c, DFX, fl_x, eps, lab, cl, phB):
    kv, kx = arm + "_" + s, "X14_" + s
    mv, mx = M[kv], M[kx]
    rv, rx = runs[kv], runs[kx]
    fl, capm = days_set(arm), cap_min(arm)
    r = {f: [mx[f], mv[f], mv[f] - mx[f]] for f in FIELDS}
    r["per_year_pnl"] = {y: [mx["per_year"][y]["sum_pnl"], mv["per_year"][y]["sum_pnl"]] for y in mx["per_year"]}
    pv, px = {}, {}
    for name, x0, x1 in DA.PER_DEV:
        pv[name], px[name] = DA.period(rv, x0, x1), DA.period(rx, x0, x1)
        for z, rr in ((pv, rv), (px, rx)):
            L = rr["d"][(rr["d"]["te"] >= pd.Timestamp(x0)) & (rr["d"]["te"] < pd.Timestamp(x1))]
            z[name]["notional"] = float(L["notional"].sum())
    r["period"] = {name: {f: [px[name][f], pv[name][f]] for f in PFIELDS} for name, _, _ in DA.PER_DEV}
    # cum hoan + von giam
    dfv = deferred(rv, p0c[s], fl, capm)
    fe_v = DA.flag_exposure(rv, fl, True, dfv)
    fe_x = DA.flag_exposure(rx, fl_x, True, DFX[s])
    tsx = par[keys[kv]]["tsx"]
    r["defer"] = dict(n=[len(DFX[s]), len(dfv)], java=tsx[3], java_cut=tsx[4], cut=int((dfv["st"] == "STOP_LOSS_DONE").sum()),
                      V4_ok=bool(len(dfv) == tsx[3]), exit=dfv["exit"].value_counts().to_dict(),
                      extra_h=[float(DFX[s]["extra_h"].mean()), float(dfv["extra_h"].mean()) if len(dfv) else 0.0],
                      pnl=[float(DFX[s]["pnl"].sum()), float(dfv["pnl"].sum())],
                      locked_flag_mean=[fe_x.get("locked_flag_mean"), fe_v.get("locked_flag_mean")],
                      locked_max=[fe_x.get("locked_max"), fe_v.get("locked_max")],
                      exp_flag_mean=[fe_x["exp_flag_mean"], fe_v["exp_flag_mean"]],
                      hours_flag=[fe_x["hours_flag"], fe_v["hours_flag"]])
    # crash-buy lo so X14 (25 dot Phase A, cua so [dau, cuoi + 15d) UTC)
    ev = []
    for i, (x0, x1) in enumerate(eps):
        b = x1 + pd.Timedelta(days=15)
        wa, wb = DA.win_stats(rx, x0, b, True), DA.win_stats(rv, x0, b, True)
        xo, vo = wa["keys"] - wb["keys"], wb["keys"] - wa["keys"]
        ev.append(dict(ep=lab[i], new=[wa["new_cl"], wb["new_cl"]], x14_only=len(xo), v_only=len(vo),
                       x14_only_pnl=float(sum(wa["pnl_new"][q] for q in xo)), v_only_pnl=float(sum(wb["pnl_new"][q] for q in vo)),
                       dd=[wa["dd"], wb["dd"]]))
    r["missed"] = ev
    kx_all, kv_all = set(zip(rx["c"]["sym"], rx["c"]["t0"])), set(zip(rv["c"]["sym"], rv["c"]["t0"]))
    px_all = dict(zip(zip(rx["c"]["sym"], rx["c"]["t0"]), rx["c"]["pnl"]))
    pv_all = dict(zip(zip(rv["c"]["sym"], rv["c"]["t0"]), rv["c"]["pnl"]))
    r["missed_all"] = dict(x14_only=len(kx_all - kv_all), v_only=len(kv_all - kx_all),
                           x14_only_pnl=float(sum(px_all[q] for q in kx_all - kv_all)),
                           v_only_pnl=float(sum(pv_all[q] for q in kv_all - kx_all)))
    # phan ra direct + con lai; theo dot
    g = cl[cl["seed"] == s]
    col = "d_" + CELL[arm]
    r["direct_ep"] = [float(g.loc[g["ep"] == e, col].sum()) for e in lab]
    r["direct"] = float(g[col].sum())
    r["direct_check"] = float(r["direct"] - phB[CELL[arm]]["delta_seed"][s])
    r["direct_outside_ep"] = float(g.loc[~g["ep"].isin(lab), col].sum())
    r["rest"] = float(r["sum_pnl"][2] - r["direct"])
    bounds = [pd.Timestamp("2021-01-01")] + [x0 for x0, _ in eps] + [pd.Timestamp("2026-01-01")]
    sd = DA.seg_delta(rx, rv, bounds)
    r["seg_pre"], r["seg_ep"] = sd[0], sd[1:]
    r["seg_check"] = float(sum(sd) - r["sum_pnl"][2])
    log.info("ROW %s %-5s CAGR22 %.2f->%.2f DD22 %.2f->%.2f Cal %.3f->%.3f dPnL %+.0f (direct %+.0f rest %+.0f) batch %d->%d "
             "defer %d (java %d) locked max %.1f->%.1f", arm, s, mx["cagr22"], mv["cagr22"], mx["dd_mtm22"], mv["dd_mtm22"],
             mx["calmar22"], mv["calmar22"], r["sum_pnl"][2], r["direct"], r["rest"], r["period"]["DEV"]["n_batch"][0],
             r["period"]["DEV"]["n_batch"][1], len(dfv), tsx[3], r["defer"]["locked_max"][0] or 0, r["defer"]["locked_max"][1] or 0)
    return r


def rule_of(rows, ok, lab):
    n = len(ok)
    dc = [rows[s]["cagr22"][2] for s in ok]
    dcal = [rows[s]["calmar22"][2] for s in ok]
    wv, wx = min(rows[s]["dd_mtm22"][1] for s in ok), min(rows[s]["dd_mtm22"][0] for s in ok)
    dir_e = np.mean(np.array([rows[s]["direct_ep"] for s in ok]), axis=0)
    seg_e = np.mean(np.array([rows[s]["seg_ep"] for s in ok]), axis=0)
    nb = [rows[s]["period"]["DEV"]["n_batch"][1] / rows[s]["period"]["DEV"]["n_batch"][0] - 1 for s in ok]
    rule = dict(C1=dict(n_pos=int(sum(x > 0 for x in dc)), ok=bool(n == 8 and sum(x > 0 for x in dc) >= 7)),
                C2=dict(n_ge0=int(sum(x >= 0 for x in dcal)), ok=bool(n == 8 and sum(x >= 0 for x in dcal) >= 6)),
                C3=dict(worst_v=wv, worst_x14=wx, ok=bool(wv >= wx - 1.0)),
                C4=dict(direct_tot=float(dir_e.sum()), direct_max_ep=lab[int(np.argmax(dir_e))], direct_loo=float(dir_e.sum() - dir_e.max()),
                        seg_tot=float(seg_e.sum()), seg_max_ep=lab[int(np.argmax(seg_e))], seg_loo=float(seg_e.sum() - seg_e.max()),
                        ok=bool(dir_e.sum() - dir_e.max() > 0 and seg_e.sum() - seg_e.max() > 0)),
                C5=dict(mean_dbatch=float(np.mean(nb)), ok=bool(np.mean(nb) >= -0.02)))
    rule["candidate"] = bool(n == 8 and all(rule[c]["ok"] for c in ("C1", "C2", "C3", "C4", "C5")))
    return rule, dir_e, seg_e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="V336,V420,VT25,VL45")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    arms = a.arms.split(",")
    seeds = ["A1"] if a.smoke else SEEDS
    os.makedirs(OUTD, exist_ok=True)
    par, keys = {}, {}
    for s in seeds:
        keys["X14_" + s] = tag_of("X14", s)
        for arm in arms:
            t = tag_of(arm, s)
            p = W + "/res_%s.json" % t
            r = json.load(open(p)) if os.path.exists(p) else None
            par[t] = r
            if r and r["passed"]:
                keys[arm + "_" + s] = t
            else:
                log.error("VOID/thieu %s %s", t, r and r.get("chk"))
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "TSX_V2_SIM " + k
    legs, daily, mt, eq = mtm_all(keys)
    ref = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    V = dict(mtm_missing={k: int(mt[k]["legacy"]["missing"]) for k in keys}, sumpnl_vs_printDone={})
    assert all(v == 0 for v in V["mtm_missing"].values()), "MTM thieu gia"
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], mt[k]["legacy"]) for k in keys}
    for k in keys:
        pdp = pd.read_csv(KS + keys[k] + "/storage/printDone.csv", index_col=False)
        pdp.columns = [c.strip() for c in pdp.columns]
        V["sumpnl_vs_printDone"][k] = float(M[k]["sum_pnl"] - pd.to_numeric(pdp["pnl"], errors="coerce").sum())
    x14 = [k for k in keys if k.startswith("X14_")]
    V["x14_vs_mtm_vision"] = {k: float(max(abs(mt[k]["legacy"]["dd_total"] - ref[k]["legacy"]["dd_total"]),
                                           abs(mt[k]["legacy"]["dd_win"] - ref[k]["legacy"]["dd_win"]))) for k in x14}
    V["x14_cagr22_mean"] = float(np.mean([M[k]["cagr22"] for k in x14]))
    V["x14_dd22_mean"] = float(np.mean([M[k]["dd_mtm22"] for k in x14]))
    V["V1_ok"] = bool(a.smoke or (abs(V["x14_cagr22_mean"] - 39.49) <= 0.1 and abs(V["x14_dd22_mean"] + 22.55) <= 0.1))
    V["V3_ok"] = bool(max(abs(v) for v in V["sumpnl_vs_printDone"].values()) < 1e-6)
    log.info("V1 X14 CAGR22 %.3f DD22 %.3f -> %s; vs mtm_vision max %.2e; V3 %s", V["x14_cagr22_mean"], V["x14_dd22_mean"],
             V["V1_ok"], max(V["x14_vs_mtm_vision"].values()), V["V3_ok"])
    assert V["V1_ok"] and V["V3_ok"], "V1/V3 FAIL"
    runs = {}
    p0c = {s: DA.clusters(DA.load("gqsf-" + s.lower())) for s in seeds}
    for k, t in keys.items():
        d = DA.load(t)
        e, base = eq[k]
        runs[k] = dict(tag=t, d=d, c=DA.clusters(d), eq=e, base=base, on=DA.open_notional(d, len(e), base, True),
                       cap0=float(R.CAP0), utc=True)
    eps = CM.episodes(CM.ew_eod())
    lab = ["%s..%s" % (x.strftime("%Y-%m-%d"), y.strftime("%Y-%m-%d")) for x, y in eps]
    cl = pd.read_csv(REPO + "/docs/result/tsx_v2/phaseB_clusters.csv")
    phB = json.load(open(REPO + "/docs/result/tsx_v2/phaseB.json"))["variants"]
    res = dict(prereg="bfa59d4a", validate=V, parity=par, episodes=lab, arms={})
    fl_x = days_set("X14")
    DFX = {s: deferred(runs["X14_" + s], p0c[s], fl_x, cap_min("X14")) for s in seeds}
    V["V4_x14"] = {s: [len(DFX[s]), json.load(open("/home/ubuntu/claude_master/tsx/parity.json"))[tag_of("X14", s)]["tsx"][1]]
                   for s in seeds}
    for arm in arms:
        ok = [s for s in seeds if arm + "_" + s in keys]
        rows = {s: seed_row(arm, s, keys, M, runs, par, p0c, DFX, fl_x, eps, lab, cl, phB) for s in ok}
        rule, dir_e, seg_e = rule_of(rows, ok, lab)
        agg = {f: dict(x14=mmm([rows[s][f][0] for s in ok]), v=mmm([rows[s][f][1] for s in ok]), d=mmm([rows[s][f][2] for s in ok]))
               for f in FIELDS}
        agg["direct"] = mmm([rows[s]["direct"] for s in ok])
        agg["rest"] = mmm([rows[s]["rest"] for s in ok])
        agg["dir_ep_mean"] = dict(zip(lab, map(float, dir_e)))
        agg["seg_ep_mean"] = dict(zip(lab, map(float, seg_e)))
        res["arms"][arm] = dict(seeds=ok, rule=rule, agg=agg, rows=rows, cell=CELL[arm],
                                flags=dict(n_days=FL[base_arm(arm)]["dev"]["n_days"], cap_h=cap_min(arm) // 60))
        log.info("RULE %s %s", arm, json.dumps(rule, default=str))
        log.info("AGG %s dCAGR22 %s dPnL %s direct %s rest %s dDD22 %s dCal %s", arm, agg["cagr22"]["d"], agg["sum_pnl"]["d"],
                 agg["direct"], agg["rest"], agg["dd_mtm22"]["d"], agg["calmar22"]["d"])
    cands = [x for x in arms if res["arms"][x]["rule"]["candidate"] and x != "CTL"]
    pick = sorted(cands, key=lambda x: (-res["arms"][x]["agg"]["calmar22"]["d"][0], -res["arms"][x]["rule"]["C3"]["worst_v"]))
    res["candidates"], res["pick"] = cands, (pick[0] if pick else None)
    log.info("UNG VIEN %s -> chon %s", cands, res["pick"])
    fn = OUTD + ("/smoke.json" if a.smoke else "/sim.json")
    json.dump(res, open(fn, "w"), indent=1, default=str)
    log.info("WROTE %s", fn)


if __name__ == "__main__":
    main()
