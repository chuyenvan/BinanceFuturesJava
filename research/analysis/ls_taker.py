#!/usr/bin/env python3
"""LS_TAKER — do H1 (ls_global factor cross-section + regime) / H2 (ls_toptrader & phan ky
smart-vs-retail) / H3 (taker_buy overlay MOM15) — 3 cot CHUA TUNG dung cua oi_percoin_full.bin.

Pre-reg: docs/PREREG_LS_TAKER.md (commit 51cfe29, chot TRUOC khi do; KHONG sua thiet ke).
Harness: CI block-72h bootstrap 2000 rep seed 20260905 x1.21; null block sign-flip 72h; MDE p80
nua-do-rong; N_eff = N/(1+(n_bar-1)*ICC72h) — ham CHEP NGUYEN tu research/analysis/oi_study.py
(vong nay phai SO SANH DUOC voi RESULT_OI_STUDY).

CI PHAN QUYET = CI72h_x1.21 x sqrt(k_gia_thuyet) (chong multiplicity; lam GO KHO hon).
Thuan Python. Khong Java. Khong claude-run. Khong cham 2026.
"""
import json
import math
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "/tmp/ls_study"
POOLS = "/tmp/funding_factor/pools.npz"
SEED = 20260905
NREP = 2000
BLOCK_H = 72
CI_INFLATE = 1.21
MIN_SYM = 50
FEE_RT = 0.0010
FEE_SIM = 0.0080
UTC = timezone.utc
KFAM = {"H1": 6, "H2": 3, "H3": 3}
KTOT = 12
REP = []
T_RES = {}
CELLS = {}
ROWS = []


def say(s=""):
    REP.append(s); print(s, flush=True)


def row(s):
    ROWS.append(s); REP.append(s); print(s, flush=True)


# ------------------------- harness (chep nguyen tu oi_study.py) -------------------------
def _boot_from_sums(bsum, bcnt, inflate=1.0, nrep=NREP, seed=SEED, idx=None):
    nb = len(bsum)
    rng = np.random.default_rng(seed)
    if idx is None:
        idx = rng.integers(0, nb, (nrep, nb))
    means = bsum[idx].sum(axis=1) / bcnt[idx].sum(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = bsum.sum() / bcnt.sum()
    half = (hi - lo) / 2.0 * inflate
    return dict(obs=obs, half=half, ci_lo=obs - half, ci_hi=obs + half, p_gt0=float((means > 0).mean()))


def sums_of(net, blk):
    g = pd.DataFrame({"b": blk, "x": net}).groupby("b")["x"]
    c = g.count().values.astype(np.float64)
    o = np.argsort(np.asarray(g.sum().index.values))
    return g.sum().values[o], c[o]


def block_boot(net, blk, inflate=1.0, nrep=NREP, seed=SEED):
    s, c = sums_of(net, blk)
    return _boot_from_sums(s, c, inflate=inflate, nrep=nrep, seed=seed)


def block_perm(net, blk, nrep=NREP, seed=SEED):
    bcode, binv = np.unique(np.asarray(blk), return_inverse=True)
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(nrep, len(bcode)))
    bsum = np.bincount(binv, weights=np.asarray(net))
    null = (signs @ bsum) / len(net)
    return float(net.mean()), float(null.mean()), float(null.std()), float((null >= net.mean()).mean())


def icc(net, gid):
    df = pd.DataFrame({"g": gid, "x": net})
    grp = df.groupby("g")["x"]
    k = grp.count().values; mi = grp.mean().values; gm = net.mean()
    a = len(k); ni = len(net)
    if a < 2 or ni <= a:
        return float("nan")
    msb = (k * (mi - gm) ** 2).sum() / (a - 1)
    within = net - df["g"].map(grp.mean()).values
    msw = (within ** 2).sum() / (ni - a)
    k0 = (ni - (k ** 2).sum() / ni) / (a - 1)
    den = msb + (k0 - 1) * msw
    return (msb - msw) / den if den != 0 else float("nan")


