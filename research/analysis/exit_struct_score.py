#!/usr/bin/env python3
"""EXIT-STRUCT scorer — docs/prereg/PREREG_EXIT_STRUCT.md.

Cham A0..A3 tren NEN sel15:
  (a) %PnL top-1% <= 15% | (b') bo top-50% > 0 | q* | median | tf_5/tf_10
  MAT CAN XUNG: mean|lo|/mean lai (return/leg) + sign%>0   <- chi so QUYET DINH
  3 chi so martingale: (1) lo lon nhat 1 vi the/1 coin (tung nam) (2) conc 1 coin >15%?
                       (3) so coin "chet" hoan toan (cum pnl < 0)
  + 5 thau chuan {tf_5, loss_mean, wl_ratio, median, conc_5} + 4 rate {TSloss%, mP|SM, mP|SL, mMargin}
  + rao cu theo nam (maxDD<=40 / UW<=250 / qmin>=-20 / 0 nam am) + CI vs A0 (block-72h, 2000, seed 20260905).

THUAN PYTHON OFFLINE tren printDone.csv DA CO. KHONG train/sim/Java. DEV only <=2025-12-31. Output NHO.

  python3 exit_struct_score.py [--json docs/result/RESULT_EXIT_STRUCT.json]
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gd92xexit_score as G

KOUT = "/home/ubuntu/kaggle_sim/out"
DEV_END = pd.Timestamp("2025-12-31 23:59")
SEED_EQ, NREP_EQ, BLOCK_EQ, CAP0 = 20260903, 2000, 21, 35000.0
KARMS = 3                      # inflate(k) cho A_x vs A0
W_INFLATE = math.sqrt(2.0 * math.log(KARMS))
A0 = "cd-sel15"
ARMS = [("A0", "cd-sel15"), ("A1", "xs-a1"), ("A2", "xs-a2"), ("A3", "xs-a3")]


def load(tag):
    d = G.trades(tag)                       # da co ts, t_end, profit, pnl, margin
    d = d[d.ts <= DEV_END].copy()
    return d


def tf_block(P):
    n = len(P)
    tot = float(P.sum())
    o = np.sort(P)[::-1]

    def tf(x):
        k = max(1, int(math.ceil(x / 100.0 * n)))
        return float(o[k:].sum())

    k1 = max(1, int(math.ceil(0.01 * n)))
    out = dict(n=n, sum_pnl=tot,
               share_top1_pct=float(o[:k1].sum() / tot * 100) if tot else float("nan"),
               tf5=float(o[max(1, int(math.ceil(.05 * n))):].mean()) if n > 1 else float("nan"),
               tf10=float(o[max(1, int(math.ceil(.10 * n))):].mean()) if n > 1 else float("nan"),
               median_leg=float(np.median(P)), sign_pct=float((P > 0).mean() * 100))
    out["tf50"] = tf(50)
    out["bottom_half_sum"] = tf(50)
    out["pass_a"] = bool(out["share_top1_pct"] <= 15.0)
    out["pass_b50"] = bool(tf(50) > 0)
    for x in (5, 10, 20, 30, 40, 50):
        out["drop%d" % x] = tf(x)
    qs = None
    for q in np.arange(0.005, 0.9555, 0.005):
        if tf(q * 100) <= 0:
            qs = float(round(q * 100, 2)); break
    out["q_breakeven_pct"] = qs
    return out


def rulers_of(x):
    x = np.asarray(x, float)
    n = len(x)
    o = np.sort(x)[::-1]
    q = np.percentile(x, [1, 5, 25, 75, 90, 95, 99])
    lo = x[x < 0]; win = x[x > 0]
    r = dict(
        median=float(np.median(x)),
        sign_frac=float((x > 0).mean() * 100),
        tf_5=float(o[max(1, int(math.ceil(.05 * n))):].mean()),
        tf_10=float(o[max(1, int(math.ceil(.10 * n))):].mean()),
        conc_5=float(o[:max(1, int(math.ceil(.05 * n)))].sum() / x.sum()),
        loss_mean=float(-lo.mean()) if len(lo) else float("nan"),
        win_mean=float(win.mean()) if len(win) else float("nan"),
        asym=float((-lo.mean()) / win.mean()) if (len(win) and len(lo)) else float("nan"),
        max_loss=float(-o[-1]) if n else float("nan"),
    )
    return r


def rates_of_run(d):
    sm = d.status == "STOP_MARKET_DONE"; sl = d.status == "STOP_LOSS_DONE"
    return dict(tsloss=100.0 * sl.mean(),
                mp_sm=float(d.loc[sm, "profit"].mean()) if sm.any() else float("nan"),
                mp_sl=float(d.loc[sl, "profit"].mean()) if sl.any() else float("nan"),
                margin=float(d.margin.mean()))


def martingale(d, tag):
    """3 chi so martingale (PREREG §5.5)."""
    dd = d.copy()
    dd["yr"] = dd.t_end.dt.year
    cl = dd.groupby(["sym", "end"]).agg(pnl=("pnl", "sum"), margin=("margin", "sum"),
                                        yr=("yr", "first"), legs=("pnl", "size")).reset_index()
    cl["loss"] = np.where(cl.pnl < 0, -cl.pnl, 0.0)
    per_year = {}
    for y, g in cl.groupby("yr"):
        per_year[int(y)] = dict(n_pos=int(len(g)), worst_loss=float(g.loss.max()),
                                worst_sym=str(g.loc[g.loss.idxmax(), "sym"]) if g.loss.max() > 0 else None)
    # conc 1 coin (% equity tai ngay mo)
    eq = G.equity(tag)
    dd["day"] = dd["start"].astype(str).str.slice(0, 8)
    dd["eq"] = dd["day"].map(eq)
    cc = dd.groupby(["sym", "end"]).agg(tot=("margin", "sum"), eq0=("eq", "last")).reset_index()
    conc1 = float((cc.tot / cc.eq0 * 100).max()) if len(cc) else float("nan")
    # coin "chet" hoan toan: tong pnl coin (ca ky) < 0
    coin = cl.groupby("sym").pnl.sum()
    dead = coin[coin < 0]
    return dict(worst_pos_loss_all=float(cl.loss.max()),
                worst_pos_loss_by_year=per_year,
                conc_1coin_pct=conc1, conc_1coin_over15=bool(conc1 > 15.0),
                n_pos=int(len(cl)), n_coin=int(coin.size),
                n_dead_coins=int(dead.size), dead_coins_losses=float(dead.sum()),
                dead_coin_list=[str(s) for s in dead.sort_values().index[:8]])


def idxmat(n, blen, nrep, seed):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    off = np.arange(blen)
    return ((starts[:, :, None] + off[None, None, :]) % n).reshape(nrep, nb * blen)[:, :n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/RESULT_EXIT_STRUCT.json")
    a = ap.parse_args()

    rows, mart, rail, rao = {}, {}, {}, {}
    for lbl, tag in ARMS:
        try:
            s = G.summary(tag)
        except Exception as e:
            print("SKIP %s (%s): %s" % (lbl, tag, e)); continue
        d = load(tag)
        rao[lbl] = tf_block(d.pnl.to_numpy(float))
        rao_ret = tf_block((d.pnl / d.margin).to_numpy(float))
        rr = rulers_of((d.pnl / d.margin).to_numpy(float))
        rr_u = rulers_of(d.pnl.to_numpy(float))
        rows[lbl] = dict(tag=tag, n=s["n"], rao_ret=rao_ret, ndays=s["ndays"], eq=s["end"], cagr=s["cagr"],
                         maxdd=s["maxDD"], uw=s["uw"], qmin=s["qmin"], conc=s["conc"],
                         entry_month=s["n"] / s["ndays"] * 365.25 / 12.0,
                         sumpnl=s["sumpnl"], meanP=s["sumpnl"] / s["n"] if s["n"] else float("nan"),
                         asym=rr["asym"], asym_usdt=rr_u["asym"], sign_pct=rr["sign_frac"],
                         loss_mean=rr["loss_mean"], loss_mean_usdt=rr_u["loss_mean"], win_mean_usdt=rr_u["win_mean"],
                         win_mean=rr["win_mean"], tl_median=rr["median"], conc_5=rr["conc_5"],
                         max_loss_leg=rr["max_loss"], tf_5r=rr["tf_5"], tf_10r=rr["tf_10"],
                         rates=rates_of_run(d),
                         legs={k: int(v) for k, v in d.level.value_counts().items()})
        mart[lbl] = martingale(d, tag)
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

    print("=" * 118)
    hdr = "%-3s %-9s %5s %8s %8s %8s %5s %7s %7s %11s"
    print(hdr % ("arm", "tag", "n", "eq", "CAGR%", "maxDD%", "UW", "qmin", "conc%", "entry/thang"))
    for lbl, tag in ARMS:
        if lbl not in rows: continue
        r = rows[lbl]
        print(hdr % (lbl, r["tag"], r["n"], "%.0f" % r["eq"], "%+.2f" % r["cagr"], "%.2f" % r["maxdd"],
                     r["uw"], "%.2f" % r["qmin"], "%.2f" % r["conc"], "%.2f" % r["entry_month"]))

    print("\n" + "=" * 118)
    print("RAO OWNER (a) top-1%<=15% | (b') bo-50% >0  + q* | median | tf_5/tf_10  [pnl USDT]")
    hd = "%-3s %10s %9s %12s %9s %9s %9s %9s %8s"
    print(hd % ("arm", "%top1", "(a)", "bo-50%", "(b')", "q*%", "median", "tf_5", "tf_10"))
    for lbl, tag in ARMS:
        if lbl not in rao: continue
        r = rao[lbl]
        print(hd % (lbl, "%.2f" % r["share_top1_pct"], "PASS" if r["pass_a"] else "FAIL",
                    "%.0f" % r["tf50"], "PASS" if r["pass_b50"] else "FAIL",
                    ("%.1f" % r["q_breakeven_pct"]) if r["q_breakeven_pct"] else "-",
                    "%.1f" % r["median_leg"], "%.1f" % r["tf5"], "%.1f" % r["tf10"]))

    print("\n  [SIZE-NEUTRAL, P = pnl/margin (lai suat/leg)] — A2/A3 chay ~1/6 size vi grid OFF bo he so DCA_GRID_SCALE=6")
    print(hd % ("arm", "%top1", "(a)", "bo-50%", "(b')", "q*%", "median", "tf_5", "tf_10"))
    for lbl, tag in ARMS:
        if lbl not in rows: continue
        rr = rows[lbl]["rao_ret"]
        print(hd % (lbl, "%.2f" % rr["share_top1_pct"], "PASS" if rr["pass_a"] else "FAIL",
                    "%.2f" % rr["tf50"], "PASS" if rr["pass_b50"] else "FAIL",
                    ("%.1f" % rr["q_breakeven_pct"]) if rr["q_breakeven_pct"] else "-",
                    "%.4f" % rr["median_leg"], "%.4f" % rr["tf5"], "%.4f" % rr["tf10"]))

    print("\n" + "=" * 118)
    print("MAT CAN XUNG (asym=return/leg, asymU=USDT) + 5 thau chuan + 4 rate")
    hd2 = "%-3s %7s %7s %10s %10s %9s %8s %9s %9s %9s %9s %8s"
    print(hd2 % ("arm", "asym", "asymU", "sign%", "loss_mean", "win_mean", "median", "conc_5", "tf_5", "TSloss%", "mP|SM", "mP|SL"))
    for lbl, tag in ARMS:
        if lbl not in rows: continue
        r = rows[lbl]; q = r["rates"]
        print(hd2 % (lbl, "%.3f" % r["asym"], "%.2f" % r["asym_usdt"], "%.1f" % r["sign_pct"],
                     "%+.5f" % r["loss_mean"], "%+.5f" % r["win_mean"], "%+.5f" % r["tl_median"], "%.3f" % r["conc_5"],
                     "%+.5f" % r["tf_5r"], "%.1f" % q["tsloss"], "%+.1f" % q["mp_sm"], "%+.1f" % q["mp_sl"]))

    print("\n" + "=" * 118)
    print("3 CHI SO MARTINGALE")
    hd3 = "%-3s %12s %26s %12s %14s"
    print(hd3 % ("arm", "worstPos(USDT)", "worst/nam (sym)", "conc1coin%>15", "coin chet"))
    for lbl, tag in ARMS:
        if lbl not in mart: continue
        m = mart[lbl]
        wy = " ".join("%d:%s(%.0f)" % (y, v["worst_sym"], v["worst_loss"]) for y, v in sorted(m["worst_pos_loss_by_year"].items()) if v["worst_loss"] > 0)
        print(hd3 % (lbl, "%.0f" % m["worst_pos_loss_all"], wy[:26], "%.2f %s" % (m["conc_1coin_pct"], "VUOT" if m["conc_1coin_over15"] else "ok"),
                     "%d/%d (%.0f)" % (m["n_dead_coins"], m["n_coin"], m["dead_coins_losses"])))

    print("\n" + "=" * 118)
    print("RAO CU theo nam (maxDD<=40 / UW<=250 / qmin>=-20 / 0 nam am)")
    for lbl, tag in ARMS:
        if lbl not in rail: continue
        print("  %-3s %s" % (lbl, "PASS" if rail[lbl]["pass_"] else "VI PHAM: " + ",".join(rail[lbl]["violations"])))

    print("\n" + "=" * 118)
    print("CI vs A0 (block-72h, 2000 rep, seed 20260905) + dCAGR paired (block-21, seed 20260903) nguong %.4f" % W_INFLATE)
    Emap = {}
    for lbl, tag in ARMS:
        try:
            Emap[lbl] = G.equity(tag)
        except Exception:
            pass
    LR = {l: np.diff(np.log(np.concatenate([[CAP0], Emap[l].values.astype(float)]))) for l in Emap}
    N = len(Emap["A0"])
    cagr = lambda lr: (np.exp(lr.sum() * 365.0 / N) - 1.0) * 100
    ci_out = {}
    for lbl, tag in ARMS:
        if lbl == "A0" or lbl not in rows: continue
        pair = G.ci_pair(tag, A0, W_INFLATE)
        ix = idxmat(N, BLOCK_EQ, NREP_EQ, SEED_EQ)
        da = (np.exp(LR[lbl][ix].sum(axis=1) * 365.0 / N) - np.exp(LR["A0"][ix].sum(axis=1) * 365.0 / N)) * 100
        sd = float(da.std(ddof=1)); thr = W_INFLATE * sd
        d = cagr(LR[lbl]) - cagr(LR["A0"])
        ci_out[lbl] = dict(dCAGR=float(d), sd=sd, thr=thr, pass_=bool(d > thr),
                           p=float((da > 0).mean()),
                           rates={k: [round(v[0], 4), round(v[1], 4), round(v[2], 4), bool(v[3])] for k, v in pair.items()})
        print("  %-3s dCAGR %+.2f pp (sd %.2f, nguong +%.2f, P>0 %.3f) => %s" % (lbl, d, sd, thr, (da > 0).mean(), "DAT" if d > thr else "khong"))
        print("      rates: " + " ".join("%s %.3f[%.3f,%.3f]%s" % (k, v[0], v[1], v[2], "*" if v[3] else "") for k, v in pair.items()))

    out = dict(prereg="docs/prereg/PREREG_EXIT_STRUCT.md", base="sel15", k=KARMS,
               inflate=W_INFLATE, arms=rows, rao=rao, martingale=mart, rails=rail, ci_vs_A0=ci_out)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("\nJSON -> %s (%.1f KB)" % (a.json, os.path.getsize(a.json) / 1024.0))


if __name__ == "__main__":
    main()
