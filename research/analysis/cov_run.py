"""COV — kiem phu (coverage) cho nhom TICK/XEP HANG. Tuan theo docs/prereg/PREREG_COV.md @ b6de3af.
CHI DEV. Khong train, khong java, khong cham VALIDATION.
"""
import json
import logging

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/cov/COV.out", "w"),
                              logging.StreamHandler()])
LG = logging.getLogger("cov")

H = 3600_000
DAY = 24 * H
SEED = 20260904
NREP_CI = 2000          # y ci_group_b.py cho phep so diem/CI
N_MC = 1000             # PREREG_COV section 3
N_BOOT = 1000           # PREREG_COV section 3
GRID_D = [1, 3, 5, 7, 9, 14, 21, 30]
ACCEPT = (0.92, 0.97)
OUT = {}

# ============================================================ 1. NAP DU LIEU
T = pd.read_csv("/home/ubuntu/feataudit/tick_stats_s1cut.csv").sort_values("ts")
T = T.reset_index(drop=True)
LG.info("tick_stats_s1cut: %d tick, ts %s .. %s", len(T),
        pd.to_datetime(T.ts.min(), unit="ms"), pd.to_datetime(T.ts.max(), unit="ms"))

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "p15", "dyn_thr", "gate_dyn_ok",
                             "score_g015", "g1lite"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
R = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                    columns=["ts", "sym", "g1_replay"])
M = C.merge(P, on=["ts", "sym"], how="inner").merge(R, on=["ts", "sym"], how="left")
M["gate_ok"] = M.gate_dyn_ok.astype(bool)
M = M.dropna(subset=["g1_replay"])
TS_MIN = int(M.ts.min())
TS_MAX = int(M.ts.max())
LG.info("M rows=%d ticks=%d gate_MO_rows=%d", len(M), M.ts.nunique(), int(M.gate_ok.sum()))

OPEN = M[M.gate_ok]


def per_tick_ic(sub, col):
    out = {}
    for ts, g in sub.groupby("ts"):
        if len(g) < 10:
            continue
        r = spearmanr(-g[col].values, g.g1_replay.values).correlation
        if not np.isnan(r):
            out[ts] = r
    return pd.Series(out, name=col)


ic_s1 = per_tick_ic(OPEN, "score")
ic_g0 = per_tick_ic(OPEN, "score_g015")
IC = pd.concat([ic_s1.rename("s1"), ic_g0.rename("g015")], axis=1).dropna()
LG.info("[B7] n_tick=%d S1=%+.4f G015=%+.4f hieu=%+.4f", len(IC), IC.s1.mean(),
        IC.g015.mean(), IC.s1.mean() - IC.g015.mean())


def topk(df, k):
    d = df.copy()
    d["rk"] = d.groupby("ts").score.rank(ascending=True, method="first")
    return d[d.rk <= k]


def rnd8(df):
    return df.sample(frac=1.0, random_state=0).groupby("ts").head(8)


T8 = topk(OPEN, 8)
R8 = rnd8(OPEN)
LG.info("[B8] top8=%.4f (n=%d) random8=%.4f (n=%d)", T8.g1_replay.mean(), len(T8),
        R8.g1_replay.mean(), len(R8))

