#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""COST2_TRACKB — cham lai Track B o CHI PHI CO HUONG (3 nhom thanh khoan) tu book_cost2.json.

Pre-reg: docs/prereg/PREREG_BOOK_COST2.md (commit b8bcca9).
Tai dung harness RESULT_TRACKB_STEP1 (research/trackb/run_trackb.py) — KHONG doi thiet ke book.
Chi thay fee: net_new[t] = gross[t] + fund[t] - sum_g TO_g[t] * C_g(S).
Thuan Python offline, 0 sim, 0 train, DEV<=2025-12-31.
"""
import json
import os
import sys
import time

import numpy as np

TRACKB = "/home/ubuntu/src/BinanceFuturesJava/research/trackb"
sys.path.insert(0, TRACKB)
import run_trackb as rt  # noqa: E402

PANEL = "/tmp/trackb"
COST2 = "/home/ubuntu/src/BinanceFuturesJava/docs/result/book_cost2.json"
OUTJ = "/home/ubuntu/src/BinanceFuturesJava/docs/result/book_cost2_trackb.json"
STOP, STOP_SLIP = rt.STOP, rt.STOP_SLIP


def groups_from_panel(panel):
    """Nhom thanh khoan theo hang dv_med trong top-200 (dung build_eligible order)."""
    dv_med, dv_n = panel["dv_med"], panel["dv_n"]
    NS = panel["D"].shape[1]
    ok = np.isfinite(dv_med) & (dv_n >= 12)
    order = np.argsort(np.where(ok, dv_med, -1))[::-1]
    top = order[:rt.TOPK_UNIV]
    g = np.full(NS, -1, dtype=np.int8)
    g[top[:20]] = 0
    g[top[20:100]] = 1
    g[top[100:200]] = 2
    return g


def pnl_group(panel, W, cvec, use_stop=True):
    """Giong rt.book_pnl nhung fee moi chan = 0.5*c_i*|dw| (c_i = chi phi CO HUONG/vong cua nhom i)."""
    D, fwd, lo24, hi24, fsum = panel["D"], panel["fwd"], panel["lo24"], panel["hi24"], panel["fsum"]
    n, NS = W.shape
    gross = np.zeros(n); fund = np.zeros(n); fee = np.zeros(n)
    to_g = np.zeros((n, 3))
    legs = []; leg_i = []
    Wprev = np.zeros(NS)
    for t in range(n):
        w = W[t]
        if not np.any(w):
            Wprev = np.zeros(NS)
            continue
        s = fwd[t].copy()
        if use_stop:
            bad = np.isfinite(lo24[t]) | np.isfinite(hi24[t])
            with np.errstate(invalid="ignore"):
                dwn = np.where(np.isfinite(lo24[t]), lo24[t] / D[t] - 1.0, np.nan)
                up = np.where(np.isfinite(hi24[t]), hi24[t] / D[t] - 1.0, np.nan)
            sl = np.where(np.isfinite(s), s, 0.0)
            sl = np.where((dwn < -STOP) & (w > 0), -STOP - STOP_SLIP, sl)
            sl = np.where((up > STOP) & (w < 0), STOP + STOP_SLIP, sl)
            s = np.where(np.isfinite(s), sl, s)
            s = np.where(~np.isfinite(s) & (dwn < -STOP) & (w > 0), -STOP - STOP_SLIP, s)
            s = np.where(~np.isfinite(s) & (up > STOP) & (w < 0), STOP + STOP_SLIP, s)
        s = np.where(np.isfinite(s), s, 0.0)
        pnl = w * s
        gross[t] = pnl.sum()
        f = np.where(np.isfinite(fsum[t]), fsum[t], 0.0)
        fund[t] = float((-w * f).sum())
        dw = np.abs(W[t] - Wprev)
        feeamt = 0.5 * cvec * dw
        fee[t] = float(feeamt.sum())
        for k in range(3):
            to_g[t, k] = 0.5 * dw[(cvec > 0) & (cg == k)].sum()
        for i in np.flatnonzero(w != 0):
            legs.append(pnl[i] + (-w[i] * f[i])); leg_i.append(i)
        for i in np.flatnonzero(dw > 0):
            legs.append(-feeamt[i]); leg_i.append(i)
        Wprev = w
    return gross, fund, fee, net_of(gross, fund, fee), to_g, np.asarray(legs), np.asarray(leg_i, dtype=np.int64)


def net_of(g, f, fe):
    return g + f - fe


def main():
    t0 = time.time()
    z = np.load(PANEL + "/panel.npz")
    panel = {k: z[k] for k in z.files}
    meta = json.load(open(PANEL + "/meta.json"))
    names = meta["sym_names"]
    c2 = json.load(open(COST2))
    global cg
    cg = groups_from_panel(panel)
    cvecs = {}
    for S in ("700", "2000", "5000"):
        for kq in ("k0.5", "k0.9"):
            v = np.zeros(panel["D"].shape[1])
            for gi, g in enumerate(["G1", "G2", "G3"]):
                v[cg == gi] = c2["C_group"][S][g][kq] / 100.0     # % -> fraction/vong
            cvecs["%s_%s" % (S, kq)] = v
    cf = np.zeros(panel["D"].shape[1])
    for i in range(len(cf)):
        if cg[i] >= 0:
            cf[i] = c2["C"]["2000"]["k0.5"] / 100.0
    E, uni = rt.build_eligible(panel, panel)
    D = panel["D"]
    sl = slice(rt.T0D, rt.T1D + 1)

    books = {}
    for nm in rt.SIGNALS:
        X = rt.factor_matrix(panel, nm, D)
        W, _ = rt.build_book(X, E, band=2)
        books[nm] = W
        print("book %s done (%.0fs)" % (nm, time.time() - t0), flush=True)

    Wew = np.zeros_like(D, dtype=np.float64)
    for nm in rt.SIGNALS:
        Wew += books[nm] / len(rt.SIGNALS)
    to = np.zeros(D.shape[0])
    for nm in rt.SIGNALS:
        to += rt.turnover(books[nm]) / len(rt.SIGNALS)   # dung dinh nghia cua run_trackb

    res = dict(prereg="docs/prereg/PREREG_BOOK_COST2.md", commit_prereg="b8bcca9",
               cost_source="docs/result/book_cost2.json",
               cost_flat_pct=c2["C"]["2000"]["k0.5"], n_days=int(len(to[sl])), cases={})
    print("\n===== BOOK_EW o cac muc phi =====")
    NC = np.full(len(cf), 0.00173)
    cases = [("cost2_directed_k0.5", cvecs["2000_k0.5"]), ("cost2_stress_5000_k0.9", cvecs["5000_k0.9"]),
             ("fee_flat_0.173", NC), ("fee_flat_0.414", np.full(len(cf), 0.00414)),
             ("fee_flat_0.757", np.full(len(cf), 0.00757))]
    for tag, cvec in cases:
        g = np.zeros_like(to); f = np.zeros_like(to); fe = np.zeros_like(to)
        L = []; LI = []
        for nm in rt.SIGNALS:
            gg, ff, fe2, nn, tg, lg, lgi = pnl_group(panel, books[nm], cvec)
            g += gg / len(rt.SIGNALS); f += ff / len(rt.SIGNALS); fe += fe2 / len(rt.SIGNALS)
            L.append(lg / len(rt.SIGNALS)); LI.append(lgi)
        legs = np.concatenate(L); leg_i = np.concatenate(LI)
        o = rt.summarise(tag, net_of(g, f, fe)[sl], g[sl], f[sl], fe[sl], to[sl], legs, panel, leg_i)
        o["fee_avg_pct_per_rt"] = float(np.mean(cvec[cg >= 0])) * 100.0
        res["cases"][tag] = o
        print("%-22s gross=%+.4f%% fund=%+.4f%% fee=%.4f%% net=%+.4f%%/d TO=%.3f "
              "CIraw=[%+.4f,%+.4f] MDE80=%.4f (a)%s (b')%s" %
              (tag, o["gross_per_day"] * 100, o["fund_per_day"] * 100, o["fee_per_day"] * 100,
               o["net_per_day"] * 100, o["turnover_per_day"], o["ci_raw"]["ci_lo"] * 100,
               o["ci_raw"]["ci_hi"] * 100, o["mde_p80"] * 100,
               "PASS" if o["rao"]["a_pass"] else "FAIL", "PASS" if o["rao"]["b_pass"] else "FAIL"), flush=True)

    # ---- BOOK CON o chi phi co huong (de thay book nao net duong) ----
    res["subbooks_cost2"] = {}
    for nm in rt.SIGNALS:
        gg, ff, fe2, nn, tg, lg, lgi = pnl_group(panel, books[nm], cvecs["2000_k0.5"])
        tow = rt.turnover(books[nm])
        o = rt.summarise(nm, net_of(gg, ff, fe2)[sl], gg[sl], ff[sl], fe2[sl], tow[sl], lg, panel, lgi)
        o["net_at_0.414"] = float((gg + ff)[sl].mean() - tow[sl].mean() * 0.00414) * 100
        res["subbooks_cost2"][nm] = o
        print("  sub %-9s net(cost2)=%+.4f%%/d TO=%.3f CI=[%+.4f,%+.4f] net@0.414=%+.4f%% (a)%s (b')%s" %
              (nm, o["net_per_day"] * 100, o["turnover_per_day"], o["ci_raw"]["ci_lo"] * 100,
               o["ci_raw"]["ci_hi"] * 100, o["net_at_0.414"],
               "PASS" if o["rao"]["a_pass"] else "FAIL", "PASS" if o["rao"]["b_pass"] else "FAIL"), flush=True)

    # ---- doi chung ngau nhien: net tai chi phi co huong (dung so cua step1: control fund ~0) ----
    R = json.load(open("/home/ubuntu/src/BinanceFuturesJava/docs/result/trackb_step1.json"))["rand"]
    be_ctrl_fund = 0.0   # control: net = gross - fee (fund ~ 0, da kiem)
    cf_flat = c2["C"]["2000"]["k0.5"] / 100.0
    res["rand"] = dict(ctrl_gross_pct=R["gross_mean"] * 100, ctrl_fund_pct=be_ctrl_fund,
                       ctrl_to=R["to_mean"],
                       ctrl_net_at_cost2_pct=(R["gross_mean"] + be_ctrl_fund - R["to_mean"] * cf_flat) * 100,
                       book_gross_pct=R["book_gross"] * 100, book_to=R["book_to"],
                       book_net_at_cost2_pct=(R["book_gross"] + be_ctrl_fund - R["book_to"] * cf_flat) * 100,
                       gross_gap_pct=(R["book_gross"] - R["gross_mean"]) * 100,
                       note="giu nguyen ket luan cu: chenh GROSS chi +0,076%/d")
    # ---- hoa von phi moi + so sanh 3 muc ----
    g_ew = np.zeros_like(to); f_ew = np.zeros_like(to)
    for nm in rt.SIGNALS:
        gg, ff, fe2, nn, tg, lg, lgi = pnl_group(panel, books[nm], cf * 0.0)
        g_ew += gg / len(rt.SIGNALS); f_ew += ff / len(rt.SIGNALS)
    be = float((g_ew + f_ew)[sl].mean() / to[sl].mean())
    res["breakeven_fee_rt_pct"] = be * 100
    res["net_at_0.173_rule"] = float((g_ew + f_ew)[sl].mean() - to[sl].mean() * 0.00173) * 100
    res["verdict"] = dict(
        net_cost2_pct=res["cases"]["cost2_directed_k0.5"]["net_per_day"] * 100,
        ci_raw=[res["cases"]["cost2_directed_k0.5"]["ci_raw"]["ci_lo"] * 100,
                res["cases"]["cost2_directed_k0.5"]["ci_raw"]["ci_hi"] * 100],
        breakeven_pct=be * 100,
        gate_a=bool(res["cases"]["cost2_directed_k0.5"]["rao"]["a_pass"]),
        gate_b=bool(res["cases"]["cost2_directed_k0.5"]["rao"]["b_pass"]),
        cost_le_breakeven=bool(res["cost_flat_pct"] <= be * 100))
    json.dump(res, open(OUTJ, "w"), ensure_ascii=False, indent=1, default=float)
    print("\nHOAVON %.4f%%/vong | net(cost2)=%+.4f%%/d CI=%s | rand: ctrl@cost2=%+.4f%% book@cost2=%+.4f%% gross_gap=%+.4f%%" %
          (be * 100, res["verdict"]["net_cost2_pct"], res["verdict"]["ci_raw"],
           res["rand"]["ctrl_net_at_cost2_pct"], res["rand"]["book_net_at_cost2_pct"],
           res["rand"]["gross_gap_pct"]))
    print("WROTE %s (%.0fs)" % (OUTJ, time.time() - t0))


if __name__ == "__main__":
    main()
