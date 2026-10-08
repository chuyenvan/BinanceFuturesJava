#!/usr/bin/env python3
"""NSEL_P0 (2026-10-08) J2 + J5 — CHI DOC output Kaggle co san: 0 sim, 0 Java, 0 tune.

J2: ty le entry == close nen 1m phut start (lag0) / phut start-1 (lag1) THEO LOAI CHAN (cot level printDone);
    ty le chan 'sap' (close/open-1 <= -1% tren nen quyet dinh) theo loai chan. Tag: twin B0 flat3-cp-p0, gqsf-a1
    (K24 skipFull = nen NSEL), in-sim P1/P2 (chan sap phai co entry = close*(1+pen) => kiem cho dat phat).
J5: post-hoc bac 1 kieu gkf_rescore (gia vao +pen, PnL -pen*notional, KHONG mo phong lai duong di) ap len twin P0
    vs in-sim SIM_CRASH_ENTRY_PENALTY (P1 0.0069, P2 0.0138, jar d944bea5): dSumPnL, dMaxDD MTM, dCAGR, Calmar;
    phan ra sai so: (a) cung lenh size-neutral (duong di TP/SL), (b) sizing/lai kep, (c) tap lenh lech.
Tai dung: gkf_rescore (umin/load_bars/crash_mask/stress_legs/stress_daily), reset_rule_score.run_mtm,
n700_driver.arm_metrics; MTM in-sim P0/P1/P2 lay tu cache flat3cp_mtm.json (md5 khop).
Usage: nice -n 10 python3 research/analysis/nsel_p0_code.py [--workers 3]
"""
import argparse
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/analysis")
import gkf_rescore as G  # noqa: E402  (import => R/F/F3/N san sang, R.MTM_COSTS = legacy)

R, F3, N = G.R, G.F3, G.N
log = logging.getLogger("nsel_p0_code")
D = "/home/ubuntu/claude_master/1008/nsel"
F3_MTM = "/home/ubuntu/claude_master/1002/flat3cp_mtm.json"
JSON_OUT = REPO + "/docs/audit/NSEL_P0_CODE_20261008.json"
TAGS = {"P0": "flat3-cp-p0", "P1": "flat3-cp-p1", "P2": "flat3-cp-p2", "A1": "gqsf-a1"}
PENS = {"P1": 0.0069, "P2": 0.0138}
# tham chieu da cong bo (RESULT_FLAT3_CRASHPEN.md §2) — tu kiem in-sim phai khop
REF = {"P0": dict(equity=131908, sum_pnl=96909, calmar=1.940, calmar22=1.898),
       "P1": dict(equity=118924, sum_pnl=83924, calmar=1.758, calmar22=1.735),
       "P2": dict(equity=108815, sum_pnl=73816, calmar=1.610, calmar22=1.590)}


def by_level(d, bar, pen=0.0):
    """theo loai chan: n, khop lag0/lag1 (|close/entry-1|<1e-5), so chan sap, so chan sap co entry=close*(1+pen)."""
    m = G.umin(d)
    e = d["entry"].to_numpy(float)
    lv = d["level"].astype(str).str.strip().to_numpy()
    sy = d["sym"].to_numpy()
    out = {}
    for k in sorted(set(lv)):
        r = dict(n=0, nobar=0, lag0=0, lag1=0, crash=0, crash_pen_match=0, noncrash_lag0=0)
        for i in np.where(lv == k)[0]:
            r["n"] += 1
            b0, b1 = bar.get((sy[i], int(m[i]))), bar.get((sy[i], int(m[i]) - 1))
            if b0 is None or not e[i] > 0:
                r["nobar"] += 1
                continue
            h0 = abs(b0[1] / e[i] - 1.0) < 1e-5
            r["lag0"] += int(h0)
            r["lag1"] += int(b1 is not None and abs(b1[1] / e[i] - 1.0) < 1e-5)
            cr = b0[0] > 0 and b0[1] / b0[0] - 1.0 <= G.CRASH
            r["crash"] += int(cr)
            if cr and pen:
                r["crash_pen_match"] += int(abs(b0[1] * (1.0 + pen) / e[i] - 1.0) < 1e-4)
            if not cr:
                r["noncrash_lag0"] += int(h0)
        out[k] = r
    return out