def mde_half(net, blk, nrep_null=500, seed=SEED):
    s, c = sums_of(net, blk)
    rng = np.random.default_rng(seed)
    nb = len(s)
    hs = np.empty(nrep_null)
    for r in range(nrep_null):
        signs = rng.choice([-1.0, 1.0], size=nb)
        ss = signs * s
        ss = ss - ss.sum() / c.sum() * c
        idx = rng.integers(0, nb, (NREP, nb))
        m = ss[idx].sum(axis=1) / c[idx].sum(axis=1)
        lo, hi = np.percentile(m, [2.5, 97.5])
        hs[r] = (hi - lo) / 2.0 * CI_INFLATE
    return float(np.percentile(hs, 80)), float(np.median(hs))


def full(net, ts_min, label, k=1):
    net = np.asarray(net, dtype=np.float64); ts_min = np.asarray(ts_min, dtype=np.int64)
    blk = ts_min // (BLOCK_H * 60)
    n = len(net)
    rl = block_boot(net, blk, inflate=CI_INFLATE)
    t = net.mean() / (net.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    nb = len(np.unique(blk))
    ic72 = icc(net, blk)
    nbar = n / nb if nb else float("nan")
    neff = n / (1 + (nbar - 1) * ic72) if ic72 == ic72 else float("nan")
    _, nm, ns, pv = block_perm(net, blk)
    dt = pd.to_datetime(ts_min * 60, unit="s", utc=True)
    qm = pd.Series(net).groupby(dt.to_period("Q").astype(str).values).mean()
    ym = pd.Series(net).groupby(dt.year.values).mean()
    oosm = ts_min >= OOS0
    oos_q = pd.Series(net[oosm]).groupby(dt.to_period("Q").astype(str).values[oosm]).mean()
    ha = rl["half"] * math.sqrt(k)
    return dict(label=label, n=n, mean=float(net.mean()), med=float(np.median(net)),
                win=float((net > 0).mean()), t_iid=float(t),
                ci_lo=float(rl["ci_lo"]), ci_hi=float(rl["ci_hi"]), half=float(rl["half"]), k=k,
                half_adj=float(ha), ci_lo_adj=float(net.mean() - ha), ci_hi_adj=float(net.mean() + ha),
                p_gt0=float(rl["p_gt0"]), nb=nb, icc72=float(ic72), n_eff=float(neff),
                null_mean=nm, null_sd=ns, p_perm=pv,
                mean_is=float(net[~oosm].mean()), mean_oos=float(net[oosm].mean()),
                n_oos=int(oosm.sum()), n_is=int((~oosm).sum()),
                qpos_all=float((qm > 0).mean()), nq_all=int(len(qm)),
                qpos_oos=float((oos_q > 0).mean()) if len(oos_q) else float("nan"),
                nq_oos=int(len(oos_q)), ypos_all=float((ym > 0).mean()), nyr=int(len(ym)))


def line(d):
    return ("%s: N=%d mean=%+.4f%% med=%+.4f%% win=%.1f%% | CI72h_x1.21=[%+.4f%%,%+.4f%%] p(>0)=%.3f "
            "| CI_adj(xSqrt%d)=[%+.4f%%,%+.4f%%] pNull=%.4f | IS=%+.4f%% OOS=%+.4f%% (N_oos=%d) "
            "q+ALL=%.0f%% OOS=%.0f%% (%dq) y+ALL=%.0f%% | N_eff=%.1f ICC72=%.3f nblk=%d" % (
                d["label"], d["n"], 100 * d["mean"], 100 * d["med"], 100 * d["win"],
                100 * d["ci_lo"], 100 * d["ci_hi"], d["p_gt0"], d["k"],
                100 * d["ci_lo_adj"], 100 * d["ci_hi_adj"], d["p_perm"],
                100 * d["mean_is"], 100 * d["mean_oos"], d["n_oos"],
                100 * d["qpos_all"], 100 * d["qpos_oos"], d["nq_oos"], 100 * d["ypos_all"],
                d["n_eff"], d["icc72"], d["nb"]))


def contrast(a, ta, b, tb, label, k=1):
    """Tuong phan mean(a)-mean(b) + CI block-72h x1.21 (va ban x sqrt(k)) + OOS + %quy OOS duong."""
    rng = np.random.default_rng(SEED)
    sa, ca = sums_of(a, ta // (BLOCK_H * 60))
    sb, cb = sums_of(b, tb // (BLOCK_H * 60))
    ia = rng.integers(0, len(sa), (NREP, len(sa)))
    ib = rng.integers(0, len(sb), (NREP, len(sb)))
    dd = sa[ia].sum(axis=1) / ca[ia].sum(axis=1) - sb[ib].sum(axis=1) / cb[ib].sum(axis=1)
    obs = a.mean() - b.mean()
    half = (np.percentile(dd, 97.5) - np.percentile(dd, 2.5)) / 2 * CI_INFLATE
    ha = half * math.sqrt(k)
    ma = ta >= OOS0; mb = tb >= OOS0
    oos = (a[ma].mean() - b[mb].mean()) if (ma.sum() and mb.sum()) else float("nan")
    dta = pd.to_datetime(ta * 60, unit="s", utc=True)
    dtb = pd.to_datetime(tb * 60, unit="s", utc=True)
    qa = pd.Series(a).groupby(dta.to_period("Q").astype(str).values).mean()
    qb = pd.Series(b).groupby(dtb.to_period("Q").astype(str).values).mean()
    qj = qa.align(qb, join="inner")
    qd = (qj[0] - qj[1])
    oosq = qd[[str(x) >= "2025Q1" for x in qd.index]]
    d = dict(label=label, n=len(a), n_b=len(b), mean=float(obs), ci_lo=float(obs - half),
             ci_hi=float(obs + half), half=float(half), k=k, half_adj=float(ha),
             ci_lo_adj=float(obs - ha), ci_hi_adj=float(obs + ha), p_gt0=float((dd > 0).mean()),
             mean_a=float(a.mean()), mean_b=float(b.mean()), mean_oos=float(oos),
             qpos_oos=float((oosq > 0).mean()) if len(oosq) else float("nan"), nq_oos=int(len(oosq)),
             qpos_all=float((qd > 0).mean()), nq_all=int(len(qd)))
    row("  %s: %+.4f%% - %+.4f%% = %+.4f%% | CI72h_x1.21=[%+.4f%%,%+.4f%%] p(diff>0)=%.3f "
        "| CI_adj(xSqrt%d)=[%+.4f%%,%+.4f%%] | OOS=%+.4f%% q+OOS=%.0f%% (%dq)" % (
            label, 100 * a.mean(), 100 * b.mean(), 100 * obs, 100 * (obs - half), 100 * (obs + half),
            d["p_gt0"], k, 100 * (obs - ha), 100 * (obs + ha), 100 * oos,
            100 * d["qpos_oos"] if d["qpos_oos"] == d["qpos_oos"] else -1, d["nq_oos"]))
    return d


def mde_of(net, ts, tag, k):
    ts = np.asarray(ts, dtype=np.int64)
    blk = ts // (BLOCK_H * 60)
    p80, p50 = mde_half(net, blk)
    rl = block_boot(net, blk, inflate=CI_INFLATE)
    _, nm, ns, _ = block_perm(net, blk)
    d = dict(p80=p80, p50=p50, half=rl["half"], half_adj=rl["half"] * math.sqrt(k), null_sd=ns,
             n=len(net), k=k, p80_adj=p80 * math.sqrt(k), mde_x28=2.8 * ns, mde_x28_adj=2.8 * ns * math.sqrt(k))
    row("%-32s N=%8d | half x1.21=%+.4f%% | half_adj(xSqrt%d)=%+.4f%% | MDE(p80)=%+.4f%% "
        "| MDE_adj=%+.4f%% | 2,8xSD(null)=%+.4f%% | 2,8xSD_adj=%+.4f%%" % (
            tag, len(net), 100 * rl["half"], k, 100 * d["half_adj"], 100 * p80,
            100 * d["p80_adj"], 100 * 2.8 * ns, 100 * d["mde_x28_adj"]))
    return d


# ------------------------- main -------------------------
def main():
    t_all = time.time()
    global OOS0
    meta = json.load(open(OUT + "/meta.json"))
    NH, ncol, T0, T0_MIN, H0 = meta["NH"], meta["ncol"], meta["T0"], meta["T0_MIN"], meta["H0"]
    lsg = np.load(OUT + "/lsg.npy", mmap_mode="r")
    lst = np.load(OUT + "/lst.npy", mmap_mode="r")
    tak = np.load(OUT + "/tak.npy", mmap_mode="r")
    d24 = np.load(OUT + "/d24.npy", mmap_mode="r")
    oiz = np.load(OUT + "/oiz.npy", mmap_mode="r")
    c5 = np.load(OUT + "/c5.npy", mmap_mode="r")
    rg = np.load(OUT + "/rg.npy", mmap_mode="r")
    f5 = np.load(OUT + "/f5.npy", mmap_mode="r")

    W1_0 = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp()) // 60
    W0_0 = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) // 60
    END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) // 60
    OOS0 = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp()) // 60

    h_all = np.arange(H0, NH, dtype=np.int64)
    tm_all = T0_MIN + h_all * 60
    hw = h_all[(tm_all >= W1_0) & (tm_all < END)]
    hw0 = h_all[(tm_all >= W0_0) & (tm_all < END)]

    def net_of(i, j, u, fee=FEE_RT):
        raw = c5[j][u] / c5[i][u] - 1.0
        return (raw - fee - 0.5 * rg[i][u] / c5[i][u] - (f5[j][u] - f5[i][u])).astype(np.float64)

    def logsafe(x):
        x = np.asarray(x, dtype=np.float64)
        return np.where(x > 0, np.log(np.maximum(x, 1e-12)), np.nan)

    say("### 0. Cua so & luoi")
    say("panel gio: NH=%d moc tu %s (T0), step 1h | ncol=%d | H0(DEV)=%d" % (
        NH, datetime.fromtimestamp(T0, UTC).strftime("%Y-%m-%d"), ncol, H0))
    say("W1 (CHINH) 2023-01-01..2025-12-31 = %d moc | W0 (bien the) 2022-2025 = %d moc" % (len(hw), len(hw0)))
    say("IS = 2023-2024 | OOS = 2025 (phan quyet tren OOS) | MIN_SYM=%d | FEE_RT=%.4f FEE_SIM=%.4f" % (
        MIN_SYM, FEE_RT, FEE_SIM))
    say("k_H1=6 k_H2=3 k_H3=3 k_tong=12 | CI PHAN QUYET = CI72h_x1.21 x sqrt(k_gia_thuyet)")
    for nm, arr in (("lsg", lsg), ("lst", lst), ("tak", tak)):
        cov = [int((np.isfinite(arr[h]) & (np.asarray(c5[h]) > 0)).sum()) for h in hw[::200]]
        say("  coverage %-4s: universe trung binh tren mau luoi W1 = %.1f symbol/moc (min %d max %d, n=%d)" % (
            nm, np.mean(cov), min(cov), max(cov), len(cov)))
    say("")

    # ===================== DOI CHUNG (b) NEO MOM15 =====================
    z = np.load(POOLS)
    m_min = z["m_min"].astype(np.int64); m_sym = z["m_sym"].astype(np.int64)
    m_valid = z["m_valid"]; m_raw = z["m_raw"]; m_slip = z["m_slip"]; m_fund = z["m_fund"]
    j24 = 1
    base24 = m_raw[j24].astype(np.float64) - m_slip.astype(np.float64) - m_fund[j24].astype(np.float64)
    devm = (m_min >= W0_0) & (m_min < END)
    say("################ DOI CHUNG (b) NEO MOM15 ################")
    say("  n_DEV=%d base=%+.4f%% net@0,10%%=%+.4f%% (KY VONG +1,6690%%, n=7128, +-0,05pp)" % (
        devm.sum(), 100 * base24[devm].mean(), 100 * base24[devm].mean() - 0.10))
    an_net = 100 * base24[devm].mean() - 0.10
    anchor_ok = (int(devm.sum()) == 7128) and (abs(an_net - 1.6690) < 0.05)
    T_RES["anchor"] = dict(n=int(devm.sum()), net10=float(an_net), ok=bool(anchor_ok))
    say("  => NEO %s" % ("TAI LAP OK" if anchor_ok else "*** LECH — KHONG KET LUAN ***"))
    say("")

    def run_decile(ffun, hours, hold, want=(9, 0), fee=FEE_RT):
        acc = {g: [[], []] for g in list(want) + ["EW"]}
        nsec = 0
        for i in hours:
            j = i + hold
            if j >= NH:
                continue
            f = ffun(i)
            c = c5[i]
            u = np.isfinite(f) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
            if u.sum() < MIN_SYM:
                continue
            nsec += 1
            idx = np.flatnonzero(u)
            order = np.argsort(np.asarray(f[idx], dtype=np.float64), kind="stable")
            N = len(idx)
            dec_r = np.empty(N, dtype=np.int8)
            dec_r[order] = np.minimum(np.arange(N) * 10 // N, 9)
            net = net_of(i, j, u, fee)
            tsm = int(T0_MIN + i * 60)
            for g in want:
                m = dec_r == g
                acc[g][0].append(net[m]); acc[g][1].append(np.full(int(m.sum()), tsm, dtype=np.int64))
            acc["EW"][0].append(net); acc["EW"][1].append(np.full(N, tsm, dtype=np.int64))
        return {g: (np.concatenate(acc[g][0]), np.concatenate(acc[g][1])) for g in list(want) + ["EW"]}, nsec

    def cell(name, o, hold, k, hyp):
        """Dang ky 1 o do: Q9 (net tuyet doi) vs EW (tuong phan)."""
        for g in (9, 0, "EW"):
            dd = full(o[g][0], o[g][1], name + "|%s" % ("EW" if g == "EW" else "Q%d" % g), k=1)
            row(line(dd))
            if g in (9, "EW"):
                T_RES["cell_" + name + "_" + str(g)] = {kk: dd[kk] for kk in
                    ("n", "mean", "ci_lo", "ci_hi", "mean_oos", "n_oos", "qpos_oos", "qpos_all",
                     "p_gt0", "p_perm", "win", "n_eff", "icc72", "mean_is", "ypos_all")}
        c = contrast(o[9][0], o[9][1], o["EW"][0], o["EW"][1], name + " Q9-EW", k=k)
        CELLS[name] = dict(a=o[9][0], ta=o[9][1], b=o["EW"][0], tb=o["EW"][1], c=c, k=k, hyp=hyp)
        return c

    # ===================== H1 =====================
    say("################ H1 — log(ls_global) NHU FACTOR CROSS-SECTION ################")
    say("luoi 1h, decile rank tat dinh, Q9 = ls_global CAO nhat (dam dong long nhat). Phi CHINH 0,10%% + slip + funding.")
    h1_o = {}
    for hold, hn in ((24, "24h"), (4, "4h"), (1, "1h")):
        o, nsec = run_decile(lambda i: logsafe(lsg[i]), hw, hold)
        h1_o[hn] = (o, nsec)
        say("")
        say("---- H1 W1 %s — so moc dung = %d ----" % (hn, nsec))
        c = cell("H1 W1 %s" % hn, o, hold, KFAM["H1"], "H1")
        say("  Q9 net>0 ? %s | EW=%+.4f%% | Q0=%+.4f%%" % (
            "CO" if o[9][0].mean() > 0 else "KHONG", 100 * o["EW"][0].mean(), 100 * o[0][0].mean()))
    say("")
    say("---- H1 bien the dd24h = log(lsg(t)) - log(lsg(t-24h)), W1, 24h ----")
    def f_dd(i):
        if i < 24:
            return np.full(ncol, np.nan, np.float32)
        return logsafe(lsg[i]) - logsafe(lsg[i - 24])
    o, nsec = run_decile(f_dd, hw, 24)
    say("so moc dung = %d" % nsec)
    cell("H1var dd24h W1 24h", o, 24, KFAM["H1"], "H1")
    say("")
    say("---- H1 bien the W0 (2022-2025), log(lsg), 24h ----")
    o, nsec = run_decile(lambda i: logsafe(lsg[i]), hw0, 24)
    say("so moc dung = %d" % nsec)
    cell("H1var W0 24h", o, 24, KFAM["H1"], "H1")

    say("")
    say("---- H1-REGIME: tercile THEO THOI GIAN cua median cross-section log(lsg) -> EW 24h ----")
    med = np.full(NH, np.nan)
    for i in hw:
        c = np.asarray(c5[i]); v = logsafe(lsg[i])
        u = np.isfinite(v) & np.isfinite(c) & (c > 0)
        if u.sum() >= MIN_SYM:
            med[i] = np.median(v[u])
    mv = med[hw]; ok = np.isfinite(mv)
    ter = np.minimum((np.argsort(np.argsort(mv[ok], kind="stable")) * 3) // int(ok.sum()), 2)
    hw_ok = hw[ok]
    accR = {t3: [[], []] for t3 in range(3)}
    for t3 in range(3):
        for i in hw_ok[ter == t3]:
            j = i + 24
            if j >= NH:
                continue
            c = c5[i]
            u = np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
            if u.sum() < MIN_SYM:
                continue
            nt = net_of(i, j, u)
            accR[t3][0].append(nt); accR[t3][1].append(np.full(len(nt), int(T0_MIN + i * 60), dtype=np.int64))
    for t3 in range(3):
        dd = full(np.concatenate(accR[t3][0]), np.concatenate(accR[t3][1]), "H1REGIME ter%d EW24h" % t3, k=1)
        row(line(dd))
        T_RES["h1regime_t%d" % t3] = {kk: dd[kk] for kk in ("n", "mean", "ci_lo", "ci_hi", "mean_oos", "p_gt0")}
    cR = contrast(np.concatenate(accR[2][0]), np.concatenate(accR[2][1]),
                  np.concatenate(accR[0][0]), np.concatenate(accR[0][1]),
                  "H1REGIME EW24h ter2-ter0", k=KFAM["H1"])
    CELLS["H1REGIME EW24h ter2-ter0"] = dict(a=np.concatenate(accR[2][0]), ta=np.concatenate(accR[2][1]),
                                             b=np.concatenate(accR[0][0]), tb=np.concatenate(accR[0][1]),
                                             c=cR, k=KFAM["H1"], hyp="H1")

    # ===================== H2 =====================
    say("")
    say("################ H2 — log(lst) va PHAN KY div = log(lst) - log(lsg) ################")
    for nm, fex, holds in (("div", lambda i: logsafe(lst[i]) - logsafe(lsg[i]), (24, 4)),
                           ("lst", lambda i: logsafe(lst[i]), (24,))):
        for hold in holds:
            o, nsec = run_decile(fex, hw, hold)
            say("")
            say("---- H2 %s W1 %dh — so moc dung = %d ----" % (nm, hold, nsec))
            cell("H2 %s W1 %dh" % (nm, hold), o, hold, KFAM["H2"], "H2")
            say("  Q9 net>0 ? %s | EW=%+.4f%%" % ("CO" if o[9][0].mean() > 0 else "KHONG", 100 * o["EW"][0].mean()))

    # ===================== H3 =====================
    say("")
    say("################ H3 — taker_buy OVERLAY LEN MOM15 (M-LEVEL k=1) ################")
    sel_all = devm & (((m_valid >> j24) & 1) == 1) & np.isfinite(base24)
    mm = m_min[sel_all]; ss = m_sym[sel_all]
    net24all = base24[sel_all] - FEE_RT
    ev = np.load(OUT + "/events_5m.npz")
    takv = ev["tak"][sel_all]; lstv = ev["lst"][sel_all]; lsgv = ev["lsg"][sel_all]
    stp5 = ev["stp5"][sel_all]; offv = ev["off"][sel_all]
    say("  [H3] so event MOM15 DEV 2022-2025 = %d (ky vong 7128) | trong W1 = %d" % (len(mm), int(((mm >= W1_0) & (mm < END)).sum())))
    w1m = (mm >= W1_0) & (mm < END)
    say("  [H3] coverage tak(<=15ph) trong W1 = %.1f%% | lst = %.1f%% | lsg = %.1f%%" % (
        100 * np.isfinite(takv[w1m]).mean(), 100 * np.isfinite(lstv[w1m]).mean(), 100 * np.isfinite(lsgv[w1m]).mean()))
    T_RES["h3_n"] = dict(n_dev=int(len(mm)), n_w1=int(w1m.sum()), cov_tak=float(np.isfinite(takv[w1m]).mean()))
    hour_of = (mm // 60) * 60
    uniq_h = np.unique(hour_of)
    rkmap = np.full(len(mm), np.nan)
    for hh in uniq_h:
        hh = int(hh); hi = (hh - T0_MIN) // 60
        if hi < 0 or hi >= NH:
            continue
        r_ = np.asarray(tak[hi], dtype=np.float64); c = np.asarray(c5[hi])
        u = np.isfinite(r_) & np.isfinite(c) & (c > 0)
        if u.sum() < MIN_SYM:
            continue
        idxs = np.flatnonzero(u)
        rk = np.argsort(np.argsort(r_[idxs], kind="stable")) / (len(idxs) - 1.0)
        mp = np.full(ncol, np.nan); mp[idxs] = rk
        sh = hour_of == hh
        rkmap[sh] = mp[ss[sh]]
    say("  [H3] rank cross-section tak: %.1f%% | so moc gio = %d" % (100 * np.isfinite(rkmap[w1m]).mean(), len(uniq_h)))
    for fname, fv in (("tak(muc)", takv), ("tak(rank_cs)", rkmap)):
        okm = w1m & np.isfinite(fv)
        v = fv[okm]
        ter3 = np.minimum((np.argsort(np.argsort(v, kind="stable")) * 3) // len(v), 2)
        say("")
        say("-- H3 tach theo %s (n=%d, W1) --" % (fname, int(okm.sum())))
        for t3 in range(3):
            m = ter3 == t3
            dd = full(net24all[okm][m], mm[okm][m], "H3 %s ter%d" % (fname, t3), k=1)
            row(line(dd))
            T_RES["h3_%s_ter%d" % (fname, t3)] = {kk: dd[kk] for kk in ("n", "mean", "ci_lo", "ci_hi", "mean_oos", "qpos_oos", "p_gt0")}
        a = net24all[okm][ter3 == 2]; ta = mm[okm][ter3 == 2]
        b = net24all[okm][ter3 == 0]; tb = mm[okm][ter3 == 0]
        c = contrast(a, ta, b, tb, "H3 %s ter2-ter0" % fname, k=KFAM["H3"])
        CELLS["H3 %s ter2-ter0" % fname] = dict(a=a, ta=ta, b=b, tb=tb, c=c, k=KFAM["H3"], hyp="H3")
        y = (net24all[okm] > 0).astype(np.float64)
        r = np.argsort(np.argsort(v, kind="stable")) + 1.0
        n1 = y.sum(); n0 = len(y) - n1
        auc = (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 > 0 and n0 > 0 else float("nan")
        row("   %s: AUC(tach thang/thua) = %.4f (win%%=%.1f n=%d) | ter net = %s" % (
            fname, auc, 100 * y.mean(), len(y), " / ".join("%+.4f%%" % (100 * net24all[okm][ter3 == t3].mean()) for t3 in range(3))))
        T_RES["h3_%s" % fname] = dict(auc=float(auc), n=int(len(y)), win=float(y.mean()),
                                      ter=[float(net24all[okm][ter3 == t3].mean()) for t3 in range(3)])
    say("")
    say("---- H3 bien the: tak MUC decile cross-section tren luoi 1h, 24h, W1 ----")
    o, nsec = run_decile(lambda i: np.asarray(tak[i], dtype=np.float64), hw, 24)
    say("so moc dung = %d" % nsec)
    cell("H3var takcs W1 24h", o, 24, KFAM["H3"], "H3")

    # ===================== MDE =====================
    say("")
    say("################ MDE (p80 nua-do-rong x1.21 tren 500 chuoi null sign-flip 72h) ################")
    mde = {}
    for tag in ("H1 W1 24h", "H2 div W1 24h", "H3 tak(muc) ter2-ter0", "H3var takcs W1 24h"):
        cl = CELLS.get(tag)
        if cl is None:
            continue
        mde[tag + " | A=Q9/ter2"] = mde_of(cl["a"], cl["ta"], tag + " [A]", cl["k"])
        mde[tag + " | B=EW/ter0"] = mde_of(cl["b"], cl["tb"], tag + " [B]", cl["k"])
    T_RES["mde"] = mde
    T_RES["cells"] = {k: {kk: v["c"][kk] for kk in
                          ("n", "mean", "ci_lo", "ci_hi", "ci_lo_adj", "ci_hi_adj", "half_adj", "p_gt0",
                           "mean_a", "mean_b", "mean_oos", "qpos_oos", "nq_oos", "qpos_all")}
                      for k, v in CELLS.items()}
    T_RES["k"] = dict(KFAM=KFAM, KTOT=KTOT)
    json.dump(T_RES, open(OUT + "/results_lstaker.json", "w"), indent=1)
    open(OUT + "/report_lstaker.txt", "w").write("\n".join(REP) + "\n")
    say("")
    say("elapsed %.0fs" % (time.time() - t_all))


if __name__ == "__main__":
    main()
