#!/usr/bin/env python3
"""exec_measure.py -- EXEC E2: mo phong khop vao chan (P0..P4) tu aggTrades Vision + proxy thoat qsleeve_q0 tren kline 1m Vision.
Pre-reg: docs/prereg/PREREG_EXEC.md (commit c60048d9) -- KHONG doi thiet ke/nguong/k sau commit.
Stage: sim (-> exec/sim.pkl) | report (-> docs/result/EXEC_RESULT.md + exec_result.json). 0 sim Java, 0 REST, DEV <= 2025-12-31.
"""
import glob
import json
import logging
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("exec_measure")
W = "/home/ubuntu/claude_master/1012/exec"
REPO = "/home/ubuntu/src/BinanceFuturesJava"
H, D, MN, S = 3600000, 86400000, 60000, 1000
TZ = 7 * H
T26 = 1767200400000
DEC_OFF, WIN_PRE, WIN_POST = 66000, 2 * MN, 30 * MN
COST = 0.000982 + 2 * 0.000067
PEN, CRASH = 0.01675, -0.01
ARM, GAP, STEP, TSTOP = 0.07, 0.03, 0.005, 168
EQ_LIVE = {"paper": 35000.0, "pilot": 10000.0}
POL = ("P0", "P1", "P2", "P3", "P4")
K_POL = 5
INFL = math.sqrt(2 * math.log(K_POL))
B_BOOT, SEED_BOOT = 4000, 20261012
MAKER_SAVE = 0.0003


def trail(x):
    return np.floor((x - np.minimum(x, GAP)) / STEP + 0.5) * STEP


def exit_proxy(E, i0, kt, kx):
    """luat thoat qsleeve_q0 Q4 tren nen kline [i0:], t0 = open(i0) - 60s. Tra (px, why, exit_t).
    why: time | trail | cut (cham 2026-01-01) | trunc (het du lieu kline truoc khi thoat)."""
    t0 = kt[i0] - MN
    tm, o, h, l, c = kt[i0:], kx[i0:, 0], kx[i0:, 1], kx[i0:, 2], kx[i0:, 3]
    n = len(tm)
    if n == 0:
        return np.nan, "nobar", -1
    hr = h / E - 1.0
    tsb = np.flatnonzero(tm - t0 > TSTOP * H)
    ab = np.flatnonzero(hr > ARM)
    its = int(tsb[0]) if len(tsb) else n
    ia = int(ab[0]) if len(ab) else n
    if its < n and its <= ia:
        return float(min(o[its], c[its])), "time", int(tm[its])
    endwhy = "cut" if tm[-1] + MN >= T26 else "trunc"
    if ia == n:
        return float(c[-1]), endwhy, int(tm[-1])
    sl = float(trail(hr[ia]))
    pend = bool(c[ia] <= E * (1 + sl))
    i = ia + 1
    if i >= n:
        return float(c[-1]), endwhy, int(tm[-1])
    hh = hr[i:]
    tr = np.where(hh >= ARM, trail(hh), -np.inf)
    after = np.maximum.accumulate(np.maximum(tr, sl))
    before = np.concatenate(([sl], after[:-1]))
    reset = after > before
    pb = np.concatenate(([pend], (reset & (c[i:] <= E * (1 + after)))[:-1]))
    ex = (l[i:] <= E * (1 + before)) | pb
    k = np.flatnonzero(ex)
    if len(k):
        k = int(k[0])
        return float(min(E * (1 + before[k]), o[i + k])), "trail", int(tm[i + k])
    return float(c[-1]), endwhy, int(tm[-1])


