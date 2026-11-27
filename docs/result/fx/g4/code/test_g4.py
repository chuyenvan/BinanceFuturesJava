#!/usr/bin/env python3
"""G4 tests. Usage: python3 test_g4.py [letters]. Real data only for loading / causality of events (no returns)."""
import copy
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

import eval_g4
import load_g4
import sig_g4
import sim_g4

LOG = logging.getLogger("g4.test")
OUT = os.path.expanduser("~/claude_master/w3/fx/g4/out")
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    LOG.info("%s %s %s", "PASS" if cond else "FAIL", name, detail)


def tm(s):
    return sig_g4.tmin(s)


def rates_const(ez=2.0, us=1.0):
    idx = pd.date_range("2004-01-01", "2019-12-01", freq="MS")
    return pd.DataFrame({"US": us, "EZ": ez, "GB": 1.0, "JP": 0.1, "AU": 3.0}, index=idx)


PAD = 40


def mini(pair, t, c, o=None, rates=None, pad=PAD):
    """Prepends `pad` flat 1-min bars so the trade is not inside the 30-min window after the series start (gap > 60)."""
    c = np.asarray(c, float)
    o = c.copy() if o is None else np.asarray(o, float)
    t = np.asarray(t, np.int64)
    if pad:
        t = np.concatenate([t[0] - pad + np.arange(pad), t])
        c = np.concatenate([np.full(pad, c[0]), c])
        o = np.concatenate([np.full(pad, o[0]), o])
    d = load_g4.build_pair(pair, t, o, np.maximum(o, c), np.minimum(o, c), c)
    d["roll_tab"] = load_g4.rollover_table(rates if rates is not None else rates_const(), pair)
    return d


# ---------------- hand trade ----------------
def test_a():
    t0 = tm("2015-06-02 10:00")
    sg = 0.001
    # trailing: entry close 1.1000 at bar 0
    c = [1.1000, 1.1005, 1.1012, 1.1008, 1.1006, 1.1006, 1.1006]
    d = mini("EURUSD", t0 + np.arange(len(c)), c)
    r = sim_g4.trades_batch(d, [PAD], 1, [sg], 240)
    rte, rtx = 0.8e-4 / 1.1, 0.8e-4 / 1.1006
    hand = 0.0006 / 1.1 - (rte / 2 + rtx / 2)
    check("a_trailing_exit", r["reason"][0] == "TRAIL" and r["exit"][0] == PAD + 4 and abs(r["net"][0] - hand) < 1e-15,
          "%s exit=%d net=%.6e hand=%.6e" % (r["reason"][0], r["exit"][0], r["net"][0], hand))
    # SL with slippage
    c = [1.1000, 1.0990, 1.0977, 1.0970]
    d = mini("EURUSD", t0 + np.arange(len(c)), c)
    r = sim_g4.trades_batch(d, [PAD], 1, [sg], 240)
    rtx = 0.8e-4 / 1.0977
    hand = (1.0977 / 1.1 - 1) - (rte / 2 + rtx / 2 + 0.5 * rtx)
    check("a_sl_exit_slip", r["reason"][0] == "SL" and r["exit"][0] == PAD + 2 and abs(r["net"][0] - hand) < 1e-15)
    # time-stop TS = 5 min, flat-ish, short side, GBPUSD (3 pip vs 3 bp)
    c = [1.5000, 1.5001, 1.4999, 1.5002, 1.5001, 1.5003, 1.5004, 1.5]
    d = mini("GBPUSD", t0 + np.arange(len(c)), c)
    r = sim_g4.trades_batch(d, [PAD], -1, [sg], 5)
    rte, rtx = max(3e-4 / 1.5, 3e-4), max(3e-4 / 1.5003, 3e-4)
    hand = -(1.5003 / 1.5 - 1) - (rte / 2 + rtx / 2 + 0.5 * rtx)
    check("a_time_stop_short", r["reason"][0] == "TS" and r["exit"][0] == PAD + 5 and abs(r["net"][0] - hand) < 1e-15,
          "%s exit=%d" % (r["reason"][0], r["exit"][0]))
    # gap: bar after 10-min gap opens below SL -> exit at OPEN
    t = t0 + np.array([0, 1, 11, 12])
    c = [1.1000, 1.0995, 1.0960, 1.0950]
    o = [1.1000, 1.0995, 1.0970, 1.0960]
    d = mini("EURUSD", t, c, o)
    r = sim_g4.trades_batch(d, [PAD], 1, [sg], 240)
    check("a_gap_exit_at_open", r["reason"][0] == "SL" and r["at_open"][0] and abs(r["gross"][0] - (1.0970 / 1.1 - 1)) < 1e-15)
    # rollover: entry 20:50 UTC (16:50 NY EDT), TS 10 -> exit bar 21:00 UTC = 17:00 NY: cost x3, one swap night
    t = tm("2015-06-02 20:50") + np.arange(12)
    c = np.full(12, 1.1)
    d = mini("EURUSD", t, c)
    r = sim_g4.trades_batch(d, [PAD], 1, [sg], 10)
    rt = 0.8e-4 / 1.1
    hc = rt / 2 + rt / 2 * 3 + 0.5 * rt
    hs = (2.0 - 1.0) / 100 / 360 - 0.01 / 360
    check("a_rollover_x3_and_swap", r["reason"][0] == "TS" and abs(r["cost"][0] - hc) < 1e-15 and abs(r["swap"][0] - hs) < 1e-15,
          "cost=%.3e hand=%.3e swap=%.3e hand=%.3e" % (r["cost"][0], hc, r["swap"][0], hs))
    r2 = sim_g4.trades_batch(d, [PAD], 1, [sg], 10, cost_mult=2.0)
    check("a_cost_x2", abs(r2["cost"][0] - 2 * hc) < 1e-15 and abs(r2["swap"][0] - ((2.0 - 1.0) / 100 / 360 - 2 * 0.01 / 360)) < 1e-15)
    rs = sim_g4.trades_batch(d, [PAD], -1, [sg], 10)
    check("a_swap_sign_short", abs(rs["swap"][0] - (-(2.0 - 1.0) / 100 / 360 - 0.01 / 360)) < 1e-15)
    check("a_cost_rule_jpy", abs(load_g4.rt_cost("USDJPY", 150.0) - 3e-4) < 1e-15 and
          abs(load_g4.rt_cost("AUDUSD", 0.5) - 6e-4) < 1e-15 and abs(load_g4.rt_cost("EURUSD", 1.25) - 0.64e-4) < 1e-15)


