"""COV addendum — kiem phu RIENG cho B7/B8 (chuoi gate-MO, thua: ~325 tick / 48 ngay).
Ly do: H4 o cov_run.py hieu chuan tren B2 (day, phu thuoc DUONG) nen KHONG mo ta B7/B8
(phu thuoc AM, VR<1). PREREG_COV section 1 doi kiem ca B7/B8 => phai hieu chuan rieng.
"""
import json
import logging

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/cov/COV2.out", "w"),
                              logging.StreamHandler()])
LG = logging.getLogger("cov2")

H = 3600_000
DAY = 24 * H
SEED = 20260904
N_MC, N_BOOT, NREP_CI = 1000, 1000, 2000
GRID_D = [1, 3, 5, 7, 9, 14, 21]
ACCEPT = (0.92, 0.97)

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "gate_dyn_ok", "score_g015"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
R = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                    columns=["ts", "sym", "g1_replay"])
M = C.merge(P, on=["ts", "sym"], how="inner").merge(R, on=["ts", "sym"], how="left")
M["gate_ok"] = M.gate_dyn_ok.astype(bool)
M = M.dropna(subset=["g1_replay"])
TS_MIN, TS_MAX = int(M.ts.min()), int(M.ts.max())
OPEN = M[M.gate_ok]

# ---- B7: per-tick IC difference
rows = []
for ts, g in OPEN.groupby("ts"):
    if len(g) < 10:
        continue
    a = spearmanr(-g.score.values, g.g1_replay.values).correlation
    b = spearmanr(-g.score_g015.values, g.g1_replay.values).correlation
    if not (np.isnan(a) or np.isnan(b)):
        rows.append((ts, a - b))
B7 = pd.DataFrame(rows, columns=["ts", "d"]).sort_values("ts").reset_index(drop=True)

# ---- B8: per-tick (mean top8 - mean random8)
d = OPEN.copy()
d["rk"] = d.groupby("ts").score.rank(ascending=True, method="first")
T8 = d[d.rk <= 8]
R8 = OPEN.sample(frac=1.0, random_state=0).groupby("ts").head(8)
g1 = T8.groupby("ts").g1_replay.mean()
g2 = R8.groupby("ts").g1_replay.mean()
B8 = pd.concat([g1.rename("a"), g2.rename("b")], axis=1).dropna()
B8 = pd.DataFrame({"ts": B8.index.values, "d": (B8.a - B8.b).values})
LG.info("B7: %d tick | B8: %d tick", len(B7), len(B8))


