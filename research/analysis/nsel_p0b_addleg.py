#!/usr/bin/env python3
"""NSEL_P0B (2026-10-08): kha thi co che "LOI cong don" -- K4 SO CO SAN (chi bao cao, in-sample, KHONG chon nguong).

0 sim, 0 Kaggle, 0 Java, 0 cham 242/shadow. Doc printDone arm D (K32, pct 0,999915; 3 seed) + bang MAT cua agent data
(~/claude_master/1008/nsel/j3_mat_rows.csv.gz, chi doc) + nen 1m /home/ubuntu/kaggle_data_hpo.
Voi moi chan NEN bi MAT do "arm dang giu symbol" (cause 2_giu_symbol, entry 2022-2025):
  - cum arm (vi the THEM) dang giu sym luc chan nen le ra vao (m0_leg0_arm <= m0_nen < m1_arm);
  - trang thai luc do: lai/lo chua thuc hien (gia close nen m0 = entry nen, lag0) so voi gia vao BINH QUAN cac leg arm
    da vao <= m0 va so voi leg dau; tuoi (gio); U (U_arm cua agent data); dinh/day 1m tu leg0 arm toi m0-1 (da arm TS?);
  - cum arm ket thuc luc nao so voi chan nen bi mat.
Can uoc luong phuong an (a) CORE_ADD (XAP XI, KHONG mo phong lai duong di; dong cum sau khi them chan se KHAC thuc te
vi gia binh quan doi moc arm/TS; thien lech in-sample):
  can 1 = chan LOI vao tai entry nen, dong CUNG LUC cum THEM thuc te (gia tp cum arm);
  can 2 = chan LOI vao tai entry nen, dong o thoi diem/gia ket thuc lenh nen thuc te.
  PnL_S = N*(exit/entry-1) - COST*N - PEN*N*[nen quyet dinh sap]; COST = RATE_FEE + 2*SLIPPAGE (khong funding).
  phu (b): dong cum THEM tai close(m0) roi mo LOI = can 2 + sum_cum (dong@m0 - PnL THEM thuc), cung xap xi.
  N chinh = notional chan nen (duong nen); N_arm = eq_arm*F_BASE*W*SCALE/LADDER*throttle(U_arm) (duong arm) -- phu.
Usage: nice -n 10 python3 research/analysis/nsel_p0b_addleg.py [--workers 3]
"""
import argparse
import gzip
import json
import logging
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import jbin  # noqa: E402
import nsel_p0_data as P  # noqa: E402  (load printDone, OUT/ARMS/PEN dung chung voi agent data)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("nsel_p0b")
W = "/home/ubuntu/claude_master/1008/nsel"
ROWS = W + "/j3_mat_rows.csv.gz"
EV_OUT = W + "/p0b_events.csv.gz"
JSON_OUT = REPO + "/docs/audit/NSEL_P0B_ADDLEG_20261008.json"
TICK = P.TICK
LOCK = P.LOCK
PEN, UMAX = P.PEN, P.UMAX                       # 0,01675 stress / 0,60 U_MAX (profile B0)
RATE_FEE, SLIP = 0.000982, 0.000067             # profiles/g2_flat3.properties SIM_RATE_FEE / SIM_SLIPPAGE_RATE
COST = RATE_FEE + 2 * SLIP                      # OrderTargetInfoTest.calTp: fee 1 lan + slippage 2 chan
LEG_FRAC = 0.015 * 1.0 * 6.0 / 4.0              # F_BASE * w(1) * DCA_GRID_SCALE / dcaGridTotalWeight(1,1,1,1)
ARM_RATE = 0.07                                 # SIM_RATE_PROFIT_STOP_MARKET
CONC_PC = 0.15                                  # CONC_CAP_PERCOIN_PCT
MAXSPAN = 7 * 1440                              # cua so 1m toi da (LOSER_TIME_STOP 168h)
YEARS = [2022, 2023, 2024, 2025]
SEEDS = P.SEEDS
ARM_TAG = P.ARMS["D"][2]


def jd(o):
    return P.jd(o)


