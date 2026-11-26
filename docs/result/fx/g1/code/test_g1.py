"""Tests for FX G1 (plain python3). Real data is used ONLY for loading / universe / position-level causality checks
(no returns, no performance statistics). Usage: python3 test_g1.py [--data DIR] [--only a,b,...]"""
import argparse
import csv
import json
import logging
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import load_g1 as L  # noqa: E402
import sim_g1 as S  # noqa: E402
import eval_g1 as E  # noqa: E402

LOG = logging.getLogger("g1.test")


# ------------------------------------------------------------------ helpers
def bdays(a, b):
    return pd.bdate_range(a, b)


def make_data(dates, ccys, P, rates, vix=None, cutoff=None):
    """P = USD per foreign unit (n, c); raw is derived in the FRED quote direction of each ccy."""
    quote = {c: L.FX[c][1] for c in ccys}
    raw = np.column_stack([P[:, j] if quote[c] == L.USD_PER else 1.0 / P[:, j] for j, c in enumerate(ccys)])
    vix = np.full(len(dates), 15.0) if vix is None else vix
    return L.G1Data(dates, ccys, quote, raw, rates, vix, cutoff or dates[-1])


def const_rates(months, ccys, usd, rmap):
    idx = pd.period_range(months[0], months[1], freq="M")
    df = pd.DataFrame({"USD": usd}, index=idx)
    for c in ccys:
        df[c] = rmap[c]
    return df


def _write_fred(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "v"])
        for d, v in rows:
            w.writerow([d, v])


def _fake_dir(tmp, fx_rows, extra_after_cutoff=False):
    """Write a minimal fake derived/ dir. fx_rows: {ccy: [(date, value), ...]}."""
    for c in L.CCYS:
        rows = list(fx_rows[c])
        if extra_after_cutoff:
            rows.append(("2020-01-02", "999"))
        _write_fred(os.path.join(tmp, "FRED_%s.csv" % L.FX[c][0]), rows)
    for c, code in L.RATE.items():
        rows = [("1999-11-01", "1.0"), ("1999-12-01", "1.0")]
        if extra_after_cutoff:
            rows.append(("2020-01-01", "9"))
        _write_fred(os.path.join(tmp, "FRED_IR3TIB01%sM156N.csv" % code), rows)
    vrows = [("2000-01-03", "20"), ("2000-01-04", "21")]
    if extra_after_cutoff:
        vrows.append(("2020-01-02", "50"))
    _write_fred(os.path.join(tmp, "FRED_VIXCLS.csv"), vrows)


# ------------------------------------------------------------------ (a) quote direction
def test_a_quote_direction():
    expect = {"DEXUSEU": L.USD_PER, "DEXUSUK": L.USD_PER, "DEXUSAL": L.USD_PER, "DEXUSNZ": L.USD_PER,
              "DEXJPUS": L.CCY_PER, "DEXSZUS": L.CCY_PER, "DEXCAUS": L.CCY_PER, "DEXNOUS": L.CCY_PER,
              "DEXSDUS": L.CCY_PER}
    for c in L.CCYS:
        assert expect[L.FX[c][0]] == L.FX[c][1], c
    tmp = tempfile.mkdtemp(prefix="g1a_")
    try:
        # foreign ccy appreciates +1% vs USD between day 1 and day 2 (hand answer: long return = +0.01)
        rows = {}
        for c in L.CCYS:
            if L.FX[c][1] == L.USD_PER:
                rows[c] = [("2000-01-03", "1.0000"), ("2000-01-04", "1.0100")]
            else:
                rows[c] = [("2000-01-03", "101.00"), ("2000-01-04", "100.00")]
        _write_fred_all = _fake_dir(tmp, rows)  # noqa: F841
        d = L.load(tmp, cutoff="2019-12-31")
        for j, c in enumerate(d.ccys):
            r = d.P[1, j] / d.P[0, j] - 1.0
            assert abs(r - 0.01) < 1e-12, (c, r)
        # also a LONG position in the sim gains: one-ccy buy-hold over the 2 rows
    finally:
        shutil.rmtree(tmp)
    # DEXJPUS 110 -> 100 means JPY appreciated 10%: long JPY return = +10%
    p = L.to_usd_per(np.array([110.0, 100.0]), L.CCY_PER)
    assert abs(p[1] / p[0] - 1 - 0.10) < 1e-12


# ------------------------------------------------------------------ (b) causality on REAL data (positions only)
def _sched_key(ev, upto_row):
    return [(e["kind"], e["row"], tuple(sorted(e["targets"].items())), e["gate"]) for e in ev if e["row"] <= upto_row]


