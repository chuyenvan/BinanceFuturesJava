"""LEVZ B1 unit tests on SYNTHETIC data (hand-computed) + independent minute-loop / hour-loop references.
Only real files read: B0 out/grid.parquet (cross-check of the selection rule vs B0's audited choice). No market data.
usage: python3 test/test_b1.py  -> test/test_report.json"""
import os
import sys
CODE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'code')
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) not in (CODE, os.path.dirname(os.path.abspath(__file__)))]
import json
import logging
import math
import traceback
sys.dont_write_bytecode = True
import importlib


def _imp(name):
    sys.path.insert(0, CODE)
    try:
        return importlib.import_module(name)
    finally:
        sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != CODE]


CB = _imp('common_b1')
PA = CB.load('paths')
X = CB.load('exits')
P = CB.load('port')
SB = CB.load('select_b1')
RB = CB.load('rand_b1')
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b1.test')
NP = CB.NPATH
FEE = 0.0007
TESTS = []


def t(fn):
    TESTS.append(fn)
    return fn


def base(v=100.0):
    return np.full(NP, v)


def ex(p, nv=NP, miss=X.BIG, fh=None, gm=None):
    return X.exits_core(p, nv, miss, np.zeros(CB.HMAX + 1) if fh is None else fh, gm)


def g(r, sl, hh, a=0.0, gp=0.0):
    i = CB.xidx(sl, hh, a, gp)
    return int(r['j'][i]), CB.RNAMES[int(r['rs'][i])], float(r['xr'][i])


def close(a, b, tol=1e-12):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


# ------------------------------------------------------------ exits: hand cases
@t
def test_sl_at_close_with_slip():
    p = base()
    p[500] = 115.5
    j, rs, xr = g(ex(p), 0.15, 24)
    assert (j, rs) == (500, 'sl') and close(xr, 115.5 * 1.003 / 100)


@t
def test_sl_not_triggered_below():
    p = base()
    p[500] = 114.99
    j, rs, xr = g(ex(p), 0.15, 24)
    assert (j, rs) == (1440, 'time') and close(xr, 1.0)


@t
def test_sl_exact_threshold_triggers():
    p = base()
    p[500] = 100.0 * (1.0 + 0.30)
    assert g(ex(p), 0.30, 24)[:2] == (500, 'sl')


@t
def test_sl_uses_close_not_wick_order():
    p = base()
    p[10] = 114.0
    p[11] = 150.0
    r = ex(p)
    assert g(r, 0.15, 24)[:2] == (11, 'sl') and g(r, 0.30, 24)[:2] == (11, 'sl') and g(r, 0.50, 24)[:2] == (11, 'sl')


@t
def test_time_stop_exact_H():
    r = ex(base())
    for hh in CB.HS:
        j, rs, xr = g(r, 0.5, hh)
        assert (j, rs) == (60 * hh, 'time') and xr == 1.0


@t
def test_time_price_is_close():
    p = base()
    p[60 * 72] = 91.0
    assert g(ex(p), 0.5, 72) == (4320, 'time', 0.91)


def trail_path():
    p = base()
    p[100:150] = 96.9
    p[150] = 94.0
    p[151:200] = 95.5
    p[200:] = 97.0
    return p


@t
def test_trail_activation_trough_exit():
    r = ex(trail_path())
    j, rs, xr = g(r, 0.5, 24, 0.03, 0.02)
    assert (j, rs) == (200, 'trail') and close(xr, 97.0 * 1.001 / 100)


@t
def test_trail_gap_not_reached():
    r = ex(trail_path())
    assert g(r, 0.5, 24, 0.03, 0.05)[:2] == (1440, 'time')


@t
def test_trail_gap3_and_arm5():
    r = ex(trail_path())
    assert g(r, 0.5, 24, 0.03, 0.03)[:2] == (200, 'trail')
    assert g(r, 0.5, 24, 0.05, 0.02)[:2] == (200, 'trail')


@t
def test_trail_never_armed():
    r = ex(trail_path())
    for a in (0.07, 0.10):
        for gp in CB.GAPS:
            assert g(r, 0.5, 24, a, gp)[:2] == (1440, 'time')


@t
def test_trail_arm_and_exit_not_same_minute():
    p = base()
    p[100] = 96.0
    p[101:] = 96.0 * 1.02
    assert g(ex(p), 0.5, 24, 0.03, 0.02)[:2] == (101, 'trail')


@t
def test_trail_trough_only_since_activation():
    p = base()
    p[50] = 97.5
    p[100] = 96.9
    p[101] = 96.9 * 1.02 + 0.01
    p[102:] = 96.9 * 1.02 + 0.01
    assert g(ex(p), 0.5, 24, 0.03, 0.02)[:2] == (101, 'trail')


