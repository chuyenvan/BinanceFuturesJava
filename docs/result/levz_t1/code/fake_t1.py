"""LEVZ T1 synthetic data (FAKE paths) for tests (c)(e)(f)(g): no real price / signal is read. Geometric random walk 1m closes for
NS coins over the full B1 minute axis (float32), random funding, random W7-like signals, random candidates per (zmin) class.
Coins 0 / 1 play BTC / ETH for the hedge legs."""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t1 as C
sys.path.pop(0)
import numpy as np

CB = C.CB


class Fake:
    pass


def make(ns=10, ncand=900, seed=7, nmin=None):
    rng = np.random.default_rng(seed)
    nmin = nmin or CB.NMIN
    F = Fake()
    lr = rng.normal(0.0, 0.0012, size=(ns, nmin)).astype(np.float32)
    lr[:, :] += (rng.normal(0, 0.00002, size=(ns, 1))).astype(np.float32)
    mm = (100.0 * np.exp(np.cumsum(lr, axis=1, dtype=np.float64))).astype(np.float32)
    # a missing run > 24 h on coin 5 (ffilled), registered as a gap
    g0, g1 = 900000, 900000 + 2000
    mm[5, g0:g1] = mm[5, g0 - 1]
    F.mm = mm
    F.gaps = (np.array([5]), np.array([g0]), np.array([g1]))
    nh = CB.NH
    F.FR = rng.normal(0.0001, 0.0002, size=(nh, ns)) * (rng.random((nh, ns)) < 0.125)
    x = mm[:, 59::60].T.astype(np.float64)              # close of the bar ending at T_{k+1}
    F.CL = np.full((nh, ns), np.nan, dtype=np.float32)
    F.CL[1:] = x[:nh - 1]
    F.sig = {kk: rng.normal(1.5, 1.5, size=(nh, ns)) for kk in ('z_oi', 'z_f')}
    F.sig['f'] = rng.normal(0.0003, 0.0003, size=(nh, ns))
    F.sig['z_oi'][rng.random((nh, ns)) < 0.01] = np.nan
    k0 = (1640995200000 - CB.H0) // CB.H                 # 2022-01-01
    kmax = nh - 800
    ks = np.sort(rng.integers(k0 - 200, kmax, size=ncand))
    cs = rng.integers(2, ns, size=ncand)
    key = np.unique(ks * 1000 + cs)
    F.U_k, F.U_c = (key // 1000).astype(np.int64), (key % 1000).astype(np.int64)
    n = len(F.U_k)
    s = rng.uniform(2.5, 6.0, size=n)
    F.cz = {}
    for z in C.ZS:
        m = s >= z
        F.cz[z] = (F.U_k[m], F.U_c[m], s[m], np.flatnonzero(m).astype(np.int64))
    F.gate = rng.random(nh) < 0.5                       # stand-in for G_EW14 open hours
    return F