def _perturb(data, t_row, seed):
    rng = np.random.default_rng(seed)
    raw = data.raw.copy()
    n = len(data.dates)
    noise = np.exp(rng.normal(0, 0.05, size=(n - t_row - 1, raw.shape[1])))
    raw[t_row + 1:] = raw[t_row + 1:] * noise
    vix = data.vix.copy()
    vix[t_row + 1:] = rng.uniform(5, 90, size=n - t_row - 1)
    rates = data.rates.copy()
    mt = data.month[t_row]
    sel = rates.index >= mt
    rates.loc[sel] = rng.uniform(-5, 20, size=(int(sel.sum()), rates.shape[1]))
    return L.G1Data(data.dates, data.ccys, data.quote, raw, rates, vix, data.cutoff)


def test_b_causality_real(data_dir):
    d = L.load(data_dir)
    assert d.dates.max() <= pd.Timestamp("2019-12-31")
    probes = ["1998-08-14", "2005-12-30", "2008-10-15", "2008-10-31", "2013-06-20", "2019-11-29"]
    cfgs = [(2, None), (3, None), (2, ("FXVOL", 0.8, 3)), (3, ("FXVOL", 0.9, 10)), (2, ("VIX", 0.9, 3))]
    for i, p in enumerate(probes):
        t = int(np.searchsorted(d.dates.values, np.datetime64(p), "right") - 1)
        d2 = _perturb(d, t, 100 + i)
        for k, g in cfgs:
            e1, _ = S.build_schedule(d, k, g)
            e2, _ = S.build_schedule(d2, k, g)
            assert _sched_key(e1, t) == _sched_key(e2, t), ("schedule changed", p, k, g)
            if g is not None:
                a1, a2 = S.gate_arrays(d, g), S.gate_arrays(d2, g)
                for x1, x2 in zip(a1, a2):
                    assert np.array_equal(x1[:t + 1], x2[:t + 1], equal_nan=True), ("gate array changed", p, g)
        # sanity: perturbation did change something after t (test is not vacuous)
        e1, _ = S.build_schedule(d, 2, ("FXVOL", 0.8, 3))
        e2, _ = S.build_schedule(d2, 2, ("FXVOL", 0.8, 3))
        if p != "2019-11-29":
            assert _sched_key(e1, 10 ** 9) != _sched_key(e2, 10 ** 9), ("perturbation vacuous", p)
    # q_t excludes t: changing v at t only leaves q_t unchanged
    v = S.fx_vol(d).copy()
    t = int(np.searchsorted(d.dates.values, np.datetime64("2008-10-15"), "right") - 1)
    q1 = S.rolling_quantile(d.dates, v, 0.8, 3)
    v[t] = 1e6
    q2 = S.rolling_quantile(d.dates, v, 0.8, 3)
    assert q1[t] == q2[t] and q2[t + 1] >= q1[t + 1]
    # prereg 10.4(iii) partial: 2008-09/2008-10 rebalance universe, ranking, weights (no PnL on real data)
    for k in (2, 3):
        ev, _ = S.build_schedule(d, k, None)
        for e in ev:
            if e["kind"] == "rebal" and e["info"]["month"] in ("2008-09", "2008-10"):
                LOG.info("HANDCHECK k=%d T=%s month=%s univ=%s d(m-1)=%s longs=%s shorts=%s w=%s", k,
                         d.dates[e["row"]].date(), e["info"]["month"], e["info"]["univ"], e["info"]["d"],
                         e["info"]["longs"], e["info"]["shorts"],
                         {c: w for c, w in e["targets"].items() if w})


def test_e_universe_real_vs_report(data_dir):
    d = L.load(data_dir)
    got = {str(mi.m): mi.univ for mi in d.months() if mi.m >= pd.Period("1994-01", "M")}
    n = 0
    with open(os.path.join(data_dir, "universe_by_month.csv"), newline="") as fh:
        for row in csv.DictReader(fh):
            if row["month"] > "2019-12":
                continue
            exp = [c for c in row["ccys"].split(",") if c]
            assert got[row["month"]] == exp, (row["month"], got[row["month"]], exp)
            n += 1
    assert n == 312, n
    LOG.info("universe matches universe_by_month.csv for %d months 1994-01..2019-12", n)