def fill_market(t0, Q, at, ap, aq, am):
    """P0/P4: walk taker MUA tu t0 (3s, noi 30s). Tra dict(E, t_fill, flag, pmax3) hoac None (khong trade 30s)."""
    i0 = np.searchsorted(at, t0, "left")
    i30 = np.searchsorted(at, t0 + 30 * S, "right")
    if i30 <= i0:
        return None
    i3 = np.searchsorted(at, t0 + 3 * S, "right")
    b3 = np.flatnonzero(~am[i0:i3]) + i0
    pmax3 = float(ap[b3].max()) if len(b3) else np.nan
    flag = "ok"
    idx = b3
    if aq[b3].sum() < Q:
        idx = np.flatnonzero(~am[i0:i30]) + i0
        flag = "thin"
    if len(idx) == 0:
        return dict(E=float(ap[i0]), t_fill=int(at[i0]), flag="noask", pmax3=pmax3)
    cq = np.cumsum(aq[idx])
    k = int(np.searchsorted(cq, Q, "left"))
    if k >= len(idx):                      # 30s van thieu: phan con lai gia = print cao nhat da thay
        flag = "short"
        tot = float((ap[idx] * aq[idx]).sum()) + (Q - float(cq[-1])) * float(ap[idx].max())
        return dict(E=tot / Q, t_fill=int(at[idx[-1]]), flag=flag, pmax3=pmax3)
    prev = float(cq[k - 1]) if k > 0 else 0.0
    tot = float((ap[idx[:k]] * aq[idx[:k]]).sum()) + (Q - prev) * float(ap[idx[k]])
    return dict(E=tot / Q, t_fill=int(at[idx[k]]), flag=flag, pmax3=pmax3)


def fill_limit(t0, L, Q, hold, at, ap, aq, am, eq_ok=False):
    """1 nac limit gia L, qty Q, dat t0, giu hold ms. Tra (q_khop, gia_TB, t_khop_cuoi, q_taker)."""
    i0 = np.searchsorted(at, t0, "left")
    i3 = np.searchsorted(at, t0 + 3 * S, "right")
    qt, vt, tl = 0.0, 0.0, -1
    for j in np.flatnonzero(~am[i0:i3]) + i0:      # marketable luc dat
        if ap[j] > L or qt >= Q:
            break
        take = min(float(aq[j]), Q - qt)
        qt += take
        vt += take * float(ap[j])
        tl = int(at[j])
    rest = Q - qt
    qm = 0.0
    if rest > 1e-15:
        i1 = np.searchsorted(at, t0, "right")
        ih = np.searchsorted(at, t0 + hold, "right")
        thr = (ap[i1:ih] <= L) if eq_ok else (ap[i1:ih] < L)
        sel = np.flatnonzero(am[i1:ih] & thr) + i1
        if len(sel):
            cq = np.cumsum(aq[sel])
            k = int(np.searchsorted(cq, rest, "left"))
            qm = rest if k < len(sel) else float(cq[-1])
            tl = max(tl, int(at[sel[min(k, len(sel) - 1)]]))
    qf = qt + qm
    return qf, ((vt + qm * L) / qf if qf > 0 else np.nan), tl, qt


def load_npz(pattern, keys):
    fs = sorted(glob.glob(pattern))
    if not fs:
        return None
    Z = [np.load(f) for f in fs]
    out = {k: np.concatenate([z[k] for z in Z]) for k in keys}
    o = np.argsort(out["t"], kind="stable")
    return {k: v[o] for k, v in out.items()}


