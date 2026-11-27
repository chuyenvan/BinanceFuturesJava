"""LEVZ T2 FAKE data (tests f / g / h and the placebo bench): full calendar (NH hours, NMIN minutes, same fold dates), ns coins,
geometric random-walk 1m closes (float32, in RAM), no gaps, funding every 8 h, random-walk hourly log-OI, random STATE conditions,
candidates spaced >= 73 h per coin with nested zmin classes. plant=True: after EVERY signal the price rises linearly to +2.5 % over
2 h, holds 2 h, then falls to -5 % of p0 by hour 10 and stays (permanent level shift; small so the fake equity
stays < ~1e7 and the B0 accounting check (abs tol 1e-6) holds) => a limit sell at +2 % (EL_2) is better than
E0 and much better than a random minute in the 48 h window.
usage: python3 code/fake_t2.py bench   (placebo speed for one rep of real size: ~4 800 filled candidates; FAKE prices only)"""
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np

log = C.setup_log('fake')


class F:
    pass


def profile(n=C.NPATH):
    i = np.arange(n, dtype=np.float64)
    f = np.ones(n)
    f = np.where(i <= 120, 1.0 + 0.025 * i / 120.0, f)
    f = np.where((i > 120) & (i <= 240), 1.025, f)
    f = np.where((i > 240) & (i <= 600), 1.025 + (0.95 - 1.025) * (i - 240) / 360.0, f)
    f = np.where(i > 600, 0.95, f)
    return f


def make(seed=1, ns=30, ncand=4800, plant=False, vol=0.0006):
    rng = np.random.default_rng(seed)
    o = F()
    nmin, nh = C.NMIN, C.NH
    lr = rng.normal(0.0, vol, size=(ns, nmin)).astype(np.float32)
    mm = np.exp(np.cumsum(lr, axis=1, dtype=np.float64)).astype(np.float64) * 10.0
    del lr
    # candidates: per coin, hours spaced >= 73 h, in [200, nh - 50]
    per = int(np.ceil(ncand / ns))
    ks, cs = [], []
    for c in range(ns):
        span = (nh - 250) - 200
        gaps = rng.integers(73, max(74, 2 * span // per - 73), size=per)
        kk = 200 + np.cumsum(gaps)
        kk = kk[kk < nh - 50]
        ks.append(kk)
        cs.append(np.full(len(kk), c))
    k = np.concatenate(ks).astype(np.int64)
    c = np.concatenate(cs).astype(np.int64)
    o_ = np.lexsort((c, k))
    k, c = k[o_][:ncand], c[o_][:ncand]
    if plant:
        pf = profile()
        for kk, cc in zip(k, c):
            a = 60 * int(kk)
            b = min(a + C.NPATH, nmin)
            mm[cc, a:b] *= pf[:b - a]
            mm[cc, b:] *= pf[-1]
    o.mm = mm.astype(np.float32)
    del mm
    o.gaps = (np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0, np.int64))
    o.first = np.zeros(ns, dtype=np.int64)
    FR = np.zeros((nh, ns))
    FR[::8] = rng.normal(1e-4, 1e-4, size=FR[::8].shape)
    o.FR = FR
    o.X = 17.0 + np.cumsum(rng.normal(0.0, 0.02, size=(nh, ns)), axis=0)
    o.conds = {zo: rng.random((nh, ns)) < (0.03 if zo == 0.0 else 0.06) for zo in C.C1.STATE_Z}
    s = rng.uniform(2.5, 5.0, size=len(k))
    cid = np.arange(len(k), dtype=np.int64)
    o.cls = {z: (k[s >= z], c[s >= z], s[s >= z], cid[s >= z]) for z in C.ZS}
    o.uk, o.uc = k, c
    EN = C.load('entry_t2')
    XB1 = C.b1('exits')
    o.src = EN.Src(mm=o.mm, gaps=o.gaps, first=o.first, X=o.X)
    o.st = XB1.Store(mm=o.mm, gaps=o.gaps, FR=o.FR)
    o.en = EN.compute(o.src, k, c)
    o.en['cid_b1'] = cid
    return o


def tables(o, entries=C.ENTRIES):
    XT = C.load('exits_t2')
    out = {}
    for e in entries:
        idx, ms, cs, pxs = XT.entry_rows(o.en, e)
        t = XT.compute(o.st, ms, cs, pxs, o.conds)
        t['k'], t['cid_b1'], t['uidx'] = o.en['k'][idx], o.en['cid_b1'][idx], idx
        out[e] = t
    return out


def bench():
    t0 = time.time()
    o = make(seed=7, ns=30, ncand=4800)
    log.info('fake make %.1fs n=%d filled EL_1=%d', time.time() - t0, len(o.uk), int((o.en['EL_1_m'] >= 0).sum()))
    PL = C.load('placebo_t2')
    PL.setup(src=o.src, st=o.st, conds=o.conds, en=o.en, cls=o.cls)
    for e in ('EL_1', 'EO_3'):
        r = PL.one_rep('time', e, 0)
        log.info('bench placebo %s: n_used=%d exits %.1fs total %.1fs', e, r['n_used'], r['sec_exits'], r['sec_total'])


if __name__ == '__main__':
    {'bench': bench}[sys.argv[1]]()
