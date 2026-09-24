#!/usr/bin/env python3
"""OI_STUDY — do H1 (DeltaOI factor cross-section) / H2 (OI+gia phan ky) / H3 (OI overlay MOM15).

Pre-reg: docs/prereg/PREREG_OI_STUDY.md (commit 7c5f025, chot TRUOC khi do; KHONG sua thiet ke).
Harness: CI block-72h bootstrap 2000 rep seed 20260905 x1.21, null block sign-flip 72h, MDE p80
nua-do-rong, N_eff = N/(1+(n_bar-1)*ICC72h) — ham block_boot/block_perm/icc CHEP NGUYEN tu
research/analysis/harness_control_stats.py, chi doi cach lay half-width cho chuoi null (precompute
per-block sum) de chay duoc 500 rep.

Thuan Python, khong Java, khong claude-run, khong cham 2026. Doc /tmp/oi_study/*.npy + pools.npz.
"""
import json
import math
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

OUT = "/tmp/oi_study"
SEED = 20260905
NREP = 2000
BLOCK_H = 72
CI_INFLATE = 1.21
MIN_SYM = 50
FEE_RT = 0.0010
FEE_SIM = 0.0080
HOLD_STEPS = {12: "1h", 48: "4h", 288: "24h"}
UTC = timezone.utc
OOS0 = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp()) // 60
DEV_START_MIN = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) // 60
DEV_END_MIN = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) // 60
REP = []
T_RES = {}


def say(s=""):
    REP.append(s)
    print(s, flush=True)


