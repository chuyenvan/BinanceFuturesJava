"""Tests for FX G2 (plain python3). Real data used ONLY for loading / signal-layer causality (positions, no returns).
Usage: python3 test_g2.py [--data DIR] [--only abc...]"""
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
import load_g2 as L2  # noqa: E402
import load_g1 as L1  # noqa: E402
import sim_g1 as S1  # noqa: E402
import sim_g2 as S2  # noqa: E402
import eval_g2 as E2  # noqa: E402
import eval_g1 as E1  # noqa: E402

LOG = logging.getLogger("g2.test")


def bdays(a, b):
    return pd.bdate_range(a, b)


def make_data(dates, ccys, P, rates, reer=None, cutoff=None):
    quote = {c: L1.FX[c][1] for c in ccys}
    raw = np.column_stack([P[:, j] if quote[c] == L1.USD_PER else 1.0 / P[:, j] for j, c in enumerate(ccys)])
    d = L1.G1Data(dates, ccys, quote, raw, rates, np.full(len(dates), 15.0), cutoff or dates[-1])
    d.reer = reer
    return d


def const_rates(months, ccys, usd, rmap):
    idx = pd.period_range(months[0], months[1], freq="M")
    df = pd.DataFrame({"USD": float(usd)}, index=idx)
    for c in ccys:
        df[c] = float(rmap[c])
    return df


def _write(path, header, rows):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _fake_dir(tmp, daily_raw, months, after_cutoff=False):
    """daily_raw: {ccy: [(date, value)]}; monthly rates 5 % for all; REER narrow 100 for all areas."""
    for c in L1.CCYS:
        rows = list(daily_raw[c]) + ([("2020-01-02", "999")] if after_cutoff else [])
        _write(os.path.join(tmp, "FRED_%s.csv" % L1.FX[c][0]), ["date", "v"], rows)
    for c, code in L1.RATE.items():
        rows = [(str(m) + "-01", "5.0") for m in months] + ([("2020-01-01", "9")] if after_cutoff else [])
        _write(os.path.join(tmp, "FRED_IR3TIB01%sM156N.csv" % code), ["date", "v"], rows)
    _write(os.path.join(tmp, "FRED_VIXCLS.csv"), ["date", "v"], [(daily_raw["CAD"][0][0], "15")])
    rr = [(a, "N", str(m), "100", "", "A") for a in ["US"] + list(L2.AREA.values()) for m in months]
    rr += [(a, "B", str(m), "50", "", "A") for a in L2.AREA.values() for m in months]
    if after_cutoff:
        rr += [(a, "N", "2020-01", "999", "", "A") for a in L2.AREA.values()]
    _write(os.path.join(tmp, "bis_reer_monthly.csv"), ["area", "basket", "month", "reer", "unit", "status"], rr)


# ------------------------------------------------------------------ (a) quote direction -> signal sign
def test_a_quote_direction():
    tmp = tempfile.mkdtemp(prefix="g2a_")
    try:
        dates = bdays("1999-01-04", "2000-06-30")
        g = np.exp(0.0005 * np.arange(len(dates)))       # every foreign ccy appreciates vs USD every day
        raw = {}
        for c in L1.CCYS:
            vals = g if L1.FX[c][1] == L1.USD_PER else 100.0 / g
            raw[c] = [(d.date().isoformat(), "%.10f" % v) for d, v in zip(dates, vals)]
        months = pd.period_range("1998-12", "2000-06", freq="M")
        _fake_dir(tmp, raw, months)
        d = L2.load(tmp)
        rec = [r for r in S2.signal_table(d, start=pd.Period("2000-05", "M")) if str(r["m"]) == "2000-05"][0]
        assert sorted(rec["univ"]) == sorted(L1.CCYS), rec["univ"]
        for c in L1.CCYS:
            assert rec["s"][c] == {"L1": 1.0, "L3": 1.0, "L12": 1.0, "C": 1.0}, (c, rec["s"][c])
        assert d.reer.loc[pd.Period("2000-01", "M"), "EUR"] == 100.0       # narrow basket, XM -> EUR
    finally:
        shutil.rmtree(tmp)