# ---------------- N4 gaps + sigma ----------------
def test_b():
    t0 = tm("2015-06-02 08:00")
    t = np.concatenate([t0 + np.arange(40), t0 + 46 + np.arange(40), t0 + 200 + np.arange(60)])
    rng = np.random.default_rng(0)
    c = 1.1 * np.exp(np.cumsum(rng.normal(0, 1e-4, len(t))))
    d = mini("EURUSD", t, c, pad=0)
    sig = np.full(len(t), 1e-4)
    z = sig_g4.zscore(d, 15, sig)
    i_gap = 40  # first bar after 6-min gap (t0+46)
    win_has_gap = (t >= t[i_gap]) & (t - 15 < t[i_gap])  # windows (t-15, t] containing the gap-follower bar
    check("b_gap5_window_rejected", np.isnan(z[win_has_gap]).all() and np.isfinite(z[(t >= t0 + 30) & (t < t0 + 40)]).all())
    i60 = 80  # first bar after 114-min gap
    first30 = (t >= t[i60]) & (t < t[i60] + 30)
    check("b_after_gap60_30min_rejected", np.isnan(z[first30]).all() and np.isfinite(z[t >= t[i60] + 30]).all())
    zz = z[(t >= t0 + 61) & (t < t0 + 80)]
    j = np.searchsorted(t, t[i_gap + 30] - 15, side="right") - 1
    hand = np.log(c[i_gap + 30] / c[j]) / (1e-4 * np.sqrt(15))
    check("b_z_hand", abs(z[i_gap + 30] - hand) < 1e-12 and len(zz) > 0)
    # sigma: pooled std of previous 20 sessions only
    days = pd.bdate_range("2015-03-02", periods=30)
    tt, cc = [], []
    p = 1.1
    for k, dd in enumerate(days):
        base = tm(dd + pd.Timedelta(hours=8))
        r = rng.normal(0, 1e-4 * (1 + k / 10), 100)
        tt.append(base + np.arange(101))
        cc.append(p * np.exp(np.concatenate([[0], np.cumsum(r)])))
        p = cc[-1][-1]
    t2, c2 = np.concatenate(tt), np.concatenate(cc)
    d2 = mini("EURUSD", t2, c2, pad=0)
    s1, info = sig_g4.session_sigma(d2)
    k = 25
    m = (t2 >= tt[k][0]) & (t2 <= tt[k][-1])
    r1 = np.concatenate([np.diff(np.log(x)) for x in cc[k - 20:k]])
    check("b_sigma_prev20_hand", np.allclose(s1[m], r1.std(ddof=1), rtol=1e-10) and np.isnan(s1[t2 <= tt[19][-1]]).all())
    d3 = mini("EURUSD", t2, pad=0, c=np.where(m, c2 * np.exp(rng.normal(0, 1e-3, len(c2))), c2))
    s3, _ = sig_g4.session_sigma(d3)
    m26 = (t2 >= tt[26][0]) & (t2 <= tt[26][-1])
    check("b_sigma_excludes_own_session", np.allclose(s3[m], s1[m]) and not np.allclose(s3[m26], s1[m26]))


