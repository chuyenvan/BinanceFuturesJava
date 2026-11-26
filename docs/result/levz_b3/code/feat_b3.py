"""LEVZ B3 step 4 - features (PREREG_LEVZ_B3 sec 4). Every feature of candidate (k, c) uses only data available at decision hour
T_k = H0 + k h. Sources (time index = row k):
- px  : levz2/work/px_1h.parquet, row k = hourly candle [T_k - 1 h, T_k) (B0 S2 convention A: t = close-time label; asserted against the
        1m close in test_b3) -> HI, LO, CL, QV.
- sig : levz2 sig_W7 (dense_from_sig): ZOI, ZF, F (r8), ZR, U at decision hour k (B0, audited).
- oi  : levz/work/oi_<ym>.parquet: X = ln OI read at tsr <= h - 10 min (same reader logic as tier-1 levz.Data).
- cc  : levz/work/hr_<ym>.parquet clast via B2 mkt.cc_from_hr (row k = candle closing at T_k) -> EW / BTCdev with B2 mkt.ewr / btcdev.
- age : levz_b2/work/mkt.npz AGE[day] (days since first d1 row; d1 starts 2021-01-01 => lower bound before 2023; capped 720).
- pool mask = U & ZOI >= 1.5 & ZF >= 1.5 & F > 1e-4 & has1m (= B0 candidates E0 condition, asserted == pool in test).
No coin name, year, month, weekday. Features that cannot be built from available data are dropped and listed (none so far).
usage: python3 code/feat_b3.py build   -> work/feat_b3.parquet, out/feat_b3.json"""
import os
import sys
import json
import logging
import time
sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('common_b3', os.path.join(_HERE, 'common_b3.py'))
C3 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault('common_b3', C3)
_spec.loader.exec_module(C3)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b3.feat')
FEAT = C3.WORK + '/feat_b3.parquet'
F_MIN = 0.0001
MINFRAC = 0.8          # rolling std / sums need >= 80 % finite hours in the window (CHOICES_B3)
AGE_CAP = 720
COIN = ['z_oi', 'z_f', 's', 'zdiff', 'f', 'z_r', 'lr1', 'lr4', 'lr24', 'lr72', 'lr168', 'rv24', 'rv168', 'rng24', 'dhi168',
        'dlo168', 'lqv24', 'qvratio', 'liqrank', 'age', 'levrun', 'ncand7d', 'doi24', 'doi72', 'df24']
MKT = ['ew3', 'ew7', 'ew14', 'btc7', 'btc20', 'btcvol7', 'frac_lev', 'frac_pool', 'ncand_hour']
ALL = COIN + MKT
TIME_KEYS = ('HI', 'LO', 'CL', 'QV', 'ZOI', 'ZF', 'F', 'ZR', 'U', 'HAS', 'X', 'CC')