# ------------------------------------------------------------------ (b) causality on REAL data (signal layer only)
def _perturb(d, t, seed):
    rng = np.random.default_rng(seed)
    raw = d.raw.copy()
    n = len(d.dates)
    raw[t + 1:] *= np.exp(rng.normal(0, 0.05, size=(n - t - 1, raw.shape[1])))
    rates = d.rates.copy()
    sel = rates.index >= d.month[t]
    rates.loc[sel] = rng.uniform(-5, 20, size=(int(sel.sum()), rates.shape[1]))
    d2 = L1.G1Data(d.dates, d.ccys, d.quote, raw, rates, d.vix, d.cutoff)
    reer = d.reer.copy()
    selr = reer.index >= d.month[t]
    reer.loc[selr] = rng.uniform(50, 200, size=(int(selr.sum()), reer.shape[1]))
    d2.reer = reer
    return d2


def _rec_key(r):
    return (str(r["m"]), r["T"], r["x"], tuple(r["univ"]), json.dumps(r["s"], sort_keys=True),
            json.dumps(r["vol"], sort_keys=True), json.dumps(r["reer"], sort_keys=True),
            json.dumps(r["reer_mean"], sort_keys=True), json.dumps(r["r"], sort_keys=True), r["r_usd"])


def test_b_causality_real(data_dir):
    d = L2.load(data_dir)
    assert d.dates.max() <= pd.Timestamp("2019-12-31") and d.reer is not None
    assert d.reer.index.max() <= pd.Period("2019-12", "M")
    recs = S2.signal_table(d)
    assert all(r["x"] == r["T"] + 1 for r in recs)
    for i, p in enumerate(["1979-03-15", "1992-09-16", "2005-12-30", "2008-10-15", "2014-12-31", "2019-11-28"]):
        t = int(np.searchsorted(d.dates.values, np.datetime64(p), "right") - 1)
        d2 = _perturb(d, t, 200 + i)
        r1 = [_rec_key(r) for r in S2.signal_table(d) if r["T"] <= t]
        r2 = [_rec_key(r) for r in S2.signal_table(d2) if r["T"] <= t]
        assert r1 == r2, ("signal layer changed", p)
        for cfg in S2.configs():
            a1 = S2.config_signs(d, cfg)
            a2 = S2.config_signs(d2, cfg)
            k = len(r1)
            for x1, x2 in zip(a1, a2):
                assert np.array_equal(x1[:k], x2[:k], equal_nan=True), ("config signs changed", p, cfg["name"])
        later1 = [_rec_key(r) for r in S2.signal_table(d) if r["T"] > t]
        later2 = [_rec_key(r) for r in S2.signal_table(d2) if r["T"] > t]
        if later1:
            assert later1 != later2, ("perturbation vacuous", p)
    # 2008-10 signal for MASTER/A1 hand check (positions only)
    for r in recs:
        if str(r["m"]) in ("2008-09", "2008-10"):
            LOG.info("HANDCHECK m=%s T=%s exec=%s univ=%s s=%s vol=%s reer=%s mean60=%s", r["m"], d.dates[r["T"]].date(),
                     d.dates[r["x"]].date(), r["univ"], {c: r["s"][c] for c in r["univ"]},
                     {c: round(r["vol"][c], 4) for c in r["univ"]}, r["reer"], {c: round(v, 2) for c, v in r["reer_mean"].items()})
    years = {}
    for r in recs:
        years.setdefault(r["m"].year, set()).add(len(r["univ"]))
    LOG.info("universe size by year (signal months): %s", {y: sorted(v) for y, v in years.items() if y in (1975, 1980, 1985, 1990, 1999, 2003, 2010)})


