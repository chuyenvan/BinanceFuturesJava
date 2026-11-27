"""LEVZ B4 FAKE data (synthetic candidates + 1-minute paths) for end-to-end tests of grid / select / report. NO real data read.
kinds: 'pump' = every trade pumps +11..14 % in 10 h then crashes to -12 % and bounces to -7 % (DCA kinds that fill all legs must beat NONE);
       'rand' = driftless random walk (no edge). Candidates: ncoin coins, one candidate every gap_h + U(0, 60) h (default 3 coins, 400 h: few trades so compounding stays small) over 2022-2025;
       score s ~ U(2.5, 5) => classes z 2.5 (all) / 3.0 / 3.5; STATE hour U(10, 200) for half of them, else none."""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_b4 as C
sys.path.pop(0)
import numpy as np

CB = C.CB


def candidates(seed, ncoin=3, gap_h=400):
    rng = np.random.default_rng(seed)
    ks, cs = [], []
    for c in range(ncoin):
        k = int(rng.integers(0, 100))
        while k < CB.NH - 2:
            ks.append(k)
            cs.append(c)
            k += gap_h + int(rng.integers(0, 60))
    ks, cs = np.array(ks, dtype=np.int64), np.array(cs, dtype=np.int64)
    o = np.lexsort((cs, ks))
    ks, cs = ks[o], cs[o]
    ss = rng.uniform(2.5, 5.0, len(ks))
    sth = np.where(rng.random(len(ks)) < 0.5, rng.integers(10, 200, len(ks)), C.BIG).astype(np.int64)
    return ks, cs, ss, sth


def pathfn(kind, seed):
    def f(i):
        r = np.random.default_rng(seed * 1000003 + int(i))
        fh = np.zeros(CB.HMAX + 1)
        fh[1:] = 1e-5
        if kind == 'rand':
            x = np.concatenate([[0.0], np.cumsum(r.normal(0.0, 0.001, CB.NPATH - 1))])
            p = 100.0 * np.exp(x)
        elif kind == 'pump':
            amp = r.uniform(0.11, 0.14)
            t = np.arange(CB.NPATH, dtype=np.float64)
            p = np.full(CB.NPATH, 93.0)
            up = t <= 600
            p[up] = 100.0 * (1.0 + amp * t[up] / 600.0)
            hold = (t > 600) & (t <= 660)
            p[hold] = 100.0 * (1.0 + amp)
            dn = (t > 660) & (t <= 1860)
            p[dn] = 100.0 * (1.0 + amp) + (88.0 - 100.0 * (1.0 + amp)) * (t[dn] - 660.0) / 1200.0
            bo = (t > 1860) & (t <= 1920)
            p[bo] = 88.0 + 5.0 * (t[bo] - 1860.0) / 60.0
            p = p * (1.0 + r.normal(0.0, 0.0003, CB.NPATH))
            p[0] = 100.0
        else:
            raise KeyError(kind)
        return p, CB.NPATH, C.BIG, np.zeros(CB.NPATH, dtype=bool), fh
    return f


def build(kind, seed, ncoin=3, gap_h=400):
    """-> (T, HK (with fc), cls {zmin: (k, c, s, row)})."""
    X = C.load('exits_b4')
    ks, cs, ss, sth = candidates(seed, ncoin, gap_h)
    T, HK = X.compute(None, ks, cs, sth, pathfn(kind, seed))
    for dn in HK:
        HK[dn]['fc'] = np.cumsum(HK[dn]['fh'], axis=1)
    rows = np.arange(len(ks))
    cls = {z: (ks[ss >= z], cs[ss >= z], ss[ss >= z], rows[ss >= z]) for z in C.ZS}
    return T, HK, cls