def lkey(d):
    return (d["sym"].astype(str) + "|" + d["start"].astype(str).str.strip() + "|"
            + d["level"].astype(str).str.strip())


def decompose(ph, sim, msk_ph):
    """sai so post-hoc (ph = twin P0 da phat) vs in-sim: sim - ph, tach (a)(b)(c)."""
    a = ph.assign(k=lkey(ph).to_numpy(), crash=msk_ph).groupby("k").agg(
        pnl=("pnl", "sum"), no=("notional", "sum"), crash=("crash", "max"))
    b = sim.assign(k=lkey(sim).to_numpy()).groupby("k").agg(pnl=("pnl", "sum"), no=("notional", "sum"))
    c = a.join(b, how="inner", lsuffix="_ph", rsuffix="_sim")
    r_ph, r_sim = c["pnl_ph"] / c["no_ph"], c["pnl_sim"] / c["no_sim"]
    path = (r_sim - r_ph) * c["no_ph"]                  # (a) size-neutral: cung lenh, khac ket qua/duong di
    size = c["pnl_sim"] - c["pnl_ph"] - path            # (b) phan con lai cua lenh chung = khac notional
    oa, ob = a.index.difference(b.index), b.index.difference(a.index)
    res = dict(n_common=int(len(c)), n_only_ph=int(len(oa)), n_only_sim=int(len(ob)),
               d_total=float(sim["pnl"].sum() - ph["pnl"].sum()),
               d_path=float(path.sum()), d_path_crash=float(path[c["crash"]].sum()),
               d_path_noncrash=float(path[~c["crash"]].sum()), d_size=float(size.sum()),
               d_set=float(b.loc[ob, "pnl"].sum() - a.loc[oa, "pnl"].sum()),
               frac_common_changed=float((np.abs(r_sim - r_ph) > 1e-6).mean()),
               frac_noncrash_changed=float((np.abs(r_sim - r_ph)[~c["crash"]] > 1e-6).mean()))
    return res


def by_year_entry(d):
    return {int(y): float(v) for y, v in d.groupby(d["ts"].dt.year)["pnl"].sum().items()}


def met(key, legs, daily, mtm):
    N.TAG[key], N.DESC[key] = key, key
    m = N.arm_metrics(R, F3, key, legs, daily, mtm)
    out = {k: m[k] for k in ("n", "equity", "sum_pnl", "sum_pnl_2022_25", "cagr", "cagr22", "dd_mtm", "dd_mtm22",
                             "uw_mtm", "uw_mtm22", "calmar", "calmar22", "win", "sl")}
    out["dd_year"] = {int(y): float(v) for y, v in mtm["dd_year"].items()}
    out["roi_year"] = m["roi_year"]
    out["pnl_entry_year"] = by_year_entry(legs)
    return out


