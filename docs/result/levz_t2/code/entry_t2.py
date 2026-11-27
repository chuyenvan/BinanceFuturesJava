"""LEVZ T2 step 1: REAL ENTRY MINUTE per (candidate, entry type) (PREREG_LEVZ_T2 sec 2). Candidates = union of cand_b1 W7_E0 classes
(z 2.5 / 3.0 / 3.5; signal hour k, coin c). Minute index j <-> 1m bar open_time H0 + j min (close1m memmap of B1, ffilled; a minute
is REAL iff the coin has a bar there: j >= first bar and j outside every gap of gaps.npz). Decision at a bar close uses only closes of
bars <= that bar and OI under the tier-1 lag rule (row h holds the last OI record with ts <= T_h - 10 min).
- E0   : m = 60 k (B1 entry, close of bar open T_k), price = close.  p0 := close1m[c, 60 k] (reference price, = B1 entry price).
- EL_b : resting sell limit at p0 (1 + b) placed after bar 60 k closed; fill at the FIRST minute m = 60 k + i, i in 1..2879 (bar
         closes at or before T_k + 48 h), with REAL bar and close >= level; price = level exactly (no slip).
- EB   : L = min over the 24 hourly candles closing at T_{k-23} .. T_k of the candle close (= close1m[60 h - 1], ffilled).  At each
         hour boundary T_{k+j}, j = 1..48: hourly close hc = close1m[60 (k + j) - 1]; first j with hc < L AND a REAL bar at minute
         60 (k + j) -> market sell at the close of that bar (1-minute delay, as E0) x (1 - 0.001).
- EO_x : at T_{k+j}, j = 1..48: OI_j = exp(X[k + j]) (lagged row); Mx = max finite OI over rows k..k+j; first j with OI_j finite and
         OI_j <= (1 - x) Mx AND a REAL bar at 60 (k + j) -> market sell at close1m[60 (k + j)] x (1 - 0.001).
- Hour-boundary trigger whose entry bar is missing: no entry at that hour; the condition is re-evaluated at the next hour (CHOICES).
- No fill inside the window (or window cut by 2025-12-31 23:59 / data end) => candidate dropped for that entry type (m = -1).
Output work/entry_t2.npz: cid_b1, k, c, p0, and per type <E>_m (abs minute, -1 none), <E>_px (float64), <E>_d (delay min = m - 60 k).
usage: python3 code/entry_t2.py build | hygiene"""
import glob
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = C.setup_log('entry')
CB = C.CB
OUTF = C.WORK + '/entry_t2.npz'


class Src:
    """close1m memmap + REAL-bar test + lagged hourly log-OI X (NH x ns), all < 2026-01-01."""
    def __init__(self, mm=None, gaps=None, first=None, X=None):
        self.mm = np.load(CB.WORK + '/close1m.npy', mmap_mode='r') if mm is None else mm
        if gaps is None:
            g = np.load(CB.WORK + '/gaps.npz')
            gaps, first = (g['c'], g['g0'], g['g1']), g['first']
        self.first = np.asarray(first)
        gc, g0, g1 = gaps
        o = np.lexsort((g0, gc))
        gc, g0, g1 = gc[o], g0[o], g1[o]
        self.gaps = {}
        for c in np.unique(gc):
            a, b = np.searchsorted(gc, c, 'left'), np.searchsorted(gc, c, 'right')
            self.gaps[int(c)] = (g0[a:b], g1[a:b])
        self.nmin = self.mm.shape[1]
        self._X = X

    @property
    def X(self):
        if self._X is None:
            self._X = load_oi_x()
        return self._X

    def real(self, c, a, b):
        """bool mask: minutes a..b-1 of coin c have a real 1m bar."""
        a, b = int(a), int(min(b, self.nmin))
        out = np.zeros(max(b - a, 0), dtype=bool)
        if b <= a:
            return out
        f = int(self.first[c])
        if f < 0:
            return out
        out[max(f - a, 0):] = True
        if int(c) in self.gaps:
            g0, g1 = self.gaps[int(c)]
            i = max(int(np.searchsorted(g1, a, 'right')), 0)
            while i < len(g0) and g0[i] < b:
                s, e = max(int(g0[i]), a), min(int(g1[i]), b)
                if e > s:
                    out[s - a:e - a] = False
                i += 1
        return out

    def close(self, c, a, b):
        a, b = int(a), int(min(b, self.nmin))
        return np.asarray(self.mm[c, a:b], dtype=np.float64)


