#!/usr/bin/env python3
"""TRACKB step 1b — SLEEVE market-neutral cross-section: book L/S, phi, hysteresis, tran squeeze,
Rao (a)/(b'), q*, asym, pnl_vol_norm, CI block, MDE, doi chung ngau nhien.

Pre-reg: docs/prereg/PREREG_TRACKB_CROSSSECTION.md (commit 642afbd) — chot TRUOC khi do.
Thuan Python offline, 0 train / 0 sim, chi DEV (2022-01-01 .. 2025-12-30).
Input /tmp/trackb/panel.npz (build_panel.py). Output /tmp/trackb/results.json + report txt (nho).
"""
import json
import math
import os
import time
from datetime import datetime, timezone

import numpy as np

OUT = "/tmp/trackb"
SEED = 20260905
RSEED = 20260928
NREP = 2000
CI_INFLATE_K = 8
BLOCK_D = 10                      # khoi 10 ngay
TOPK_UNIV = 200
MIN_ELIG = 50
FEE_RT = 0.0076
FEE_HALF = FEE_RT / 2.0
STOP = 0.10
STOP_SLIP = 0.005
T0D = 365                         # 2022-01-01
T1D = 1824                        # 2025-12-30 (hold ket thuc 2025-12-31)
SIGNALS = ["funding", "dOI", "vol", "reversal"]
REP = []


def say(s=""):
    REP.append(s)
    print(s, flush=True)


def inflate(k):
    return 1.0 if k < 2 else math.sqrt(2.0 * math.log(k))


# ---------------- block bootstrap ----------------
def blk_id(n, block=BLOCK_D):
    return np.arange(n) // block


def block_boot_mean(x, block=BLOCK_D, nrep=NREP, seed=SEED, inflate_k=1.0):
    x = np.asarray(x, dtype=np.float64)
    b = blk_id(len(x), block)
    nb = b.max() + 1
    s = np.bincount(b, weights=x, minlength=nb)
    c = np.bincount(b, minlength=nb).astype(np.float64)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nb, (nrep, nb))
    means = s[idx].sum(1) / c[idx].sum(1)
    obs = x.mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    half = (hi - lo) / 2.0 * inflate_k
    return dict(obs=float(obs), half=float(half), ci_lo=float(obs - half), ci_hi=float(obs + half),
                raw_half=float((hi - lo) / 2), p_gt0=float((means > 0).mean()))


def block_signflip(x, block=BLOCK_D, nrep=NREP, seed=SEED, nnull=500):
    x = np.asarray(x, dtype=np.float64)
    b = blk_id(len(x), block)
    nb = b.max() + 1
    bs = np.bincount(b, weights=x, minlength=nb)
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(nnull, nb))
    nullmean = (signs @ bs) / len(x)
    return float(x.mean()), float(nullmean.std()), float(np.percentile(np.abs(nullmean), 80))


def mde_p80(x, block=BLOCK_D, seed=SEED, nnull=500):
    """MDE(p80) = p80 cua nua-do-rong tren 500 chuoi null sign-flip (cung khoi)."""
    x = np.asarray(x, dtype=np.float64)
    b = blk_id(len(x), block)
    nb = b.max() + 1
    bs = np.bincount(b, weights=x, minlength=nb)
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(nnull, nb))
    nullmean = (signs @ bs) / len(x)
    half = np.abs(nullmean)
    return float(np.percentile(half, 80)), float(2.8 * nullmean.std())


# ---------------- Rao ----------------
def rao(net):
    net = np.asarray(net, dtype=np.float64)
    n = len(net)
    o = np.sort(net)[::-1]
    tot = net.sum()
    k1 = max(1, int(math.ceil(0.01 * n)))
    share_top1 = float(o[:k1].sum() / tot * 100) if tot != 0 else float("nan")
    # Σpnl <= 0 thi 'share top-1%' khong co nghia (dau am) -> danh dau N/A, khong tinh la PASS
    a_defined = bool(tot > 0)
    k25 = max(1, int(math.ceil(0.25 * n)))
    tf25 = float(o[k25:].sum())
    q = None
    for pct in np.arange(0.5, 100.0, 0.5):
        kk = max(1, int(math.ceil(pct / 100.0 * n)))
        if o[kk:].sum() <= 0:
            q = float(pct)
            break
    pos = net[net > 0]
    neg = net[net < 0]
    asym = float((-neg).mean() / pos.mean()) if len(pos) and pos.mean() > 0 else float("nan")
    return dict(n=n, sum=float(tot), share_top1_pct=share_top1,
                a_pass=bool(a_defined and share_top1 <= 15.0), a_defined=a_defined,
                tf25=tf25, b_pass=bool(tf25 > 0), q_star=q, asym=asym,
                winrate_leg=float((net > 0).mean()))