def v1_check(ev, at, ap, aq, kt, kx):
    """V1: phut tron trong cua so: OHLC aggTrades == kline va |sum qty - vol| <= 1e-6 vol + 1e-9."""
    mins = set()
    for s in ev["s_ms"]:
        a, b = s + DEC_OFF - WIN_PRE, s + DEC_OFF + WIN_POST
        m0 = -(-a // MN) * MN
        mins.update(range(int(m0), int(b + 1 - MN) + 1, MN))
    mins = np.array(sorted(mins), np.int64)
    ik = np.searchsorted(kt, mins)
    has_k = (ik < len(kt)) & (kt[np.minimum(ik, len(kt) - 1)] == mins)
    r = dict(n_min=int(len(mins)), n_kl=int(has_k.sum()), match=0, bad_ohlc=0, bad_vol=0, kv0_notr=0, tr_nokl=0)
    tm = at // MN * MN
    df = pd.DataFrame(dict(m=tm, p=ap, q=aq))
    df = df[np.isin(tm, mins)]
    g = df.groupby("m").agg(o=("p", "first"), h=("p", "max"), l=("p", "min"), c=("p", "last"), v=("q", "sum"))
    for m, k, hk in zip(mins, ik, has_k):
        if not hk:
            r["tr_nokl"] += int(m in g.index)
            continue
        o, h, l, c, v = kx[k]
        if m not in g.index:
            ok = v == 0
            r["kv0_notr"] += int(ok)
            r["match"] += int(ok)
            r["bad_vol"] += int(not ok)
            continue
        x = g.loc[m]
        okp = (x.o == o) and (x.h == h) and (x.l == l) and (x.c == c)
        okv = abs(x.v - v) <= 1e-6 * v + 1e-9
        r["match"] += int(okp and okv)
        r["bad_ohlc"] += int(not okp)
        r["bad_vol"] += int(okp and not okv)
    return r


def run_sym(arg):
    sym, ev, legs = arg
    K = load_npz(W + "/kl/%sUSDT_*.npz" % sym, ("t", "x"))
    A = load_npz(W + "/agg/%sUSDT_*.npz" % sym, ("t", "p", "q", "m"))
    EV, R, CAL = [], [], []
    if K is None:
        for e in ev.itertuples():
            EV.append(dict(eid=e.eid, st="nokl"))
        return sym, EV, R, CAL, None
    kt, kx = K["t"], K["x"]
    if A is None:
        A = dict(t=np.zeros(0, np.int64), p=np.zeros(0), q=np.zeros(0), m=np.zeros(0, bool))
    at, ap, aq, am = A["t"], A["p"], A["q"], A["m"]
    v1 = v1_check(ev, at, ap, aq, kt, kx) if len(at) else None
    lg = legs.groupby("eid")
    for e in ev.itertuples():
        s = int(e.s_ms)
        td = s + DEC_OFF
        im = int(np.searchsorted(kt, s))
        if im >= len(kt) or kt[im] != s:
            EV.append(dict(eid=e.eid, st="nobarM"))
            continue
        oM, cM = float(kx[im, 0]), float(kx[im, 3])
        ntr = int(np.searchsorted(at, td + 30 * S, "right") - np.searchsorted(at, td, "left"))
        rec = dict(eid=e.eid, st="ok" if ntr > 0 else "notrade", oM=oM, cM=cM, br=cM / oM - 1.0, ntr30=ntr)
        EV.append(rec)
        if ntr == 0:
            continue
        iend = int(np.searchsorted(kt, min(T26 - 1, s + 169 * H + 31 * MN), "right"))
        kts, kxs = kt[:iend], kx[:iend]
        # P4: nen xanh dau tien M+1.. mo <= s+28'
        j = im + 1
        tg = None
        while j < iend and kt[j] <= s + 28 * MN:
            if kx[j, 3] > kx[j, 0]:
                tg = int(kt[j]) + DEC_OFF
                break
            j += 1
        cache = {}

        def ex(E, tf):
            i0 = int(np.searchsorted(kts, tf // MN * MN))
            key = (i0, round(E, 12))
            if key not in cache:
                cache[key] = exit_proxy(E, i0, kts, kxs)
            return cache[key]
        R.extend(sim_legs(e, lg.get_group(e.eid), cM, td, tg, at, ap, aq, am, ex))
        for x in lg.get_group(e.eid).itertuples():
            if x.leg0 and x.nleg == 1:
                px, why, et = exit_proxy(float(x.entry), im + 1, kts, kxs)
                CAL.append(dict(seed=x.seed, row=x.row, gross=px / x.entry - 1, real=x.profit / 100.0, why=why,
                                same_exit=(et == x.e_ms), ent_ok=abs(x.entry / (cM * (1 + PEN * (cM / oM - 1 <= CRASH))) - 1) < 1e-6))
    return sym, EV, R, CAL, v1


def ladder(td, cM, Q, at, ap, aq, am, levels, hold, eq_ok):
    qf = vt = qtk = 0.0
    tl = -1
    for f in levels:
        q1, e1, t1, k1 = fill_limit(td, cM * f, Q / len(levels), hold, at, ap, aq, am, eq_ok)
        if q1 > 0:
            qf += q1
            vt += q1 * e1
            qtk += k1
            tl = max(tl, t1)
    return qf, (vt / qf if qf > 0 else np.nan), tl, qtk


def sim_legs(e, g, cM, td, tg, at, ap, aq, am, ex):
    out = []
    spec = (("P1", (1.0,), 60 * S), ("P2", (0.997,), 300 * S), ("P3", (1.0, 0.995, 0.99), 300 * S))
    for x in g.itertuples():
        for sz, eq in EQ_LIVE.items():
            N = float(x.size_ratio) * eq
            Q = N / cM
            res = {}
            fm = fill_market(td, Q, at, ap, aq, am)
            res["P0"] = (1.0, fm["E"], fm["t_fill"], fm["flag"], 0.0, fm["pmax3"])
            for nm, lv, hold in spec:
                for opt in (False, True):
                    qf, E, tl, qtk = ladder(td, cM, Q, at, ap, aq, am, lv, hold, opt)
                    res[nm + ("o" if opt else "")] = (qf / Q, E, tl, "lim", (qf - qtk) / Q, np.nan)
            f4 = fill_market(tg, Q, at, ap, aq, am) if tg is not None else None
            res["P4"] = ((1.0, f4["E"], f4["t_fill"], f4["flag"], 0.0, np.nan) if f4 is not None
                         else (0.0, np.nan, -1, "nogreen" if tg is None else "nodata", 0.0, np.nan))
            for pol, (fr, E, tf, flag, fmk, pm) in res.items():
                if fr > 1e-12:
                    px, why, et = ex(E, tf)
                    pnl = N * fr * (px / E - 1 - COST)
                else:
                    px, why, et, pnl = np.nan, "nofill", -1, 0.0
                out.append((x.seed, x.row, e.eid, sz, pol, fr, E, (E / cM - 1) * 1e4 if fr > 0 else np.nan, tf, flag,
                            px, why, et, pnl, pnl + N * fmk * MAKER_SAVE, (pm / cM - 1) * 1e4, N))
    return out


RCOLS = ("seed", "row", "eid", "size", "pol", "frac", "E", "cost_bps", "t_fill", "flag", "px", "why", "exit_t", "pnl",
         "pnl_mk", "pmax3_bps", "N")


def stage_sim(workers=3):
    d = pd.read_pickle(W + "/legs.pkl")
    L, ev = d["L"], d["ev"]
    args = [(sym, ev[ev["sym"] == sym], L[L["sym"] == sym]) for sym in sorted(ev["sym"].unique())]
    t0 = time.time()
    EV, R, CAL, V1 = [], [], [], {}
    with Pool(workers) as pool:
        for i, (sym, e1, r1, c1, v1) in enumerate(pool.imap_unordered(run_sym, args, chunksize=2)):
            EV += e1
            R += r1
            CAL += c1
            V1[sym] = v1
            if i % 50 == 0:
                log.info("SIM %d/%d sym %s %.0fs, rec %d", i, len(args), sym, time.time() - t0, len(R))
    EVd = ev.merge(pd.DataFrame(EV), on="eid", how="left")
    Rd = pd.DataFrame(R, columns=RCOLS)
    pd.to_pickle(dict(EV=EVd, R=Rd, CAL=pd.DataFrame(CAL), V1=V1), W + "/sim.pkl")
    log.info("SIM xong %.0fs: su kien %s, ban ghi %d", time.time() - t0, EVd["st"].value_counts().to_dict(), len(Rd))


# ---------------------------------------------------------------- report
def episodes(days):
    u = np.array(sorted(set(days)))
    gid = np.concatenate(([0], np.cumsum(np.diff(u) - 1 >= 3)))
    return dict(zip(u, gid)), int(gid[-1] + 1)


def boot(vals_by_ep, rng, stat=np.sum):
    """vals_by_ep: mang [n_ep]; tra sd bootstrap cua stat theo dot."""
    n = len(vals_by_ep)
    idx = rng.integers(0, n, size=(B_BOOT, n))
    return float(np.std(stat(vals_by_ep[idx], axis=1), ddof=1))


def ratio_ci(num, den, rng):
    """CI95 percentile cho sum(num)/sum(den), bootstrap theo dot (num/den da gom theo dot)."""
    n = len(num)
    idx = rng.integers(0, n, size=(B_BOOT, n))
    r = num[idx].sum(1) / np.maximum(den[idx].sum(1), 1e-12)
    return float(num.sum() / den.sum()), float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def bucket(br):
    return np.select([br > -0.01, br > -0.02, br > -0.04], ["khong_sap", "-1..-2", "-2..-4"], "<-4")


def maxdd(eq):
    pk = np.maximum.accumulate(eq)
    return float(((eq / pk) - 1).min() * 100)


def stage_report():
    rng = np.random.default_rng(SEED_BOOT)
    sm = pd.read_pickle(W + "/sim.pkl")
    L = pd.read_pickle(W + "/legs.pkl")["L"]
    EV, R, CAL, V1 = sm["EV"], sm["R"], sm["CAL"], sm["V1"]
    js = dict(prereg="c60048d9", k=K_POL, inflate=INFL)
    L = L.merge(EV[["eid", "st", "oM", "cM", "br"]], on="eid", how="left")
    L["year"] = pd.to_datetime(L["s_ms"] + TZ, unit="ms").dt.year
    L["day"] = (L["s_ms"] + TZ) // D
    # phu + V1..V3
    js["cov"] = dict(events=EV["st"].value_counts(dropna=False).to_dict(), legs=L["st"].value_counts(dropna=False).to_dict(),
                     n_events=int(len(EV)), n_legs=int(len(L)))
    v = [x for x in V1.values() if x]
    js["V1"] = {k: int(sum(x[k] for x in v)) for k in v[0]}
    js["V1"]["rate"] = js["V1"]["match"] / max(1, js["V1"]["n_kl"])
    hb = L["st"].isin(["ok", "notrade"])
    exp = L["cM"] * (1 + PEN * (L["br"] <= CRASH))
    ok2 = (np.abs(L["entry"] / exp - 1) < 1e-6) & hb
    js["V2"] = dict(n=int(hb.sum()), ok=int(ok2.sum()), rate=float(ok2.sum() / hb.sum()),
                    crash_share=float((L.loc[hb, "br"] <= CRASH).mean()))
    js["V3"] = dict(n=int(len(CAL)), pearson=float(np.corrcoef(CAL["gross"], CAL["real"])[0, 1]),
                    bias_pp=float(100 * (CAL["gross"] - CAL["real"]).mean()), same_exit=float(CAL["same_exit"].mean()),
                    ent_ok=float(CAL["ent_ok"].mean()))
    A = L[L["st"] == "ok"].copy()
    R = R.merge(A[["seed", "row", "year", "day", "br", "nleg", "level"]], on=["seed", "row"], how="inner")
    R["bk"] = bucket(R["br"].to_numpy())
    emap, nep = episodes(A["day"])
    R["ep"] = R["day"].map(emap)
    R["xday"] = np.where(R["exit_t"] > 0, (R["exit_t"] + TZ) // D, -1)
    js["episodes"] = nep
    js["flags_P0"] = R[(R["pol"] == "P0") & (R["size"] == "paper")]["flag"].value_counts().to_dict()
    js["flags_P4"] = R[(R["pol"] == "P4") & (R["size"] == "paper")]["flag"].value_counts().to_dict()
    js["why"] = R[R["size"] == "paper"].groupby("pol")["why"].value_counts().unstack(fill_value=0).to_dict("index")
    lim = R[R["pol"].isin(["P1", "P2", "P3", "P1o", "P2o", "P3o"]) & (R["frac"] > 0)]
    thr = lim["pol"].str[:2].map({"P1": 1e-6, "P2": -30 + 1e-6, "P3": 1e-6})
    w = R.pivot_table(index=["seed", "row", "size"], columns="pol", values="frac")
    js["V5"] = dict(lim_E_le_L=bool((lim["cost_bps"] <= thr).all()),
                    cons_le_opt=bool(all((w[p] <= w[p + "o"] + 1e-12).all() for p in ("P1", "P2", "P3"))))
    js.update(report_tables(R, A, nep, rng))
    with open(REPO + "/docs/result/exec_result.json", "w") as f:
        json.dump(js, f, indent=1, default=float)
    log.info("REPORT json xong: V1 %.5f V2 %.4f V3 %.3f cov %s", js["V1"]["rate"], js["V2"]["rate"], js["V3"]["pearson"],
             js["cov"]["events"])


def report_tables(R, A, nep, rng):
    NS = 8.0
    out = dict(main={}, slices={}, calib={}, daily={}, impact={})
    pols = ("P0", "P1", "P2", "P3", "P4", "P1o", "P2o", "P3o")
    for sz in EQ_LIVE:
        X = R[R["size"] == sz]
        P = X.pivot_table(index=["seed", "row"], columns="pol", values="pnl", aggfunc="first")
        PM = X.pivot_table(index=["seed", "row"], columns="pol", values="pnl_mk", aggfunc="first")
        meta = X[X["pol"] == "P0"].set_index(["seed", "row"])[["ep", "year", "bk", "nleg"]].loc[P.index]
        ep = meta["ep"].to_numpy()
        tab = {}
        for p in pols:
            Y = X[X["pol"] == p]
            fl = Y[Y["frac"] > 0]
            pe = np.bincount(ep, weights=P[p].to_numpy(), minlength=nep) / NS
            r = dict(fill=float(Y["frac"].mean()), cost_mean=float(np.average(fl["cost_bps"], weights=fl["frac"])),
                     cost_med=float(fl["cost_bps"].median()), pnl=float(P[p].sum() / NS), n_pos=int((pe > 0).sum()),
                     pnl_mk=float(PM[p].sum() / NS))
            if p == "P0":
                r["pmax3_mean"] = float(Y["pmax3_bps"].mean())
            else:
                dl = (P[p] - P["P0"]).to_numpy()
                de = np.bincount(ep, weights=dl, minlength=nep) / NS
                sd = boot(de, rng)
                Sx = float(de.sum())
                r.update(dS=Sx, sd=sd, lo=Sx - INFL * 1.96 * sd, hi=Sx + INFL * 1.96 * sd, lo_raw=Sx - 1.96 * sd,
                         hi_raw=Sx + 1.96 * sd, d_pos_ep=float((de > 0).mean()),
                         dS_mk=float((PM[p] - PM["P0"]).sum() / NS),
                         dS_nodca=float(dl[meta["nleg"].to_numpy() == 1].sum() / NS))
                r["dS_year"] = {int(y): float(dl[meta["year"].to_numpy() == y].sum() / NS) for y in (2022, 2023, 2024, 2025)}
                r["dS_bk"] = {b: float(dl[meta["bk"].to_numpy() == b].sum() / NS) for b in ("khong_sap", "-1..-2", "-2..-4", "<-4")}
            tab[p] = r
        n0 = tab["P0"]["n_pos"]
        for p in ("P1", "P2", "P3", "P4"):
            t = tab[p]
            t["go"] = bool(sz == "paper" and t["lo"] > 0 and t["n_pos"] >= 0.9 * n0)
            t["sign_ok"] = t["dS"] > 0
        out["main"][sz] = tab
        sl = {}
        for (y, b), g in X.groupby(["year", "bk"]):
            e = {}
            for p in ("P0", "P1", "P2", "P3", "P4"):
                q = g[g["pol"] == p]
                f = q[q["frac"] > 0]
                e[p] = dict(n=int(len(q)), fill=float(q["frac"].mean()),
                            cost=float(np.average(f["cost_bps"], weights=f["frac"])) if len(f) else None,
                            pnl=float(q["pnl"].sum() / NS))
            sl["%d|%s" % (y, b)] = e
        out["slices"][sz] = sl
        out["daily"][sz] = daily(X, nep, EQ_LIVE[sz])
        # HAU KIEM mo ta (khong pre-reg, khong dung cho GO): adverse selection = PnL P0 cua chan limit khop vs khong khop
        fr = X.pivot_table(index=["seed", "row"], columns="pol", values="frac", aggfunc="first").loc[P.index]
        nn = (X[X["pol"] == "P0"].set_index(["seed", "row"])["N"]).loc[P.index]
        out.setdefault("adverse", {})[sz] = {p: dict(
            n_fill=int((fr[p] >= 0.999).sum()), n_none=int((fr[p] == 0).sum()),
            p0_ret_fill=float(100 * (P["P0"][fr[p] >= 0.999] / nn[fr[p] >= 0.999]).mean()),
            p0_ret_none=float(100 * (P["P0"][fr[p] == 0] / nn[fr[p] == 0]).mean()),
            pol_ret_fill=float(100 * (P[p][fr[p] >= 0.999] / nn[fr[p] >= 0.999]).mean()),
            p0_pnl_none=float(P["P0"][fr[p] == 0].sum() / NS)) for p in ("P1", "P2", "P3")}
    out["calib"] = calib_pen(R[(R["size"] == "paper") & (R["pol"] == "P0")], nep, rng)
    out["impact"] = impact(A, R)
    return out


def daily(X, nep, eq0):
    NS = 8.0
    out = {}
    base = None
    for p in ("P0", "P1", "P2", "P3", "P4"):
        Y = X[(X["pol"] == p) & (X["xday"] > 0)]
        s = Y.groupby("xday")["pnl"].sum() / NS
        if base is None:
            base = s
        u = s.index.union(base.index)
        dd = s.reindex(u, fill_value=0) - base.reindex(u, fill_value=0)
        eq = eq0 + s.sort_index().cumsum().to_numpy()
        yr = pd.Series(s.values, index=pd.to_datetime(s.index * D, unit="ms").year).groupby(level=0).sum()
        out[p] = dict(maxdd_closed=maxdd(eq), roi_simple={int(k): float(100.0 * v / eq0) for k, v in yr.items()},
                      days_dpos=float((dd > 1e-9).mean()), days_dneg=float((dd < -1e-9).mean()))
    return out


def calib_pen(Y, nep, rng):
    out = {}
    grp = {"sap": Y["br"] <= CRASH, "khong_sap": Y["br"] > CRASH}
    for b in ("-1..-2", "-2..-4", "<-4"):
        grp[b] = Y["bk"] == b
    for nm, m in grp.items():
        Z = Y[m]
        ep = Z["ep"].to_numpy()
        num = np.bincount(ep, weights=Z["cost_bps"].to_numpy(), minlength=nep)
        den = np.bincount(ep, minlength=nep).astype(float)
        num2 = np.bincount(ep, weights=Z["pmax3_bps"].fillna(0).to_numpy(), minlength=nep)
        mu, lo, hi = ratio_ci(num, den, rng)
        out[nm] = dict(n=int(len(Z)), n_ep=int((den > 0).sum()), mean=mu, lo=lo, hi=hi, med=float(Z["cost_bps"].median()),
                       p90=float(Z["cost_bps"].quantile(0.9)), pmax3_mean=float(num2.sum() / den.sum()))
    c = out["sap"]
    out["verdict"] = "DUNG" if c["lo"] <= 167.5 <= c["hi"] else ("THUA" if c["hi"] < 167.5 else "THIEU")
    return out


def impact(A, R):
    NS = 8.0
    c = R[(R["size"] == "paper") & (R["pol"] == "P0")][["seed", "row", "cost_bps"]]
    Z = A.merge(c, on=["seed", "row"], how="inner")
    cr = Z["br"] <= CRASH
    pen = (Z["margin"] * PEN * cr).sum() / NS
    real_cr = (Z["margin"] * Z["cost_bps"] / 1e4 * cr).sum() / NS
    real_nc = (Z["margin"] * Z["cost_bps"] / 1e4 * ~cr).sum() / NS
    by = {int(y): dict(pen=float((g["margin"] * PEN * (g["br"] <= CRASH)).sum() / NS),
                       real=float((g["margin"] * g["cost_bps"] / 1e4).sum() / NS), pnl_stress=float(g["pnl"].sum() / NS))
          for y, g in Z.groupby("year")}
    return dict(pen_usd=float(pen), p0_crash_usd=float(real_cr), p0_noncrash_usd=float(real_nc),
                pnl_stress_usd=float(Z["pnl"].sum() / NS), n=int(len(Z)), by_year=by)


def main():
    st = sys.argv[1]
    if st == "sim":
        stage_sim(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif st == "report":
        stage_report()
    elif st == "test":                      # chay thu 1 sym, khong ghi
        d = pd.read_pickle(W + "/legs.pkl")
        L, ev = d["L"], d["ev"]
        sym = sys.argv[2]
        r = run_sym((sym, ev[ev["sym"] == sym], L[L["sym"] == sym]))
        R = pd.DataFrame(r[2], columns=RCOLS)
        log.info("TEST %s: ev %s v1 %s cal %d", sym, pd.DataFrame(r[1])["st"].value_counts().to_dict(), r[4], len(r[3]))
        log.info("\n%s", R[R["size"] == "paper"].groupby("pol")[["frac", "cost_bps", "pnl"]].mean().to_string())
        if r[3]:
            C = pd.DataFrame(r[3])
            log.info("CAL pearson %.4f same_exit %.3f ent_ok %.3f", np.corrcoef(C["gross"], C["real"])[0, 1],
                     C["same_exit"].mean(), C["ent_ok"].mean())


if __name__ == "__main__":
    main()
