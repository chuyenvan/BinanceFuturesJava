"""LEVZ B1 step 1 - 1-minute price paths (PREREG_LEVZ_B1 sec 1, 2).
Storage (CHOICES_B1 #1): ONE dense per-coin memmap work/close1m.npy float32 [ns, NMIN] (minute j <-> bar open_time H0 + j*1m,
value = close, forward-filled; NaN before the first bar). The path of candidate (sym c, entry hour k) is the VIEW
close1m[c, 60k : 60k + 43201] (minute 0 = entry bar open_time T_k ... minute 43200 = T_k + 720 h), cut at NMIN (2025-12-31 23:59).
Missing runs: work/gaps.npz (c, g0, g1): minutes g0..g1-1 missing after the coin's first bar (g1 = NMIN if open-ended).
Hourly: work/hourly.npz: has1m[k, c] (bar with open_time T_k exists) and CLH[k, c] = close1m[c, 60k] (ffilled).
Candidates: work/cand_b1.npz: B0 candidates() (imported) for 12 classes with pxok = has1m; union (k, c) -> cid.
Reader asserts ts < 2026-01-01 (files 2021-12..2025-12 only).
usage: python3 code/paths.py build | cand"""
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
import pandas as pd
import pyarrow.parquet as pq

log = logging.getLogger('levz_b1.paths')
MM = CB.WORK + '/close1m.npy'


def read_month(ym, col):
    t = pq.read_table(CB.KL % ym, columns=['ts', 'sym', 'close'], filters=[('ts', '<', CB.CUT)])
    d = t.to_pandas()
    assert len(d) == 0 or int(d['ts'].max()) < CB.CUT, 'data >= 2026 loaded'
    d['sym'] = d['sym'].astype(str)
    n0 = len(d)
    d = d[d['sym'].isin(col)]
    ts = d['ts'].values.astype(np.int64)
    assert (ts % CB.M == 0).all() and (ts >= CB.H0).all()
    j = (ts - CB.H0) // CB.M
    c = d['sym'].map(col).values.astype(np.int64)
    v = d['close'].values.astype(np.float64)
    ok = np.isfinite(v) & (v > 0)
    return c[ok], j[ok], v[ok], n0 - len(d), int((~ok).sum())


def ffill_gaps(row):
    """row: float array (NaN = no bar). Returns (ffilled float32, gap starts, gap ends (exclusive), first bar minute or -1,
    present mask). Gaps = runs of missing minutes AFTER the first bar (open-ended run ends at len(row))."""
    pr = np.isfinite(row)
    z = np.zeros(0, dtype=np.int64)
    if not pr.any():
        return np.full(len(row), np.nan, dtype=np.float32), z, z, -1, pr
    ar = np.arange(len(row), dtype=np.int64)
    idx = np.maximum.accumulate(np.where(pr, ar, -1))
    f = int(np.flatnonzero(pr)[0])
    ff = np.where(idx >= 0, row[np.maximum(idx, 0)], np.nan).astype(np.float32)
    miss = ~pr[f:]
    dm = np.diff(np.concatenate([[0], miss.astype(np.int8), [0]]))
    st = np.flatnonzero(dm == 1).astype(np.int64) + f
    en = np.flatnonzero(dm == -1).astype(np.int64) + f
    return ff, st, en, f, pr


def build():
    m = CB.meta()
    syms = m['syms']
    ns = len(syms)
    col = {s: i for i, s in enumerate(syms)}
    est = ns * CB.NMIN * 4 / 1e9
    log.info('memmap estimate %.2f GB (ns=%d NMIN=%d)', est, ns, CB.NMIN)
    assert est < 8.0
    mm = np.lib.format.open_memmap(MM + '.tmp', mode='w+', dtype=np.float32, shape=(ns, CB.NMIN))
    for c in range(ns):
        mm[c] = np.nan
    dup_tot = 0
    for ym in CB.ym_list():
        t0 = time.time()
        c, j, v, nout, nbad = read_month(ym, col)
        key = c * CB.NMIN + j
        o = np.lexsort((np.arange(len(key)), key))
        ks = key[o]
        last = np.ones(len(ks), dtype=bool)
        last[:-1] = ks[1:] != ks[:-1]
        dup_tot += int((~last).sum())
        o = o[last]
        mm[c[o], j[o]] = v[o].astype(np.float32)
        log.info('%s rows=%d syms_out=%d bad=%d dup=%d %.1fs', ym, len(o), nout, nbad, int((~last).sum()), time.time() - t0)
    gc, g0, g1 = [], [], []
    has1m = np.zeros((CB.NH, ns), dtype=bool)
    clh = np.full((CB.NH, ns), np.nan, dtype=np.float32)
    first = np.full(ns, -1, dtype=np.int64)
    for c in range(ns):
        ff, st, en, f, pr = ffill_gaps(np.array(mm[c]))
        has1m[:, c] = pr[::60]
        if f < 0:
            continue
        first[c] = f
        mm[c] = ff
        clh[:, c] = ff[::60]
        if len(st):
            gc.append(np.full(len(st), c, dtype=np.int64))
            g0.append(st)
            g1.append(en)
    mm.flush()
    del mm
    os.replace(MM + '.tmp', MM)
    gc = np.concatenate(gc) if gc else np.zeros(0, np.int64)
    g0 = np.concatenate(g0) if g0 else np.zeros(0, np.int64)
    g1 = np.concatenate(g1) if g1 else np.zeros(0, np.int64)
    np.savez(CB.WORK + '/gaps.npz', c=gc, g0=g0, g1=g1, first=first)
    np.savez(CB.WORK + '/hourly.npz', has1m=has1m, CLH=clh)
    ln = g1 - g0
    log.info('build done dup=%d gaps=%d gaps>1440=%d coins_with_data=%d', dup_tot, len(g0), int((ln > CB.MISS_MIN).sum()),
             int((first >= 0).sum()))


def cand():
    S = CB.load_b0('sim')
    SG = S.load_sibling('sig')
    m = CB.meta()
    hz = np.load(CB.WORK + '/hourly.npz')
    has1m = hz['has1m']
    out = {}
    keys = []
    for W in (14, 7):
        G = SG.dense_from_sig(W)
        assert G['syms'] == m['syms']
        for E in ('E0', 'E1'):
            for z in (2.5, 3.0, 3.5):
                ck, cc, cs = S.candidates(G['z_oi'], G['z_f'], G['f'], G['z_r'], G['u'], has1m, E, z)
                key = 'W%d_%s_%.1f' % (W, E, z)
                out[key + '_k'], out[key + '_c'], out[key + '_s'] = ck, cc, cs
                keys.append(key)
                log.info('cand %s n=%d', key, len(ck))
        del G
    allk = np.concatenate([out[k + '_k'] for k in keys])
    allc = np.concatenate([out[k + '_c'] for k in keys])
    code = np.unique(allk * 10000 + allc)
    uk, uc = code // 10000, code % 10000
    out['U_k'], out['U_c'] = uk, uc
    for key in keys:
        out[key + '_cid'] = np.searchsorted(code, out[key + '_k'] * 10000 + out[key + '_c']).astype(np.int64)
    np.savez(CB.WORK + '/cand_b1.npz', **out)
    log.info('union cands=%d est hourly arrays %.1f MB', len(code), len(code) * 721 * 4 * 4 / 1e6)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'build': build, 'cand': cand}[sys.argv[1]]()