# ---------------- real data: causality, excluded years, cutoff ----------------
_REAL = {}


def real():
    if "d" not in _REAL:
        _REAL["d"] = load_g4.load()
    return _REAL["d"]


def test_c():
    data = real()
    d = data["pairs"]["EURUSD"]
    T0 = tm("2013-06-04 12:00")
    base = {(s, N, T): sig_g4.events(d, s, N, T) for s in ("L", "S") for N, T in sig_g4.NT}
    zb = {N: d[("_z", N)].copy() for N in (15, 60)}
    d2 = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in d.items() if not str(k).startswith("_") and not isinstance(k, tuple)}
    m = d2["t"] >= T0
    rng = np.random.default_rng(1)
    f = np.exp(rng.normal(0, 2e-3, m.sum()))
    for kk in ("o", "c", "h", "l"):
        d2[kk][m] = d2[kk][m] * f
    ok = True
    for key, ev in base.items():
        ev2 = sig_g4.events(d2, *key)
        b1 = ev[d["t"][ev] < T0 - 1]
        b2 = ev2[d2["t"][ev2] < T0 - 1]
        ok &= np.array_equal(b1, b2)
        ok &= (d["t"][ev + 1] > d["t"][ev]).all()
    zsame = all(np.array_equal(zb[N][d["t"] < T0], d2[("_z", N)][d["t"] < T0], equal_nan=True) for N in (15, 60))
    zchg = not np.array_equal(zb[60][d["t"] >= T0 + 30 * 1440], d2[("_z", 60)][d["t"] >= T0 + 30 * 1440], equal_nan=True)
    check("c_causal_events_before_T0_unchanged", ok and zsame and zchg)
    pd.DataFrame(dict(event_t=pd.to_datetime(d["t"][base[("L", 60, 3.0)][:50]] * 60, unit="s"),
                      entry_t=pd.to_datetime(d["t"][base[("L", 60, 3.0)][:50] + 1] * 60, unit="s"))).to_csv(
        os.path.join(OUT, "sample_event_entry_minutes_EURUSD_L603.csv"), index=False)
    allbad = 0
    for p, dd in data["pairs"].items():
        for s in ("L", "S"):
            for N, T in sig_g4.NT:
                ev = sig_g4.events(dd, s, N, T)
                allbad += int(dd["bad"][ev].sum() + dd["bad"][ev + 1].sum())
    check("c_excluded_pair_years_no_events", allbad == 0)
    first = (d["t"] >= tm("2009-01-01")) & (d["t"] < tm("2009-01-20"))
    check("c_sigma_undefined_20_sessions_after_excluded_year", np.isnan(d["_sig1"][first]).all() and
          np.isfinite(d["_sig1"][(d["t"] >= tm("2009-03-02")) & (d["t"] < tm("2009-03-03"))]).all())
    g = data["pairs"]["GBPUSD"]
    check("c_gbp_2009_excluded", g["bad"][g["year"] == 2009].all() and not g["bad"][g["year"] == 2010].any())