# ---------------- universe + signals ----------------
def build_eligible(P, panel):
    D, dv_med, dv_n = panel["D"], panel["dv_med"], panel["dv_n"]
    NS = D.shape[1]
    ok_liq = np.isfinite(dv_med) & (dv_n >= 12)
    order = np.argsort(np.where(ok_liq, dv_med, -1))[::-1]
    uni_static = set(order[:TOPK_UNIV].tolist())
    uni = np.zeros(NS, dtype=bool)
    uni[list(uni_static)] = True
    elig = np.zeros_like(D, dtype=bool)
    fin = np.isfinite(D)
    for t in range(T1D + 1):
        hist = fin[max(0, t - 30):t].sum(0) >= 30
        elig[t] = uni & hist & np.isfinite(D[t])
    elig[:T0D] = False
    return elig, uni_static


def factor_matrix(panel, name, D):
    if name == "funding":
        return panel["fsum"]
    if name == "dOI":
        return panel["oid"]
    if name == "vol":
        return panel["vol168"]
    if name == "reversal":
        return panel["ret168"]
    raise KeyError(name)


def u_rank(X, E):
    """rank chuan hoa trong tap eligible, 0(day)..1(cuoi); nan neu khong eligible."""
    n, NS = X.shape
    U = np.full((n, NS), np.nan, dtype=np.float32)
    for t in range(n):
        m = E[t] & np.isfinite(X[t])
        k = int(m.sum())
        if k == 0:
            continue
        v = X[t][m]
        o = np.argsort(np.argsort(v, kind="stable"), kind="stable").astype(np.float32)
        U[t][m] = (o + 0.5) / k
    return U


def build_book(X, E, band=2, dec=0.10):
    """Tra ve W (n,NS) trong so signed (long +, short -), tong gross = 1.0."""
    U = u_rank(X, E)
    n, NS = X.shape
    W = np.zeros((n, NS), dtype=np.float64)
    lo_prev = np.zeros(NS, dtype=bool)
    hi_prev = np.zeros(NS, dtype=bool)
    lo_b = dec
    hi_b = dec * band
    has_prev = False
    npos = np.zeros(n, dtype=np.int32)
    for t in range(n):
        m = E[t] & np.isfinite(U[t])
        k = int(m.sum())
        if k < MIN_ELIG:
            lo_prev = np.zeros(NS, dtype=bool)
            hi_prev = np.zeros(NS, dtype=bool)
            has_prev = False
            continue
        nd = max(1, int(round(dec * k)))
        u = U[t]
        ent_lo = m & (u < lo_b)
        ent_hi = m & (u > 1.0 - lo_b)
        stay_lo = m & (u < hi_b)
        stay_hi = m & (u > 1.0 - hi_b)
        if has_prev:
            lo = (lo_prev & stay_lo) | ent_lo
            hi = (hi_prev & stay_hi) | ent_hi
        else:
            lo, hi = ent_lo, ent_hi
        no = 0.5 / nd
        cap = 2.0 * no
        for side, mk in ((1.0, lo), (-1.0, hi)):
            ii = np.flatnonzero(mk)
            if len(ii) == 0:
                continue
            w = np.full(len(ii), 0.5 / len(ii))
            w = np.minimum(w, cap)
            w = w * (0.5 / w.sum())
            W[t, ii] = side * w
        npos[t] = len(np.flatnonzero(lo)) + len(np.flatnonzero(hi))
        lo_prev, hi_prev, has_prev = lo, hi, True
    return W, npos


