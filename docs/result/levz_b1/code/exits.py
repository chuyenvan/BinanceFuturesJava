"""LEVZ B1 step 2 - exit engine on 1-minute CLOSE (PREREG_LEVZ_B1 sec 2), vectorised over the 195 exit configs.
Path minute i (0..43200): close of the 1m bar with open_time T_k + i min (ffilled). Entry p0 = path[0].
Per minute i >= 1, in order: (a) SL: close >= p0 (1 + SL) -> exit at close x 1.003; (b) trailing (arm a, gap g): armed at the first
i_a >= 1 with close <= p0 (1 - a); trough = min close over [i_a, i]; exit at the first i > i_a with close >= trough(i-1) x (1 + g)
-> close x 1.001 (arming and exit never in the same minute); (c) time: i = 60 H -> close. Missing run > 24 h -> exit at the
1441st missing minute at the last close ('miss'). Events at minutes >= nv (beyond 2025-12-31 23:59) do not exist; if none: 'eod'
at nv - 1 (the portfolio forces fold-end closes earlier anyway). Tie priority SL > TRAIL > TIME > MISS.
Funding: settlement at hour boundary T_{k+h} (h >= 1; B0 FR[k+h]) is received iff 60 h - 1 <= j (exit bar closes at or after
the boundary; B0 CHOICES2 #12), notional = qty x close of the bar ending at the boundary (path[60 h - 1]).
Outputs per candidate cid (ratios to p0): j, rs, xr (exit price / p0), fund (per notional), mx (max close 0..j / p0),
mxh (max close in the exit's hour window (60(h-1), 60h] up to j / p0), flag (exit minute ffilled); hourly mk[h] = path[60h]/p0,
hm[h] = max path over (60(h-1), 60h] / p0, fh[h] = funding per notional at boundary h, longgap.
usage: python3 code/exits.py all | bench"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]
import logging
import time
sys.dont_write_bytecode = True
sys.path.insert(0, _HERE)
import common_b1 as CB
sys.path.pop(0)
import numpy as np

log = logging.getLogger('levz_b1.exits')
BIG = 1 << 30
NX = len(CB.XCFGS)
X_S = np.array([CB.SLS.index(x[0]) for x in CB.XCFGS])
X_H = np.array([CB.HS.index(x[1]) for x in CB.XCFGS])
X_T = np.array([CB.TRAILS.index((x[2], x[3])) for x in CB.XCFGS])
OUTK = ('j', 'rs', 'xr', 'fund', 'mx', 'mxh', 'flag')


def exits_core(p, nv, miss_m, fh, gapmask=None):
    """p: float64 array len NPATH (p[0] = entry; padded with last value beyond nv); nv: number of valid minutes;
    miss_m: relative minute of a missing-run exit (BIG if none); fh: float64 len HMAX+1 funding per notional at boundary h.
    gapmask: bool len NPATH, True = ffilled minute (optional). Returns dict of arrays len 195."""
    assert len(p) == CB.NPATH and 1 <= nv <= CB.NPATH and np.isfinite(p).all() and p[0] > 0
    p0 = p[0]
    q = p[1:]
    cmax = np.maximum.accumulate(q)
    cmin = np.minimum.accumulate(q)
    sli = np.empty(len(CB.SLS), dtype=np.int64)
    for s, sl in enumerate(CB.SLS):
        i = int(np.searchsorted(cmax, p0 * (1.0 + sl), 'left')) + 1
        sli[s] = i if i < nv else BIG
    tri = np.full(len(CB.TRAILS), BIG, dtype=np.int64)
    for t, (a, g) in enumerate(CB.TRAILS):
        if a == 0.0:
            continue
        ia = int(np.searchsorted(-cmin, -(p0 * (1.0 - a)), 'left')) + 1
        if ia >= nv - 1:
            continue
        tr = np.minimum.accumulate(p[ia:nv])
        cond = p[ia + 1:nv] >= tr[:-1] * (1.0 + g)
        x = int(np.argmax(cond))
        if cond[x]:
            tri[t] = ia + 1 + x
    tmi = np.array([60 * hh if 60 * hh < nv else BIG for hh in CB.HS], dtype=np.int64)
    mi = miss_m if miss_m < nv else BIG
    ev = np.vstack([sli[X_S], tri[X_T], tmi[X_H], np.full(NX, mi, dtype=np.int64)])
    j = ev.min(axis=0)
    rs = np.argmax(ev == j[None, :], axis=0).astype(np.int8)
    eod = j >= BIG
    j = np.where(eod, nv - 1, j)
    rs[eod] = CB.R_EOD
    pj = p[j]
    mult = np.where(rs == CB.R_SL, 1.0 + CB.SL_SLIP, np.where(rs == CB.R_TRAIL, 1.0 + CB.TR_SLIP, 1.0))
    xr = pj * mult / p0
    fc = np.concatenate([[0.0], np.cumsum(fh[1:])])
    fund = fc[np.minimum((j + 1) // 60, CB.HMAX)]
    mx = np.maximum(p0, cmax[j - 1]) / p0
    rmh = np.maximum.accumulate(q.reshape(CB.HMAX, 60), axis=1).ravel()
    mxh = rmh[j - 1] / p0
    flag = gapmask[j].astype(np.int8) if gapmask is not None else np.zeros(NX, dtype=np.int8)
    return dict(j=j.astype(np.int32), rs=rs, xr=xr, fund=fund, mx=mx, mxh=mxh, flag=flag)


def hourly_core(p, fh):
    """mk[h] = p[60h]/p0 (h = 0..720), hm[h] = max p(60(h-1), 60h] / p0 (hm[0] = 1), fh passthrough."""
    p0 = p[0]
    mk = p[::60] / p0
    hm = np.concatenate([[1.0], p[1:].reshape(CB.HMAX, 60).max(axis=1) / p0])
    return mk, hm


class Store:
    def __init__(self, mm=None, gaps=None, FR=None):
        self.mm = np.load(CB.WORK + '/close1m.npy', mmap_mode='r') if mm is None else mm
        if gaps is None:
            g = np.load(CB.WORK + '/gaps.npz')
            gaps = (g['c'], g['g0'], g['g1'])
        gc, g0, g1 = gaps
        self.gaps = {}
        o = np.lexsort((g0, gc))
        gc, g0, g1 = gc[o], g0[o], g1[o]
        for c in np.unique(gc):
            a, b = np.searchsorted(gc, c, 'left'), np.searchsorted(gc, c, 'right')
            self.gaps[int(c)] = (g0[a:b], g1[a:b])
        if FR is None:
            FR = np.load(CB.L2 + '/work/inputs.npz')['FR']
        self.FR = FR
        self.NMIN = self.mm.shape[1]
        self.NH = FR.shape[0]


def path_of(st, c, k):
    """returns (p padded float64 len NPATH, nv, miss_m, gapmask, fh, longgap)."""
    b = 60 * int(k)
    nv = min(CB.NPATH, st.NMIN - b)
    assert nv >= 1
    raw = np.asarray(st.mm[c, b:b + nv], dtype=np.float64)
    assert np.isfinite(raw[0]), 'no 1m bar at entry'
    p = np.empty(CB.NPATH)
    p[:nv] = raw
    p[nv:] = raw[-1]
    gm = np.zeros(CB.NPATH, dtype=bool)
    miss_m = BIG
    longgap = False
    if int(c) in st.gaps:
        g0, g1 = st.gaps[int(c)]
        i = int(np.searchsorted(g0, b, 'right'))
        while i < len(g0) and g0[i] < b + nv:
            a, e = int(g0[i]) - b, min(int(g1[i]) - b, nv)
            gm[a:e] = True
            if int(g1[i]) - int(g0[i]) > CB.MISS_MIN and miss_m == BIG:
                miss_m = int(g0[i]) + CB.MISS_MIN - b
                longgap = True
            i += 1
        assert not (len(g0) and np.any((g0 <= b) & (g1 > b))), 'entry minute inside a gap'
    fh = np.zeros(CB.HMAX + 1)
    hh = np.arange(1, CB.HMAX + 1)
    kk = int(k) + hh
    ok = kk < st.NH
    fh[1:][ok] = st.FR[kk[ok], c] * p[60 * hh[ok] - 1] / p[0]
    return p, nv, miss_m, gm, fh, longgap


def compute(st, ks, cs):
    """exits + hourly arrays for candidate list (ks, cs)."""
    n = len(ks)
    out = {kk: None for kk in OUTK}
    res = {kk: [] for kk in OUTK}
    mk = np.empty((n, CB.HMAX + 1))
    hm = np.empty((n, CB.HMAX + 1))
    fh = np.empty((n, CB.HMAX + 1))
    p0 = np.empty(n)
    lg = np.zeros(n, dtype=bool)
    for i in range(n):
        p, nv, miss_m, gm, f, longgap = path_of(st, int(cs[i]), int(ks[i]))
        r = exits_core(p, nv, miss_m, f, gm)
        for kk in OUTK:
            res[kk].append(r[kk])
        mk[i], hm[i] = hourly_core(p, f)
        fh[i] = f
        p0[i] = p[0]
        lg[i] = longgap
    for kk in OUTK:
        out[kk] = np.vstack(res[kk]) if n else np.zeros((0, NX))
    out.update(mk=mk, hm=hm, fh=fh, fc=np.cumsum(fh, axis=1), p0=p0, longgap=lg, k=np.asarray(ks), c=np.asarray(cs))
    return out


def load_table(path=CB.WORK + '/exits.npz'):
    z = np.load(path)
    return {kk: z[kk] for kk in z.files}


def main_all():
    cz = np.load(CB.WORK + '/cand_b1.npz')
    uk, uc = cz['U_k'], cz['U_c']
    st = Store()
    t0 = time.time()
    out = compute(st, uk, uc)
    dt = time.time() - t0
    np.savez(CB.WORK + '/exits.npz.tmp.npz', **out)
    os.replace(CB.WORK + '/exits.npz.tmp.npz', CB.WORK + '/exits.npz')
    log.info('exits all n=%d %.1fs (%.4f s/cand, %.2e s/cand/cfg)', len(uk), dt, dt / max(len(uk), 1), dt / max(len(uk), 1) / NX)


def bench(n=300):
    """timing only on the first n union candidates; results are NOT saved / inspected."""
    cz = np.load(CB.WORK + '/cand_b1.npz')
    st = Store()
    t0 = time.time()
    compute(st, cz['U_k'][:n], cz['U_c'][:n])
    dt = time.time() - t0
    log.info('bench exits n=%d %.2fs -> %.4f s/cand (195 cfgs)', n, dt, dt / n)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'all': main_all, 'bench': bench}[sys.argv[1]]()