# ------------------------------------------------------------------ (c) hand month + inverse-vol sizing + next-day exec
def test_c_hand_month():
    ccys = ["EUR", "JPY"]
    dates = bdays("1999-11-01", "2000-02-29")
    n = len(dates)
    T = dates.get_loc(pd.Timestamp("2000-01-31"))
    alt = np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    lrE = 0.004 * alt
    lrJ = 0.008 * alt
    j14 = dates.get_loc(pd.Timestamp("2000-01-14"))
    lrE[j14], lrJ[j14] = 0.02, -0.03
    lrE[0] = lrJ[0] = 0.0
    lrE[T + 1:] = 0.0
    lrJ[T + 1:] = 0.0
    lrE[T + 1], lrJ[T + 1] = 0.005, -0.002                  # Feb 1 move happens BEFORE the position exists
    j15 = dates.get_loc(pd.Timestamp("2000-02-15"))
    lrE[j15], lrJ[j15] = 0.01, 0.01
    P = np.column_stack([1.0 * np.exp(np.cumsum(lrE)), 0.01 * np.exp(np.cumsum(lrJ))])
    rates = const_rates(("1999-10", "2000-02"), ccys, 5.0, {"EUR": 3.0, "JPY": 0.5})
    d = make_data(dates, ccys, P, rates)
    cfg = dict(name="L1-F0", sig="L1", X=None)
    res = S2.simulate(d, cfg)
    # ---- by hand
    vE = np.std(lrE[T - 62:T + 1], ddof=1) * np.sqrt(252)
    vJ = np.std(lrJ[T - 62:T + 1], ddof=1) * np.sqrt(252)
    wE, wJ = (1 / vE) / (1 / vE + 1 / vJ), -(1 / vJ) / (1 / vE + 1 / vJ)
    x = T + 1
    PE1, PJ1, PE2, PJ2 = P[x, 0], P[x, 1], P[-1, 0], P[-1, 1]
    cost = abs(wE) * 0.5 * 0.8e-4 / PE1 + abs(wJ) * 0.5 * max(3 * 0.01 / (1 / PJ1), 3e-4)
    uE, uJ = wE / PE1, wJ / PJ1
    price = uE * (PE2 - PE1) + uJ * (PJ2 - PJ1)
    # legs %/yr: EUR long (3-5)-1 = -3 ; JPY short (5-0.5)-1 = 3.5 ; Feb1->Feb15 14 days, Feb15->Feb29 14 days
    carry = (-3.0 * (abs(uE * PE1) * 14 + abs(uE * PE2) * 14) + 3.5 * (abs(uJ * PJ1) * 14 + abs(uJ * PJ2) * 14)) / 36000
    expect = 1.0 - cost + price + carry
    got = res["equity"][n - 1]
    LOG.info("hand month: expect %.12f got %.12f (wE %.6f wJ %.6f)", expect, got, wE, wJ)
    assert abs(got - expect) < 1e-12, (got, expect)
    tr = res["trades"]
    assert set(tr["row"]) == {x} and x == T + 1                # executed on the NEXT business day
    assert abs(tr.loc[tr.ccy == "EUR", "w"].iloc[0] - wE) < 1e-12 and abs(tr.loc[tr.ccy == "JPY", "w"].iloc[0] - wJ) < 1e-12
    # sizing hand answer: vols 0.1, 0.2, 0.4 ; signs +, -, + -> (10, -5, 2.5)/17.5
    w = S2.inv_vol_weights([1, -1, 1], [0.1, 0.2, 0.4])
    assert np.allclose(w, [4 / 7, -2 / 7, 1 / 7], atol=1e-15, rtol=0)
    assert np.allclose(S2.inv_vol_weights([0, 0], [0.1, 0.2]), [0, 0])
    assert np.allclose(S2.inv_vol_weights([1, 0, -1], [0.1, 0.3, 0.1]), [0.5, 0, -0.5])


