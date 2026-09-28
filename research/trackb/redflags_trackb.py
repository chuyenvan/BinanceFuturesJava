#!/usr/bin/env python3
"""D4 — GO 3 CO DO Track B (0 sim). Pre-reg: docs/prereg/PREREG_TRACKB_REDFLAGS.md.

VIEC 1: tai lap doi chung ngau nhien gross +0.064%/d + phan ra 3 nguon (a universe tinh, b stop -10%,
        c trong so L/S lech) bang thiet ke 2x2 (tinh/as-of) x (stop/no-stop).
VIEC 2: control CUNG band/hysteresis + khop turnover => chenh gross book-control + CI block(72h).
VIEC 3: hoi quy PnL ngay tren BTC + alt-EW => alpha + t (block).

Thuan Python offline, 0 train/0 sim, DEV <=2025-12-31. Input /tmp/trackb/panel.npz.
Output /tmp/trackb/redflags.json (nho) -> chep vao docs/result/trackb_redflags.json.
"""
import json
import math
import sys
import time
import warnings
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/trackb")
import run_trackb as R  # dung lai: build_book, u_rank, book_pnl, turnover, block_boot_mean, inflate

warnings.filterwarnings("ignore")
OUT = "/tmp/trackb"
SEED_BOOT = 20260905
SEED_CTRL = 20260928
NREP = 2000
K_INF = 8
BLOCK_MAIN = 3          # 72h (chinh cho D4)
BLOCK_ALT = 10          # 10 ngay (phu, tuong thich step1)
FEE_REAL = 0.00112      # chi phi co huong C(2000) median
FEE_BE = 0.00414        # hoa von
SIGNS = R.SIGNALS
T0D, T1D = R.T0D, R.T1D
H0 = 1609459200000
REP = []


def say(s=""):
    REP.append(s)
    print(s, flush=True)


# ---------------------------------------------------------------- universe AS-OF
def build_eligible_asof(panel):
    D, DVS, DVD = panel["D"], panel["DVS"], panel["DVS_DATE"]
    NS = D.shape[1]
    fin = np.isfinite(D)
    ym_list = (DVD[:, 0].astype(np.int64) * 100 + DVD[:, 1]).tolist()
    cache = {}
    E = np.zeros_like(D, dtype=bool)
    for t in range(T1D + 1):
        dt = datetime.fromtimestamp((H0 + t * 86400000) / 1000.0, timezone.utc)
        ym_t = dt.year * 100 + dt.month
        u = cache.get(ym_t)
        if u is None:
            cols = np.array([m < ym_t for m in ym_list])
            if cols.sum() < 12:
                u = np.zeros(NS, dtype=bool)
            else:
                sub = DVS[:, cols]
                cnt = np.isfinite(sub).sum(1)
                med = np.nanmedian(np.where(np.isfinite(sub), sub, np.nan), axis=1)
                ok = np.isfinite(med) & (cnt >= 12)
                order = np.argsort(np.where(ok, med, -1.0))[::-1]
                u = np.zeros(NS, dtype=bool)
                u[order[:R.TOPK_UNIV]] = True
            cache[ym_t] = u
        hist = fin[max(0, t - 30):t].sum(0) >= 30
        E[t] = u & hist & fin[t]
    E[:T0D] = False
    return E


# ---------------------------------------------------------------- control books
def rand_book_fresh(E, n_long, n_short, seed, long_gross=0.5, short_gross=0.5):
    """Doi chung ngau nhien kieu step1: chon moi ngay, dollar-neutral tuy chon lech."""
    rng = np.random.default_rng(seed)
    n, NS = E.shape
    W = np.zeros((n, NS))
    for t in range(n):
        if not E[t].any():
            continue
        m = np.flatnonzero(E[t])
        k = n_long + n_short
        if len(m) < k:
            continue
        pick = rng.choice(m, size=k, replace=False)
        W[t, pick[:n_long]] = long_gross / n_long
        if n_short:
            W[t, pick[n_long:]] = -short_gross / n_short
    return W


def rand_book_ar1(E, seed, rho=0.0, band=2):
    """Control CUNG band/hysteresis: factor ngau nhien AR(1) -> build_book."""
    rng = np.random.default_rng(seed)
    n, NS = E.shape
    X = np.empty((n, NS), dtype=np.float64)
    prev = rng.standard_normal(NS)
    X[0] = prev
    s = math.sqrt(max(0.0, 1.0 - rho * rho))
    for t in range(1, n):
        prev = rho * prev + s * rng.standard_normal(NS)
        X[t] = prev
    W, npos = R.build_book(X, E, band=band)
    return W, npos


