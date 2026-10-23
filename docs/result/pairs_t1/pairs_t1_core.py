#!/usr/bin/env python3
"""PAIRS_T1 core - data, universe PIT, formation (M1 EG / M2 distance / M3 Kalman / M4 AL), accounting.

Pre-reg: docs/prereg/PREREG_PAIRS_T1.md (committed BEFORE any PnL). All parameters are fixed constants below.
Panel: ~/claude_master/pairs/data/panel_1h.npz (build_1h.py, Vision kline1m + vz-funding, DEV 2021-2025).
Time convention: bar h = [H0+h*1h, H0+(h+1)*1h). Signal at CLOSE of bar h -> fill at OPEN of bar h+1.
"""
import logging
import os

import numpy as np
from statsmodels.tsa.adfvalues import mackinnonp

log = logging.getLogger("pairs_t1")

PANEL = os.path.expanduser("~/claude_master/pairs/data/panel_1h.npz")
H0_MS = 1609459200000
H_START = 72                # 2021-01-04 00:00Z (2021-01-01..03 left out: edge of the sealed 2020s reservoir)
FORM = 720                  # 30 days formation
TRAD = 168                  # 7 days trading
W0 = H_START + FORM         # first trading window start = 2021-02-03 00:00Z
NUNIV = 50
NPAIR = 10
G_PAIR = 1.0 / NPAIR        # gross per pair slot (fraction of window equity); 10 slots = 1x gross
COV_MIN = 0.95              # >=95% hourly closes present in formation
RANGE_MIN = 0.01            # stable-like guard: 30d max/min - 1 < 1% => excluded
COSTS = {"base": 0.0005 + 0.0002, "x2": 2 * (0.0005 + 0.0002), "maker": 0.0002, "gross": 0.0}
EXCL = {"BTCDOMUSDT", "DEFIUSDT", "FOOTBALLUSDT", "BLUEBIRDUSDT",
        "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "EURUSDT", "USDEUSDT",
        "AEURUSDT", "BFUSDUSDT", "XUSDUSDT", "USD1USDT", "RLUSDUSDT", "PYUSDUSDT", "EURIUSDT", "USDSUSDT"}
# M1 (Engle-Granger 1987; selection/rules per brief; ADF autolag AIC = statsmodels coint default)
M1_P = 0.05
M1_HL = (6.0, 168.0)
M1_ENTRY, M1_EXIT, M1_STOP, M1_TSTOP = 2.0, 0.0, 4.0, 2.0
# M2 (Gatev, Goetzmann, Rouwenhorst 2006)
M2_ENTRY = 2.0
# M3 (Kalman hedge, Chan 2013 Ex.3.3: delta = 1e-4; Ve = formation OLS residual variance)
M3_DELTA = 1e-4
M3_ENTRY = 2.0
# M4 (Avellaneda & Lee 2010) - windows scaled from daily (252 corr / 60 est) to 1h (720 corr / 168 est)
M4_K = 3
M4_EST = 168
M4_TAU_MAX = M4_EST / 2.0   # mean-reversion time < half estimation window (AL: kappa > 252/30)
M4_SBO, M4_SSO, M4_SBC, M4_SSC = 1.25, 1.25, 0.50, 0.75   # open long s<-1.25, open short s>1.25, close long s>-0.5, close short s<0.75


class Panel:
    def __init__(self, path=PANEL, arrays=None):
        if arrays is None:
            z = np.load(path, allow_pickle=False)
            arrays = {k: z[k] for k in ("syms", "open", "close", "qv", "fund", "first", "last")}
        self.syms = arrays["syms"]
        self.O = arrays["open"]
        self.C = arrays["close"]
        self.Q = arrays["qv"]
        self.F = arrays["fund"]
        self.first = arrays["first"]
        self.last = arrays["last"]
        self.NH, self.S = self.C.shape
        self.CF = ffill2d(self.C)
        self.excl = np.array([s in EXCL for s in self.syms])
        self.NW = (self.NH - W0) // TRAD

    def copy_poisoned(self, h_from, seed=1):
        """V1: rows >= h_from replaced by garbage (prices x U(0.5,2), random qv, random funding)."""
        rng = np.random.default_rng(seed)
        a = {"syms": self.syms, "first": self.first, "last": self.last}
        for k, v in (("open", self.O), ("close", self.C), ("qv", self.Q), ("fund", self.F)):
            w = v.copy()
            n = self.NH - h_from
            if k in ("open", "close"):
                w[h_from:] = w[h_from:] * rng.uniform(0.5, 2.0, size=(n, self.S))
            elif k == "qv":
                w[h_from:] = rng.uniform(0, 1e12, size=(n, self.S))
            else:
                w[h_from:] = rng.normal(0, 0.01, size=(n, self.S))
            a[k] = w
        return Panel(arrays=a)


