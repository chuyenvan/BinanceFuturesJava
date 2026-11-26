"""LEVZ B2 tests: synthetic hand-computed cases for every series / option / placebo transform + a few real-data checks
(independent loop re-computation of mkt series at random hours, NONE == B1 classes, F2-only routine == grid_b1 F2_ret).
usage: python3 test/test_b2.py  -> test/test_report.json (exit 1 on any failure)"""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/home/ubuntu/claude_master/w3/levz_b2/code')
import b2c
sys.path.pop(0)
import json
import logging
import traceback
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b2.test')
MK = b2c.b2('mkt')
O = b2c.b2('opts')
H = 3600000
NAN = np.nan
TESTS = []


def t(fn):
    TESTS.append(fn)
    return fn


def close(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.all((np.abs(a - b) <= 1e-12) | (np.isnan(a) & np.isnan(b))))


# ------------------------------------------------------------ mkt
@t
def cc_maps_closed_candle():
    h0 = 0
    cc = MK.cc_from_hr([0, 0, 1], [0 * H, 1 * H, 1 * H], [10.0, 11.0, 5.0], h0, 4, 2)
    assert np.isnan(cc[0]).all()
    assert cc[1, 0] == 10.0 and cc[2, 0] == 11.0 and cc[2, 1] == 5.0 and np.isnan(cc[1, 1])


@t
def cc_forming_candle_not_used():
    a = MK.cc_from_hr([0, 0], [0, H], [10.0, 11.0], 0, 4, 1)
    b = MK.cc_from_hr([0, 0], [0, H], [10.0, 999.0], 0, 4, 1)   # candle opening at T_1 changes
    assert a[1, 0] == b[1, 0] == 10.0      # value at k = 1 unchanged


@t
def cc_drops_last_open_candle_and_nan():
    cc = MK.cc_from_hr([0, 0], [2 * H, 3 * H], [7.0, NAN], 0, 4, 1)
    assert cc[3, 0] == 7.0 and np.isfinite(cc).sum() == 1   # h = T_3 -> k = 4 = NH dropped


@t
def ewr_hand():
    cc = np.array([[1.0, 2.0], [2.0, 2.0], [1.5, 4.0], [3.0, 1.0]])
    U = np.ones((4, 2), dtype=bool)
    ew, n = MK.ewr(cc, U, 2, hpd=1)
    assert close(ew, [NAN, NAN, (0.5 + 1.0) / 2, (0.5 - 0.5) / 2]) and list(n) == [0, 0, 2, 2]


@t
def ewr_universe_only():
    cc = np.array([[1.0, 2.0], [2.0, 2.0], [1.5, 4.0]])
    U = np.array([[1, 1], [1, 1], [1, 0]], dtype=bool)
    ew, n = MK.ewr(cc, U, 2, hpd=1)
    assert close(ew[2], 0.5) and n[2] == 1


@t
def ewr_missing():
    cc = np.array([[1.0, NAN], [2.0, 2.0], [NAN, 4.0]])
    U = np.ones((3, 2), dtype=bool)
    ew, n = MK.ewr(cc, U, 2, hpd=1)
    assert np.isnan(ew[2]) and n[2] == 0


@t
def ewr_causal():
    rng = np.random.default_rng(1)
    cc = rng.uniform(1, 2, (40, 5))
    U = rng.uniform(size=(40, 5)) > 0.3
    a, _ = MK.ewr(cc, U, 3, hpd=2)
    cc2 = cc.copy()
    cc2[21:] *= 3.0
    U2 = U.copy()
    U2[21:] = ~U2[21:]
    b, _ = MK.ewr(cc2, U2, 3, hpd=2)
    assert close(a[:21], b[:21]) and not close(a[21:], b[21:])