# ------------------------------------------------------------------ (d) value filter, both sides
def test_d_value_filter():
    F = S2.value_filter
    assert F(1, 111.0, 100.0, 0.10) == (0, True)        # long, REER > 1.1 mean -> blocked
    assert F(1, 109.0, 100.0, 0.10) == (1, False)
    assert F(1, 80.0, 100.0, 0.10) == (1, False)        # long cheap ccy allowed
    assert F(-1, 89.0, 100.0, 0.10) == (0, True)        # short, REER < 0.9 mean -> blocked
    assert F(-1, 91.0, 100.0, 0.10) == (-1, False)
    assert F(-1, 130.0, 100.0, 0.10) == (-1, False)     # short expensive ccy allowed
    assert F(1, 119.0, 100.0, 0.20) == (1, False) and F(1, 121.0, 100.0, 0.20) == (0, True)
    assert F(-1, 79.0, 100.0, 0.20) == (0, True) and F(-1, 81.0, 100.0, 0.20) == (-1, False)
    assert F(1, 500.0, 100.0, None) == (1, False) and F(1, np.nan, 100.0, 0.1) == (1, False)
    # integration: mean over m-60..m-1 (includes m-1), REER of m-1 (not m)
    ccys = ["EUR", "JPY"]
    dates = bdays("1999-06-01", "2000-02-29")
    n = len(dates)
    lr = np.tile(np.where(np.arange(n) % 2 == 0, 0.003, -0.002)[:, None], (1, 2))
    lr[:, 1] *= -1                                         # EUR trends up (long), JPY trends down (short)
    P = np.exp(np.cumsum(lr, axis=0)) * np.array([1.0, 0.01])
    rates = const_rates(("1999-05", "2000-02"), ccys, 5.0, {"EUR": 5.0, "JPY": 5.0})
    idx = pd.period_range("1994-01", "2000-02", freq="M")
    reer = pd.DataFrame({"EUR": 100.0, "JPY": 100.0}, index=idx)
    reer.loc[pd.Period("1999-12", "M"), "EUR"] = 170.0    # m-1 for the 2000-01 signal
    reer.loc[pd.Period("1999-12", "M"), "JPY"] = 40.0
    reer.loc[pd.Period("2000-01", "M"), ["EUR", "JPY"]] = [1000.0, 1.0]   # month m itself must NOT be used
    d = make_data(dates, ccys, P, rates, reer=reer)
    rec = [r for r in S2.signal_table(d) if str(r["m"]) == "2000-01"][0]
    assert rec["reer"] == {"EUR": 170.0, "JPY": 40.0}
    assert abs(rec["reer_mean"]["EUR"] - (59 * 100 + 170) / 60) < 1e-12        # 101.1667 -> 170 > 1.2x -> block long
    assert abs(rec["reer_mean"]["JPY"] - (59 * 100 + 40) / 60) < 1e-12         # 99.0 -> 40 < 0.8x -> block short
    i = [str(r["m"]) for r in S2.signal_table(d)].index("2000-01")
    for X in (0.10, 0.20):
        S, V, U, nraw, nfilt = S2.config_signs(d, dict(name="t", sig="L1", X=X))
        assert U[i].all() and S[i, 0] == 0 and S[i, 1] == 0 and nraw[i] == 2 and nfilt[i] == 2
    S, V, U, nraw, nfilt = S2.config_signs(d, dict(name="t", sig="L1", X=None))
    assert S[i, 0] == 1 and S[i, 1] == -1 and nfilt[i] == 0


# ------------------------------------------------------------------ (e) controls: circular shift keeps structure
def test_e_controls():
    rng = np.random.default_rng(3)
    nm, nc = 168, 9
    S = rng.choice([-1.0, 0.0, 1.0], size=(nm, nc))
    U = np.ones((nm, nc), dtype=bool)
    r2 = np.random.default_rng(9)
    So, ks = E2.circular_shift(S, U, r2)
    for j in range(nc):
        assert 12 <= ks[j] <= nm - 12
        assert np.count_nonzero(So[:, j]) == np.count_nonzero(S[:, j])          # months with a position preserved
        assert sorted(So[:, j]) == sorted(S[:, j]) and np.array_equal(So[:, j], np.roll(S[:, j], ks[j]))
    assert not np.array_equal(So, S)
    U2 = U.copy()
    U2[:5, 0] = False
    So2, _ = E2.circular_shift(S, U2, np.random.default_rng(9))
    assert np.all(So2[:5, 0] == 0)
    iid = E2.iid_signs(U2, np.random.default_rng(1))
    assert np.all(iid[~U2] == 0) and set(np.unique(iid[U2])) <= {-1.0, 1.0}
    # p with +1 (ERRATA3 K1)
    assert E2.p_value is E1.p_value
    p, n_ge = E2.p_value(np.zeros(1000), 1.0)
    assert n_ge == 0 and abs(p - 1 / 1001) < 1e-15
    p, n_ge = E2.p_value([0.5, np.nan, 0.1], 0.4)
    assert n_ge == 2 and abs(p - 3 / 4) < 1e-15
    # D5 drops the BEST months (hand)
    tot, nd = E2.drop_best_months(pd.Series([0.10, -0.02, 0.03, 0.05, -0.01] + [0.0] * 15))
    assert nd == 1 and abs(tot - (0.98 * 1.03 * 1.05 * 0.99 - 1)) < 1e-12
    # criteria boundaries D1-D6
    base = dict(sharpe=0.31, p=0.05, n_shift=1000, maxdd=0.25, n_pos=8, n_cfg=12, drop5_total=0.01, x2_cagr=0.01)
    assert E2.verdict_of(E2.criteria(**base)) == "DAT"
    for kk, vv, dk in (("sharpe", 0.3, "D1"), ("p", 0.0501, "D2"), ("n_shift", 999, "D2"), ("maxdd", 0.2501, "D3"),
                       ("n_pos", 7, "D4"), ("drop5_total", 0.0, "D5"), ("x2_cagr", 0.0, "D6")):
        D = E2.criteria(**dict(base, **{kk: vv}))
        assert not D[dk] and sum(D.values()) == 5, (kk, D)
    assert E2.verdict_of(E2.criteria(**dict(base, maxdd=0.5))) == "CO TIN HIEU, CHUA DU"
    assert E2.verdict_of(E2.criteria(**dict(base, p=0.2))) == "KHONG DAT"