def wait_lock():
    while os.path.exists(LOCK):
        log.info("cho lock %s", LOCK)
        time.sleep(60)


def clusters(d):
    """printDone arm -> dict sym -> list cum (m0_leg0, m1, tp, legs[(m0, entry, qty, lt)]); kiem tp dong nhat trong cum."""
    out, tp_bad = {}, 0
    for pid, g in d.groupby("pid", sort=False):
        g = g.sort_values(["m0", "row"], kind="mergesort")
        tps = g["tp"].astype(float).to_numpy()
        if np.nanmax(np.abs(tps / tps[0] - 1.0)) > 1e-6:
            tp_bad += 1
        legs = list(zip(g["m0"].tolist(), g["entry"].astype(float).tolist(), g["quantity"].astype(float).tolist(),
                        g["lt"].tolist()))
        c = dict(sym=g["sym"].iloc[0], m0=int(g["m0"].iloc[0]), m1=int(g["m1"].iloc[0]), tp=float(tps[0]),
                 pnl=float(g["pnl"].sum()), legs=legs, lt0=g["lt"].iloc[0])
        out.setdefault(c["sym"], []).append(c)
    return out, tp_bad


def find_cluster(cl, sym, m):
    """cum arm dang giu sym tai phut m: m0_leg0 <= m < m1 (cum dong o phut m da duoc xu ly TRUOC selector, SIM:244)."""
    hit = [c for c in cl.get(sym, []) if c["m0"] <= m < c["m1"]]
    return hit


def _day(args):
    """1 file ticker ngay: (phut UTC, high, low, close) cua cac symbol can. tup = (startTime, max, min, close, open, vol)."""
    day, syms = args
    p = os.path.join(TICK, "ticker_%s.bin.gz" % day)
    if not os.path.exists(p):
        return day, {}
    acc = {s: [] for s in syms}
    with gzip.open(p, "rb") as f:
        b = f.read()
    for k, v in jbin.iter_minutes(b):
        m = k // 60000
        for s in syms:
            tup = v.get(s + "USDT")
            if tup is not None:
                acc[s].append((m, tup[1], tup[2], tup[3]))
    return day, {s: np.array(a, dtype=np.float64) for s, a in acc.items() if a}


