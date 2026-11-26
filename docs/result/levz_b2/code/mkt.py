"""LEVZ B2 step 1 - market / coin series per hour (PREREG_LEVZ_B2 sec 1). CAUSAL: value at decision hour k (T_k = H0 + k h) uses only
hourly candles CLOSED at or before T_k; data < 2026-01-01 UTC only.
Hourly close: CC[k, c] = clast of the hour candle [T_{k-1}, T_k) (tier-1 work/hr_<ym>.parquet, close of last 1m bar with open_time in
[T_{k-1}, T_{k-1}+59m]; NaN if that hour has no 1m bar; CC[0] = NaN). The candle opening at T_k (still forming) is never used.
- EWr_n(k) = mean over c with U[k, c] and CC[k, c], CC[k-24n, c] finite of CC[k, c] / CC[k-24n, c] - 1; NaN (=> gate closed) unless
  >= 50 % of U[k] coins have both prices (B2 ADDENDUM1 D).
- BTCdev_n(k) = CC[k, BTC] / mean(CC[k-24n .. k-1, BTC]) - 1; ALL 24n closes required (else NaN).
- BR(k) = #{c: U[k, c] and LEV7 at some hour in k-23..k} / #{c: U[k, c]}; LEV7 = z_oi >= 2.5 & z_f >= 2.5 & f > 1e-4 (W = 7, NaN -> False).
  BR(k) = NaN if #U[k] = 0, k < 23, or in any hour of k-23..k fewer than 50 % of U coins have finite z_oi and z_f (warm-up guard).
- BRmed(k) = median of finite BR[k-2160 .. k-1] (90 days, excl. k); NaN unless >= 80 % (1 728) of those 2 160 values are finite.
- coin: r24(k, c) = CC[k, c] / CC[k-24, c] - 1; f(k, c) = B0 signal f (sig_W7; equal to sig_W14 where both finite, asserted);
  qv30(D, c) = mean d1 qv over D-30..D-1 (all 30 days required; tier-1 universe definition) with D = UTC day of T_k;
  age(D, c) = days since first d1 day of c (d1 starts 2021-01-01 => lower bound; -1 if no d1 row).
usage: python3 code/mkt.py build   -> work/mkt.npz"""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2c
sys.path.pop(0)
import logging
import time
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b2.mkt')
H = 3600000
DAY = 86400000
HPD = 24
LEV_Z = 2.5
LEV_F = 0.0001
BR_WIN = 24
BR_COV = 0.5
MED_WIN = 90 * 24
MED_FRAC = 0.8
EW_MINFRAC = 0.5
HR = '/home/ubuntu/claude_master/w3/levz/work/hr_%s.parquet'


# ---------------------------------------------------------------- pure functions (unit-tested)
def cc_from_hr(c, h, clast, h0, nh, ns):
    """hourly close table: row k <- candle with open time h = T_{k-1} (closes at T_k)."""
    cc = np.full((nh, ns), np.nan)
    k = (np.asarray(h, dtype=np.int64) - h0) // H + 1
    m = (k >= 1) & (k < nh) & np.isfinite(clast)
    cc[k[m], np.asarray(c)[m]] = np.asarray(clast, dtype=np.float64)[m]
    return cc


def lagret(cc, lag):
    r = np.full(cc.shape, np.nan)
    with np.errstate(divide='ignore', invalid='ignore'):
        r[lag:] = cc[lag:] / cc[:-lag] - 1.0
    return r


def ewr(cc, U, ndays, hpd=HPD, minfrac=EW_MINFRAC):
    """B2 ADDENDUM1 D: coins without both prices dropped; NaN (=> gate closed) unless cnt >= minfrac x #U[k] (and cnt > 0)."""
    r = lagret(cc, ndays * hpd)
    ok = U & np.isfinite(r)
    cnt = ok.sum(axis=1)
    nu = U.sum(axis=1)
    s = np.where(ok, r, 0.0).sum(axis=1)
    good = (cnt > 0) & (cnt >= minfrac * nu)
    with np.errstate(divide='ignore', invalid='ignore'):
        ew = np.where(good, s / np.maximum(cnt, 1), np.nan)
    return ew, cnt