@t
def test_trail_trough_moves_down():
    p = base()
    p[100] = 96.0
    p[101] = 90.0
    p[102] = 96.0 * 1.02 - 0.5
    p[103:] = 90.0 * 1.02 + 0.001
    assert g(ex(p), 0.5, 24, 0.03, 0.02)[:2] == (102, 'trail')


@t
def test_trail_off_never_trail():
    rng = np.random.default_rng(1)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.004, NP)))
    p = p / p[0] * 100
    r = ex(p)
    for i, (sl, hh, a, gp) in enumerate(CB.XCFGS):
        if a == 0.0:
            assert CB.RNAMES[int(r['rs'][i])] != 'trail'


@t
def test_priority_sl_over_trail_same_minute():
    p = base()
    p[100] = 96.9
    p[101:] = 115.5
    j, rs, xr = g(ex(p), 0.15, 24, 0.03, 0.02)
    assert (j, rs) == (101, 'sl') and close(xr, 115.5 * 1.003 / 100)


@t
def test_priority_trail_over_time_same_minute():
    p = base()
    p[100:] = 96.9
    p[1440] = 99.0
    j, rs, xr = g(ex(p), 0.5, 24, 0.03, 0.02)
    assert (j, rs) == (1440, 'trail') and close(xr, 0.99 * 1.001)


@t
def test_priority_sl_over_time_same_minute():
    p = base()
    p[1440] = 116.0
    assert g(ex(p), 0.15, 24)[:2] == (1440, 'sl')


@t
def test_eod_when_short_path():
    p = base()
    r = ex(p, nv=1000)
    assert g(r, 0.5, 24) == (999, 'eod', 1.0)


@t
def test_events_beyond_nv_ignored():
    p = base()
    p[1200:] = 200.0
    r = ex(p, nv=1000)
    assert g(r, 0.15, 24)[:2] == (999, 'eod')


@t
def test_funding_window():
    fh = np.zeros(CB.HMAX + 1)
    fh[1:] = 0.001 * np.arange(1, CB.HMAX + 1)
    p = base()
    r = ex(p, fh=fh)
    assert close(float(r['fund'][CB.xidx(0.5, 24, 0, 0)]), 0.001 * 300)
    p2 = base()
    p2[59] = 120.0
    r2 = ex(p2, fh=fh)
    assert g(r2, 0.15, 24)[:2] == (59, 'sl') and close(float(r2['fund'][CB.xidx(0.15, 24, 0, 0)]), 0.001)
    p3 = base()
    p3[58] = 120.0
    r3 = ex(p3, fh=fh)
    assert float(r3['fund'][CB.xidx(0.15, 24, 0, 0)]) == 0.0


@t
def test_mx_and_mxh():
    p = base()
    p[300] = 110.0
    p[1400] = 105.0
    r = ex(p)
    i = CB.xidx(0.5, 24, 0, 0)
    assert close(float(r['mx'][i]), 1.10) and close(float(r['mxh'][i]), 1.05)


@t
def test_hourly_core():
    p = base()
    p[60] = 101.0
    p[61] = 103.0
    p[120] = 99.0
    mk, hm = X.hourly_core(p, None)
    assert close(mk[1], 1.01) and close(mk[2], 0.99) and close(hm[1], 1.01) and close(hm[2], 1.03) and hm[0] == 1.0


def ref_exit(p, nv, miss_m, sl, hh, a, gp):
    p0 = p[0]
    armed, tr = False, math.inf
    for i in range(1, nv):
        c = p[i]
        if c >= p0 * (1.0 + sl):
            return i, 'sl', c * 1.003 / p0
        if a > 0:
            if armed and c >= tr * (1.0 + gp):
                return i, 'trail', c * 1.001 / p0
            if not armed and c <= p0 * (1.0 - a):
                armed, tr = True, c
            elif armed:
                tr = min(tr, c)
        if i == 60 * hh:
            return i, 'time', c / p0
        if i == miss_m:
            return i, 'miss', c / p0
    return nv - 1, 'eod', p[nv - 1] / p0


@t
def test_exits_vs_minute_loop_reference():
    rng = np.random.default_rng(7)
    nbad = 0
    for trial in range(3):
        p = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, NP)))
        p[0] = 100.0
        nv = NP if trial < 2 else 20000
        miss = 5000 if trial == 1 else X.BIG
        r = X.exits_core(p, nv, miss, np.zeros(CB.HMAX + 1))
        for i, (sl, hh, a, gp) in enumerate(CB.XCFGS):
            jr, rr, xr = ref_exit(p, nv, miss, sl, hh, a, gp)
            if not (int(r['j'][i]) == jr and CB.RNAMES[int(r['rs'][i])] == rr and close(float(r['xr'][i]), xr)):
                nbad += 1
    assert nbad == 0, nbad