# ---------------------------------------------------------------- loaders (real data, < 2026 only)
def load_raw():
    CB = C3.CB
    m = CB.meta()
    syms, NH = m['syms'], CB.NH
    ns = len(syms)
    col = {s: i for i, s in enumerate(syms)}
    A = dict(off=0, syms=syms, ib=col['BTCUSDT'])
    px = pd.read_parquet(CB.L2 + '/work/px_1h.parquet')
    px = px[px['sym'].isin(col)]
    k = ((px['t'].values - C3.H0) // C3.H).astype(np.int64)
    mm = (k >= 0) & (k < NH)
    px, k = px[mm], k[mm]
    assert int(px['t'].max()) < C3.CUT
    c = px['sym'].map(col).values.astype(np.int64)
    for nm, cn in (('HI', 'high'), ('LO', 'low'), ('CL', 'close'), ('QV', 'qv')):
        a = np.full((NH, ns), np.nan)
        a[k, c] = px[cn].values
        A[nm] = a
    del px
    S = CB.load_b0('sim')
    G = S.load_sibling('sig').dense_from_sig(C3.W)
    assert G['syms'] == syms
    A['ZOI'], A['ZF'], A['F'], A['ZR'], A['U'] = G['z_oi'], G['z_f'], G['f'], G['z_r'], G['u']
    del G
    A['HAS'] = np.load(C3.B1WORK + '/hourly.npz')['has1m']
    X = np.full((NH, ns), np.nan)
    tsr = np.full((NH, ns), -1, dtype=np.int64)
    for ym in CB.ym_list():
        d = pd.read_parquet('%s/oi_%s.parquet' % (C3.L1WORK, ym))
        d['sym'] = d['sym'].astype(str)
        d = d[d['sym'].isin(col) & (d['h'] >= C3.H0) & (d['h'] < C3.CUT)]
        r = ((d['h'].values - C3.H0) // C3.H).astype(np.int64)
        cc = d['sym'].map(col).values.astype(np.int64)
        t = d['tsr'].values
        assert (t <= d['h'].values - 10 * 60000).all()
        o = np.argsort(t, kind='mergesort')
        X[r[o], cc[o]] = d['x'].values[o]          # latest tsr wins
        tsr[r[o], cc[o]] = t[o]
    A['X'] = X
    MK = C3.b2('mkt')
    parts = []
    for ym in CB.ym_list():
        d = pd.read_parquet(MK.HR % ym, columns=['sym', 'h', 'clast'])
        assert len(d) == 0 or int(d['h'].max()) + C3.H <= C3.CUT
        d['sym'] = d['sym'].astype(str)
        d = d[d['sym'].isin(col)]
        parts.append((d['sym'].map(col).values.astype(np.int64), d['h'].values.astype(np.int64), d['clast'].values))
    A['CC'] = MK.cc_from_hr(np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts]),
                            np.concatenate([p[2] for p in parts]), C3.H0, NH, ns)
    z = np.load(C3.B2WORK + '/mkt.npz')
    A['AGE'] = z['AGE']
    A['_mkt_ref'] = {kk: z[kk] for kk in ('EW3', 'EW7', 'EW14', 'BTC7', 'BTC20')}
    return A


# ---------------------------------------------------------------- pure feature code (works on any time slice; tested)
def _g(M, ks, cs, lag):
    i = ks - lag
    ok = i >= 0
    out = np.full(len(ks), np.nan)
    out[ok] = M[i[ok], cs[ok]]
    return out


def _win(M, ks, cs, n):
    """(N, n) values M[k - n + 1 .. k, c] (NaN before row 0)."""
    lags = np.arange(n - 1, -1, -1)
    i = ks[:, None] - lags[None, :]
    ok = i >= 0
    out = np.full(i.shape, np.nan)
    cc = np.broadcast_to(cs[:, None], i.shape)
    out[ok] = M[i[ok], cc[ok]]
    return out