def btcdev(cb, ndays, hpd=HPD):
    L = ndays * hpd
    n = len(cb)
    fin = np.isfinite(cb)
    cs = np.concatenate([[0.0], np.cumsum(np.where(fin, cb, 0.0))])
    cn = np.concatenate([[0], np.cumsum(fin.astype(np.int64))])
    out = np.full(n, np.nan)
    k = np.arange(L, n)
    s = cs[k] - cs[k - L]          # sum of cb[k-L .. k-1]
    c = cn[k] - cn[k - L]
    ok = (c == L) & fin[k]
    with np.errstate(divide='ignore', invalid='ignore'):
        out[k] = np.where(ok, cb[k] / (s / L) - 1.0, np.nan)
    return out


def lev_mat(z_oi, z_f, f, z=LEV_Z, fmin=LEV_F):
    with np.errstate(invalid='ignore'):
        return (z_oi >= z) & (z_f >= z) & (f > fmin)


def win_any(b, win):
    """out[k, c] = any(b[k-win+1 .. k, c]) (rows < 0 ignored)."""
    cs = np.concatenate([np.zeros((1, b.shape[1]), dtype=np.int64), np.cumsum(b.astype(np.int64), axis=0)])
    k = np.arange(b.shape[0])
    lo = np.maximum(k - win + 1, 0)
    return (cs[k + 1] - cs[lo]) > 0


