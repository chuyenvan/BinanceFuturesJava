#!/usr/bin/env python3
"""CROWDED_LONG — do luat RUI RO/SIZE "crowded-long => giam size" bang QUANTILE TRUOT.

Thuc thi DUNG docs/PREREG_CROWDED_LONG.md (commit 0acf68c, chot TRUOC khi do; KHONG sua thiet ke).

Cau hoi: KHONG phai alpha. La RUI RO/SIZE: giam size khi crowded-long co lam GIAM DUOI
(intraday maxDD / worst-window drop cua sach) > CHI PHI (loi nhuan bo lo) khong?

  §1  x_t = median(log ls_global) cross-section; thr truot p80 tren [t-N*24, t-1]; N in {30,90}; CAUSAL.
  §2  Loi nhuan ON vs OFF: EW + neo MOM15, H in {1h,4h,24h}; phi harness; CI block-72h x1.21 + CI_adj(x sqrt2).
  §3  Duoi intraday: TAI DUNG chuoi equity MTM moc phut da nghiem thu (/home/ubuntu/intradaydd/series.npz)
      -> drop24(t) = min_{m in (t,t+24h]} E(m)/E(t) - 1; dd24 = maxDD trong cua so; ON vs OFF.
  §4  Kiem cheo BAT BUOC: (a) bien dong cao (SD cross-section), (b) downtrend BTC.
  §5  Tac dong SO LENH: % gio ON, % event MOM15 trong ON.
  §6  Kinh te luat: s=0,5 khi ON -> mean/CVaR5/p01/maxDD so baseline.

Thuan Python offline. KHONG Java/sim. KHONG claude-run. KHONG push. DEV only (khong doc 2026).
"""
import json
import math
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PAN = "/tmp/crowded"
OUT = "/tmp/crowded"
SERIES = "/home/ubuntu/intradaydd/series.npz"
POOLS = "/tmp/funding_factor/pools.npz"
SEED = 20260905
NREP = 2000
BLOCK_H = 72
CI_INFLATE = 1.21
MIN_SYM = 50
FEE_RT = 0.0010
NDAYS = (30, 90)
KFAM = 2
UTC = timezone.utc
M0 = int(pd.Timestamp("2021-07-01").timestamp()) // 60
REP = []
T_RES = {}


def say(s=""):
    REP.append(s)
    print(s, flush=True)


# ---------------------------- harness (CHEP NGUYEN tu ls_taker.py / oi_study.py) ------------
def _boot_from_sums(bsum, bcnt, inflate=1.0, nrep=NREP, seed=SEED, idx=None):
    rng = np.random.default_rng(seed)
    if idx is None:
        idx = rng.integers(0, len(bsum), (nrep, len(bsum)))
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


def tails(net):
    net = np.asarray(net, dtype=np.float64)
    if len(net) == 0:
        return dict(n=0, mean=float("nan"), med=float("nan"), win=float("nan"),
                    p05=float("nan"), p01=float("nan"), cvar5=float("nan"), cvar1=float("nan"))
    k5 = max(1, int(round(0.05 * len(net)))); k1 = max(1, int(round(0.01 * len(net))))
    so = np.sort(net)
    return dict(n=len(net), mean=float(net.mean()), med=float(np.median(net)),
                win=float((net > 0).mean()), p05=float(np.percentile(net, 5)),
                p01=float(np.percentile(net, 1)), cvar5=float(so[:k5].mean()),
                cvar1=float(so[:k1].mean()))


def path_maxdd(net, ts):
    """maxDD cua chuoi luu ke (1+r).cumprod() — LUU Y: chong lan khi H>1h."""
    net = np.asarray(net, dtype=np.float64)
    o = np.argsort(np.asarray(ts))
    c = np.cumprod(1.0 + net[o])
    return float((c / np.maximum.accumulate(c) - 1.0).min())


