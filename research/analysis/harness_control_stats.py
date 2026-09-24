#!/usr/bin/env python3
"""HARNESS_CONTROL stats — A (positive control MOM15) / B (placebo + FP rate) / C (MDE).

Harness nguyen ban (PREREG §2): block-72h bootstrap 2000 rep seed 20260905, CI x1.21, null test
block sign-flip 72h, ICC, DEV = 2022-01-01..2024-06-30.

Doc /tmp/harness_ctl/{ev1.csv,ev2.csv,placebo.npz,pool.npz}. Thuan Python, khong Java, khong push.
"""
import math
import sys

import numpy as np
import pandas as pd

OUT = "/tmp/harness_ctl"
SEED = 20260905
NREP = 2000
BLOCK_H = 72
CI_INFLATE = 1.21
DEV_START = int(pd.Timestamp("2022-01-01", tz="UTC").timestamp() // 60)
DEV_END = int(pd.Timestamp("2024-07-01", tz="UTC").timestamp() // 60)
NPLAC = 200
X_GRID = [0.0025, 0.005, 0.01, 0.02, 0.04]
N_GRID = [100, 200, 500, 1000, 2000, 5000, 20000, 50000]


def block_boot(net, blk, inflate=1.0, nrep=NREP, seed=SEED):
    """CHEP NGUYEN harness: groupby block -> sum/count; resample blocks; percentile 2.5/97.5;
    half-width * inflate; obs = mean."""
    g = pd.DataFrame({"b": blk, "x": net}).groupby("b")["x"]
    s = g.sum().values
    c = g.count().values
    nb = len(s)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nb, (nrep, nb))
    means = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = net.mean()
    half = (hi - lo) / 2.0 * inflate
    return dict(obs=obs, lo=lo, hi=hi, half=half, ci_lo=obs - half, ci_hi=obs + half,
                p_gt0=float((means > 0).mean()))


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
    k = grp.count().values
    mi = grp.mean().values
    gm = net.mean()
    a = len(k)
    ni = len(net)
    if a < 2 or ni <= a:
        return float("nan")
    msb = (k * (mi - gm) ** 2).sum() / (a - 1)
    within = net - df["g"].map(grp.mean()).values
    msw = (within ** 2).sum() / (ni - a)
    k0 = (ni - (k ** 2).sum() / ni) / (a - 1)
    den = msb + (k0 - 1) * msw
    return (msb - msw) / den if den != 0 else float("nan")


def prep(df):
    df = df.copy()
    df["blk"] = df["entry_ts"] // (BLOCK_H * 60)
    df["date"] = pd.to_datetime(df["entry_ts"] + 420, unit="m").dt.strftime("%Y-%m-%d")
    df["dayid"] = pd.factorize(df["date"])[0]
    df["is_dev"] = (df["entry_ts"] >= DEV_START) & (df["entry_ts"] < DEV_END)
    df["completed"] = df["hold"] >= 1440
    return df


def summ(sub, label):
    n = len(sub)
    if n == 0:
        return "%s: N=0" % label
    net = sub["net_ret"].values
    r = block_boot(net, sub["blk"].values, inflate=1.0)
    rl = block_boot(net, sub["blk"].values, inflate=CI_INFLATE)
    t = net.mean() / (net.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    return ("%s: N=%d meanNet=%.4f%% meanRaw=%.4f%% win=%.1f%% t(iid)=%.2f CI72h=[%.4f%%,%.4f%%] "
            "p(>0)=%.3f half=%.4f%% | CI72h_x1.21=[%.4f%%,%.4f%%]" % (
                label, n, net.mean() * 100, sub["raw_ret"].mean() * 100, (net > 0).mean() * 100, t,
                r["lo"] * 100, r["hi"] * 100, r["p_gt0"], r["half"] * 100,
                rl["ci_lo"] * 100, rl["ci_hi"] * 100))


def half_centered(net_r, blk_r):
    """nua-do-rong CI x1.21 cua chuoi da center (mean=0) -> detection tai X <=> X > half."""
    c = net_r - net_r.mean()
    return block_boot(c, blk_r, inflate=CI_INFLATE)["half"]


def main():
    rep = []
    ev1 = prep(pd.read_csv(OUT + "/ev1.csv"))
    ev2 = prep(pd.read_csv(OUT + "/ev2.csv"))

    rep.append("=== HARNESS CONTROL: A positive (MOM15) / B placebo / C MDE ===")
    rep.append("pre-reg docs/prereg/PREREG_HARNESS_CONTROL.md (commit 9611823); harness nguyen ban: HOLD 1440,")
    rep.append("fee 0.10%% + slip 0.5x range + funding; CI block-72h 2000 rep seed %s x1.21; DEV=%s..%s"
               % (SEED, "2022-01-01", "2024-06-30"))

    # ---------------- A ----------------
    rep.append("")
    rep.append("################ A. POSITIVE CONTROL — MOM15 (rateDown15MAvg < -0.028) ################")
    for tag, df, kk in (("A-PRIMARY (k=1, = SMALL_DOWN_15M live)", ev1, 1),
                        ("A-SECONDARY (k=2, so vong truoc)", ev2, 2)):
        rep.append("")
        rep.append("---- %s ----" % tag)
        rep.append(summ(df, "ALL 2021-2025"))
        rep.append(summ(df[df["is_dev"]], "DEV 2022-01..2024-06"))
        rep.append(summ(df[~df["is_dev"]], "NON-DEV"))
        rep.append("-- by year --")
        for yr in sorted(df["year"].unique()):
            rep.append("  " + summ(df[df["year"] == yr], "Y%d" % yr))
        rep.append("-- %%coin+ / delist / null / ICC --")
        pmg = df.groupby("sym")["net_ret"].agg(["mean", "count"])
        for mt in (1, 5, 10):
            s2 = pmg[pmg["count"] >= mt]
            if len(s2):
                rep.append("  min_trades>=%d: nsym=%d %%coin+=%.1f%%" % (mt, len(s2), (s2["mean"] > 0).mean() * 100))
        comp = df[df["completed"]]
        dl = df[~df["completed"]]
        rep.append("  completed N=%d meanNet=%.4f%% | short_delist N=%d meanNet=%.4f%%" % (
            len(comp), comp["net_ret"].mean() * 100 if len(comp) else float("nan"),
            len(dl), dl["net_ret"].mean() * 100 if len(dl) else float("nan")))
        for tag2, sub in (("ALL", df), ("DEV", df[df["is_dev"]])):
            if len(sub) < 5:
                continue
            o, nm, ns, pv = block_perm(sub["net_ret"].values, sub["blk"].values)
            rep.append("  null(block sign-flip 72h) %s: obs=%.5f%% nullMean=%.5f%% sd=%.5f%% p(>=obs)=%.4f"
                       % (tag2, o * 100, nm * 100, ns * 100, pv))
            rep.append("  ICC %s: ICC(day)=%.4f ICC(72h)=%.4f" % (
                tag2, icc(sub["net_ret"].values, sub["dayid"].values),
                icc(sub["net_ret"].values, sub["blk"].values)))
        dev = df[df["is_dev"]]
        r = block_boot(dev["net_ret"].values, dev["blk"].values, inflate=CI_INFLATE)
        rep.append("  ** CỔNG A (PREREG §3) k=%d: DEV mean=%+.4f%% ; CI72h_x1.21=[%.4f%%,%.4f%%] ; p(>0)=%.3f "
                   "=> %s **" % (kk, dev["net_ret"].mean() * 100, r["ci_lo"] * 100, r["ci_hi"] * 100,
                                 r["p_gt0"], "PASS" if (dev["net_ret"].mean() > 0 and r["ci_lo"] > 0) else "KHONG DAT"))

    # ---------------- B ----------------
    rep.append("")
    rep.append("################ B. NEGATIVE CONTROL (placebo) ################")
    z = np.load(OUT + "/placebo.npz")
    pnet = z["net"].astype(np.float64)          # (N_ev1, 200)
    pmin = z["minute"]
    pblk = pmin // (BLOCK_H * 60)
    is_dev = (pmin >= DEV_START) & (pmin < DEV_END)
    rep.append("placebo events=%d (day-permute, giu symbol + gio:phut, ngay ngau nhien tren DEV); "
               "rep=1..%d seed=%d+r" % (len(pmin), NPLAC, SEED))

    def fp_table(mat, blk_arr, label):
        out = []
        means, halfs, fp1, fp2, fpneg = [], [], 0, 0, 0
        for rr in range(mat.shape[1]):
            col = mat[:, rr]
            ok = np.isfinite(col)
            if ok.sum() < 10:
                continue
            v = col[ok]
            r = block_boot(v, blk_arr[ok], inflate=CI_INFLATE)
            means.append(v.mean())
            halfs.append(r["half"])
            if r["ci_lo"] > 0:
                fp1 += 1
            if r["ci_lo"] > 0 or r["ci_hi"] < 0:
                fp2 += 1
            if r["ci_hi"] < 0:
                fpneg += 1
        n = len(means)
        means = np.array(means)
        halfs = np.array(halfs)
        out.append("%s: reps=%d" % (label, n))
        out.append("  mean(net) qua cac rep: mean=%+.5f%% sd=%.5f%% min=%+.4f%% max=%+.4f%%"
                   % (means.mean() * 100, means.std() * 100, means.min() * 100, means.max() * 100))
        out.append("  CI72h_x1.21 half-width: median=%.4f%% p80=%.4f%% p95=%.4f%%"
                   % (np.median(halfs) * 100, np.percentile(halfs, 80) * 100, np.percentile(halfs, 95) * 100))
        out.append("  ** FP_1side (CI lo > 0, bao nham edge DUONG) = %d/%d = %.1f%% **" % (fp1, n, 100.0 * fp1 / n))
        out.append("  FP_2side (CI loai 0) = %d/%d = %.1f%% | CI hi < 0 (drag chi phi, KHONG phai FP) = %d/%d = %.1f%%"
                   % (fp2, n, 100.0 * fp2 / n, fpneg, n, 100.0 * fpneg / n))
        return out, halfs, means

    lines, half_p_all, mean_p_all = fp_table(pnet, pblk, "B-PRIMARY (day-permute) — ALL event")
    rep += ["  " + x for x in lines]

    lines, half_p_dev, mean_p_dev = fp_table(pnet[is_dev], pblk[is_dev],
                                             "B-PRIMARY (day-permute) — DEV event (headline)")
    rep += ["  " + x for x in lines]

    # B-secondary: same-minute random symbol from pool
    pz = np.load(OUT + "/pool.npz")
    pool_min = pz["minute"].astype(np.int64)
    pool_net = pz["net"].astype(np.float64)
    ordr = np.argsort(pool_min, kind="stable")
    pool_min = pool_min[ordr]
    pool_net = pool_net[ordr]
    upm, start, cntm = np.unique(pool_min, return_index=True, return_counts=True)
    pos_of = {int(m): i for i, m in enumerate(upm)}
    ev1_min = pmin                     # primary event minutes (same order as pnet rows)
    keep_ev = np.array([int(m) in pos_of for m in ev1_min])
    rep.append("")
    rep.append("B-SECONDARY (same-minute random symbol): pool rows=%d ; event co pool=%d/%d"
               % (len(pool_min), int(keep_ev.sum()), len(ev1_min)))
    if keep_ev.sum() > 10:
        idxs = np.array([pos_of[int(m)] for m in ev1_min[keep_ev]])
        cnts = cntm[idxs]
        sec = np.empty((int(keep_ev.sum()), NPLAC), dtype=np.float64)
        for rr in range(NPLAC):
            rng = np.random.default_rng(SEED + rr + 1)
            pick = np.array([rng.integers(0, c) for c in cnts])
            sec[:, rr] = pool_net[start[idxs] + pick]
        msk = np.isfinite(sec).all(axis=1)
        lines, half_s_all, mean_s_all = fp_table(sec, (ev1_min[keep_ev][msk] // (BLOCK_H * 60)),
                                                 "B-SECONDARY (same-minute random symbol) — ALL")
        rep += ["  " + x for x in lines]
        devm = (ev1_min[keep_ev][msk] >= DEV_START) & (ev1_min[keep_ev][msk] < DEV_END)
        lines, half_s_dev, mean_s_dev = fp_table(sec[devm], (ev1_min[keep_ev][msk][devm] // (BLOCK_H * 60)),
                                                 "B-SECONDARY — DEV")
        rep += ["  " + x for x in lines]
        rep.append("  (B-SECONDARY giu THOI DIEM, bo CHON SYMBOL: neu dong duong manh => edge la hieu ung")
        rep.append("   thoi diem/market-timing co that trong du lieu, khong phai loi harness.)")
    else:
        half_s_all = half_s_dev = np.zeros(0)

    # ---------------- C ----------------
    rep.append("")
    rep.append("################ C. POWER / MDE (don vi %%/lenh) ################")
    rep.append("Chuoi nen = placebo B-PRIMARY. Detection = CI72h_x1.21 lo > 0 (cung cong GO).")
    rep.append("Voi chuoi net -> (net - mean) + X thi half-width KHONG doi va obs = X, nen")
    rep.append("detection <=> X > half-width(centered) — dung dan, khong xap xi (kiem chung o duoi).")

    def mde_from_half(halfs, label):
        out = []
        out.append("  %s: n_rep=%d | half-width(centered) median=%.4f%% p80=%.4f%% p95=%.4f%%"
                   % (label, len(halfs), np.median(halfs) * 100, np.percentile(halfs, 80) * 100,
                      np.percentile(halfs, 95) * 100))
        power = {}
        for X in X_GRID:
            power[X] = float((halfs < X).mean())
            out.append("    X=%5.2f%% -> power=%.1f%%" % (X * 100, power[X] * 100))
        hit = [X for X in X_GRID if power[X] >= 0.8]
        out.append("    => MDE (X nho nhat power>=80%%) = %s" % (
            ("%.2f%%/lenh" % (min(hit) * 100)) if hit else "> 4%/lenh (khong dat 80%% tren luoi)"))
        return out, power, (min(hit) if hit else None)

    # half-width centered cho tung rep placebo (dup dung RNG/seed nhu harness)
    def halfs_for(net, blk, mask=None, nsub=None, seed=SEED):
        hs = []
        rng = np.random.default_rng(seed)
        for rr in range(net.shape[1]):
            col = net[:, rr]
            ok = np.isfinite(col)
            if mask is not None:
                ok = ok & mask
            if ok.sum() < 10:
                continue
            v = col[ok]
            b = blk[ok]
            if nsub is not None and len(v) > nsub:
                pick = np.sort(rng.choice(len(v), size=nsub, replace=False))
                v = v[pick]
                b = b[pick]
            hs.append(half_centered(v, b))
        return np.array(hs)

    # verify the identity on 3 reps
    chk = []
    for rr in (0, 50, 100):
        col = pnet[is_dev, rr]
        ok = np.isfinite(col)
        v, b = col[ok], pblk[is_dev][ok]
        h = half_centered(v, b)
        Xt = 0.01
        rs = block_boot((v - v.mean()) + Xt, b, inflate=CI_INFLATE)
        chk.append("rep%d: X=1%% -> ci_lo=%.6f%% (X-half=%.6f%%)" % (rr, rs["ci_lo"] * 100, (Xt - h) * 100))
    rep.append("  kiem chung danh tinh (3 rep): " + " | ".join(chk))

    hs_dev = halfs_for(pnet[is_dev], pblk[is_dev])
    lines, power_dev, mde_dev = mde_from_half(hs_dev, "MDE @ N = N_A_PRIMARY_DEV")
    rep += lines

    n_ev_dev = int(np.isfinite(pnet[is_dev]).sum(axis=0).max())
    rep.append("  (N_A_PRIMARY_DEV = %d event; N_placebo/dev/rep = %d)"
               % (n_ev_dev, int(np.isfinite(pnet[is_dev]).mean(axis=0).max())))

    rep.append("")
    rep.append("-- MDE theo N (lay mau con chuoi placebo DEV, 200 rep/N) --")
    rep.append("  N        n_rep  half_med   MDE(80%)")
    mde_by_n = {}
    for N in N_GRID:
        if N > n_ev_dev:
            continue
        hs = halfs_for(pnet[is_dev], pblk[is_dev], nsub=N)
        out, ppx, mde = mde_from_half(hs, "N=%d" % N)
        mde_by_n[N] = mde
        rep.append("  %-8d %-6d %7.4f%%   %s" % (N, len(hs), np.median(hs) * 100,
                                                 ("%.2f%%" % (mde * 100)) if mde else ">4%"))
        for l in out[1:len(X_GRID) + 1]:
            rep.append("     " + l.strip())

    # ---- C-SENSITIVITY (exploratory): do phan giai cho tin hieu kieu capitulation ----
    rep.append("")
    rep.append("---- C-SENSITIVITY (exploratory, POST-HOC, khong thuoc thiet ke pre-reg) ----")
    rep.append("B-PRIMARY (day-permute) lam PHANG cum thoi gian (ngay ngau nhien) => half-width nho gia tao.")
    rep.append("Nen B-SECONDARY (same-minute random symbol) giu DUNG thoi diem MOM15 => half-width that cua")
    rep.append("mot tin hieu kieu capitulation voi cung N:")
    mde_clust = {}
    if 'sec' in dir() and keep_ev.sum() > 10 and msk.sum() > 50:
        blk_sec = ev1_min[keep_ev][msk] // (BLOCK_H * 60)
        sec_dev = sec[msk][devm]
        blk_sec_dev = blk_sec[devm]
        for N in ([len(sec_dev)] + [n for n in N_GRID if n < len(sec_dev)]):
            hs = halfs_for(sec_dev, blk_sec_dev, nsub=None if N == len(sec_dev) else N)
            if not len(hs):
                continue
            powr = {X: float((hs < X).mean()) for X in X_GRID}
            hit = [X for X in X_GRID if powr[X] >= 0.8]
            mde_clust[N] = min(hit) if hit else None
            rep.append("  N=%-6d half_med=%.4f%% -> power 0.25/0.5/1/2/4%% = %s ; MDE(80%%)=%s" % (
                N, np.median(hs) * 100,
                "/".join("%.0f" % (powr[X] * 100) for X in X_GRID),
                ("%.2f%%" % (min(hit) * 100)) if hit else ">4%"))

    # ---- So sanh voi cac ung vien da NULL ----
    rep.append("")
    rep.append("---- SO SANH: hieu ung DEV do duoc cua cac ung vien da NULL vs MDE ----")
    rep.append("| ung vien | N_DEV | net DEV do duoc | MDE(day-permute)@N | MDE(clustered)@N | ket luan |")
    cands = [("reversal-bounce long", 1179302, -0.00080, 0.0043, 0.0043,
              "DƯỚI MDE: |net|=0.08% < MDE~0.5% (CI rieng cua chinh no: half 0.36% -> x1.21 = 0.43%)"),
             ("BIG_UP (cu)", 89, 0.0087, None, None, ""),
             ("MEDIUM_UP (cu)", 316, 0.0184, None, None, ""),
             ("MEDIUM_DOWN (cu)", 158, 0.0125, None, None, "")]

    def mde_at(curve, N):
        best = None
        for n in sorted(curve):
            if n <= N:
                best = n
        if best is None:
            return curve[min(curve)] if curve else None
        return curve[best]

    for nm, Nc, eff, m1, m2, note in cands:
        if nm.startswith("reversal"):
            rep.append("| %s | %d | %+.3f%% | %.2f%% (CI rieng) | n/a (khong cum) | %s |" % (
                nm, Nc, eff * 100, m1 * 100, note))
            continue
        m_dp = mde_at(mde_by_n, Nc)
        m_cl = mde_at(mde_clust, Nc) if mde_clust else None
        below = (m_dp is not None and abs(eff) < m_dp) or (m_cl is not None and abs(eff) < m_cl)
        rep.append("| %s | ~%d | %+.2f%% | %s | %s | %s |" % (
            nm, Nc, eff * 100,
            ("%.2f%%" % (m_dp * 100)) if m_dp else "n/a",
            ("%.2f%%" % (m_cl * 100)) if m_cl else "n/a",
            "DƯỚI MDE" if below else "tren MDE"))
    rep.append("")
    rep.append("Ghi chu: N_DEV cua BIG_UP/MEDIUM_UP/MEDIUM_DOWN = tong N theo nam 2022+2023+2024 trong")
    rep.append("docs/result/RESULT_BIGUP_MEDIUPDOWN.md §3.2 (can tren, 2024 chi tinh 6 thang); reversal-bounce N=1 179 302")
    rep.append("va net DEV -0.080% lay tu docs/result/RESULT_REVERSAL_BOUNCE.md (CI rieng cua no: half x1.21=0.43%).")

    txt = "\n".join(rep)
    open(OUT + "/report_A.txt", "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