def minute_path(ev, workers):
    """dict sym -> mang (phut, high, low, close) sap theo phut, chi cho cac ngay can (leg0 arm .. m0 nen)."""
    need = {}
    for sym, a, b in ev:
        for dd in range((a - 1440) // 1440, b // 1440 + 2):
            need.setdefault(pd.Timestamp(dd * 86400, unit="s").strftime("%Y%m%d"), set()).add(sym)
    jobs = sorted((k, sorted(v)) for k, v in need.items())
    log.info("nen 1m: %d file ngay, %d cap (ngay, sym)", len(jobs), sum(len(v) for _, v in jobs))
    per = {}
    with Pool(workers) as pool:
        for i, (day, res) in enumerate(pool.imap_unordered(_day, jobs, chunksize=4)):
            for s, arr in res.items():
                per.setdefault(s, []).append(arr)
            if i % 200 == 0:
                log.info("  %d/%d", i, len(jobs))
    out = {}
    for s, lst in per.items():
        a = np.concatenate(lst)
        a = a[np.argsort(a[:, 0], kind="mergesort")]
        _, idx = np.unique(a[:, 0], return_index=True)
        out[s] = a[idx]
    return out


def build_events():
    r = pd.read_csv(ROWS)
    r = r[r["key"].str.startswith("D|") & (r["cause"] == "2_giu_symbol") & r["year"].isin(YEARS)].copy()
    ev, chk = [], {}
    for s in SEEDS:
        rs = r[r["key"] == "D|" + s]
        arm, meta = P.load(ARM_TAG[s])
        cl, tp_bad = clusters(arm)
        nmiss, nmulti = 0, 0
        for x in rs.itertuples(index=False):
            m = int(x.m0)
            hit = find_cluster(cl, x.sym, m)
            if not hit:
                nmiss += 1
                continue
            if len(hit) > 1:
                nmulti += 1
            c = max(hit, key=lambda z: z["m0"])
            le = [lg for lg in c["legs"] if lg[0] <= m]
            q = sum(lg[2] for lg in le)
            eq_ = sum(lg[1] * lg[2] for lg in le)
            ev.append(dict(seed=s, sym=x.sym, year=int(x.year), lt_b=x.lt, m0_b=m, m1_b=int(x.m1), e_b=float(x.entry),
                           tp_b=float(x.tp), N_b=float(x.notional), pnl_b=float(x.pnl), pnl_s_b=float(x.pnl_s),
                           crash=bool(x.crash), U=float(x.U_arm), eq=float(x.eq_arm), m0_a=c["m0"], m1_a=c["m1"],
                           tp_a=c["tp"], pnl_a=c["pnl"], lt0_a=c["lt0"], nleg_le=len(le), nleg_a=len(c["legs"]),
                           avg_a=eq_ / q, first_a=c["legs"][0][1], marg_a=eq_))
        chk[s] = dict(n_rows=int(len(rs)), n_arm_legs=int(meta["n"]), n_arm_clusters=int(sum(len(v) for v in cl.values())),
                      tp_not_uniform_clusters=int(tp_bad), miss=int(nmiss), multi=int(nmulti))
        log.info("seed %s: %s", s, chk[s])
    return pd.DataFrame(ev), chk


def add_features(e, workers):
    req = [(s, max(int(a), int(b) - MAXSPAN), int(b)) for s, a, b in zip(e["sym"], e["m0_a"], e["m0_b"])]
    path = minute_path(req, workers)
    pk, lo, cl0, nbar = (np.full(len(e), np.nan) for _ in range(4))
    for i, (s, a, b) in enumerate(req):
        arr = path.get(s)
        if arr is None:
            continue
        mm = arr[:, 0]
        j = np.searchsorted(mm, b)
        if j < len(mm) and mm[j] == b:
            cl0[i] = arr[j, 3]
        i0 = np.searchsorted(mm, a)
        if j > i0:                       # [leg0 arm, m0 nen - 1]: nen da dong truoc quyet dinh
            pk[i], lo[i], nbar[i] = arr[i0:j, 1].max(), arr[i0:j, 2].min(), j - i0
    e["close_b"], e["peak_hi"], e["min_lo"], e["nbar"] = cl0, pk, lo, nbar
    e["unreal_avg"] = 100.0 * (e["e_b"] / e["avg_a"] - 1.0)
    e["unreal_first"] = 100.0 * (e["e_b"] / e["first_a"] - 1.0)
    e["peak_avg"] = 100.0 * (e["peak_hi"] / e["avg_a"] - 1.0)
    e["mae_avg"] = 100.0 * (e["min_lo"] / e["avg_a"] - 1.0)
    e["armed"] = e["peak_avg"] >= 100.0 * ARM_RATE
    e["age_h"] = (e["m0_b"] - e["m0_a"]) / 60.0
    e["dend_h"] = (e["m1_a"] - e["m1_b"]) / 60.0
    e["N_arm"] = e["eq"] * LEG_FRAC * np.clip(1.0 - e["U"] / UMAX, 0.0, 1.0)
    pen = PEN * e["crash"].astype(float)
    for nk in ("N_b", "N_arm"):
        n = e[nk]
        e["b1_" + nk] = n * (e["tp_a"] / e["e_b"] - 1.0) - COST * n - pen * n
        e["b2_" + nk] = n * (e["tp_b"] / e["e_b"] - 1.0) - COST * n - pen * n
    e["pnl_model_b"] = e["N_b"] * (e["tp_b"] / e["e_b"] - 1.0) - COST * e["N_b"]
    # phuong an (b) (phu, xap xi): dong cum THEM tai close(m0) (chi cac leg <= m0, khong stress/funding) thay vi ket qua thuc
    e["them_close_m0"] = (e["marg_a"] / e["avg_a"]) * e["e_b"] - e["marg_a"] - COST * e["marg_a"]
    e["dthem_b"] = e["them_close_m0"] - e["pnl_a"]
    e["conc_after"] = (e["marg_a"] + e["N_arm"]) / e["eq"]
    e["U_after"] = e["U"] + e["N_arm"] / e["eq"]
    e["day"] = (e["m0_b"] + 420) // 1440           # ngay gio local (cung truc 'start' printDone)
    return e


QS = [10, 25, 50, 75, 90]


def qd(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return [round(float(v), 3) for v in np.percentile(x, QS)] if len(x) else None


def summarize(g):
    uniq = g.sort_values("m0_b", kind="mergesort").drop_duplicates(["seed", "sym", "m0_a"])
    return dict(
        n=int(len(g)), n_them_clusters=int(len(uniq)), sum_pnl_them_clusters=float(uniq["pnl_a"].sum()),
        sum_dthem_b=float(uniq["dthem_b"].sum()), sum_opt_b=float(g["b2_N_b"].sum() + uniq["dthem_b"].sum()),
        unreal_avg_q=qd(g["unreal_avg"]), unreal_first_q=qd(g["unreal_first"]), age_h_q=qd(g["age_h"]),
        U_q=qd(g["U"]), dend_h_q=qd(g["dend_h"]), peak_avg_q=qd(g["peak_avg"]), mae_avg_q=qd(g["mae_avg"]),
        nleg_le_mean=float(g["nleg_le"].mean()),
        sh_unreal_neg=float((g["unreal_avg"] < 0).mean()), sh_armed=float(g["armed"].mean()),
        sh_U_ge_umax=float((g["U"] >= UMAX).mean()), sh_age_le1h=float((g["age_h"] < 1).mean()),
        sh_them_end_before=float((g["dend_h"] < 0).mean()), sh_them_end_same=float((g["dend_h"] == 0).mean()),
        sh_them_end_after=float((g["dend_h"] > 0).mean()),
        sum_pnl_s_mat=float(g["pnl_s_b"].sum()), sum_N_b=float(g["N_b"].sum()), sum_N_arm=float(g["N_arm"].sum()),
        sum_b1_N_b=float(g["b1_N_b"].sum()), sum_b2_N_b=float(g["b2_N_b"].sum()),
        sum_b1_N_arm=float(g["b1_N_arm"].sum()), sum_b2_N_arm=float(g["b2_N_arm"].sum()),
        roi_b1=float(100 * g["b1_N_b"].sum() / g["N_b"].sum()), roi_b2=float(100 * g["b2_N_b"].sum() / g["N_b"].sum()),
        sh_b1_neg=float((g["b1_N_b"] < 0).mean()),
        conc_after_q=qd(100 * g["conc_after"]), sh_conc_gt_cap=float((g["conc_after"] > CONC_PC).mean()),
        sh_U_after_ge_umax=float((g["U_after"] >= UMAX).mean()))


def daily(g):
    d = g.groupby("day")[["b1_N_b", "b2_N_b", "pnl_s_b"]].sum()
    out = {}
    for c in d.columns:
        v = d[c].to_numpy()
        out[c] = dict(ndays=int(len(v)), p5=float(np.percentile(v, 5)), p50=float(np.percentile(v, 50)),
                      p95=float(np.percentile(v, 95)), min=float(v.min()), max=float(v.max()),
                      sh_neg=float((v < 0).mean()))
    dd = (d["b1_N_b"] - d["b2_N_b"]).to_numpy()
    out["b1_minus_b2"] = dict(mean=float(dd.mean()), sd=float(dd.std(ddof=1)), sh_neg=float((dd < 0).mean()))
    return out


def validate(e):
    ok = np.isfinite(e["close_b"])
    rel = np.abs(e.loc[ok, "close_b"] / e.loc[ok, "e_b"] - 1.0)
    res = e["pnl_b"] - e["pnl_model_b"]
    return dict(
        n=int(len(e)), close_missing=int((~ok).sum()), close_eq_entry_lag0=float((rel < 1e-5).mean()),
        nbar_missing=int(e["nbar"].isna().sum()), same_minute_leg0=int((e["m0_a"] == e["m0_b"]).sum()),
        cost_model_resid_sum=float(res.sum()), cost_model_resid_med=float(res.median()),
        cost_model_resid_absp99=float(np.percentile(np.abs(res), 99)),
        b2_vs_pnl_s_sum_diff=float((e["b2_N_b"] - e["pnl_s_b"]).sum()),
        N_arm_over_N_b_med=float((e["N_arm"] / e["N_b"]).median()),
        avg_le_first=float((e["avg_a"] <= e["first_a"] * (1 + 1e-6)).mean()))


def table(name, rows, cols):
    print("\n#### " + name)
    print("| " + " | ".join(["nhom"] + cols) + " |")
    print("|" + "---|" * (len(cols) + 1))
    for k, v in rows.items():
        cells = []
        for c in cols:
            x = v.get(c)
            cells.append("%.3f" % x if isinstance(x, float) else str(x))
        print("| %s | %s |" % (k, " | ".join(cells)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    wait_lock()                       # RAM < 4G: khong tao lock, chi cho neu job nang khac dang chay
    e, chk = build_events()
    e = add_features(e, a.workers)
    e.to_csv(EV_OUT, index=False, compression="gzip")
    out = dict(meta=dict(script="research/analysis/nsel_p0b_addleg.py", rows=ROWS, arm_tags=ARM_TAG, years=YEARS,
                         cost=COST, pen=PEN, leg_frac=LEG_FRAC, arm_rate=ARM_RATE, conc_pc=CONC_PC,
                         note="xap xi, KHONG mo phong lai duong di; in-sample; chi bao cao"),
               check=chk, valid=validate(e), by_seed={}, by_seed_lt={}, by_year={}, daily={})
    for s in SEEDS:
        g = e[e["seed"] == s]
        out["by_seed"][s] = summarize(g)
        out["daily"][s] = daily(g)
        for lt, gl in g.groupby("lt_b"):
            out["by_seed_lt"]["%s|%s" % (s, lt)] = summarize(gl)
        for y, gy in g.groupby("year"):
            out["by_year"]["%s|%d" % (s, y)] = dict(n=int(len(gy)), sum_pnl_s_mat=float(gy["pnl_s_b"].sum()),
                                                   sum_b1_N_b=float(gy["b1_N_b"].sum()),
                                                   sum_b2_N_b=float(gy["b2_N_b"].sum()),
                                                   sh_unreal_neg=float((gy["unreal_avg"] < 0).mean()))
    out["pooled"] = summarize(e)
    with open(JSON_OUT, "w") as f:
        json.dump(out, f, indent=1, default=jd)
    log.info("valid: %s", out["valid"])
    cols = ["n", "n_them_clusters", "sum_pnl_s_mat", "sum_b1_N_b", "sum_b2_N_b", "sum_b1_N_arm", "sum_b2_N_arm",
            "roi_b1", "roi_b2", "sh_b1_neg", "sum_pnl_them_clusters", "sum_dthem_b", "sum_opt_b"]
    table("bound theo seed", out["by_seed"], cols)
    table("bound theo seed|loai chan", out["by_seed_lt"], cols)
    cols2 = ["unreal_avg_q", "unreal_first_q", "age_h_q", "U_q", "dend_h_q", "peak_avg_q", "mae_avg_q"]
    table("trang thai THEM (p10/25/50/75/90)", out["by_seed"], cols2)
    cols3 = ["sh_unreal_neg", "sh_armed", "sh_U_ge_umax", "sh_age_le1h", "sh_them_end_before", "sh_them_end_same",
             "sh_them_end_after", "nleg_le_mean", "conc_after_q", "sh_conc_gt_cap", "sh_U_after_ge_umax"]
    table("ti le", out["by_seed"], cols3)
    table("theo nam", out["by_year"], ["n", "sum_pnl_s_mat", "sum_b1_N_b", "sum_b2_N_b", "sh_unreal_neg"])
    print(json.dumps(out["daily"], indent=1, default=jd))
    print(json.dumps(out["check"], default=jd))


if __name__ == "__main__":
    main()