# ============================================================ 2. MAY BOOTSTRAP
def blockagg(ts_arr, vals, blen_h, nblk):
    bid = ((np.asarray(ts_arr, dtype=np.int64) - TS_MIN) // (blen_h * H)).astype(np.int64)
    s = np.bincount(bid, weights=np.asarray(vals, dtype=float), minlength=nblk)
    c = np.bincount(bid, minlength=nblk).astype(float)
    return s[:nblk], c[:nblk]


def nblocks(blen_h):
    return int((TS_MAX - TS_MIN) // (blen_h * H)) + 1


def boot_paired(sa, ca, sb, cb, nblk, nrep, rng):
    """CI cua HIEU hai ty so tong, CUNG danh sach khoi moi rep (ghep cap)."""
    draw = rng.integers(0, nblk, size=(nrep, nblk))
    xa = sa[draw].sum(axis=1) / np.maximum(ca[draw].sum(axis=1), 1e-12)
    xb = sb[draw].sum(axis=1) / np.maximum(cb[draw].sum(axis=1), 1e-12)
    return xa - xb


def boot_single(s, c, nblk, nrep, rng):
    draw = rng.integers(0, nblk, size=(nrep, nblk))
    return s[draw].sum(axis=1) / np.maximum(c[draw].sum(axis=1), 1e-12)


# ---------- 2a. tai lap B7/B8 tai 72h (cong bat buoc) ----------
LG.info("\n=== CONG TAI LAP (72h, seed %d, nrep %d) ===", 20260903, NREP_CI)
rng0 = np.random.default_rng(20260903)
nb72 = nblocks(72)
a7s, a7c = blockagg(IC.index.values, IC.s1.values, 72, nb72)
b7s, b7c = blockagg(IC.index.values, IC.g015.values, 72, nb72)
d7 = boot_paired(a7s, a7c, b7s, b7c, nb72, NREP_CI, np.random.default_rng(20260903))
pt7 = a7s.sum() / a7c.sum() - b7s.sum() / b7c.sum()
a8s, a8c = blockagg(T8.ts.values, T8.g1_replay.values, 72, nb72)
b8s, b8c = blockagg(R8.ts.values, R8.g1_replay.values, 72, nb72)
d8 = boot_paired(a8s, a8c, b8s, b8c, nb72, NREP_CI, np.random.default_rng(20260903))
pt8 = a8s.sum() / a8c.sum() - b8s.sum() / b8c.sum()
for nm, pt, d, ref in [("B7", pt7, d7, 0.0973), ("B8", pt8, d8, 0.0182)]:
    lo, hi = np.percentile(d, [2.5, 97.5])
    LG.info("%s d=%+.5f (ban ghi cu %+.4f, lech %+.5f) CI[%+.5f,%+.5f] sd=%.5f n_blk=%d",
            nm, pt, ref, pt - ref, lo, hi, d.std(ddof=1), nb72)
    OUT[f"repro_{nm}"] = dict(point=float(pt), ref=ref, lo=float(lo), hi=float(hi),
                              sd=float(d.std(ddof=1)))

# ============================================================ 3. CHUOI DUOC KIEM
SERIES = {}
SERIES["B1_full9_core3"] = (T.ts.values, (T.repl_full9 - T.repl_core3).values,
                            np.ones(len(T)))
SERIES["B2_full9_worse2"] = (T.ts.values, (T.repl_full9 - T.repl_worse2).values,
                             np.ones(len(T)))
SERIES["B7_s1_g015"] = (IC.index.values, (IC.s1 - IC.g015).values, np.ones(len(IC)))

LG.info("\n=== 3. sd_boot theo do dai khoi (chuoi hieu tick-weighted) ===")
LG.info("%-18s %6s %8s %10s %10s %10s %8s", "chuoi", "L(d)", "n_blk", "d", "lo95", "hi95", "sd")
sd_by_L = {}
for nm, (ts_a, v_a, w_a) in SERIES.items():
    sd_by_L[nm] = {}
    for Ld in GRID_D:
        bh = Ld * 24
        nb = nblocks(bh)
        s, c = blockagg(ts_a, v_a, bh, nb)
        st = boot_single(s, c, nb, NREP_CI, np.random.default_rng(SEED))
        lo, hi = np.percentile(st, [2.5, 97.5])
        sd_by_L[nm][Ld] = float(st.std(ddof=1))
        LG.info("%-18s %6d %8d %+10.5f %+10.5f %+10.5f %8.5f", nm, Ld, nb,
                s.sum() / c.sum(), lo, hi, st.std(ddof=1))
# B8 row-weighted rieng (hieu hai nhom khac nhau)
sd_by_L["B8_top8_rnd8"] = {}
LG.info("%-18s %6s %8s %10s %10s %10s %8s", "B8(row-w)", "L(d)", "n_blk", "d", "lo95", "hi95", "sd")
for Ld in GRID_D:
    bh = Ld * 24
    nb = nblocks(bh)
    as_, ac_ = blockagg(T8.ts.values, T8.g1_replay.values, bh, nb)
    bs_, bc_ = blockagg(R8.ts.values, R8.g1_replay.values, bh, nb)
    d = boot_paired(as_, ac_, bs_, bc_, nb, NREP_CI, np.random.default_rng(SEED))
    lo, hi = np.percentile(d, [2.5, 97.5])
    sd_by_L["B8_top8_rnd8"][Ld] = float(d.std(ddof=1))
    LG.info("%-18s %6d %8d %+10.5f %+10.5f %+10.5f %8.5f", "B8_top8_rnd8", Ld, nb,
            as_.sum() / ac_.sum() - bs_.sum() / bc_.sum(), lo, hi, d.std(ddof=1))
OUT["sd_by_L"] = sd_by_L

# ============================================================ 4. DO DAI PHU THUOC THAT
def daily_series(ts_a, v_a):
    dd = ((np.asarray(ts_a, dtype=np.int64) - TS_MIN) // DAY).astype(int)
    nd = dd.max() + 1
    s = np.bincount(dd, weights=v_a.astype(float), minlength=nd)
    c = np.bincount(dd, minlength=nd).astype(float)
    x = np.where(c > 0, s / np.maximum(c, 1e-12), np.nan)
    return x, c


def acf(x, kmax):
    y = x[~np.isnan(x)]
    y = y - y.mean()
    n = len(y)
    g0 = (y * y).sum() / n
    return np.array([1.0] + [float((y[:-k] * y[k:]).sum() / n / g0)
                             for k in range(1, kmax + 1)]), n


def lam_flattop(u):
    a = np.abs(u)
    return np.where(a <= 0.5, 1.0, np.where(a <= 1.0, 2.0 * (1.0 - a), 0.0))


def politis_white(x):
    """b_opt circular-block cho trung binh (Politis-White 2004, cua so flat-top)."""
    y = x[~np.isnan(x)]
    y = y - y.mean()
    n = len(y)
    kmax = min(n - 2, int(np.ceil(2 * np.sqrt(n))) + 20)
    rho, _ = acf(y, kmax)
    thr = 2.0 * np.sqrt(np.log10(n) / n)
    KN = max(5, int(np.sqrt(np.log10(n))))
    mhat = 1
    for k in range(1, kmax - KN):
        if np.all(np.abs(rho[k:k + KN]) < thr):
            mhat = k
            break
    else:
        mhat = kmax // 2
    Mv = min(2 * mhat, kmax)
    g0 = (y * y).sum() / n
    gam = np.array([g0] + [float((y[:-k] * y[k:]).sum() / n) for k in range(1, Mv + 1)])
    ks = np.arange(-Mv, Mv + 1)
    lam = lam_flattop(ks / max(Mv, 1))
    gk = gam[np.abs(ks)]
    Ghat = float((lam * np.abs(ks) * gk).sum())
    g0hat = float((lam * gk).sum())
    D_cb = (4.0 / 3.0) * g0hat ** 2
    if D_cb <= 0 or Ghat <= 0:
        return float("nan"), mhat, Mv
    b = (2.0 * Ghat ** 2 / D_cb) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    return float(b), mhat, Mv


LG.info("\n=== 4. DO DAI PHU THUOC THAT (chuoi ngay cua hieu) ===")
dep = {}
for nm, (ts_a, v_a, _w) in list(SERIES.items()):
    x, c = daily_series(ts_a, v_a)
    rho, nn = acf(x, 30)
    b, mhat, Mv = politis_white(x)
    thr = 2.0 / np.sqrt(nn)
    span = 0
    for k in range(1, 31):
        if abs(rho[k]) >= thr:
            span = k
    dep[nm] = dict(n_day=int(nn), pw_b=b, mhat=int(mhat), M=int(Mv),
                   span_last_signif=int(span), thr=float(thr),
                   rho1_5=[round(float(r), 4) for r in rho[1:6]])
    LG.info("%-18s n_day=%d PW b_opt=%.2f ngay (mhat=%d, M=%d) | span lag cuoi con y nghia=%d"
            " (nguong %.4f) | rho1..5=%s", nm, nn, b, mhat, Mv, span, thr,
            [round(float(r), 4) for r in rho[1:6]])
    # variance ratio
    vr = {}
    xv = x[~np.isnan(x)]
    v1 = xv.var(ddof=1)
    for Ld in GRID_D:
        nfull = len(xv) // Ld
        if nfull < 5:
            continue
        blk = xv[:nfull * Ld].reshape(nfull, Ld).sum(axis=1)
        vr[Ld] = float(blk.var(ddof=1) / (Ld * v1))
    dep[nm]["VR"] = {k: round(v, 4) for k, v in vr.items()}
    LG.info("%-18s VR(L)=%s   (VR>1 = phu thuoc DUONG, VR<1 = AM)", nm, dep[nm]["VR"])
OUT["dependence"] = dep

# ============================================================ 5. GENERATOR + KIEM PHU
def calib(ts_a, v_a):
    """Tach phuong sai thanh tang NGAY (latent) va tang TICK (noise)."""
    x, c = daily_series(ts_a, v_a)
    ok = ~np.isnan(x)
    var_unit = float(np.var(v_a, ddof=1))
    var_day = float(np.var(x[ok], ddof=1))
    inv_n = float(np.mean(1.0 / c[ok]))
    var_lat = (var_day - var_unit * inv_n) / max(1.0 - inv_n, 1e-9)
    var_lat = max(var_lat, 0.0)
    var_noise = max(var_unit - var_lat, 1e-12)
    return var_lat, var_noise, int((~np.isnan(x)).size)


def ar_fit(x, pmax=10):
    y = x[~np.isnan(x)]
    y = y - y.mean()
    n = len(y)
    best = (np.inf, np.array([]))
    g = np.array([float((y[:n - k] * y[k:]).sum() / n) for k in range(pmax + 1)])
    for p in range(1, pmax + 1):
        Rm = np.array([[g[abs(i - j)] for j in range(p)] for i in range(p)])
        try:
            phi = np.linalg.solve(Rm, g[1:p + 1])
        except np.linalg.LinAlgError:
            continue
        s2 = g[0] - float(phi @ g[1:p + 1])
        if s2 <= 0:
            continue
        aic = n * np.log(s2) + 2 * p
        if aic < best[0] and np.all(np.abs(np.roots(np.r_[1, -phi])) < 1.0):
            best = (aic, phi)
    return best[1]


def sim_ar(phi, nd, rng, burn=200):
    p = len(phi)
    if p == 0:
        return rng.standard_normal(nd)
    z = np.zeros(nd + burn)
    e = rng.standard_normal(nd + burn)
    for t in range(p, nd + burn):
        z[t] = float(phi @ z[t - p:t][::-1]) + e[t]
    z = z[burn:]
    s = z.std(ddof=1)
    return z / (s if s > 0 else 1.0)


def sim_ma(nd, span, rng):
    e = rng.standard_normal(nd + span)
    w = np.ones(span) / np.sqrt(span)
    z = np.convolve(e, w, mode="valid")[:nd]
    s = z.std(ddof=1)
    return z / (s if s > 0 else 1.0)


def coverage(ts_a, kind, var_lat, var_noise, phi, span, mu, Lgrid, n_mc, n_boot, rng):
    dd = ((np.asarray(ts_a, dtype=np.int64) - TS_MIN) // DAY).astype(int)
    nd = dd.max() + 1
    nunit = len(ts_a)
    pre = {}
    for Ld in Lgrid:
        bh = Ld * 24
        nb = nblocks(bh)
        bid = ((np.asarray(ts_a, dtype=np.int64) - TS_MIN) // (bh * H)).astype(np.int64)
        cnt = np.bincount(bid, minlength=nb)[:nb].astype(float)
        pre[Ld] = (bid, cnt, nb)
    hit = {Ld: 0 for Ld in Lgrid}
    sdm = {Ld: [] for Ld in Lgrid}
    sl = np.sqrt(var_lat)
    sn = np.sqrt(var_noise)
    for _ in range(n_mc):
        if kind == "iid":
            lat = np.zeros(nd)
        elif kind == "ma":
            lat = sim_ma(nd, span, rng) * sl
        else:
            lat = sim_ar(phi, nd, rng) * sl
        v = mu + lat[dd] + rng.standard_normal(nunit) * sn
        for Ld in Lgrid:
            bid, cnt, nb = pre[Ld]
            s = np.bincount(bid, weights=v, minlength=nb)[:nb]
            draw = rng.integers(0, nb, size=(n_boot, nb))
            st = s[draw].sum(axis=1) / np.maximum(cnt[draw].sum(axis=1), 1e-12)
            lo, hi = np.percentile(st, [2.5, 97.5])
            if lo <= mu <= hi:
                hit[Ld] += 1
            sdm[Ld].append(st.std(ddof=1))
    return ({Ld: hit[Ld] / n_mc for Ld in Lgrid},
            {Ld: float(np.mean(sdm[Ld])) for Ld in Lgrid})


MU = 0.02
mc_err = np.sqrt(0.95 * 0.05 / N_MC)
LG.info("\n=== 5. CONG KIEM PHU (N_MC=%d, N_BOOT=%d, mu=%.3f, dai nhan %s, sai so MC %.4f) ===",
        N_MC, N_BOOT, MU, ACCEPT, mc_err)

# hieu chuan tren chuoi B2 (chuoi quyet dinh: doi chung cong suat cua S1CUT)
ts_ref, v_ref, _ = SERIES["B2_full9_worse2"]
vl, vn, _ = calib(ts_ref, v_ref)
x_ref, _ = daily_series(ts_ref, v_ref)
phi_ref = ar_fit(x_ref)
LG.info("hieu chuan H4 tren B2: var_latent(ngay)=%.6g var_noise(tick)=%.6g AR(p=%d) phi=%s",
        vl, vn, len(phi_ref), np.round(phi_ref, 4).tolist())
OUT["calib_B2"] = dict(var_lat=vl, var_noise=vn, phi=[float(p) for p in phi_ref])

cov_res = {}
for tag, kind, span in [("H0_iid", "iid", 0), ("H3_span3", "ma", 3), ("H4_real", "ar", 0)]:
    rng = np.random.default_rng(SEED)
    vl_u, vn_u = (0.0, vn + vl) if kind == "iid" else (vl, vn)
    cov, sdm = coverage(ts_ref, kind, vl_u, vn_u, phi_ref, span, MU,
                        GRID_D, N_MC, N_BOOT, rng)
    cov_res[tag] = cov
    LG.info("%-10s %s", tag, {k: round(v, 3) for k, v in cov.items()})
    for Ld in GRID_D:
        flag = "DUOI PHU" if cov[Ld] < ACCEPT[0] else ("BAO THU" if cov[Ld] > ACCEPT[1] else "PASS")
        LG.info("   L=%2dd nblk=%3d do_phu=%.3f %-9s sd_tb=%.5f", Ld, nblocks(Ld * 24),
                cov[Ld], flag, sdm[Ld])
OUT["coverage"] = {k: {str(a): b for a, b in v.items()} for k, v in cov_res.items()}

with open("/home/ubuntu/cov/cov_meta.json", "w") as f:
    json.dump(OUT, f, indent=1, default=float)
LG.info("\nDONE")
