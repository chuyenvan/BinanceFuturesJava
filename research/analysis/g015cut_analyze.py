"""G015CUT — cham diem + CI cho MOI bien the, tren Oracle. Theo dung docs/PREREG_G015CUT.md.
Doc pred_<v>.npy (thu tu POOL) tu cac thu muc output kernel + pool_dev.parquet. Chi DOC.
"""
import os, sys, glob, json, time, logging
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ana")
DIRS = sys.argv[1:] or ["/home/ubuntu/g015/out_g015-cut-a", "/home/ubuntu/g015/out_g015-cut-b"]
POOL = "/home/ubuntu/g015/pool/pool_dev.parquet"
OUTD = "/home/ubuntu/g015"
NREP = 2000
BSEED = 20260903
NCRUDE = int(os.environ.get("NCRUDE", "60"))
K_MULT = float(np.sqrt(2.0 * np.log(9.0)))
GMM, GAMIN, GAMULT, GRMAX = 0.008, 0.26787, 1.2876, 0.15
BLS = ("72h", "24h", "168h")
ORDER = ["full45", "no_oi", "noise46_a", "noise46_b", "no_funding", "no_basket",
         "no_xsec", "no_oi_no_xsec", "oi_only", "p_old"]
NFEAT = {"full45": 45, "no_oi": 40, "noise46_a": 46, "noise46_b": 46, "no_funding": 36,
         "no_basket": 40, "no_xsec": 42, "no_oi_no_xsec": 37, "oi_only": 5, "p_old": 45}


def dyn_thr(score, c=1.0):
    return c * GMM * np.maximum(GAMIN, score / GRMAX * GAMULT)


def match_c(score, p15, n0):
    lo, hi = 0.05, 20.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        n = int((p15 >= dyn_thr(score, mid)).sum())
        if abs(n - n0) <= max(1, int(0.005 * n0)):
            return mid, n
        if n > n0:
            lo = mid
        else:
            hi = mid
    mid = 0.5 * (lo + hi)
    return mid, int((p15 >= dyn_thr(score, mid)).sum())


def mono20(p, y):
    b = pd.qcut(pd.Series(p), 20, labels=False, duplicates="drop")
    m = pd.DataFrame({"b": b, "y": y}).groupby("b").y.mean()
    d = m.diff().dropna()
    return float((d > 0).mean()), int(len(d) + 1)


def bstats(u, v, bid, nb):
    return np.stack([np.bincount(bid, minlength=nb).astype(np.float64),
                     np.bincount(bid, weights=u, minlength=nb),
                     np.bincount(bid, weights=v, minlength=nb),
                     np.bincount(bid, weights=u * u, minlength=nb),
                     np.bincount(bid, weights=v * v, minlength=nb),
                     np.bincount(bid, weights=u * v, minlength=nb)], axis=1)


def r_from(S):
    n, Sx, Sy, Sxx, Syy, Sxy = [S[..., i] for i in range(6)]
    with np.errstate(invalid="ignore", divide="ignore"):
        return (Sxy - Sx * Sy / n) / np.sqrt((Sxx - Sx * Sx / n) * (Syy - Sy * Sy / n))


pool = pd.read_parquet(POOL)
assert len(pool) == 15442092, len(pool)
ts = pool.ts.to_numpy(np.int64)
p15 = pool.p15.to_numpy(np.float64)
y = pool.g1lite.to_numpy(np.float64)
yr = pd.to_datetime(ts, unit="ms").year.to_numpy()
log.info("pool %d dong | ts[%s..%s]", len(pool), pd.to_datetime(ts.min(), unit="ms"),
         pd.to_datetime(ts.max(), unit="ms"))

P = {"p_old": pool.p_old.to_numpy(np.float64)}
for d in DIRS:
    for f in sorted(glob.glob(d + "/pred_*.npy")):
        v = os.path.basename(f)[5:-4]
        if v == "p_old" or v in P:
            continue
        a = np.load(f)
        assert len(a) == len(pool), (v, len(a))
        P[v] = a.astype(np.float64)
        log.info("nap %-14s tu %s", v, d)
V = [v for v in ORDER if v in P]
log.info("bien the co du lieu (%d): %s", len(V), V)
assert "full45" in V, "thieu full45 -> khong cham duoc"