# ------------------------------------------------------------------ (f) cutoff + locks
def test_f_cutoff_lock(data_dir):
    for bad in ("2020-01-01", "2026-10-31"):
        try:
            L2.load(data_dir, cutoff=bad)
        except PermissionError:
            pass
        else:
            raise AssertionError("cutoff accepted")
    tmp = tempfile.mkdtemp(prefix="g2f_")
    try:
        dates = bdays("1999-01-04", "1999-03-31")
        raw = {c: [(x.date().isoformat(), "1.0") for x in dates] for c in L1.CCYS}
        _fake_dir(tmp, raw, pd.period_range("1998-12", "1999-03", freq="M"), after_cutoff=True)
        d = L2.load(tmp)
        assert d.dates.max() <= pd.Timestamp("2019-12-31") and np.nanmax(d.raw) < 999
        assert d.reer.index.max() <= pd.Period("2019-12", "M") and d.reer.max().max() == 100.0
        assert d.is_real
        for fn in (lambda: S2.simulate(d, S2.configs()[0]), lambda: E2.evaluate(d, n_shift=1, n_iid=1)):
            try:
                fn()
            except PermissionError:
                pass
            else:
                raise AssertionError("real lock bypassed")
        S2.signal_table(d)                                   # signal layer allowed
        r = L2.read_reer(os.path.join(tmp, "bis_reer_monthly.csv"), "2019-12-31")
        assert list(r.columns) == L1.CCYS and r.index.max() == pd.Period("1999-03", "M")
    finally:
        shutil.rmtree(tmp)
    for mod in (S2, E2):
        old = sys.argv
        try:
            sys.argv = ["x"]
            mod.main()
        except SystemExit as ex:
            assert ex.code == 2
        else:
            raise AssertionError("CLI not locked")
        finally:
            sys.argv = old


# ------------------------------------------------------------------ (g) synthetic end-to-end
def synth_market(planted, seed):
    """planted: each ccy has a persistent drift +-10 %/yr switching sign with prob 1/24 per month (TSMOM premium);
    else pure random walk. vol 6 %; all rates = USD (no carry; margin drag 1 %/yr). REER = monthly mean price x 100."""
    rng = np.random.default_rng(seed)
    ccys = list(L1.CCYS)
    dates = bdays("1972-01-03", "2019-12-31")
    n, c = len(dates), len(ccys)
    lr = rng.normal(0, 0.06 / np.sqrt(252), size=(n, c))
    if planted:
        months = dates.to_period("M")
        um = pd.period_range(months[0], months[-1], freq="M")
        sign = np.ones((len(um), c))
        cur = rng.choice([-1.0, 1.0], size=c)
        for i in range(len(um)):
            flip = rng.random(c) < 1 / 24
            cur = np.where(flip, -cur, cur)
            sign[i] = cur
        pos = um.get_indexer(months)
        lr += sign[pos] * 0.10 / 252
    P = np.exp(np.cumsum(lr, axis=0)) * np.array([1.1, 0.009, 1.6, 0.7, 0.75, 0.7, 0.6, 0.13, 0.12])
    rates = pd.DataFrame({"USD": 5.0}, index=pd.period_range("1971-12", "2019-12", freq="M"))
    for cc in ccys:
        rates[cc] = 5.0
    pm = pd.DataFrame(P, index=dates, columns=ccys)
    reer = pm.groupby(dates.to_period("M")).mean()
    reer = 100 * reer / reer.iloc[0]
    reer.index = pd.PeriodIndex(reer.index, freq="M")
    return make_data(dates, ccys, P, rates, reer=reer)


