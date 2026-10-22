#!/usr/bin/env python3
"""TSX_V3_JAVA (PREREG_TSX_V3_JAVA e930e249 + ADDENDUM A) - cham DEV 8 seed: T25 / L45 / C420 vs X14 (tsx-x14-*), sim Java day du.
T25 = tsx2-vt25-*, L45 = tsx2-vl45-*, C420 = tsx2-v420-* (run cua TSX_V2_SIM bfa59d4a, khoa byte-identical).
Dua tren research/tsx_v3/score.py (MTM phut gvz_mtm import TRUOC -> n700.arm_metrics; mo ta kieu DEEP) + them theo prereg §4-§5:
win %, von giam TB moi gio, doi chieu tung dot vao (bo / thu nho so ma / thu nho size / moi), direct_sim (cum hoan khop 2 run) + LOO dot,
luat R1-R5 + verdict theo luat TSX_V2_SIM (C1-C5) va TSX_V3 ((i)-(iv)) de minh bach.
Out: docs/result/tsx_v3_java/{validate,dev}.json + dev_rows.csv + batches.csv. Usage: python3 score.py [--smoke]
"""
import argparse
import hashlib
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
log = logging.getLogger("tsx3j")
WJ, W2, W3 = "/home/ubuntu/claude_master/tsx_v3_java", "/home/ubuntu/claude_master/tsx2sim", "/home/ubuntu/claude_master/tsx_v3"
OUTD = REPO + "/docs/result/tsx_v3_java"
KS = "/home/ubuntu/kaggle_sim/out/"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
FL = json.load(open(WJ + "/flags.json"))["arms"]
SRC = {"T25": "tsx2-vt25-%s", "L45": "tsx2-vl45-%s", "C420": "tsx2-v420-%s"}
CELL = {"T25": "B4_-0.25_30", "L45": "B4_-0.30_45", "C420": "B1b_420h"}
ARMS = ["C420", "T25", "L45"]  # = thu tu don gian (prereg §5 hoa)
H7 = pd.Timedelta(hours=7)
ONE = pd.Timedelta(days=1)
TS_MIN = 168 * 60
UMAX = 0.60
REG = []
FIELDS = ("cagr22", "sum_pnl", "dd_mtm22", "dd_mtm", "calmar22", "calmar", "uw_mtm22", "win22", "n_per_year")
PFIELDS = ("n_cl", "n_batch", "n_leg", "notional", "win", "cl_win", "pnl", "roi", "dd", "calmar", "exp_mean", "exp_max", "hold_mean",
           "n168", "ncut")
YEARS = ["2021H2", "2022", "2023", "2024", "2025"]
CLS = ("drop", "shrink_n", "shrink_size", "bigger", "same", "new")


class Rec(MT.MTMStateD):
    def __init__(self):
        super().__init__()
        self.rec = {}
        REG.append(self)

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        self.rec[int(m_global)] = np.asarray(eq["legacy"], np.float32).copy()


def tag_of(arm, s):
    return "tsx-x14-" + s.lower() if arm == "X14" else SRC[arm] % s.lower()


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


def deferred(run, p0c, fl, capm, xc=None):
    """= research/tsx_v3/score.py deferred() (quy uoc DEEP §1) voi co + tran cua bien the.
    ADDENDUM A: amb = cum khong co trong P0 va X14 (xc), thoat arm_trail -> trang thai arm tai 168h khong quan sat duoc."""
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
    if xc is None or len(df) == 0:
        df["amb"] = False
    else:
        kp, kx = set(zip(p0c["sym"], p0c["t0"])), set(zip(xc["sym"], xc["t0"]))
        df["amb"] = [(k not in kp) and (k not in kx) and e == "arm_trail" for k, e in zip(zip(df["sym"], df["t0"]), df["exit"])]
    return df