def ffill2d(A):
    A = A.copy()
    n = A.shape[0]
    idx = np.where(np.isfinite(A), np.arange(n)[:, None], 0)
    np.maximum.accumulate(idx, axis=0, out=idx)
    out = A[idx, np.arange(A.shape[1])[None, :]]
    return out


def window_start(k):
    return W0 + k * TRAD


def universe(P, t):
    """PIT top-NUNIV by quote volume over [t-FORM, t); uses only bars < t."""
    sl = slice(t - FORM, t)
    cw = P.C[sl]
    cov = np.isfinite(cw).mean(0)
    ok = (cov >= COV_MIN) & np.isfinite(P.C[t - 1]) & ~P.excl
    with np.errstate(all="ignore"):
        rng = np.nanmax(cw, 0) / np.nanmin(cw, 0) - 1.0
    ok &= np.nan_to_num(rng, nan=0.0) >= RANGE_MIN
    qv = np.nansum(P.Q[sl], 0)
    qv = np.where(ok, qv, -1.0)
    idx = np.argsort(-qv, kind="stable")[:NUNIV]
    idx = idx[qv[idx] > 0]
    return np.sort(idx)


def form_logprices(P, t, U):
    cw = P.C[t - FORM:t, U]
    f = ffill2d(cw)
    # leading NaN -> first valid (bfill)
    for j in range(f.shape[1]):
        col = f[:, j]
        if not np.isfinite(col[0]):
            fv = np.argmax(np.isfinite(col))
            col[:fv] = col[fv]
    return np.log(f)