def nblocks(bh):
    return int((TS_MAX - TS_MIN) // (bh * H)) + 1


def daily_series(ts_a, v_a):
    dd = ((np.asarray(ts_a, np.int64) - TS_MIN) // DAY).astype(int)
    nd = dd.max() + 1
    s = np.bincount(dd, weights=v_a.astype(float), minlength=nd)
    c = np.bincount(dd, minlength=nd).astype(float)
    return np.where(c > 0, s / np.maximum(c, 1e-12), np.nan), c


def acf(x, kmax):
    y = x[~np.isnan(x)]
    y = y - y.mean()
    n = len(y)
    g0 = (y * y).sum() / n
    kmax = min(kmax, n - 2)
    return np.array([1.0] + [float((y[:-k] * y[k:]).sum() / n / g0)
                             for k in range(1, kmax + 1)]), n


def ar_fit(x, pmax=6):
    y = x[~np.isnan(x)]
    y = y - y.mean()
    n = len(y)
    g = np.array([float((y[:n - k] * y[k:]).sum() / n) for k in range(pmax + 1)])
    best = (np.inf, np.array([]))
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


def calib(ts_a, v_a):
    x, c = daily_series(ts_a, v_a)
    ok = ~np.isnan(x)
    vu = float(np.var(v_a, ddof=1))
    vd = float(np.var(x[ok], ddof=1))
    inv = float(np.mean(1.0 / c[ok]))
    vl = max((vd - vu * inv) / max(1.0 - inv, 1e-9), 0.0)
    return vl, max(vu - vl, 1e-12)


def coverage(ts_a, kind, vl, vn, phi, span, mu, rng):
    dd = ((np.asarray(ts_a, np.int64) - TS_MIN) // DAY).astype(int)
    nd = dd.max() + 1
    nu = len(ts_a)
    pre = {}
    for Ld in GRID_D:
        bh = Ld * 24
        nb = nblocks(bh)
        bid = ((np.asarray(ts_a, np.int64) - TS_MIN) // (bh * H)).astype(np.int64)
        cnt = np.bincount(bid, minlength=nb)[:nb].astype(float)
        pre[Ld] = (bid, cnt, nb, int((cnt > 0).sum()))
    hit = {L: 0 for L in GRID_D}
    sl, sn = np.sqrt(vl), np.sqrt(vn)
    for _ in range(N_MC):
        if kind == "iid":
            lat = np.zeros(nd)
        elif kind == "ma":
            e = rng.standard_normal(nd + span)
            w = np.ones(span) / np.sqrt(span)
            z = np.convolve(e, w, mode="valid")[:nd]
            lat = z / (z.std(ddof=1) or 1.0) * sl
        else:
            lat = sim_ar(phi, nd, rng) * sl
        v = mu + lat[dd] + rng.standard_normal(nu) * sn
        for Ld in GRID_D:
            bid, cnt, nb, _ = pre[Ld]
            s = np.bincount(bid, weights=v, minlength=nb)[:nb]
            dr = rng.integers(0, nb, size=(N_BOOT, nb))
            st = s[dr].sum(axis=1) / np.maximum(cnt[dr].sum(axis=1), 1e-12)
            lo, hi = np.percentile(st, [2.5, 97.5])
            if lo <= mu <= hi:
                hit[Ld] += 1
    return {L: hit[L] / N_MC for L in GRID_D}, {L: pre[L][3] for L in GRID_D}


MU = 0.02
OUT = {}
for nm, S in [("B7", B7), ("B8", B8)]:
    x, c = daily_series(S.ts.values, S.d.values)
    rho, nn = acf(x, min(20, len(x[~np.isnan(x)]) - 3))
    phi = ar_fit(x)
    vl, vn = calib(S.ts.values, S.d.values)
    xv = x[~np.isnan(x)]
    v1 = xv.var(ddof=1)
    vr = {}
    for Ld in GRID_D:
        nf = len(xv) // Ld
        if nf >= 5:
            vr[Ld] = round(float(xv[:nf * Ld].reshape(nf, Ld).sum(axis=1).var(ddof=1)
                                 / (Ld * v1)), 4)
    LG.info("\n--- %s: n_tick=%d n_day=%d var_lat=%.6g var_noise=%.6g AR(p=%d)=%s",
            nm, len(S), nn, vl, vn, len(phi), np.round(phi, 4).tolist())
    LG.info("%s rho1..5=%s VR=%s", nm, [round(float(r), 4) for r in rho[1:6]], vr)
    OUT[nm] = dict(n_tick=len(S), n_day=int(nn), var_lat=vl, var_noise=vn,
                   phi=[float(p) for p in phi], VR=vr,
                   rho=[round(float(r), 4) for r in rho[1:6]])
    for tag, kind, span in [("H0_iid", "iid", 0), ("H3_span3", "ma", 3), ("H4_real", "ar", 0)]:
        rng = np.random.default_rng(SEED)
        a, b = (0.0, vn + vl) if kind == "iid" else (vl, vn)
        cov, npop = coverage(S.ts.values, kind, a, b, phi, span, MU, rng)
        OUT[nm][tag] = {str(k): v for k, v in cov.items()}
        LG.info("%s %-9s %s", nm, tag,
                " ".join(f"L{L}d={cov[L]:.3f}{'*' if not (ACCEPT[0] <= cov[L] <= ACCEPT[1]) else ''}"
                         f"(pop{npop[L]})" for L in GRID_D))

with open("/home/ubuntu/cov/cov2_meta.json", "w") as f:
    json.dump(OUT, f, indent=1, default=float)
LG.info("\nDONE2  (* = ngoai dai nhan [0.92,0.97]; pop = so khoi CO du lieu)")
