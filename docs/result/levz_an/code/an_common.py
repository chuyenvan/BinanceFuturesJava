"""LEVZ-AN shared helpers (descriptive analysis only; read-only use of levz_b1 / levz2 / levz / p15_stab).
Every market-data reader asserts ts < 2026-01-01 UTC."""
import os
import sys
import json
import logging
import importlib.util
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

B1CODE = '/home/ubuntu/claude_master/w3/levz_b1/code'
AN = '/home/ubuntu/claude_master/w3/levz_an'
OUT = AN + '/out'
LEVZ_WORK = '/home/ubuntu/claude_master/w3/levz/work'
L2_WORK = '/home/ubuntu/claude_master/w3/levz2/work'
LONG_DIR = '/home/ubuntu/claude_master/w3/p15_stab/s2/k/%s'
LONG_RUNS = ('c0s42', 'c0s7', 'c0s123', 'c0s13')
CUT = 1767225600000
DEV0 = 1640995200000      # 2022-01-01 UTC
H0 = 1638316800000
H = 3600000
M = 60000
REF = (4107, 5204, 3550)
log = logging.getLogger('levz_an')


def setup_log(name):
    os.makedirs(AN + '/logs', exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler('%s/logs/%s.log' % (AN, name)), logging.StreamHandler()])


def _load(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def b1():
    """returns (CB, P, X) = levz_b1 common_b1, port, exits modules (imported by file path, read-only)."""
    sys.path.insert(0, B1CODE)
    CB = _load('common_b1', B1CODE + '/common_b1.py')
    sys.path.pop(0)
    P = CB.load('port')
    X = CB.load('exits')
    return CB, P, X


def meta():
    with open(L2_WORK + '/sig_meta.json') as fh:
        m = json.load(fh)
    assert int(m['H0']) == H0
    return m


def family(n=50):
    g = pd.read_parquet('/home/ubuntu/claude_master/w3/levz_b1/out/grid_b1_scored.parquet')
    v = g[g['valid'].astype(bool)].sort_values(['score', 'cfg_id'], ascending=[False, True])
    return g, v.head(n)['cfg_id'].astype(int).tolist()


def dev_k():
    k0 = (DEV0 - H0) // H
    kl = (CUT - H0) // H - 1
    return int(k0), int(kl)


def dense_sig(W, syms):
    d = pd.read_parquet('%s/sig_W%d.parquet' % (L2_WORK, W))
    assert int(d['t'].max()) < CUT
    NH = (CUT - H0) // H
    col = {s: i for i, s in enumerate(syms)}
    r = ((d['t'].values - H0) // H).astype(np.int64)
    c = d['sym'].map(col).values.astype(np.int64)
    out = {}
    for kk in ('z_oi', 'z_f', 'f'):
        a = np.full((NH, len(syms)), np.nan, dtype=np.float32)
        a[r, c] = d[kk].values
        out[kk] = a
    u = np.zeros((NH, len(syms)), dtype=bool)
    u[r, c] = d['u'].values
    out['u'] = u
    return out


def dense_oi(syms):
    NH = (CUT - H0) // H
    col = {s: i for i, s in enumerate(syms)}
    X = np.full((NH, len(syms)), np.nan, dtype=np.float64)
    tsr = np.full((NH, len(syms)), -1, dtype=np.int64)
    y, mo = 2021, 12
    while (y, mo) <= (2025, 12):
        d = pd.read_parquet('%s/oi_%04d-%02d.parquet' % (LEVZ_WORK, y, mo))
        d = d[d['h'] < CUT]
        assert len(d) == 0 or int(d['h'].max()) < CUT and int(d['tsr'].max()) < CUT
        d = d[d['sym'].astype(str).isin(col) & (d['h'] >= H0)]
        r = ((d['h'].values - H0) // H).astype(np.int64)
        c = d['sym'].astype(str).map(col).values.astype(np.int64)
        t = d['tsr'].values
        m = t > tsr[r, c]
        X[r[m], c[m]] = d['x'].values[m]
        tsr[r[m], c[m]] = t[m]
        mo += 1
        if mo == 13:
            y, mo = y + 1, 1
    return X


def dense_qv30(syms):
    """qv30[k, c] = mean daily quote volume over 1h bars with open in [T_k - 720h, T_k - 1h] (all closed before T_k)."""
    NH = (CUT - H0) // H
    col = {s: i for i, s in enumerate(syms)}
    d = pd.read_parquet(L2_WORK + '/px_1h.parquet', columns=['sym', 't', 'qv'])
    d = d[d['t'] < CUT]
    assert int(d['t'].max()) < CUT
    d = d[d['sym'].astype(str).isin(col) & (d['t'] >= H0)]
    r = ((d['t'].values - H0) // H).astype(np.int64)
    c = d['sym'].astype(str).map(col).values.astype(np.int64)
    Q = np.zeros((NH, len(syms)), dtype=np.float64)
    Q[r, c] = np.nan_to_num(d['qv'].values)
    C = np.zeros((NH + 1, len(syms)))
    C[1:] = np.cumsum(Q, axis=0)
    out = np.full((NH, len(syms)), np.nan, dtype=np.float32)
    k = np.arange(720, NH)
    out[720:] = ((C[k] - C[k - 720]) / 30.0).astype(np.float32)
    return out


def market(CLH, has1m, u, syms):
    """btc7[k], ew7[k]: 7-day return up to the entry close CLH[k] (close of 1m bar open T_k); ew = equal-weight mean over
    universe coins (excl. BTC) with 1m bars at k and k-168."""
    NH = CLH.shape[0]
    b = syms.index('BTCUSDT')
    btc7 = np.full(NH, np.nan)
    ew7 = np.full(NH, np.nan)
    btc7[168:] = CLH[168:, b] / CLH[:-168, b] - 1.0
    ok = has1m[168:] & has1m[:-168] & u[168:]
    ok[:, b] = False
    with np.errstate(invalid='ignore', divide='ignore'):
        rr = np.where(ok, CLH[168:] / CLH[:-168] - 1.0, np.nan)
    ew7[168:] = np.nanmean(rr, axis=1)
    return btc7, ew7


def dts(ms):
    return pd.to_datetime(np.asarray(ms, dtype=np.int64), unit='ms', utc=True)
