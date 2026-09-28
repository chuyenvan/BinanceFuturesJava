#!/usr/bin/env python3
"""EXIT-STRUCT P6 scorer — docs/prereg/PREREG_EXIT_STRUCT_P6.md.

Khu confound SIZE cua A2: cham lai 3 cot
  A0      (cd-sel15, grid ON,  TS168)          <- chuan
  A2      (xs-a2,    grid OFF, bo TS168)       <- ~1/6 size
  A2size  (xs-a2s6,  grid OFF, bo TS168, SIM_F_BASE=0,18 = 0,03x6)
Bang: n | entry/thang | gross TB/MAX | CAGR | maxDD | UW | qmin | %top-1 | TF50 | asym | sign% | q*
+ size-neutral (pnl/margin) + 4 thuoc chuan + 4 rate + CI vs A0 (block-72h, 2000, seed 20260905, inflate(3))
+ rao cu --appetite latest + 3 chi so martingale. THUAN PYTHON OFFLINE, DEV<=2025-12-31.

  python3 exit_struct_p6_score.py [--json docs/result/RESULT_EXIT_STRUCT_P6.json]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

AD = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
sys.path.insert(0, AD)
import gd92xexit_score as G
import size_count_score as S
import exit_struct_score as E

ARMS = [("A0", "cd-sel15"), ("A2", "xs-a2"), ("A2size", "xs-a2s6")]
A0 = "cd-sel15"


def gross_of(tag):
    d = S.legs(tag)
    eq = S.eq_series(tag)
    g = S.gross(d, eq)
    return dict(gross_mean=g["gross_mean"], gross_max=g["gross_max"],
                margin_mean=float(pd.to_numeric(d["margin"], errors="coerce").mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    if a.json is None:
        a.json = os.path.join(AD, "..", "..", "docs/result/RESULT_EXIT_STRUCT_P6.json")

    rows, mart, rail, rao, rao_ret = {}, {}, {}, {}, {}
    for lbl, tag in ARMS:
        try:
            s = G.summary(tag)
        except Exception as e:
            print("SKIP %s (%s): %s" % (lbl, tag, e))
            continue
        d = E.load(tag)
        rao[lbl] = E.tf_block(d.pnl.to_numpy(float))
        rao_ret[lbl] = E.tf_block((d.pnl / d.margin).to_numpy(float))
        rr = E.rulers_of((d.pnl / d.margin).to_numpy(float))
        rr_u = E.rulers_of(d.pnl.to_numpy(float))
        g = gross_of(tag)
        rows[lbl] = dict(tag=tag, n=s["n"], ndays=s["ndays"], eq=s["end"], cagr=s["cagr"],
                         maxdd=s["maxDD"], uw=s["uw"], qmin=s["qmin"], conc=s["conc"],
                         entry_month=s["n"] / s["ndays"] * 365.25 / 12.0,
                         sumpnl=s["sumpnl"],
                         asym=rr["asym"], asym_usdt=rr_u["asym"], sign_pct=rr["sign_frac"],
                         loss_mean=rr["loss_mean"], win_mean=rr["win_mean"], tl_median=rr["median"],
                         conc_5=rr["conc_5"], max_loss_leg=rr["max_loss"], tf_5r=rr["tf_5"],
                         **g, rates=E.rates_of_run(d))
        mart[lbl] = E.martingale(d, tag)
        yd = G.yearly_detail(tag)
        bad = []
        for y, v in sorted(yd.items()):
            if v.get("ret", 0) <= 0: bad.append("%s:ret<=0" % y)
            if v.get("uw", 0) > 250: bad.append("%s:UW%d" % (y, v["uw"]))
            if v.get("maxDD", 0) < -40: bad.append("%s:DD%.1f" % (y, v["maxDD"]))
            if v.get("qmin", 0) < -20: bad.append("%s:qmin%.1f" % (y, v["qmin"]))
        if s["maxDD"] < -40: bad.append("ALL:DD%.1f" % s["maxDD"])
        if s["uw"] > 250: bad.append("ALL:UW%d" % s["uw"])
        if s["qmin"] < -20: bad.append("ALL:qmin%.1f" % s["qmin"])
        if s["conc"] > 15: bad.append("ALL:conc%.1f" % s["conc"])
        rail[lbl] = dict(pass_=not bad, violations=bad)

    L = 118
    print("=" * L)
    print("SIZE: margin TB/leg + gross (ledger, m/E) — do, khong doan")
    print("%-7s %-9s %5s %8s %10s %10s %10s %8s" % ("arm", "tag", "n", "eq", "margin/leg", "gross TB%", "gross MAX%", "vs A0"))
    m0 = rows.get("A0", {}).get("margin_mean")
    for lbl, tag in ARMS:
        if lbl not in rows: continue
        r = rows[lbl]
        print("%-7s %-9s %5d %8.0f %10.1f %10.3f %10.2f %8s" % (
            lbl, tag, r["n"], r["eq"], r["margin_mean"], r["gross_mean"], r["gross_max"],
            ("%.2fx" % (r["margin_mean"] / m0) if m0 else "-")))

    print("\n" + "=" * L)
    hdr = "%-7s %5s %8s %8s %8s %8s %6s %8s %8s %8s"
    print("BANG CHINH: n | entry/thang | CAGR | maxDD | UW | qmin | conc | asym | sign% | q*%")
    print(hdr % ("arm", "n", "ent/th", "CAGR%", "maxDD%", "UW", "qmin%", "asym", "sign%", "q*%"))
    for lbl, tag in ARMS:
        if lbl not in rows: continue
        r = rows[lbl]; q = rao[lbl]
        print(hdr % (lbl, r["n"], "%.2f" % r["entry_month"], "%+.2f" % r["cagr"], "%.2f" % r["maxdd"],
                     r["uw"], "%.2f" % r["qmin"], "%.3f" % r["asym"], "%.1f" % r["sign_pct"],
                     ("%.1f" % q["q_breakeven_pct"]) if q["q_breakeven_pct"] else "-"))

    print("\n" + "=" * L)
    print("RAO (a) top-1%<=15 | (b') bo-50% >0   [USDT]  va  [SIZE-NEUTRAL pnl/margin]")
    hd = "%-7s %10s %6s %12s %6s %10s %8s %9s %9s"
    for space, R in (("USDT", rao), ("SIZE-NEUTRAL", rao_ret)):
        print("  -- %s --" % space)
        print(hd % ("arm", "%top1", "(a)", "bo-50%", "(b')", "q*%", "median", "tf_5", "tf_10"))
        for lbl, tag in ARMS:
            if lbl not in R: continue
            r = R[lbl]
            print(hd % (lbl, "%.2f" % r["share_top1_pct"], "PASS" if r["pass_a"] else "FAIL",
                        "%.2f" % r["tf50"] if space != "USDT" else "%.0f" % r["tf50"],
                        "PASS" if r["pass_b50"] else "FAIL",
                        ("%.1f" % r["q_breakeven_pct"]) if r["q_breakeven_pct"] else "-",
                        ("%.4f" % r["median_leg"]) if space != "USDT" else ("%.1f" % r["median_leg"]),
                        ("%.4f" % r["tf5"]) if space != "USDT" else ("%.1f" % r["tf5"]),
                        ("%.4f" % r["tf10"]) if space != "USDT" else ("%.1f" % r["tf10"])))

    print("\n" + "=" * L)
    print("4 THUOC CHUAN + 4 RATE")
    hd2 = "%-7s %8s %10s %10s %9s %9s %8s %9s %9s %9s"
    print(hd2 % ("arm", "asym", "loss_mean", "win_mean", "median", "conc_5", "tf_5", "TSloss%", "mP|SM", "mP|SL"))
    for lbl, tag in ARMS:
        if lbl not in rows: continue
        r = rows[lbl]; q = r["rates"]
        print(hd2 % (lbl, "%.3f" % r["asym"], "%+.5f" % r["loss_mean"], "%+.5f" % r["win_mean"],
                     "%+.5f" % r["tl_median"], "%.3f" % r["conc_5"], "%+.5f" % r["tf_5r"],
                     "%.1f" % q["tsloss"],
                     "%+.1f" % q["mp_sm"] if np.isfinite(q["mp_sm"]) else "-",
                     "%+.1f" % q["mp_sl"] if np.isfinite(q["mp_sl"]) else "-"))

    print("\n" + "=" * L)
    print("3 CHI SO MARTINGALE")
    for lbl, tag in ARMS:
        if lbl not in mart: continue
        m = mart[lbl]
        print("  %-7s worstPos=%.0f USDT | conc1coin=%.2f%% (%s) | coin chet %d/%d (%.0f)" % (
            lbl, m["worst_pos_loss_all"], m["conc_1coin_pct"],
            "VUOT 15" if m["conc_1coin_over15"] else "ok", m["n_dead_coins"], m["n_coin"],
            m["dead_coins_losses"]))

    print("\n" + "=" * L)
    print("RAO CU --appetite latest (maxDD<=40 / UW<=250 / qmin>=-20 / 0 nam am / conc<=15)")
    for lbl, tag in ARMS:
        if lbl not in rail: continue
        print("  %-7s %s" % (lbl, "PASS" if rail[lbl]["pass_"] else "VI PHAM: " + ",".join(rail[lbl]["violations"])))

    print("\n" + "=" * L)
    print("CI vs A0 (block-72h, 2000 rep, seed 20260905, inflate(3)=%.4f) + rate CI" % E.W_INFLATE)
    E.map = None
    Emap = {}
    for lbl, tag in ARMS:
        try: Emap[lbl] = G.equity(tag)
        except Exception: pass
    LR = {l: np.diff(np.log(np.concatenate([[E.CAP0], Emap[l].values.astype(float)]))) for l in Emap}
    N = len(Emap["A0"])
    cagr = lambda lr: (np.exp(lr.sum() * 365.0 / N) - 1.0) * 100
    ci_out = {}
    for lbl, tag in ARMS:
        if lbl == "A0" or lbl not in rows: continue
        pair = G.ci_pair(tag, A0, E.W_INFLATE)
        ix = E.idxmat(N, E.BLOCK_EQ, E.NREP_EQ, E.SEED_EQ)
        da = (np.exp(LR[lbl][ix].sum(axis=1) * 365.0 / N) - np.exp(LR["A0"][ix].sum(axis=1) * 365.0 / N)) * 100
        sd = float(da.std(ddof=1)); thr = E.W_INFLATE * sd
        d = cagr(LR[lbl]) - cagr(LR["A0"])
        ci_out[lbl] = dict(dCAGR=float(d), sd=sd, thr=thr, dat=bool(d > thr), p=float((da > 0).mean()),
                           rates={k: [round(v[0], 4), round(v[1], 4), round(v[2], 4), bool(v[3])] for k, v in pair.items()})
        print("  %-7s dCAGR %+.2f pp (sd %.2f, nguong +%.2f, P>0 %.3f) => %s" % (
            lbl, d, sd, thr, (da > 0).mean(), "DAT" if d > thr else "khong"))
        print("      " + " ".join("%s %.3f[%.3f,%.3f]%s" % (k, v[0], v[1], v[2], "*" if v[3] else "")
                                  for k, v in pair.items()))

    out = dict(prereg="docs/prereg/PREREG_EXIT_STRUCT_P6.md", arms=rows, rao=rao, rao_size_neutral=rao_ret,
               martingale=mart, rails=rail, ci_vs_A0=ci_out, inflate=E.W_INFLATE)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("\nJSON -> %s (%.1f KB)" % (a.json, os.path.getsize(a.json) / 1024.0))


if __name__ == "__main__":
    main()