# ------------------------------------------------------------------ (c) hand month
def test_c_hand_month():
    ccys = ["EUR", "GBP", "JPY", "CHF"]
    dates = bdays("2000-01-03", "2000-02-29")
    n = len(dates)
    P = np.empty((n, 4))
    P[:, 0] = 1.0
    P[:, 1] = 1.6
    P[:, 2] = 1 / 100.0
    P[:, 3] = 1 / 1.6
    j15 = dates.get_loc(pd.Timestamp("2000-02-15"))
    P[j15:, 0] = 1.02
    P[j15:, 2] = 1 / 98.0
    rates = const_rates(("1999-12", "2000-02"), ccys, 5.0, {"EUR": 3.0, "GBP": 6.0, "JPY": 0.5, "CHF": 2.0})
    d = make_data(dates, ccys, P, rates)
    ev, end_row = S.build_schedule(d, 2, None)
    assert len(ev) == 1 and d.dates[ev[0]["row"]] == pd.Timestamp("2000-01-31")
    assert ev[0]["info"]["longs"] == "GBP,EUR" and ev[0]["info"]["shorts"] == "CHF,JPY"
    res = S.run_sim(d, ev, end_row)
    # ---- by hand
    # ERRATA2 J1: GBP 3pip/1.6=1.875bp -> 3bp ; USDJPY 3*0.01/100 = 3bp ; USDCHF 3pip/1.6 -> 3bp ; EUR 0.8 pip
    cost = 0.25 * (0.5 * 0.8 * 1e-4 / 1.0 + 0.5 * 3e-4 + 0.5 * 3e-4 + 0.5 * 3e-4)
    price = 0.25 * (1.02 - 1.0) + (-25.0) * (1 / 98.0 - 1 / 100.0)
    # leg carry %/yr: EUR long (3-5)-1=-3 ; GBP long (6-5)-1=0 ; CHF short (5-2)-1=2 ; JPY short (5-0.5)-1=3.5
    # calendar days Jan31->Feb15 = 15 at old notional, Feb15->Feb29 = 14 at new notional
    carry = (-3.0 * (0.25 * 15 + 0.255 * 14) + 0.0 + 2.0 * 0.25 * 29 + 3.5 * (0.25 * 15 + 25.0 / 98.0 * 14)) / 360.0 / 100.0
    expect = 1.0 - cost + price + carry
    got = res["equity"][end_row]
    LOG.info("hand month: expect %.12f got %.12f", expect, got)
    assert abs(got - expect) < 1e-12, (got, expect)
    assert abs(np.prod(1 + res["ret"][~np.isnan(res["ret"])]) - got) < 1e-12
    assert abs(res["gross"][ev[0]["row"]] * res["equity"][ev[0]["row"]] - 1.0) < 1e-12  # gross 1 of pre-trade equity
    # ERRATA2 J1 hand answers (one-way = half round trip):
    #  USDNOK 8.0 : 3 pip = 0.0003/8 = 0.375 bp < 3 bp -> RT 3 bp, one-way 1.5 bp
    #  USDJPY 80  : 3 pip = 0.03/80 = 3.75 bp > 3 bp -> RT 3.75 bp, one-way 1.875 bp
    #  USDJPY 110 : 0.03/110 = 2.727 bp -> RT 3 bp, one-way 1.5 bp ; EURUSD 1.25: 0.8e-4/1.25 = 0.64 bp RT, one-way 0.32 bp
    dd = make_data(bdays("2000-01-03", "2000-01-04"), ["NOK", "JPY", "EUR"],
                   np.array([[1 / 8.0, 1 / 80.0, 1.25], [1 / 8.0, 1 / 110.0, 1.25]]), rates.iloc[:1])
    assert abs(S.oneway_cost_frac(dd, 0, 0) - 1.5e-4) < 1e-15
    assert abs(S.oneway_cost_frac(dd, 1, 0) - 1.875e-4) < 1e-15
    assert abs(S.oneway_cost_frac(dd, 1, 1) - 1.5e-4) < 1e-15
    assert abs(S.oneway_cost_frac(dd, 2, 0) - 0.32e-4) < 1e-15