@t
def btcdev_hand():
    cb = np.array([1.0, 2.0, 3.0, 4.0, 6.0])
    d = MK.btcdev(cb, 2, hpd=1)     # mean of the 2 previous closes
    assert close(d, [NAN, NAN, 3.0 / 1.5 - 1, 4.0 / 2.5 - 1, 6.0 / 3.5 - 1])


@t
def btcdev_excludes_t():
    cb = np.array([1.0, 2.0, 3.0, 4.0])
    cb2 = cb.copy()
    cb2[3] = 8.0
    a, b = MK.btcdev(cb, 2, hpd=1), MK.btcdev(cb2, 2, hpd=1)
    assert close((a[3] + 1) * 2, b[3] + 1)       # denominator unchanged by cb[t]


@t
def btcdev_needs_all():
    cb = np.array([1.0, NAN, 3.0, 4.0, 5.0])
    d = MK.btcdev(cb, 2, hpd=1)
    assert np.isnan(d[1]) and np.isnan(d[2]) and np.isnan(d[3]) and close(d[4], 5.0 / 3.5 - 1)


@t
def btcdev_causal():
    rng = np.random.default_rng(2)
    cb = rng.uniform(1, 2, 60)
    cb2 = cb.copy()
    cb2[31:] = 9.0
    assert close(MK.btcdev(cb, 3, hpd=4)[:31], MK.btcdev(cb2, 3, hpd=4)[:31])


@t
def lev_thresholds():
    zo = np.array([[2.5, 2.4, NAN, 3.0, 3.0]])
    zf = np.array([[2.5, 3.0, 3.0, NAN, 3.0]])
    f = np.array([[0.0002, 0.0002, 0.0002, 0.0002, 0.0001]])
    assert MK.lev_mat(zo, zf, f).tolist() == [[True, False, False, False, False]]


@t
def win_any_hand():
    b = np.array([[0], [1], [0], [0], [0]], dtype=bool)
    assert MK.win_any(b, 3)[:, 0].tolist() == [False, True, True, True, False]


@t
def br_hand():
    lev = np.zeros((6, 3), dtype=bool)
    lev[1, 0] = True
    lev[4, 1] = True
    U = np.ones((6, 3), dtype=bool)
    U[5, 2] = False
    zok = np.ones((6, 3), dtype=bool)
    b, cov = MK.br(lev, U, zok, win=3, covmin=0.5)
    # k=2: window 0..2 -> coin0 -> 1/3; k=3: window 1..3 -> 1/3; k=4: window 2..4 -> coin1 -> 1/3; k=5: U={0,1}, coin1 -> 1/2
    assert close(b, [NAN, NAN, 1 / 3, 1 / 3, 1 / 3, 1 / 2])


@t
def br_includes_t_excludes_old():
    lev = np.zeros((5, 1), dtype=bool)
    lev[4, 0] = True
    U = np.ones((5, 1), dtype=bool)
    b, _ = MK.br(lev, U, np.ones((5, 1), dtype=bool), win=2)
    assert close(b, [NAN, 0.0, 0.0, 0.0, 1.0])
    lev2 = np.zeros((5, 1), dtype=bool)
    lev2[1, 0] = True
    b2, _ = MK.br(lev2, U, np.ones((5, 1), dtype=bool), win=2)
    assert close(b2, [NAN, 1.0, 1.0, 0.0, 0.0])


@t
def br_nan_rules():
    lev = np.ones((7, 2), dtype=bool)
    U = np.ones((7, 2), dtype=bool)
    U[3] = False                          # no universe coin at k=3 -> NaN at 3 and in windows containing 3
    zok = np.ones((7, 2), dtype=bool)
    zok[1, :] = False                     # coverage 0 at k=1 -> windows containing 1 are NaN
    b, cov = MK.br(lev, U, zok, win=2)
    assert np.isnan(b[:5]).all() and close(b[5:], [1.0, 1.0])
    zok2 = np.ones((7, 2), dtype=bool)
    zok2[6, 0] = False                    # coverage 0.5 >= 0.5 -> still valid
    b2, _ = MK.br(lev, np.ones((7, 2), dtype=bool), zok2, win=2)
    assert close(b2[1:], np.ones(6)) and np.isnan(b2[0])