# ------------------------- harness -------------------------
def _boot_from_sums(bsum, bcnt, inflate=1.0, nrep=NREP, seed=SEED, idx=None):
    nb = len(bsum)
    rng = np.random.default_rng(seed)
    if idx is None:
        idx = rng.integers(0, nb, (nrep, nb))
    means = bsum[idx].sum(axis=1) / bcnt[idx].sum(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = bsum.sum() / bcnt.sum()
    half = (hi - lo) / 2.0 * inflate
    return dict(obs=obs, half=half, ci_lo=obs - half, ci_hi=obs + half,
                p_gt0=float((means > 0).mean()))


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


def mde_half(net, blk, nrep_null=500, seed=SEED):
    """MDE = p80 cua nua-do-rong (x1.21) tren 500 chuoi null sign-flip 72h ghep cau truc block."""
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


def full(net, ts_min, label):
    net = np.asarray(net, dtype=np.float64)
    ts_min = np.asarray(ts_min, dtype=np.int64)
    blk = ts_min // (BLOCK_H * 60)
    day = ts_min // 1440
    n = len(net)
    r = block_boot(net, blk, inflate=1.0)
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
    return dict(label=label, n=n, mean=float(net.mean()), med=float(np.median(net)),
                win=float((net > 0).mean()), t_iid=float(t),
                ci_lo=float(rl["ci_lo"]), ci_hi=float(rl["ci_hi"]), half=float(rl["half"]),
                p_gt0=float(rl["p_gt0"]), raw_lo=float(r["ci_lo"]), raw_hi=float(r["ci_hi"]),
                nb=nb, icc72=float(ic72), n_eff=float(neff),
                null_mean=nm, null_sd=ns, p_perm=pv,
                mean_is=float(net[~oosm].mean()), mean_oos=float(net[oosm].mean()),
                n_oos=int(oosm.sum()), n_is=int((~oosm).sum()),
                qpos_all=float((qm > 0).mean()), nq_all=int(len(qm)),
                qpos_oos=float((oos_q > 0).mean()) if len(oos_q) else float("nan"),
                nq_oos=int(len(oos_q)), ypos_all=float((ym > 0).mean()), nyr=int(len(ym)))


def line(d):
    return ("%s: N=%d mean=%+.4f%% med=%+.4f%% win=%.1f%% | CI72h_x1.21=[%+.4f%%,%+.4f%%] p(>0)=%.3f "
            "pNull=%.4f | IS=%+.4f%% OOS=%+.4f%% (N_oos=%d) q+ALL=%.0f%% OOS=%.0f%% (%dq) y+ALL=%.0f%% "
            "| N_eff=%.1f ICC72=%.3f nblk=%d" % (
                d["label"], d["n"], 100 * d["mean"], 100 * d["med"], 100 * d["win"],
                100 * d["ci_lo"], 100 * d["ci_hi"], d["p_gt0"], d["p_perm"],
                100 * d["mean_is"], 100 * d["mean_oos"], d["n_oos"],
                100 * d["qpos_all"], 100 * d["qpos_oos"], d["nq_oos"], 100 * d["ypos_all"],
                d["n_eff"], d["icc72"], d["nb"]))


def contrast(a, ta, b, tb, label):
    """Tuong phan mean(a)-mean(b), CI block-72h x1.21 rut DOC LAP hai ben."""
    rng = np.random.default_rng(SEED)
    sa, ca = sums_of(a, ta // (BLOCK_H * 60))
    sb, cb = sums_of(b, tb // (BLOCK_H * 60))
    ia = rng.integers(0, len(sa), (NREP, len(sa)))
    ib = rng.integers(0, len(sb), (NREP, len(sb)))
    dd = sa[ia].sum(axis=1) / ca[ia].sum(axis=1) - sb[ib].sum(axis=1) / cb[ib].sum(axis=1)
    obs = a.mean() - b.mean()
    half = (np.percentile(dd, 97.5) - np.percentile(dd, 2.5)) / 2 * CI_INFLATE
    d = dict(label=label, n=len(a), mean=float(obs), ci_lo=float(obs - half), ci_hi=float(obs + half),
             p_gt0=float((dd > 0).mean()), half=float(half),
             mean_a=float(a.mean()), mean_b=float(b.mean()))
    say("  %s: %+.4f%% - %+.4f%% = %+.4f%% | CI72h_x1.21=[%+.4f%%,%+.4f%%] p(diff>0)=%.3f" % (
        label, 100 * a.mean(), 100 * b.mean(), 100 * obs, 100 * (obs - half), 100 * (obs + half),
        d["p_gt0"]))
    return d


def net_of(i, u, d, c5, rg5, f5, j, iarr):
    raw = c5[j][u] / c5[i][u] - 1.0
    return (raw - FEE_RT - 0.5 * rg5[i][u] / c5[i][u] - (f5[j][u] - f5[i][u])).astype(np.float64)


# ------------------------- main -------------------------
def main():
    t_all = time.time()
    meta = json.load(open(OUT + "/meta.json"))
    NSTEP, ncol, T0 = meta["nstep"], meta["ncol"], meta["T0"]
    d24 = np.load(OUT + "/d24.npy", mmap_mode="r")
    oiz = np.load(OUT + "/oiz.npy", mmap_mode="r")
    c5 = np.load(OUT + "/c5.npy", mmap_mode="r")
    rg5 = np.load(OUT + "/rg5.npy", mmap_mode="r")
    f5 = np.load(OUT + "/f5.npy", mmap_mode="r")
    a0 = T0 * 1000 // 300000
    i0 = (int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) * 1000 // 300000) - a0
    say("### 0. Du lieu / cua so")
    say("NSTEP=%d ncol=%d buoc0=%s | i0(DEV)=%d | DEV=%d buoc 5m = %.2f nam" % (
        NSTEP, ncol, datetime.fromtimestamp(T0, UTC).strftime("%Y-%m-%d"), i0, NSTEP - i0,
        (NSTEP - i0) * 5 / 60 / 24 / 365.25))
    hours = np.arange(i0 + ((-i0) % 12), NSTEP, 12, dtype=np.int64)
    ts_h = (hours + a0) * 5
    say("luoi 1h: %d moc %s .. %s" % (
        len(hours), datetime.fromtimestamp(int(ts_h[0]) * 60, UTC).strftime("%Y-%m-%d %H:%M"),
        datetime.fromtimestamp(int(ts_h[-1]) * 60, UTC).strftime("%Y-%m-%d %H:%M")))
    nv = 0; ntot = 0
    for i in hours[::50]:
        u = np.isfinite(c5[i]) & np.isfinite(d24[i]) & (c5[i] > 0)
        ntot += 1; nv += int(u.sum())
    say("universe trung binh tren mau luoi = %.1f symbol/moc (MIN_SYM=%d)" % (nv / max(ntot, 1), MIN_SYM))

    # ===================== H1 =====================
    say("")
    say("################ H1 — ΔOI (oi_delta24h) NHU FACTOR CROSS-SECTION ################")
    say("luoi 1h, decile rank tat dinh, Q9=ΔOI cao nhat (LONG-ONLY quan tam Q9). Phi CHINH 0,10%% RT + slip + funding.")
    h1 = {}
    for hstep, hname in HOLD_STEPS.items():
        acc = {g: [] for g in list(range(10)) + ["EW"]}
        ats = {g: [] for g in list(range(10)) + ["EW"]}
        nsec = 0
        for i in hours:
            j = i + hstep
            if j >= NSTEP:
                continue
            d = d24[i]; c = c5[i]
            u = np.isfinite(d) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
            if u.sum() < MIN_SYM:
                continue
            nsec += 1
            idx = np.flatnonzero(u)
            order = np.argsort(d[idx], kind="stable")
            N = len(idx)
            dec_r = np.empty(N, dtype=np.int8)
            dec_r[order] = np.minimum(np.arange(N) * 10 // N, 9)
            net = net_of(i, u, d, c5, rg5, f5, j, None)
            tsm = int(ts_h[np.searchsorted(hours, i)])
            for g in range(10):
                m = dec_r == g
                acc[g].append(net[m]); ats[g].append(np.full(int(m.sum()), tsm, dtype=np.int64))
            acc["EW"].append(net); ats["EW"].append(np.full(N, tsm, dtype=np.int64))
        say("")
        say("---- H1 horizon %s — so moc dung = %d ----" % (hname, nsec))
        r = {}
        for g in list(range(10)) + ["EW"]:
            dd = full(np.concatenate(acc[g]), np.concatenate(ats[g]),
                      "H1 %s %s" % (hname, "EW" if g == "EW" else "Q%d" % g))
            r[g] = dd
            say(line(dd))
        ew = r["EW"]
        say("  chenh vs universe EW (pp/lenh): " + "  ".join(
            "Q%d=%+.3f" % (g, 100 * (r[g]["mean"] - ew["mean"])) for g in range(10)))
        say("  OOS: EW=%+.4f%% ; " % (100 * ew["mean_oos"]) + "  ".join(
            "Q%d=%+.3f" % (g, 100 * (r[g]["mean_oos"] - ew["mean_oos"])) for g in range(10)))
        h1[hname] = r

    # ===================== H1 bien the =====================
    say("")
    say("################ H1 — BIEN THE da dang ky @ 24h (Q9, Q0, EW) ################")
    var = {}
    for vname in ("d24", "dd24_1h", "dd24_4h", "oiz"):
        acc = {g: [] for g in (9, 0, "EW")}
        ats = {g: [] for g in (9, 0, "EW")}
        for i in hours:
            j = i + 288
            if j >= NSTEP or i - 48 < 0:
                continue
            if vname == "d24":
                f = d24[i]
            elif vname == "dd24_1h":
                f = d24[i] - d24[i - 12]
            elif vname == "dd24_4h":
                f = d24[i] - d24[i - 48]
            else:
                f = oiz[i]
            c = c5[i]
            u = np.isfinite(f) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
            if u.sum() < MIN_SYM:
                continue
            idx = np.flatnonzero(u)
            order = np.argsort(f[idx], kind="stable")
            N = len(idx)
            dec_r = np.empty(N, dtype=np.int8)
            dec_r[order] = np.minimum(np.arange(N) * 10 // N, 9)
            net = net_of(i, u, f, c5, rg5, f5, j, None)
            tsm = int(ts_h[np.searchsorted(hours, i)])
            for g in (9, 0):
                m = dec_r == g
                acc[g].append(net[m]); ats[g].append(np.full(int(m.sum()), tsm, dtype=np.int64))
            acc["EW"].append(net); ats["EW"].append(np.full(N, tsm, dtype=np.int64))
        var[vname] = {}
        for g in (9, 0, "EW"):
            dd = full(np.concatenate(acc[g]), np.concatenate(ats[g]),
                      "H1var/%s %s" % (vname, "EW" if g == "EW" else "Q%d" % g))
            var[vname][g] = dd
            say(line(dd))
        d9 = contrast(np.concatenate(acc[9]), np.concatenate(ats[9]),
                      np.concatenate(acc["EW"]), np.concatenate(ats["EW"]),
                      "H1var/%s Q9 - EW" % vname)

    # ===================== H2 =====================
    say("")
    say("################ H2 — OI + GIA PHAN KY (tercile 3x3, 24h) ################")
    acc = {}
    for a in range(3):
        for b in range(3):
            acc[(a, b)] = [[], []]
    acc["EW"] = [[], []]
    nsec = 0
    for i in hours:
        j = i + 288
        if j >= NSTEP or i - 288 < 0:
            continue
        d = d24[i]; c = c5[i]; cp = c5[i - 288]
        u = (np.isfinite(d) & np.isfinite(c) & np.isfinite(cp) & np.isfinite(c5[j]) & (c > 0) & (cp > 0))
        if u.sum() < MIN_SYM:
            continue
        nsec += 1
        idx = np.flatnonzero(u)
        dv = np.asarray(d[idx], dtype=np.float64)
        p24 = c[idx] / cp[idx] - 1.0
        oi_ter = np.minimum((np.argsort(np.argsort(dv, kind="stable")) * 3) // len(idx), 2)
        p_ter = np.minimum((np.argsort(np.argsort(p24, kind="stable")) * 3) // len(idx), 2)
        net = net_of(i, u, d, c5, rg5, f5, j, None)
        tsm = int(ts_h[np.searchsorted(hours, i)])
        for a in range(3):
            for b in range(3):
                m = (oi_ter == a) & (p_ter == b)
                if m.any():
                    acc[(a, b)][0].append(net[m])
                    acc[(a, b)][1].append(np.full(int(m.sum()), tsm, dtype=np.int64))
        acc["EW"][0].append(net); acc["EW"][1].append(np.full(len(idx), tsm, dtype=np.int64))
    say("so moc 3x3 dung duoc = %d" % nsec)
    h2 = {}
    for key in [(a, b) for a in range(3) for b in range(3)] + ["EW"]:
        net = np.concatenate(acc[key][0]); tt = np.concatenate(acc[key][1])
        lab = "H2 EW" if key == "EW" else "H2 OI_ter%d x P24_ter%d" % key
        h2[key] = full(net, tt, lab)
        say(line(h2[key]))
    say("")
    say("H2 - net 24h (%%/lenh) 3x3 [hang=tercile ΔOI thap->cao, cot=tercile P24 thap->cao]:")
    for a in range(3):
        say("   ΔOI_ter%d: " % a + "  ".join("%+8.4f" % (100 * h2[(a, b)]["mean"]) for b in range(3)) +
            "   (N " + "/".join("%d" % h2[(a, b)]["n"] for b in range(3)) + ")")
    say("")
    say("H2 - tuong phan:")
    cP = {}
    for k1, k2 in [((2, 0), (2, 2)), ((2, 0), "EW"), ((2, 0), (2, 1)), ((2, 2), "EW"), ((0, 0), "EW")]:
        a = np.concatenate(acc[k1][0]); ta = np.concatenate(acc[k1][1])
        b = np.concatenate(acc[k2][0]) if k2 != "EW" else np.concatenate(acc["EW"][0])
        tb = np.concatenate(acc[k2][1]) if k2 != "EW" else np.concatenate(acc["EW"][1])
        cP["%s-%s" % (k1, k2)] = contrast(a, ta, b, tb, "H2 %s - %s" % (k1, k2))

    # ===================== H3 =====================
    say("")
    say("################ H3 — OI OVERLAY LEN MOM15 (M-LEVEL k=1) ################")
    z = np.load("/tmp/funding_factor/pools.npz")
    m_min = z["m_min"].astype(np.int64); m_sym = z["m_sym"].astype(np.int64)
    m_valid = z["m_valid"]; m_raw = z["m_raw"]; m_slip = z["m_slip"]; m_fund = z["m_fund"]
    j24 = 1
    base24 = m_raw[j24].astype(np.float64) - m_slip.astype(np.float64) - m_fund[j24].astype(np.float64)
    devm = (m_min >= DEV_START_MIN) & (m_min < DEV_END_MIN)
    say("  [DOI CHUNG (b) NEO MOM15] n_DEV=%d base=%+.4f%% net@0,10%%=%+.4f%% (ky vong +1,6690%%, n=7128, ±0,05pp)" % (
        devm.sum(), 100 * base24[devm].mean(), 100 * base24[devm].mean() - 0.10))
    T_RES["anchor"] = dict(n=int(devm.sum()), base=float(base24[devm].mean()),
                           net10=float(base24[devm].mean() - 0.10))
    sel = devm & (((m_valid >> j24) & 1) == 1) & np.isfinite(base24)
    net24 = base24[sel] - FEE_RT
    mm = m_min[sel]; ss = m_sym[sel]
    n = len(mm)
    t0m = T0 // 60
    stp = (mm - t0m) // 5
    off = mm - (t0m + 5 * stp)
    okv = (stp >= 0) & (stp < NSTEP) & (off <= 15)
    d24v = np.full(n, np.nan); oizv = np.full(n, np.nan)
    d24v[okv] = np.asarray(d24[stp[okv], ss[okv]], dtype=np.float64)
    oizv[okv] = np.asarray(oiz[stp[okv], ss[okv]], dtype=np.float64)
    say("  [H3 coverage] tra duoc OI(<=15 phut): %d/%d = %.1f%% | d24 finite=%.1f%% oiz finite=%.1f%%" % (
        okv.sum(), n, 100 * okv.sum() / n, 100 * np.isfinite(d24v).mean(), 100 * np.isfinite(oizv).mean()))
    T_RES["h3_coverage"] = float(okv.sum() / n)
    hour_of = (mm // 60) * 60
    uniq_h = np.unique(hour_of)
    hmap = np.full(n, np.nan)
    for hh in uniq_h:
        hm = int((hh - t0m) // 5)
        if hm < 0 or hm >= NSTEP:
            continue
        row = d24[hm]
        u = np.isfinite(c5[hm]) & np.isfinite(row)
        if u.sum() < MIN_SYM:
            continue
        idxs = np.flatnonzero(u)
        rk = np.argsort(np.argsort(np.asarray(row[idxs]), kind="stable")) / (len(idxs) - 1.0)
        mp = np.full(ncol, np.nan); mp[idxs] = rk
        sh = hour_of == hh
        hmap[sh] = mp[ss[sh]]
    say("  [H3 coverage] rank cross-section d24: %.1f%% | so moc gio = %d" % (
        100 * np.isfinite(hmap).mean(), len(uniq_h)))
    np.savez_compressed(OUT + "/h3_events.npz", mm=mm, ss=ss, net=net24, d24=d24v, oiz=oizv, rk=hmap)
    h3 = {}
    for fname, fv in (("d24(muc)", d24v), ("oiz(muc)", oizv), ("rank_d24(cs)", hmap)):
        ok = np.isfinite(fv)
        if ok.sum() < 100:
            continue
        v = fv[ok]
        ter = np.minimum((np.argsort(np.argsort(v, kind="stable")) * 3) // len(v), 2)
        say("")
        say("-- H3 tach theo %s (n=%d) --" % (fname, ok.sum()))
        for t3 in range(3):
            m = ter == t3
            dd = full(net24[ok][m], mm[ok][m], "H3 %s ter%d" % (fname, t3))
            h3[(fname, t3)] = dd
            say(line(dd))
        a = net24[ok][ter == 2]; ta = mm[ok][ter == 2]
        b = net24[ok][ter == 0]; tb = mm[ok][ter == 0]
        h3[(fname, "c")] = contrast(a, ta, b, tb, "H3 %s ter2 - ter0" % fname)
        y = (net24[ok] > 0).astype(np.float64)
        r = np.argsort(np.argsort(v, kind="stable")) + 1.0
        n1 = y.sum(); n0 = len(y) - n1
        auc = (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 > 0 and n0 > 0 else float("nan")
        say("   %s: AUC(tach thang/thua) = %.4f  (win%%=%.1f n=%d)" % (fname, auc, 100 * y.mean(), len(y)))
        h3[(fname, "auc")] = float(auc)

    # ===================== MDE =====================
    say("")
    say("################ MDE (p80 nua-do-rong x1.21 tren 500 chuoi null sign-flip 72h) ################")
    mde = {}
    for tag, key, hname in (("H1 24h Q9 (leg long-only)", 9, "24h"), ("H1 24h EW", "EW", "24h"),
                            ("H1 4h Q9", 9, "4h"), ("H1 1h Q9", 9, "1h")):
        accq = {}
        net_all = []
        for i in hours:
            j = i + HOLD_STEPS_INV[hname]
            if j >= NSTEP:
                continue
            d = d24[i]; c = c5[i]
            u = np.isfinite(d) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
            if u.sum() < MIN_SYM:
                continue
            idx = np.flatnonzero(u)
            order = np.argsort(d[idx], kind="stable")
            N = len(idx)
            dec_r = np.empty(N, dtype=np.int8)
            dec_r[order] = np.minimum(np.arange(N) * 10 // N, 9)
            net = net_of(i, u, d, c5, rg5, f5, j, None)
            m = dec_r == key if key != "EW" else np.ones(N, bool)
            accq.setdefault("n", []).append(net[m])
            accq.setdefault("t", []).append(np.full(int(m.sum()), int(ts_h[np.searchsorted(hours, i)]), dtype=np.int64))
        netv = np.concatenate(accq["n"]); tv = np.concatenate(accq["t"])
        p80, p50 = mde_half(netv, tv // (BLOCK_H * 60))
        rl = block_boot(netv, tv // (BLOCK_H * 60), inflate=CI_INFLATE)
        _, nm, ns, _ = block_perm(netv, tv // (BLOCK_H * 60))
        mde[tag] = dict(p80=p80, p50=p50, half=rl["half"], null_sd=ns, n=len(netv))
        say("%-26s N=%8d | half-width x1.21=%+.4f%% | MDE(p80)=%+.4f%% | 2,8xSD(null)=%+.4f%% (SD=%+.4f%%)" % (
            tag, len(netv), 100 * rl["half"], 100 * p80, 100 * 2.8 * ns, 100 * ns))
    T_RES["mde"] = mde
    T_RES["h1"] = {h: {str(k): v["mean"] for k, v in r.items()} for h, r in h1.items()}
    T_RES["h1_detail"] = {h: {str(k): {kk: v[kk] for kk in ("n", "mean", "ci_lo", "ci_hi", "mean_oos", "n_eff", "qpos_oos", "p_gt0", "p_perm", "win")} for k, v in r.items()} for h, r in h1.items()}
    T_RES["h1_var"] = {vn: {str(g): {kk: d[kk] for kk in ("n", "mean", "mean_oos", "ci_lo", "ci_hi", "p_gt0")} for g, d in vv.items()} for vn, vv in var.items()}
    T_RES["h2"] = {str(k): {kk: h2[k][kk] for kk in ("n", "mean", "ci_lo", "ci_hi", "mean_oos")} for k in h2}
    T_RES["h2_contrast"] = {k: {kk: vv for kk, vv in v.items()} for k, v in cP.items()}
    T_RES["h3"] = {("%s|%s" % k): (v if isinstance(v, float) else {kk: vv for kk, vv in v.items()}) for k, v in h3.items()}
    json.dump(T_RES, open(OUT + "/results.json", "w"), indent=1)
    open(OUT + "/report.txt", "w").write("\n".join(REP) + "\n")
    say("")
    say("elapsed %.0fs" % (time.time() - t_all))


HOLD_STEPS_INV = {"1h": 12, "4h": 48, "24h": 288}

if __name__ == "__main__":
    main()
