"""LEVZ B2 step 2 - the 12 SINGLE options (PREREG_LEVZ_B2 sec 2) as masks on the B1 candidate set (work/cand_b1.npz of levz_b1).
A mask only removes NEW-entry candidates (k, c); open positions are never touched (the B1 portfolio layer is unchanged).
Conditions are evaluated at the candidate's ENTRY hour k (E0: the LEV hour; E1: the z_r trigger hour t1 = entry hour) with the
series of mkt.py (value at k uses candles closed <= T_k). Missing data (NaN) => condition False => candidate NOT accepted.
GATE  : G_EW3 EW3 <= 0 | G_EW7 EW7 <= 0 | G_EW14 EW14 <= 0 | G_BTC7 BTC7 <= 0 | G_BTC20 BTC20 <= 0 | G_BRhi BR >= BRmed | G_BRlo BR < BRmed
FILTER: F_LIQ50 qv30 >= 50e6 | F_AGE90 age >= 90 d | F_NOPUMP r24 < 0.20 | F_PUMP r24 >= 0.10 | F_FHI f >= 0.0003
NONE  : accept everything (identity check vs B1).
Placebo (sec 4e): GATE -> circular shift of the hourly gate series by d hours, d ~ U{720 .. NH-720} (>= 30 days both ways);
FILTER -> per calendar month m, a random permutation pi_m of the coins in universe at any hour of m; candidate (k, c) gets the filter
value of (k, pi_m(c)) (per hour the number of passing coins in the month's set is unchanged); ADDENDUM1 B: a draw whose exclusion rate on
the candidate set (pooled over the 12 classes) deviates > 20 % (relative) from the real rate is discarded and redrawn (counted).
usage: python3 code/opts.py describe  -> out/describe_b2.json|md (block rates / gate-open rates, NO profit)"""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2c
sys.path.pop(0)
import json
import logging
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b2.opts')
H = 3600000
GATES = {'G_EW3': ('EW3', 'le0'), 'G_EW7': ('EW7', 'le0'), 'G_EW14': ('EW14', 'le0'), 'G_BTC7': ('BTC7', 'le0'),
         'G_BTC20': ('BTC20', 'le0'), 'G_BRhi': ('BR', 'ge_med'), 'G_BRlo': ('BR', 'lt_med')}
FILTERS = ('F_LIQ50', 'F_AGE90', 'F_NOPUMP', 'F_PUMP', 'F_FHI')
OPTS = tuple(GATES) + FILTERS
assert len(OPTS) == 12
ALL = ('NONE',) + OPTS
LIQ = 50e6
AGE = 90
NOPUMP = 0.20
PUMP = 0.10
FHI = 0.0003
SHIFT_MIN = 720
CLASSES = [(W, E, z) for W in (14, 7) for E in ('E0', 'E1') for z in (2.5, 3.0, 3.5)]


def kind(name):
    return 'none' if name == 'NONE' else ('gate' if name in GATES else 'filter')


def gate_series(name, mk):
    v, op = GATES[name]
    x = mk[v]
    with np.errstate(invalid='ignore'):
        if op == 'le0':
            g = x <= 0.0
        elif op == 'ge_med':
            g = x >= mk['BRmed']
        else:
            g = x < mk['BRmed']
    return np.asarray(g, dtype=bool) & np.isfinite(x) & (np.isfinite(mk['BRmed']) if op != 'le0' else True)


def filter_at(name, mk, k, c):
    k = np.asarray(k, dtype=np.int64)
    c = np.asarray(c, dtype=np.int64)
    d = k // 24
    with np.errstate(invalid='ignore'):
        if name == 'F_LIQ50':
            return mk['QV30'][d, c] >= LIQ
        if name == 'F_AGE90':
            return mk['AGE'][d, c] >= AGE
        if name == 'F_NOPUMP':
            return mk['R24'][k, c] < NOPUMP
        if name == 'F_PUMP':
            return mk['R24'][k, c] >= PUMP
        if name == 'F_FHI':
            return mk['F'][k, c] >= FHI
    raise KeyError(name)


def mask_at(name, mk, k, c, gate=None):
    k = np.asarray(k, dtype=np.int64)
    if name == 'NONE':
        return np.ones(len(k), dtype=bool)
    if name in GATES:
        g = gate_series(name, mk) if gate is None else gate
        return g[k]
    return filter_at(name, mk, k, c)


# ---------------------------------------------------------------- placebo transforms
def gate_shift(g, d):
    """g'[k] = g[(k - d) mod NH]"""
    return np.roll(np.asarray(g, dtype=bool), int(d))


def draw_shift(rng, nh, smin=SHIFT_MIN):
    return int(rng.integers(smin, nh - smin + 1))


def month_id(nh, h0):
    t = pd.to_datetime(h0 + np.arange(nh, dtype=np.int64) * H, unit='ms')
    ym = t.year.values * 12 + t.month.values - 1
    return (ym - ym[0]).astype(np.int64)


def coin_perm_map(U, mid, rng):
    """map[m, c] = pi_m(c) for c in S_m (coins in U at any hour of month m), identity otherwise."""
    nm = int(mid.max()) + 1
    ns = U.shape[1]
    mp = np.tile(np.arange(ns, dtype=np.int64), (nm, 1))
    for m in range(nm):
        rows = mid == m
        sm = np.flatnonzero(U[rows].any(axis=0))
        if len(sm) > 1:
            mp[m, sm] = sm[rng.permutation(len(sm))]
    return mp