def mtm_for(keys_legs, md5s, workers):
    """MTM phut: in-sim tu cache flat3 (md5 khop), post-hoc tinh moi (cache rieng D/mtm.json)."""
    f3 = json.load(open(F3_MTM))
    cp = D + "/mtm.json"
    raw = json.load(open(cp)) if os.path.exists(cp) else {}
    out, miss = {}, {}
    for k, d in keys_legs.items():
        if k in f3 and f3[k]["md5"] == md5s[k]:
            out[k] = f3[k]["legacy"]
        elif raw.get(k, {}).get("md5") == md5s[k]:
            out[k] = raw[k]["legacy"]
        else:
            miss[k] = d
    if miss:
        log.info("MTM phut can tinh: %s", sorted(miss))
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, v in new.items():
            v["md5"] = md5s[k]
            raw[k] = v
            out[k] = v["legacy"]
        json.dump(raw, open(cp, "w"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(D, exist_ok=True)
    G.BAR_CACHE = D + "/bar.json"
    legs = {k: R.load_legs(t) for k, t in TAGS.items()}
    daily = {k: R.load_daily(t) for k, t in TAGS.items() if k != "A1"}
    md5 = {k: R.md5_of(t) for k, t in TAGS.items()}
    log.info("md5 %s", md5)
    assert md5["P0"] == F3.PARITY_MD5, "twin P0 khong phai B0"
    bar = G.load_bars(legs, a.workers)
    J2 = {k: by_level(legs[k], bar, PENS.get(k, 0.0)) for k in TAGS}
    for k, v in J2.items():
        log.info("J2 %s %s", k, v)
    lg = {k: F3.crashpen(TAGS[k]) for k in PENS}
    log.info("log [CRASH-PENALTY] SUMMARY %s", lg)
    # ---- J5 post-hoc tren twin P0
    msk, br, hit = G.crash_mask(legs["P0"], bar, 0)
    keys_legs, keys_daily, md5s = {}, {}, {}
    for k in ("P0", "P1", "P2"):
        keys_legs[k], keys_daily[k], md5s[k] = legs[k], daily[k], md5[k]
    for k, pen in PENS.items():
        G.PEN = pen
        s = G.stress_legs(legs["P0"], msk)
        hk = "PH" + k[1]
        keys_legs[hk], keys_daily[hk], md5s[hk] = s, G.stress_daily(daily["P0"], s), md5["P0"] + "#S%.4f" % pen
    mtm = mtm_for(keys_legs, md5s, a.workers)
    M = {k: met(k, keys_legs[k], keys_daily[k], mtm[k]) for k in keys_legs}
    bad = []
    for k, ref in REF.items():
        for f, v in ref.items():
            tol = 0.0015 if f.startswith("calmar") else 1.0
            if abs(M[k][f] - v) > tol:
                bad.append((k, f, M[k][f], v))
    log.info("TU KIEM in-sim vs RESULT_FLAT3_CRASHPEN: %d lech %s", len(bad), bad)
    assert not bad, "TU KIEM LECH -> DUNG"
    J5 = {}
    for k in PENS:
        hk = "PH" + k[1]
        ph, sm = M[hk], M[k]
        J5[k] = dict(pen=PENS[k],
                     d_sum_pnl=sm["sum_pnl"] - ph["sum_pnl"], d_equity=sm["equity"] - ph["equity"],
                     d_cagr=sm["cagr"] - ph["cagr"], d_cagr22=sm["cagr22"] - ph["cagr22"],
                     d_dd_mtm=sm["dd_mtm"] - ph["dd_mtm"], d_dd_mtm22=sm["dd_mtm22"] - ph["dd_mtm22"],
                     d_calmar=sm["calmar"] - ph["calmar"], d_calmar22=sm["calmar22"] - ph["calmar22"],
                     drop_sim=M["P0"]["sum_pnl"] - sm["sum_pnl"], drop_ph=M["P0"]["sum_pnl"] - ph["sum_pnl"],
                     dcagr_sim=M["P0"]["cagr"] - sm["cagr"], dcagr_ph=M["P0"]["cagr"] - ph["cagr"],
                     decomp=decompose(keys_legs[hk], legs[k], msk))
        log.info("J5 %s %s", k, J5[k])
    js = dict(title="NSEL_P0_CODE_20261008", tags=TAGS, md5=md5, crash_thr=G.CRASH,
              j2_by_level=J2, crashpen_log=lg, j5_n_crash_P0=int(msk.sum()), j5_no_bar_P0=int(np.isnan(br).sum()),
              j5_entry_match_P0=float(hit.mean()), metrics=M, j5=J5,
              note="post-hoc bac 1 (gkf_rescore): entry*(1+pen), pnl-=pen*notional, khong mo phong lai duong di")
    json.dump(js, open(JSON_OUT, "w"), indent=1, default=G.jd)
    log.info("WROTE %s", JSON_OUT)


if __name__ == "__main__":
    main()
