"""LEVZ2 unit tests on SMALL SYNTHETIC data (hand-computed expectations). No real market data is read.
Run: python3 test/test_sim.py   (self-running; pytest-compatible names). Writes test/test_report.json."""
import os
import sys
_CODE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'code')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) not in (_CODE, _HERE)]
import importlib.util
import json
import logging
import traceback
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd


def _load(name):
    mn = 'levz2_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(_CODE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod


S = _load('sim')
SEL = _load('select')
RND = _load('rand')
log = logging.getLogger('levz2.test')

K0 = S.kidx(S.ms('2022-01-01'))
NH = K0 + 24 * 20
END = '2022-01-15'
KL = S.kidx(S.ms(END)) - 1
TOL = 1e-9


def mk(ns=3, p=100.0):
    a = np.full((NH, ns), p)
    px = dict(O=a.copy(), HI=a.copy(), LO=a.copy(), CL=a.copy(), tms=S.H0 + np.arange(NH, dtype=np.int64) * S.H)
    return px, np.zeros((NH, ns))


def bar(px, k, c, o, h, l, cl):
    px['O'][k, c], px['HI'][k, c], px['LO'][k, c], px['CL'][k, c] = o, h, l, cl


def nan_bar(px, k, c):
    for n in ('O', 'HI', 'LO', 'CL'):
        px[n][k, c] = np.nan


def cand(lst):
    if not lst:
        z = np.zeros(0, dtype=np.int64)
        return S.Cand(z, z, np.zeros(0))
    ck = np.array([x[0] for x in lst], dtype=np.int64)
    cc = np.array([x[1] for x in lst], dtype=np.int64)
    cs = np.array([x[2] for x in lst], dtype=np.float64)
    o = np.lexsort((cc, -cs, ck))
    return S.Cand(ck[o], cc[o], cs[o])


def cfg(**kw):
    d = dict(W=14, E='E0', zmin=2.5, K=1, SL=0.30, H=24, trail=0, dca=0)
    d.update(kw)
    return d


def R(c, cd, px, FR, start='2022-01-01', end=END):
    return S.run(c, cd, px, FR, start, end)


def close(a, b, tol=TOL):
    assert abs(a - b) <= tol * max(1.0, abs(b)), (a, b)


def inv(tr, eq):
    assert abs(tr['net'].sum() - (eq['eq'].values[-1] - S.INIT)) <= 1e-6


# ---------------------------------------------------------------- fees / SL / time
def test_fee_only():
    px, FR = mk()
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    assert len(tr) == 1 and tr['reason'][0] == 'time' and tr['kx'][0] == K0 + 24
    close(tr['size0'][0], 6000.0)
    close(tr['fees'][0], 8.4)
    close(tr['net'][0], -8.4)
    close(m['eq_end'], 9991.6)
    inv(tr, eq)


def test_sl_touch():
    px, FR = mk()
    bar(px, K0 + 3, 0, 100, 131, 100, 100)
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'sl' and tr['kx'][0] == K0 + 3
    close(tr['px_exit'][0], 130.0 * 1.005)
    close(tr['gross'][0], 60 * (100 - 130.65))
    close(tr['fees'][0], 4.2 + 60 * 130.65 * 0.0007)
    close(tr['net'][0], -1839.0 - 9.6873)
    inv(tr, eq)


def test_sl_gap_open():
    px, FR = mk()
    bar(px, K0 + 3, 0, 140, 141, 139, 140)
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'sl'
    close(tr['px_exit'][0], 140.0)
    close(tr['gross'][0], -2400.0)


def test_entry_candle_not_checked():
    px, FR = mk()
    bar(px, K0, 0, 100, 200, 50, 100)      # entry candle (closes at T_K0): must be ignored
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'time'
    close(tr['net'][0], -8.4)


def test_time_stop_close():
    px, FR = mk()
    bar(px, K0 + 24, 0, 100, 100, 90, 90)
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'time' and tr['kx'][0] == K0 + 24
    close(tr['px_exit'][0], 90.0)
    close(tr['net'][0], 600 - 4.2 - 60 * 90 * 0.0007)


def test_sl_priority_over_time_stop():
    px, FR = mk()
    bar(px, K0 + 24, 0, 100, 135, 90, 90)
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'sl' and tr['kx'][0] == K0 + 24


