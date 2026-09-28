#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RULERS_UNIT — do lai Rao (a)/(b') o 3 DON VI cho Track B (top-200, nhip ngay, band=2, phi co huong).

U1 = CAP VI THE (coin-ngay) [CHINH]  · U2 = CAP NGAY (book) [doi chieu] · U0 = tai lap dinh nghia vong truoc.
Pre-reg: docs/prereg/PREREG_RULERS_UNIT.md (commit 107d411) — chot TRUOC khi do.
Thuan Python offline, 0 train/0 sim, DEV<=2025-12-31, khong cham 2026.
"""
import json
import math
import sys
import time

import numpy as np

TRACKB = "/home/ubuntu/src/BinanceFuturesJava/research/trackb"
sys.path.insert(0, TRACKB)
import run_trackb as rt  # noqa: E402

PANEL = "/tmp/trackb"
COST2 = "/home/ubuntu/src/BinanceFuturesJava/docs/result/book_cost2.json"
OUTJ = "/home/ubuntu/src/BinanceFuturesJava/docs/result/rulers_unit.json"
SEED, NREP, BLOCK, K = 20260905, 2000, 10, 8
RSEED, NR = 20260928, 200
STOP, STOP_SLIP = rt.STOP, rt.STOP_SLIP
T0D, T1D = rt.T0D, rt.T1D


def inflate(k):
    return 1.0 if k < 2 else math.sqrt(2.0 * math.log(k))


def groups_from_panel(panel):
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


def cost_vec(panel, c2, S="2000", kq="k0.5"):
    cg = groups_from_panel(panel)
    v = np.zeros(panel["D"].shape[1])
    for gi, g in enumerate(["G1", "G2", "G3"]):
        v[cg == gi] = c2["C_group"][S][g][kq] / 100.0
    return v


def leg_arrays(W, panel, cvec, skip_empty=True):
    """Tra ve (day, coin, val) cho U1 (hoat dong: w!=0 hoac dw!=0; val RONG) va (oday, oval) cho U0.

    skip_empty=True  -> tai lap DUNG quy uoc `run_trackb.book_pnl` (ngay book TRONG => bo qua, reset Wprev)
    skip_empty=False -> tinh ca phi THOAT cua ngay book trong (Sigma = net dung nghia)
    """
    D, fwd, lo24, hi24, fsum = panel["D"], panel["fwd"], panel["lo24"], panel["hi24"], panel["fsum"]
    n, NS = W.shape
    day, coin, val = [], [], []
    oday, oval = [], []
    Wprev = np.zeros(NS)
    for t in range(n):
        w = W[t]
        dw = np.abs(w - Wprev)
        if not np.any(w):
            Wprev = np.zeros(NS)
            if skip_empty or not np.any(dw):
                continue
        s = fwd[t].copy()
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
        f = np.where(np.isfinite(fsum[t]), fsum[t], 0.0)
        feeamt = 0.5 * cvec * dw
        act = (w != 0) | (dw != 0)
        for i in np.flatnonzero(act):
            day.append(t)
            coin.append(i)
            val.append(pnl[i] + (-w[i] * f[i]) - feeamt[i])
        for i in np.flatnonzero(w != 0):
            oday.append(t)
            oval.append(pnl[i] + (-w[i] * f[i]))
        for i in np.flatnonzero(dw > 0):
            oday.append(t)
            oval.append(-feeamt[i])
        Wprev = w
    return (np.asarray(day, np.int64), np.asarray(coin, np.int64), np.asarray(val, np.float64),
            np.asarray(oday, np.int64), np.asarray(oval, np.float64))


# ---------------- thong ke + CI ----------------
def point_stats(v):
    v = np.sort(np.asarray(v, np.float64))[::-1]
    n = len(v)
    S = float(v.sum())
    k1 = max(1, int(math.ceil(0.01 * n)))
    k5 = max(1, int(math.ceil(0.05 * n)))
    k25 = max(1, int(math.ceil(0.25 * n)))
    top1 = float(v[:k1].sum())
    top5 = float(v[:k5].sum())
    top25 = float(v[:k25].sum())
    pos = v[v > 0]
    neg = v[v < 0]
    posm = float(pos.mean()) if len(pos) else float("nan")
    negm = float((-neg).mean()) if len(neg) else float("nan")
    q = None
    for pct in np.arange(0.5, 100.0, 0.5):
        kk = max(1, int(math.ceil(pct / 100.0 * n)))
        if v[kk:].sum() <= 0:
            q = float(pct)
            break
    return dict(n=int(n), sum=S,
                share_top1_pct=(top1 / S * 100.0) if S > 0 else float("nan"),
                a_defined=bool(S > 0), tf25=float(S - top25), tf_5=float(S - top5),
                q_star=q,
                asym=(negm / posm) if (len(pos) and posm > 0 and len(neg)) else float("nan"),
                wl_ratio=(posm / negm) if (len(neg) and negm > 0 and len(pos)) else float("nan"),
                winrate=float((v > 0).mean()), median=float(np.median(v)),
                loss_mean=negm, conc_5_pct=(top5 / S * 100.0) if S > 0 else float("nan"),
                mean=float(S / n))


def fast_stats(v):
    """Chi tinh cac luong can cho CI (khong sort toan phan)."""
    n = len(v)
    S = float(v.sum())
    k1 = max(1, int(math.ceil(0.01 * n)))
    k25 = max(1, int(math.ceil(0.25 * n)))
    p1 = np.partition(v, n - k1)[n - k1:]
    p25 = np.partition(v, n - k25)[n - k25:]
    top1 = float(p1.sum())
    top25 = float(p25.sum())
    pos = v[v > 0]
    neg = v[v < 0]
    posm = float(pos.mean()) if len(pos) else float("nan")
    negm = float((-neg).mean()) if len(neg) else float("nan")
    return dict(n=n, mean=float(S / n), tf25=float(S - top25),
                share_top1_pct=(top1 / S * 100.0) if S > 0 else float("nan"),
                asym=(negm / posm) if (len(pos) and posm > 0 and len(neg)) else float("nan"),
                winrate=float((v > 0).mean()))


def bounds_by_day(day, nd):
    day = np.asarray(day)
    order = np.argsort(day, kind="stable")
    d = day[order]
    b = np.searchsorted(d, np.arange(nd + 1))
    return b, order


def boot_ci(v, day, nd, metrics, seed=SEED, nrep=NREP, block=BLOCK, k=K):
    v = np.asarray(v, np.float64)
    b, order = bounds_by_day(day, nd)
    v = v[order]
    nb = int(math.ceil(nd / block))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nb, (nrep, nb))
    acc = {m: np.empty(nrep) for m in metrics}
    for r in range(nrep):
        parts = [v[b[bb * block]:b[min((bb + 1) * block, nd)]] for bb in idx[r]]
        s = np.concatenate(parts)
        st = fast_stats(s)
        for m in metrics:
            acc[m][r] = st[m]
    out = {}
    ps = point_stats(v)
    for m in metrics:
        a = acc[m]
        a = a[np.isfinite(a)]
        lo, hi = np.percentile(a, [2.5, 97.5])
        p_obs = ps[m]
        half = float((hi - lo) / 2.0)
        out[m] = dict(obs=p_obs, ci_raw=[float(lo), float(hi)], half_raw=half,
                      ci_infl_lo=float(p_obs - half * inflate(k)), ci_infl_hi=float(p_obs + half * inflate(k)),
                      p_gt0=float((a > 0).mean()), med=float(np.median(a)))
    return out


def main():
    t0 = time.time()
    z = np.load(PANEL + "/panel.npz")
    panel = {k: z[k] for k in z.files}
    c2 = json.load(open(COST2))
    cvec = cost_vec(panel, c2)
    E, uni = rt.build_eligible(panel, panel)
    nd = T1D - T0D + 1          # 1460 ngay trong cua so
    sl = slice(T0D, T1D + 1)

    books = {}
    legs_sig = {}
    for nm in rt.SIGNALS:
        X = rt.factor_matrix(panel, nm, panel["D"])
        W, _ = rt.build_book(X, E, band=2)
        books[nm] = W
        legs_sig[nm] = leg_arrays(W, panel, cvec)
        print("book %s (%.0fs)" % (nm, time.time() - t0), flush=True)

    # ---- U1/U0 cho BOOK_EW = trung binh 4 book con theo o (ngay, coin) ----
    NS = panel["D"].shape[1]
    keys = np.concatenate([legs_sig[nm][0] * NS + legs_sig[nm][1] for nm in rt.SIGNALS])
    vals = np.concatenate([legs_sig[nm][2] for nm in rt.SIGNALS]) / len(rt.SIGNALS)
    daysew = np.concatenate([legs_sig[nm][0] for nm in rt.SIGNALS])
    u, inv = np.unique(keys, return_inverse=True)
    agg = np.zeros(len(u))
    np.add.at(agg, inv, vals)
    ew_day = (u // NS).astype(np.int64)
    ew_val = agg
    # U0 EW: chia 4 va noi tiep (tai lap vong truoc)
    ew_o_day = np.concatenate([legs_sig[nm][3] for nm in rt.SIGNALS])
    ew_o_val = np.concatenate([legs_sig[nm][4] for nm in rt.SIGNALS]) / len(rt.SIGNALS)

    # ---- U2 (ngay) ----
    def day_net(W):
        D, fwd, lo24, hi24, fsum = (panel["D"], panel["fwd"], panel["lo24"], panel["hi24"], panel["fsum"])
        n = W.shape[0]
        out = np.zeros(n)
        Wprev = np.zeros(W.shape[1])
        for t in range(n):
            w = W[t]
            dw = np.abs(w - Wprev)
            if not np.any(w):
                Wprev = np.zeros(W.shape[1])
                continue
            s = fwd[t].copy()
            with np.errstate(invalid="ignore"):
                dwn = np.where(np.isfinite(lo24[t]), lo24[t] / D[t] - 1.0, np.nan)
                up = np.where(np.isfinite(hi24[t]), hi24[t] / D[t] - 1.0, np.nan)
            sl2 = np.where(np.isfinite(s), s, 0.0)
            sl2 = np.where((dwn < -STOP) & (w > 0), -STOP - STOP_SLIP, sl2)
            sl2 = np.where((up > STOP) & (w < 0), STOP + STOP_SLIP, sl2)
            s = np.where(np.isfinite(s), sl2, s)
            s = np.where(~np.isfinite(s) & (dwn < -STOP) & (w > 0), -STOP - STOP_SLIP, s)
            s = np.where(~np.isfinite(s) & (up > STOP) & (w < 0), STOP + STOP_SLIP, s)
            s = np.where(np.isfinite(s), s, 0.0)
            pnl = w * s
            f = np.where(np.isfinite(fsum[t]), fsum[t], 0.0)
            out[t] = pnl.sum() + float((-w * f).sum()) - float((0.5 * cvec * dw).sum())
            Wprev = w
        return out

    day_ew = np.zeros(panel["D"].shape[0])
    day_sig = {}
    for nm in rt.SIGNALS:
        dd = day_net(books[nm])
        day_sig[nm] = dd
        day_ew += dd / len(rt.SIGNALS)

    # ---- tinh 3 don vi ----
    objects = {nm: dict(U1=(legs_sig[nm][0] - T0D, legs_sig[nm][2]),
                        U0=(legs_sig[nm][3] - T0D, legs_sig[nm][4]),
                        U2=(np.arange(nd), day_sig[nm][sl])) for nm in rt.SIGNALS}
    objects["BOOK_EW"] = dict(U1=(ew_day - T0D, ew_val), U0=(ew_o_day - T0D, ew_o_val),
                              U2=(np.arange(nd), day_ew[sl]))

    metrics = ["share_top1_pct", "tf25", "asym", "winrate", "mean"]
    res = dict(prereg="docs/prereg/PREREG_RULERS_UNIT.md", commit_prereg="107d411",
               cost="cost2_directed 2000 k0.5", n_days=int(nd),
               units=dict(U0="tai lap vong truoc (vi the + phi tach roi, /4)",
                          U1="CAP VI THE coin-ngay (rong, 1 leg/o (coin,ngay) hoat dong)",
                          U2="CAP NGAY (book)"),
               objects={}, )
    print("\n===== 3 DON VI x 6 object =====")
    hdr = "%-10s %-4s %8s %10s %10s %8s %8s %8s %9s %9s %8s"
    print(hdr % ("object", "unit", "n", "sum", "shareT1%", "TF25", "tf_5", "q*", "asym", "winrate", "median"))
    for nm, dd in objects.items():
        res["objects"][nm] = {}
        for unit in ("U1", "U2", "U0"):
            d, v = dd[unit]
            st = point_stats(v)
            st["net_per_day"] = st["sum"] / nd
            ci = boot_ci(v, d, nd, metrics)
            st["ci"] = ci
            st["a_pass"] = bool(st["a_defined"] and st["share_top1_pct"] <= 15.0)
            st["b_pass"] = bool(st["tf25"] > 0)
            res["objects"][nm][unit] = st
            print(hdr % (nm, unit, st["n"], "%.3f" % st["sum"],
                         "%.2f" % st["share_top1_pct"] if st["a_defined"] else "N/A",
                         "%+.3f" % st["tf25"], "%+.3f" % st["tf_5"],
                         "%s" % st["q_star"], "%.3f" % st["asym"], "%.3f" % st["winrate"],
                         "%.5f" % st["median"]))
        for u in ("U1", "U2", "U0"):
            o = res["objects"][nm][u]
            c = o["ci"]
            print("   [%s %-7s] (a)%s shareT1=%.2f CIraw=[%.2f,%.2f] CIinf=[%.2f,%.2f] | (b')%s TF25=%+.3f CIraw=[%+.3f,%+.3f] CIinf=[%+.3f,%+.3f] p(>0)=%.3f" %
                  (nm, u, "PASS" if o["a_pass"] else "FAIL",
                   o["share_top1_pct"] if o["a_defined"] else float("nan"),
                   c["share_top1_pct"]["ci_raw"][0], c["share_top1_pct"]["ci_raw"][1],
                   c["share_top1_pct"]["ci_infl_lo"], c["share_top1_pct"]["ci_infl_hi"],
                   "PASS" if o["b_pass"] else "FAIL", o["tf25"],
                   c["tf25"]["ci_raw"][0], c["tf25"]["ci_raw"][1],
                   c["tf25"]["ci_infl_lo"], c["tf25"]["ci_infl_hi"], c["tf25"]["p_gt0"]))

    # ---- doi chung ngau nhien: n=200, seed 20260928, o CA HAI don vi ----
    npos_book = None
    Wew = np.zeros_like(panel["D"])
    for nm in rt.SIGNALS:
        Wew += (books[nm] != 0) / float(len(rt.SIGNALS))
    npos_med = float(np.median(Wew[T0D:T1D + 1].sum(1)))
    nlong = int(round(npos_med / 2))
    print("\n===== DOI CHUNG NGau NHIEN n=%d (nlong=%d) =====" % (NR, nlong), flush=True)
    rng = np.random.default_rng(RSEED)
    rg = {u: {m: [] for m in ("mean", "net_per_day", "share_top1_pct", "tf25")} for u in ("U1", "U2")}
    apass = {"U1": 0, "U2": 0}; bpass = {"U1": 0, "U2": 0}; adef = {"U1": 0, "U2": 0}
    for r in range(NR):
        Wr = np.zeros_like(panel["D"])
        for t in range(T0D, T1D + 1):
            m = np.flatnonzero(E[t])
            if len(m) < 2 * nlong:
                continue
            pick = rng.choice(m, size=2 * nlong, replace=False)
            Wr[t, pick[:nlong]] = 0.5 / nlong
            Wr[t, pick[nlong:]] = -0.5 / nlong
        d, ci, v, od, ov = leg_arrays(Wr, panel, cvec)
        dd = day_net(Wr)
        st1 = point_stats(v); st2 = point_stats(dd[sl])
        for u, st in (("U1", st1), ("U2", st2)):
            rg[u]["mean"].append(st["mean"]); rg[u]["net_per_day"].append(st["sum"] / nd)
            rg[u]["share_top1_pct"].append(st["share_top1_pct"])
            rg[u]["tf25"].append(st["tf25"])
            apass[u] += int(st["a_defined"] and st["share_top1_pct"] <= 15.0)
            bpass[u] += int(st["tf25"] > 0)
            adef[u] += int(st["a_defined"])
    res["rand"] = {}
    for u in ("U1", "U2"):
        res["rand"][u] = {}
        for m in ("mean", "net_per_day", "share_top1_pct", "tf25"):
            a = np.asarray(rg[u][m], float); a = a[np.isfinite(a)]
            res["rand"][u][m] = dict(mean=float(a.mean()), p5=float(np.percentile(a, 5)),
                                      p95=float(np.percentile(a, 95)), n_ok=int(len(a))) if len(a) else None
        res["rand"][u]["a_pass_n"] = int(apass[u]); res["rand"][u]["b_pass_n"] = int(bpass[u])
        res["rand"][u]["a_defined_n"] = int(adef[u])
        print("  [%s] net/d mean=%+.4f%% p95=%+.4f%% | shareT1 %s | TF25 mean=%+.3f p95=%+.3f | (a)PASS %d/%d (b')PASS %d/%d" %
              (u, res["rand"][u]["net_per_day"]["mean"] * 100, res["rand"][u]["net_per_day"]["p95"] * 100,
               ("undef(Sum<=0)" if res["rand"][u]["share_top1_pct"] is None else
                "mean=%.1f p95=%.1f" % (res["rand"][u]["share_top1_pct"]["mean"],
                                        res["rand"][u]["share_top1_pct"]["p95"])),
               res["rand"][u]["tf25"]["mean"], res["rand"][u]["tf25"]["p95"],
               apass[u], NR, bpass[u], NR), flush=True)

    json.dump(res, open(OUTJ, "w"), ensure_ascii=False, indent=1, default=float)
    print("\nWROTE %s (%.0fs)" % (OUTJ, time.time() - t0))


if __name__ == "__main__":
    main()