def day_series(W, panel, use_stop=True):
    g, f, fe, net, legs, li = R.book_pnl(W, panel, use_stop=use_stop)
    to = R.turnover(W)
    sl = slice(T0D, T1D + 1)
    return dict(gross=g[sl], fund=f[sl], to=to[sl])


def ci(x, block, inflate=False):
    r = R.block_boot_mean(x, block=block, nrep=NREP, seed=SEED_BOOT,
                          inflate_k=R.inflate(K_INF) if inflate else 1.0)
    return r


def main():
    t0 = time.time()
    z = np.load(OUT + "/panel.npz")
    panel = {k: z[k] for k in z.files}
    meta = json.load(open(OUT + "/meta.json"))
    D = panel["D"]
    say("panel %s loaded %.0fs | DVS %s" % (str(D.shape), time.time() - t0, str(panel["DVS"].shape)))

    E_st = R.build_eligible(panel, panel)[0]
    E_as = build_eligible_asof(panel)
    n_st = E_st[T0D:T1D + 1].sum(1)
    n_as = E_as[T0D:T1D + 1].sum(1)
    say("n_elig/ngay TINH median=%d | AS-OF median=%d min=%d max=%d" %
        (int(np.median(n_st)), int(np.median(n_as)), int(n_as.min()), int(n_as.max())))

    res = dict(universe=dict(n_static_med=int(np.median(n_st)), n_asof_med=int(np.median(n_as)),
                             n_asof_min=int(n_as.min()), n_asof_max=int(n_as.max())))

    # ---- BOOK that (4 tin hieu, band=2) de lay npos_med + TO + series ----
    say("\n== BOOK_EW (tao lai de doi chieu) ==")
    books = {}
    for nm in SIGNS:
        X = R.factor_matrix(panel, nm, D)
        W, npos = R.build_book(X, E_st, band=2)
        books[nm] = (W, npos)
    npos_book = np.mean([(books[nm][0][T0D:T1D + 1] != 0).sum(1) for nm in SIGNS], axis=0)
    npos_med = float(np.median(npos_book))
    nlong_base = int(round(npos_med / 2))
    g_book = np.mean([day_series(books[nm][0], panel)["gross"] for nm in SIGNS], axis=0)
    f_book = np.mean([day_series(books[nm][0], panel)["fund"] for nm in SIGNS], axis=0)
    to_book = np.mean([day_series(books[nm][0], panel)["to"] for nm in SIGNS], axis=0)
    say("BOOK_EW gross/d=%+.4f%% fund/d=%+.4f%% TO/d=%.3f npos_med=%.1f nlong=%d" %
        (g_book.mean() * 100, f_book.mean() * 100, to_book.mean(), npos_med, nlong_base))
    res["book"] = dict(gross=float(g_book.mean()), fund=float(f_book.mean()), to=float(to_book.mean()),
                       npos_med=npos_med, nlong=nlong_base)

    # ================================================================ VIEC 1
    say("\n===== VIEC 1: GO CO DO #1 (bias harness) — 2x2 =====")
    NR = 200
    acc = {k: [] for k in ["A", "B", "C", "D", "c1", "c2"]}
    for s in range(NR):
        seed = SEED_CTRL + s
        Wst = rand_book_fresh(E_st, nlong_base, nlong_base, seed)
        Was = rand_book_fresh(E_as, nlong_base, nlong_base, seed)
        Wc1 = rand_book_fresh(E_st, 2 * nlong_base, nlong_base, seed)
        Wc2 = rand_book_fresh(E_st, nlong_base, nlong_base, seed, long_gross=0.55, short_gross=0.45)
        acc["A"].append(day_series(Wst, panel, True)["gross"].mean())
        acc["B"].append(day_series(Wst, panel, False)["gross"].mean())
        acc["C"].append(day_series(Was, panel, True)["gross"].mean())
        acc["D"].append(day_series(Was, panel, False)["gross"].mean())
        acc["c1"].append(day_series(Wc1, panel, True)["gross"].mean())
        acc["c2"].append(day_series(Wc2, panel, True)["gross"].mean())
    m = {k: float(np.mean(v)) for k, v in acc.items()}
    sd = {k: float(np.std(v, ddof=1)) for k, v in acc.items()}
    a1 = m["A"] - m["C"]      # universe tinh - as-of (co stop)
    a2 = m["B"] - m["D"]      # universe tinh - as-of (khong stop)
    b1 = m["A"] - m["B"]      # stop (tinh)
    b2 = m["C"] - m["D"]      # stop (as-of)
    c1e = m["c1"] - m["A"]
    c2e = m["c2"] - m["A"]
    a_eff = 0.5 * (a1 + a2)
    b_eff = 0.5 * (b1 + b2)
    explained = a_eff + b_eff + abs(c1e) + abs(c2e)
    say("A tinh+stop   gross/d=%+.4f%% (sd %.4f)" % (m["A"] * 100, sd["A"] * 100))
    say("B tinh,no-stop gross/d=%+.4f%%" % (m["B"] * 100))
    say("C asof+stop    gross/d=%+.4f%%" % (m["C"] * 100))
    say("D asof,no-stop gross/d=%+.4f%%" % (m["D"] * 100))
    say("(a) universe (A-C)=%+.4f%% (B-D)=%+.4f%% -> eff %+.4f%%" % (a1 * 100, a2 * 100, a_eff * 100))
    say("(b) stop     (A-B)=%+.4f%% (C-D)=%+.4f%% -> eff %+.4f%%" % (b1 * 100, b2 * 100, b_eff * 100))
    say("(c1) long/short COUNT lech: gross(c1)-A=%+.4f%%" % (c1e * 100))
    say("(c2) long/short GROSS lech: gross(c2)-A=%+.4f%%" % (c2e * 100))
    say("D as-of/no-stop (ky vong ~0) = %+.4f%% ; tong giai thich %+.4f%% / A %+.4f%%" %
        (m["D"] * 100, explained * 100, m["A"] * 100))
    flag1 = dict(A=m["A"], B=m["B"], C=m["C"], D=m["D"], sd_A=sd["A"], sdc=dict(c1=m["c1"], c2=m["c2"]),
                 a_eff=a_eff, b_eff=b_eff, c1_eff=c1e, c2_eff=c2e, explained=explained,
                 reproduced=bool(abs(m["A"] - 0.000642) <= 0.00010),
                 ctrl_after_fix=float(m["D"]),
                 ctrl_after_fix_ok=bool(abs(m["D"]) <= 0.00020),
                 explained_frac=float(explained / m["A"]) if m["A"] else float("nan"))
    flag1["cleared"] = bool(flag1["reproduced"] and flag1["explained_frac"] >= 0.75 and flag1["ctrl_after_fix_ok"])
    res["flag1"] = flag1

    # ================================================================ VIEC 2
    say("\n===== VIEC 2: GO CO DO #2 (turnover) =====")
    to_target = float(to_book.mean())
    # chon rho khop turnover
    say("TO(book)=%.3f ; quet rho (n=15)..." % to_target)
    rho_grid = [0.0, 0.2, 0.4, 0.6, 0.65, 0.70, 0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.85, 0.90, 0.95, 0.98]
    best = (None, 9e9)
    to_by_rho = {}
    for rho in rho_grid:
        tos = []
        for s in range(15):
            W, _ = rand_book_ar1(E_st, SEED_CTRL + s, rho=rho, band=2)
            tos.append(float(day_series(W, panel)["to"].mean()))
        tv = float(np.mean(tos))
        to_by_rho[rho] = tv
        say("  rho=%.2f -> TO/d=%.3f (rel err %.1f%%)" % (rho, tv, abs(tv - to_target) / to_target * 100))
        if abs(tv - to_target) < best[1]:
            best = (rho, abs(tv - to_target))
    rho_star = best[0]
    say("rho* = %.2f" % rho_star)
    gs, ts, fs, gs_ns = [], [], [], []
    for s in range(NR):
        W, _ = rand_book_ar1(E_st, SEED_CTRL + s, rho=rho_star, band=2)
        d = day_series(W, panel)
        gs.append(d["gross"]); ts.append(d["to"]); fs.append(d["fund"])
        gs_ns.append(day_series(W, panel, use_stop=False)["gross"])
    g_ctrl = np.mean(gs, axis=0); to_ctrl = np.mean(ts, axis=0); f_ctrl = np.mean(fs, axis=0)
    g_ctrl_ns = np.mean(gs_ns, axis=0)
    g_book_ns = np.mean([day_series(books[nm][0], panel, use_stop=False)["gross"] for nm in SIGNS], axis=0)
    diff_ns = g_book_ns - g_ctrl_ns
    ci_ns = ci(diff_ns, BLOCK_MAIN)
    to_err = abs(to_ctrl.mean() - to_target) / to_target
    diff_g = g_book - g_ctrl
    ci_g = ci(diff_g, BLOCK_MAIN)
    ci_g10 = ci(diff_g, BLOCK_ALT)
    net_book_112 = g_book + f_book - FEE_REAL * to_book
    net_ctrl_112 = g_ctrl + f_ctrl - FEE_REAL * to_ctrl
    diff_n = net_book_112 - net_ctrl_112
    ci_n = ci(diff_n, BLOCK_MAIN)
    net_book_be = g_book + f_book - FEE_BE * to_book
    ci_bk112 = ci(net_book_112, BLOCK_MAIN)
    say("TO(book)=%.3f TO(control)=%.3f (rel err %.1f%%)" % (to_target, to_ctrl.mean(), to_err * 100))
    say("gross book=%+.4f%% control=%+.4f%% | chenh=%+.4f%% CI72h=[%+.4f%%,%+.4f%%] p(>0)=%.3f" %
        (g_book.mean() * 100, g_ctrl.mean() * 100, diff_g.mean() * 100,
         ci_g["ci_lo"] * 100, ci_g["ci_hi"] * 100, ci_g["p_gt0"]))
    say("  CI10d=[%+.4f%%,%+.4f%%] | net@0.112 book=%+.4f%% chenh net=%+.4f%% CI72h=[%+.4f%%,%+.4f%%]" %
        (ci_g10["ci_lo"] * 100, ci_g10["ci_hi"] * 100, net_book_112.mean() * 100,
         diff_n.mean() * 100, ci_n["ci_lo"] * 100, ci_n["ci_hi"] * 100))
    say("  net@0.414 book=%+.4f%% CI72h=[%+.4f%%,%+.4f%%]" %
        (net_book_be.mean() * 100, ci_bk112["ci_lo"] * 100, ci_bk112["ci_hi"] * 100))
    say("  [KHONG STOP] gross book=%+.4f%% control=%+.4f%% chenh=%+.4f%% CI72h=[%+.4f%%,%+.4f%%] p(>0)=%.3f" %
        (g_book_ns.mean() * 100, g_ctrl_ns.mean() * 100, diff_ns.mean() * 100,
         ci_ns["ci_lo"] * 100, ci_ns["ci_hi"] * 100, ci_ns["p_gt0"]))
    flag2 = dict(rho_star=rho_star, to_by_rho=to_by_rho, to_book=to_target, to_ctrl=float(to_ctrl.mean()),
                 to_rel_err=float(to_err), gross_book=float(g_book.mean()), gross_ctrl=float(g_ctrl.mean()),
                 diff_gross=float(diff_g.mean()), ci72_lo=ci_g["ci_lo"], ci72_hi=ci_g["ci_hi"],
                 ci72_p=ci_g["p_gt0"], ci10_lo=ci_g10["ci_lo"], ci10_hi=ci_g10["ci_hi"],
                 net_book_112=float(net_book_112.mean()), diff_net=float(diff_n.mean()),
                 ci_net_lo=ci_n["ci_lo"], ci_net_hi=ci_n["ci_hi"],
                 net_book_be=float(net_book_be.mean()),
                 gross_book_ns=float(g_book_ns.mean()), gross_ctrl_ns=float(g_ctrl_ns.mean()),
                 diff_gross_ns=float(diff_ns.mean()), ci_ns_lo=ci_ns["ci_lo"], ci_ns_hi=ci_ns["ci_hi"],
                 ci_ns_p=ci_ns["p_gt0"], stop_artifact=float(g_ctrl.mean() - g_ctrl_ns.mean()))
    flag2["cleared"] = bool(to_err <= 0.10 and ci_g["ci_lo"] > 0)
    res["flag2"] = flag2

    # ================================================================ VIEC 3
    say("\n===== VIEC 3: GO CO DO #3 (vol = beta?) =====")
    syms = meta["syms"]
    btc = syms.index(1)
    fwd = panel["fwd"]
    r_btc = fwd[T0D:T1D + 1, btc].astype(np.float64)
    alt = np.full(T1D + 1 - T0D, np.nan)
    for i, t in enumerate(range(T0D, T1D + 1)):
        mm = E_st[t] & np.isfinite(fwd[t])
        if mm.sum() >= 20:
            alt[i] = float(np.nanmean(fwd[t][mm]))
    r_alt = alt

    def reg_with_ci(y, block):
        ok = np.isfinite(y) & np.isfinite(r_btc) & np.isfinite(r_alt)
        Xm = np.column_stack([np.ones(ok.sum()), r_btc[ok], r_alt[ok]])
        yy = y[ok]
        b, *_ = np.linalg.lstsq(Xm, yy, rcond=None)
        fit = Xm @ b
        r2 = 1 - ((yy - fit) ** 2).sum() / ((yy - yy.mean()) ** 2).sum()
        b = b * np.array([1.0, 1.0, 1.0])
        nb = int(ok.sum() // block) + 1
        bidx = np.arange(ok.sum()) // block
        rng = np.random.default_rng(SEED_BOOT)
        A = np.full((NREP, 3), np.nan)
        Xo, yo = Xm, yy
        for r in range(NREP):
            take = rng.integers(0, nb, nb)
            sel = np.concatenate([np.flatnonzero(bidx == k) for k in take]) if False else None
            # resample blocks
            rows = np.concatenate([np.arange(k * block, min((k + 1) * block, len(yy))) for k in take])
            br, *_ = np.linalg.lstsq(Xo[rows], yo[rows], rcond=None)
            A[r] = br
        lo = np.percentile(A, 2.5, axis=0); hi = np.percentile(A, 97.5, axis=0)
        t_al = b[0] / ((hi[0] - lo[0]) / 2 / 1.96) if hi[0] > lo[0] else float("nan")
        return dict(alpha=float(b[0]), beta_btc=float(b[1]), beta_alt=float(b[2]), r2=float(r2),
                    ci_lo=[float(x) for x in lo], ci_hi=[float(x) for x in hi],
                    t_alpha_block=float(t_al), n=int(ok.sum()))

    regs = {}
    for nm in ["vol", "BOOK_EW"]:
        if nm == "vol":
            g = day_series(books["vol"][0], panel)["gross"]; f = day_series(books["vol"][0], panel)["fund"]
            tt = day_series(books["vol"][0], panel)["to"]
        else:
            g, f, tt = g_book, f_book, to_book
        net112 = g + f - FEE_REAL * tt
        regs[nm] = dict(gross=reg_with_ci(g.astype(np.float64), BLOCK_MAIN),
                        net=reg_with_ci(net112.astype(np.float64), BLOCK_MAIN),
                        net10=reg_with_ci(net112.astype(np.float64), BLOCK_ALT),
                        net_mean_pct=float(net112.mean() * 100))
        for why in ["gross", "net", "net10"]:
            z_ = regs[nm][why]
            say("  [%s %s] alpha=%+.4f%%/d t_blk=%.2f | b_btc=%+.3f b_alt=%+.3f R2=%.3f" %
                (nm, why, z_["alpha"] * 100, z_["t_alpha_block"], z_["beta_btc"], z_["beta_alt"], z_["r2"]))
    v = regs["vol"]["net"]
    flag3 = dict(alpha=float(v["alpha"]), t_alpha_block=float(v["t_alpha_block"]),
                 ci_lo=float(v["ci_lo"][0]), ci_hi=float(v["ci_hi"][0]),
                 beta_btc=float(v["beta_btc"]), beta_alt=float(v["beta_alt"]), r2=float(v["r2"]))
    flag3["cleared"] = bool(v["alpha"] > 0 and v["ci_lo"][0] > 0)
    res["flag3"] = flag3
    res["regs"] = regs

    res["flags_cleared"] = dict(f1=flag1["cleared"], f2=flag2["cleared"], f3=flag3["cleared"])
    go2 = bool(flag1["cleared"] and flag2["cleared"] and flag3["cleared"])
    res["GO_STEP2"] = go2
    say("\n== KET LUAN: #1=%s #2=%s #3=%s => GO buoc 2? %s ==" %
        (flag1["cleared"], flag2["cleared"], flag3["cleared"], go2))

    json.dump(res, open(OUT + "/redflags.json", "w"), indent=1, default=str)
    open(OUT + "/redflags_report.txt", "w").write("\n".join(REP) + "\n")
    say("DONE %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