def book_pnl(W, panel, fee_rt=FEE_RT, use_stop=True, fund_ts="trail"):
    """Tra (gross, fund, fee, net, to) theo ngay + legs net."""
    D, fwd, lo24, hi24, fsum = panel["D"], panel["fwd"], panel["lo24"], panel["hi24"], panel["fsum"]
    n, NS = W.shape
    # fsum hold: dung trailing fsum[t] lam ky vong (CAUSAL); ban realized = fsum[t+1]
    F = fsum
    Fh = np.full_like(fsum, np.nan)
    if fund_ts == "realized":
        Fh[:-1] = fsum[1:]
        F = Fh
    gross = np.zeros(n); fund = np.zeros(n); fee = np.zeros(n)
    legs = []
    leg_i = []
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
            stopped_long = dwn < -STOP
            stopped_short = up > STOP
            sl = np.where(np.isfinite(s), s, 0.0)
            sl = np.where(stopped_long & (w > 0), -STOP - STOP_SLIP, sl)
            sl = np.where(stopped_short & (w < 0), STOP + STOP_SLIP, sl)
            s = np.where(np.isfinite(s), sl, s)
            # neu fwd NaN nhung bi stop -> dat gia tri stop
            s = np.where(~np.isfinite(s) & stopped_long & (w > 0), -STOP - STOP_SLIP, s)
            s = np.where(~np.isfinite(s) & stopped_short & (w < 0), STOP + STOP_SLIP, s)
        s = np.where(np.isfinite(s), s, 0.0)
        # PnL: long w>0 -> + w*s ; short w<0 -> w*s (s la ret gia, short duoc -ret)
        pnl = w * s
        gross[t] = pnl.sum()
        f = np.where(np.isfinite(F[t]), F[t], 0.0)
        fund[t] = float((-(w) * f).sum())
        dw = np.abs(W[t] - Wprev)
        feeamt = FEE_HALF * dw
        fee[t] = float(feeamt.sum())
        for i in np.flatnonzero(w != 0):
            legs.append(pnl[i] + (-w[i] * f[i]))
            leg_i.append(i)
        for i in np.flatnonzero(dw > 0):
            legs.append(-feeamt[i])
            leg_i.append(i)
        Wprev = w
    net = gross + fund - fee
    return gross, fund, fee, net, np.asarray(legs), np.asarray(leg_i, dtype=np.int64)


def turnover(W):
    n = W.shape[0]
    to = np.zeros(n)
    prev = np.zeros(W.shape[1])
    for t in range(n):
        to[t] = 0.5 * np.abs(W[t] - prev).sum()
        prev = W[t]
    return to


def stats_series(net, to, W, panel, name):
    d = dict(name=name, n_days=int(len(net)))
    d["gross_per_day"] = float(np.nanmean(GROSS)) if False else None
    return d


def summarise(tag, net, gross, fund, fee, to, legs, panel, leg_i=None):
    n = len(net)
    mu = float(net.mean()); sd = float(net.std(ddof=1)) if n > 1 else float("nan")
    cum = np.cumsum(net)
    peak = np.maximum.accumulate(cum)
    mdd = float((cum - peak).min())
    r = rao(legs)
    pvn = float("nan")
    if leg_i is not None and len(leg_i) == len(legs):
        sig = np.nanstd(panel["fwd"], axis=0)
        ss = sig[leg_i]
        ok = np.isfinite(ss) & (ss > 0)
        if ok.any():
            pvn = float((legs[ok] / ss[ok]).mean())
    r["pnl_vol_norm"] = pvn
    ci_raw = block_boot_mean(net, inflate_k=1.0)
    ci_inf = block_boot_mean(net, inflate_k=inflate(CI_INFLATE_K))
    _, nstd, _ = block_signflip(net)
    p_gt0 = ci_raw["p_gt0"]
    mde80, mde28 = mde_p80(net)
    out = dict(tag=tag, n_days=n,
               gross_per_day=float(gross.mean()), fund_per_day=float(fund.mean()),
               fee_per_day=float(fee.mean()), net_per_day=mu,
               turnover_per_day=float(to.mean()), turnover_per_month=float(to.mean() * 30),
               sharpe=float(mu / sd * math.sqrt(365)) if sd and sd > 0 else float("nan"),
               maxdd=mdd, net_sd=sd, null_sd=nstd, p_gt0=p_gt0,
               ci_raw=ci_raw, ci_infl=ci_inf, mde_p80=mde80, mde_28sd=mde28,
               outside_raw=bool(mu - ci_raw["raw_half"] > 0),
               outside_infl=bool(mu - ci_inf["half"] > 0),
               rao=r, winrate_day=float((net > 0).mean()))
    pc = panel["D"]
    return out


