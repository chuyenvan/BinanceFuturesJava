"""Thu vien dung chung cho job NBETS. Phuong phap chot o docs/PREREG_NBETS.md."""
import logging, os, re
import numpy as np
import pandas as pd

B = "/home/ubuntu/java/devrun"
SEED = 20260903
NREP = 2000
CAP0 = 35000.0
GRID = [1, 2, 3, 5, 7, 10, 14, 21, 28, 42, 63]
Z80 = 2.80158
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")


def eq(tag):
    """Y het qret.py / PREREG_CI section 1: equity = b+unP, ban ghi cuoi trong ngay."""
    rows = []
    for line in open("%s/%s/logs/sim.out" % (B, tag), errors="ignore"):
        m = RX.search(line)
        if m:
            rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


def logret(tag):
    s = eq(tag)
    v = np.concatenate([[CAP0], s.values.astype(float)])
    assert (v > 0).all(), tag
    return np.diff(np.log(v)), s


def idxmat(n, blen, nrep, seed):
    """Y HET ci_group_a.py: moving-block circular, ghep nb block roi cat con n."""
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    off = np.arange(blen)
    ix = (starts[:, :, None] + off[None, None, :]) % n
    return ix.reshape(nrep, nb * blen)[:, :n]


def _circ_blocksum(x, m):
    """bs[j] = sum(x[j:j+m]) vong tron, j = 0..n-1."""
    n = len(x)
    xc = np.concatenate([x, x[: m]])
    c = np.concatenate([[0.0], np.cumsum(xc)])
    return c[m: m + n] - c[0:n]


def boot_starts(n, blen, nrep, seed):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    return rng.integers(0, n, size=(nrep, nb)), nb


def boot_sum(x, blen, starts, nb):
    """Tong cua chuoi resample (dai dung n) — tuong duong x[idxmat].sum(axis=1)."""
    n = len(x)
    p = n - (nb - 1) * blen
    tot = np.zeros(starts.shape[0])
    if nb > 1:
        bs = _circ_blocksum(x, blen)
        tot += bs[starts[:, : nb - 1]].sum(axis=1)
    ps = _circ_blocksum(x, p)
    tot += ps[starts[:, nb - 1]]
    return tot


def pw_blocklen(x):
    """Politis-White (2004) + Patton-Politis-White (2009), circular block bootstrap."""
    x = np.asarray(x, float)
    n = len(x)
    xd = x - x.mean()
    kn = max(5, int(np.ceil(np.sqrt(np.log10(n)))))
    mmax = int(np.ceil(np.sqrt(n))) + kn
    ac = np.array([np.dot(xd[: n - k], xd[k:]) / n for k in range(0, mmax + 1)])
    rho = ac / ac[0]
    thr = 2.0 * np.sqrt(np.log10(n) / n)
    m = mmax
    for cand in range(1, mmax + 1):
        hi = min(cand + kn, mmax)
        if np.all(np.abs(rho[cand + 1: hi + 1]) < thr):
            m = cand
            break
    M = int(min(2 * m, mmax))
    ks = np.arange(-M, M + 1)
    t = np.abs(ks) / float(M)
    lam = np.where(t <= 0.5, 1.0, np.where(t <= 1.0, 2.0 * (1.0 - t), 0.0))
    R = ac[np.abs(ks)]
    Ghat = np.sum(lam * np.abs(ks) * R)
    Shat = np.sum(lam * R)
    Dcb = (4.0 / 3.0) * Shat ** 2
    if Dcb <= 0 or Ghat == 0:
        return 1, m, M
    b = (2.0 * Ghat ** 2 / Dcb) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    bmax = np.ceil(min(3.0 * np.sqrt(n), n / 3.0))
    b = float(np.clip(b, 1.0, bmax))
    return int(np.ceil(b)), m, M


def var_ratio(x, grid=None):
    """V(L) = L * var(trung binh khoi do dai L, vong tron); VR(L) = V(L)/V(1)."""
    grid = grid or GRID
    x = np.asarray(x, float)
    n = len(x)
    out = {}
    for L in grid:
        bs = _circ_blocksum(x, L) / float(L)
        out[L] = L * bs.var(ddof=1)
    v1 = x.var(ddof=1)
    return {L: out[L] / v1 for L in grid}, out, v1


def vr_plateau(vr, grid=None):
    """PREREG_NBETS section 3.3: L nho nhat sao cho moi L' trong [L, min(4L,63)] lech <= 10%."""
    grid = grid or GRID
    for L in grid:
        hi = min(4 * L, grid[-1])
        ok = True
        for L2 in grid:
            if L <= L2 <= hi:
                if abs(vr[L2] / vr[L] - 1.0) > 0.10:
                    ok = False
                    break
        if ok:
            return L, True
    return grid[-1], False


def ess_from_vr(n, vr, L):
    """ESS = T * V(1)/V(L) — so quan sat ngay doc lap-hoa."""
    return n / vr[L]


def snap_up(L, grid=None):
    grid = grid or GRID
    for g in grid:
        if g >= L:
            return g
    return grid[-1]