def br(lev, U, zok, win=BR_WIN, covmin=BR_COV):
    nu = U.sum(axis=1)
    anyl = win_any(lev, win)
    num = (U & anyl).sum(axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        cov = np.where(nu > 0, (U & zok).sum(axis=1) / np.maximum(nu, 1), 0.0)
    bad = (cov < covmin).astype(np.int64)
    cb = np.concatenate([[0], np.cumsum(bad)])
    k = np.arange(len(nu))
    lo = np.maximum(k - win + 1, 0)
    badw = (cb[k + 1] - cb[lo]) > 0
    ok = (nu > 0) & (k >= win - 1) & ~badw
    with np.errstate(divide='ignore', invalid='ignore'):
        out = np.where(ok, num / np.maximum(nu, 1), np.nan)
    return out, cov


def brmed(b, win=MED_WIN, frac=MED_FRAC):
    n = len(b)
    out = np.full(n, np.nan)
    need = int(np.ceil(frac * win))
    fin = np.isfinite(b)
    cn = np.concatenate([[0], np.cumsum(fin.astype(np.int64))])
    for k in range(win, n):
        if cn[k] - cn[k - win] >= need:
            out[k] = np.nanmedian(b[k - win:k])
    return out


def qv30_age(sym_col, d1, day0_ms, nd):
    """d1: DataFrame sym, day (datetime64), qv. Returns QV30[nd, ns] (NaN = unknown) and AGE[nd, ns] (int32, -1 = unknown)."""
    ns = len(sym_col)
    q = np.full((nd, ns), np.nan)
    age = np.full((nd, ns), -1, dtype=np.int32)
    dd = np.arange(nd, dtype=np.int64)
    for s, g in d1.groupby('sym', sort=True):
        if s not in sym_col:
            continue
        c = sym_col[s]
        g = g.set_index('day')['qv'].sort_index()
        g = g[~g.index.duplicated()]
        idx = pd.date_range(g.index.min(), g.index.max() + pd.Timedelta(days=1), freq='D')
        g = g.reindex(idx)
        q30 = g.rolling(30, min_periods=30).mean().shift(1)
        di = (idx.values.astype('datetime64[ms]').astype(np.int64) - day0_ms) // DAY
        m = (di >= 0) & (di < nd)
        q[di[m], c] = q30.values[m]
        f = (int(idx[0].value // 10**6) - day0_ms) // DAY
        a = dd - f
        age[:, c] = np.where(a >= 0, a, -1).astype(np.int32)
    return q, age


# ---------------------------------------------------------------- build on real data
def build():
    CB = b2c.b1('common_b1')
    C = b2c.l1common()
    m = CB.meta()
    syms, NH, H0, CUT = m['syms'], CB.NH, CB.H0, CB.CUT
    assert CUT == C.CUTOFF_MS == 1767225600000
    ns = len(syms)
    col = {s: i for i, s in enumerate(syms)}
    t0 = time.time()
    parts = []
    for ym in CB.ym_list():
        d = pd.read_parquet(HR % ym, columns=['sym', 'h', 'clast'])
        assert len(d) == 0 or int(d['h'].max()) + H <= CUT, 'hour candle closing after 2026-01-01'
        d['sym'] = d['sym'].astype(str)
        d = d[d['sym'].isin(col)]
        parts.append((d['sym'].map(col).values.astype(np.int64), d['h'].values.astype(np.int64), d['clast'].values))
    c = np.concatenate([p[0] for p in parts])
    h = np.concatenate([p[1] for p in parts])
    cl = np.concatenate([p[2] for p in parts])
    key = c * (NH + 1) + (h - H0) // H
    assert len(np.unique(key)) == len(key), 'duplicate (sym, hour) in hr tables'
    CC = cc_from_hr(c, h, cl, H0, NH, ns)
    del parts, c, h, cl
    log.info('CC built finite=%d %.1fs', int(np.isfinite(CC).sum()), time.time() - t0)
    U = np.load(CB.L2 + '/work/inputs.npz')['U']
    assert U.shape == (NH, ns)
    S = CB.load_b0('sim')
    SG = S.load_sibling('sig')
    G = SG.dense_from_sig(7)
    assert G['syms'] == syms and (G['u'] == U).all()
    lev = lev_mat(G['z_oi'], G['z_f'], G['f'])
    zok = np.isfinite(G['z_oi']) & np.isfinite(G['z_f'])
    F = G['f'].copy()
    del G
    f14 = pd.read_parquet(CB.L2 + '/work/sig_W14.parquet', columns=['sym', 't', 'f'])
    assert int(f14['t'].max()) < CUT
    r14 = ((f14['t'].values - H0) // H).astype(np.int64)
    c14 = f14['sym'].map(col).values.astype(np.int64)
    v14 = f14['f'].values
    v7 = F[r14, c14]
    both = np.isfinite(v14) & np.isfinite(v7)
    assert (v14[both] == v7[both]).all(), 'f differs between sig_W7 and sig_W14'
    log.info('f W7 vs W14: both finite=%d equal; only W14 finite=%d', int(both.sum()), int((np.isfinite(v14) & ~np.isfinite(v7)).sum()))
    out = {}
    for n in (3, 7, 14):
        out['EW%d' % n], out['EWN%d' % n] = ewr(CC, U, n)
    ib = col['BTCUSDT']
    for n in (7, 20):
        out['BTC%d' % n] = btcdev(CC[:, ib], n)
    out['BR'], out['BRCOV'] = br(lev, U, zok)
    out['BRmed'] = brmed(out['BR'])
    out['R24'] = lagret(CC, 24)
    out['F'] = F
    d1 = C.read_d1(CUT)
    assert d1['day'].max() < pd.Timestamp(CUT, unit='ms')
    d1['sym'] = d1['sym'].astype(str)
    nd = (CUT - H0) // DAY
    out['QV30'], out['AGE'] = qv30_age(col, d1, H0, nd)
    out['NU'] = U.sum(axis=1)
    out['syms'] = np.array(syms)
    out['H0'] = np.int64(H0)
    out['NH'] = np.int64(NH)
    fn = b2c.WORK + '/mkt.npz'
    np.savez(fn + '.tmp.npz', **out)
    os.replace(fn + '.tmp.npz', fn)
    for kk in ('EW3', 'EW7', 'EW14', 'BTC7', 'BTC20', 'BR', 'BRmed'):
        v = out[kk]
        log.info('%s finite=%d/%d first_finite_k=%s', kk, int(np.isfinite(v).sum()), NH,
                 int(np.flatnonzero(np.isfinite(v))[0]) if np.isfinite(v).any() else None)
    log.info('mkt built %.1fs size=%.0f MB', time.time() - t0, os.path.getsize(fn) / 1e6)


def load(path=None):
    z = np.load(path or b2c.WORK + '/mkt.npz')
    return {k: z[k] for k in z.files}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'build': build}[sys.argv[1]]()
