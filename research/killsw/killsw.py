#!/usr/bin/env python3
"""KILLSW (PREREG_KILLSW 437d7ea9) - CHI DO, hau kiem bac 1.
Equity MTM theo gio tu chan lenh ECMEAS bucket DEV + close gio Vision; mo phong luat DD bac A0/A40/A(d1,d2).
Lam ro truoc khi chay (khong doi sau): HALT chi kich lai khi DD da tung > -d2 tu lan thoat HALT truoc (nghia 'giu 7 ngay roi ve HALF').
Usage: python3 killsw.py out.json
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ks")
EA = "/home/ubuntu/claude_master/edge_attr"
OUT = "/home/ubuntu/claude_master/killsw"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CAP = 35000.0
HMS = 3600 * 1000
G0 = int(pd.Timestamp("2021-06-30 17:00").value // 10**6) // HMS   # 2021-07-01 00:00 +07
G1 = int(pd.Timestamp("2025-12-31 17:00").value // 10**6) // HMS   # 2026-01-01 00:00 +07
W22 = int(pd.Timestamp("2021-12-31 17:00").value // 10**6) // HMS - G0
Y22a = W22
Y22b = int(pd.Timestamp("2022-12-31 17:00").value // 10**6) // HMS - G0
NH = G1 - G0
VARIANTS = {"A0": None, "A40": "stop40", "A10_20": (0.10, 0.20), "A15_25": (0.15, 0.25), "A20_30": (0.20, 0.30)}


def kp(ym):
    a = "/home/ubuntu/claude_master/gvz/k2021/kline1m-%s.parquet" % ym
    b = "/home/ubuntu/vz_e1/raw/kline1m-%s.parquet" % ym
    if ym < "2021-12" and os.path.exists(a):
        return a
    return b if os.path.exists(b) else None


def hourly_closes(syms):
    cache = OUT + "/hclose.npz"
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        return z["mat"], list(z["syms"])
    syms = sorted(syms)
    pos = {s: i for i, s in enumerate(syms)}
    mat = np.full((len(syms), NH), np.nan, np.float64)
    for ym in pd.period_range("2021-06", "2025-12", freq="M").strftime("%Y-%m"):
        p = kp(ym)
        if p is None:
            log.warning("no kline %s", ym)
            continue
        t = pq.read_table(p, columns=["ts", "sym", "close"]).to_pandas()
        t["sym"] = t["sym"].astype(str)
        t = t[t["sym"].isin(pos)]
        t["h"] = t["ts"] // HMS - G0
        t = t[(t["h"] >= 0) & (t["h"] < NH)].sort_values(["sym", "ts"], kind="mergesort")
        last = t.groupby(["sym", "h"], sort=False)["close"].last().reset_index()
        mat[last["sym"].map(pos).to_numpy(), last["h"].to_numpy()] = last["close"].to_numpy()
        log.info("hclose %s rows=%d", ym, len(last))
    # ffill toi da 24h
    df = pd.DataFrame(mat.T)
    mat = df.ffill(limit=24).to_numpy().T
    np.savez_compressed(cache, mat=mat, syms=np.array(syms, dtype=object))
    return mat, syms


def prep_seed(d, mat, pos):
    legs = []
    for r in d.itertuples(index=False):
        h0 = int(r.M // HMS - G0)
        h1 = int(r.E // HMS - G0)
        qty = r.margin / r.entry
        if h1 > h0:
            row = mat[pos[r.vs], h0:h1] if r.vs in pos else np.full(h1 - h0, np.nan)
            u = qty * (row - r.entry)
            u = np.where(np.isfinite(u), u, 0.0)
        else:
            u = np.zeros(0)
        legs.append((h0, h1, u, float(r.pnl)))
    legs.sort(key=lambda x: x[0])
    return legs


def simulate(legs, var):
    unreal = np.zeros(NH + 1)
    rdiff = np.zeros(NH + 2)
    eq = np.empty(NH)
    st = np.empty(NH, np.int8)  # 0 FULL 1 HALF 2 HALT 3 STOP
    state, halt_until, armed = 0, -1, True
    peak, racc, p = CAP, 0.0, 0
    n_half = n_halt = skipped = 0
    stopped_eq = None
    for h in range(NH):
        if stopped_eq is not None:
            eq[h], st[h] = stopped_eq, 3
            while p < len(legs) and legs[p][0] <= h:
                skipped += 1
                p += 1
            continue
        s = {0: 1.0, 1: 0.5, 2: 0.0}[state]
        while p < len(legs) and legs[p][0] <= h:
            h0, h1, u, pnl = legs[p]
            if s > 0:
                if h1 > h0:
                    unreal[h0:h1] += s * u
                rdiff[min(max(h1, h0), NH)] += s * pnl
            else:
                skipped += 1
            p += 1
        racc += rdiff[h]
        e = CAP + racc + unreal[h]
        eq[h], st[h] = e, state
        peak = max(peak, e)
        dd = e / peak - 1
        if var is None:
            continue
        if var == "stop40":
            if dd <= -0.40:
                stopped_eq = e
            continue
        d1, d2 = var
        if state == 2 and h >= halt_until:
            state = 1
        if dd > -d2:
            armed = True
        if dd <= -d2 and state != 2 and armed:
            state, halt_until, armed = 2, h + 168, False
            n_halt += 1
        elif dd <= -d1 and state == 0:
            state = 1
            n_half += 1
        elif state == 1 and dd >= -d1 / 2:
            state = 0
    return eq, st, {"n_half": n_half, "n_halt": n_halt, "skipped": skipped}


def metrics(eq, st, extra):
    w = eq[W22:]
    years = (NH - W22) / (24 * 365.25)
    pk = np.maximum.accumulate(w)
    y = eq[Y22a:Y22b]
    pky = np.maximum.accumulate(y)
    m = {"sum_pnl": float(eq[-1] - CAP), "cagr22": float(100 * ((w[-1] / w[0]) ** (1 / years) - 1)),
         "maxdd22": float(100 * (w / pk - 1).min()), "pnl_2022": float(y[-1] - y[0]), "maxdd_2022": float(100 * (y / pky - 1).min()),
         "maxdd_full": float(100 * (eq / np.maximum.accumulate(eq) - 1).min()),
         "pct_half": float(100 * (st == 1).mean()), "pct_halt": float(100 * (st == 2).mean()), "pct_stop": float(100 * (st == 3).mean())}
    m["calmar22"] = m["cagr22"] / abs(m["maxdd22"]) if m["maxdd22"] < 0 else np.nan
    m.update(extra)
    return m


def main():
    os.makedirs(OUT, exist_ok=True)
    d = pd.read_parquet(EA + "/legs.parquet")
    d = d[d.win == "D"].copy()
    t0 = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    t1 = pd.to_datetime(d.end, format="%Y%m%d %H:%M", errors="coerce")
    d = d[(t0 >= "2021-07-01") & t1.notna() & (t1 < "2026-01-01")]
    mat, syms = hourly_closes(set(d.vs))
    pos = {s: i for i, s in enumerate(syms)}
    ecm = json.load(open("/home/ubuntu/claude_master/vz_e1_wt/docs/result/RESULT_ENTRYCOST_MEASURE.json"))["runs"]["D"]["bucket"]
    res = {"prereg": "437d7ea9", "seeds": {}, "K": {}}
    for s in SEEDS:
        legs = prep_seed(d[d.seed == s], mat, pos)
        res["seeds"][str(s)] = {}
        for vn, var in VARIANTS.items():
            eq, st, ex = simulate(legs, var)
            res["seeds"][str(s)][vn] = metrics(eq, st, ex)
        b = res["seeds"][str(s)]["A0"]
        E = ecm[str(s)]
        res["K"][str(s)] = {"K1_dpnl": b["sum_pnl"] - E["spnl"], "K2_dd_hour": b["maxdd22"], "K2_dd_min": E["maxdd22"],
                            "K3_cagr_hour": b["cagr22"], "K3_cagr_ecm": E["cagr22"]}
        log.info("seed %s K %s", s, res["K"][str(s)])
    agg = {}
    for vn in VARIANTS:
        agg[vn] = {}
        for k in res["seeds"]["42"][vn]:
            v = np.array([res["seeds"][str(s)][vn][k] for s in SEEDS], float)
            agg[vn][k] = [float(np.nanmean(v)), float(np.nanstd(v, ddof=1)), float(np.nanmin(v)), float(np.nanmax(v))]
    res["agg"] = agg
    json.dump(res, open(sys.argv[1], "w"), indent=1, default=float)
    for vn, a in agg.items():
        log.info("%-7s pnl %8.0f cagr22 %5.1f+-%.1f maxdd22 %6.1f (min %6.1f) calmar %4.2f | 2022 pnl %7.0f dd %6.1f | half %4.1f%% halt %4.1f%% stop %4.1f%% nHalf %.1f nHalt %.1f skip %.0f",
                 vn, a["sum_pnl"][0], a["cagr22"][0], a["cagr22"][1], a["maxdd22"][0], a["maxdd22"][2], a["calmar22"][0],
                 a["pnl_2022"][0], a["maxdd_2022"][0], a["pct_half"][0], a["pct_halt"][0], a["pct_stop"][0], a["n_half"][0], a["n_halt"][0], a["skipped"][0])


if __name__ == "__main__":
    main()