def contrast(a, ta, b, tb, label, k=1):
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
    dta = pd.to_datetime(ta * 60, unit="s", utc=True); dtb = pd.to_datetime(tb * 60, unit="s", utc=True)
    qa = pd.Series(a).groupby(dta.to_period("Q").astype(str).values).mean()
    qb = pd.Series(b).groupby(dtb.to_period("Q").astype(str).values).mean()
    qj = qa.align(qb, join="inner"); qd = (qj[0] - qj[1])
    oosq = qd[[str(x) >= "2025Q1" for x in qd.index]]
    return dict(label=label, n=len(a), n_b=len(b), mean=float(obs), a_mean=float(a.mean()),
                b_mean=float(b.mean()), ci_lo=float(obs - half), ci_hi=float(obs + half),
                half=float(half), half_adj=float(ha), k=k, ci_lo_adj=float(obs - ha),
                ci_hi_adj=float(obs + ha), p_gt0=float((dd > 0).mean()), mean_oos=float(oos),
                mean_is=float(a[~ma].mean() - b[~mb].mean()) if (not ma.all() and not mb.all()) else float("nan"),
                qpos_oos=float((oosq > 0).mean()) if len(oosq) else float("nan"), nq_oos=int(len(oosq)),
                qpos_all=float((qd > 0).mean()), nq_all=int(len(qd)))


def row_contrast(d):
    say("  %s: %+.4f%% - %+.4f%% = %+.4f%% | CI72h_x1.21=[%+.4f%%,%+.4f%%] p(diff>0)=%.3f "
        "| CI_adj(xSqrt%d)=[%+.4f%%,%+.4f%%] | IS=%+.4f%% OOS=%+.4f%% q+OOS=%s (%dq)" % (
            d["label"], 100 * d["a_mean"], 100 * d["b_mean"], 100 * d["mean"],
            100 * d["ci_lo"], 100 * d["ci_hi"], d["p_gt0"], d["k"],
            100 * d["ci_lo_adj"], 100 * d["ci_hi_adj"], 100 * d["mean_is"], 100 * d["mean_oos"],
            ("%.0f%%" % (100 * d["qpos_oos"])) if d["qpos_oos"] == d["qpos_oos"] else "-", d["nq_oos"]))
    return d


def row_tail(tag, t):
    if t["n"] == 0:
        say("  %-26s n=0" % tag); return t
    say("  %-26s n=%7d mean=%+.4f%% med=%+.4f%% win=%4.1f%% p05=%+.4f%% p01=%+.4f%% "
        "CVaR5=%+.4f%% CVaR1=%+.4f%%" % (tag, t["n"], 100 * t["mean"], 100 * t["med"],
                                         100 * t["win"], 100 * t["p05"], 100 * t["p01"],
                                         100 * t["cvar5"], 100 * t["cvar1"]))
    return t


def mde_of(net, ts, tag, k):
    ts = np.asarray(ts, dtype=np.int64)
    blk = ts // (BLOCK_H * 60)
    p80, p50 = mde_half(net, blk)
    rl = block_boot(net, blk, inflate=CI_INFLATE)
    d = dict(p80=p80, p50=p50, half=rl["half"], half_adj=rl["half"] * math.sqrt(k), n=len(net), k=k,
             p80_adj=p80 * math.sqrt(k))
    say("  %-32s N=%8d | half x1.21=%+.4f%% | half_adj(xSqrt%d)=%+.4f%% | MDE(p80)=%+.4f%% | MDE_adj=%+.4f%%" % (
        tag, len(net), 100 * rl["half"], k, 100 * d["half_adj"], 100 * p80, 100 * d["p80_adj"]))
    return d