# ---------------------------------------------------------------- trailing
def test_trail_activate_prev_level_then_exit():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 100, 89, 95)   # activates (89 <= 90); level set AFTER check => no exit although high 100
    bar(px, K0 + 2, 0, 93, 94, 92, 93)     # high 94 >= 93.45 => exit 93.45*1.001
    tr, eq, m = R(cfg(trail=1, SL=0.5, H=72), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'trail' and tr['kx'][0] == K0 + 2
    close(tr['px_exit'][0], 89 * 1.05 * 1.001)
    close(tr['gross'][0], 60 * (100 - 89 * 1.05 * 1.001))
    inv(tr, eq)


def test_trail_not_activated():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 100, 90.5, 95)
    bar(px, K0 + 2, 0, 95, 99, 94, 98)
    tr, eq, m = R(cfg(trail=1, SL=0.5, H=72), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'time' and tr['kx'][0] == K0 + 72


def test_trail_gap_open():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 100, 89, 95)
    bar(px, K0 + 2, 0, 96, 97, 95, 96)     # open above level => max(open, lvl*1.001) = open
    tr, eq, m = R(cfg(trail=1, SL=0.5, H=72), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'trail'
    close(tr['px_exit'][0], 96.0)


def test_trail_trough_update_after_check():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 100, 89, 95)   # lvl 93.45
    bar(px, K0 + 2, 0, 90, 93, 80, 85)     # 93 < 93.45 no exit; trough 80 -> lvl 84
    bar(px, K0 + 3, 0, 83, 85, 82, 84)     # 85 >= 84 -> exit 84*1.001
    tr, eq, m = R(cfg(trail=1, SL=0.5, H=72), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'trail' and tr['kx'][0] == K0 + 3
    close(tr['px_exit'][0], 80 * 1.05 * 1.001)


def test_sl_before_trail_same_candle():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 100, 89, 95)
    bar(px, K0 + 2, 0, 100, 131, 95, 100)
    tr, eq, m = R(cfg(trail=1, SL=0.3, H=72), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'sl'
    close(tr['px_exit'][0], 130.65)


# ---------------------------------------------------------------- DCA
def test_dca_add():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 111, 100, 100)
    tr, eq, m = R(cfg(K=3, dca=1, SL=0.3), cand([(K0, 0, 3.0)]), px, FR)
    t = tr.iloc[0]
    assert t['dca'] == 1 and t['k_dca'] == K0 + 1 and t['reason'] == 'time'
    qa = 2000 / 110.0
    close(t['qty'], 20 + qa)
    close(t['avg'], 4000.0 / (20 + qa))
    close(t['notional_in'], 4000.0)
    close(t['gross'], qa * 10)
    close(t['fees'], 1.4 + 1.4 + (20 + qa) * 100 * 0.0007)
    inv(tr, eq)


def test_dca_blocked_by_cap_single():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 111, 100, 100)
    tr, eq, m = R(cfg(K=1, dca=1), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['dca'][0] == 0
    close(tr['net'][0], -8.4)


def test_dca_blocked_by_cap_with_other_position():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 111, 100, 100)
    tr, eq, m = R(cfg(K=3, dca=1), cand([(K0, 0, 3.0), (K0, 1, 2.9)]), px, FR)
    assert tr.set_index('c').loc[0, 'dca'] == 0     # 2000 + 2200 + 2000 = 6200 > 0.6 * 9797.2


def test_g2_dca_then_sl_same_candle():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 135, 100, 100)          # open < 110 <= high and high >= stop 130: DCA first, then SL on new qty
    tr, eq, m = R(cfg(K=3, dca=1, SL=0.3), cand([(K0, 0, 3.0)]), px, FR)
    t = tr.iloc[0]
    assert t['reason'] == 'sl' and t['dca'] == 1 and t['k_dca'] == K0 + 1 and t['kx'] == K0 + 1
    qa = 2000 / 110.0
    close(t['px_exit'], 130.65)
    close(t['gross'], 20 * (100 - 130.65) + qa * (110 - 130.65))
    close(t['fees'], 1.4 + 1.4 + (20 + qa) * 130.65 * 0.0007)
    inv(tr, eq)


def test_g2_dca_blocked_by_cap_then_sl():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 135, 100, 100)
    tr, eq, m = R(cfg(K=1, dca=1, SL=0.3), cand([(K0, 0, 3.0)]), px, FR)
    t = tr.iloc[0]
    assert t['reason'] == 'sl' and t['dca'] == 0
    close(t['gross'], 60 * (100 - 130.65))
    close(t['fees'], 4.2 + 60 * 130.65 * 0.0007)