ry = rankdata(y)
ry = (ry - ry.mean()) / len(ry)
t0 = ts.min()
bids = dict((k, ((ts - t0) // (int(k[:-1]) * 3_600_000)).astype(np.int64)) for k in BLS)
nbs = dict((k, int(b.max()) + 1) for k, b in bids.items())
log.info("so khoi: %s", nbs)

pt = {}
S = {}
A = {}
n0 = None
for v in V:
    p = P[v]
    rho = float(spearmanr(p, y).correlation)
    mo, nb20 = mono20(p, y)
    pyr = {}
    for u in sorted(set(yr.tolist())):
        m = yr == u
        pyr[str(u)] = float(spearmanr(p[m], y[m]).correlation)
    sc = 1.0 - p
    adm = p15 >= dyn_thr(sc)
    na = int(adm.sum())
    if v == "full45":
        n0 = na
    cm, nm = match_c(sc, p15, n0)
    admm = p15 >= dyn_thr(sc, cm)
    pt[v] = {"variant": v, "n_feat": NFEAT.get(v, -1), "rho": rho, "mono20": mo, "nb20": nb20,
             "rho_year": pyr, "n_admit": na, "admit_rate": na / len(p),
             "q_admit": float(y[adm].mean()), "match_c": cm, "n_admit_matched": nm,
             "q_admit_matched": float(y[admm].mean()), "p_mean": float(p.mean()),
             "p_std": float(p.std())}
    log.info("%-14s rho=%.5f mono=%.2f yr=%s n_adm=%6d rate=%.5f q=%.5f qm=%.5f c=%.3f",
             v, rho, mo, dict((k, round(x, 4)) for k, x in pyr.items()), na, na / len(p),
             pt[v]["q_admit"], pt[v]["q_admit_matched"], cm)
    rp = rankdata(p)
    rp = (rp - rp.mean()) / len(rp)
    S[v] = dict((k, bstats(rp, ry, bids[k], nbs[k])) for k in BLS)
    A[v] = dict((k, np.stack([
        np.bincount(bids[k][adm], minlength=nbs[k]).astype(np.float64),
        np.bincount(bids[k][adm], weights=y[adm], minlength=nbs[k]),
        np.bincount(bids[k][admm], minlength=nbs[k]).astype(np.float64),
        np.bincount(bids[k][admm], weights=y[admm], minlength=nbs[k])], axis=1)) for k in BLS)
    del rp


BOOT = {"k_mult": K_MULT, "n_rep": NREP, "seed": BSEED, "M": 9}
picks72 = None
for bl in BLS:
    alive = np.flatnonzero(S["full45"][bl][:, 0] > 0)
    rng = np.random.default_rng(BSEED)
    picks = rng.integers(0, len(alive), size=(NREP, len(alive)))
    cnt = np.zeros((NREP, len(alive)), dtype=np.float64)
    for i in range(NREP):
        cnt[i] = np.bincount(picks[i], minlength=len(alive))
    if bl == "72h":
        picks72 = (alive, picks)
    rr, qq, qm = {}, {}, {}
    for v in V:
        rr[v] = r_from(cnt @ S[v][bl][alive])
        tot = cnt @ A[v][bl][alive]
        with np.errstate(invalid="ignore", divide="ignore"):
            qq[v] = tot[:, 1] / tot[:, 0]
            qm[v] = tot[:, 3] / tot[:, 2]
    obs = {}
    for v in V:
        Sv = S[v][bl].sum(axis=0)
        Av = A[v][bl].sum(axis=0)
        obs[(v, "rho")] = float(r_from(Sv))
        obs[(v, "q_admit")] = float(Av[1] / Av[0])
        obs[(v, "q_admit_matched")] = float(Av[3] / Av[2])
    for v in V:
        for tag, arr in (("rho", rr), ("q_admit", qq), ("q_admit_matched", qm)):
            d = arr[v] - arr["full45"]
            sd = float(np.nanstd(d, ddof=1))
            do = obs[(v, tag)] - obs[("full45", tag)]
            lo, hi = np.nanpercentile(d, [2.5, 97.5])
            BOOT["%s|%s|%s" % (v, tag, bl)] = {
                "point_obs": obs[(v, tag)], "d_obs": do, "sd": sd,
                "ci_lo": float(lo), "ci_hi": float(hi),
                "wide_lo": do - K_MULT * sd, "wide_hi": do + K_MULT * sd,
                "p_d_gt0": float(np.nanmean(d > 0)), "n_block": int(len(alive))}
    log.info("boot %s n_block=%d sd(d rho)=%s", bl, len(alive),
             dict((v, round(BOOT["%s|rho|%s" % (v, bl)]["sd"], 5)) for v in V))

if NCRUDE > 0 and "no_oi" in V:
    alive, picks = picks72
    bid = bids["72h"]
    o = np.argsort(bid, kind="stable")
    bs = bid[o]
    st = np.searchsorted(bs, np.arange(int(bid.max()) + 2))
    rows = [o[st[b]:st[b + 1]] for b in alive]
    ds = []
    tc = time.time()
    for i in range(NCRUDE):
        idx = np.concatenate([rows[j] for j in picks[i]])
        yy = rankdata(y[idx])
        a = float(np.corrcoef(rankdata(P["full45"][idx]), yy)[0, 1])
        b = float(np.corrcoef(rankdata(P["no_oi"][idx]), yy)[0, 1])
        ds.append(b - a)
        del idx, yy
    ds = np.array(ds)
    BOOT["crude"] = {"n_rep": NCRUDE, "sd_crude": float(ds.std(ddof=1)),
                     "d_mean_crude": float(ds.mean()), "sec": round(time.time() - tc, 1)}
    log.info("crude %d rep %.0fs: sd=%.6f mean=%+.6f (xap xi sd=%.6f d_obs=%+.6f)",
             NCRUDE, time.time() - tc, ds.std(ddof=1), ds.mean(),
             BOOT["no_oi|rho|72h"]["sd"], BOOT["no_oi|rho|72h"]["d_obs"])

json.dump({"point": pt, "boot": BOOT}, open(OUTD + "/g015cut_final.json", "w"), indent=1)
log.info("ghi %s/g015cut_final.json", OUTD)