# ------------------------------------------------------------------ M1: Engle-Granger
def adf_n_aic(e):
    """Replicates statsmodels adfuller(e, regression='n', autolag='aic', maxlag=None) -> adf t-stat."""
    n = len(e)
    maxlag = int(np.ceil(12.0 * np.power(n / 100.0, 0.25)))
    maxlag = min(n // 2 - 1, maxlag)
    xd = np.diff(e)
    nd = len(xd)
    nobs = nd - maxlag
    X = np.empty((nobs, maxlag + 1))
    for L in range(maxlag + 1):
        X[:, L] = xd[maxlag - L:nd - L]
    X[:, 0] = e[-nobs - 1:-1]
    y = xd[-nobs:]
    Qm, _ = np.linalg.qr(X)
    qy = Qm.T @ y
    rss = (y @ y) - np.cumsum(qy ** 2)
    rss = np.maximum(rss, 1e-300)
    kk = np.arange(1, maxlag + 2)
    aic = nobs * np.log(2 * np.pi) + nobs * np.log(rss / nobs) + nobs + 2 * kk
    bl = int(np.argmin(aic))
    nobs2 = nd - bl
    X2 = np.empty((nobs2, bl + 1))
    for L in range(bl + 1):
        X2[:, L] = xd[bl - L:nd - L]
    X2[:, 0] = e[-nobs2 - 1:-1]
    y2 = xd[-nobs2:]
    XtX = X2.T @ X2
    coef = np.linalg.solve(XtX, X2.T @ y2)
    r = y2 - X2 @ coef
    s2 = (r @ r) / (nobs2 - X2.shape[1])
    se0 = np.sqrt(s2 * np.linalg.inv(XtX)[0, 0])
    return coef[0] / se0


def ols_yx(y, x):
    xm, ym = x.mean(), y.mean()
    vx = ((x - xm) ** 2).sum()
    b = ((x - xm) * (y - ym)).sum() / vx
    a = ym - b * xm
    return b, a, y - b * x - a


def half_life(e):
    de = np.diff(e)
    el = e[:-1]
    elm = el.mean()
    lam = ((el - elm) * (de - de.mean())).sum() / ((el - elm) ** 2).sum()
    return -np.log(2.0) / lam if lam < 0 else np.inf


def eg_test(y, x):
    b, a, e = ols_yx(y, x)
    r2 = 1.0 - (e @ e) / (((y - y.mean()) ** 2).sum())
    stat = adf_n_aic(e) if r2 < 1 - 100 * np.sqrt(np.finfo(float).eps) else -np.inf
    return stat, b, a, e


def form_m1(P, t, U):
    """Return (selected top-NPAIR pairs, n_tested, n_pass). Pair dict uses GLOBAL symbol idx."""
    lp = form_logprices(P, t, U)
    N = len(U)
    cand = []
    ntest = 0
    corr = np.corrcoef(lp.T)
    for i in range(N):
        for j in range(i + 1, N):
            if not corr[i, j] > 0:          # beta>0 required; sign(beta) == sign(corr) for both orderings
                continue
            ntest += 1
            best = None
            for (yi, xi) in ((i, j), (j, i)):
                stat, b, a, e = eg_test(lp[:, yi], lp[:, xi])
                if best is None or stat < best[0]:
                    best = (stat, yi, xi, b, a, e)
            stat, yi, xi, b, a, e = best
            if b <= 0:
                continue
            p = mackinnonp(stat, regression="c", N=2) if np.isfinite(stat) else 0.0
            if not p < M1_P:
                continue
            hl = half_life(e)
            if not (M1_HL[0] <= hl <= M1_HL[1]):
                continue
            cand.append(dict(y=int(U[yi]), x=int(U[xi]), beta=float(b), alpha=float(a), sigma=float(e.std(ddof=1)),
                             hl=float(hl), stat=float(stat), p=float(p), var=float(e.var(ddof=1))))
    cand.sort(key=lambda d: (d["stat"], d["y"], d["x"]))
    return cand[:NPAIR], ntest, len(cand)


def rand_pairs_m1(P, t, U, rng, n=NPAIR):
    """Control: random ordered pairs (beta>0 by OLS), HL clipped into M1_HL."""
    lp = form_logprices(P, t, U)
    N = len(U)
    out = []
    tries = 0
    while len(out) < n and tries < 5000:
        tries += 1
        i, j = rng.choice(N, 2, replace=False)
        b, a, e = ols_yx(lp[:, i], lp[:, j])
        if not b > 0:
            continue
        hl = float(np.clip(half_life(e), *M1_HL))
        out.append(dict(y=int(U[i]), x=int(U[j]), beta=float(b), alpha=float(a), sigma=float(e.std(ddof=1)),
                        hl=hl, stat=np.nan, p=np.nan, var=float(e.var(ddof=1))))
    return out


# ------------------------------------------------------------------ M2: distance (Gatev 2006)
def form_m2(P, t, U):
    cw = P.C[t - FORM:t, U]
    f = np.exp(form_logprices(P, t, U))
    nz = f / f[0]
    G = nz.T @ nz
    d = np.diag(G)
    ssd = d[:, None] + d[None, :] - 2 * G
    cv = np.cov(nz.T)
    vd = np.diag(cv)
    var = vd[:, None] + vd[None, :] - 2 * cv
    N = len(U)
    cand = []
    for i in range(N):
        for j in range(i + 1, N):
            if var[i, j] > 0:
                cand.append((float(ssd[i, j]), int(U[i]), int(U[j]), float(np.sqrt(var[i, j]))))
    cand.sort()
    del cw
    return [dict(i=c[1], j=c[2], ssd=c[0], sigma=c[3]) for c in cand[:NPAIR]]


def rand_pairs_m2(P, t, U, rng, n=NPAIR):
    f = np.exp(form_logprices(P, t, U))
    nz = f / f[0]
    out = []
    N = len(U)
    while len(out) < n:
        i, j = rng.choice(N, 2, replace=False)
        s = float(np.std(nz[:, i] - nz[:, j], ddof=1))
        if s > 0:
            out.append(dict(i=int(U[i]), j=int(U[j]), ssd=np.nan, sigma=s))
    return out


# ------------------------------------------------------------------ M3: Kalman (Chan 2013)
def kalman_z(ly, lx, ve, delta=M3_DELTA):
    """Returns z (forecast error / sqrt(Q)) and prior beta for each obs; NaN obs -> no update, z NaN."""
    n = len(ly)
    vw = delta / (1 - delta) * np.eye(2)
    th = np.zeros(2)
    Pm = np.zeros((2, 2))
    z = np.full(n, np.nan)
    bp = np.full(n, np.nan)
    for k in range(n):
        if not (np.isfinite(ly[k]) and np.isfinite(lx[k])):
            continue
        R = Pm + vw
        Fv = np.array([lx[k], 1.0])
        yhat = Fv @ th
        qv = Fv @ R @ Fv + ve
        e = ly[k] - yhat
        z[k] = e / np.sqrt(qv)
        bp[k] = th[0]
        K = R @ Fv / qv
        th = th + K * e
        Pm = R - np.outer(K, Fv) @ R
    return z, bp


# ------------------------------------------------------------------ pair trade simulators
def _ok_open(P, h, syms):
    return all(np.isfinite(P.O[h, s]) for s in syms)


def _dir(pos, flip_rng):
    return pos if flip_rng is None else pos * (1 if flip_rng.random() < 0.5 else -1)


def sim_m1(P, t, pairs, flip_rng=None):
    """EG rule: enter 2<=|z|<4 (z>=2 -> short spread), exit z crosses 0, stop |z|>=4, time-stop held>=2*HL.
    After stop/time-stop the pair is disabled for the rest of the window. Forced close at open of t+TRAD."""
    trades = []
    hs = np.arange(t, t + TRAD - 1)         # signal closes; last fill at open t+TRAD-1
    for pr in pairs:
        y, x, b, a, sg, hl = pr["y"], pr["x"], pr["beta"], pr["alpha"], pr["sigma"], pr["hl"]
        with np.errstate(all="ignore"):
            z = (np.log(P.C[hs, y]) - b * np.log(P.C[hs, x]) - a) / sg
        pos, dis, e, d = 0, False, None, 0
        for zi, h in zip(z, hs):
            if not np.isfinite(zi):
                continue
            if pos == 0:
                if dis:
                    continue
                if M1_ENTRY <= abs(zi) < M1_STOP and _ok_open(P, h + 1, (y, x)):
                    pos = -1 if zi > 0 else 1
                    e = h + 1
                    d = _dir(pos, flip_rng)
            else:
                why = None
                if (pos == -1 and zi <= M1_EXIT) or (pos == 1 and zi >= -M1_EXIT):
                    why = "mr"
                elif abs(zi) >= M1_STOP:
                    why = "stop"
                elif (h + 1 - e) >= M1_TSTOP * hl:
                    why = "time"
                if why:
                    trades.append(dict(e=e, x=h + 1, why=why, key=(y, x),
                                       legs=[(y, d * G_PAIR / (1 + b)), (x, -d * G_PAIR * b / (1 + b))]))
                    pos = 0
                    if why != "mr":
                        dis = True
        if pos != 0:
            trades.append(dict(e=e, x=t + TRAD, why="end", key=(y, x),
                               legs=[(y, d * G_PAIR / (1 + b)), (x, -d * G_PAIR * b / (1 + b))]))
    return trades


def sim_m2(P, t, pairs, flip_rng=None):
    """Gatev: normalized at trading start (close t-1); open |d|>2 sigma_f; close at next crossing; re-entry allowed."""
    trades = []
    hs = np.arange(t, t + TRAD - 1)
    for pr in pairs:
        i, j, sg = pr["i"], pr["j"], pr["sigma"]
        bi, bj = P.CF[t - 1, i], P.CF[t - 1, j]
        dd = P.C[hs, i] / bi - P.C[hs, j] / bj
        pos, e, d = 0, None, 0
        for di, h in zip(dd, hs):
            if not np.isfinite(di):
                continue
            if pos == 0:
                if abs(di) > M2_ENTRY * sg and _ok_open(P, h + 1, (i, j)):
                    pos = -1 if di > 0 else 1
                    e = h + 1
                    d = _dir(pos, flip_rng)
            else:
                if (pos == -1 and di <= 0) or (pos == 1 and di >= 0):
                    trades.append(dict(e=e, x=h + 1, why="cross", key=(i, j),
                                       legs=[(i, d * G_PAIR / 2), (j, -d * G_PAIR / 2)]))
                    pos = 0
        if pos != 0:
            trades.append(dict(e=e, x=t + TRAD, why="end", key=(i, j),
                               legs=[(i, d * G_PAIR / 2), (j, -d * G_PAIR / 2)]))
    return trades


def sim_m3(P, t, pairs, flip_rng=None):
    """Kalman (Chan 2013): filter warm-up over formation (ffilled log prices), then trade on raw closes.
    Enter |z|>=2 with prior beta>0 (hedge fixed at entry), exit z crosses 0. No stop. Forced close at t+TRAD."""
    trades = []
    hs = np.arange(t, t + TRAD - 1)
    for pr in pairs:
        y, x = pr["y"], pr["x"]
        lpf = form_logprices(P, t, np.array([y, x]))
        with np.errstate(all="ignore"):
            ly = np.r_[lpf[:, 0], np.log(P.C[hs, y])]
            lx = np.r_[lpf[:, 1], np.log(P.C[hs, x])]
        z, bp = kalman_z(ly, lx, pr["var"])
        z, bp = z[FORM:], bp[FORM:]
        pos, e, d, bb = 0, None, 0, 0.0
        for zi, bi, h in zip(z, bp, hs):
            if not np.isfinite(zi):
                continue
            if pos == 0:
                if abs(zi) >= M3_ENTRY and bi > 0 and _ok_open(P, h + 1, (y, x)):
                    pos = -1 if zi > 0 else 1
                    e, bb = h + 1, bi
                    d = _dir(pos, flip_rng)
            else:
                if (pos == -1 and zi <= 0) or (pos == 1 and zi >= 0):
                    trades.append(dict(e=e, x=h + 1, why="mr", key=(y, x),
                                       legs=[(y, d * G_PAIR / (1 + bb)), (x, -d * G_PAIR * bb / (1 + bb))]))
                    pos = 0
        if pos != 0:
            trades.append(dict(e=e, x=t + TRAD, why="end", key=(y, x),
                               legs=[(y, d * G_PAIR / (1 + bb)), (x, -d * G_PAIR * bb / (1 + bb))]))
    return trades


# ------------------------------------------------------------------ accounting (pairs)
def exit_fill(P, s, x):
    col = P.O[x:min(x + TRAD + 1, P.NH), s]
    ok = np.isfinite(col)
    if ok.any():
        i = int(np.argmax(ok))
        return float(col[i]), x + i, ("gap" if i > 0 else "")
    return float(P.CF[x - 1, s]), x, "delist"


def mark(P, f, s):
    v = P.O[f, s]
    return v if np.isfinite(v) else P.CF[f - 1, s]


def account(P, t, trades):
    """Per-window cumulative paths (fraction of window-start equity) at tau_m = t+m, m=0..TRAD:
    gross (price PnL), turn (traded notional; cost = c*turn), fund (funding received, + = income).
    Adds per-leg ledger to each trade (V4)."""
    gross = np.zeros(TRAD + 1)
    turn = np.zeros(TRAD + 1)
    fund = np.zeros(TRAD + 1)
    mm = np.arange(TRAD + 1)
    for tr in trades:
        e, x = tr["e"], tr["x"]
        me, mx = e - t, min(x - t, TRAD)
        tr["ledger"] = []
        tg = tt = tf = 0.0
        for s, w in tr["legs"]:
            pe = float(P.O[e, s])
            px, xe, flag = exit_fill(P, s, x)
            qty = w / pe
            path = np.zeros(TRAD + 1)
            mid = (mm > me) & (mm < mx)
            path[mid] = qty * (P.CF[t + mm[mid] - 1, s] - pe)
            path[mm >= mx] = qty * (px - pe)
            gross += path
            turn[mm >= me] += abs(w)
            turn[mm >= mx] += abs(qty) * px
            fsum = 0.0
            for f in range(e + 1, xe + 1):      # funding charged if entry < f <= exit fill
                r = P.F[f, s]
                if r != 0.0:
                    pay = -qty * mark(P, f, s) * r
                    fsum += pay
                    fund[mm >= min(f - t, TRAD)] += pay
            g = qty * (px - pe)
            tr["ledger"].append(dict(sym=int(s), w=float(w), qty=float(qty), pe=pe, px=px, e=int(e), x=int(x), xe=int(xe),
                                     flag=flag, gross=g, turn=abs(w) + abs(qty) * px, fund=fsum))
            tg += g
            tt += abs(w) + abs(qty) * px
            tf += fsum
        tr.update(gross=tg, turn=tt, fund=tf)
    return gross, turn, fund


# ------------------------------------------------------------------ M4: Avellaneda-Lee residual stat-arb
def log_returns(P):
    with np.errstate(all="ignore"):
        L = np.log(P.CF)
    R = np.zeros_like(L)
    R[1:] = L[1:] - L[:-1]
    R[~np.isfinite(R)] = 0.0
    return R


def m4_pca(R, d, U):
    """Eigenportfolios from correlation of returns of bars [d-FORM, d) (AL 2010 sec.2.1)."""
    X = R[d - FORM:d][:, U]
    sd = X.std(0, ddof=1)
    sd = np.where(sd > 0, sd, np.inf)
    Z = (X - X.mean(0)) / sd
    Cm = (Z.T @ Z) / (len(Z) - 1)
    w, V = np.linalg.eigh(Cm)
    top = V[:, np.argsort(w)[::-1][:M4_K]]          # N x K
    Qd = (top / sd[:, None]).T                       # K x N dollar weights per unit factor
    return Qd, float(w[np.argsort(w)[::-1][:M4_K]].sum() / w.sum())


def m4_scores(R, h, U, Qd):
    """s-scores at close of bar h from returns of bars h-EST+1..h (AL 2010 sec.4, eq. for s with centered m)."""
    Rw = R[h - M4_EST + 1:h + 1][:, U]               # EST x N
    Fw = Rw @ Qd.T                                   # EST x K
    X = np.column_stack([np.ones(M4_EST), Fw])
    B, *_ = np.linalg.lstsq(X, Rw, rcond=None)       # (K+1) x N
    eps = Rw - X @ B
    Xc = np.cumsum(eps, 0)
    x0, x1 = Xc[:-1], Xc[1:]
    m0, m1 = x0.mean(0), x1.mean(0)
    vx = ((x0 - m0) ** 2).sum(0)
    b = np.where(vx > 0, ((x0 - m0) * (x1 - m1)).sum(0) / np.where(vx > 0, vx, 1), np.nan)
    a = m1 - b * m0
    zeta = x1 - a - b * x0
    vz = zeta.var(0)
    with np.errstate(all="ignore"):
        kappa = -np.log(b)
        valid = (b > 0) & (b < 1) & (kappa > 1.0 / M4_TAU_MAX)
        m = a / (1 - b)
        seq = np.sqrt(vz / (1 - b ** 2))
    s = np.full(len(U), np.nan)
    if valid.sum() >= 2:
        mbar = m - m[valid].mean()
        s[valid] = (Xc[-1, valid] - mbar[valid]) / seq[valid]
    return s, B[1:].T                                # s (N), beta (N x K)


def m4_signals(P, R=None):
    """Precompute for every decision hour h (signal at close of h, fill at open h+1) with week kk=(h+1-W0)//TRAD:
    universe U_kk (PIT at t_kk), eigenportfolios from latest day boundary d<=h+1, s-scores and betas."""
    if R is None:
        R = log_returns(P)
    out = []
    for kk in range(P.NW):
        t = window_start(kk)
        U = universe(P, t)
        S = np.full((TRAD, len(U)), np.nan)
        Bt = np.zeros((TRAD, len(U), M4_K))
        Qs, ev = [], []
        for n in range(TRAD // 24):
            Qd, e = m4_pca(R, t + 24 * n, U)
            Qs.append(Qd)
            ev.append(e)
        for r in range(TRAD):
            h = t - 1 + r
            Qd = Qs[r // 24]
            S[r], Bt[r] = m4_scores(R, h, U, Qd)
        out.append(dict(t=t, U=U, s=S, beta=Bt, Q=np.array(Qs), ev=ev))
    return out


def sim_m4(P, sig, c, flip_rng=None, want_detail=False):
    """Portfolio sim. Rebalance to target only when the open-signal set changes or at a week boundary.
    Target w = sum_i a_i (e_i - beta_i . Q), normalized to sum|w| = 1 (gross 1x equity)."""
    S = P.S
    q = np.zeros(S)
    E = 1.0
    dirs, flips = {}, {}
    H_end = W0 + P.NW * TRAD
    eqc = np.zeros(H_end - W0 + 2)       # eqc[i] = equity at close of bar W0-1+i ; last = after final liquidation
    eqc[0] = 1.0
    attr = np.zeros(S)
    tot_turn = tot_cost = tot_fund = 0.0
    n_entries = np.zeros(P.NW, int)
    gross_exp = np.zeros(H_end - W0)
    part = []
    pending = None
    gsum = fsum = csum = 0.0             # sums of per-bar simple returns (price / funding / cost)
    for h in range(W0 - 1, H_end):
        b = h + 1
        kk = (b - W0) // TRAD
        # ---------- decision at close of h (for fill at open b)
        if b < H_end:
            sg = sig[kk]
            r = b - sg["t"]                 # 0..TRAD-1 ; decision row r <-> h = t-1+r
            U = sg["U"]
            s = sg["s"][r]
            inU = {int(u): li for li, u in enumerate(U)}
            changed = (b == sg["t"])
            for i in list(dirs):
                li = inU.get(i)
                dead = b > P.last[i]
                if li is None or dead:
                    del dirs[i]
                    changed = True
                    continue
                si = s[li]
                if np.isfinite(si) and ((dirs[i] == 1 and si > -M4_SBC) or (dirs[i] == -1 and si < M4_SSC)):
                    del dirs[i]
                    changed = True
            for li, u in enumerate(U):
                u = int(u)
                if u in dirs or b > P.last[u] or not np.isfinite(s[li]):
                    continue
                if s[li] < -M4_SBO:
                    dirs[u] = 1
                elif s[li] > M4_SSO:
                    dirs[u] = -1
                else:
                    continue
                flips[u] = 1 if flip_rng is None else (1 if flip_rng.random() < 0.5 else -1)
                n_entries[kk] += 1
                changed = True
            if changed:
                w = np.zeros(len(U))
                Qd = sg["Q"][r // 24]
                for i, dd in dirs.items():
                    li = inU[i]
                    unit = -(sg["beta"][r][li] @ Qd)
                    unit[li] += 1.0
                    w += dd * flips[i] * unit
                w[P.last[U] < b] = 0.0               # never trade into a symbol with no further bars
                tgt = np.zeros(S)
                gw = np.abs(w).sum()
                if gw > 0:
                    w /= gw
                    pf = np.where(np.isfinite(P.O[b, U]), P.O[b, U], P.CF[h, U])
                    tgt[U] = w * E / pf
                pending = tgt
        else:
            pending = np.zeros(S)            # final liquidation at open of H_end
        # ---------- bar b
        held = np.nonzero(q)[0]
        po = np.where(np.isfinite(P.O[b]), P.O[b], P.CF[h]) if b < P.NH else P.CF[h]
        gap = float((q[held] * (po[held] - P.CF[h, held])).sum())
        fpay = 0.0
        if b < P.NH:
            fv = -(q[held] * po[held] * P.F[b, held])
            fpay = float(fv.sum())
            attr[held] += fv
        attr[held] += q[held] * (po[held] - P.CF[h, held])
        cost = 0.0
        # delisted symbols still held are force-closed at last price
        dead = held[b > P.last[held]]
        if len(dead):
            if pending is None:
                pending = q.copy()
            pending[dead] = 0.0
        if pending is not None:
            dq = pending - q
            tr = np.nonzero(dq)[0]
            tn = np.abs(dq[tr]) * po[tr]
            cost = c * float(tn.sum())
            attr[tr] -= c * tn
            tot_turn += float(tn.sum())
            if want_detail and len(tr):
                adv = P.Q[max(0, b - FORM):b, tr].sum(0) / 30.0
                ok = adv > 0
                part.extend(list((tn[ok] / E * 1e6) / adv[ok]))
            q = pending
            pending = None
        E_prev = E
        E = E + gap + fpay - cost
        tot_cost += cost
        tot_fund += fpay
        gsum += gap / E_prev
        fsum += fpay / E_prev
        csum += cost / E_prev
        if b < H_end:
            held = np.nonzero(q)[0]
            intr = q[held] * (P.CF[b, held] - po[held])
            attr[held] += intr
            E += float(intr.sum())
            gsum += float(intr.sum()) / E_prev
            gross_exp[b - W0] = float((np.abs(q[held]) * P.CF[b, held]).sum()) / E if E > 0 else 0.0
        eqc[b - W0 + 1] = E
    res = dict(eq=eqc, attr=attr, turn=tot_turn, cost=tot_cost, fund=tot_fund, n_entries=n_entries,
               gross_exp=gross_exp, gsum=gsum, fsum=fsum, csum=csum)
    if want_detail:
        res["part"] = np.array(part)
    return res