def test_g_end_to_end():
    o1 = E2.evaluate(synth_market(True, 7), n_shift=1000, n_iid=50)
    LOG.info("planted: sel %s D=%s p=%.4f verdict=%s", o1["selected"], o1["D"], o1["control_shift"]["p"], o1["verdict"])
    assert o1["verdict"] == "DAT", o1["D"]
    o2 = E2.evaluate(synth_market(False, 8), n_shift=1000, n_iid=50)
    LOG.info("noise: sel %s D=%s p=%.4f verdict=%s", o2["selected"], o2["D"], o2["control_shift"]["p"], o2["verdict"])
    assert o2["verdict"] == "KHONG DAT", o2["D"]
    md = E2.report_md({k: v for k, v in o1.items() if k != "_res"})
    assert "[in-sample]" in md and "Ket luan: DAT" in md


# ------------------------------------------------------------------ (h) selection by TRAIN only, x2, determinism
def test_h_select_x2_determinism():
    mk = lambda n, s, X, tr, wf: dict(name=n, sig=s, X=X, train=dict(sharpe=tr), wfo=dict(sharpe=wf))  # noqa: E731
    rows = [mk("A", "L3", 0.1, 0.9, -1.0), mk("B", "L12", None, 0.2, 5.0), mk("C", "C", None, 0.5, 3.0)]
    assert E2.select(rows)["name"] == "A"
    rows = [mk("X", "L1", 0.1, 0.7, 9.0), mk("Y", "L1", None, 0.7, 0.0), mk("Z", "L12", None, 0.7, -9.0),
            mk("W", "C", None, 0.7, 9.0)]
    assert E2.select(rows)["name"] == "Z"
    calls = []
    orig = S2.simulate

    def spy(data, cfg, **kw):
        calls.append((cfg["name"], kw.get("cost_mult", 1.0), kw.get("S_override") is not None, kw.get("start")))
        return orig(data, cfg, **kw)
    S2.simulate = spy
    try:
        o = E2.evaluate(synth_market(True, 5), n_shift=3, n_iid=2)
    finally:
        S2.simulate = orig
    x2 = [c for c in calls if c[1] != 1.0]
    assert x2 == [(o["selected"], 2.0, False, None)], x2
    sh = [c for c in calls if c[2]]
    assert len(sh) == 5 and all(c[0] == o["selected"] and c[3] == E2.WFO_SIG_START for c in sh)
    sel = next(r for r in o["configs"] if r["name"] == o["selected"])
    assert o["cost_x2"]["cagr"] < sel["wfo"]["cagr"]
    d = synth_market(True, 5)
    cfg = S2.configs()[0]
    r1, r2 = S2.simulate(d, cfg), S2.simulate(d, cfg, cost_mult=2.0)
    t1, t2 = r1["trades"], r2["trades"]
    assert len(t1) == len(t2) and (t1["row"].values == t2["row"].values).all()
    k1 = t1["cost_frac"] / t1["traded_frac"]
    k2 = t2["cost_frac"] / t2["traded_frac"]
    ok = t1["traded_frac"] > 0
    assert np.allclose(k2[ok], 2 * k1[ok], rtol=1e-12, atol=0)      # cost per unit traded exactly doubled

    def run():
        x = E2.evaluate(synth_market(True, 11), n_shift=5, n_iid=3)
        x.pop("_res")
        return json.dumps(x, sort_keys=True, default=str)
    assert run() == run()


TESTS = dict(a=lambda a: test_a_quote_direction(), b=lambda a: test_b_causality_real(a.data),
             c=lambda a: test_c_hand_month(), d=lambda a: test_d_value_filter(), e=lambda a: test_e_controls(),
             f=lambda a: test_f_cutoff_lock(a.data), g=lambda a: test_g_end_to_end(),
             h=lambda a: test_h_select_x2_determinism())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=L2.DEFAULT_DATA)
    ap.add_argument("--only", default="abcdefgh")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("g1.load").setLevel(logging.WARNING)
    logging.getLogger("g2.load").setLevel(logging.WARNING)
    have_real = os.path.isdir(a.data)
    fails = 0
    for key in a.only:
        if key == "b" and not have_real:
            LOG.warning("TEST b SKIP (no real data dir)")
            continue
        try:
            TESTS[key](a)
            LOG.info("TEST %s PASS", key)
        except Exception:
            fails += 1
            LOG.exception("TEST %s FAIL", key)
    LOG.info("DONE fails=%d", fails)
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