@t
def test_gap_monotone():
    rng = np.random.default_rng(3)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, NP)))
    p[0] = 100.0
    r = ex(p)
    for a in CB.ARMS:
        js = [int(r['j'][CB.xidx(0.5, 720, a, gp)]) for gp in CB.GAPS]
        assert js[0] <= js[1] <= js[2]


@t
def test_exits_no_lookahead_price():
    rng = np.random.default_rng(11)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, NP)))
    p[0] = 100.0
    r = ex(p)
    for m in (500, 3000, 15000):
        q = p.copy()
        q[m + 1:] = q[m + 1:] * np.exp(rng.normal(0, 0.05, NP - m - 1))
        r2 = ex(q)
        sel = r['j'] <= m
        assert sel.any()
        assert (r['j'][sel] == r2['j'][sel]).all() and (r['rs'][sel] == r2['rs'][sel]).all() and np.allclose(r['xr'][sel], r2['xr'][sel], rtol=0, atol=0)
        assert (r2['j'][~sel] > m).all()


@t
def test_exits_deterministic():
    rng = np.random.default_rng(5)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, NP)))
    p[0] = 100.0
    a, b = ex(p), ex(p.copy())
    for kk in X.OUTK:
        assert np.array_equal(a[kk], b[kk])


# ------------------------------------------------------------ paths / store
@t
def test_ffill_gaps():
    row = np.array([np.nan, np.nan, 1.0, np.nan, np.nan, 2.0, np.nan])
    ff, st, en, f, pr = PA.ffill_gaps(row)
    assert f == 2 and list(st) == [3, 6] and list(en) == [5, 7]
    assert np.isnan(ff[0]) and np.isnan(ff[1]) and list(ff[2:]) == [1.0, 1.0, 1.0, 2.0, 2.0]


def mkstore(rows, NHs, FR=None):
    ns = len(rows)
    mm = np.zeros((ns, NHs * 60), dtype=np.float32)
    gc, g0, g1 = [], [], []
    for c, row in enumerate(rows):
        ff, st, en, f, pr = PA.ffill_gaps(np.asarray(row, dtype=np.float64))
        mm[c] = ff
        gc += [c] * len(st)
        g0 += list(st)
        g1 += list(en)
    if FR is None:
        FR = np.zeros((NHs, ns))
    return X.Store(mm=mm, gaps=(np.array(gc, dtype=np.int64), np.array(g0, dtype=np.int64), np.array(g1, dtype=np.int64)), FR=FR)


@t
def test_missing_run_over_24h_exit():
    NHs = 800
    row = np.full(NHs * 60, 100.0)
    b = 60 * 10
    row[b + 300:b + 300 + 1441] = np.nan
    st = mkstore([row], NHs)
    p, nv, miss_m, gm, fh, lg = X.path_of(st, 0, 10)
    assert miss_m == 300 + 1440 and lg
    r = X.exits_core(p, nv, miss_m, fh, gm)
    i = CB.xidx(0.5, 72, 0, 0)
    assert (int(r['j'][i]), CB.RNAMES[int(r['rs'][i])], int(r['flag'][i])) == (1740, 'miss', 1)
    i24 = CB.xidx(0.5, 24, 0, 0)
    assert (int(r['j'][i24]), CB.RNAMES[int(r['rs'][i24])], int(r['flag'][i24])) == (1440, 'time', 1)


@t
def test_missing_run_exactly_24h_no_exit():
    NHs = 800
    row = np.full(NHs * 60, 100.0)
    b = 60 * 10
    row[b + 300:b + 300 + 1440] = np.nan
    st = mkstore([row], NHs)
    p, nv, miss_m, gm, fh, lg = X.path_of(st, 0, 10)
    assert miss_m == X.BIG and not lg
    r = X.exits_core(p, nv, miss_m, fh, gm)
    assert g(r, 0.5, 72)[:2] == (4320, 'time')


@t
def test_missing_minutes_hold_last_price_no_trigger():
    NHs = 800
    row = np.full(NHs * 60, 100.0)
    b = 600
    row[b + 100] = 96.0
    row[b + 101:b + 600] = np.nan
    row[b + 600:] = 96.0
    st = mkstore([row], NHs)
    p, nv, miss_m, gm, fh, lg = X.path_of(st, 0, 10)
    assert (p[101:600] == 96.0).all() and gm[101:600].all() and not gm[100]
    r = X.exits_core(p, nv, miss_m, fh, gm)
    assert g(r, 0.5, 24, 0.03, 0.02)[:2] == (1440, 'time')