# ------------------------------------------------------------------ (d) gate
def _gate_data(spikes_fx=(), spike_vix=None):
    ccys = ["EUR", "GBP", "JPY", "CHF"]
    dates = bdays("1990-01-01", "1994-12-30")
    n = len(dates)
    a = 0.004 * (1 - 0.5 * np.arange(n) / n)          # decreasing calm vol -> v_t below its own history
    sgn = np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    lr = np.tile((a * sgn)[:, None], (1, 4))
    for s in spikes_fx:
        lr[dates.get_loc(pd.Timestamp(s)), :] = 0.05
    P = np.exp(np.cumsum(lr, axis=0)) * np.array([1.0, 1.6, 0.01, 0.6])
    vix = 30 - 10 * np.arange(n) / n
    if spike_vix:
        vix[dates.get_loc(pd.Timestamp(spike_vix))] = 80.0
    rates = const_rates(("1989-12", "1994-12"), ccys, 5.0, {"EUR": 3.0, "GBP": 6.0, "JPY": 0.5, "CHF": 2.0})
    return make_data(dates, ccys, P, rates, vix=vix)


def _held(res, row):
    return res["gross"][row] > 0


def test_d_gate():
    d = _gate_data(spikes_fx=("1994-03-01", "1994-08-31"))
    g = ("FXVOL", 0.8, 3)
    v, q, trig, act = S.gate_arrays(d, g)
    X = d.dates.get_loc(pd.Timestamp("1994-03-01"))
    assert trig[X] and not trig[X - 1]
    ev, end_row = S.build_schedule(d, 2, g)
    res = S.run_sim(d, ev, end_row)
    rows = {e["row"]: e for e in ev}
    assert rows[X]["kind"] == "gate_close"
    R0 = d.dates.get_loc(pd.Timestamp("1994-02-28"))
    R1 = d.dates.get_loc(pd.Timestamp("1994-03-31"))
    assert _held(res, X - 1) and not _held(res, X)            # flat exactly on X
    assert all(not _held(res, r) for r in range(X, R1)) and _held(res, R1)   # reopened exactly at R1
    assert all(res["state"][r] == "gate" for r in range(X + 1, R1 + 1))
    assert rows[R0]["kind"] == "rebal" and not rows[R0]["gate"]
    tr = res["trades"]
    for _, t in tr.iterrows():
        j = d.ccys.index(t["ccy"])
        ow = S.oneway_cost_frac(d, j, int(t["row"]))
        mult = 2.0 if t["gate"] else 1.0
        assert abs(t["cost_frac"] - t["traded_frac"] * ow * mult) < 1e-15
    assert tr[tr["row"] == X]["gate"].all() and len(tr[tr["row"] == X]) == 4
    # spike on a rebalance day: flat at that rebalance (gate flag, x2 cost), reopen next rebalance
    RA = d.dates.get_loc(pd.Timestamp("1994-08-31"))
    RS = d.dates.get_loc(pd.Timestamp("1994-09-30"))
    assert rows[RA]["kind"] == "rebal" and rows[RA]["gate"] and not _held(res, RA) and _held(res, RS)
    assert tr[tr["row"] == RA]["gate"].all()
    # gate OFF while history < N years (data from 1990: N=10 never active)
    assert not S.gate_arrays(d, ("FXVOL", 0.8, 10))[3].any()
    assert not act[:d.dates.get_loc(pd.Timestamp("1993-01-01"))].any()
    # VIX gate uses previous-day VIX (close 16:15 ET > FRED noon fix): spike day Y -> flat at Y+1
    d2 = _gate_data(spike_vix="1994-06-01")
    ev2, end2 = S.build_schedule(d2, 2, ("VIX", 0.9, 3))
    Y = d2.dates.get_loc(pd.Timestamp("1994-06-01"))
    gc = [e["row"] for e in ev2 if e["kind"] == "gate_close"]
    assert gc == [Y + 1], gc
    res2 = S.run_sim(d2, ev2, end2)
    assert _held(res2, Y) and not _held(res2, Y + 1)
    assert _held(res2, d2.dates.get_loc(pd.Timestamp("1994-06-30")))
    # ERRATA2 J2: FX_VOL = mean vol of every ccy with a valid price on row t, rate availability irrelevant
    dates = bdays("2000-01-03", "2000-03-31")
    n = len(dates)
    lr = np.zeros((n, 3))
    lr[:, 0] = np.where(np.arange(n) % 2 == 0, 0.01, -0.01)
    lr[:, 1] = np.where(np.arange(n) % 2 == 0, 0.02, -0.02)
    lr[:, 2] = np.where(np.arange(n) % 2 == 0, 0.04, -0.04)
    P = np.exp(np.cumsum(lr, axis=0))
    t = n - 1
    P[t, 2] = np.nan                                        # SEK price missing on row t -> excluded on t
    rates3 = const_rates(("1999-12", "2000-03"), ["NOK", "SEK"], 5.0, {"NOK": 5.0, "SEK": 5.0})
    rates3["CAD"] = np.nan                                   # CAD has NO rate at all -> still in FX_VOL
    d3 = make_data(dates, ["CAD", "NOK", "SEK"], P, rates3)
    v = S.fx_vol(d3)
    sd = lambda a: np.std(np.tile([a, -a], 11)[:21], ddof=1) * np.sqrt(252.0)  # noqa: E731
    assert abs(v[t - 1] - (sd(0.01) + sd(0.02) + sd(0.04)) / 3) < 1e-9, v[t - 1]
    assert abs(v[t] - (sd(0.01) + sd(0.02)) / 2) < 1e-9, v[t]


