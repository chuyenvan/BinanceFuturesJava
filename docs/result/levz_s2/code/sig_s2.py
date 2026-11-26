"""LEVZ S2 signal states P5, P5b, P6a, P6b (PREREG_LEVZ_S2 sec 2), W = 7. Functions copied VERBATIM (logic) from
levz_rev/sigcount/code/{count_sig.py: fund_parts, roll, top_mask ; ext_s2.py: pct_rank, daily_thr} so nothing is written to sigcount.
Causal convention = tier-1: X[t] ln OI ts in (t-70m, t-10m]; f[t] latest settlement ts <= t-1m; rolling stats on rows < t."""
import sys
import numpy as np
import pandas as pd
sys.dont_write_bytecode = True
import common_s2 as CM
sys.path.insert(0, CM.LEVZ_CODE)
import common as C   # frozen tier-1
import levz as L     # frozen tier-1
sys.path.pop(0)

H = L.H
W = 7
H90, MP90 = 2160, 720
EPS, EPS_F = 1e-9, 1e-12
P_TOP = 2
MIN_RANKED = 40
Q6 = {'P6a': 0.999, 'P6b': 0.998}


def fund_parts(fs, tms, Wh):
    """exact-integer funding mean / sd (sigcount count_sig.fund_parts). returns f, f - mean_f, sd_f (NaN where not ok)."""
    ts, r8, ih = fs['ts'], fs['r8'], fs['ih']
    k8 = (np.rint(fs['rate'] * 1e8).astype(np.int64) * 8) // ih.astype(np.int64)
    j = np.searchsorted(ts, tms - C.M_MS, side='right') - 1
    valid = j >= 0
    jj = np.clip(j, 0, None)
    fresh = valid & ((tms - ts[jj]) <= ih[jj] * H + C.M_MS)
    lo = np.searchsorted(ts, tms - Wh * H, side='left')
    lo = np.minimum(lo, jj)
    ni = (jj - lo).astype(np.int64)
    n = ni.astype(np.float64)
    S1 = np.concatenate([[0], np.cumsum(k8)])
    S2 = np.concatenate([[0], np.cumsum(k8 * k8)])
    s1 = S1[jj] - S1[lo]
    s2 = S2[jj] - S2[lo]
    safe = (ni >= 2) & (np.abs(s1) < 3000000000) & (s2 < 9000000000000000000 // np.maximum(ni, 1))
    numi = np.where(safe, ni * np.where(safe, s2, 0) - np.where(safe, s1, 0) ** 2, 0)
    with np.errstate(divide='ignore', invalid='ignore'):
        varf = (s2.astype(np.float64) - s1.astype(np.float64) ** 2 / n) / (n - 1)
        var = np.where(safe, numi.astype(np.float64) / (n * (n - 1)), varf) / 1e16
        numf = (k8[jj] * ni - s1).astype(np.float64) / (n * 1e8)
    sd = np.sqrt(np.maximum(var, 0.0))
    ok = fresh & (ni >= 2) & (n >= 0.8 * (Wh / ih[jj]))
    f = np.where(fresh, r8[jj], np.nan)
    return f, np.where(ok, numf, np.nan), np.where(ok, sd, np.nan)


def roll(A, w, mp, q=None):
    r = pd.DataFrame(A).rolling(w, min_periods=mp)
    v = r.median() if q is None else r.quantile(q, interpolation='linear')
    return v.shift(1).values


def top_mask(Z, elig, p):
    A = np.where(elig, Z, -np.inf)
    n = elig.sum(1)
    k = np.ceil(n * p / 100.0).astype(np.int64)
    srt = -np.sort(-A, axis=1)
    thr = srt[np.arange(A.shape[0]), np.clip(k - 1, 0, None)]
    thr = np.where(k > 0, thr, np.inf)
    return elig & (A >= thr[:, None])


def pct_rank(Z, elig):
    A = np.where(elig, Z, np.nan)
    return pd.DataFrame(A).rank(axis=1, pct=True, method='average').values


def daily_thr(Sv, U, qs):
    NH = Sv.shape[0]
    vals = [Sv[r][U[r] & np.isfinite(Sv[r])] for r in range(NH)]
    nd = -(-NH // 24)
    thr = np.full((nd, len(qs)), np.nan)
    for d in range(nd):
        d0 = 24 * d
        if d0 < 720:
            continue
        v = np.concatenate(vals[max(0, d0 - 2160):d0])
        if len(v):
            thr[d] = np.quantile(v, qs)
    return np.repeat(thr, 24, axis=0)[:NH]


def states(X, U, Fd, tms):
    """returns {name: (S bool [NH x ns], score float [NH x ns])} for P5, P5b, P6a, P6b; plus 'n_ranked' per hour."""
    NH, ns = X.shape
    Wh = W * 24
    F_ = np.full((NH, ns), np.nan)
    NF = np.full((NH, ns), np.nan)
    SDF = np.full((NH, ns), np.nan)
    for c, fs in Fd.items():
        F_[:, c], NF[:, c], SDF[:, c] = fund_parts(fs, tms, Wh)
    m, sd = L.roll_z_inputs(X, Wh)
    num = X - m
    del m
    out = {}
    with np.errstate(invalid='ignore', divide='ignore'):
        zoi0 = num / np.maximum(sd, L.SD_OI_FLOOR)
        zf0 = NF / np.maximum(SDF, L.SD_F_FLOOR)
        fin0 = U & np.isfinite(zoi0) & np.isfinite(zf0)
        sv = np.where(fin0, np.fmin(zoi0, zf0), np.nan)
        del zoi0, zf0
        names = list(Q6)
        thr = daily_thr(sv, U, [Q6[k] for k in names])
        for i, k in enumerate(names):
            out[k] = (fin0 & (sv >= thr[:, i][:, None]) & (sv > 0), sv)
        sdc = np.where(sd < EPS, 0.0, sd)
        den = np.maximum(sdc, roll(sdc, H90, MP90))
        den[~(den > EPS)] = np.nan
        zoi2 = num / den
        sdc = np.where(SDF < EPS_F, 0.0, SDF)
        den = np.maximum(sdc, roll(sdc, H90, MP90))
        den[~(den > EPS_F)] = np.nan
        zf2 = NF / den
        del sdc, den, sd, SDF, NF, num
        fin2 = U & np.isfinite(zoi2) & np.isfinite(zf2)
        nr = fin2.sum(1)
        okh = (nr >= MIN_RANKED)[:, None]
        medf = np.nanmedian(np.where(U, F_, np.nan), axis=1)
        eligb = fin2 & (F_ >= medf[:, None])
        pos = (zoi2 > 0) & (zf2 > 0)
        S5 = CS_top(zoi2, zf2, fin2) & pos & okh
        out['P5'] = (S5, np.fmin(pct_rank(zoi2, fin2), pct_rank(zf2, fin2)))
        S5b = CS_top(zoi2, zf2, eligb) & pos & okh
        out['P5b'] = (S5b, np.fmin(pct_rank(zoi2, eligb), pct_rank(zf2, eligb)))
    out['n_ranked'] = nr
    return out


def CS_top(zo, zf, elig):
    return top_mask(zo, elig, P_TOP) & top_mask(zf, elig, P_TOP)


def load_data():
    D = L.Data('2025-12')
    assert int(D.tms[-1]) < C.CUTOFF_MS
    for a in ('P0', 'CL', 'CM', 'LAST'):
        delattr(D, a)   # prices from hr_ files never used here
    return D