def main():
    t0 = time.time()
    z = np.load(OUT + "/panel.npz")
    panel = {k: z[k] for k in z.files}
    meta = json.load(open(OUT + "/meta.json"))
    D = panel["D"]
    say("panel loaded %s (%.0fs)" % (str(D.shape), time.time() - t0))
    E, uni = build_eligible(panel, panel)
    n_elig = E[T0D:T1D + 1].sum(1)
    say("UNIVERSE tinh: top-%d theo dv_med; n_elig/ngay: median=%d min=%d max=%d" %
        (TOPK_UNIV, int(np.median(n_elig)), int(n_elig.min()), int(n_elig.max())))
    say("universe gom major: BTC=%s ETH=%s | tong sym tinh=%d" % (
        int(1 in uni), int(2 in uni), len(uni)))

    res = {"universe": dict(topk=TOPK_UNIV, n_static=len(uni), n_elig_median=float(np.median(n_elig)),
                            has_btc=bool(1 in uni), has_eth=bool(2 in uni)),
           "estimate_sub": {}, "books": {}, "ic": {}, "rand": {}, "fee_sens": {},
           "hyst_sens": {}, "stop_variant": {}, "nofundx": {}, "s1": {}}

    # ---------------- tung tin hieu ----------------
    books = {}
    say("\n===== 1. TUNG TIN HIEU (band=2, fee=0.76%%) =====")
    say("%-10s %8s %8s %8s %7s %7s %7s %6s %6s %6s" %
        ("signal", "gross/d", "fund/d", "fee/d", "net/d", "TO/d", "TO/mo", "Sharpe", "mdd", "winr"))
    for nm in SIGNALS:
        X = factor_matrix(panel, nm, D)
        U = u_rank(X, E)
        # IC
        ics = []
        for t in range(T0D, T1D + 1):
            m = E[t] & np.isfinite(X[t]) & np.isfinite(panel["fwd"][t])
            if m.sum() < 20:
                continue
            u = U[t][m]; f = panel["fwd"][t][m]
            ru = np.argsort(np.argsort(u)); rf = np.argsort(np.argsort(f))
            ics.append(np.corrcoef(ru, rf)[0, 1])
        res["ic"][nm] = float(np.mean(ics))
        W, npos = build_book(X, E, band=2)
        to = turnover(W)
        gross, fund, fee, net, legs, leg_i = book_pnl(W, panel)
        sl = slice(T0D, T1D + 1)
        o = summarise(nm, net[sl], gross[sl], fund[sl], fee[sl], to[sl], legs, panel, leg_i)
        o["npos_med"] = float(np.median(npos[sl]))
        books[nm] = (net, gross, fund, fee, to, W)
        res["books"][nm] = o
        say("%-10s %+8.4f %+8.4f %8.4f %+8.4f %7.3f %7.2f %7.3f %+6.2f %6.3f" %
            (nm, o["gross_per_day"] * 100, o["fund_per_day"] * 100, o["fee_per_day"] * 100,
             o["net_per_day"] * 100, o["turnover_per_day"], o["turnover_per_month"],
             o["sharpe"], o["maxdd"] * 100, o["winrate_day"]))
    say("IC trung binh (rank vs fwd24): " + " ".join("%s=%.4f" % (k, v) for k, v in res["ic"].items()))

    # ---------------- book ghep ----------------
    say("\n===== 2. BOOK GHEP =====")
    def agg(names):
        n = T1D + 1 - T0D
        g = np.zeros(n); f = np.zeros(n); fe = np.zeros(n); le = []
        li = []
        for nm in names:
            net, gross, fund, fee, to, W = books[nm]
            g += gross[T0D:T1D + 1] / len(names)
            f += fund[T0D:T1D + 1] / len(names)
            fe += fee[T0D:T1D + 1] / len(names)
        return g, f, fe, g + f - fe
    for tag, names in [("BOOK_EW", SIGNALS)]:
        g, f, fe, net = agg(names)
        # legs: gop leg cua tung book con /4
        L = []
        LI = []
        for nm in names:
            _, _, _, _, _, W = books[nm]
            _, _, _, _, lg, lgi = book_pnl(W, panel)
            L.append(lg / len(names))
            LI.append(lgi)
        legs = np.concatenate(L)
        leg_i = np.concatenate(LI)
        to = sum(books[nm][4][T0D:T1D + 1] for nm in names) / len(names)
        o = summarise(tag, net, g, f, fe, to, legs, panel, leg_i)
        res["books"][tag] = o
        say("%-10s gross/d=%+.4f%% fund/d=%+.4f%% fee/d=%.4f%% net/d=%+.4f%% TO/d=%.3f "
            "Sharpe=%.3f mdd=%+.2f%% winr=%.3f" %
            (tag, g.mean() * 100, f.mean() * 100, fe.mean() * 100, net.mean() * 100,
             to.mean(), o["sharpe"], o["maxdd"] * 100, o["winrate_day"]))
        say("   Rao: (a) share_top1=%.2f%% [%s]%s | (b') TF25=%+.4f [%s] | q*=%s | asym=%.3f" %
            (o["rao"]["share_top1_pct"], "PASS" if o["rao"]["a_pass"] else "FAIL",
             "" if o["rao"].get("a_defined", True) else " (N/A: tong<0)",
             o["rao"]["tf25"], "PASS" if o["rao"]["b_pass"] else "FAIL", o["rao"]["q_star"],
             o["rao"]["asym"]))
        say("   CI raw95=[%+.4f%%,%+.4f%%] | inflate(8)=[%+.4f%%,%+.4f%%] | p(>0)=%.3f | "
            "MDE80=%+.4f%% | null_sd=%.4f%%" %
            (o["ci_raw"]["ci_lo"] * 100, o["ci_raw"]["ci_hi"] * 100,
             o["ci_infl"]["ci_lo"] * 100, o["ci_infl"]["ci_hi"] * 100, o["p_gt0"],
             o["mde_p80"] * 100, o["null_sd"] * 100))
        # BOOK_RANK (phu)
        Ur = np.nanmean(np.stack([u_rank(factor_matrix(panel, nm, D), E) for nm in SIGNALS]), axis=0)
        Wr, _ = build_book(Ur, E, band=2)
        tor = turnover(Wr)
        gr, fr, fer, ner, lr, lri = book_pnl(Wr, panel)
        orr = summarise("BOOK_RANK", ner[T0D:T1D + 1], gr[T0D:T1D + 1], fr[T0D:T1D + 1],
                        fer[T0D:T1D + 1], tor[T0D:T1D + 1], lr, panel, lri)
        res["books"]["BOOK_RANK"] = orr
        say("   [phu] BOOK_RANK net/d=%+.4f%% TO/d=%.3f Sharpe=%.3f (a)%s (b')%s" %
            (orr["net_per_day"] * 100, orr["turnover_per_day"], orr["sharpe"],
             "PASS" if orr["rao"]["a_pass"] else "FAIL", "PASS" if orr["rao"]["b_pass"] else "FAIL"))

    net_book = agg(SIGNALS)[3]
    npos_book = np.zeros(len(net_book))
    for nm in SIGNALS:
        _, _, _, _, _, W = books[nm]
        npos_book += (W[T0D:T1D + 1] != 0).sum(1) / len(SIGNALS)
    res["npos_med"] = float(np.median(npos_book))

    # ---------------- doi chung ngau nhien ----------------
    say("\n===== 3. DOI CHUNG COIN NGAU NHIEN (n=%d) =====" % NREP if False else "\n===== 3. DOI CHUNG COIN NGAU NHIEN =====")
    NR = 200
    nlong = int(round(res["npos_med"] / 2))
    rng = np.random.default_rng(RSEED)
    rand_net = []
    rand_gross = []; rand_to = []
    for _ in range(NR):
        W = np.zeros_like(panel["D"], dtype=np.float64)
        for t in range(T0D, T1D + 1):
            m = np.flatnonzero(E[t])
            if len(m) < 2 * nlong:
                continue
            pick = rng.choice(m, size=2 * nlong, replace=False)
            W[t, pick[:nlong]] = 0.5 / nlong
            W[t, pick[nlong:]] = -0.5 / nlong
        g, f, fe, net, lg, lgi = book_pnl(W, panel)
        rand_net.append(float(net[T0D:T1D + 1].mean()))
        rand_gross.append(float(g[T0D:T1D + 1].mean()))
        rand_to.append(float(turnover(W)[T0D:T1D + 1].mean()))
    rand_net = np.array(rand_net); rand_gross = np.array(rand_gross); rand_to = np.array(rand_to)
    bm = float(net_book.mean())
    res["rand"] = dict(n=NR, mean=float(rand_net.mean()), p5=float(np.percentile(rand_net, 5)),
                       p95=float(np.percentile(rand_net, 95)),
                       max=float(rand_net.max()), book=bm, diff=bm - float(rand_net.mean()),
                       beats_p95=bool(bm > np.percentile(rand_net, 95)),
                       gross_mean=float(rand_gross.mean()), to_mean=float(rand_to.mean()),
                       book_gross=float((sum(books[nm][1][T0D:T1D + 1] for nm in SIGNALS) /
                                         len(SIGNALS)).mean()),
                       book_to=float((sum(books[nm][4][T0D:T1D + 1] for nm in SIGNALS) /
                                      len(SIGNALS)).mean()))
    say("control net/d: mean=%+.4f%% p5=%+.4f%% p95=%+.4f%% max=%+.4f%% | BOOK_EW=%+.4f%% "
        "| chenh=%+.4f%% | >p95? %s" %
        (rand_net.mean() * 100, res["rand"]["p5"] * 100, res["rand"]["p95"] * 100,
         res["rand"]["max"] * 100, bm * 100, res["rand"]["diff"] * 100, res["rand"]["beats_p95"]))
    say("control GROSS/d=%+.4f%% (TO/d=%.3f) vs BOOK_EW gross/d=%+.4f%% (TO/d=%.3f) -- "
        "chenh gross=%+.4f%%" %
        (res["rand"]["gross_mean"] * 100, res["rand"]["to_mean"], res["rand"]["book_gross"] * 100,
         res["rand"]["book_to"], (res["rand"]["book_gross"] - res["rand"]["gross_mean"]) * 100))

    # ---------------- do nhay phi ----------------
    say("\n===== 4. DO NHAY PHI =====")
    for fr in [0.0030, 0.0050, 0.0076, 0.0100]:
        g, f, fe, net = agg(SIGNALS)
        # tinh lai voi phi khac: fee = fee_rt * TO
        toavg = sum(books[nm][4][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
        gavg = sum(books[nm][1][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
        favg = sum(books[nm][2][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
        nv = gavg + favg - fr * toavg
        res["fee_sens"]["%.4f" % fr] = float(nv.mean())
        say("  fee_rt=%.2f%% -> net/d=%+.4f%% (gross/fund=-fee: %+.4f%% %+.4f%% -%.4f%%)" %
            (fr * 100, nv.mean() * 100, gavg.mean() * 100, favg.mean() * 100,
             (fr * toavg).mean() * 100))
    gavg = sum(books[nm][1][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
    favg = sum(books[nm][2][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
    toavg = sum(books[nm][4][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
    be = float((gavg + favg).mean() / toavg.mean()) if toavg.mean() > 0 else float("nan")
    res["breakeven_fee_rt"] = be
    say("  PHI HOA VON (fee_rt lam net/d=0) = %.3f%% /vong (turnover/d=%.3f)" % (be * 100, toavg.mean()))

    # ---------------- do nhay hysteresis ----------------
    say("\n===== 5. DO NHAY HYSTERESIS =====")
    for band in [1, 2, 3]:
        nets = []; tos = []
        for nm in SIGNALS:
            X = factor_matrix(panel, nm, D)
            W, _ = build_book(X, E, band=band)
            to = turnover(W)
            g, f, fe, net, lg, lgi = book_pnl(W, panel)
            nets.append(net[T0D:T1D + 1]); tos.append(to[T0D:T1D + 1])
        nv = np.mean(nets, axis=0); tv = np.mean(tos, axis=0)
        cnt = float(np.mean([build_book(factor_matrix(panel, nm, D), E, band=band)[1][T0D:T1D + 1]
                             for nm in SIGNALS]))
        res["hyst_sens"][band] = dict(net=float(nv.mean()), to=float(tv.mean()),
                                      net_sd=float(nv.std(ddof=1)), nhold_days=float(cnt))
        say("  band=%d: net/d=%+.4f%% TO/d=%.3f TO/mo=%.2f Sharpe=%.3f (nhold tb=%.0f ngay)" %
            (band, nv.mean() * 100, tv.mean(), tv.mean() * 30,
             nv.mean() / nv.std(ddof=1) * math.sqrt(365), cnt))

    # ---------------- bien the stop / funding cuc doan ----------------
    say("\n===== 6. BIEN THE (stop tat; fsum realized; loai funding cuc doan) =====")
    base_g = sum(books[nm][1][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
    base_f = sum(books[nm][2][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
    base_fe = sum(books[nm][3][T0D:T1D + 1] for nm in SIGNALS) / len(SIGNALS)
    say("  [chinh] net/d=%+.4f%%" % ((base_g + base_f - base_fe).mean() * 100))
    # (i) tat stop
    nets = []
    for nm in SIGNALS:
        X = factor_matrix(panel, nm, D)
        W, _ = build_book(X, E, band=2)
        g, f, fe, net, lg, _ = book_pnl(W, panel, use_stop=False)
        nets.append(net[T0D:T1D + 1])
    res["stop_variant"]["no_stop_net"] = float(np.mean(nets).mean())
    say("  [tat stop -10%%] net/d=%+.4f%%" % (np.mean(nets).mean() * 100))
    # (ii) fsum realized (t+1)
    nets = []
    for nm in SIGNALS:
        X = factor_matrix(panel, nm, D)
        W, _ = build_book(X, E, band=2)
        g, f, fe, net, lg, _ = book_pnl(W, panel, fund_ts="realized")
        nets.append(net[T0D:T1D + 1])
    res["stop_variant"]["fund_realized_net"] = float(np.mean(nets).mean())
    say("  [fsum realized] net/d=%+.4f%%" % (np.mean(nets).mean() * 100))

    # ---------------- cau (1) S1 spread ----------------
    say("\n===== 7. (CAU 1) SPREAD S1 L/S — TINH LAI BANG CI BLOCK =====")
    s1 = s1_spread(t0)
    res["s1"] = s1
    for tag, v in s1.items():
        c = v["ci"]
        say("  [%s] pool n=%d tick=%d | lo8=%+.4f%% hi8=%+.4f%% spread=%+.4f%%/72h | t_iid=%.2f | "
            "block72h(khoi=%d): CI95=[%+.4f%%,%+.4f%%] t_block=%.2f p(>0)=%.3f | block10d: "
            "CI95=[%+.4f%%,%+.4f%%] t_block=%.2f" %
            (tag, v["n_obs"], v["n_ticks"], v["lo8"], v["hi8"], v["mean_spread_pct72"], v["t_iid"],
             v["n_blocks"], c["ci_lo"] * 100, c["ci_hi"] * 100, c["t_block"], c["p_gt0"],
             v["ci_block10d"]["ci_lo"] * 100, v["ci_block10d"]["ci_hi"] * 100,
             v["ci_block10d"]["t_block"]))
        say("      decile f72: " + " ".join("q%d=%+.3f%%" % (i, x) for i, x in enumerate(v["decile"])))
        say("      cua so: %s .. %s" % (v["tick_min"], v["tick_max"]))

    json.dump(res, open(OUT + "/results.json", "w"), indent=1, default=str)
    open(OUT + "/report.txt", "w").write("\n".join(REP) + "\n")
    say("\nDONE %.0fs" % (time.time() - t0))


def s1_spread(t0):
    """Tai lap RESEARCH_SHORT §2.3: long top-8 diem THAP vs short bot-8 diem CAO, f72."""
    import pandas as pd
    CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
    H0 = 1609459200000
    T1 = 1767225600000
    a = np.fromfile(CLOSES, dtype=np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")]))
    ts = a["ts"].astype(np.int64); sy = a["sym"].astype(np.int64); cc = a["c"].astype(np.float32)
    del a
    m = (ts >= H0) & (ts < T1) & (ts % 3600000 == 0)
    ts, sy, cc = ts[m], sy[m], cc[m]
    NH = int((T1 - H0) // 3600000)
    ids = np.unique(sy)
    cidx = {int(s): i for i, s in enumerate(ids)}
    CH = np.full((NH, len(ids)), np.nan, dtype=np.float32)
    CH[((ts - H0) // 3600000).astype(np.int64), np.array([cidx[int(x)] for x in sy])] = cc
    del ts, sy, cc
    df = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2x1.parquet")
    # Pool GOC cua RESEARCH_SHORT = giao voi cand_dev (n=774.148 obs / 4.595 tick)
    cd = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet", columns=["ts", "sym", "retEnd_72h"])
    out = {}
    for tag, sub in (("pool_canddev", df.merge(cd, on=["ts", "sym"], how="inner")),
                     ("pool_allparq", df)):
        sub = sub[sub.ts < T1].copy()
        sub["h"] = ((sub.ts - H0) // 3600000).astype(np.int64)
        sub = sub[sub.h + 72 < NH]
        col = np.array([cidx.get(int(s), -1) for s in sub.sym], dtype=np.int64)
        fwd = CH[sub.h.values + 72, col] / CH[sub.h.values, col] - 1.0
        sub["fwd"] = fwd
        sub = sub[np.isfinite(sub.fwd)]
        rows = []
        for t, g in sub.groupby("ts"):
            if len(g) < 16:
                continue
            sc = g.score.values.astype(np.float64); fw = g.fwd.values
            o = np.argsort(sc, kind="stable")
            q = np.empty(len(o), dtype=int); q[o] = np.arange(len(o)) * 10 // len(o)
            d = {"ts": int(t), "n": len(o), "lo8": float(fw[o[:8]].mean()),
                 "hi8": float(fw[o[-8:]].mean()), "all": float(fw.mean())}
            for qq in range(10):
                d["q%d" % qq] = float(fw[q == qq].mean())
            rows.append(d)
        R = pd.DataFrame(rows)
        sp = R.lo8 - R.hi8
        b = (R.ts.values - R.ts.min()) // (72 * 3600 * 1000)
        nb = int(b.max()) + 1
        s = np.bincount(b, weights=sp.values, minlength=nb)
        c = np.bincount(b, minlength=nb).astype(float)
        rng = np.random.default_rng(SEED)
        idx = rng.integers(0, nb, (NREP, nb))
        means = s[idx].sum(1) / c[idx].sum(1)
        lo, hi = np.percentile(means, [2.5, 97.5])
        obs = float(sp.mean()); half = float((hi - lo) / 2)
        o = dict(n_obs=int(len(sub)), n_ticks=int(len(R)), n_blocks=nb,
                 mean_spread_pct72=obs * 100,
                 t_iid=float(sp.mean() / sp.std(ddof=1) * math.sqrt(len(sp))),
                 winfrac=float((sp > 0).mean()), lo8=float(R.lo8.mean() * 100),
                 hi8=float(R.hi8.mean() * 100), all=float(R["all"].mean() * 100),
                 decile=[float(R["q%d" % qq].mean() * 100) for qq in range(10)],
                 ci=dict(obs=obs, ci_lo=obs - half, ci_hi=obs + half, half=half,
                         p_gt0=float((means > 0).mean()),
                         t_block=float(obs / (half / 1.96)) if half > 0 else float("nan")))
        # block 10 ngay (nhu chuoi daily)
        b2 = (R.ts.values - R.ts.min()) // (10 * 86400000)
        nb2 = int(b2.max()) + 1
        s2 = np.bincount(b2, weights=sp.values, minlength=nb2)
        c2 = np.bincount(b2, minlength=nb2).astype(float)
        idx2 = rng.integers(0, nb2, (NREP, nb2))
        m2 = s2[idx2].sum(1) / c2[idx2].sum(1)
        lo2, hi2 = np.percentile(m2, [2.5, 97.5])
        half2 = float((hi2 - lo2) / 2)
        o["ci_block10d"] = dict(n_blocks=nb2, ci_lo=obs - half2, ci_hi=obs + half2, half=half2,
                                p_gt0=float((m2 > 0).mean()),
                                t_block=float(obs / (half2 / 1.96)) if half2 > 0 else float("nan"))
        o["tick_min"] = str(datetime.utcfromtimestamp(int(R.ts.min()) / 1000))
        o["tick_max"] = str(datetime.utcfromtimestamp(int(R.ts.max()) / 1000))
        out[tag] = o
    return out


if __name__ == "__main__":
    main()