# ------------------------------------------------------------------ (e) universe (synthetic)
def test_e_universe_synth():
    ccys = ["EUR", "GBP", "JPY", "CHF", "CAD"]
    dates = bdays("2001-01-01", "2001-07-31")
    n = len(dates)
    P = np.tile(np.array([1.0, 1.6, 0.01, 0.6, 0.7]), (n, 1))
    rates = const_rates(("2000-12", "2001-07"), ccys, 5.0, {"EUR": 3.0, "GBP": 6.0, "JPY": 0.5, "CHF": 2.0, "CAD": 4.0})
    rates.loc[pd.Period("2001-01", "M"), "JPY"] = np.nan                    # Feb: JPY out (rate m-1 missing)
    rates.loc[pd.Period("2001-02", "M"), "USD"] = np.nan                    # Mar: empty (USD rate missing)
    rates.loc[pd.Period("2001-04", "M"), ["JPY", "CAD"]] = np.nan          # May: n=3 < 4
    P[(dates >= "2001-04-09") & (dates <= "2001-04-12"), 3] = np.nan       # Apr: CHF 4 missing days -> out
    P[(dates >= "2001-06-11") & (dates <= "2001-06-13"), 3] = np.nan       # Jun: CHF 3 missing days -> in
    d = make_data(dates, ccys, P, rates)
    U = {str(mi.m): mi.univ for mi in d.months()}
    assert U["2001-01"] == ccys
    assert U["2001-02"] == ["EUR", "GBP", "CHF", "CAD"]
    assert U["2001-03"] == []
    assert U["2001-04"] == ["EUR", "GBP", "JPY", "CAD"]
    assert U["2001-05"] == ["EUR", "GBP", "CHF"]
    assert U["2001-06"] == ccys
    for k in (2, 3):
        ev, end_row = S.build_schedule(d, k, None)
        res = S.run_sim(d, ev, end_row)
        by_m = {e["info"]["month"]: e for e in ev if e["kind"] == "rebal"}
        for m, e in by_m.items():
            nz = sum(1 for w in e["targets"].values() if w != 0)
            should = len(U[m]) >= 2 * k
            assert nz == (2 * k if should else 0), (k, m, nz)
            if should:
                assert abs(sum(abs(w) for w in e["targets"].values()) - 1.0) < 1e-12
                assert set(c for c, w in e["targets"].items() if w) <= set(U[m])
        # month without trade -> flat during next month
        T3 = by_m["2001-03"]["row"]
        assert res["gross"][T3 + 1] == 0.0
    # price missing on the rebalance day: that ccy trades at its next valid price (prereg sec 3)
    P2 = np.tile(np.array([1.0, 1.6, 0.01, 0.6, 0.7]), (n, 1))
    T1 = dates.get_loc(pd.Timestamp("2001-01-31"))
    P2[T1, 1] = np.nan
    rates2 = const_rates(("2000-12", "2001-07"), ccys, 5.0, {"EUR": 3.0, "GBP": 6.0, "JPY": 0.5, "CHF": 2.0, "CAD": 4.0})
    d2 = make_data(dates, ccys, P2, rates2)
    ev2, e2 = S.build_schedule(d2, 2, None)
    r2 = S.run_sim(d2, ev2, e2)
    gb = r2["trades"][r2["trades"]["ccy"] == "GBP"]
    assert gb.iloc[0]["row"] == T1 + 1