# ================================ MAIN ================================
def main():
    t_all = time.time()
    global OOS0
    meta = json.load(open(PAN + "/meta.json"))
    NH, ncol, T0_MIN, H0 = meta["NH"], meta["ncol"], meta["T0_MIN"], meta["H0"]
    btc = meta["btc_col"]
    lsg = np.load(PAN + "/lsg.npy", mmap_mode="r")
    c5 = np.load(PAN + "/c5.npy", mmap_mode="r")
    rg = np.load(PAN + "/rg.npy", mmap_mode="r")
    f5 = np.load(PAN + "/f5.npy", mmap_mode="r")

    W1_0 = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp()) // 60
    W0_0 = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) // 60
    END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) // 60
    OOS0 = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp()) // 60

    say("### 0. Cua so & du lieu")
    say("panel gio NH=%d tu %s | ncol=%d | H0=%d | BTC col=%d" % (
        NH, datetime.fromtimestamp(meta["T0"], UTC).strftime("%Y-%m-%d"), ncol, H0, btc))
    say("W1 (CHINH) 2023-01-01..2025-12-31 23:00 | IS=2023-2024 | OOS=2025 | MIN_SYM=%d FEE_RT=%.4f" % (MIN_SYM, FEE_RT))
    say("k=2 (N=30 vs N=90) | CI PHAN QUYET = CI72h_x1.21 x sqrt(2) | p=0,80 co dinh | seed %d" % SEED)

    # ---------- §1 x_t ----------
    say("")
    say("### 1. TIN HIEU x_t = median(log ls_global) cross-section (CAUSAL)")
    allh = np.arange(H0, NH, dtype=np.int64)
    x = np.full(NH, np.nan)
    n_u = np.zeros(NH, dtype=np.int32)
    for i in allh:
        v = np.asarray(lsg[i], dtype=np.float64); c = np.asarray(c5[i], dtype=np.float64)
        u = np.isfinite(v) & (v > 0) & np.isfinite(c) & (c > 0)
        n_u[i] = int(u.sum())
        if n_u[i] >= MIN_SYM:
            x[i] = np.median(np.log(np.maximum(v[u], 1e-12)))
    yr_all = pd.to_datetime((T0_MIN + allh * 60) * 60, unit="s", utc=True).year.values
    say("x_t: %d moc gio co gia tri | universe TB %.1f sym/moc (min %d max %d)" % (
        int(np.isfinite(x).sum()), n_u[allh].mean(), n_u[allh].min(), n_u[allh].max()))
    for y in (2022, 2023, 2024, 2025):
        m = yr_all == y
        say("  coverage x_t %d: %.1f%% (thieu %d/%d moc)" % (y, 100 * np.isfinite(x[allh][m]).mean(),
                                                             int(np.isnan(x[allh][m]).sum()), int(m.sum())))
    T_RES["x"] = dict(n_valid=int(np.isfinite(x).sum()), n_all=int(len(allh)), u_mean=float(n_u[allh].mean()))

    s_x = pd.Series(x)
    ON = {}
    for N in NDAYS:
        win = N * 24
        q = s_x.rolling(win, min_periods=1).quantile(0.80).shift(1).values
        cnt = s_x.rolling(win, min_periods=1).count().shift(1).values
        ok = (cnt >= 0.9 * win) & np.isfinite(q) & np.isfinite(x)
        ON[N] = np.where(ok, x > q, np.nan)

    hw = allh[(T0_MIN + allh * 60 >= W1_0) & (T0_MIN + allh * 60 < END)]
    say("")
    say("thr_t(N) = p80 cua x tren [t-N*24, t-1] (KHONG gom t; can >=90%% moc hop le)")
    say("---- TRANG THAI ON trong W1 (%d moc gio) ----" % len(hw))
    say("%-9s %8s %8s %8s %9s %11s %10s %9s" % ("N(ngay)", "n_undef", "%ON", "n_doan", "n_chuyen",
                                                 "med_doan(h)", "mean_doan", "max_doan"))
    onstat = {}
    for N in NDAYS:
        o = ON[N][hw]
        un = int(np.isnan(o).sum())
        b = (o == 1).astype(np.int8)
        d = np.diff(np.concatenate([[0], b, [0]]))
        st = np.flatnonzero(d == 1); en = np.flatnonzero(d == -1)
        runs = en - st
        onstat[N] = dict(n=len(hw), undef=un, pon=float(np.nanmean(o)), nruns=int(len(runs)),
                         ntrans=int((d == 1).sum()),
                         med_run=float(np.median(runs)) if len(runs) else float("nan"),
                         mean_run=float(runs.mean()) if len(runs) else float("nan"),
                         max_run=int(runs.max()) if len(runs) else 0)
        dd = onstat[N]
        say("%-9d %8d %7.1f%% %8d %9d %11.1f %10.1f %9d" % (N, dd["undef"], 100 * dd["pon"],
            dd["nruns"], dd["ntrans"], dd["med_run"], dd["mean_run"], dd["max_run"]))
    T_RES["onstat"] = onstat
    say("")
    say("---- % gio ON theo nam (chi nam trong W1) ----")
    ys = {}
    in_w1_all = (T0_MIN + allh * 60 >= W1_0) & (T0_MIN + allh * 60 < END)
    for N in NDAYS:
        o = ON[N][allh]
        row = []
        for y in (2023, 2024, 2025):
            m = in_w1_all & (yr_all == y)
            row.append("%d:%.1f%%" % (y, 100 * np.nanmean(o[m])))
        say("  N=%dd  %s" % (N, "  ".join(row)))
        ys[N] = row
    T_RES["on_by_year"] = ys

    # ---------- EW ----------
    say("")
    say("### 2. LOI NHUAN: EW (universe) & NEO MOM15 khi ON vs OFF")
    say("net(t,H) = mean_u[c5(t+H)/c5(t)-1] - 0,0010 - 0,5*rg(t)/c5(t) - [f5(t+H)-f5(t)]")
    EW = {}
    for H in (1, 4, 24):
        n_ = np.full(NH, np.nan); ts_ = np.zeros(NH, dtype=np.int64)
        for i in hw:
            j = i + H
            if j >= NH:
                continue
            ci = np.asarray(c5[i], dtype=np.float64); cj = np.asarray(c5[j], dtype=np.float64)
            lv = np.asarray(lsg[i], dtype=np.float64)
            u = np.isfinite(ci) & (ci > 0) & np.isfinite(cj) & np.isfinite(lv) & (lv > 0)
            if u.sum() < MIN_SYM:
                continue
            nt = (cj[u] / ci[u] - 1.0 - FEE_RT - 0.5 * np.asarray(rg[i], dtype=np.float64)[u] / ci[u]
                  - (np.asarray(f5[j], dtype=np.float64)[u] - np.asarray(f5[i], dtype=np.float64)[u]))
            n_[i] = nt.mean(); ts_[i] = T0_MIN + i * 60
        m = np.isfinite(n_)
        EW[H] = (n_[m], ts_[m])
        say("  H=%2dh: so moc dung = %d | EW net TB toan W1 = %+.4f%%" % (H, int(m.sum()), 100 * n_[m].mean()))
    T_RES["ew_h"] = {str(H): dict(n=int(len(EW[H][0])), mean=float(EW[H][0].mean())) for H in EW}

    # ---------- anchor ----------
    z = np.load(POOLS)
    m_min = z["m_min"].astype(np.int64)
    m_valid = z["m_valid"]; m_raw = z["m_raw"]; m_slip = z["m_slip"]; m_fund = z["m_fund"]
    devm = (m_min >= W0_0) & (m_min < END)
    J4, J24 = 0, 1
    base24 = m_raw[J24].astype(np.float64) - m_slip.astype(np.float64) - m_fund[J24].astype(np.float64)
    base4 = m_raw[J4].astype(np.float64) - m_slip.astype(np.float64) - m_fund[J4].astype(np.float64)
    devm &= (((m_valid >> J24) & 1) == 1) & np.isfinite(base24)
    an = 100 * base24[devm].mean() - 0.10
    say("")
    say("### NEO MOM15 (bat buoc): n_DEV=%d base=%+.4f%% net@0,10%%=%+.4f%% (KY VONG +1,6690%%, n=7128)" % (
        int(devm.sum()), 100 * base24[devm].mean(), an))
    anchor_ok = (int(devm.sum()) == 7128) and (abs(an - 1.6690) < 0.05)
    T_RES["anchor"] = dict(n=int(devm.sum()), net10=float(an), ok=bool(anchor_ok))
    say("  => NEO %s" % ("TAI LAP OK" if anchor_ok else "*** LECH — KHONG KET LUAN ***"))
    if not anchor_ok:
        json.dump(T_RES, open(OUT + "/results_crowded.json", "w"), indent=1)
        open(OUT + "/report_crowded.txt", "w").write("\n".join(REP) + "\n")
        return

    # ---------- (A) EW ON/OFF ----------
    say("")
    say("################ (A) LOI NHUAN EW: ON vs OFF ################")
    ew_cells = {}
    for N in NDAYS:
        onarr = ON[N]
        for H in (1, 4, 24):
            n_, ts_ = EW[H]
            idx = ((ts_ - T0_MIN) // 60).astype(np.int64)
            m1 = onarr[idx] == 1; m0 = onarr[idx] == 0
            a = n_[m1]; ta = ts_[m1]; b = n_[m0]; tb = ts_[m0]
            say("")
            say("-- N=%dd H=%dh: n_ON=%d n_OFF=%d (bo qua %d moc trang thai khong xac dinh) --" % (
                N, H, len(a), len(b), int(np.isnan(onarr[idx]).sum())))
            t1 = row_tail("ON   net%dh" % H, tails(a)); t0 = row_tail("OFF  net%dh" % H, tails(b))
            c = row_contrast(contrast(a, ta, b, tb, "N%dd H%dh ON-OFF" % (N, H), k=KFAM))
            cell = dict(tail_on=t1, tail_off=t0, contrast=c)
            if H == 24:
                cell["mde_on"] = mde_of(a, ta, "N%d H24 ON" % N, KFAM)
                cell["mde_off"] = mde_of(b, tb, "N%d H24 OFF" % N, KFAM)
            ew_cells["N%dd_H%dh" % (N, H)] = cell
    T_RES["ew_cells"] = ew_cells

    # ---------- (B) MOM15 ----------
    say("")
    say("################ (B) NEO MOM15: ON vs OFF ################")
    hm = (m_min // 60) * 60
    hi = ((hm - T0_MIN) // 60).astype(np.int64)
    okh = (hi >= 0) & (hi < NH)
    inw1 = (m_min >= W1_0) & (m_min < END)
    mom_cells = {}
    for N in NDAYS:
        onv = np.full(len(m_min), np.nan)
        onv[okh] = ON[N][hi[okh]]
        for J, H, bs in ((J4, 4, base4), (J24, 24, base24)):
            net = bs - FEE_RT
            v = devm & np.isfinite(onv)
            sel = v & inw1
            a = net[sel & (onv == 1)]; ta = m_min[sel & (onv == 1)]
            b = net[sel & (onv == 0)]; tb = m_min[sel & (onv == 0)]
            say("")
            say("-- MOM15 N=%dd H=%dh: n_ON=%d n_OFF=%d (event ngoai W1 = %d) --" % (
                N, H, len(a), len(b), int((v & ~inw1).sum())))
            t1 = row_tail("ON   mom%dh" % H, tails(a)); t0 = row_tail("OFF  mom%dh" % H, tails(b))
            c = row_contrast(contrast(a, ta, b, tb, "MOM15 N%dd H%dh ON-OFF" % (N, H), k=KFAM))
            cell = dict(tail_on=t1, tail_off=t0, contrast=c)
            if H == 24:
                cell["mde_on"] = mde_of(a, ta, "MOM15 N%d H24 ON" % N, KFAM)
                cell["mde_off"] = mde_of(b, tb, "MOM15 N%d H24 OFF" % N, KFAM)
            mom_cells["N%dd_H%dh" % (N, H)] = cell
    T_RES["mom_cells"] = mom_cells

    # ---------- (C) tercile theo thoi gian (doi chung dinh nghia) ----------
    say("")
    say("################ (C) DOI CHUNG DINH NGHIA: tercile THEO THOI GIAN (khong tinh vao k) ################")
    xw = x[hw]; okw = np.isfinite(xw)
    ter = np.minimum((np.argsort(np.argsort(xw[okw], kind="stable")) * 3) // int(okw.sum()), 2)
    ter_at = np.full(NH, -1, dtype=np.int8); ter_at[hw[okw]] = ter
    n24, ts24 = EW[24]
    idx24 = ((ts24 - T0_MIN) // 60).astype(np.int64)
    for t3 in range(3):
        a = n24[ter_at[idx24] == t3]
        tt = row_tail("tercile-TH %d EW24h" % t3, tails(a))
        T_RES["tercit_t%d" % t3] = tt
        say("    (so moc gio trong tercile = %d, so moc EW co trang thai = %d)" % (
            int((ter == t3).sum()), int((ter_at[idx24] == t3).sum())))
    row_contrast(contrast(n24[ter_at[idx24] == 2], ts24[ter_at[idx24] == 2],
                          n24[ter_at[idx24] == 0], ts24[ter_at[idx24] == 0],
                          "tercileTH ter2-ter0 (k=1)", k=1))

    # ---------- (D) duoi intraday ----------
    say("")
    say("################ (D) DUOI INTRADAY TREN SACH THAT ################")
    zz = np.load(SERIES)
    L = len(zz["c_KEEPLEG0"])
    say("truc phut %s .. %s (L=%d) | nguon series.npz (V1-V5 PASS o RESULT_INTRADAY_DD)" % (
        pd.to_datetime(M0 * 60, unit="s", utc=True).strftime("%Y-%m-%d %H:%M"),
        pd.to_datetime((M0 + L - 1) * 60, unit="s", utc=True).strftime("%Y-%m-%d %H:%M"), L))
    RUNS = ("KEEPLEG0", "T170", "T100", "GD92")
    hwL = hw[((T0_MIN + hw * 60) - M0 + 24 * 60) <= L - 1]
    say("gio dung = %d (bo %d gio cuoi W1 vi thieu 24h forward trong cache)" % (len(hwL), len(hw) - len(hwL)))
    hiL = ((T0_MIN + hwL * 60) - M0).astype(np.int64)
    tsm = (T0_MIN + hwL * 60)
    store = {}
    for run in RUNS:
        for mk in ("c", "l"):
            E = zz["%s_%s" % (mk, run)]
            rmin = pd.Series(E[::-1]).rolling(24 * 60, min_periods=1).min().values
            fmin = rmin[::-1][1:]                      # fmin[t] = min(E[t+1 .. t+1440])
            drop = fmin[hiL] / E[hiL] - 1.0
            r24 = E[hiL + 24 * 60] / E[hiL] - 1.0
            dd = np.empty(len(hiL))
            for q, t in enumerate(hiL):
                w = E[t + 1:t + 24 * 60 + 1]
                cm = np.maximum.accumulate(np.concatenate([[E[t]], w]))
                dd[q] = (w / cm[1:] - 1.0).min()
            store[(run, mk)] = dict(drop=drop, r24=r24, dd=dd)
    say("drop24(t) = min_{m in (t,t+24h]} E(m)/E(t) - 1 (mark=close; ban the 'l'=bar.low)")
    tail_res = {}
    for N in NDAYS:
        onarr = ON[N]
        for run in RUNS:
            for mk in (("c", "l") if run == "KEEPLEG0" else ("c",)):
                S = store[(run, mk)]
                st = onarr[hwL]
                a = S["drop"][st == 1]; b = S["drop"][st == 0]
                base_rate = float(np.nanmean(st))
                say("")
                say("-- %s/%s N=%dd (tan suat ON nen = %.1f%%) --" % (run, mk, N, 100 * base_rate))
                t1 = row_tail("ON  drop24", tails(a)); t0 = row_tail("OFF drop24", tails(b))
                c = row_contrast(contrast(a, tsm[st == 1], b, tsm[st == 0],
                                          "drop24 %s/%s N%d ON-OFF" % (run, mk, N),
                                          k=KFAM if (run == "KEEPLEG0" and mk == "c") else 1))
                o10 = np.argsort(S["drop"])[:10]
                o50 = np.argsort(S["drop"])[:50]
                lift10 = float((st[o10] == 1).mean()) / base_rate if base_rate > 0 else float("nan")
                lift50 = float((st[o50] == 1).mean()) / base_rate if base_rate > 0 else float("nan")
                neg = S["drop"] < 0
                contrib = float(S["drop"][(st == 1) & neg].sum() / S["drop"][neg].sum()) if neg.any() else float("nan")
                say("    lift ON trong 10 cua so te nhat = %.2fx (50 te nhat = %.2fx) | ty trong tong drop AM cua cua so ON = %.1f%%"
                    % (lift10, lift50, 100 * contrib))
                say("    maxDD trong cua so (TB): ON=%+.3f%% OFF=%+.3f%% | r24 TB: ON=%+.3f%% OFF=%+.3f%%" % (
                    100 * S["dd"][st == 1].mean(), 100 * S["dd"][st == 0].mean(),
                    100 * S["r24"][st == 1].mean(), 100 * S["r24"][st == 0].mean()))
                # duoi cua dd24 (cummax)
                say("    dd24 (cummax, khong co CI): p05 ON=%+.3f%% OFF=%+.3f%% | p01 ON=%+.3f%% OFF=%+.3f%%" % (
                    100 * np.percentile(S["dd"][st == 1], 5), 100 * np.percentile(S["dd"][st == 0], 5),
                    100 * np.percentile(S["dd"][st == 1], 1), 100 * np.percentile(S["dd"][st == 0], 1)))
                tail_res["%s_%s_N%d" % (run, mk, N)] = dict(
                    base_rate=base_rate, on=t1, off=t0, contrast=c, lift10=lift10, lift50=lift50,
                    contrib=contrib, dd_on=float(S["dd"][st == 1].mean()),
                    dd_off=float(S["dd"][st == 0].mean()),
                    dd_p05_on=float(np.percentile(S["dd"][st == 1], 5)),
                    dd_p05_off=float(np.percentile(S["dd"][st == 0], 5)),
                    dd_p01_on=float(np.percentile(S["dd"][st == 1], 1)),
                    dd_p01_off=float(np.percentile(S["dd"][st == 0], 1)),
                    r24_on=float(S["r24"][st == 1].mean()), r24_off=float(S["r24"][st == 0].mean()))
    T_RES["tail"] = tail_res

    # ---------- (E) kiem cheo ----------
    say("")
    say("################ (E) KIEM CHEO BAT BUOC ################")
    lr = np.full(NH, np.nan)
    for i in allh:
        if i < 1:
            continue
        c0 = np.asarray(c5[i - 1], dtype=np.float64); c1 = np.asarray(c5[i], dtype=np.float64)
        u = np.isfinite(c0) & (c0 > 0) & np.isfinite(c1) & (c1 > 0)
        if u.sum() >= MIN_SYM:
            r = np.log(c1[u] / c0[u]); lr[i] = r.std(ddof=1)
    btcc = np.asarray(c5[:, btc], dtype=np.float64)
    ma = pd.Series(btcc).rolling(30 * 24, min_periods=30 * 24).mean().values
    btcma = btcc / ma - 1.0
    btc24 = np.full(NH, np.nan); btc24[24:] = btcc[24:] / btcc[:-24] - 1.0
    lw = lr[hw]; okv = np.isfinite(lw)
    vol_ter = np.full(NH, -1, dtype=np.int8)
    vol_ter[hw[okv]] = np.minimum((np.argsort(np.argsort(lw[okv], kind="stable")) * 3) // int(okv.sum()), 2)
    say("(a) vol_t = SD cross-section log-return 1h; Spearman(x_t, vol_t) tren W1 = %.3f" % (
        pd.Series(x[hw]).corr(pd.Series(lr[hw]), method="spearman")))
    say("(b) BTC: btc24_t = return 24h cua BTCUSDT; btcma_t = close/MA30 - 1")
    cr = {}
    for N in NDAYS:
        o = ON[N]
        ov = o[hw]; ovok = np.isfinite(ov)
        p_vol = float((vol_ter[hw][ov == 1] == 2).mean()); q_vol = float((vol_ter[hw][ovok] == 2).mean())
        p_dn = float((btc24[hw][ov == 1] < 0).mean()); q_dn = float((btc24[hw][ovok] < 0).mean())
        p_ma = float((btcma[hw][ov == 1] < 0).mean()); q_ma = float((btcma[hw][ovok] < 0).mean())
        j_vol = p_vol * ovok.sum() / max(1e-9, ((ov == 1).sum() + q_vol * ovok.sum() - p_vol * ovok.sum()))
        say("")
        say("  N=%dd: P(vol-ter2|ON)=%.1f%% vs P(vol-ter2)=%.1f%% (tang %.2fx, Jaccard~%.2f)" % (
            N, 100 * p_vol, 100 * q_vol, p_vol / max(1e-9, q_vol), j_vol))
        say("         P(BTC24h<0|ON)=%.1f%% vs P=%.1f%% (tang %.2fx) | P(BTC<MA30|ON)=%.1f%% vs P=%.1f%% (tang %.2fx)" % (
            100 * p_dn, 100 * q_dn, p_dn / max(1e-9, q_dn), 100 * p_ma, 100 * q_ma, p_ma / max(1e-9, q_ma)))
        cr["N%d_ovl" % N] = dict(p_vol=p_vol, q_vol=q_vol, p_dn=p_dn, q_dn=q_dn, p_ma=p_ma, q_ma=q_ma)
        for tag, mskb in (("vol-ter0", vol_ter[idx24] == 0), ("vol-ter1", vol_ter[idx24] == 1),
                          ("vol-ter2", vol_ter[idx24] == 2),
                          ("BTC24hUP", btc24[idx24] > 0), ("BTC24hDN", btc24[idx24] < 0),
                          ("BTCgtMA30", btcma[idx24] > 0), ("BTCltMA30", btcma[idx24] < 0)):
            m1 = mskb & (o[idx24] == 1); m0 = mskb & (o[idx24] == 0)
            if m1.sum() < 200 or m0.sum() < 200:
                say("    %-11s n_ON=%5d n_OFF=%5d (qua it, bo)" % (tag, int(m1.sum()), int(m0.sum()))); continue
            c = contrast(n24[m1], ts24[m1], n24[m0], ts24[m0], "N%d|%s" % (N, tag), k=1)
            say("    %-11s n_ON=%5d n_OFF=%5d | ON-OFF=%+.4f%% CI72h_x1.21=[%+.4f%%,%+.4f%%] p(diff>0)=%.3f"
                % (tag, int(m1.sum()), int(m0.sum()), 100 * c["mean"], 100 * c["ci_lo"], 100 * c["ci_hi"], c["p_gt0"]))
            cr["N%d|%s" % (N, tag)] = c
    T_RES["cross"] = cr

    # ---------- (F) so lenh ----------
    say("")
    say("################ (F) TAC DONG SO LENH ################")
    ords = {}
    for N in NDAYS:
        onv = np.full(len(m_min), np.nan)
        onv[okh] = ON[N][hi[okh]]
        sel = devm & inw1 & np.isfinite(onv)
        d_ = dict(pct_on=float(np.nanmean(ON[N][hw])), n_ev_w1=int(sel.sum()),
                  pct_ev_w1=float((onv[sel] == 1).mean()),
                  n_ev_dev=int((devm & np.isfinite(onv)).sum()),
                  pct_ev_dev=float(np.nanmean(onv[devm])))
        say("  N=%dd: %% gio ON trong W1 = %.1f%% (= %% thoi gian phai giam size)" % (N, 100 * d_["pct_on"]))
        say("         %% event MOM15 trong W1 roi vao gio ON = %.1f%% (n=%d) | toan DEV 2022-2025 = %.1f%% (n=%d)" % (
            100 * d_["pct_ev_w1"], d_["n_ev_w1"], 100 * d_["pct_ev_dev"], d_["n_ev_dev"]))
        ords["N%d" % N] = d_
    T_RES["orders"] = ords

    # ---------- (G) kinh te luat ----------
    say("")
    say("################ (G) KINH TE LUAT: s=0,5 khi ON (proxy EW) ################")
    rules = {}
    for N in NDAYS:
        for H in (24, 1):
            nn, tt = EW[H]
            idx = ((tt - T0_MIN) // 60).astype(np.int64)
            st = ON[N][idx]
            keep = np.isfinite(st)
            nn = nn[keep]; tt = tt[keep]; st = st[keep].astype(np.float64)
            rn = 0.5 * nn * (st == 1) + nn * (st == 0)
            tb_ = tails(nn); tr_ = tails(rn)
            mdb = path_maxdd(nn, tt); mdr = path_maxdd(rn, tt)
            dmean = tr_["mean"] - tb_["mean"]; dcvar = tr_["cvar5"] - tb_["cvar5"]
            dp01 = tr_["p01"] - tb_["p01"]
            say("  N=%dd H=%dh (%.1f%% gio ON): baseline mean=%+.4f%% CVaR5=%+.4f%% p01=%+.4f%% maxDD(path)=%+.2f%%" % (
                N, H, 100 * st.mean(), 100 * tb_["mean"], 100 * tb_["cvar5"], 100 * tb_["p01"], 100 * mdb))
            say("        rule(0,5): mean=%+.4f%% (D=%+.4f%%) CVaR5=%+.4f%% (D=%+.4f%%) p01=%+.4f%% (D=%+.4f%%) maxDD(path)=%+.2f%% (D=%+.2f%%)" % (
                100 * tr_["mean"], 100 * dmean, 100 * tr_["cvar5"], 100 * dcvar,
                100 * tr_["p01"], 100 * dp01, 100 * mdr, 100 * (mdr - mdb)))
            say("        ty le loi ich/chi phi (D CVaR5 / D mean) = %s" % (
                "%.2fx" % (dcvar / dmean) if dmean != 0 else "n/a"))
            rules["N%dd_H%dh" % (N, H)] = dict(base=tb_, rule=tr_, dmean=float(dmean), dcvar5=float(dcvar),
                                               dp01=float(dp01), maxdd_base=mdb, maxdd_rule=mdr,
                                               ratio=float(dcvar / dmean) if dmean != 0 else float("nan"),
                                               pct_on=float(st.mean()), n=int(len(nn)))
    T_RES["rule"] = rules
    T_RES["tail"] = tail_res
    json.dump(T_RES, open(OUT + "/results_crowded.json", "w"), indent=1)
    open(OUT + "/report_crowded.txt", "w").write("\n".join(REP) + "\n")
    say("")
    say("elapsed %.0fs" % (time.time() - t_all))


if __name__ == "__main__":
    main()
