#!/usr/bin/env python3
"""TSX_V3 (PREREG_TSX_V3 26b97f10) - cham DEV 8 seed: V1..V4 vs V0 (= X14 tsx-x14-*), sim Java day du.
V1 = tsx2-v420-*, V3 = tsx2-vt25-*, V4 = tsx2-vl45-* (tai dung TSX_V2_SIM, byte-identical), V2 = tsx3-v2-* (moi).
Dua tren research/tsx_v2_sim/score.py (MTM phut gvz_mtm import TRUOC -> n700.arm_metrics; mo ta kieu DEEP) + them:
cham tran U_MAX, tach dPnL = direct (replay phaseB) + sizing (lai kep, DEEP deep_extra) + phan du, theo nam, lo lenh trong/sau dot,
luat ung vien (i)-(iv) + co (v) HO (tu ho.json neu co). Out: docs/result/tsx_v3/dev.json + dev_rows.csv + validate.json.
Usage: python3 score.py [--smoke]
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
log = logging.getLogger("tsx3score")
W3, W2 = "/home/ubuntu/claude_master/tsx_v3", "/home/ubuntu/claude_master/tsx2sim"
OUTD = REPO + "/docs/result/tsx_v3"
KS = "/home/ubuntu/kaggle_sim/out/"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
FL = json.load(open(W3 + "/flags_v3.json"))["arms"]
SRC = {"V1": ("tsx2-v420-%s", W2), "V2": ("tsx3-v2-%s", W3), "V3": ("tsx2-vt25-%s", W2), "V4": ("tsx2-vl45-%s", W2)}
CELL = {"V1": "B1b_420h", "V2": "B3b_r0.20", "V3": "B4_-0.25_30", "V4": "B4_-0.30_45"}
ORDER = ["V2", "V1", "V4", "V3"]  # it thay doi nhat -> nhieu nhat (prereg §5)
ARMS = ["V1", "V2", "V3", "V4"]
H7 = pd.Timedelta(hours=7)
ONE = pd.Timedelta(days=1)
TS_MIN = 168 * 60
UMAX = 0.60
REG = []
FIELDS = ("cagr22", "sum_pnl", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year")
PFIELDS = ("n_cl", "n_batch", "n_leg", "pnl", "roi", "dd", "calmar", "exp_mean", "exp_max", "notional", "hold_mean", "n168", "ncut")
YEARS = ["2021H2", "2022", "2023", "2024", "2025"]
LUNA, J24 = "2022-04-27..2022-07-06", "2024-06-18..2024-07-26"


class Rec(MT.MTMStateD):
    def __init__(self):
        super().__init__()
        self.rec = {}
        REG.append(self)

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        self.rec[int(m_global)] = np.asarray(eq["legacy"], np.float32).copy()


def tag_of(arm, s):
    return "tsx-x14-" + s.lower() if arm == "V0" else SRC[arm][0] % s.lower()


def mmm(v):
    v = np.asarray([x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))], float)
    return [float(np.median(v)), float(v.min()), float(v.max())] if len(v) else [float("nan")] * 3


def days_set(arm):
    out = set()
    for r in FL[arm]["dev"]["ranges"].split(","):
        x, y = r.split("-")
        out |= set(pd.date_range(pd.Timestamp(x), pd.Timestamp(y), freq="D"))
    assert len(out) == FL[arm]["dev"]["n_days"]
    return out


def cap_min(arm):
    return (168 + FL[arm]["ext_hours"]) * 60


def deferred(run, p0c, fl, capm):
    """= research/tsx_v2_sim/score.py deferred() (quy uoc DEEP §1) voi co + tran cua bien the."""
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


def open_sum(d, col, n, base):
    """tong cot `col` cua leg dang mo theo phut tren truc UTC cua eq (= DA.open_notional voi cot tuy chon)."""
    a = ((d["ts"] - H7 - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    b = ((d["te"] - H7 - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    a, b = np.clip(a, 0, n), np.clip(b, 0, n)
    x = np.zeros(n + 1)
    np.add.at(x, a, d[col].to_numpy(float))
    np.add.at(x, b, -d[col].to_numpy(float))
    return np.cumsum(x)[:n]


def umax_stats(run, fl):
    """U(t) = margin leg mo / equity MTM, mau theo gio; gio U >= 0,60, so lan cham (chuyen < -> >=), theo nam (UTC).
    Them (mo ta, ngoai danh sach prereg): he so throttle sim (1 - U/U_MAX) tai phut vao leg dau moi cum (U phut truoc khi vao),
    TB toan DEV va TB cum vao trong ngay co (co cua chinh run)."""
    eq, base = run["eq"], run["base"]
    mg = open_sum(run["d"], "margin", len(eq), base)
    idx = np.arange(0, len(eq), 60)
    U = mg[idx] / eq[idx]
    hit = U >= UMAX
    touch = hit & ~np.concatenate([[False], hit[:-1]])
    yr = (base + pd.to_timedelta(idx, unit="m")).year
    c = run["c"]
    j = np.clip(((c["t0"] - H7 - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64) - 1, 0, len(eq) - 1)
    thr = np.clip(1 - (mg[j] / eq[j]) / UMAX, 0, 1)
    onf = (c["t0"] - H7).dt.normalize().isin(fl).to_numpy()
    return dict(hours=int(hit.sum()), touches=int(touch.sum()), u_mean=float(U.mean()), u_max=float(U.max()),
                u_p99=float(np.percentile(U, 99)), by_year={int(y): int(hit[yr == y].sum()) for y in np.unique(yr)},
                thr_all=float(thr.mean()), thr_flag=float(thr[onf].mean()) if onf.any() else float("nan"), n_flag_entries=int(onf.sum()))


def bal_at(d, cap0, t):
    """= DEEP deep_extra.bal_at: so du thuc hien (cap0 + PnL leg da dong truoc t)."""
    o = d.sort_values("te")
    te = o["te"].to_numpy()
    cp = np.concatenate([[0.0], np.cumsum(o["pnl"].to_numpy())])
    return cap0 + cp[np.searchsorted(te, t, side="left")]


def sizing(rx, rv, aff, cap0):
    """DEEP deep_extra: leg V0 (khong thuoc cum bi anh huong) x (bal_V / bal_V0 - 1)."""
    L = rx["d"]
    m = np.array([k not in aff for k in zip(L["sym"], L["te"])])
    L = L[m]
    t = L["ts"].to_numpy()
    ratio = bal_at(rv["d"], cap0, t) / bal_at(rx["d"], cap0, t)
    return float((L["pnl"].to_numpy() * (ratio - 1)).sum()), int((~m).sum()), float(ratio[-1]) if len(ratio) else 1.0


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


def seed_row(arm, s, M, runs, par, p0c, DFX, eps, lab, cl, phB):
    kv, kx = arm + "_" + s, "V0_" + s
    mv, mx = M[kv], M[kx]
    rv, rx = runs[kv], runs[kx]
    fl, capm = days_set(arm), cap_min(arm)
    r = {f: [mx[f], mv[f], mv[f] - mx[f]] for f in FIELDS}
    pv, px = {}, {}
    for name, x0, x1 in DA.PER_DEV:
        pv[name], px[name] = DA.period(rv, x0, x1), DA.period(rx, x0, x1)
        for z, rr in ((pv, rv), (px, rx)):
            L = rr["d"][(rr["d"]["te"] >= pd.Timestamp(x0)) & (rr["d"]["te"] < pd.Timestamp(x1))]
            z[name]["notional"] = float(L["notional"].sum())
    r["period"] = {name: {f: [px[name][f], pv[name][f]] for f in PFIELDS} for name, _, _ in DA.PER_DEV}
    r["dpnl_year"] = {y: pv[y]["pnl"] - px[y]["pnl"] for y in YEARS}
    # cum hoan + von giam
    dfv = deferred(rv, p0c[s], fl, capm)
    fe_v = DA.flag_exposure(rv, fl, True, dfv)
    fe_x = DA.flag_exposure(rx, days_set("V0"), True, DFX[s])
    tsx = par[arm][s]["tsx"]
    jc = tsx[3] if len(tsx) == 5 else tsx[1]
    r["defer"] = dict(n=[len(DFX[s]), len(dfv)], java=jc, va5_ok=bool(len(dfv) == jc), exit=dfv["exit"].value_counts().to_dict(),
                      extra_h=[float(DFX[s]["extra_h"].mean()), float(dfv["extra_h"].mean()) if len(dfv) else 0.0],
                      pnl=[float(DFX[s]["pnl"].sum()), float(dfv["pnl"].sum())],
                      locked_flag_mean=[fe_x.get("locked_flag_mean"), fe_v.get("locked_flag_mean")],
                      locked_max=[fe_x.get("locked_max"), fe_v.get("locked_max")],
                      exp_flag_mean=[fe_x["exp_flag_mean"], fe_v["exp_flag_mean"]], hours_flag=[fe_x["hours_flag"], fe_v["hours_flag"]])
    r["umax"] = [runs[kx]["umax"], runs[kv]["umax"]]
    # lenh bi lo: trong dot [dau, cuoi] va sau dot (cuoi, cuoi + 15 ngay] (UTC)
    ev = []
    for i, (x0, x1) in enumerate(eps):
        e = dict(ep=lab[i])
        for nm, a, b in (("in", x0, x1 + ONE), ("after", x1 + ONE, x1 + 16 * ONE)):
            wa, wb = DA.win_stats(rx, a, b, True), DA.win_stats(rv, a, b, True)
            xo, vo = wa["keys"] - wb["keys"], wb["keys"] - wa["keys"]
            e[nm] = dict(new=[wa["new_cl"], wb["new_cl"]], v0_only=len(xo), v_only=len(vo),
                         v0_only_pnl=float(sum(wa["pnl_new"][q] for q in xo)), v_only_pnl=float(sum(wb["pnl_new"][q] for q in vo)))
        ev.append(e)
    r["missed"] = ev
    for nm in ("in", "after"):
        r["missed_sum_" + nm] = {k: float(sum(e[nm][k] for e in ev)) for k in ("v0_only", "v_only", "v0_only_pnl", "v_only_pnl")}
        r["missed_sum_" + nm]["new_v0"] = float(sum(e[nm]["new"][0] for e in ev))
        r["missed_sum_" + nm]["new_v"] = float(sum(e[nm]["new"][1] for e in ev))
    kx_all, kv_all = set(zip(rx["c"]["sym"], rx["c"]["t0"])), set(zip(rv["c"]["sym"], rv["c"]["t0"]))
    px_all = dict(zip(zip(rx["c"]["sym"], rx["c"]["t0"]), rx["c"]["pnl"]))
    pv_all = dict(zip(zip(rv["c"]["sym"], rv["c"]["t0"]), rv["c"]["pnl"]))
    r["missed_all"] = dict(v0_only=len(kx_all - kv_all), v_only=len(kv_all - kx_all),
                           v0_only_pnl=float(sum(px_all[q] for q in kx_all - kv_all)),
                           v_only_pnl=float(sum(pv_all[q] for q in kv_all - kx_all)))
    # phan ra direct + sizing + du; theo dot
    g = cl[cl["seed"] == s]
    col = "d_" + CELL[arm]
    r["direct_ep"] = [float(g.loc[g["ep"] == e, col].sum()) for e in lab]
    r["direct"] = float(g[col].sum())
    r["direct_check"] = float(r["direct"] - phB[CELL[arm]]["delta_seed"][s])
    aff = set(zip(g.loc[g[col].abs() > 1e-9, "sym"], g.loc[g[col].abs() > 1e-9, "te"]))
    r["n_aff"] = len(aff)
    r["aff_found"] = int(len(aff & set(zip(rx["c"]["sym"], rx["c"]["te"]))))
    sz, nex, rend = sizing(rx, rv, aff, float(R.CAP0))
    r["sizing"], r["sizing_excl_legs"], r["bal_ratio_end"] = sz, nex, rend
    r["resid"] = float(r["sum_pnl"][2] - r["direct"] - sz)
    r["replay_gap"] = float(r["sum_pnl"][2] - r["direct"])
    bounds = [pd.Timestamp("2021-01-01")] + [x0 for x0, _ in eps] + [pd.Timestamp("2026-01-01")]
    sd = DA.seg_delta(rx, rv, bounds)
    r["seg_pre"], r["seg_ep"] = sd[0], sd[1:]
    r["seg_check"] = float(sum(sd) - r["sum_pnl"][2])
    log.info("ROW %s %-5s CAGR22 %.2f->%.2f DD22 %.2f->%.2f Cal %.3f->%.3f dPnL %+.0f = direct %+.0f + sizing %+.0f + du %+.0f | "
             "batch %d->%d leg %d->%d notional %.3g->%.3g | defer %d (java %d) locked max %.1f->%.1f | Uhit %d->%d",
             arm, s, mx["cagr22"], mv["cagr22"], mx["dd_mtm22"], mv["dd_mtm22"], mx["calmar22"], mv["calmar22"], r["sum_pnl"][2],
             r["direct"], sz, r["resid"], r["period"]["DEV"]["n_batch"][0], r["period"]["DEV"]["n_batch"][1],
             r["period"]["DEV"]["n_leg"][0], r["period"]["DEV"]["n_leg"][1], r["period"]["DEV"]["notional"][0],
             r["period"]["DEV"]["notional"][1], len(dfv), jc, r["defer"]["locked_max"][0] or 0, r["defer"]["locked_max"][1] or 0,
             r["umax"][0]["hours"], r["umax"][1]["hours"])
    return r


def rule_of(rows, ok, lab, ho):
    n = len(ok)
    dc = [rows[s]["cagr22"][2] for s in ok]
    wv, wx = min(rows[s]["dd_mtm22"][1] for s in ok), min(rows[s]["dd_mtm22"][0] for s in ok)
    dir_e = np.mean(np.array([rows[s]["direct_ep"] for s in ok]), axis=0)
    seg_e = np.array([rows[s]["seg_ep"] for s in ok])
    es = int(np.argmax(dir_e))
    loo = float(np.mean([rows[s]["sum_pnl"][2] - rows[s]["seg_ep"][es] for s in ok]))
    nb = [rows[s]["period"]["DEV"]["n_batch"][1] / rows[s]["period"]["DEV"]["n_batch"][0] - 1 for s in ok]
    rule = dict(i=dict(n_pos=int(sum(x > 0 for x in dc)), ok=bool(n == 8 and all(x > 0 for x in dc))),
                ii=dict(worst_v=wv, worst_v0=wx, ok=bool(wv >= wx - 1.0)),
                iii=dict(e_star=lab[es], direct_e_star=float(dir_e[es]), seg_e_star=float(seg_e[:, es].mean()),
                         dpnl_mean=float(np.mean([rows[s]["sum_pnl"][2] for s in ok])), loo=loo, ok=bool(loo > 0)),
                iv=dict(mean_dbatch=float(np.mean(nb)), per_seed=[float(x) for x in nb], ok=bool(np.mean(nb) >= -0.03)))
    rule["v"] = dict(n_ge0=ho.get("n_ge0"), ok=(ho.get("n_ge0") >= 6) if ho.get("n_ge0") is not None else None, gating=False)
    rule["candidate"] = bool(n == 8 and all(rule[c]["ok"] for c in ("i", "ii", "iii", "iv")))
    rule["ho_warning"] = bool(rule["candidate"] and rule["v"]["ok"] is False)
    return rule, dir_e, seg_e.mean(axis=0)


def load_par(seeds):
    par, bad = {"V0": {}}, []
    x14p = json.load(open("/home/ubuntu/claude_master/tsx/parity.json"))
    for s in seeds:
        t = tag_of("V0", s)
        par["V0"][s] = dict(passed=bool(x14p[t]["ok"]), tsx=x14p[t]["tsx"])
    for arm in ARMS:
        par[arm] = {}
        for s in seeds:
            t = tag_of(arm, s)
            p = SRC[arm][1] + "/res_%s.json" % t
            r = json.load(open(p)) if os.path.exists(p) else None
            if r is None:
                bad.append(t)
                continue
            pr = T.GA.prof_run(t)
            kok = pr.get("SIM_LOSER_TS_EXT_DAYS") == FL[arm]["dev"]["ranges"] and pr.get("SIM_LOSER_TS_EXT_HOURS") == str(FL[arm]["ext_hours"])
            par[arm][s] = dict(passed=bool(r["passed"] and kok), key_v3=kok, md5=r.get("md5"), tsx=r.get("tsx"), chk=r.get("chk"))
            if not par[arm][s]["passed"]:
                bad.append(t)
    return par, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    seeds = ["A1"] if a.smoke else SEEDS
    os.makedirs(OUTD, exist_ok=True)
    par, bad = load_par(seeds)
    log.info("PARITY thieu/VOID: %s", bad)
    keys = {"V0_" + s: tag_of("V0", s) for s in seeds}
    for arm in ARMS:
        for s in seeds:
            if par[arm].get(s, {}).get("passed"):
                keys[arm + "_" + s] = tag_of(arm, s)
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "TSX_V3 " + k
    legs, daily, mt, eq = mtm_all(keys)
    ref = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    V = dict(prereg=open(W3 + "/prereg_commit.txt").read().strip(), bad=bad,
             mtm_missing={k: int(mt[k]["legacy"]["missing"]) for k in keys}, sumpnl_vs_printDone={})
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], mt[k]["legacy"]) for k in keys}
    for k in keys:
        pdp = pd.read_csv(KS + keys[k] + "/storage/printDone.csv", index_col=False)
        pdp.columns = [c.strip() for c in pdp.columns]
        V["sumpnl_vs_printDone"][k] = float(M[k]["sum_pnl"] - pd.to_numeric(pdp["pnl"], errors="coerce").sum())
    x0 = [k for k in keys if k.startswith("V0_")]
    V["v0_vs_mtm_vision"] = {k: float(max(abs(mt[k]["legacy"]["dd_total"] - ref["X14_" + k[3:]]["legacy"]["dd_total"]),
                                          abs(mt[k]["legacy"]["dd_win"] - ref["X14_" + k[3:]]["legacy"]["dd_win"]))) for k in x0}
    V["v0_cagr22_mean"] = float(np.mean([M[k]["cagr22"] for k in x0]))
    V["v0_dd22_mean"] = float(np.mean([M[k]["dd_mtm22"] for k in x0]))
    V["VA1"] = bool(a.smoke or (abs(V["v0_cagr22_mean"] - 39.49) <= 0.1 and abs(V["v0_dd22_mean"] + 22.55) <= 0.1))
    V["VA4"] = bool(all(v == 0 for v in V["mtm_missing"].values()) and max(abs(v) for v in V["sumpnl_vs_printDone"].values()) < 1e-6)
    rc = json.load(open(W3 + "/res_tsx3-ctl-s13.json")) if os.path.exists(W3 + "/res_tsx3-ctl-s13.json") else {}
    r2 = json.load(open(W2 + "/res_tsx2-ctl-a1.json"))
    r2h = json.load(open(W2 + "/res_tsx2-ho-ctl-s7.json"))
    V["VA2"] = dict(tsx3_ctl_s13=rc.get("chk", {}).get("bitexact_ref"), md5=rc.get("md5"), ref_md5=rc.get("ref_md5"),
                    tsx2_ctl_a1=r2.get("chk", {}).get("bitexact_ref"), tsx2_ho_ctl_s7=r2h.get("bitexact_ref"))
    V["VA2_ok"] = bool(a.smoke or V["VA2"]["tsx3_ctl_s13"] is True)
    fc = json.load(open(W3 + "/flags_v3.json"))["checks"]
    V["VA3"] = bool(fc["v0_dev"] and fc["v0_dev_sha_c79ef302"] and fc["v0_ho"])
    log.info("VA1 V0 CAGR22 %.3f DD22 %.3f -> %s; vs mtm_vision max %.2e; VA2 %s; VA3 %s; VA4 %s", V["v0_cagr22_mean"],
             V["v0_dd22_mean"], V["VA1"], max(V["v0_vs_mtm_vision"].values()), V["VA2"], V["VA3"], V["VA4"])
    runs = {}
    p0c = {s: DA.clusters(DA.load("gqsf-" + s.lower())) for s in seeds}
    for k, t in keys.items():
        d = DA.load(t)
        e, base = eq[k]
        runs[k] = dict(tag=t, d=d, c=DA.clusters(d), eq=e, base=base, on=DA.open_notional(d, len(e), base, True),
                       cap0=float(R.CAP0), utc=True)
        runs[k]["umax"] = umax_stats(runs[k], days_set(k.split("_")[0]))
    eps = CM.episodes(CM.ew_eod())
    lab = ["%s..%s" % (x.strftime("%Y-%m-%d"), y.strftime("%Y-%m-%d")) for x, y in eps]
    assert LUNA in lab and J24 in lab
    cl = pd.read_csv(REPO + "/docs/result/tsx_v2/phaseB_clusters.csv")
    cl["te"] = pd.to_datetime(cl["te"])
    phB = json.load(open(REPO + "/docs/result/tsx_v2/phaseB.json"))["variants"]
    DFX = {s: deferred(runs["V0_" + s], p0c[s], days_set("V0"), cap_min("V0")) for s in seeds}
    V["VA5_v0"] = {s: [len(DFX[s]), par["V0"][s]["tsx"][1]] for s in seeds}
    hoj = json.load(open(OUTD + "/ho.json")) if os.path.exists(OUTD + "/ho.json") else {"arms": {}}
    res = dict(prereg=V["prereg"], parity=par, episodes=lab, arms={})
    for arm in ARMS:
        ok = [s for s in seeds if arm + "_" + s in keys]
        if not ok:
            log.error("ARM %s khong co seed hop le", arm)
            continue
        rows = {s: seed_row(arm, s, M, runs, par, p0c, DFX, eps, lab, cl, phB) for s in ok}
        ho = hoj["arms"].get(arm, {}).get("agg", {})
        rule, dir_e, seg_e = rule_of(rows, ok, lab, ho)
        agg = {f: dict(v0=mmm([rows[s][f][0] for s in ok]), v=mmm([rows[s][f][1] for s in ok]), d=mmm([rows[s][f][2] for s in ok]))
               for f in FIELDS}
        for f in ("direct", "sizing", "resid", "replay_gap"):
            agg[f] = mmm([rows[s][f] for s in ok])
        agg["dir_ep_mean"] = dict(zip(lab, map(float, dir_e)))
        agg["seg_ep_mean"] = dict(zip(lab, map(float, seg_e)))
        agg["dpnl_year"] = {y: mmm([rows[s]["dpnl_year"][y] for s in ok]) for y in YEARS}
        res["arms"][arm] = dict(seeds=ok, rule=rule, agg=agg, rows=rows, cell=CELL[arm],
                                flags=dict(n_days=FL[arm]["dev"]["n_days"], cap_h=cap_min(arm) // 60))
        V.setdefault("VA5", {})[arm] = {s: [rows[s]["defer"]["n"][1], rows[s]["defer"]["java"]] for s in ok}
        V.setdefault("VA6", {})[arm] = max(abs(rows[s]["direct_check"]) for s in ok)
        V.setdefault("aff_match", {})[arm] = {s: [rows[s]["aff_found"], rows[s]["n_aff"]] for s in ok}
        V.setdefault("seg_check", {})[arm] = max(abs(rows[s]["seg_check"]) for s in ok)
        log.info("RULE %s %s", arm, json.dumps(rule, default=str))
        log.info("AGG %s dCAGR22 %s dPnL %s direct %s sizing %s du %s dDD22 %s dCal %s", arm, agg["cagr22"]["d"], agg["sum_pnl"]["d"],
                 agg["direct"], agg["sizing"], agg["resid"], agg["dd_mtm22"]["d"], agg["calmar22"]["d"])
    V["VA5_ok"] = bool(all(a_ == b_ for v in list(V["VA5"].values()) + [V["VA5_v0"]] for a_, b_ in v.values()))
    V["VA6_ok"] = bool(max(V["VA6"].values()) <= 1e-6)
    V["ALL_OK"] = bool(V["VA1"] and V["VA2_ok"] and V["VA3"] and V["VA4"] and V["VA5_ok"] and V["VA6_ok"])
    log.info("VALIDATE VA5 %s VA6 %s aff %s seg %s -> ALL %s", V["VA5_ok"], V["VA6"], V["aff_match"], V["seg_check"], V["ALL_OK"])
    json.dump(V, open(OUTD + ("/validate_smoke.json" if a.smoke else "/validate.json"), "w"), indent=1, default=str)
    if not V["ALL_OK"] and not a.smoke:
        log.error("VALIDATE FAIL -> DUNG, khong ghi ket qua (prereg §3)")
        sys.exit(4)
    cands = [x for x in ORDER if x in res["arms"] and res["arms"][x]["rule"]["candidate"]]
    res["candidates"], res["pick"] = cands, (cands[0] if cands else None)
    log.info("UNG VIEN %s -> chon %s", cands, res["pick"])
    fn = OUTD + ("/dev_smoke.json" if a.smoke else "/dev.json")
    json.dump(res, open(fn, "w"), indent=1, default=str)
    rows = []
    for arm in [x for x in ARMS if x in res["arms"]]:
        for s, r in res["arms"][arm]["rows"].items():
            P = r["period"]["DEV"]
            rows.append(dict(arm=arm, seed=s, cagr22_v0=r["cagr22"][0], cagr22=r["cagr22"][1], dd22_v0=r["dd_mtm22"][0], dd22=r["dd_mtm22"][1],
                             calmar22_v0=r["calmar22"][0], calmar22=r["calmar22"][1], uw22_v0=r["uw_mtm22"][0], uw22=r["uw_mtm22"][1],
                             pnl_v0=r["sum_pnl"][0], pnl=r["sum_pnl"][1], dpnl=r["sum_pnl"][2], direct=r["direct"], sizing=r["sizing"],
                             resid=r["resid"], n_cl_v0=P["n_cl"][0], n_cl=P["n_cl"][1], n_batch_v0=P["n_batch"][0], n_batch=P["n_batch"][1],
                             n_leg_v0=P["n_leg"][0], n_leg=P["n_leg"][1], notional_v0=P["notional"][0], notional=P["notional"][1],
                             exp_mean_v0=P["exp_mean"][0], exp_mean=P["exp_mean"][1], exp_max_v0=P["exp_max"][0], exp_max=P["exp_max"][1],
                             defer_v0=r["defer"]["n"][0], defer=r["defer"]["n"][1], locked_mean_v0=r["defer"]["locked_flag_mean"][0],
                             locked_mean=r["defer"]["locked_flag_mean"][1], locked_max_v0=r["defer"]["locked_max"][0],
                             locked_max=r["defer"]["locked_max"][1], uhit_h_v0=r["umax"][0]["hours"], uhit_h=r["umax"][1]["hours"],
                             utouch_v0=r["umax"][0]["touches"], utouch=r["umax"][1]["touches"],
                             missed_in_v0only=r["missed_sum_in"]["v0_only"], missed_in_vonly=r["missed_sum_in"]["v_only"],
                             missed_after_v0only=r["missed_sum_after"]["v0_only"], missed_after_vonly=r["missed_sum_after"]["v_only"]))
    pd.DataFrame(rows).to_csv(OUTD + ("/dev_rows_smoke.csv" if a.smoke else "/dev_rows.csv"), index=False)
    log.info("WROTE %s", fn)


if __name__ == "__main__":
    main()
