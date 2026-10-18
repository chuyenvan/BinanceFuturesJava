#!/usr/bin/env python3
"""KILLSW ban PHUT (PREREG_KILLSW 437d7ea9 + ADDENDUM 1) - CHI DO, hau kiem bac 1.
Equity MTM theo phut tu chan lenh ECMEAS bucket DEV + close kline1m Vision (ffill <= 60 phut, dau chan thieu => entry).
Trang thai cap nhat moi phut; lenh co phut vao > phut chuyen trang thai nhan size moi. HALT 10080 phut, chi kich lai khi DD
da tung > -d2 sau lan thoat HALT truoc. Mo phong theo su kien: tinh lai equity vector hoa sau moi lan chuyen trang thai.
Usage: python3 killsw_m.py out.json
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ksm")
EA = "/home/ubuntu/claude_master/edge_attr"
OUT = "/home/ubuntu/claude_master/killsw"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CAP = 35000.0
MS = 60000
G0 = int(pd.Timestamp("2021-06-30 17:00").value // 10**6) // MS
G1 = int(pd.Timestamp("2025-12-31 17:00").value // 10**6) // MS
NM = G1 - G0
W22 = int(pd.Timestamp("2021-12-31 17:00").value // 10**6) // MS - G0
Y22b = int(pd.Timestamp("2022-12-31 17:00").value // 10**6) // MS - G0
HALT_MIN = 10080
VARIANTS = {"A0": None, "A40": "stop40", "A10_20": (0.10, 0.20), "A15_25": (0.15, 0.25), "A20_30": (0.20, 0.30)}


def kp(ym):
    a = "/home/ubuntu/claude_master/gvz/k2021/kline1m-%s.parquet" % ym
    b = "/home/ubuntu/vz_e1/raw/kline1m-%s.parquet" % ym
    if ym < "2021-12" and os.path.exists(a):
        return a
    return b if os.path.exists(b) else None


def leg_closes(u):
    """u: DataFrame cac chan duy nhat (vs, m0, m1). Tra dict key->float32 close theo phut [m0, m1)."""
    arrs = {k: np.full(max(m1 - m0, 0), np.nan, np.float32) for k, m0, m1 in zip(u.key, u.m0, u.m1)}
    for ym in pd.period_range("2021-06", "2025-12", freq="M").strftime("%Y-%m"):
        p = kp(ym)
        if p is None:
            log.warning("no kline %s", ym)
            continue
        a0 = int(pd.Timestamp(ym + "-01").value // 10**6) // MS - G0
        a1 = int((pd.Timestamp(ym + "-01") + pd.offsets.MonthBegin(1)).value // 10**6) // MS - G0
        live = u[(u.m0 < a1) & (u.m1 > a0)]
        if live.empty:
            continue
        t = pq.read_table(p, columns=["ts", "sym", "close"]).to_pandas()
        t["sym"] = t["sym"].astype(str)
        t = t[t["sym"].isin(set(live.vs))].sort_values(["sym", "ts"], kind="mergesort")
        g = {s: (x["ts"].to_numpy(np.int64) // MS - G0, x["close"].to_numpy(np.float32)) for s, x in t.groupby("sym", sort=False)}
        for k, vs, m0, m1 in zip(live.key, live.vs, live.m0, live.m1):
            if vs not in g:
                continue
            mi, cl = g[vs]
            lo, hi = np.searchsorted(mi, max(m0, a0)), np.searchsorted(mi, min(m1, a1))
            arrs[k][mi[lo:hi] - m0] = cl[lo:hi]
        log.info("closes %s live=%d", ym, len(live))
    return arrs


def ffill60(a, fill):
    s = pd.Series(a).ffill(limit=60)
    s = s.fillna(fill)
    return s.to_numpy(np.float64)


class Seed:
    def __init__(self, d, arrs):
        d = d.sort_values("m0")
        self.m0 = d.m0.to_numpy()
        self.m1 = d.m1.to_numpy()
        self.pnl = d.pnl.to_numpy(float)
        self.u = []
        for k, e, mg in zip(d.key, d.entry, d.margin):
            c = ffill60(arrs[k], e) if len(arrs[k]) else np.zeros(0)
            self.u.append((mg / e) * (c - e))

    def equity(self, sc):
        U = np.zeros(NM + 1)
        R = np.zeros(NM + 2)
        for i in np.nonzero(sc)[0]:
            if self.m1[i] > self.m0[i]:
                U[self.m0[i]:self.m1[i]] += sc[i] * self.u[i]
            R[self.m1[i]] += sc[i] * self.pnl[i]
        return CAP + np.cumsum(R)[:NM] + U[:NM]


def first(cond, start):
    if start >= len(cond):
        return None
    idx = np.flatnonzero(cond[start:])
    return int(start + idx[0]) if len(idx) else None


def simulate(S, var):
    n = len(S.m0)
    sc = np.ones(n)
    st = np.zeros(NM, np.int8)
    ex = {"n_half": 0, "n_halt": 0}
    eq = S.equity(sc)
    if var is None:
        return eq, st, sc, ex
    if var == "stop40":
        dd = eq / np.maximum.accumulate(eq) - 1
        t = first(dd <= -0.40, 0)
        if t is not None:
            sc[S.m0 > t] = 0
            eq = S.equity(sc)
            eq[t:] = eq[t]
            st[t:] = 3
        return eq, st, sc, ex
    d1, d2 = var
    state, t, te, halt_end = 0, 0, 0, None
    while True:
        eq = S.equity(sc)
        dd = eq / np.maximum.accumulate(eq) - 1
        armed_from = first(dd > -d2, te)
        armed_from = NM if armed_from is None else armed_from
        if state == 2:
            nxt, new = halt_end, 1
            if nxt >= NM:
                st[t:] = 2
                break
        else:
            c_halt = first(dd <= -d2, max(t, armed_from))
            c_other = first(dd <= -d1, t) if state == 0 else first(dd >= -d1 / 2, t)
            cands = [(c, s) for c, s in ((c_halt, 2), (c_other, 1 if state == 0 else 0)) if c is not None]
            if not cands:
                st[t:] = state
                break
            nxt, new = min(cands, key=lambda x: (x[0], -x[1]))
        st[t:nxt + 1] = state
        if new == 2:
            ex["n_halt"] += 1
            halt_end = nxt + HALT_MIN
        elif new == 1 and state == 0:
            ex["n_half"] += 1
        if state == 2:
            te = nxt
        sc[S.m0 > nxt] = {0: 1.0, 1: 0.5, 2: 0.0}[new]
        state, t = new, nxt + 1
        if t >= NM:
            break
    eq = S.equity(sc)
    return eq, st, sc, ex


def metrics(eq, st, sc, ex):
    w = eq[W22:]
    years = (NM - W22) / (1440 * 365.25)
    y = eq[W22:Y22b]
    m = {"sum_pnl": float(eq[-1] - CAP), "cagr22": float(100 * ((w[-1] / w[0]) ** (1 / years) - 1)),
         "maxdd22": float(100 * (w / np.maximum.accumulate(w) - 1).min()), "pnl_2022": float(y[-1] - y[0]),
         "maxdd_2022": float(100 * (y / np.maximum.accumulate(y) - 1).min()),
         "maxdd_full": float(100 * (eq / np.maximum.accumulate(eq) - 1).min()),
         "pct_half": float(100 * (st == 1).mean()), "pct_halt": float(100 * (st == 2).mean()), "pct_stop": float(100 * (st == 3).mean()),
         "skipped": int((sc == 0).sum()), "half_legs": int((sc == 0.5).sum())}
    m["calmar22"] = m["cagr22"] / abs(m["maxdd22"]) if m["maxdd22"] < 0 else float("nan")
    m.update(ex)
    return m


def main():
    os.makedirs(OUT, exist_ok=True)
    d = pd.read_parquet(EA + "/legs.parquet")
    d = d[d.win == "D"].copy()
    t0 = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    t1 = pd.to_datetime(d.end, format="%Y%m%d %H:%M", errors="coerce")
    d = d[(t0 >= "2021-07-01") & t1.notna() & (t1 < "2026-01-01")].copy()
    d["m0"] = (d.M // MS - G0).astype(np.int64)
    d["m1"] = (d.E // MS - G0).astype(np.int64)
    d["key"] = d.vs + "|" + d.m0.astype(str) + "|" + d.m1.astype(str)
    u = d.drop_duplicates("key")[["key", "vs", "m0", "m1"]]
    log.info("legs %d unique %d NM %d", len(d), len(u), NM)
    arrs = leg_closes(u)
    cover = np.mean([np.isfinite(a).mean() if len(a) else 1.0 for a in arrs.values()])
    ecm = json.load(open("/home/ubuntu/claude_master/vz_e1_wt/docs/result/RESULT_ENTRYCOST_MEASURE.json"))["runs"]["D"]["bucket"]
    res = {"prereg": "437d7ea9+addendum1", "close_coverage_mean": float(cover), "seeds": {}, "K": {}}
    for s in SEEDS:
        S = Seed(d[d.seed == s], arrs)
        res["seeds"][str(s)] = {}
        for vn, var in VARIANTS.items():
            res["seeds"][str(s)][vn] = metrics(*simulate(S, var))
        b, E = res["seeds"][str(s)]["A0"], ecm[str(s)]
        res["K"][str(s)] = {"K1_dpnl": b["sum_pnl"] - E["spnl"], "K2_dd_min": b["maxdd22"], "K2_dd_ecm": E["maxdd22"],
                            "K3_cagr": b["cagr22"], "K3_cagr_ecm": E["cagr22"]}
        log.info("seed %s K %s", s, res["K"][str(s)])
    K = res["K"].values()
    res["K_pass"] = {"K1": all(abs(k["K1_dpnl"]) <= 1 for k in K), "K2": all(abs(k["K2_dd_min"] - k["K2_dd_ecm"]) <= 2.0 for k in K),
                     "K3": all(abs(k["K3_cagr"] - k["K3_cagr_ecm"]) <= 2.0 for k in K)}
    log.info("K_pass %s coverage %.4f", res["K_pass"], cover)
    agg = {}
    for vn in VARIANTS:
        agg[vn] = {k: [float(np.nanmean(v)), float(np.nanstd(v, ddof=1)), float(np.nanmin(v)), float(np.nanmax(v))]
                   for k in res["seeds"]["42"][vn]
                   for v in [np.array([res["seeds"][str(s)][vn][k] for s in SEEDS], float)]}
    res["agg"] = agg
    json.dump(res, open(sys.argv[1], "w"), indent=1, default=float)
    if not all(res["K_pass"].values()):
        log.info("KIEM HOP LE FAIL -> khong in bang bien the")
        return
    for vn, a in agg.items():
        log.info("%-7s pnl %8.0f cagr22 %5.1f+-%.1f maxdd22 %6.1f (worst %6.1f) calmar %4.2f | 2022 pnl %7.0f dd %6.1f | half %4.1f%% halt %4.1f%% stop %4.1f%% nHalf %.1f nHalt %.1f skip %.0f halfLegs %.0f",
                 vn, a["sum_pnl"][0], a["cagr22"][0], a["cagr22"][1], a["maxdd22"][0], a["maxdd22"][2], a["calmar22"][0],
                 a["pnl_2022"][0], a["maxdd_2022"][0], a["pct_half"][0], a["pct_halt"][0], a["pct_stop"][0], a["n_half"][0],
                 a["n_halt"][0], a["skipped"][0], a["half_legs"][0])


if __name__ == "__main__":
    main()