def open_sum(d, col, n, base):
    a = ((d["ts"] - H7 - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    b = ((d["te"] - H7 - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    a, b = np.clip(a, 0, n), np.clip(b, 0, n)
    x = np.zeros(n + 1)
    np.add.at(x, a, d[col].to_numpy(float))
    np.add.at(x, b, -d[col].to_numpy(float))
    return np.cumsum(x)[:n]


def umax_stats(run):
    """U(t) = margin leg mo / equity MTM (mo ta); luu U theo phut (float32) de tra tai t0 cua dot vao."""
    eq, base = run["eq"], run["base"]
    mg = open_sum(run["d"], "margin", len(eq), base)
    run["U"] = (mg / eq).astype(np.float32)
    idx = np.arange(0, len(eq), 60)
    U = run["U"][idx]
    hit = U >= UMAX
    touch = hit & ~np.concatenate([[False], hit[:-1]])
    yr = (base + pd.to_timedelta(idx, unit="m")).year
    return dict(hours=int(hit.sum()), touches=int(touch.sum()), u_mean=float(U.mean()), u_max=float(U.max()),
                u_p99=float(np.percentile(U, 99)), by_year={int(y): int(hit[yr == y].sum()) for y in np.unique(yr)})


def locked(run, dfx, fl):
    """von giam = notional leg cum hoan tu mark_u den te / equity MTM, mau theo gio (truc UTC). TB gio co ON, TB moi gio, dinh, theo nam."""
    eq, base = run["eq"], run["base"]
    n = len(eq)
    idx = np.arange(0, n, 60)
    t = base + pd.to_timedelta(idx, unit="m")
    m = np.isin(t.normalize().values, np.array(sorted(fl), dtype="datetime64[ns]"))
    if len(dfx) == 0:
        z = np.zeros(len(idx))
    else:
        L = run["d"].merge(dfx[["sym", "te", "mark_u"]], on=["sym", "te"])
        a = ((L["mark_u"] - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
        b = ((L["te"] - H7 - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
        a, b = np.clip(a, 0, n), np.clip(b, 0, n)
        x = np.zeros(n + 1)
        np.add.at(x, a, L["notional"].to_numpy(float))
        np.add.at(x, b, -L["notional"].to_numpy(float))
        z = np.cumsum(x)[:n][idx] / eq[idx]
    yr = t.year
    return dict(flag_mean=float(100 * z[m].mean()) if m.any() else float("nan"), all_mean=float(100 * z.mean()), max=float(100 * z.max()),
                hours_locked=int((z > 0).sum()), by_year_mean={int(y): float(100 * z[yr == y].mean()) for y in np.unique(yr)})


def bal_at(d, cap0, t):
    o = d.sort_values("te")
    te = o["te"].to_numpy()
    cp = np.concatenate([[0.0], np.cumsum(o["pnl"].to_numpy())])
    return cap0 + cp[np.searchsorted(te, t, side="left")]


def sizing(rx, rv, aff, cap0):
    L = rx["d"]
    m = np.array([k not in aff for k in zip(L["sym"], L["te"])])
    L = L[m]
    t = L["ts"].to_numpy()
    ratio = bal_at(rv["d"], cap0, t) / bal_at(rx["d"], cap0, t)
    return float((L["pnl"].to_numpy() * (ratio - 1)).sum()), int((~m).sum()), float(ratio[-1]) if len(ratio) else 1.0


def batch_table(run, dfd):
    """dot vao = phut anchor t0 (local). n_sym, notional leg anchor, notional moi leg, pnl, so du thuc hien tai t0, U tai phut truoc t0,
    so cum hoan dang mo tai t0 (UTC: mark_u <= t < te_u)."""
    d, c = run["d"], run["c"]
    L = d.merge(c[["sym", "te", "t0"]], on=["sym", "te"])
    L["anc"] = np.where(L["ts"] == L["t0"], L["notional"], 0.0)
    g = L.groupby("t0").agg(n_sym=("sym", "nunique"), anc=("anc", "sum"), notional=("notional", "sum"), pnl=("pnl", "sum"))
    t0 = g.index.to_numpy()
    g["bal"] = bal_at(d, run["cap0"], t0)
    j = np.clip(((g.index - H7 - run["base"]) // pd.Timedelta(minutes=1)).to_numpy(np.int64) - 1, 0, len(run["U"]) - 1)
    g["U"] = run["U"][j]
    if len(dfd):
        mu = np.sort(dfd["mark_u"].to_numpy())
        tu = np.sort((dfd["te"] - H7).to_numpy())
        tt = (g.index - H7).to_numpy()
        g["open_def"] = np.searchsorted(mu, tt, side="right") - np.searchsorted(tu, tt, side="right")
    else:
        g["open_def"] = 0
    return g


def where_of(t0u, eps):
    for x0, x1 in eps:
        if x0 <= t0u < x1 + ONE:
            return "in"
    for x0, x1 in eps:
        if x1 + ONE <= t0u < x1 + 16 * ONE:
            return "after"
    return "out"


def batch_cmp(bx, bv, eps, arm, s):
    """doi chieu tung dot vao X14 vs V (prereg §4). Tra (tom tat, cac dong khac 'same')."""
    j = bx.join(bv, how="outer", lsuffix="_x", rsuffix="_v")
    rows = []
    for t0, r in j.iterrows():
        if np.isnan(r["n_sym_x"]):
            k = "new"
        elif np.isnan(r["n_sym_v"]):
            k = "drop"
        elif r["n_sym_v"] < r["n_sym_x"]:
            k = "shrink_n"
        else:
            q = (r["anc_v"] / r["bal_v"]) / (r["anc_x"] / r["bal_x"])
            k = "shrink_size" if q < 0.99 else ("bigger" if q > 1.01 else "same")
        rows.append((t0, k))
    j["cls"] = [k for _, k in rows]
    j["where"] = [where_of(t - H7, eps) for t in j.index]
    j["year"] = [str(t.year) if t >= pd.Timestamp("2022-01-01") else "2021H2" for t in (j.index - H7)]
    out = dict(n_x=int(j["n_sym_x"].notna().sum()), n_v=int(j["n_sym_v"].notna().sum()))
    for k in CLS:
        m = j["cls"] == k
        out[k] = dict(n=int(m.sum()), by_where={w: int((m & (j["where"] == w)).sum()) for w in ("in", "after", "out")},
                      by_year={y: int((m & (j["year"] == y)).sum()) for y in YEARS})
    dr, nw, sn, ss = (j["cls"] == "drop"), (j["cls"] == "new"), (j["cls"] == "shrink_n"), (j["cls"] == "shrink_size")
    out["drop"].update(notional_x=float(j.loc[dr, "notional_x"].sum()), pnl_x=float(j.loc[dr, "pnl_x"].sum()),
                       U_x_med=float(j.loc[dr, "U_x"].median()) if dr.any() else None,
                       open_def_x_mean=float(j.loc[dr, "open_def_x"].mean()) if dr.any() else None)
    out["new"].update(notional_v=float(j.loc[nw, "notional_v"].sum()), pnl_v=float(j.loc[nw, "pnl_v"].sum()))
    for k, m in (("shrink_n", sn), ("shrink_size", ss)):
        out[k].update(d_notional=float((j.loc[m, "notional_v"] - j.loc[m, "notional_x"]).sum()),
                      d_pnl=float((j.loc[m, "pnl_v"] - j.loc[m, "pnl_x"]).sum()),
                      d_sym=float((j.loc[m, "n_sym_v"] - j.loc[m, "n_sym_x"]).sum()))
    both = j["n_sym_x"].notna() & j["n_sym_v"].notna()
    out["U_at_t0_both"] = dict(x_med=float(j.loc[both, "U_x"].median()), v_med=float(j.loc[both, "U_v"].median()))
    out["open_def_both_mean"] = [float(j.loc[both, "open_def_x"].mean()), float(j.loc[both, "open_def_v"].mean())]
    out["notional_total"] = [float(j["notional_x"].sum()), float(j["notional_v"].sum())]
    keep = j[j["cls"] != "same"].copy()
    keep.insert(0, "seed", s)
    keep.insert(0, "arm", arm)
    return out, keep.reset_index().rename(columns={"index": "t0"})


def direct_sim(rx, rv, dfx, dfv, eps):
    """direct_sim = sum (pnl_V - pnl_X14) tren cum (sym, t0) bi hoan o V HOAC X14 va co mat o CA HAI run; theo dot (mark_day)."""
    K = set(zip(dfv["sym"], dfv["t0"])) | set(zip(dfx["sym"], dfx["t0"]))
    pv = rv["c"].groupby(["sym", "t0"])["pnl"].sum()
    px = rx["c"].groupby(["sym", "t0"])["pnl"].sum()
    ep = np.zeros(len(eps) + 1)
    tot, nm, ov, ox, nov, nox = 0.0, 0, 0.0, 0.0, 0, 0
    for k in K:
        inv, inx = k in pv.index, k in px.index
        if inv and inx:
            dl = float(pv[k] - px[k])
            md = (k[1] - H7 + pd.Timedelta(minutes=TS_MIN + 1)).normalize()
            i = next((ii for ii, (x0, x1) in enumerate(eps) if x0 <= md <= x1), len(eps))
            ep[i] += dl
            tot += dl
            nm += 1
        elif inv:
            ov += float(pv[k])
            nov += 1
        else:
            ox += float(px[k])
            nox += 1
    return dict(direct=tot, n_matched=nm, n_union=len(K), ep=[float(x) for x in ep[:-1]], out_ep=float(ep[-1]),
                v_only_pnl=ov, n_v_only=nov, x_only_pnl=ox, n_x_only=nox)


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


def period_plus(rr, x0, x1):
    p = DA.period(rr, x0, x1)
    L = rr["d"][(rr["d"]["te"] >= pd.Timestamp(x0)) & (rr["d"]["te"] < pd.Timestamp(x1))]
    K = rr["c"][(rr["c"]["te"] >= pd.Timestamp(x0)) & (rr["c"]["te"] < pd.Timestamp(x1))]
    p["notional"] = float(L["notional"].sum())
    p["cl_win"] = float(100 * (K["pnl"] > 0).mean()) if len(K) else float("nan")
    return p


def seed_row(arm, s, M, runs, par, p0c, DFX, BX, eps, lab, cl, phB, BROWS):
    kv, kx = arm + "_" + s, "X14_" + s
    mv, mx = M[kv], M[kx]
    rv, rx = runs[kv], runs[kx]
    fl, capm = days_set(arm), cap_min(arm)
    r = {f: [mx[f], mv[f], mv[f] - mx[f]] for f in FIELDS}
    pv, px = {}, {}
    for name, x0, x1 in DA.PER_DEV:
        pv[name], px[name] = period_plus(rv, x0, x1), period_plus(rx, x0, x1)
    r["period"] = {name: {f: [px[name][f], pv[name][f]] for f in PFIELDS} for name, _, _ in DA.PER_DEV}
    r["dpnl_year"] = {y: pv[y]["pnl"] - px[y]["pnl"] for y in YEARS}
    dfv = deferred(rv, p0c[s], fl, capm, rx["c"])
    lk_v, lk_x = locked(rv, dfv, fl), locked(rx, DFX[s], days_set("X14"))
    tsx = par[arm][s]["tsx"]
    jc = tsx[3] if len(tsx) == 5 else tsx[1]
    namb = int(dfv["amb"].sum())
    r["defer"] = dict(n=[len(DFX[s]), len(dfv)], java=jc, va5_ok=bool(len(dfv) == jc), n_amb=namb,
                      va5p_ok=bool(len(dfv) - namb <= jc <= len(dfv)), exit=dfv["exit"].value_counts().to_dict(),
                      extra_h=[float(DFX[s]["extra_h"].mean()), float(dfv["extra_h"].mean()) if len(dfv) else 0.0],
                      pnl=[float(DFX[s]["pnl"].sum()), float(dfv["pnl"].sum())], locked=[lk_x, lk_v])
    r["umax"] = [rx["umax"], rv["umax"]]
    bv = batch_table(rv, dfv)
    r["batch"], rows = batch_cmp(BX[s], bv, eps, arm, s)
    BROWS.append(rows)
    r["dsim"] = direct_sim(rx, rv, DFX[s], dfv, eps)
    r["dsim_excl"] = direct_sim(rx, rv, DFX[s], dfv[~dfv["amb"].astype(bool)], eps)
    r["rest"] = float(r["sum_pnl"][2] - r["dsim"]["direct"])
    # mo ta them: direct replay + sizing + du (nhu TSX_V3), doan theo dot
    g = cl[cl["seed"] == s]
    col = "d_" + CELL[arm]
    r["direct_rep_ep"] = [float(g.loc[g["ep"] == e, col].sum()) for e in lab]
    r["direct_rep"] = float(g[col].sum())
    r["direct_rep_check"] = float(r["direct_rep"] - phB[CELL[arm]]["delta_seed"][s])
    aff = set(zip(g.loc[g[col].abs() > 1e-9, "sym"], g.loc[g[col].abs() > 1e-9, "te"]))
    sz, nex, rend = sizing(rx, rv, aff, float(R.CAP0))
    r["sizing"], r["sizing_excl_legs"], r["bal_ratio_end"] = sz, nex, rend
    r["resid_rep"] = float(r["sum_pnl"][2] - r["direct_rep"] - sz)
    bounds = [pd.Timestamp("2021-01-01")] + [x0 for x0, _ in eps] + [pd.Timestamp("2026-01-01")]
    sd = DA.seg_delta(rx, rv, bounds)
    r["seg_pre"], r["seg_ep"] = sd[0], sd[1:]
    r["seg_check"] = float(sum(sd) - r["sum_pnl"][2])
    b = r["batch"]
    log.info("ROW %-4s %-5s CAGR22 %.2f->%.2f DD22 %.2f->%.2f Cal %.3f->%.3f dPnL %+.0f = dsim %+.0f + rest %+.0f (rep %+.0f) | "
             "dot %d->%d drop %d shrN %d shrS %d new %d | defer %d (java %d) lockedAll %.1f->%.1f",
             arm, s, mx["cagr22"], mv["cagr22"], mx["dd_mtm22"], mv["dd_mtm22"], mx["calmar22"], mv["calmar22"], r["sum_pnl"][2],
             r["dsim"]["direct"], r["rest"], r["direct_rep"], b["n_x"], b["n_v"], b["drop"]["n"], b["shrink_n"]["n"],
             b["shrink_size"]["n"], b["new"]["n"], len(dfv), jc, lk_x["all_mean"], lk_v["all_mean"])
    return r


def rules(rows, ok, lab):
    n = len(ok)
    dc = [rows[s]["cagr22"][2] for s in ok]
    dcal = [rows[s]["calmar22"][2] for s in ok]
    wv, wx = min(rows[s]["dd_mtm22"][1] for s in ok), min(rows[s]["dd_mtm22"][0] for s in ok)
    nb = [rows[s]["period"]["DEV"]["n_batch"][1] / rows[s]["period"]["DEV"]["n_batch"][0] - 1 for s in ok]
    ds = np.array([rows[s]["dsim"]["ep"] for s in ok])
    dtot = np.array([rows[s]["dsim"]["direct"] for s in ok])
    es = int(np.argmax(ds.mean(axis=0)))
    loo = float(dtot.mean() - ds.mean(axis=0)[es])
    ds2 = np.array([rows[s]["dsim_excl"]["ep"] for s in ok])
    dtot2 = np.array([rows[s]["dsim_excl"]["direct"] for s in ok])
    es2 = int(np.argmax(ds2.mean(axis=0)))
    loo2 = float(dtot2.mean() - ds2.mean(axis=0)[es2])
    full = n == 8
    R_ = dict(R1=dict(n_pos=int(sum(x > 0 for x in dc)), ok=bool(full and all(x > 0 for x in dc))),
              R2=dict(worst_v=wv, worst_x14=wx, ok=bool(wv >= wx - 1.0)),
              R3=dict(n_ge0=int(sum(x >= 0 for x in dcal)), ok=bool(sum(x >= 0 for x in dcal) >= 6)),
              R4=dict(mean=float(np.mean(nb)), per_seed=[float(x) for x in nb], ok=bool(np.mean(nb) >= -0.02)),
              R5=dict(dsim_mean=float(dtot.mean()), e_star=lab[es], dsim_e_star=float(ds.mean(axis=0)[es]), loo=loo,
                      n_seed_pos=int((dtot > 0).sum()), out_ep_max=float(max(abs(rows[s]["dsim"]["out_ep"]) for s in ok)),
                      excl=dict(dsim_mean=float(dtot2.mean()), e_star=lab[es2], loo=loo2, ok=bool(loo2 > 0)),
                      ok=bool(loo > 0 and loo2 > 0)))
    R_["candidate"] = bool(full and all(R_[k]["ok"] for k in ("R1", "R2", "R3", "R4", "R5")))
    R_["dcal_median"] = float(np.median(dcal))
    # minh bach: luat TSX_V2_SIM (bfa59d4a) C1-C5
    dre = np.array([rows[s]["direct_rep_ep"] for s in ok]).mean(axis=0)
    sge = np.array([rows[s]["seg_ep"] for s in ok]).mean(axis=0)
    c4 = dict(direct=float(dre.sum() - dre.max()), seg=float(sge.sum() - sge.max()))
    v2 = dict(C1=bool(sum(x > 0 for x in dc) >= 7), C2=R_["R3"]["ok"], C3=R_["R2"]["ok"], C4=bool(c4["direct"] > 0 and c4["seg"] > 0),
              C5=R_["R4"]["ok"], c4_vals=c4)
    v2["candidate"] = bool(full and all(v2[k] for k in ("C1", "C2", "C3", "C4", "C5")))
    # minh bach: luat TSX_V3 (26b97f10) (i)-(iv)
    es3 = int(np.argmax(dre))
    loo3 = float(np.mean([rows[s]["sum_pnl"][2] - rows[s]["seg_ep"][es3] for s in ok]))
    v3 = dict(i=R_["R1"]["ok"], ii=R_["R2"]["ok"], iii=bool(loo3 > 0), iii_loo=loo3, iii_e=lab[es3], iv=bool(np.mean(nb) >= -0.03))
    v3["candidate"] = bool(full and all(v3[k] for k in ("i", "ii", "iii", "iv")))
    return R_, dict(TSX_V2_SIM=v2, TSX_V3=v3)


def load_par(seeds):
    par, bad = {"X14": {}}, []
    x14p = json.load(open("/home/ubuntu/claude_master/tsx/parity.json"))
    for s in seeds:
        t = tag_of("X14", s)
        par["X14"][s] = dict(passed=bool(x14p[t]["ok"]), tsx=x14p[t]["tsx"])
    for arm in ARMS:
        par[arm] = {}
        for s in seeds:
            t = tag_of(arm, s)
            p = W2 + "/res_%s.json" % t
            r = json.load(open(p)) if os.path.exists(p) else None
            if r is None:
                bad.append(t)
                continue
            pr = T.GA.prof_run(t)
            kok = pr.get("SIM_LOSER_TS_EXT_DAYS") == FL[arm]["dev"]["ranges"] and pr.get("SIM_LOSER_TS_EXT_HOURS") == str(FL[arm]["ext_hours"])
            par[arm][s] = dict(passed=bool(r["passed"] and kok), key_ok=kok, md5=r.get("md5"), tsx=r.get("tsx"), chk=r.get("chk"))
            if not par[arm][s]["passed"]:
                bad.append(t)
    return par, bad


def md5f(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    seeds = ["A1"] if a.smoke else SEEDS
    sfx = "_smoke" if a.smoke else ""
    os.makedirs(OUTD, exist_ok=True)
    par, bad = load_par(seeds)
    log.info("PARITY thieu/VOID: %s", bad)
    keys = {"X14_" + s: tag_of("X14", s) for s in seeds}
    for arm in ARMS:
        for s in seeds:
            if par[arm].get(s, {}).get("passed"):
                keys[arm + "_" + s] = tag_of(arm, s)
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "TSX_V3_JAVA " + k
    legs, daily, mt, eq = mtm_all(keys)
    ref = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    V = dict(prereg=open(WJ + "/prereg_commit.txt").read().strip(), bad=bad,
             mtm_missing={k: int(mt[k]["legacy"]["missing"]) for k in keys}, sumpnl_vs_printDone={})
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], mt[k]["legacy"]) for k in keys}
    for k in keys:
        pdp = pd.read_csv(KS + keys[k] + "/storage/printDone.csv", index_col=False)
        pdp.columns = [c.strip() for c in pdp.columns]
        V["sumpnl_vs_printDone"][k] = float(M[k]["sum_pnl"] - pd.to_numeric(pdp["pnl"], errors="coerce").sum())
    x0 = [k for k in keys if k.startswith("X14_")]
    V["x14_vs_mtm_vision"] = {k: float(max(abs(mt[k]["legacy"]["dd_total"] - ref["X14_" + k[4:]]["legacy"]["dd_total"]),
                                           abs(mt[k]["legacy"]["dd_win"] - ref["X14_" + k[4:]]["legacy"]["dd_win"]))) for k in x0}
    V["x14_cagr22_mean"] = float(np.mean([M[k]["cagr22"] for k in x0]))
    V["x14_dd22_mean"] = float(np.mean([M[k]["dd_mtm22"] for k in x0]))
    V["VA1"] = bool((a.smoke or (abs(V["x14_cagr22_mean"] - 39.49) <= 0.1 and abs(V["x14_dd22_mean"] + 22.55) <= 0.1))
                    and max(V["x14_vs_mtm_vision"].values()) <= 1e-6)
    V["VA4"] = bool(all(v == 0 for v in V["mtm_missing"].values()) and max(abs(v) for v in V["sumpnl_vs_printDone"].values()) < 1e-6)
    r2 = json.load(open(W2 + "/res_tsx2-ctl-a1.json"))
    r2h = json.load(open(W2 + "/res_tsx2-ho-ctl-s7.json"))
    rh_ref = json.load(open("/home/ubuntu/claude_master/tsx/ho/res_tsx-ho-x14-s7.json"))
    V["VA2"] = dict(dev_md5_new=md5f(KS + "tsx2-ctl-a1/storage/printDone.csv"), dev_md5_old=md5f(KS + "tsx-x14-a1/storage/printDone.csv"),
                    dev_res_bitexact=r2.get("chk", {}).get("bitexact_ref"), ho_md5_new=r2h.get("md5"), ho_md5_old=rh_ref.get("md5"),
                    ho_res_bitexact=r2h.get("bitexact_ref"))
    rc = W3 + "/res_tsx3-ctl-s13.json"
    V["VA2"]["tsx3_ctl_s13"] = json.load(open(rc)).get("chk", {}).get("bitexact_ref") if os.path.exists(rc) else "chua xong"
    V["VA2_ok"] = bool(V["VA2"]["dev_md5_new"] is not None and V["VA2"]["dev_md5_new"] == V["VA2"]["dev_md5_old"]
                       and V["VA2"]["ho_md5_new"] == V["VA2"]["ho_md5_old"] and V["VA2"]["dev_res_bitexact"] is True
                       and V["VA2"]["ho_res_bitexact"] is True)
    fc = json.load(open(WJ + "/flags.json"))["checks"]
    V["VA3"] = bool(all(fc.values()))
    log.info("VA1 X14 CAGR22 %.3f DD22 %.3f vs mtm_vision max %.2e -> %s; VA2 %s -> %s; VA3 %s; VA4 %s", V["x14_cagr22_mean"],
             V["x14_dd22_mean"], max(V["x14_vs_mtm_vision"].values()), V["VA1"], V["VA2"], V["VA2_ok"], V["VA3"], V["VA4"])
    runs = {}
    p0c = {s: DA.clusters(DA.load("gqsf-" + s.lower())) for s in seeds}
    for k, t in keys.items():
        d = DA.load(t)
        e, base = eq[k]
        runs[k] = dict(tag=t, d=d, c=DA.clusters(d), eq=e, base=base, on=DA.open_notional(d, len(e), base, True),
                       cap0=float(R.CAP0), utc=True)
        runs[k]["umax"] = umax_stats(runs[k])
    eps = CM.episodes(CM.ew_eod())
    lab = ["%s..%s" % (x.strftime("%Y-%m-%d"), y.strftime("%Y-%m-%d")) for x, y in eps]
    cl = pd.read_csv(REPO + "/docs/result/tsx_v2/phaseB_clusters.csv")
    cl["te"] = pd.to_datetime(cl["te"])
    phB = json.load(open(REPO + "/docs/result/tsx_v2/phaseB.json"))["variants"]
    DFX = {s: deferred(runs["X14_" + s], p0c[s], days_set("X14"), cap_min("X14")) for s in seeds}
    BX = {s: batch_table(runs["X14_" + s], DFX[s]) for s in seeds}
    V["VA5_x14"] = {s: [len(DFX[s]), par["X14"][s]["tsx"][1]] for s in seeds}
    res = dict(prereg=V["prereg"], parity=par, episodes=lab, arms={})
    BROWS = []
    for arm in ARMS:
        ok = [s for s in seeds if arm + "_" + s in keys]
        if not ok:
            log.error("ARM %s khong co seed hop le", arm)
            continue
        rows = {s: seed_row(arm, s, M, runs, par, p0c, DFX, BX, eps, lab, cl, phB, BROWS) for s in ok}
        rule, other = rules(rows, ok, lab)
        agg = {f: dict(x14=mmm([rows[s][f][0] for s in ok]), v=mmm([rows[s][f][1] for s in ok]), d=mmm([rows[s][f][2] for s in ok]))
               for f in FIELDS}
        for f in ("rest", "direct_rep", "sizing", "resid_rep"):
            agg[f] = mmm([rows[s][f] for s in ok])
        agg["dsim"] = mmm([rows[s]["dsim"]["direct"] for s in ok])
        agg["dsim_ep_mean"] = dict(zip(lab, map(float, np.array([rows[s]["dsim"]["ep"] for s in ok]).mean(axis=0))))
        agg["dpnl_year"] = {y: mmm([rows[s]["dpnl_year"][y] for s in ok]) for y in YEARS}
        res["arms"][arm] = dict(seeds=ok, rule=rule, other_rules=other, agg=agg, rows=rows, cell=CELL[arm],
                                flags=dict(n_days=FL[arm]["dev"]["n_days"], cap_h=cap_min(arm) // 60))
        V.setdefault("VA5", {})[arm] = {s: [rows[s]["defer"]["n"][1], rows[s]["defer"]["java"]] for s in ok}
        V.setdefault("VA5p", {})[arm] = {s: [rows[s]["defer"]["n"][1] - rows[s]["defer"]["n_amb"], rows[s]["defer"]["java"],
                                             rows[s]["defer"]["n"][1], rows[s]["defer"]["va5p_ok"]] for s in ok}
        V.setdefault("direct_rep_check", {})[arm] = max(abs(rows[s]["direct_rep_check"]) for s in ok)
        V.setdefault("seg_check", {})[arm] = max(abs(rows[s]["seg_check"]) for s in ok)
        V.setdefault("dsim_out_ep", {})[arm] = max(abs(rows[s]["dsim"]["out_ep"]) for s in ok)
        log.info("RULE %s %s | other %s", arm, json.dumps(rule, default=str), json.dumps(other, default=str))
    V["VA5_ok"] = bool(all(a_ == b_ for v in list(V["VA5"].values()) + [V["VA5_x14"]] for a_, b_ in v.values()))
    V["VA5p_ok"] = bool(all(a_ == b_ for a_, b_ in V["VA5_x14"].values()) and all(x[3] for v in V["VA5p"].values() for x in v.values()))
    V["ALL_OK"] = bool(V["VA1"] and V["VA2_ok"] and V["VA3"] and V["VA4"] and V["VA5p_ok"])
    log.info("VA5 goc (strict) %s | VA5' (ADDENDUM A) %s %s", V["VA5_ok"], V["VA5p_ok"], V["VA5p"])
    log.info("VALIDATE VA5 %s direct_rep_check %s seg %s dsim_out_ep %s -> ALL %s", V["VA5_ok"], V["direct_rep_check"], V["seg_check"],
             V["dsim_out_ep"], V["ALL_OK"])
    json.dump(V, open(OUTD + "/validate%s.json" % sfx, "w"), indent=1, default=str)
    if not V["ALL_OK"] and not a.smoke:
        log.error("VALIDATE FAIL -> DUNG, khong ghi ket qua (prereg §3)")
        sys.exit(4)
    cands = [x for x in ARMS if x in res["arms"] and res["arms"][x]["rule"]["candidate"]]
    pick = None
    if cands:
        best = max(res["arms"][x]["rule"]["dcal_median"] for x in cands)
        pick = next(x for x in ARMS if x in cands and res["arms"][x]["rule"]["dcal_median"] >= best - 0.005)
    res["candidates"], res["pick"] = cands, pick
    log.info("UNG VIEN %s -> chon %s", cands, pick)
    json.dump(res, open(OUTD + "/dev%s.json" % sfx, "w"), indent=1, default=str)
    pd.concat(BROWS).to_csv(OUTD + "/batches%s.csv" % sfx, index=False)
    rows = []
    for arm in [x for x in ARMS if x in res["arms"]]:
        for s, r in res["arms"][arm]["rows"].items():
            P, b = r["period"]["DEV"], r["batch"]
            rows.append(dict(arm=arm, seed=s, cagr22_x14=r["cagr22"][0], cagr22=r["cagr22"][1], dd22_x14=r["dd_mtm22"][0], dd22=r["dd_mtm22"][1],
                             calmar22_x14=r["calmar22"][0], calmar22=r["calmar22"][1], uw22_x14=r["uw_mtm22"][0], uw22=r["uw_mtm22"][1],
                             win22_x14=r["win22"][0], win22=r["win22"][1], pnl_x14=r["sum_pnl"][0], pnl=r["sum_pnl"][1], dpnl=r["sum_pnl"][2],
                             dsim=r["dsim"]["direct"], rest=r["rest"], direct_rep=r["direct_rep"], sizing=r["sizing"],
                             n_cl_x14=P["n_cl"][0], n_cl=P["n_cl"][1], n_batch_x14=P["n_batch"][0], n_batch=P["n_batch"][1],
                             n_leg_x14=P["n_leg"][0], n_leg=P["n_leg"][1], notional_x14=P["notional"][0], notional=P["notional"][1],
                             exp_mean_x14=P["exp_mean"][0], exp_mean=P["exp_mean"][1], exp_max_x14=P["exp_max"][0], exp_max=P["exp_max"][1],
                             defer_x14=r["defer"]["n"][0], defer=r["defer"]["n"][1], locked_all_x14=r["defer"]["locked"][0]["all_mean"],
                             locked_all=r["defer"]["locked"][1]["all_mean"], locked_flag_x14=r["defer"]["locked"][0]["flag_mean"],
                             locked_flag=r["defer"]["locked"][1]["flag_mean"], locked_max_x14=r["defer"]["locked"][0]["max"],
                             locked_max=r["defer"]["locked"][1]["max"], b_drop=b["drop"]["n"], b_shrink_n=b["shrink_n"]["n"],
                             b_shrink_size=b["shrink_size"]["n"], b_bigger=b["bigger"]["n"], b_new=b["new"]["n"],
                             b_drop_pnl_x14=b["drop"]["pnl_x"], b_new_pnl=b["new"]["pnl_v"]))
    pd.DataFrame(rows).to_csv(OUTD + "/dev_rows%s.csv" % sfx, index=False)
    log.info("WROTE %s/dev%s.json", OUTD, sfx)


if __name__ == "__main__":
    main()