def test_g():
    for cut, tok in (("2020-01-01", None), ("2021-06-30", "x")):
        try:
            load_g4.load(pairs=["EURUSD"], cutoff=cut, holdout=tok)
            ok = False
        except PermissionError:
            ok = True
        check("g_refuse_cutoff_%s" % cut, ok)
    data = real()
    mx = max(int(d["t"].max()) for d in data["pairs"].values())
    check("g_real_max_le_cutoff", mx < tm("2020-01-01"), str(pd.to_datetime(mx * 60, unit="s")))
    try:
        sim_g4.run_config(data, sig_g4.configs()[0])
        ok = False
    except PermissionError:
        ok = True
    check("g_sim_real_locked", ok)
    check("g_perm_p_plus1", abs(eval_g4.perm_p([0, 1, 2], 1.5) - 0.5) < 1e-15 and abs(eval_g4.perm_p([0] * 499, 9) - 1 / 500) < 1e-15)


# ---------------- synthetic market ----------------
def synth(seed=1, effect=True, pairs=("EURUSD", "USDJPY"), start="2005-01-03", end="2019-12-31"):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end)
    base = (days.values.astype("datetime64[m]").astype(np.int64))
    data = dict(pairs={}, rates=rates_const(), cutoff=pd.Timestamp(end), real=False)
    for p in pairs:
        t = (base[:, None] + 360 + np.arange(720)[None, :]).ravel()  # 06:00-17:59 UTC
        n = len(t)
        s1 = 1.5e-4
        # pure noise with intraday volatility clustering (hourly vol multiplier exp(0.7 N(0,1))) so |z| >= 3-4 events are
        # frequent without any planted directional effect
        hv = np.repeat(np.exp(0.7 * rng.normal(size=n // 60 + 1)), 60)[:n]
        lr = rng.normal(0, s1, n) * hv / np.exp(0.245)
        if effect:
            s60 = s1 * np.sqrt(60)
            for kind, rate, sz, rb in (("crash", 1 / 1000, -1.5e-3, 3.0), ("spike", 1 / 2500, 1.5e-3, 1.5)):
                pos = np.flatnonzero(rng.random(n) < rate)
                pos = pos[(pos % 720 > 60) & (pos % 720 < 500)]
                for q in pos:
                    lr[q:q + 3] += sz
                    lr[q + 3:q + 123] += -np.sign(sz) * rb * s60 / 120
        lvl = 100.0 if p == "USDJPY" else 1.2
        c = lvl * np.exp(np.cumsum(lr))
        o = np.concatenate([[c[0]], c[:-1]])
        d = load_g4.build_pair(p, t, o, np.maximum(o, c), np.minimum(o, c), c)
        d["roll_tab"] = load_g4.rollover_table(data["rates"], p)
        data["pairs"][p] = d
    return data


def test_h():
    for tag, eff, want in (("rebound", True, "DAT"), ("noise", False, "KHONG DAT")):
        t = time.time()
        rep = eval_g4.evaluate(synth(seed=5, effect=eff), n_rand=500)
        ok = rep["conclusion"] == want
        if eff:
            ok &= rep["selected"].startswith("L")
        check("h_%s" % tag, ok, "sel=%s concl=%s crit=%s ctrl=%s (%.0fs)" % (rep["selected"], rep["conclusion"], rep["criteria"],
                                                                         {k: (round(v, 4) if isinstance(v, float) else v)
                                                                          for k, v in rep["controls"].items()}, time.time() - t))
        open(os.path.join(OUT, "synthetic_h_%s.md" % tag), "w").write(eval_g4.to_markdown(rep))


def test_e():
    """Controls keep count / pair / UTC hour / month (random) and time-of-day / count (day shift)."""
    data = synth(seed=3, effect=True)
    c = sig_g4.configs()[3]  # L-60-3-24h
    res = sim_g4.run_config(data, c)
    wa, we = sig_g4.WFO
    ev = {}
    for p, r in res.items():
        tt = data["pairs"][p]["t"]
        ev[p] = r["event"][(tt[r["event"]] >= tm(wa))]
    rp = eval_g4.random_pool(data, ev, wa, we)
    dr = eval_g4.random_draw(data, rp, 1, c["TS"], np.random.default_rng(0))
    ok = True
    for p in ev:
        tt = data["pairs"][p]["t"]
        k_real = np.sort(eval_g4.month_index(tt[ev[p]]) * 24 + pd.to_datetime(tt[ev[p]] * 60, unit="s").hour.values)
        b = dr[p]["entry"] - 1
        k_rand = np.sort(eval_g4.month_index(tt[b]) * 24 + pd.to_datetime(tt[b] * 60, unit="s").hour.values)
        ok &= np.array_equal(k_real, k_rand) and not np.array_equal(np.sort(b), np.sort(ev[p]))
    check("e_random_same_count_hour_month", ok)
    sp = eval_g4.shift_pool(data, ev, wa, we)
    ds = eval_g4.shift_draw(data, sp, 1, c["TS"], np.random.default_rng(0))
    ok = True
    for p in ev:
        tt = data["pairs"][p]["t"]
        b = ds[p]["entry"] - 1
        mod = data["pairs"][p]["mod"]  # NY minute of day (shift keeps NY time of session)
        h_real = np.sort(mod[ev[p]])
        h_shift = np.sort(mod[b])
        ok &= len(b) >= 0.95 * len(ev[p]) and np.mean(np.isin(h_shift, h_real)) > 0.99 and not np.array_equal(np.sort(b), np.sort(ev[p]))
    check("e_shift_keeps_time_of_day_count", ok)


def test_f():
    seen = []
    orig = eval_g4.choose

    def spy(cfgs, train):
        seen.append(len(train))
        return orig(cfgs, train)

    eval_g4.choose = spy
    try:
        base = synth(seed=7, effect=True)
        r1 = eval_g4.evaluate(base, n_rand=5, allow_small=True)
        mod = copy.deepcopy(base)
        for p, d in mod["pairs"].items():
            m = d["t"] >= tm("2013-01-01")
            lr = np.diff(np.log(d["c"]), prepend=np.log(d["c"][0]))
            lr[m] = -lr[m]
            c = np.exp(np.cumsum(lr)) * d["c"][0] / np.exp(lr[0])
            o = np.concatenate([[c[0]], c[:-1]])
            nd = load_g4.build_pair(p, d["t"], o, np.maximum(o, c), np.minimum(o, c), c)
            nd["roll_tab"] = d["roll_tab"]
            mod["pairs"][p] = nd
        r2 = eval_g4.evaluate(mod, n_rand=5, allow_small=True)
        tr_same = all(abs(r1["configs"][k]["train_in_sample"]["sharpe_m"] - r2["configs"][k]["train_in_sample"]["sharpe_m"])
                      < 1e-9 for k in r1["configs"])
        check("f_selection_train_only", r1["selected"] == r2["selected"] and tr_same and
              r1["configs"][r1["selected"]]["wfo"]["total"] != r2["configs"][r2["selected"]]["wfo"]["total"] and len(seen) == 2,
              "%s / %s" % (r1["selected"], r2["selected"]))
        cfgs = sig_g4.configs()
        fake = [dict(sharpe_m=1.0) for _ in cfgs]
        check("f_tie_break_short_TS_then_high_T", cfgs[orig(cfgs, fake)]["name"] == "L-15-4-4h")
    finally:
        eval_g4.choose = orig


def test_i():
    a = eval_g4.dumps(eval_g4.evaluate(synth(seed=9), n_rand=20, allow_small=True))
    b = eval_g4.dumps(eval_g4.evaluate(synth(seed=9), n_rand=20, allow_small=True))
    check("i_deterministic", a == b)
    try:
        eval_g4.evaluate(synth(seed=9), n_rand=100)
        ok = False
    except ValueError:
        ok = True
    check("i_nrand_lt_500_refused", ok)


TESTS = dict(a=test_a, b=test_b, c=test_c, e=test_e, f=test_f, g=test_g, h=test_h, i=test_i)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("g4.load").setLevel(logging.WARNING)
    sel = sys.argv[1] if len(sys.argv) > 1 else "".join(TESTS)
    for k in sel:
        t = time.time()
        try:
            TESTS[k]()
        except Exception as e:
            LOG.exception("test %s crashed", k)
            check("%s_CRASH" % k, False, repr(e))
        LOG.info("test %s done %.1fs", k, time.time() - t)
    nf = sum(not ok for _, ok, _ in RESULTS)
    with open(os.path.join(OUT, "test_results_%s.txt" % sel), "w") as f:
        for n, ok, dtl in RESULTS:
            f.write("%s %s %s\n" % ("PASS" if ok else "FAIL", n, dtl))
        f.write("TOTAL %d FAIL %d\n" % (len(RESULTS), nf))
    LOG.info("TOTAL %d FAIL %d", len(RESULTS), nf)
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