@t
def br_causal():
    rng = np.random.default_rng(3)
    lev = rng.uniform(size=(50, 6)) > 0.8
    U = rng.uniform(size=(50, 6)) > 0.2
    zok = np.ones((50, 6), dtype=bool)
    a, _ = MK.br(lev, U, zok, win=5)
    lev2, U2 = lev.copy(), U.copy()
    lev2[30:] = ~lev2[30:]
    U2[30:] = True
    b, _ = MK.br(lev2, U2, zok, win=5)
    assert close(a[:30], b[:30])


@t
def brmed_hand_fix():
    b = np.array([1.0, 3.0, 2.0, 10.0, NAN, 5.0, NAN, NAN])
    m = MK.brmed(b, win=3, frac=0.6)
    assert close(m[3:], [2.0, 3.0, 6.0, 7.5, NAN])


@t
def brmed_causal_excludes_t():
    rng = np.random.default_rng(4)
    b = rng.uniform(size=40)
    b2 = b.copy()
    b2[20:] = 100.0
    assert close(MK.brmed(b, win=6, frac=0.8)[:21], MK.brmed(b2, win=6, frac=0.8)[:21])


@t
def r24_hand_causal():
    cc = np.arange(1.0, 31.0).reshape(30, 1)
    r = MK.lagret(cc, 24)
    assert np.isnan(r[:24]).all() and close(r[24, 0], 25.0 / 1.0 - 1) and close(r[29, 0], 30.0 / 6.0 - 1)
    cc2 = cc.copy()
    cc2[27:] = 0.5
    assert close(MK.lagret(cc2, 24)[:27], r[:27])


def _d1(days, qv, sym='AAAUSDT'):
    return pd.DataFrame({'sym': sym, 'day': pd.to_datetime(days), 'qv': qv})