@t
def test_path_funding_from_FR():
    NHs = 800
    row = np.full(NHs * 60, 100.0)
    row[600 + 59] = 110.0
    FR = np.zeros((NHs, 1))
    FR[11, 0] = 0.0001
    FR[12, 0] = -0.0002
    st = mkstore([row], NHs, FR)
    p, nv, miss_m, gm, fh, lg = X.path_of(st, 0, 10)
    assert close(fh[1], 0.0001 * 1.10) and close(fh[2], -0.0002) and fh[3] == 0.0


@t
def test_path_end_of_data():
    NHs = 800
    st = mkstore([np.full(NHs * 60, 100.0)], NHs)
    p, nv, miss_m, gm, fh, lg = X.path_of(st, 0, NHs - 10)
    assert nv == 600 and len(p) == NP
    r = X.exits_core(p, nv, miss_m, fh, gm)
    assert g(r, 0.5, 24)[:2] == (599, 'eod')


# ------------------------------------------------------------ port: hand cases
def mkT(n, j, rs, xr, fund=None, mk=None, hm=None, fh=None, mxh=None):
    def col(v, dt):
        return np.repeat(np.asarray(v, dtype=dt).reshape(n, 1), 195, axis=1)
    fh = np.zeros((n, CB.HMAX + 1)) if fh is None else fh
    fc = np.cumsum(fh, axis=1)
    if fund is None:
        fund = [fc[i, min((int(j[i]) + 1) // 60, CB.HMAX)] for i in range(n)]
    T = dict(j=col(j, np.int32), rs=col(rs, np.int8), xr=col(xr, float), fund=col(fund, float),
             mx=col(np.ones(n) if mxh is None else mxh, float), mxh=col(np.ones(n) if mxh is None else mxh, float),
             flag=col(np.zeros(n), np.int8), mk=np.ones((n, CB.HMAX + 1)) if mk is None else mk,
             hm=np.ones((n, CB.HMAX + 1)) if hm is None else hm, fh=fh, fc=fc)
    return T


def mkcand(rows):
    a = np.array(rows, dtype=float)
    return P.CandB1(a[:, 0].astype(np.int64), a[:, 1].astype(np.int64), a[:, 2], a[:, 3].astype(np.int64))


@t
def test_port_single_trade_hand():
    fh = np.zeros((1, CB.HMAX + 1))
    fh[0, 1:25] = 0.001 / 24
    T = mkT(1, [1440], [CB.R_TIME], [0.9], fh=fh)
    tr, eq, m = P.run(1, mkcand([(100, 0, 5.0, 0)]), P.XView(T, 0), 100, 400)
    N = 6000.0
    net = N * 0.1 - N * FEE - N * 0.9 * FEE + N * 0.001
    assert len(tr) == 1 and close(float(tr['net'].iloc[0]), net, 1e-12)
    assert close(m['eq_end'], 10000 + net, 1e-12) and abs(m['acct_err']) < 1e-9
    assert int(tr['kx'].iloc[0]) == 124 and close(float(eq['eq'].iloc[24]), 10000 + net, 1e-12)


@t
def test_port_fees_and_size():
    T = mkT(2, [60, 60], [CB.R_TIME] * 2, [1.0, 1.0])
    tr, eq, m = P.run(2, mkcand([(100, 0, 5.0, 0), (100, 1, 4.0, 1)]), P.XView(T, 0), 100, 400)
    assert (tr['notional_in'] == 3000.0).all()
    assert close(float(tr['fees'].sum()), 4 * 3000 * FEE, 1e-12) and close(m['eq_end'], 10000 - 4 * 3000 * FEE, 1e-12)


@t
def test_port_size_uses_mtm_equity():
    mk = np.ones((2, CB.HMAX + 1))
    mk[0, 1:] = 0.9
    T = mkT(2, [43200, 60], [CB.R_TIME] * 2, [0.9, 1.0], mk=mk)
    tr, eq, m = P.run(2, mkcand([(100, 0, 5.0, 0), (101, 1, 5.0, 1)]), P.XView(T, 0), 100, 400)
    N0 = 3000.0
    eq101 = 10000 - N0 * FEE + N0 * 0.1
    assert close(float(tr.loc[tr['c'] == 1, 'notional_in'].iloc[0]), eq101 * 0.6 / 2, 1e-12)


@t
def test_port_slot_free_next_hour_mid_hour_exit():
    T = mkT(3, [61, 60, 60], [CB.R_SL] * 3, [1.0] * 3)
    tr, eq, m = P.run(1, mkcand([(100, 0, 5, 0), (101, 1, 5, 1), (102, 2, 5, 2)]), P.XView(T, 0), 100, 400)
    assert sorted(tr['c'].tolist()) == [0, 2]
    T2 = mkT(3, [60, 60, 60], [CB.R_SL] * 3, [1.0] * 3)
    tr2, _, _ = P.run(1, mkcand([(100, 0, 5, 0), (101, 1, 5, 1), (102, 2, 5, 2)]), P.XView(T2, 0), 100, 400)
    assert sorted(tr2['c'].tolist()) == [0, 1, 2]


@t
def test_port_cooldown_72h():
    T = mkT(3, [60, 60, 60], [CB.R_TIME] * 3, [1.0] * 3)
    tr, _, _ = P.run(3, mkcand([(100, 0, 5, 0), (172, 0, 5, 1), (173, 0, 5, 2)]), P.XView(T, 0), 100, 400)
    assert sorted(tr['ke'].tolist()) == [100, 173]


@t
def test_port_held_coin_skipped():
    T = mkT(2, [43200, 60], [CB.R_TIME] * 2, [1.0] * 2)
    tr, _, _ = P.run(3, mkcand([(100, 0, 5, 0), (200, 0, 5, 1)]), P.XView(T, 0), 100, 400)
    assert len(tr) == 1


@t
def test_port_topk_tiebreak():
    T = mkT(3, [60] * 3, [CB.R_TIME] * 3, [1.0] * 3)
    tr, _, _ = P.run(2, mkcand([(100, 3, 5.0, 0), (100, 1, 5.0, 1), (100, 2, 6.0, 2)]), P.XView(T, 0), 100, 400)
    assert sorted(tr['c'].tolist()) == [1, 2]


@t
def test_port_eod_and_no_entry_at_last_hour():
    mk = np.ones((2, CB.HMAX + 1))
    mk[0, 10] = 1.05
    T = mkT(2, [43200, 60], [CB.R_TIME] * 2, [0.8, 1.0], mk=mk)
    tr, _, m = P.run(3, mkcand([(390, 0, 5, 0), (400, 1, 5, 1)]), P.XView(T, 0), 100, 400)
    assert len(tr) == 1 and tr['reason'].iloc[0] == 'eod' and close(float(tr['xr'].iloc[0]), 1.05) and int(tr['kx'].iloc[0]) == 400


@t
def test_port_funding_sign():
    fh = np.zeros((1, CB.HMAX + 1))
    fh[0, 8] = 0.0001
    T = mkT(1, [1440], [CB.R_TIME], [1.0], fh=fh)
    tr, _, m = P.run(1, mkcand([(100, 0, 5, 0)]), P.XView(T, 0), 100, 400)
    assert close(float(tr['funding'].iloc[0]), 6000 * 0.0001) and float(tr['funding'].iloc[0]) > 0


@t
def test_port_worst_uses_hour_max():
    mk = np.ones((1, CB.HMAX + 1))
    hm = np.ones((1, CB.HMAX + 1))
    hm[0, 5] = 1.2
    T = mkT(1, [1440], [CB.R_TIME], [1.0], mk=mk, hm=hm)
    tr, eq, m = P.run(1, mkcand([(100, 0, 5, 0)]), P.XView(T, 0), 100, 400)
    assert close(float(eq['eq'].iloc[5] - eq['eq_worst'].iloc[5]), 6000 * 0.2, 1e-12)
    assert m['maxdd_worst'] > 0.11 and m['maxdd'] < 0.001


@t
def test_port_worst_exit_hour_premax():
    T = mkT(1, [130], [CB.R_TRAIL], [1.0], mxh=[1.1])
    tr, eq, m = P.run(1, mkcand([(100, 0, 5, 0)]), P.XView(T, 0), 100, 400)
    assert close(float(eq['eq'].iloc[3] - eq['eq_worst'].iloc[3]), 6000 * 0.1, 1e-12)


# ------------------------------------------------------------ port: synthetic integration + references
def synth(seed, ns=6, NHs=1600, ncand=120, kmax=800):
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(ns):
        r = 50 * np.exp(np.cumsum(rng.normal(0, 0.004, NHs * 60)))
        for _ in range(3):
            a = int(rng.integers(0, NHs * 60 - 3000))
            r[a:a + int(rng.integers(10, 2500))] = np.nan
        r[:60] = 50.0
        rows.append(r)
    FR = np.zeros((NHs, ns))
    FR[::8] = rng.normal(0.0001, 0.0003, (len(FR[::8]), ns))
    st = mkstore(rows, NHs, FR)
    pr = np.isfinite(np.array([rows[c][::60] for c in range(ns)])).T
    ks, cs = [], []
    while len(ks) < ncand:
        k, c = int(rng.integers(5, kmax)), int(rng.integers(0, ns))
        if pr[k, c] and (k, c) not in set(zip(ks, cs)):
            ks.append(k)
            cs.append(c)
    ks, cs = np.array(ks), np.array(cs)
    T = X.compute(st, ks, cs)
    sc = rng.normal(3, 1, len(ks))
    return st, T, ks, cs, sc, rng


def ref_port(K, ks, cs, sc, T, xi, k0, kl):
    """independent hour-by-hour loop (B0 structure)."""
    xv = P.XView(T, xi)
    cash = 10000.0
    pos = {}
    last = {}
    trades = []
    eqs = []
    byk = {}
    for i in np.lexsort((cs, -sc, ks)):
        byk.setdefault(int(ks[i]), []).append((int(cs[i]), int(i)))
    for k in range(k0, kl + 1):
        for c in sorted(pos):
            p = pos[c]
            h = k - p['ke']
            if h >= 1 and 60 * h - 1 <= p['j']:
                cash += p['N'] * xv.fh[p['cid'], h]
            kx = p['ke'] + (p['j'] + 59) // 60
            if kx <= k or k == kl:
                xr = xv.xr[p['cid']] if kx <= k else xv.mk[p['cid'], h]
                cash += p['N'] * (1 - xr) - p['N'] * xr * FEE
                trades.append((c, p['ke'], k))
                del pos[c]
        eq = cash + sum(p['N'] * (1 - xv.mk[p['cid'], k - p['ke']]) for p in pos.values())
        if k < kl and k in byk and len(pos) < K:
            size = eq * 0.6 / K
            for c, cid in byk[k]:
                if len(pos) >= K:
                    break
                if c in pos or (c in last and k - last[c] <= 72):
                    continue
                pos[c] = dict(ke=k, N=size, cid=cid, j=int(xv.j[cid]))
                last[c] = k
                cash -= size * FEE
        eqs.append(cash + sum(p['N'] * (1 - xv.mk[p['cid'], k - p['ke']]) for p in pos.values()))
    return sorted(trades), np.array(eqs), cash


@t
def test_port_vs_hour_loop_reference():
    st, T, ks, cs, sc, rng = synth(21)
    cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
    for xi in (0, 7, 50, 120, 194):
        for K in (1, 3):
            tr, eq, m = P.run(K, cand, P.XView(T, xi), 5, 1000)
            rt, req, rcash = ref_port(K, ks, cs, sc, T, xi, 5, 1000)
            assert sorted(zip(tr['c'], tr['ke'], tr['kx'])) == rt, (xi, K)
            assert np.allclose(eq['eq'].values, req, rtol=0, atol=1e-8), (xi, K, np.abs(eq['eq'].values - req).max())
            assert abs(m['eq_end'] - rcash) < 1e-8


@t
def test_port_accounting_invariant():
    worst = 0.0
    for seed in (1, 2, 3):
        st, T, ks, cs, sc, rng = synth(seed)
        cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
        for xi in range(0, 195, 13):
            for K in (3, 5, 10):
                tr, eq, m = P.run(K, cand, P.XView(T, xi), 5, 1000)
                worst = max(worst, abs(m['acct_err']), abs(float(tr['net'].sum()) - (float(eq['eq'].iloc[-1]) - 10000)))
    assert worst <= 1e-6, worst


@t
def test_port_phase1_equity_matches_ledger():
    st, T, ks, cs, sc, rng = synth(4)
    cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
    dbg = []
    tr, eq, m = P.run(3, cand, P.XView(T, 60), 5, 1000, debug=dbg)
    fees_at = tr.groupby('ke')['notional_in'].sum() * FEE
    e = eq['eq'].values
    for k, v in dbg:
        assert abs(v - (e[k - 5] + float(fees_at.get(k, 0.0)))) < 1e-8


@t
def test_port_max_K_open():
    st, T, ks, cs, sc, rng = synth(5, ncand=200)
    cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
    for K in (1, 3, 5):
        tr, eq, m = P.run(K, cand, P.XView(T, CB.xidx(0.5, 720, 0, 0)), 5, 1000)
        cnt = np.zeros(1001)
        for a, b in zip(tr['ke'], tr['kx']):
            cnt[a:b] += 1
        assert cnt.max() <= K and len(tr) > 0


@t
def test_port_worst_le_close():
    st, T, ks, cs, sc, rng = synth(6)
    cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
    tr, eq, m = P.run(5, cand, P.XView(T, 100), 5, 1000)
    assert (eq['eq_worst'].values <= eq['eq'].values + 1e-9).all() and m['maxdd_worst'] >= m['maxdd']


@t
def test_port_no_lookahead_signals():
    st, T, ks, cs, sc, rng = synth(8, ncand=200)
    cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
    t0 = 400
    tr, _, _ = P.run(3, cand, P.XView(T, 40), 5, 1000)
    sc2 = sc.copy()
    late = ks > t0
    sc2[late] = rng.normal(3, 1, late.sum())
    keep = ~(late & (rng.random(len(ks)) < 0.5))
    cand2 = P.CandB1(ks[keep], cs[keep], sc2[keep], np.arange(len(ks))[keep])
    tr2, _, _ = P.run(3, cand2, P.XView(T, 40), 5, 1000)
    a = tr[tr['ke'] <= t0][['c', 'ke', 'kx', 'j', 'net']].reset_index(drop=True)
    b = tr2[tr2['ke'] <= t0][['c', 'ke', 'kx', 'j', 'net']].reset_index(drop=True)
    assert len(a) > 0 and a.equals(b)


@t
def test_port_no_lookahead_prices():
    NHs = 1600
    rng = np.random.default_rng(9)
    rows = [50 * np.exp(np.cumsum(rng.normal(0, 0.004, NHs * 60))) for _ in range(4)]
    ks = np.array([10, 30, 60, 90, 200, 300, 450, 600])
    cs = np.array([0, 1, 2, 3, 0, 1, 2, 3])
    sc = np.ones(len(ks))
    Mx = 60 * 320
    T = X.compute(mkstore(rows, NHs), ks, cs)
    rows2 = [r.copy() for r in rows]
    for r in rows2:
        r[Mx + 1:] *= np.exp(rng.normal(0, 0.05, len(r) - Mx - 1))
    T2 = X.compute(mkstore(rows2, NHs), ks, cs)
    cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
    for xi in (5, 77, 150):
        tr, _, _ = P.run(2, cand, P.XView(T, xi), 5, 1000)
        tr2, _, _ = P.run(2, cand, P.XView(T2, xi), 5, 1000)
        ab = (tr['ke'] * 60 + tr['j'] <= Mx)
        a = tr[ab][['c', 'ke', 'j', 'xr']].reset_index(drop=True)
        b = tr2[tr2['ke'] * 60 + tr2['j'] <= Mx][['c', 'ke', 'j', 'xr']].reset_index(drop=True)
        assert a.equals(b)
        assert tr[tr['ke'] <= Mx // 60][['c', 'ke']].reset_index(drop=True).equals(tr2[tr2['ke'] <= Mx // 60][['c', 'ke']].reset_index(drop=True))


@t
def test_port_deterministic():
    st, T, ks, cs, sc, rng = synth(10)
    cand = P.CandB1(ks, cs, sc, np.arange(len(ks)))
    a = P.run(3, cand, P.XView(T, 33), 5, 1000)
    b = P.run(3, cand, P.XView(T, 33), 5, 1000)
    assert a[0].equals(b[0]) and a[1].equals(b[1])


# ------------------------------------------------------------ selection
def synth_grid(seed):
    GB = CB.load('grid_b1')
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(GB.all_cfgs())
    n = len(df)
    for f in ('DEV', 'F1', 'F2', 'F3'):
        df[f + '_ret'] = rng.normal(0.02, 0.1, n)
        df[f + '_maxdd_worst'] = rng.uniform(0.05, 0.35, n)
        df[f + '_n'] = rng.integers(20, 200, n)
    return df


@t
def test_restrict_drops_test_folds():
    df = synth_grid(1)
    d = SB.restrict(df, ('F1',))
    assert 'F1_ret' in d.columns and not any(c.startswith(('F2_', 'F3_', 'DEV_')) for c in d.columns)


@t
def test_wfo_trap_best_on_test_fold_not_selected():
    df = synth_grid(2)
    trap = 1234
    df.loc[df['cfg_id'] == trap, ['F2_ret', 'F3_ret', 'F2_n', 'F3_n']] = [5.0, 5.0, 500, 500]
    df.loc[df['cfg_id'] == trap, ['F1_ret']] = -0.05
    w = SB.wfo(df)
    R = SB.rule(df, ('F1',), 'folds')
    assert trap not in R['passing20'] and w['2024']['chosen'] != trap
    df2 = df.copy()
    rng = np.random.default_rng(0)
    for c in ('F2_ret', 'F3_ret', 'F2_maxdd_worst', 'F3_maxdd_worst', 'F2_n', 'F3_n', 'DEV_ret', 'DEV_maxdd_worst'):
        df2[c] = rng.permutation(df2[c].values)
    R2 = SB.rule(df2, ('F1',), 'folds')
    assert R2['passing20'] == R['passing20'] and R2['chosen'] == R['chosen']
    R3 = SB.rule(df, ('F1', 'F2'), 'folds')
    df3 = df.copy()
    df3['F3_ret'] = rng.permutation(df3['F3_ret'].values)
    assert SB.rule(df3, ('F1', 'F2'), 'folds')['passing20'] == R3['passing20']


@t
def test_neighbours_trailing():
    base_ = dict(W=14, E='E0', zmin=3.0, K=5, SL=0.30, H=168)
    off = SB.neighbours(dict(base_, arm=0.0, gap=0.0))
    tn = [(d['arm'], d['gap']) for d in off if (d['arm'], d['gap']) != (0.0, 0.0)]
    assert sorted(tn) == [(0.10, 0.02), (0.10, 0.03), (0.10, 0.05)] and len(off) == 13
    nb = SB.neighbours(dict(base_, arm=0.10, gap=0.05))
    tn = sorted((d['arm'], d['gap']) for d in nb if (d['arm'], d['gap']) != (0.10, 0.05))
    assert tn == [(0.0, 0.0), (0.07, 0.05), (0.10, 0.03)]


@t
def test_plateau_threshold():
    rows = [dict(cfg_id=0, a=0, F1_ret=1.0, F1_maxdd_worst=0.1, F1_n=50)]
    for i in range(1, 6):
        rows.append(dict(cfg_id=i, a=i, F1_ret=(0.1 if i <= 3 else -0.1), F1_maxdd_worst=0.5, F1_n=50))
    df = pd.DataFrame(rows)
    nb = lambda r: [dict(a=i) for i in range(1, 6)] if r['a'] == 0 else [dict(a=0)]
    R = SB.rule(df, ('F1',), 'folds', neigh=nb, key=lambda d: d['a'], pkeys=('a',))
    assert R['chosen'] == 0
    df.loc[df['a'] == 3, 'F1_ret'] = -0.1
    R = SB.rule(df, ('F1',), 'folds', neigh=nb, key=lambda d: d['a'], pkeys=('a',))
    assert R['chosen'] is None


@t
def test_rule_reproduces_B0_choice_on_B0_grid():
    S0 = CB.load_b0('sim')
    SEL0 = CB.load_b0('select')
    df = pd.read_parquet(CB.L2 + '/out/grid.parquet')
    R = SB.rule(df, ('F1', 'F2', 'F3'), 'DEV', neigh=lambda r: SEL0.neighbours(r, S0.GRID),
                key=lambda d: tuple(d[p] for p in S0.PKEYS), pkeys=S0.PKEYS)
    assert R['chosen'] == 759 and int(R['d']['valid'].sum()) == 69
    _, ranked, tried, chosen = SEL0.select(df, S0.GRID, S0.PKEYS)
    assert int(chosen['cfg_id']) == 759


# ------------------------------------------------------------ random control
@t
def test_rand_draw_counts_and_pool():
    rng = np.random.default_rng(0)
    I = RB.Shim()
    I.tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    I.U = rng.random((CB.NH, 4)) < 0.5
    has = rng.random((CB.NH, 4)) < 0.9
    I.px = {'CL': np.where(has, 1.0, np.nan)}
    real = RB.Shim()
    kk = np.sort(rng.choice(np.arange(800, CB.NH), 300, replace=False))
    real.ck, real.cc = kk, rng.integers(0, 4, 300)
    pools = RB.R0.build_pools(I, real)
    ek, ec = RB.R0.episode_starts(real.ck, real.cc)
    a = RB.R0.draw(pools, np.random.default_rng([1, 2, 3]))
    b = RB.R0.draw(pools, np.random.default_rng([1, 2, 3]))
    assert np.array_equal(a.ck, b.ck) and np.array_equal(a.cc, b.cc)
    assert len(a.ck) == sum(p[0] for p in pools)
    assert (I.U[a.ck, a.cc] & has[a.ck, a.cc]).all()
    mk = RB.R0.month_keys(I.tms)
    k0 = CB.H0
    dev = (ek >= (1640995200000 - CB.H0) // CB.H)
    assert len(a.ck) == int(dev.sum())
    assert pd.Series(mk[a.ck]).value_counts().sort_index().equals(pd.Series(mk[ek[dev]]).value_counts().sort_index())


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    res = []
    for fn in TESTS:
        try:
            fn()
            res.append((fn.__name__, 'PASS', ''))
        except Exception:
            res.append((fn.__name__, 'FAIL', traceback.format_exc()[-1500:]))
        log.info('%s %s', res[-1][1], fn.__name__)
    npass = sum(r[1] == 'PASS' for r in res)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_report.json'), 'w') as fh:
        json.dump(dict(passed=npass, total=len(res), results=res), fh, indent=1)
    log.info('TESTS %d/%d', npass, len(res))
    for r in res:
        if r[1] == 'FAIL':
            log.info('FAIL %s\n%s', r[0], r[2])
    return npass == len(res)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