def test_g2_gap_over_stop_no_dca():
    px, FR = mk()
    bar(px, K0 + 1, 0, 140, 141, 139, 140)
    tr, eq, m = R(cfg(K=3, dca=1, SL=0.3), cand([(K0, 0, 3.0)]), px, FR)
    t = tr.iloc[0]
    assert t['reason'] == 'sl' and t['dca'] == 0
    close(t['px_exit'], 140.0)
    close(t['gross'], 20 * (100 - 140))


def test_g3_trail_hit_no_dca():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 100, 89, 95)            # arm trail, lvl 93.45
    bar(px, K0 + 2, 0, 93, 111, 92, 100)            # high >= lvl AND >= DCA level: trail exit, NO DCA
    tr, eq, m = R(cfg(K=3, dca=1, trail=1, SL=0.5, H=72), cand([(K0, 0, 3.0)]), px, FR)
    t = tr.iloc[0]
    assert t['reason'] == 'trail' and t['dca'] == 0 and t['kx'] == K0 + 2
    close(t['px_exit'], 89 * 1.05 * 1.001)
    close(t['gross'], 20 * (100 - 89 * 1.05 * 1.001))


def test_g3_dca_when_trail_not_armed():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 111, 95, 100)           # trail not armed (low 95 > 90): DCA happens
    tr, eq, m = R(cfg(K=3, dca=1, trail=1, SL=0.5, H=72), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['dca'][0] == 1 and tr['reason'][0] == 'time'


def test_dca_sl_from_first_entry():
    px, FR = mk()
    bar(px, K0 + 1, 0, 100, 111, 100, 100)
    bar(px, K0 + 2, 0, 100, 130.5, 100, 100)
    tr, eq, m = R(cfg(K=3, dca=1, SL=0.3), cand([(K0, 0, 3.0)]), px, FR)
    t = tr.iloc[0]
    assert t['reason'] == 'sl' and t['dca'] == 1
    qa = 2000 / 110.0
    close(t['gross'], 20 * (100 - 130.65) + qa * (110 - 130.65))
    inv(tr, eq)


# ---------------------------------------------------------------- funding
def test_funding_positive():
    px, FR = mk()
    FR[K0 + 5, 0] = 0.001
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    close(tr['funding'][0], 6.0)
    close(tr['net'][0], -2.4)
    inv(tr, eq)


def test_funding_negative():
    px, FR = mk()
    FR[K0 + 5, 0] = -0.001
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    close(tr['funding'][0], -6.0)


def test_funding_window_entry_exit():
    px, FR = mk()
    FR[K0, 0] = 0.001       # settlement at entry boundary: not received (entry after settlement)
    FR[K0 + 24, 0] = 0.002  # at time-stop boundary: received (exit at close, after settlement)
    FR[K0 + 25, 0] = 0.005  # after exit
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    close(tr['funding'][0], 12.0)


def test_funding_not_in_intrabar_exit_hour():
    px, FR = mk()
    FR[K0 + 2, 0] = 0.001
    FR[K0 + 3, 0] = 0.01
    bar(px, K0 + 3, 0, 100, 131, 100, 100)
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    close(tr['funding'][0], 6.0)


def test_funding_notional_at_close():
    px, FR = mk()
    bar(px, K0 + 5, 0, 100, 120, 100, 120)
    FR[K0 + 5, 0] = 0.001
    tr, eq, m = R(cfg(SL=0.5), cand([(K0, 0, 3.0)]), px, FR)
    close(tr['funding'][0], 60 * 120 * 0.001)


# ---------------------------------------------------------------- top-K / cooldown / slots
def test_topk_cut():
    px, FR = mk()
    tr, eq, m = R(cfg(K=2), cand([(K0, 0, 3.0), (K0, 1, 5.0), (K0, 2, 4.0)]), px, FR)
    assert sorted(tr['c'].tolist()) == [1, 2]
    close(tr['size0'][0], 3000.0)


def test_tie_break_sym_asc():
    px, FR = mk()
    tr, eq, m = R(cfg(K=1), cand([(K0, 2, 4.0), (K0, 1, 4.0)]), px, FR)
    assert tr['c'].tolist() == [1]


def test_cooldown_from_entry():
    px, FR = mk()
    tr, eq, m = R(cfg(K=1), cand([(K0, 0, 3.0), (K0 + 30, 0, 3.0), (K0 + 72, 0, 3.0), (K0 + 73, 0, 3.0)]), px, FR)
    assert tr['ke'].tolist() == [K0, K0 + 73]


def test_no_reentry_while_open():
    px, FR = mk()
    tr, eq, m = R(cfg(K=1, H=168, SL=0.5), cand([(K0, 0, 3.0), (K0 + 80, 0, 3.0)]), px, FR)
    assert len(tr) == 1 and tr['ke'][0] == K0


def test_slot_freed_same_hour():
    px, FR = mk()
    tr, eq, m = R(cfg(K=1), cand([(K0, 0, 3.0), (K0 + 24, 1, 3.0)]), px, FR)
    assert tr['ke'].tolist() == [K0, K0 + 24]


def test_size_uses_current_equity():
    px, FR = mk()
    bar(px, K0 + 3, 0, 100, 131, 100, 100)
    tr, eq, m = R(cfg(K=1), cand([(K0, 0, 3.0), (K0 + 10, 1, 3.0)]), px, FR)
    eq1 = 10000 - 1839.0 - 9.6873
    close(tr.set_index('c').loc[1, 'size0'], eq1 * 0.6)


# ---------------------------------------------------------------- missing data / eod
def test_missing_gt24_close_last():
    px, FR = mk()
    bar(px, K0 + 2, 0, 100, 100, 95, 95)
    for k in range(K0 + 3, K0 + 41):
        nan_bar(px, k, 0)
    tr, eq, m = R(cfg(H=168, SL=0.5), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'gap' and tr['kx'][0] == K0 + 27 and tr['flag'][0] == 1
    close(tr['px_exit'][0], 95.0)


def test_missing_at_time_stop():
    px, FR = mk()
    bar(px, K0 + 23, 0, 100, 100, 97, 97)
    nan_bar(px, K0 + 24, 0)
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    assert tr['reason'][0] == 'time_sub' and tr['kx'][0] == K0 + 24
    close(tr['px_exit'][0], 97.0)


def test_eod_forced_close():
    px, FR = mk()
    tr, eq, m = R(cfg(H=168, SL=0.5), cand([(K0, 0, 3.0)]), px, FR, end='2022-01-03')
    assert tr['reason'][0] == 'eod' and tr['kx'][0] == K0 + 47


def test_no_entry_at_last_hour():
    px, FR = mk()
    tr, eq, m = R(cfg(), cand([(KL, 0, 3.0)]), px, FR)
    assert len(tr) == 0
    close(m['eq_end'], S.INIT)


# ---------------------------------------------------------------- equity / DD
def test_worst_hour_equity():
    px, FR = mk()
    bar(px, K0 + 5, 0, 100, 110, 100, 100)
    tr, eq, m = R(cfg(), cand([(K0, 0, 3.0)]), px, FR)
    i = K0 + 5 - K0
    close(eq['eq'].values[i] - eq['eq_worst'].values[i], 600.0)
    close(m['maxdd_worst'], 1 - (10000 - 4.2 - 600) / 10000.0, 1e-9)   # peak = initial 10 000 (before entry fee)


def test_maxdd_function():
    e = np.array([10000., 12000., 9000., 11000.])
    w = np.array([10000., 12000., 8400., 11000.])
    dd, ddw = S._maxdd(e, w)
    close(dd, 0.25)
    close(ddw, 0.30)


def _rand_world(seed, ns=6):
    rng = np.random.default_rng(seed)
    px, FR = mk(ns)
    r = rng.normal(0, 0.02, size=(NH, ns))
    cl = 100 * np.exp(np.cumsum(r, axis=0))
    op = np.vstack([cl[:1], cl[:-1]])
    hi = np.maximum(op, cl) * (1 + np.abs(rng.normal(0, 0.02, size=(NH, ns))))
    lo = np.minimum(op, cl) * (1 - np.abs(rng.normal(0, 0.02, size=(NH, ns))))
    px['O'][:], px['HI'][:], px['LO'][:], px['CL'][:] = op, hi, lo, cl
    miss = rng.random((NH, ns)) < 0.01
    for c in range(ns):
        k = int(rng.integers(K0 + 20, K0 + 200))
        miss[k:k + 30, c] = True     # long gap
    for n in ('O', 'HI', 'LO', 'CL'):
        px[n][miss] = np.nan
    FR[::8] = rng.normal(0.0001, 0.0005, size=FR[::8].shape)
    lst = []
    for k in range(K0, KL + 1):
        for c in range(ns):
            if rng.random() < 0.03 and np.isfinite(px['CL'][k, c]):
                lst.append((k, c, float(rng.normal(3, 1))))
    return px, FR, lst


def test_accounting_invariant_random():
    worst = 0.0
    for seed in range(4):
        px, FR, lst = _rand_world(seed)
        for tr_ in (0, 1):
            for dc in (0, 1):
                for K in (3, 10):
                    c = cfg(K=K, SL=0.15, H=72, trail=tr_, dca=dc)
                    tr, eq, m = R(c, cand(lst), px, FR)
                    assert len(tr) > 5
                    err = abs(tr['net'].sum() - (eq['eq'].values[-1] - S.INIT))
                    worst = max(worst, err, abs(m['acct_err']))
                    # per-trade decomposition
                    assert np.allclose(tr['net'], tr['gross'] - tr['fees'] + tr['funding'], atol=1e-9)
    assert worst <= 1e-6, worst


def test_no_lookahead():
    px, FR, lst = _rand_world(11)
    c = cfg(K=3, SL=0.15, H=72, trail=1, dca=1)
    t = K0 + 150
    tr1, eq1, _ = R(c, cand(lst), px, FR)
    px2 = {k: (v.copy() if k != 'tms' else v) for k, v in px.items()}
    FR2 = FR.copy()
    rng = np.random.default_rng(5)
    for n in ('O', 'HI', 'LO', 'CL'):
        px2[n][t + 1:] = px2[n][t + 1:] * rng.uniform(0.5, 1.5, size=px2[n][t + 1:].shape)
    FR2[t + 1:] = rng.normal(0, 0.01, size=FR2[t + 1:].shape)
    lst2 = [x for x in lst if x[0] <= t] + [(k, cc, 9.0) for k in range(t + 1, KL, 7) for cc in range(6)]
    tr2, eq2, _ = R(c, cand(lst2), px2, FR2)
    a = tr1[tr1['kx'] <= t].reset_index(drop=True)
    b = tr2[tr2['kx'] <= t].reset_index(drop=True)
    assert a.equals(b)
    assert set(zip(tr1.loc[tr1['ke'] <= t, 'c'], tr1.loc[tr1['ke'] <= t, 'ke'])) == \
        set(zip(tr2.loc[tr2['ke'] <= t, 'c'], tr2.loc[tr2['ke'] <= t, 'ke']))
    i = t - K0
    assert np.array_equal(eq1['eq'].values[:i + 1], eq2['eq'].values[:i + 1])
    assert np.array_equal(eq1['eq_worst'].values[:i + 1], eq2['eq_worst'].values[:i + 1])


def test_deterministic():
    px, FR, lst = _rand_world(3)
    c = cfg(K=5, SL=0.30, H=24, trail=1, dca=1)
    a = R(c, cand(lst), px, FR)
    b = R(c, cand(lst), px, FR)
    assert a[0].equals(b[0]) and a[1].equals(b[1]) and json.dumps(a[2], default=str) == json.dumps(b[2], default=str)


def test_fold_independent_start():
    px, FR, lst = _rand_world(4)
    c = cfg(K=3, SL=0.30, H=24)
    tr1, eq1, m1 = R(c, cand(lst), px, FR, '2022-01-01', '2022-01-08')
    tr2, eq2, m2 = R(c, cand(lst), px, FR, '2022-01-08', '2022-01-15')
    k8 = S.kidx(S.ms('2022-01-08'))
    assert tr2['ke'].min() >= k8 and tr1['kx'].max() <= k8 - 1
    first = tr2.sort_values(['ke', 'c']).iloc[0]
    assert abs(first['size0'] - S.INIT * 0.6 / 3) < 1e-9


# ---------------------------------------------------------------- candidates
def test_candidates_E0():
    n, ns = 10, 3
    zo = np.full((n, ns), 3.0)
    zf = np.full((n, ns), 3.0)
    f = np.full((n, ns), 0.0002)
    zr = np.zeros((n, ns))
    u = np.ones((n, ns), dtype=bool)
    ok = np.ones((n, ns), dtype=bool)
    zo[1, 0] = 2.5                        # == zmin -> candidate (>=)
    zo[2, 0] = 2.4999
    f[3, 0] = 0.0001                      # == F_MIN -> NOT (strict >)
    u[4, 0] = False
    zf[5, 0] = np.nan
    ok[6, 0] = False                      # no store price
    zo[7, 1] = 4.0
    zf[7, 1] = 3.5                        # s = 3.5 ; coin 0 & 2 s = 3.0
    ck, cc, cs = S.candidates(zo, zf, f, zr, u, ok, 'E0', 2.5)
    got = set(zip(ck.tolist(), cc.tolist()))
    for k in (2, 3, 4, 5, 6):
        assert (k, 0) not in got
    assert (1, 0) in got and (0, 0) in got
    r7 = [(int(a), int(b)) for a, b in zip(ck, cc) if a == 7]
    assert r7 == [(7, 1), (7, 0), (7, 2)]
    assert cs[(ck == 7) & (cc == 1)][0] == 3.5


def test_candidates_E1():
    n, ns = 80, 2
    zo = np.zeros((n, ns))
    zf = np.zeros((n, ns))
    f = np.full((n, ns), 0.0002)
    zr = np.zeros((n, ns))
    u = np.ones((n, ns), dtype=bool)
    ok = np.ones((n, ns), dtype=bool)
    zo[10, 0], zf[10, 0] = 4.0, 3.0      # LEV at 10, s=3
    zr[15, 0] = -2.0                      # first z_r<=-2 after LEV within 24h -> candidate at 15
    zr[17, 0] = -3.0                      # not first -> no
    zo[40, 0], zf[40, 0] = 3.0, 3.0      # LEV at 40 with z_r<=-2 at the LEV hour itself
    zr[40, 0] = -2.5
    zr[42, 0] = -2.1                      # first since LEV(40) (LEV hour excluded) -> candidate at 42
    zo[50, 1], zf[50, 1] = 3.0, 3.0
    zr[74, 1] = -2.2                      # exactly 24h after -> candidate
    zo[2, 1], zf[2, 1] = 3.0, 3.0
    zr[27, 1] = -2.2                      # 25h after -> no
    ck, cc, cs = S.candidates(zo, zf, f, zr, u, ok, 'E1', 2.5)
    got = sorted(zip(ck.tolist(), cc.tolist()))
    assert got == [(15, 0), (42, 0), (74, 1)], got
    assert cs[(ck == 15)][0] == 3.0
    ok[15, 0] = False
    ck, cc, cs = S.candidates(zo, zf, f, zr, u, ok, 'E1', 2.5)
    assert (15, 0) not in set(zip(ck.tolist(), cc.tolist()))


def test_all_cfgs():
    cf = S.all_cfgs()
    keys = set(tuple(d[p] for p in S.PKEYS) for d in cf)
    assert len(cf) == 1296 and len(keys) == 1296
    assert [d['cfg_id'] for d in cf] == list(range(1296))


# ---------------------------------------------------------------- selection rule / plateau (fake grid)
def _fake_grid():
    rows = []
    for d in S.all_cfgs():
        r = dict(d)
        for f in ('F1', 'F2', 'F3'):
            r[f + '_n'] = 50
            r[f + '_ret'] = -0.1
            r[f + '_maxdd_worst'] = 0.2
        r['DEV_maxdd_worst'] = 0.2
        r['DEV_ret'] = 0.0
        r['DEV_cagr'] = 0.0
        rows.append(r)
    return pd.DataFrame(rows)


def _id(df, **kw):
    m = np.ones(len(df), dtype=bool)
    for k, v in kw.items():
        m &= (df[k] == v).values
    assert m.sum() == 1
    return int(np.flatnonzero(m)[0])


def _set(df, i, ret, dd=0.1, n=50, devdd=0.2):
    for f in ('F1', 'F2', 'F3'):
        df.loc[i, f + '_ret'] = ret[f] if isinstance(ret, dict) else ret
        df.loc[i, f + '_maxdd_worst'] = dd
        df.loc[i, f + '_n'] = n
    df.loc[i, 'DEV_maxdd_worst'] = devdd


def test_neighbours_count():
    base = dict(W=14, E='E0', zmin=2.5, K=3, SL=0.15, H=24, trail=0, dca=0)
    assert len(SEL.neighbours(base, S.GRID)) == 8
    mid = dict(base, zmin=3.0, K=5)
    nb = SEL.neighbours(mid, S.GRID)
    assert len(nb) == 10
    assert dict(mid, zmin=2.5) in nb and dict(mid, zmin=3.5) in nb and dict(mid, K=10) in nb
    assert dict(base, K=10) not in SEL.neighbours(base, S.GRID)          # non-adjacent value excluded


def test_validity_rules():
    df = _fake_grid()
    a = _id(df, W=14, E='E0', zmin=2.5, K=3, SL=0.15, H=24, trail=0, dca=0)
    _set(df, a, 0.5, n=29)                                         # n < 30 in a fold -> invalid
    b = _id(df, W=14, E='E0', zmin=2.5, K=3, SL=0.15, H=24, trail=0, dca=1)
    _set(df, b, 0.5, devdd=0.31)                                   # DEV DD > 30 % -> invalid
    c = _id(df, W=14, E='E0', zmin=2.5, K=3, SL=0.15, H=24, trail=1, dca=0)
    _set(df, c, {'F1': 0.5, 'F2': 0.0, 'F3': 0.5})                  # profit must be > 0
    d = _id(df, W=14, E='E0', zmin=2.5, K=3, SL=0.15, H=24, trail=1, dca=1)
    _set(df, d, 0.5, n=30, devdd=0.30)                              # boundaries inclusive -> valid
    out, ranked, tried, chosen = SEL.select(df, S.GRID, S.PKEYS)
    assert set(ranked['cfg_id']) == {d}


def test_maximin_score():
    r = {'F1_ret': 0.2, 'F1_maxdd_worst': 0.1, 'F2_ret': 0.3, 'F2_maxdd_worst': 0.3, 'F3_ret': 0.5, 'F3_maxdd_worst': 0.1}
    close(SEL.score_of(r), 1.0)


def test_plateau_reject_then_next():
    df = _fake_grid()
    a = _id(df, W=14, E='E0', zmin=2.5, K=3, SL=0.15, H=24, trail=0, dca=0)
    _set(df, a, 1.0)                                    # best score 10 but neighbours all negative
    bcfg = dict(W=7, E='E1', zmin=3.0, K=5, SL=0.30, H=72, trail=1, dca=1)
    b = _id(df, **bcfg)
    _set(df, b, 0.2)                                    # score 2
    nb = SEL.neighbours(bcfg, S.GRID)
    assert len(nb) == 12
    for j, d in enumerate(nb):
        if j < 8:                                       # 8/12 = 66.7 % positive in all folds (but invalid: n<30)
            _set(df, _id(df, **d), 0.01, n=10)
    out, ranked, tried, chosen = SEL.select(df, S.GRID, S.PKEYS)
    assert tried[0]['cfg_id'] == a and not tried[0]['plateau_ok']
    assert chosen is not None and int(chosen['cfg_id']) == b
    close(tried[1]['frac_nb_pos3'], 8 / 12)
    # 7/12 = 58 % < 60 % -> no config
    _set(df, _id(df, **nb[0]), -0.01, n=10)
    out, ranked, tried, chosen = SEL.select(df, S.GRID, S.PKEYS)
    assert chosen is None
    rep, top = SEL.report(out, ranked, tried, chosen, S.GRID, S.PKEYS)
    assert rep['verdict'] == 'KHONG CO CAU HINH' and rep['n_valid'] == 2


def test_plateau_exact_60pct():
    df = _fake_grid()
    bcfg = dict(W=14, E='E0', zmin=2.5, K=3, SL=0.15, H=24, trail=0, dca=0)   # 8 neighbours? need 10 for exact 60%
    bcfg = dict(W=14, E='E0', zmin=3.0, K=5, SL=0.15, H=24, trail=0, dca=0)   # 10 neighbours
    b = _id(df, **bcfg)
    _set(df, b, 0.2)
    nb = SEL.neighbours(bcfg, S.GRID)
    assert len(nb) == 10
    for d in nb[:6]:
        _set(df, _id(df, **d), 0.01, n=10)
    out, ranked, tried, chosen = SEL.select(df, S.GRID, S.PKEYS)
    assert chosen is not None and int(chosen['cfg_id']) == b


# ---------------------------------------------------------------- random control
class _FakeI:
    pass


def test_random_draw_counts_and_seed():
    I = _FakeI()
    I.tms = S.H0 + np.arange(NH, dtype=np.int64) * S.H
    ns = 5
    I.U = np.zeros((NH, ns), dtype=bool)
    I.U[K0:, :3] = True
    I.px = dict(CL=np.full((NH, ns), 100.0))
    I.px['CL'][K0 + 5, 1] = np.nan
    real = cand([(K0 + 1, 0, 3.0), (K0 + 2, 1, 3.0), (K0 + 3, 2, 3.0)])
    pools = RND.build_pools(I, real, '2022-01-01', '2022-01-15')
    assert sum(p[0] for p in pools) == 3
    c1 = RND.draw(pools, np.random.default_rng([RND.SEED, 7]))
    c2 = RND.draw(pools, np.random.default_rng([RND.SEED, 7]))
    assert np.array_equal(c1.ck, c2.ck) and np.array_equal(c1.cc, c2.cc) and np.array_equal(c1.cs, c2.cs)
    assert len(c1.ck) == 3 and (c1.cc < 3).all() and (c1.ck >= K0).all()
    assert not ((c1.ck == K0 + 5) & (c1.cc == 1)).any()
    assert len(set(zip(c1.ck.tolist(), c1.cc.tolist()))) == 3


def test_g1_episode_starts_and_pool_counts():
    k_feb = S.kidx(S.ms('2022-02-01'))
    n = k_feb + 24 * 30
    I = _FakeI()
    I.tms = S.H0 + np.arange(n, dtype=np.int64) * S.H
    ns = 4
    I.U = np.zeros((n, ns), dtype=bool)
    I.U[K0:, :] = True
    I.px = dict(CL=np.full((n, ns), 100.0))
    lst = [(K0 + 1, 0, 3.0), (K0 + 50, 0, 3.0), (K0 + 122, 0, 3.0),      # chain (gaps 49, 72) -> 1 episode
           (K0 + 195, 0, 3.0),                                           # gap 73 -> new episode
           (K0 + 10, 1, 3.0), (K0 + 11, 1, 3.0),                         # 1 episode
           (k_feb + 5, 2, 3.0), (k_feb + 77, 2, 3.0), (k_feb + 150, 2, 3.0),  # gaps 72, 73 -> 2 episodes
           (k_feb - 30, 3, 3.0), (k_feb + 20, 3, 3.0)]                   # chained across months -> start in Jan only
    real = cand(lst)
    ek, ec = RND.episode_starts(real.ck, real.cc)
    assert sorted(zip(ek.tolist(), ec.tolist())) == sorted([(K0 + 1, 0), (K0 + 195, 0), (K0 + 10, 1), (k_feb + 5, 2),
                                                            (k_feb + 150, 2), (k_feb - 30, 3)])
    pools = RND.build_pools(I, real, '2022-01-01', '2022-03-01')
    assert [p[0] for p in pools] == [4, 2]                                # Jan 4 episodes, Feb 2
    for r in range(20):
        c1 = RND.draw(pools, np.random.default_rng([RND.SEED, r]))
        mk_ = RND.month_keys(I.tms[c1.ck])
        assert int((mk_ == 202201).sum()) == 4 and int((mk_ == 202202).sum()) == 2


def test_g5_grid_acct_assert():
    G = _load('grid')
    df = pd.DataFrame({f + '_acct_err': [1e-9, -2e-9] for f in ('DEV', 'F1', 'F2', 'F3')})
    G.check_acct(df)
    for f in ('DEV', 'F1', 'F2', 'F3'):
        d = df.copy()
        d.loc[1, f + '_acct_err'] = 1e-3
        try:
            G.check_acct(d)
            raise RuntimeError('no assert for %s' % f)
        except AssertionError:
            pass


# ---------------------------------------------------------------- runner
def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    res = {}
    for k, f in tests:
        try:
            f()
            res[k] = 'PASS'
        except Exception:
            res[k] = 'FAIL ' + traceback.format_exc().strip().splitlines()[-1]
            log.error('%s\n%s', k, traceback.format_exc())
    npass = sum(v == 'PASS' for v in res.values())
    for k, v in res.items():
        log.info('%-45s %s', k, v)
    log.info('TESTS %d/%d PASS', npass, len(res))
    with open(os.path.join(_HERE, 'test_report.json'), 'w') as fh:
        json.dump(dict(n=len(res), n_pass=npass, results=res), fh, indent=1)
    return 0 if npass == len(res) else 1


if __name__ == '__main__':
    sys.exit(main())