@t
def qv30_hand():
    days = pd.date_range('2021-11-01', periods=40, freq='D')
    qv = np.arange(1.0, 41.0) * 1e6
    d1 = _d1(days, qv)
    day0 = int(pd.Timestamp('2021-12-01').value // 10**6)
    q, age = MK.qv30_age({'AAAUSDT': 0}, d1, day0, 12)
    # 2021-12-01 is day index 30 of the series -> mean of qv[0..29] = 15.5e6
    assert close(q[0, 0], 15.5e6) and close(q[1, 0], 16.5e6) and age[0, 0] == 30 and age[5, 0] == 35


@t
def qv30_missing_day_nan_and_causal():
    days = list(pd.date_range('2021-11-01', periods=60, freq='D'))
    del days[20]                                   # 2021-11-21 missing
    d1 = _d1(days, np.ones(59) * 1e6)
    day0 = int(pd.Timestamp('2021-12-01').value // 10**6)
    q, _ = MK.qv30_age({'AAAUSDT': 0}, d1, day0, 25)
    ok_j = [j for j in range(25) if np.isfinite(q[j, 0])]
    assert ok_j == list(range(21, 25))             # D valid iff D-30 > 2021-11-21  <=>  D >= 2021-12-22
    full = _d1(pd.date_range('2021-11-01', periods=60, freq='D'), np.arange(60) * 1e6)
    qa, _ = MK.qv30_age({'AAAUSDT': 0}, full, day0, 25)
    fb = full.copy()
    fb.loc[fb['day'] == pd.Timestamp('2021-12-05'), 'qv'] = 1e12
    qb, _ = MK.qv30_age({'AAAUSDT': 0}, fb, day0, 25)
    assert close(qa[:5, 0], qb[:5, 0]) and (qb[5:, 0] > qa[5:, 0]).all()   # day 4 (12-05) unaffected by its own qv


@t
def age_unknown_sym():
    d1 = _d1(pd.date_range('2021-11-01', periods=5, freq='D'), np.ones(5))
    day0 = int(pd.Timestamp('2021-12-01').value // 10**6)
    q, age = MK.qv30_age({'AAAUSDT': 0, 'BBBUSDT': 1}, d1, day0, 3)
    assert (age[:, 1] == -1).all() and np.isnan(q[:, 1]).all()


# ------------------------------------------------------------ opts
def _mk(nh=48, ns=3):
    mk = {k: np.full(nh, NAN) for k in ('EW3', 'EW7', 'EW14', 'BTC7', 'BTC20', 'BR', 'BRmed')}
    mk['R24'] = np.full((nh, ns), NAN)
    mk['F'] = np.full((nh, ns), NAN)
    mk['QV30'] = np.full((nh // 24, ns), NAN)
    mk['AGE'] = np.full((nh // 24, ns), -1, dtype=np.int32)
    return mk


@t
def gates_le0():
    mk = _mk()
    for v, o in (('EW3', 'G_EW3'), ('EW7', 'G_EW7'), ('EW14', 'G_EW14'), ('BTC7', 'G_BTC7'), ('BTC20', 'G_BTC20')):
        mk[v][:4] = [-0.1, 0.0, 1e-9, NAN]
        g = O.gate_series(o, mk)
        assert g[:4].tolist() == [True, True, False, False] and not g[4:].any(), o


@t
def gates_br():
    mk = _mk()
    mk['BR'][:5] = [0.2, 0.3, 0.1, NAN, 0.2]
    mk['BRmed'][:5] = [0.2, 0.2, 0.2, 0.2, NAN]
    hi, lo = O.gate_series('G_BRhi', mk), O.gate_series('G_BRlo', mk)
    assert hi[:5].tolist() == [True, True, False, False, False] and lo[:5].tolist() == [False, False, True, False, False]
    assert not (hi & lo).any()


@t
def filter_liq_age_daily_index():
    mk = _mk()
    mk['QV30'][0] = [50e6, 49.9e6, NAN]
    mk['QV30'][1] = [1.0, 60e6, 60e6]
    mk['AGE'][0] = [90, 89, -1]
    mk['AGE'][1] = [0, 91, 100]
    k = np.array([0, 0, 0, 23, 24, 24, 47])
    c = np.array([0, 1, 2, 1, 0, 1, 2])
    assert O.filter_at('F_LIQ50', mk, k, c).tolist() == [True, False, False, False, False, True, True]
    assert O.filter_at('F_AGE90', mk, k, c).tolist() == [True, False, False, False, False, True, True]


@t
def filter_pump_nopump_f():
    mk = _mk()
    mk['R24'][5] = [0.20, 0.1999, NAN]
    mk['R24'][6] = [0.10, 0.0999, -0.5]
    mk['F'][5] = [0.0003, 0.00029, NAN]
    k = np.array([5, 5, 5, 6, 6, 6])
    c = np.array([0, 1, 2, 0, 1, 2])
    assert O.filter_at('F_NOPUMP', mk, k, c).tolist() == [False, True, False, True, True, True]
    assert O.filter_at('F_PUMP', mk, k, c).tolist() == [True, True, False, True, False, False]
    assert O.filter_at('F_FHI', mk, k[:3], c[:3]).tolist() == [True, False, False]


@t
def mask_none_and_gate_at_k():
    mk = _mk()
    mk['EW7'][10] = -1.0
    k = np.array([9, 10, 11])
    c = np.array([0, 1, 2])
    assert O.mask_at('NONE', mk, k, c).all()
    assert O.mask_at('G_EW7', mk, k, c).tolist() == [False, True, False]


@t
def twelve_options():
    assert len(O.OPTS) == 12 and set(O.OPTS) == {'G_EW3', 'G_EW7', 'G_EW14', 'G_BTC7', 'G_BTC20', 'G_BRhi', 'G_BRlo', 'F_LIQ50', 'F_AGE90',
                                                   'F_NOPUMP', 'F_PUMP', 'F_FHI'}


@t
def gate_shift_preserves_open():
    rng = np.random.default_rng(5)
    g = rng.uniform(size=5000) > 0.6
    for _ in range(20):
        d = O.draw_shift(rng, len(g), smin=720)
        assert 720 <= d <= 5000 - 720
        gs = O.gate_shift(g, d)
        assert gs.sum() == g.sum() and gs[d] == g[0] and gs[(d + 17) % 5000] == g[17]


@t
def draw_shift_bounds_full():
    rng = np.random.default_rng(6)
    ds = [O.draw_shift(rng, 1600, smin=720) for _ in range(2000)]
    assert min(ds) == 720 and max(ds) == 880


@t
def perm_map_keeps_rate():
    rng = np.random.default_rng(7)
    nh, ns = 96, 8
    mid = np.repeat([0, 1, 2, 3], 24)
    U = rng.uniform(size=(nh, ns)) > 0.4
    U[:24, 7] = False                      # coin 7 not in S_0
    Pm = rng.uniform(size=(nh, ns)) > 0.5
    mp = O.coin_perm_map(U, mid, rng)
    for m in range(4):
        sm = np.flatnonzero(U[mid == m].any(axis=0))
        assert sorted(mp[m, sm].tolist()) == sorted(sm.tolist())
        out = np.setdiff1d(np.arange(ns), sm)
        assert (mp[m, out] == out).all()
        for kk in np.flatnonzero(mid == m):
            assert Pm[kk, mp[m, sm]].sum() == Pm[kk, sm].sum()
    assert mp[0, 7] == 7


@t
def deterministic_rng():
    U = np.ones((48, 6), dtype=bool)
    mid = np.repeat([0, 1], 24)
    a = O.coin_perm_map(U, mid, np.random.default_rng([1, 2, 3]))
    b = O.coin_perm_map(U, mid, np.random.default_rng([1, 2, 3]))
    c = O.coin_perm_map(U, mid, np.random.default_rng([1, 2, 4]))
    assert (a == b).all() and not (a == c).all()
    assert O.draw_shift(np.random.default_rng([9, 1]), 10000) == O.draw_shift(np.random.default_rng([9, 1]), 10000)


@t
def month_id_real_calendar():
    CB = b2c.b1('common_b1')
    mid = O.month_id(CB.NH, CB.H0)
    assert mid[0] == 0 and mid[-1] == 48 and mid[31 * 24 - 1] == 0 and mid[31 * 24] == 1


# ------------------------------------------------------------ VONG 2 (PREREG_LEVZ_B2_ADDENDUM1 B, D)
@t
def ewr_min_coverage_D():
    cc = np.array([[1.0, 1.0, 1.0, 1.0], [2.0, NAN, NAN, 1.0], [3.0, NAN, NAN, NAN]])
    U = np.ones((3, 4), dtype=bool)
    ew, n = MK.ewr(cc, U, 1, hpd=1)
    # k=1: 2 of 4 coins priced (= 50 %) -> value; k=2: 1 of 4 (< 50 %) -> NaN
    assert close(ew[1], (1.0 + 0.0) / 2) and np.isnan(ew[2]) and list(n) == [0, 2, 1]
    U2 = U.copy()
    U2[2, 1:] = False                      # universe shrinks to the priced coin -> 1 of 1 -> value
    ew2, _ = MK.ewr(cc, U2, 1, hpd=1)
    assert close(ew2[2], 0.5)


@t
def ewr_low_coverage_closes_gate():
    cc = np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [0.5, NAN, NAN], [0.5, 0.5, NAN]])
    U = np.ones((4, 3), dtype=bool)
    mk = _mk(nh=4, ns=3)
    mk['EW3'] = MK.ewr(cc, U, 2, hpd=1)[0]      # k=2: return -0.5 but only 1/3 priced -> NaN; k=3: 2/3 priced -> -0.5
    assert np.isnan(mk['EW3'][2]) and close(mk['EW3'][3], -0.5)
    assert O.gate_series('G_EW3', mk).tolist() == [False, False, False, True]


@t
def rate_ok_bounds_B():
    assert O.rate_ok(0.12, 0.10) and O.rate_ok(0.08, 0.10) and not O.rate_ok(0.1201, 0.10) and not O.rate_ok(0.0799, 0.10)
    assert O.rate_ok(0.0, 0.0) and not O.rate_ok(0.01, 0.0)


@t
def placebo_redraw_B():
    U = np.ones((48, 6), dtype=bool)
    mid = np.repeat([0, 1], 24)
    seq = iter([0.5, 0.05, 0.13, 0.11, 0.3])     # rates of successive draws; real = 0.10 -> 3rd draw (0.13) rejected, 4th accepted
    calls = []

    def ex_fn(mp):
        calls.append(mp.copy())
        return next(seq)
    mp, ex, nred = O.draw_filter_perm(U, mid, np.random.default_rng([5, 6]), ex_fn, 0.10)
    assert ex == 0.11 and nred == 3 and (mp == calls[3]).all()
    # deterministic: same seed -> same accepted map / same n_redraw for a map-dependent rate
    Pm = np.random.default_rng(1).uniform(size=(48, 6)) > 0.5
    k = np.arange(0, 48, 3)
    c = k % 6

    def ex2(mp):
        return 1.0 - float(Pm[k, mp[mid[k], c]].mean())
    real = 1.0 - float(Pm[k, c].mean())
    a = O.draw_filter_perm(U, mid, np.random.default_rng([7, 1]), ex2, real)
    b = O.draw_filter_perm(U, mid, np.random.default_rng([7, 1]), ex2, real)
    assert (a[0] == b[0]).all() and a[1:] == b[1:] and O.rate_ok(a[1], real)


@t
def placebo_redraw_gives_up_B():
    U = np.ones((24, 3), dtype=bool)
    mid = np.zeros(24, dtype=np.int64)
    try:
        O.draw_filter_perm(U, mid, np.random.default_rng(0), lambda mp: 1.0, 0.1, max_tries=5)
    except RuntimeError:
        return
    raise AssertionError('no error')


# ------------------------------------------------------------ classes / grid / report
@t
def filtered_classes_none_equals_b1():
    P = b2c.b1('port')
    cz = O.load_cz()
    cl, cnt = O.filtered_classes(cz, lambda k, c: np.ones(len(k), dtype=bool), P)
    for (W, E, z), cb in cl.items():
        ref = P.load_class(cz, W, E, z)
        for a in ('ck', 'cc', 'cs', 'cid'):
            assert (getattr(cb, a) == getattr(ref, a)).all()
        assert cb.by_k == ref.by_k and cnt[(W, E, z)][0] == cnt[(W, E, z)][1]


@t
def filtered_classes_removes_exact():
    P = b2c.b1('port')
    cz = O.load_cz()
    cl, cnt = O.filtered_classes(cz, lambda k, c: (k % 2) == 0, P)
    for (W, E, z), cb in cl.items():
        key = O.class_key(W, E, z)
        m = cz[key + '_k'] % 2 == 0
        assert cnt[(W, E, z)] == (len(m), int(m.sum())) and (cb.ck % 2 == 0).all() and len(cb.ck) == m.sum()
        assert set(zip(cb.ck.tolist(), cb.cc.tolist())) == set(zip(cz[key + '_k'][m].tolist(), cz[key + '_c'][m].tolist()))


@t
def sample300_fixed():
    GR = b2c.b2('grid_b2')
    a, b = GR.sample300(), GR.sample300()
    assert a == b and len(a) == 300
    cf = {c['cfg_id']: c for c in GR.all_cfgs()}
    from collections import Counter
    cnt = Counter((cf[i]['W'], cf[i]['E'], cf[i]['zmin']) for i in a)
    assert len(cnt) == 12 and set(cnt.values()) == {25}


@t
def compare_exact_works():
    GR = b2c.b2('grid_b2')
    a = pd.DataFrame({'cfg_id': [0, 1], 'x': [1.0, NAN], 'E': ['E0', 'E1'], 'sec': [1, 2]})
    b = a.copy()
    b['sec'] = [5, 6]
    assert GR.compare_exact(a, b) == (2, [])
    b.loc[1, 'x'] = 0.0
    assert GR.compare_exact(a, b) == (1, ['x'])


@t
def criteria_boundaries():
    R = b2c.b2('report_b2')
    base = {f: dict(median_ret=0.05, frac_pos=0.6) for f in R.FOLDS}
    st = {f: dict(median_ret=0.031, frac_pos=0.51, trades_kept=0.5) for f in R.FOLDS}
    st['F2'] = dict(median_ret=0.0, frac_pos=0.5, trades_kept=0.5)
    wf = {y: dict(top20_valid=dict(n=20, median_ret=0.001)) for y in ('2024', '2025')}
    c = R.criteria(st, base, wf)
    assert c == dict(a=True, b=True, c=True, d=True, pass_a_to_d=True), c
    st['F3'] = dict(median_ret=0.0299, frac_pos=0.51, trades_kept=0.5)
    assert R.criteria(st, base, wf)['b'] is False
    st['F3'] = dict(median_ret=0.031, frac_pos=0.51, trades_kept=0.4999)
    assert R.criteria(st, base, wf)['c'] is False
    st['F3'] = dict(median_ret=0.031, frac_pos=0.51, trades_kept=0.5)
    wf['2025'] = dict(top20_valid=dict(n=20, median_ret=0.0))
    assert R.criteria(st, base, wf)['d'] is False
    wf['2025'] = dict(top20_valid=dict(n=0))
    assert R.criteria(st, base, wf)['d'] is False
    st['F2'] = dict(median_ret=-1e-9, frac_pos=0.9, trades_kept=0.9)
    assert R.criteria(st, base, wf)['a'] is False
    st['F2'] = dict(median_ret=0.0, frac_pos=0.5, trades_kept=0.9)
    st['F1'] = dict(median_ret=0.031, frac_pos=0.49, trades_kept=0.9)
    assert R.criteria(st, base, wf)['b'] is False and R.criteria(st, base, wf)['a'] is True


# ------------------------------------------------------------ real data: independent re-computation
def _real():
    if 'R' not in _real.__dict__:
        CB = b2c.b1('common_b1')
        mk = MK.load()
        syms = [str(s) for s in mk['syms']]
        U = np.load(CB.L2 + '/work/inputs.npz')['U']
        _real.R = (CB, mk, syms, U)
    return _real.R


def _hr_close(sym, h):
    ym = pd.Timestamp(h, unit='ms').strftime('%Y-%m')
    d = pd.read_parquet(MK.HR % ym, columns=['sym', 'h', 'clast'], filters=[('sym', '==', sym), ('h', '==', int(h))])
    return float(d['clast'].iloc[0]) if len(d) else NAN


@t
def real_cc_r24_btc_loop():
    CB, mk, syms, U = _real()
    rng = np.random.default_rng(11)
    ib = syms.index('BTCUSDT')
    for k in rng.integers(24 * 25, CB.NH, 4):
        k = int(k)
        T = CB.H0 + k * H
        c = int(np.flatnonzero(U[k])[rng.integers(U[k].sum())])
        a, b = _hr_close(syms[c], T - H), _hr_close(syms[c], T - 25 * H)
        assert close(mk['R24'][k, c], a / b - 1), (k, c)
        # BTC7: loop over 168 previous hourly closes
        prev = [_hr_close('BTCUSDT', T - H - j * H) for j in range(1, 169)]
        cur = _hr_close('BTCUSDT', T - H)
        assert abs(mk['BTC7'][k] - (cur / np.mean(prev) - 1)) < 1e-12, k
    assert 'BTCUSDT' == syms[ib]


@t
def real_ew3_loop():
    CB, mk, syms, U = _real()
    k = int(np.random.default_rng(12).integers(24 * 30, CB.NH))
    T = CB.H0 + k * H
    vals = []
    ymA = pd.Timestamp(T - H, unit='ms').strftime('%Y-%m')
    ymB = pd.Timestamp(T - 73 * H, unit='ms').strftime('%Y-%m')
    A = pd.read_parquet(MK.HR % ymA, columns=['sym', 'h', 'clast'], filters=[('h', '==', T - H)]).set_index('sym')['clast']
    B = pd.read_parquet(MK.HR % ymB, columns=['sym', 'h', 'clast'], filters=[('h', '==', T - 73 * H)]).set_index('sym')['clast']
    for c in np.flatnonzero(U[k]):
        s = syms[c]
        if s in A.index and s in B.index and np.isfinite(A[s]) and np.isfinite(B[s]):
            vals.append(A[s] / B[s] - 1)
    assert abs(mk['EW3'][k] - np.mean(vals)) < 1e-12 and mk['EWN3'][k] == len(vals)


@t
def real_br_loop():
    CB, mk, syms, U = _real()
    S = CB.load_b0('sim')
    SG = S.load_sibling('sig')
    G = SG.dense_from_sig(7)
    rng = np.random.default_rng(13)
    for k in rng.integers(3000, CB.NH, 3):
        k = int(k)
        num = 0
        for c in np.flatnonzero(U[k]):
            w = slice(k - 23, k + 1)
            with np.errstate(invalid='ignore'):
                lv = (G['z_oi'][w, c] >= 2.5) & (G['z_f'][w, c] >= 2.5) & (G['f'][w, c] > 0.0001)
            num += bool(lv.any())
        assert abs(mk['BR'][k] - num / U[k].sum()) < 1e-12
        prev = mk['BR'][k - 2160:k]
        assert abs(mk['BRmed'][k] - np.nanmedian(prev)) < 1e-12


@t
def real_no_2026():
    CB, mk, syms, U = _real()
    assert int(mk['NH']) == CB.NH and CB.H0 + CB.NH * H == 1767225600000 and mk['QV30'].shape[0] * 86400000 + CB.H0 == 1767225600000


@t
def real_f2_routine_equals_b1():
    PL = b2c.b2('placebo_b2')
    GR = PL.GR
    ids = set(GR.sample300())
    cfgs = [c for c in GR.all_cfgs() if c['cfg_id'] in ids][::10]
    T = GR.X.load_table()
    cl, _ = GR.classes_for('NONE')
    st, rets = PL.stat_for(cl, cfgs, T)
    ref = pd.read_parquet(GR.GRID_B1).set_index('cfg_id').loc[[c['cfg_id'] for c in cfgs], 'F2_ret'].values
    assert np.array_equal(rets, ref)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    res = []
    for fn in TESTS:
        try:
            fn()
            res.append((fn.__name__, 'PASS', ''))
        except Exception:
            res.append((fn.__name__, 'FAIL', traceback.format_exc()[-800:]))
        log.info('%s %s', res[-1][0], res[-1][1])
    npass = sum(r[1] == 'PASS' for r in res)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_report.json'), 'w') as fh:
        json.dump(dict(n=len(res), passed=npass, results=res), fh, indent=1)
    log.info('TESTS %d/%d PASS', npass, len(res))
    for r in res:
        if r[1] == 'FAIL':
            log.error('%s\n%s', r[0], r[2])
    sys.exit(0 if npass == len(res) else 1)


if __name__ == '__main__':
    main()