def load_oi_x():
    """tier-1 lagged log-OI per hour (same loop as levz.Data.X; syms = levz2 sig_meta syms)."""
    syms = CB.meta()['syms']
    col = {s: i for i, s in enumerate(syms)}
    X = np.full((C.NH, len(syms)), np.nan)
    tsr = np.full((C.NH, len(syms)), -1, dtype=np.int64)
    for ym in CB.ym_list():
        d = pd.read_parquet('%s/oi_%s.parquet' % (C.OIDIR, ym))
        d['sym'] = d['sym'].astype(str)
        d = d[d['sym'].isin(col) & (d['h'] >= C.H0) & (d['h'] < CB.CUT)]
        r = ((d['h'].values - C.H0) // C.H).astype(np.int64)
        c = d['sym'].map(col).values.astype(np.int64)
        t = d['tsr'].values
        assert (t <= d['h'].values - 10 * C.M).all() and (t > d['h'].values - 70 * C.M).all(), 'OI lag rule violated'
        assert int(d['h'].max()) < CB.CUT if len(d) else True
        m = t > tsr[r, c]
        X[r[m], c[m]] = d['x'].values[m]
        tsr[r[m], c[m]] = t[m]
    return X


# ---------------------------------------------------------------- per candidate
def entry_E0(src, k, c):
    m = 60 * int(k)
    return m, float(src.close(c, m, m + 1)[0])


def entry_EL(src, k, c, b, p0):
    base = 60 * int(k)
    lv = p0 * (1.0 + b)
    seg = src.close(c, base + 1, base + C.WIN_MIN)            # i = 1..2879
    ok = src.real(c, base + 1, base + C.WIN_MIN)
    hit = (seg >= lv) & ok
    if not hit.any():
        return -1, np.nan
    i = int(np.argmax(hit))
    return base + 1 + i, lv


def eb_level(src, k, c):
    base = 60 * int(k)
    idx = base - 1 - 60 * np.arange(C.EB_LOOKBACK)              # closes of candles closing at T_k, T_{k-1}, ..., T_{k-23}
    idx = idx[idx >= 0]
    v = np.asarray(src.mm[c, idx], dtype=np.float64)
    v = v[np.isfinite(v)]
    return float(v.min()) if len(v) else np.nan


def _hour_entry(src, k, c, trig):
    """trig: bool array over j = 1..len(trig) (hour boundary T_{k+j}); first j with trig and a REAL bar at 60 (k + j)."""
    base = 60 * int(k)
    for jj in np.flatnonzero(trig):
        m = base + 60 * (int(jj) + 1)
        if m >= src.nmin:
            break
        if src.real(c, m, m + 1)[0]:
            return m, float(src.close(c, m, m + 1)[0]) * (1.0 - C.MKT_SLIP)
    return -1, np.nan


def entry_EB(src, k, c):
    L = eb_level(src, k, c)
    if not np.isfinite(L):
        return -1, np.nan
    base = 60 * int(k)
    idx = base + 60 * np.arange(1, C.WIN_H + 1) - 1
    idx = idx[idx < src.nmin]
    hc = np.asarray(src.mm[c, idx], dtype=np.float64)
    return _hour_entry(src, k, c, hc < L)


def entry_EO(src, k, c, x):
    k = int(k)
    hi = min(k + C.WIN_H + 1, C.NH)
    xs = src.X[k:hi, c]                                          # rows k .. k+48 (lagged)
    oi = np.exp(xs)
    mx = np.fmax.accumulate(oi)                                  # NaN ignored once a finite value was seen
    with np.errstate(invalid='ignore'):
        trig = np.isfinite(oi[1:]) & np.isfinite(mx[1:]) & (oi[1:] <= (1.0 - x) * mx[1:])
    return _hour_entry(src, k, c, trig)


def entry_one(src, k, c, e, p0=None):
    if p0 is None:
        p0 = entry_E0(src, k, c)[1]
    if e == 'E0':
        return entry_E0(src, k, c)
    if e in C.EL_B:
        return entry_EL(src, k, c, C.EL_B[e], p0)
    if e == 'EB':
        return entry_EB(src, k, c)
    if e in C.EO_X:
        return entry_EO(src, k, c, C.EO_X[e])
    raise KeyError(e)


def compute(src, uk, uc, entries=C.ENTRIES):
    n = len(uk)
    out = dict(k=np.asarray(uk, dtype=np.int64), c=np.asarray(uc, dtype=np.int64), p0=np.empty(n))
    for e in entries:
        out[e + '_m'] = np.full(n, -1, dtype=np.int64)
        out[e + '_px'] = np.full(n, np.nan)
    for i in range(n):
        k, c = int(uk[i]), int(uc[i])
        m0, p0 = entry_E0(src, k, c)
        assert src.real(c, m0, m0 + 1)[0] and np.isfinite(p0) and p0 > 0, 'E0 entry bar missing'
        out['p0'][i] = p0
        for e in entries:
            m, px = entry_one(src, k, c, e, p0)
            out[e + '_m'][i], out[e + '_px'][i] = m, px
    for e in entries:
        mm = out[e + '_m']
        out[e + '_d'] = np.where(mm >= 0, mm - 60 * out['k'], -1)
        assert (out[e + '_d'] <= C.WIN_MIN).all()
    return out


def load_entries(path=OUTF):
    z = np.load(path)
    return {kk: z[kk] for kk in z.files}


def build():
    cls, ucid, uk, uc = C.cand_classes()
    src = Src()
    import time
    t0 = time.time()
    out = compute(src, uk, uc)
    out['cid_b1'] = ucid
    np.savez(OUTF + '.tmp.npz', **out)
    os.replace(OUTF + '.tmp.npz', OUTF)
    log.info('entry_t2 build n=%d %.1fs', len(uk), time.time() - t0)
    hygiene(out)


def hygiene(out=None):
    """NO profit: fill rate per signal year, delay quantiles (minutes), price ratio checks."""
    if out is None:
        out = load_entries()
    yr = C.year_of_k(out['k'])
    for e in C.ENTRIES:
        m = out[e + '_m'] >= 0
        rates = {int(y): '%.3f (%d/%d)' % (m[yr == y].mean(), int(m[yr == y].sum()), int((yr == y).sum())) for y in np.unique(yr)}
        d = out[e + '_d'][m] / 60.0
        q = np.round(np.quantile(d, [0.1, 0.5, 0.9]), 2).tolist() if m.any() else None
        rr = out[e + '_px'][m] / out['p0'][m]
        log.info('hygiene %-5s fill=%.3f by_year=%s delay_h q10/50/90=%s px/p0 min/med/max=%s nan_px=%d', e, m.mean(), rates, q,
                 np.round([rr.min(), np.median(rr), rr.max()], 4).tolist() if m.any() else None, int(np.isnan(out[e + '_px'][m]).sum()))


if __name__ == '__main__':
    {'build': build, 'hygiene': hygiene}[sys.argv[1]]()