def _std_min(a, n):
    fin = np.isfinite(a)
    cnt = fin.sum(axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        mu = np.where(fin, a, 0.0).sum(axis=1) / np.maximum(cnt, 1)
        v = np.where(fin, (a - mu[:, None]) ** 2, 0.0).sum(axis=1) / np.maximum(cnt - 1, 1)
    return np.where(cnt >= max(2, int(np.ceil(MINFRAC * n))), np.sqrt(v), np.nan)


def _logret_win(CL, ks, cs, n):
    w = _win(CL, ks, cs, n + 1)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.log(w[:, 1:] / w[:, :-1])


def masks(A):
    with np.errstate(invalid='ignore'):
        cond15 = A['U'] & (A['ZOI'] >= C3.ZMIN) & (A['ZF'] >= C3.ZMIN) & (A['F'] > F_MIN)
        lev = A['U'] & (A['ZOI'] >= C3.ZLEV) & (A['ZF'] >= C3.ZLEV) & (A['F'] > F_MIN)
    return cond15, cond15 & A['HAS'], lev


def run_length(b):
    out = np.zeros(b.shape, dtype=np.int64)
    prev = np.zeros(b.shape[1], dtype=np.int64)
    for i in range(b.shape[0]):
        prev = np.where(b[i], prev + 1, 0)
        out[i] = prev
    return out


def features(A, ks, cs):
    """A: dict of time-indexed arrays (rows = hours, possibly a slice starting at absolute hour A['off']); ks: row index in A
    (relative), cs: coin index. Returns DataFrame with columns ALL."""
    ks = np.asarray(ks, dtype=np.int64)
    cs = np.asarray(cs, dtype=np.int64)
    CL, HI, LO, QV = A['CL'], A['HI'], A['LO'], A['QV']
    o = {}
    o['z_oi'] = A['ZOI'][ks, cs]
    o['z_f'] = A['ZF'][ks, cs]
    o['s'] = np.fmin(o['z_oi'], o['z_f'])
    o['zdiff'] = o['z_oi'] - o['z_f']
    o['f'] = A['F'][ks, cs]
    o['z_r'] = A['ZR'][ks, cs]
    c0 = CL[ks, cs]
    with np.errstate(invalid='ignore', divide='ignore'):
        for n in (1, 4, 24, 72, 168):
            o['lr%d' % n] = np.log(c0 / _g(CL, ks, cs, n))
        o['rv24'] = _std_min(_logret_win(CL, ks, cs, 24), 24)
        o['rv168'] = _std_min(_logret_win(CL, ks, cs, 168), 168)
        h24, l24 = _win(HI, ks, cs, 24), _win(LO, ks, cs, 24)
        ok24 = np.isfinite(h24).sum(axis=1) >= MINFRAC * 24
        o['rng24'] = np.where(ok24, (np.nanmax(np.where(np.isfinite(h24), h24, -np.inf), axis=1)
                                     - np.nanmin(np.where(np.isfinite(l24), l24, np.inf), axis=1)) / c0, np.nan)
        h168, l168 = _win(HI, ks, cs, 168), _win(LO, ks, cs, 168)
        ok168 = np.isfinite(h168).sum(axis=1) >= MINFRAC * 168
        o['dhi168'] = np.where(ok168, c0 / np.max(np.where(np.isfinite(h168), h168, -np.inf), axis=1) - 1.0, np.nan)
        o['dlo168'] = np.where(ok168, c0 / np.min(np.where(np.isfinite(l168), l168, np.inf), axis=1) - 1.0, np.nan)
        q24 = _win(QV, ks, cs, 24)
        q168 = _win(QV, ks, cs, 168)
        s24 = np.where(np.isfinite(q24).sum(axis=1) >= MINFRAC * 24, np.nansum(q24, axis=1), np.nan)
        s168 = np.where(np.isfinite(q168).sum(axis=1) >= MINFRAC * 168, np.nansum(q168, axis=1), np.nan)
        o['lqv24'] = np.where(s24 > 0, np.log(s24), np.nan)
        o['qvratio'] = np.where(s168 > 0, s24 / (s168 / 7.0), np.nan)
    # liquidity rank: cross-sectional percentile of 168 h quote volume among U coins at k
    qz = np.where(np.isfinite(QV), QV, 0.0)
    qn = np.isfinite(QV).astype(np.int64)
    cq = np.vstack([np.zeros((1, QV.shape[1])), np.cumsum(qz, axis=0)])
    cn = np.vstack([np.zeros((1, QV.shape[1]), dtype=np.int64), np.cumsum(qn, axis=0)])
    uk, inv = np.unique(ks, return_inverse=True)
    lo = np.maximum(uk - 167, 0)
    s7 = cq[uk + 1] - cq[lo]
    n7 = cn[uk + 1] - cn[lo]
    s7 = np.where((n7 >= MINFRAC * 168) & A['U'][uk], s7, np.nan)
    rk = np.full(len(ks), np.nan)
    for i in range(len(uk)):
        row = s7[i]
        fin = np.isfinite(row)
        nf = int(fin.sum())
        sel = np.flatnonzero(inv == i)
        if nf < 2:
            continue
        v = row[cs[sel]]
        srt = np.sort(row[fin])
        r = (np.searchsorted(srt, v, 'left') + np.searchsorted(srt, v, 'right') - 1) / 2.0 / (nf - 1)
        rk[sel] = np.where(np.isfinite(v), r, np.nan)
    o['liqrank'] = rk
    day = (A['off'] + ks) // 24
    ag = A['AGE'][day, cs].astype(np.float64)
    o['age'] = np.where(ag >= 0, np.minimum(ag, AGE_CAP), np.nan)
    cond15, poolm, lev = masks(A)
    o['levrun'] = run_length(lev)[ks, cs].astype(np.float64)
    cp = np.vstack([np.zeros((1, poolm.shape[1]), dtype=np.int64), np.cumsum(poolm, axis=0)])
    o['ncand7d'] = (cp[ks, cs] - cp[np.maximum(ks - 168, 0), cs]).astype(np.float64)
    o['doi24'] = A['X'][ks, cs] - _g(A['X'], ks, cs, 24)
    o['doi72'] = A['X'][ks, cs] - _g(A['X'], ks, cs, 72)
    o['df24'] = o['f'] - _g(A['F'], ks, cs, 24)
    MK = C3.b2('mkt')
    for n in (3, 7, 14):
        o['ew%d' % n] = MK.ewr(A['CC'], A['U'], n)[0][ks]
    cb = A['CC'][:, A['ib']]
    for n in (7, 20):
        o['btc%d' % n] = MK.btcdev(cb, n)[ks]
    bcl = A['CL'][:, [A['ib']]]
    lrb = _logret_win(bcl, ks, np.zeros(len(ks), dtype=np.int64), 168)
    o['btcvol7'] = _std_min(lrb, 168)
    nu = A['U'].sum(axis=1).astype(np.float64)
    with np.errstate(invalid='ignore', divide='ignore'):
        o['frac_lev'] = np.where(nu > 0, lev.sum(axis=1) / nu, np.nan)[ks]
        o['frac_pool'] = np.where(nu > 0, cond15.sum(axis=1) / nu, np.nan)[ks]
    o['ncand_hour'] = poolm.sum(axis=1).astype(np.float64)[ks]
    df = pd.DataFrame({kk: np.asarray(o[kk], dtype=np.float64) for kk in ALL})
    return df


def slice_raw(A, a, b):
    """rows [a, b) of every time-indexed array; AGE (daily) kept whole (absolute day index via off)."""
    B = {kk: (v[a:b] if kk in TIME_KEYS else v) for kk, v in A.items() if not kk.startswith('_')}
    B['off'] = A['off'] + a
    return B


def build():
    t0 = time.time()
    A = load_raw()
    log.info('raw loaded %.1fs', time.time() - t0)
    P = dict(np.load(C3.WORK + '/pool_b3.npz'))
    cond15, poolm, lev = masks(A)
    pk, pc = np.nonzero(poolm)
    code = np.sort(pk * 10000 + pc)
    assert np.array_equal(code, np.sort(P['k'] * 10000 + P['c'])), 'pool mask != pool'
    MK = C3.b2('mkt')
    reg = {}
    for n in (3, 7, 14):
        reg['EW%d' % n] = bool(np.array_equal(MK.ewr(A['CC'], A['U'], n)[0], A['_mkt_ref']['EW%d' % n], equal_nan=True))
    for n in (7, 20):
        reg['BTC%d' % n] = bool(np.array_equal(MK.btcdev(A['CC'][:, A['ib']], n), A['_mkt_ref']['BTC%d' % n], equal_nan=True))
    assert all(reg.values()), reg
    df = features(A, P['k'], P['c'])
    df.insert(0, 'k', P['k'])
    df.insert(1, 'c', P['c'])
    dropped = [f for f in ALL if not np.isfinite(df[f]).any()]
    df.to_parquet(FEAT, index=False)
    rep = dict(n=int(len(df)), features=ALL, n_features=len(ALL), dropped=dropped, dropped_reason='all NaN' if dropped else None,
               nan_frac={f: float((~np.isfinite(df[f])).mean()) for f in ALL}, mkt_regression_b2=reg, sec=time.time() - t0,
               not_built=[])
    with open(C3.OUT + '/feat_b3.json', 'w') as fh:
        json.dump(rep, fh, indent=1)
    log.info('features n=%d nfeat=%d dropped=%s %.1fs', len(df), len(ALL), dropped, time.time() - t0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'build': build}[sys.argv[1]]()