# ------------------------------------------------------------------ (f) cutoff
def test_f_cutoff(data_dir):
    for bad in ("2020-01-01", "2020-06-30", "2026-10-31"):
        for tok in (None, "yes", "I_HAVE_A1_PASS"):
            try:
                L.check_cutoff(bad, tok)
            except PermissionError:
                pass
            else:
                raise AssertionError("cutoff %s accepted" % bad)
    tmp = tempfile.mkdtemp(prefix="g1f_")
    try:
        rows = {c: [("2000-01-03", "1.0"), ("2000-01-04", "1.0")] for c in L.CCYS}
        _fake_dir(tmp, rows, extra_after_cutoff=True)
        try:
            L.load(tmp, cutoff="2020-12-31")
        except PermissionError:
            pass
        else:
            raise AssertionError("load accepted cutoff > 2019-12-31")
        d = L.load(tmp)
        assert d.dates.max() <= pd.Timestamp("2019-12-31") and np.nanmax(d.raw) < 999
        assert d.rates.index.max() <= pd.Period("2019-12", "M") and np.nanmax(d.vix) < 50
    finally:
        shutil.rmtree(tmp)
    if data_dir and os.path.isdir(data_dir):
        d = L.load(data_dir)
        assert d.dates.max() <= pd.Timestamp("2019-12-31")
        assert d.rates.index.max() <= pd.Period("2019-12", "M")
    for mod in (S, E):
        old = sys.argv
        try:
            sys.argv = ["x"]
            mod.main()
        except SystemExit as ex:
            assert ex.code == 2
        else:
            raise AssertionError("real run not locked")
        finally:
            sys.argv = old
    # constructor refuses rows after its cutoff
    try:
        L.G1Data(bdays("2019-12-30", "2020-01-02"), ["EUR"], {"EUR": L.USD_PER}, np.ones((4, 1)),
                 pd.DataFrame(), np.ones(4), "2019-12-31")
    except AssertionError:
        pass
    else:
        raise AssertionError("G1Data accepted row after cutoff")


# ------------------------------------------------------------------ (g) synthetic end-to-end
def synth_market(planted, seed):
    """Synthetic fixture. planted=True: persistent rate spread (+-8 %/yr vs USD), no UIP depreciation, 5 vol-led
    carry crashes (vol spike on day X, high-carry ccys fall / low-carry rise from X+3) -> carry premium exists and the
    vol gate helps. planted=False: all rates = USD +- tiny noise, pure random-walk prices -> no premium."""
    rng = np.random.default_rng(seed)
    ccys = list(L.CCYS)
    dates = bdays("1983-01-03", "2019-12-31")
    n, c = len(dates), len(ccys)
    sig = 0.05 / np.sqrt(252)
    lr = rng.normal(0, sig, size=(n, c))
    idx = pd.period_range("1982-12", "2019-12", freq="M")
    ar = np.zeros(n)
    eps = rng.standard_normal(n)
    for t in range(1, n):
        ar[t] = 0.98 * ar[t - 1] + eps[t]
    vix = 15 + 0.5 * ar
    if planted:
        diffs = 2.0 * np.array([-4, -3, -2, -1, 0, 1, 2, 3, 4], dtype=float)
        rates = pd.DataFrame({"USD": 5.0}, index=idx)
        for j, cc in enumerate(ccys):
            rates[cc] = 5.0 + diffs[j]
        hi = np.argsort(-diffs)[:3]
        lo = np.argsort(diffs)[:3]
        for X in ("1997-10-01", "2001-09-04", "2008-09-02", "2015-08-03", "2018-02-01"):
            x = dates.get_loc(pd.Timestamp(X))
            lr[x, :] = 0.04 * np.where(rng.random(c) < 0.5, 1, -1)
            lr[x + 1:x + 40, :] *= 5
            lr[x + 3:x + 18, hi] -= 0.007
            lr[x + 3:x + 18, lo] += 0.007
            vix[x - 1:x + 40] += 40
    else:
        rates = pd.DataFrame({"USD": 3.0 + rng.normal(0, 0.05, len(idx))}, index=idx)
        for cc in ccys:
            rates[cc] = 3.0 + rng.normal(0, 0.05, len(idx))
    base = np.array([1.1, 0.009, 1.6, 0.7, 0.75, 0.7, 0.6, 0.13, 0.12])
    P = np.exp(np.cumsum(lr, axis=0)) * base
    return make_data(dates, ccys, P, rates, vix=vix)


def test_g_end_to_end():
    out1 = E.evaluate(synth_market(True, 7), n_random=500)
    LOG.info("planted: selected %s D=%s p=%s verdict=%s", out1["selected"], out1["D"], out1["control_random"]["p"],
             out1["verdict"])
    assert out1["verdict"] == "DAT", out1["D"]
    out2 = E.evaluate(synth_market(False, 8), n_random=500)
    LOG.info("noise: selected %s D=%s p=%s verdict=%s", out2["selected"], out2["D"], out2["control_random"]["p"],
             out2["verdict"])
    assert out2["verdict"] == "KHONG DAT", out2["D"]
    md = E.report_md({k: v for k, v in out1.items() if k != "_res"})
    assert "[in-sample]" in md and "Ket luan: DAT" in md