PL_TOL = 0.20
PL_MAX_TRIES = 1000


def rate_ok(ex, real, tol=PL_TOL):
    """B2 ADDENDUM1 B: placebo exclusion rate on the candidate set must be within +-20 % (relative) of the real rate."""
    return abs(ex - real) <= tol * real


def draw_filter_perm(U, mid, rng, ex_fn, real, tol=PL_TOL, max_tries=PL_MAX_TRIES):
    """draw coin_perm_map until ex_fn(map) is within tol of real; returns (map, ex, n_redraw). Deterministic given rng."""
    for i in range(max_tries):
        mp = coin_perm_map(U, mid, rng)
        ex = ex_fn(mp)
        if rate_ok(ex, real, tol):
            return mp, ex, i
    raise RuntimeError('placebo filter: no permutation within tolerance after %d tries' % max_tries)


# ---------------------------------------------------------------- candidate classes
def class_key(W, E, z):
    return 'W%d_%s_%.1f' % (W, E, z)


def filtered_classes(cz, mask_fn, P):
    """cz: cand_b1.npz dict; mask_fn(k, c) -> bool; P: B1 port module. Returns {(W,E,z): CandB1}, {(W,E,z): (n_in, n_kept)}."""
    out, cnt = {}, {}
    for W, E, z in CLASSES:
        key = class_key(W, E, z)
        ck, cc, cs, cid = cz[key + '_k'], cz[key + '_c'], cz[key + '_s'], cz[key + '_cid']
        m = np.asarray(mask_fn(ck, cc), dtype=bool)
        assert m.shape == ck.shape
        out[(W, E, z)] = P.CandB1(ck[m], cc[m], cs[m], cid[m])
        cnt[(W, E, z)] = (int(len(ck)), int(m.sum()))
    return out, cnt


def load_cz():
    z = np.load('/home/ubuntu/claude_master/w3/levz_b1/work/cand_b1.npz')
    return {k: z[k] for k in z.files}


# ---------------------------------------------------------------- sec 7 description (no profit)
def describe():
    mkm = b2c.b2('mkt')
    mk = mkm.load()
    cz = load_cz()
    nh, h0 = int(mk['NH']), int(mk['H0'])
    yr_h = pd.to_datetime(h0 + np.arange(nh, dtype=np.int64) * H, unit='ms').year.values
    key = class_key(7, 'E0', 2.5)
    ck, cc = cz[key + '_k'], cz[key + '_c']
    yr_c = yr_h[ck]
    years = (2022, 2023, 2024, 2025)
    rep = dict(cls=key, n_cand={str(y): int((yr_c == y).sum()) for y in years}, opts={})
    for o in OPTS:
        m = mask_at(o, mk, ck, cc)
        r = dict(kind=kind(o), block_rate={str(y): float(1.0 - m[yr_c == y].mean()) if (yr_c == y).any() else None for y in years},
                 block_rate_2022_2025=float(1.0 - m[(yr_c >= 2022) & (yr_c <= 2025)].mean()))
        if o in GATES:
            g = gate_series(o, mk)
            r['gate_open'] = {str(y): float(g[yr_h == y].mean()) for y in years}
            v = mk[GATES[o][0]]
            r['nan_hours'] = {str(y): int((~np.isfinite(v[yr_h == y])).sum()) for y in years}
        rep['opts'][o] = r
    # data coverage notes
    rep['coverage'] = dict(
        EWN3_min_2022_2025=int(mk['EWN3'][yr_h >= 2022].min()), NU_min_2022_2025=int(mk['NU'][yr_h >= 2022].min()),
        BR_first_finite=str(pd.Timestamp(h0 + int(np.flatnonzero(np.isfinite(mk['BR']))[0]) * H, unit='ms')),
        BRmed_first_finite=str(pd.Timestamp(h0 + int(np.flatnonzero(np.isfinite(mk['BRmed']))[0]) * H, unit='ms')),
        cand_nan={nm: float(np.mean(~np.isfinite(a))) for nm, a in (
            ('R24', mk['R24'][ck, cc]), ('F', mk['F'][ck, cc]), ('QV30', mk['QV30'][ck // 24, cc]))},
        cand_age_unknown=float(np.mean(mk['AGE'][ck // 24, cc] < 0)))
    with open(b2c.OUT + '/describe_b2.json', 'w') as fh:
        json.dump(rep, fh, indent=1)
    L = ['# describe_b2 - ti le chan / ti le gate mo theo nam (KHONG loi nhuan). Lop %s; so ung vien: %s' % (key, rep['n_cand']), '',
         '| phuong an | chan 2022 | 2023 | 2024 | 2025 | gate mo 2022 | 2023 | 2024 | 2025 |', '|---|---|---|---|---|---|---|---|---|']
    for o in OPTS:
        r = rep['opts'][o]
        b = ['%.3f' % r['block_rate'][str(y)] for y in years]
        go = ['%.3f' % r['gate_open'][str(y)] for y in years] if 'gate_open' in r else ['-'] * 4
        L.append('| %s | %s | %s |' % (o, ' | '.join(b), ' | '.join(go)))
    L += ['', 'coverage: ' + json.dumps(rep['coverage'])]
    with open(b2c.OUT + '/describe_b2.md', 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    log.info('describe done')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'describe': describe}[sys.argv[1]]()