# ------------------------------------------------------------------ (h) determinism
def test_h_determinism():
    def run():
        o = E.evaluate(synth_market(True, 11), n_random=20)
        o.pop("_res")
        return json.dumps(o, sort_keys=True, default=str)
    assert run() == run()
    d1, d2 = synth_market(True, 3), synth_market(True, 3)
    r1 = S.simulate(d1, 3, ("FXVOL", 0.9, 3))
    r2 = S.simulate(d2, 3, ("FXVOL", 0.9, 3))
    assert np.array_equal(r1["ret"], r2["ret"], equal_nan=True)
    assert r1["trades"].equals(r2["trades"])


# ------------------------------------------------------------------ (i) ERRATA3 K6 / NHO-7 guards
def test_i_a1_guards():
    # (1) q_t over [t-N, t) excludes t, at a t where v_t is NOT the window max and including it would change q
    rng = np.random.default_rng(5)
    dates = bdays("1990-01-01", "1994-12-30")
    v = rng.normal(10, 1, len(dates))
    t = dates.get_loc(pd.Timestamp("1994-06-01"))
    lo = int(np.searchsorted(dates.values, (dates[t] - pd.DateOffset(years=3)).to_datetime64(), "left"))
    w = v[lo:t]
    v[t] = (np.quantile(w, 0.8) + w.max()) / 2           # above q, below window max
    q = S.rolling_quantile(dates, v, 0.8, 3)
    assert v[t] < w.max()
    assert q[t] == np.quantile(w, 0.8)
    assert q[t] != np.quantile(v[lo:t + 1], 0.8)
    # (2) selection uses TRAIN Sharpe only; ties -> smaller k, then gate OFF
    mk = lambda name, k, g, tr, wf: dict(name=name, k=k, gate=g, train=dict(sharpe=tr), wfo=dict(sharpe=wf))  # noqa: E731
    rows = [mk("A", 3, ("FXVOL", 0.8, 3), 0.9, -1.0), mk("B", 2, None, 0.1, 5.0), mk("C", 2, ("VIX", 0.9, 3), 0.5, 3.0)]
    assert E.select(rows)["name"] == "A"
    rows = [mk("X", 3, None, 0.7, 9.0), mk("Y", 2, ("FXVOL", 0.9, 3), 0.7, 0.0), mk("Z", 2, None, 0.7, -9.0)]
    assert E.select(rows)["name"] == "Z"
    # (3) random runs use the selected k + gate; (5) x2 scenario passes cost_mult 2 with selected k + gate
    calls = []
    orig = S.simulate

    def spy(data, k, gate, **kw):
        calls.append((k, gate, kw.get("mode", "carry"), kw.get("cost_mult", 1.0), kw.get("carry_rates", "signal")))
        return orig(data, k, gate, **kw)
    S.simulate = spy
    try:
        out = E.evaluate(synth_market(True, 7), n_random=5)
    finally:
        S.simulate = orig
    sel = next(c for c in S.configs() if c["name"] == out["selected"])
    rnd = [c for c in calls if c[2] == "random"]
    assert len(rnd) == 5 and all(c[0] == sel["k"] and c[1] == sel["gate"] for c in rnd), rnd
    assert sel["gate"] is not None
    x2 = [c for c in calls if c[3] != 1.0]
    assert x2 == [(sel["k"], sel["gate"], "carry", 2.0, "signal")], x2
    assert out["cost_x2"]["cagr"] < out["configs"][[c["name"] for c in S.configs()].index(sel["name"])]["wfo"]["cagr"]
    assert out["k5_carry_holding_month"]["label"] == "mo ta, ngoai tieu chi"
    # random run really goes through the gate: some gate closes appear in a random schedule
    dsm = synth_market(True, 7)
    ev, _ = S.build_schedule(dsm, sel["k"], sel["gate"], mode="random", rng=np.random.default_rng(1))
    assert any(e["kind"] == "gate_close" or e["gate"] for e in ev)
    # x2 engine: costs exactly doubled on the same trades (hand month data)
    ccys = ["EUR", "GBP", "JPY", "CHF"]
    hd = bdays("2000-01-03", "2000-02-29")
    P = np.tile(np.array([1.0, 1.6, 0.01, 0.625]), (len(hd), 1))
    rates = const_rates(("1999-12", "2000-02"), ccys, 5.0, {"EUR": 3.0, "GBP": 6.0, "JPY": 0.5, "CHF": 2.0})
    dh = make_data(hd, ccys, P, rates)
    r1, r2 = S.simulate(dh, 2, None), S.simulate(dh, 2, None, cost_mult=2.0)
    assert np.allclose(r2["trades"]["cost_frac"], 2 * r1["trades"]["cost_frac"], rtol=0, atol=1e-18)
    # (4) D6 drops the BEST months: hand series
    mon = pd.Series([0.10, -0.02, 0.03, 0.05, -0.01] + [0.0] * 15)
    tot, nd = E.drop_best_months(mon)
    assert nd == 1 and abs(tot - (0.98 * 1.03 * 1.05 * 0.99 - 1)) < 1e-12
    mon = pd.Series([0.2, 0.1] + [-0.01] * 19)            # 21 months -> ceil(1.05) = 2 dropped
    tot, nd = E.drop_best_months(mon)
    assert nd == 2 and abs(tot - (0.99 ** 19 - 1)) < 1e-12
    # (6) thresholds D1-D7 and K1 p-value
    base = dict(sharpe=0.31, p=0.05, n_random=500, maxdd=0.25, n_pos=8, n_cfg=12, d5=True, drop5_total=0.01, x2_cagr=0.01)
    assert all(E.criteria(**base).values()) and E.verdict_of(E.criteria(**base)) == "DAT"
    for kk, vv, dk in (("sharpe", 0.3, "D1"), ("p", 0.0501, "D2"), ("n_random", 499, "D2"), ("maxdd", 0.2501, "D3"),
                       ("n_pos", 7, "D4"), ("d5", False, "D5"), ("drop5_total", 0.0, "D6"), ("x2_cagr", 0.0, "D7")):
        b = dict(base, **{kk: vv})
        D = E.criteria(**b)
        assert not D[dk] and sum(D.values()) == 6, (kk, D)
    assert E.verdict_of(E.criteria(**dict(base, maxdd=0.3))) == "CO TIN HIEU, CHUA DU"
    assert E.verdict_of(E.criteria(**dict(base, p=0.06))) == "KHONG DAT"
    p, n_ge = E.p_value([0.1, 0.5, np.nan, 0.2], 0.2)
    assert n_ge == 3 and abs(p - 4 / 5) < 1e-15
    p, n_ge = E.p_value(np.zeros(500), 1.0)
    assert n_ge == 0 and abs(p - 1 / 501) < 1e-15
    # NHO-7: simulate / evaluate on loaded (real-flagged) data refuse without the token
    tmp = tempfile.mkdtemp(prefix="g1i_")
    try:
        _fake_dir(tmp, {c: [("2000-01-03", "1.0"), ("2000-01-04", "1.0")] for c in L.CCYS})
        dl = L.load(tmp)
        assert dl.is_real
        for fn in (lambda: S.simulate(dl, 2, None), lambda: E.evaluate(dl, n_random=1)):
            try:
                fn()
            except PermissionError:
                pass
            else:
                raise AssertionError("real lock bypassed")
        S.build_schedule(dl, 2, None)                        # signal layer (positions only) stays allowed
    finally:
        shutil.rmtree(tmp)


TESTS = dict(i=lambda a: test_i_a1_guards(), a=lambda a: test_a_quote_direction(), b=lambda a: test_b_causality_real(a.data),
             c=lambda a: test_c_hand_month(), d=lambda a: test_d_gate(),
             e=lambda a: (test_e_universe_synth(), test_e_universe_real_vs_report(a.data)),
             f=lambda a: test_f_cutoff(a.data), g=lambda a: test_g_end_to_end(), h=lambda a: test_h_determinism())
REAL = {"b"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=L.DEFAULT_DATA)
    ap.add_argument("--only", default="abcdefghi")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("g1.load").setLevel(logging.WARNING)
    have_real = os.path.isdir(a.data)
    fails = 0
    for key in a.only.replace(",", ""):
        if (key in REAL or key == "e") and not have_real:
            if key in REAL:
                LOG.warning("TEST %s SKIP (no real data dir)", key)
                continue
        try:
            if key == "e" and not have_real:
                test_e_universe_synth()
            else:
                TESTS[key](a)
            LOG.info("TEST %s PASS", key)
        except Exception:
            fails += 1
            LOG.exception("TEST %s FAIL", key)
    LOG.info("DONE fails=%d", fails)
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
