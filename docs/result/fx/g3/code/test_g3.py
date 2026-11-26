#!/usr/bin/env python3
"""G3 tests (a)..(j). Usage: python3 test_g3.py [letters, e.g. abc]. Real data is used ONLY for loading, inventory and
signal/position causality (no returns). Return-based tests run on synthetic data only."""
import copy
import logging
import os
import shutil
import sys
import tempfile
import time

import numpy as np
import pandas as pd

import eval_g3
import load_g3
import sig_g3
import sim_g3

LOG = logging.getLogger("g3.test")
OUT = os.path.expanduser("~/claude_master/w3/fx/g3/out")
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    LOG.info("%s %s %s", "PASS" if cond else "FAIL", name, detail)


_REAL = {}


def real():
    if "d" not in _REAL:
        _REAL["d"] = load_g3.load()
    return _REAL["d"]


# ---------------- synthetic market ----------------
def synth(seed=7, effect=1, mu=0.001, noise=0.006, start="1986-01-01", end="2019-12-31"):
    rng = np.random.default_rng(seed)
    D = pd.bdate_range(start, end)
    tues = pd.date_range(pd.Timestamp(start) + pd.Timedelta(days=6), end, freq="W-TUE")
    ccys = load_g3.CCYS
    base = {}
    for c in ccys:
        e = rng.normal(0, 0.05, len(tues))
        x = np.zeros(len(tues))
        for i in range(1, len(tues)):
            x[i] = 0.97 * x[i - 1] + e[i]
        base[c] = x
    cot = {}
    for g in load_g3.GROUPS:
        rows = []
        for c in ccys:
            x = base[c] + rng.normal(0, 0.005, len(tues))
            m = np.ones(len(tues), bool)
            if c == "EUR":
                m &= tues >= pd.Timestamp("1999-01-05")
            if g != "NonComm_LEG":
                m &= tues >= pd.Timestamp("2006-06-13")
            rows.append(pd.DataFrame(dict(date=tues[m], ccy=c, x=x[m], name="SYNTH")))
        cot[g] = pd.concat(rows).sort_values(["ccy", "date"]).reset_index(drop=True)
    ex = pd.DataFrame(dict(report_date=pd.DatetimeIndex([]), pub=pd.DatetimeIndex([]), event=[]))
    zs = sig_g3.zscores(cot["NonComm_LEG"], 52, ex)
    px, quote = {}, {}
    for c in ccys:
        zc = zs[zs["ccy"] == c].dropna(subset=["z"])
        zd = pd.Series(zc["z"].values, index=pd.DatetimeIndex(zc["anchor"])).groupby(level=0).last()
        zd = zd.reindex(D.union(zd.index)).ffill().reindex(D).fillna(0.0).values
        drift = effect * mu * np.clip(zd / 1.5, -1, 1)
        lr = drift + rng.normal(0, noise, len(D))
        lvl = 0.01 if c == "JPY" else 1.0
        p = lvl * np.exp(np.cumsum(lr))
        p[rng.random(len(D)) < 0.01] = np.nan  # single-day holidays
        if c == "EUR":
            p[D < pd.Timestamp("1999-01-04")] = np.nan
        px[c] = p
        quote[c] = p if load_g3.CCY[c]["quote"] == "XXXUSD" else 1.0 / p
    months = pd.date_range("1985-01-01", end, freq="MS")
    rates = pd.DataFrame({c: 3.0 for c in ["USD"] + ccys}, index=months)
    return dict(cot=cot, px=pd.DataFrame(px, index=D), quote=pd.DataFrame(quote, index=D), rates=rates, exceptions=ex,
                cutoff=pd.Timestamp(end), real=False)


# ---------------- fake files for loader tests ----------------
LEG_H = ["Market and Exchange Names", "As of Date in Form YYYY-MM-DD", "CFTC Contract Market Code", "Open Interest (All)",
         "Noncommercial Positions-Long (All)", "Noncommercial Positions-Short (All)"]
TFF_H = ["Market_and_Exchange_Names", "Report_Date_as_YYYY-MM-DD", "CFTC_Contract_Market_Code", "Open_Interest_All",
         "Asset_Mgr_Positions_Long_All", "Asset_Mgr_Positions_Short_All", "Lev_Money_Positions_Long_All",
         "Lev_Money_Positions_Short_All"]
FX_FAKE = {"DEXUSEU": (1.0, 1.1), "DEXJPUS": (100.0, 80.0), "DEXUSUK": (1.5, 1.65), "DEXSZUS": (1.0, 1.25),
           "DEXCAUS": (1.25, 1.0), "DEXUSAL": (0.8, 0.88), "DEXUSNZ": (0.5, 0.45)}
HAND_RET = {"EUR": 0.10, "JPY": 0.25, "GBP": 0.10, "CHF": -0.20, "CAD": 0.25, "AUD": 0.10, "NZD": -0.10}


def make_fake_dir():
    t = tempfile.mkdtemp(prefix="g3test_")
    der = os.path.join(t, "derived")
    os.mkdir(der)
    for s, (v0, v1) in FX_FAKE.items():
        with open(os.path.join(der, "FRED_%s.csv" % s), "w") as f:
            f.write("date,v\n2010-01-04,%s\n2010-01-05,%s\n2010-01-06,\n2020-01-02,%s\n" % (v0, v1, v1 * 9))
    for rid in ["US", "EZ", "GB", "JP", "CH", "CA", "AU", "NZ"]:
        with open(os.path.join(der, "FRED_IR3TIB01%sM156N.csv" % rid), "w") as f:
            f.write("date,v\n2009-12-01,1.0\n2010-01-01,1.0\n2020-01-01,9.0\n")
    leg = [("EUROPEAN CURRENCY UNIT - INTERNATIONAL MONETARY MARKET", "1986-01-15", "099741", 1000, 600, 200),
           ("EURO FX - CHICAGO MERCANTILE EXCHANGE", "2005-01-04", "099741", 1000, 600, 200),
           ("EUROPEAN CURRENCY UNIT - INTERNATIONAL MONETARY MARKET", "2005-01-11", "099741", 1000, 600, 200),
           ("POUND STERLING - INTERNATIONAL MONETARY MARKET", "1999-01-05", "096742", 1000, 100, 300),
           ("BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE", "2004-01-06", "096742", 1000, 100, 300),
           ("BRITISH POUND - CHICAGO MERCANTILE EXCHANGE", "2019-12-31", "096742", 1000, 100, 300),
           ("EURO FX/BRITISH POUND XRATE - CHICAGO MERCANTILE EXCHANGE", "2015-01-06", "299741", 1000, 1, 2),
           ("EURO FX - CHICAGO MERCANTILE EXCHANGE", "2020-01-07", "099741", 1000, 999, 0)]
    with open(os.path.join(der, "cot_legacy_fx_cut.csv"), "w") as f:
        f.write(",".join('"%s"' % h for h in LEG_H) + "\n")
        for r in leg:
            f.write('"%s",%s,%s,%d,%d,%d\n' % r)
    with open(os.path.join(der, "cot_tff_fx_cut.csv"), "w") as f:
        f.write(",".join(TFF_H) + "\n")
        f.write('"EURO FX - CHICAGO MERCANTILE EXCHANGE",2010-01-05,099741,1000,100,400,300,100\n')
        f.write('"EURO FX - CHICAGO MERCANTILE EXCHANGE",2020-01-07,099741,1000,100,400,300,100\n')
    with open(os.path.join(t, "cot_release_exceptions.csv"), "w") as f:
        f.write("report_date,actual_publish_date,normal_publish_date,event,source\n2013-10-01,2013-10-25,2013-10-04,s,x\n"
                "2025-09-30,2025-11-19,2025-10-03,s,x\n")
    return t


def test_cost_rule():
    """ERRATA2 J1 hand answers: round trip = max(3 pip / quote, 3 bp); EURUSD 0.8 pip / quote."""
    D = pd.bdate_range("2010-01-04", periods=2)
    q = {"EUR": 1.25, "JPY": 150.0, "GBP": 1.5, "AUD": 0.5, "CAD": 1.0, "CHF": 0.9, "NZD": 0.25}
    hand_rt = {"EUR": 0.8e-4 / 1.25, "JPY": 3e-4, "GBP": 3e-4, "AUD": 6e-4, "CAD": 3e-4, "CHF": 3.0e-4 / 0.9, "NZD": 12e-4}
    # JPY: 3*0.01/150 = 2e-4 < 3 bp -> 3 bp; GBP: 2e-4 -> 3 bp; AUD: 6e-4; CAD: 3e-4 (tie); CHF: 3.333e-4; NZD: 12e-4
    quote = pd.DataFrame({c: [v, v] for c, v in q.items()}, index=D)
    px = pd.DataFrame({c: [(v if load_g3.CCY[c]["quote"] == "XXXUSD" else 1 / v)] * 2 for c, v in q.items()}, index=D)
    months = pd.date_range("2009-01-01", "2010-12-01", freq="MS")
    m = dict(px=px, quote=quote, rates=pd.DataFrame({c: 1.0 for c in ["USD"] + list(q)}, index=months), real=False)
    half = sim_g3.prepare_market(m)["half"][0]
    cc = sim_g3.prepare_market(m)["ccys"]
    for j, c in enumerate(cc):
        check("a_cost_rule_%s" % c, abs(2 * half[j] - hand_rt[c]) < 1e-15, "rt=%.3e hand=%.3e" % (2 * half[j], hand_rt[c]))


def test_a():
    test_cost_rule()
    t = make_fake_dir()
    try:
        d = load_g3.load(data_dir=t, real=False)
        for c, h in HAND_RET.items():
            r = d["px"].at[pd.Timestamp("2010-01-05"), c] / d["px"].at[pd.Timestamp("2010-01-04"), c] - 1
            check("a_quote_%s" % c, abs(r - h) < 1e-12, "long %s vs USD ret=%.6f hand=%.6f" % (c, r, h))
        check("a_missing_is_nan", d["px"].loc["2010-01-06"].isna().all())
        check("a_fake_cutoff_rows_dropped", d["px"].index.max() <= pd.Timestamp("2019-12-31")
              and d["rates"].index.max() <= pd.Timestamp("2019-12-31"))
    finally:
        shutil.rmtree(t)


def test_j():
    t = make_fake_dir()
    try:
        d = load_g3.load(data_dir=t, real=False)
        leg = d["cot"]["NonComm_LEG"]
        eur = leg[leg["ccy"] == "EUR"]
        check("j_fake_ecu_dropped", list(eur["date"]) == [pd.Timestamp("2005-01-04")], str(list(eur["date"])))
        check("j_fake_x", abs(eur["x"].iloc[0] - 0.4) < 1e-12)
        gbp = leg[leg["ccy"] == "GBP"]
        check("j_fake_gbp_3names_merged", len(gbp) == 3 and gbp["name"].nunique() == 3)
        tf = d["cot"]
        check("j_fake_tff_x", abs(tf["LevFunds_TFF"]["x"].iloc[0] - 0.2) < 1e-12
              and abs(tf["AssetMgr_TFF"]["x"].iloc[0] + 0.3) < 1e-12)
        check("j_fake_post_cutoff_cot_dropped", all(v["date"].max() <= pd.Timestamp("2019-12-31") for v in tf.values()))
    finally:
        shutil.rmtree(t)
    d = real()
    leg = d["cot"]["NonComm_LEG"]
    eur = leg[leg["ccy"] == "EUR"]
    check("j_real_eur_from_1999", eur["date"].min() >= pd.Timestamp("1999-01-04") and not eur["name"].str.contains(
        "EUROPEAN CURRENCY").any(), str(eur["date"].min().date()))
    nd = d["dropped"].get(("LEG", "099741", "EUROPEAN CURRENCY UNIT - INTERNATIONAL MONETARY MARKET"), 0)
    check("j_real_ecu_rows_dropped", nd == 10, "dropped=%d" % nd)
    for c, nmin in (("GBP", 4), ("AUD", 3), ("NZD", 3)):
        s = leg[leg["ccy"] == c]
        check("j_real_%s_names_merged" % c, s["name"].nunique() >= nmin, " | ".join(sorted(s["name"].unique())))
    g = leg[(leg["ccy"] == "GBP") & (leg["date"] >= "1993-01-01")]["date"].sort_values()
    check("j_real_gbp_continuous_across_renames", g.diff().max() <= pd.Timedelta(days=14), str(g.diff().max()))


def test_g():
    for cut, tok in (("2020-01-01", None), ("2021-06-30", "wrong"), ("2026-10-31", None)):
        try:
            load_g3.load(cutoff=cut, holdout=tok)
            ok = False
        except PermissionError:
            ok = True
        check("g_refuse_cutoff_%s" % cut, ok)
    d = real()
    mx = max([v["date"].max() for v in d["cot"].values()] + [d["px"].index.max(), d["rates"].index.max(),
                                                              d["exceptions"]["report_date"].max()])
    check("g_real_max_date_le_cutoff", mx <= pd.Timestamp("2019-12-31"), str(mx.date()))
    try:
        sim_g3.simulate(d, pd.DataFrame())
        ok = False
    except PermissionError:
        ok = True
    check("g_sim_real_locked", ok)
    try:
        sim_g3.unlock_real("nope")
        ok = False
    except PermissionError:
        ok = True
    check("g_sim_bad_token_refused", ok and not sim_g3._UNLOCK["real"])


def test_d():
    ex = pd.DataFrame(dict(report_date=pd.DatetimeIndex([]), pub=pd.DatetimeIndex([]), event=[]))
    tues = pd.date_range("2010-01-05", periods=5, freq="W-TUE")
    x = pd.DataFrame(dict(date=tues, ccy="EUR", x=[1.0, 2.0, 3.0, 4.0, 10.0]))
    z = sig_g3.zscores(x, 4, ex)
    check("d_hand_z_t4", abs(z["z"].iloc[3] - 1.161895) < 1e-6, "%.6f" % z["z"].iloc[3])
    check("d_hand_z_t5", abs(z["z"].iloc[4] - 1.460778) < 1e-6, "%.6f" % z["z"].iloc[4])
    check("d_short_window_nan", z["z"].iloc[:3].isna().all())
    rng = np.random.default_rng(1)
    tues = pd.date_range("2010-01-05", periods=60, freq="W-TUE")
    xv = rng.normal(size=60)
    for W, drop, expect in ((20, 1, True), (20, 2, False), (52, 2, True), (52, 3, False)):
        keep = np.ones(60, bool)
        keep[59 - W + 1: 59 - W + 1 + drop] = False  # holes inside the window of the last report
        zz = sig_g3.zscores(pd.DataFrame(dict(date=tues[keep], ccy="EUR", x=xv[keep])), W, ex)
        last = zz.iloc[-1]
        check("d_cover_W%d_missing%d" % (W, drop), np.isfinite(last["z"]) == expect, "n_win=%d" % last["n_win"])
        if expect:
            win = xv[keep][-(W - drop):]
            hz = (win[-1] - win.mean()) / win.std(ddof=1)
            check("d_z_matches_hand_W%d" % W, abs(hz - last["z"]) < 1e-12)


def _mini_market():
    D = pd.bdate_range("2010-01-01", "2010-04-30")
    px = pd.DataFrame({"EUR": 1.0}, index=D)
    months = pd.date_range("2009-01-01", "2010-12-01", freq="MS")
    return dict(px=px, quote=px.copy(), rates=pd.DataFrame({"USD": 2.0, "EUR": 2.0}, index=months),
                exceptions=pd.DataFrame(dict(report_date=pd.DatetimeIndex([]), pub=pd.DatetimeIndex([]))), real=False,
                cot={})


def test_e():
    tues = pd.date_range("2010-01-05", periods=5, freq="W-TUE")
    sig = [1, 1, -1, 0, 1]
    book = pd.DataFrame(dict(date=tues, ccy="EUR", anchor=tues + pd.Timedelta(days=7), entry_date=tues + pd.Timedelta(days=7),
                             eligible=True, signal=sig, N_dt=2, z=[2.0, 2.0, -2.0, 0.0, 2.0]))
    hand4 = {"2010-01-12": .125, "2010-01-19": .25, "2010-01-26": .125, "2010-02-02": .125, "2010-02-09": .125,
             "2010-02-16": 0.0, "2010-02-23": .125, "2010-03-09": 0.0}
    hand1 = {"2010-01-12": .5, "2010-01-19": .5, "2010-01-26": -.5, "2010-02-02": 0.0, "2010-02-09": .5, "2010-02-16": 0.0}
    for H, hand in ((4, hand4), (1, hand1)):
        m = _mini_market()
        tr = sim_g3.make_tranches(m, book, H, +1)
        res = sim_g3.simulate(m, tr)
        got = {k: float(res["net_pos"].at[pd.Timestamp(k), "EUR"]) for k in hand}
        check("e_net_position_H%d" % H, all(abs(got[k] - hand[k]) < 1e-12 for k in hand), str(got))
    m = _mini_market()
    tr = sim_g3.make_tranches(m, book, 4, +1)
    half = 0.8e-4 / 2
    c_net = sim_g3.simulate(m, tr, netting=True)["daily"]["cost"]
    c_gross = sim_g3.simulate(m, tr)["daily"]["cost"]  # default = no netting (ERRATA2 J5)
    t = pd.Timestamp("2010-02-09")
    check("e_cost_netting", abs(c_net[t]) < 1e-15 and abs(c_gross[t] + 2 * .125 * half) < 1e-15,
          "net=%g gross=%g" % (c_net[t], c_gross[t]))
    check("e_cost_entry", abs(c_net[pd.Timestamp("2010-01-12")] + .125 * half) < 1e-15)
    # no-netting hand answer, H=4 overlap: open A 01-12, B 01-19, C 01-26, (none 02-02), A close + E open 02-09,
    # B close 02-16, C close 02-23, E close 03-09 -> each event costs 1/8 * half; total 8 events
    hand = {"2010-01-12": 1, "2010-01-19": 1, "2010-01-26": 1, "2010-02-02": 0, "2010-02-09": 2, "2010-02-16": 1,
            "2010-02-23": 1, "2010-03-09": 1}
    got = {k: -c_gross[pd.Timestamp(k)] / (.125 * half) for k in hand}
    check("e_no_netting_hand_H4", all(abs(got[k] - hand[k]) < 1e-9 for k in hand) and abs(c_gross.sum() + 8 * .125 * half)
          < 1e-15, str(got))
    c2 = sim_g3.simulate(m, tr, cost_mult=2.0)["daily"]["cost"]
    check("e_cost_x2", abs(c2.sum() - 2 * c_gross.sum()) < 1e-15)
    nd = sim_g3.make_tranches(m, book, 4, -1)
    check("e_ND_flips_sign", np.allclose(nd["w"].values, -tr["w"].values))


def _perturb(d, T0):
    d2 = dict(d)
    d2["cot"] = {}
    for g, df in d["cot"].items():
        df = df.copy()
        m = df["date"] >= T0
        df.loc[m, "x"] = -3.0 * df.loc[m, "x"] + 0.5
        d2["cot"][g] = df
    for k in ("px", "quote"):
        v = d[k].copy()
        v.loc[v.index >= T0] *= 1.7
        d2[k] = v
    r = d["rates"].copy()
    r.loc[r.index >= T0.to_period("M").to_timestamp()] += 5.0
    d2["rates"] = r
    d2.pop("_mkt", None)
    return d2


def _same(a, b, cols):
    if len(a) != len(b):
        return False
    for c in cols:
        x, y = a[c].values, b[c].values
        if x.dtype.kind == "f":
            if not np.array_equal(x, y, equal_nan=True):
                return False
        elif not (pd.Series(x).fillna(pd.NaT if x.dtype.kind == "M" else -999).values ==
                  pd.Series(y).fillna(pd.NaT if y.dtype.kind == "M" else -999).values).all():
            if not all((p == q) or (pd.isna(p) and pd.isna(q)) for p, q in zip(x, y)):
                return False
    return True


def test_b():
    d = real()
    T0s = [pd.Timestamp(t) for t in ("1995-06-13", "2001-09-11", "2008-10-07", "2013-10-08", "2016-06-21", "2019-06-04")]
    bc = ["date", "ccy", "z", "eligible", "signal", "N_dt", "entry_date"]
    tc = ["ccy", "report_date", "entry_date", "exit_date", "w"]
    books = {}
    for g in load_g3.GROUPS:
        for W in sig_g3.WS:
            b = sig_g3.build_book(d, g, W)
            books[(g, W)] = b
            e = b[b["eligible"]]
            check("b_entry_ge_T_plus_7_%s_W%d" % (g, W), (e["entry_date"] >= e["date"] + pd.Timedelta(days=7)).all())
            zz = b[b["z"].notna()]
            check("b_window_published_before_entry_%s_W%d" % (g, W), (zz["win_max_pub"] < zz["anchor"]).all()
                  and (zz["win_min_date"] > zz["date"] - pd.Timedelta(days=7 * W)).all())
    for T0 in T0s:
        d2 = _perturb(d, T0)
        for g in load_g3.GROUPS:
            if g != "NonComm_LEG" and T0 < pd.Timestamp("2007-06-01"):
                continue
            for W in sig_g3.WS:
                b1 = books[(g, W)]
                b2 = sig_g3.build_book(d2, g, W)
                m1, m2 = b1["date"] < T0, b2["date"] < T0
                ok_b = _same(b1[m1].reset_index(drop=True), b2[m2].reset_index(drop=True), bc)
                changed = not _same(b1[~m1].reset_index(drop=True), b2[~m2].reset_index(drop=True), ["z"])
                ok_t = True
                for H in (1, 4):
                    t1 = sim_g3.make_tranches(d, b1, H, 1)
                    t2 = sim_g3.make_tranches(d2, b2, H, 1)
                    lim = T0 + pd.Timedelta(days=7)
                    ok_t &= _same(t1[t1["entry_date"] < lim].reset_index(drop=True),
                                  t2[t2["entry_date"] < lim].reset_index(drop=True), tc)
                check("b_causal_%s_W%d_T0_%s" % (g, W, T0.date()), ok_b and ok_t and changed,
                      "book_same=%s tranches_same=%s later_changed=%s" % (ok_b, ok_t, changed))
    # 2008-10 hand-check table (x, z, positions only; no PnL) + independent naive z recomputation
    b = books[("NonComm_LEG", 52)]
    h = b[(b["date"] >= "2008-09-30") & (b["date"] <= "2008-10-28") & b["ccy"].isin(["EUR", "GBP"])].copy()
    leg = d["cot"]["NonComm_LEG"]
    nz = []
    for r in h.itertuples():
        s = leg[(leg["ccy"] == r.ccy) & (leg["date"] > r.date - pd.Timedelta(days=364)) & (leg["date"] <= r.date)]["x"]
        nz.append((s.iloc[-1] - s.mean()) / s.std())
    h["z_naive"] = nz
    h["w_H4_TD"] = np.where(h["eligible"], h["signal"] / (h["N_dt"] * 4), 0.0)
    h[["date", "ccy", "x", "z", "z_naive", "n_win", "N_dt", "signal", "entry_date", "w_H4_TD"]].to_csv(
        os.path.join(OUT, "handcheck_2008_10_EUR_GBP_noPnL.csv"), index=False)
    check("b_handcheck_2008_10_naive_z", np.allclose(h["z"].values, h["z_naive"].values, atol=1e-12), "rows=%d" % len(h))


def test_c():
    d = real()
    ex = d["exceptions"]
    check("c_exceptions_le_cutoff_n", len(ex) == 15 and ex["report_date"].max() <= pd.Timestamp("2019-12-31"), str(len(ex)))
    check("c_all_listed_pub_gt_T6", (ex["pub"] > ex["report_date"] + pd.Timedelta(days=6)).all())
    exs = sig_g3.excluded_set(ex)
    for g in load_g3.GROUPS:
        for W in sig_g3.WS:
            b = sig_g3.build_book(d, g, W)
            hit = b[b["date"].isin(exs)]
            tr = sim_g3.make_tranches(d, b, 4, 1)
            check("c_excluded_%s_W%d" % (g, W), len(hit) > 0 and hit["excluded"].all() and (~hit["eligible"]).all()
                  and not tr["report_date"].isin(exs).any(), "rows=%d" % len(hit))
    # synthetic: pub = T+6 kept, T+7 excluded; late-published report not in a later window before its publication
    tues = pd.date_range("2012-01-03", periods=70, freq="W-TUE")
    T6, T7, TL = tues[60], tues[62], tues[64]
    exd = pd.DataFrame(dict(report_date=[T6, T7, TL], pub=[T6 + pd.Timedelta(days=6), T7 + pd.Timedelta(days=7),
                                                          TL + pd.Timedelta(days=30)]))
    s = sig_g3.excluded_set(exd)
    check("c_rule_T6_kept_T7_excluded", T6 not in s and T7 in s and TL in s)
    x = pd.DataFrame(dict(date=tues, ccy="EUR", x=np.random.default_rng(3).normal(size=70)))
    z0 = sig_g3.zscores(x, 52, exd.iloc[:0])
    z1 = sig_g3.zscores(x, 52, exd)
    r_next = z1[z1["date"] == tues[65]].iloc[0]
    r_next0 = z0[z0["date"] == tues[65]].iloc[0]
    r_after = z1[z1["date"] == tues[69]].iloc[0]  # anchor = TL+42 > pub TL+30 -> TL back in window; T7 (pub T+7) is
    # excluded as a SIGNAL but, once published, belongs to later windows (CHOICES C7)
    check("c_late_report_not_in_window_before_pub", r_next["n_win"] == r_next0["n_win"] - 1 and
          r_after["n_win"] == z0[z0["date"] == tues[69]].iloc[0]["n_win"],
          "n_win next=%d (no-ex %d), after=%d" % (r_next["n_win"], r_next0["n_win"], r_after["n_win"]))


def test_f():
    seen = []
    orig = eval_g3.choose_direction

    def spy(tr, te):
        seen.append((tr.index.max(), pd.Timestamp(te)))
        return orig(tr, te)

    eval_g3.choose_direction = spy
    try:
        base = synth(seed=11, effect=1)
        dirs = {}
        for tag, cut in (("orig", None), ("rev2013", "2013-01-01"), ("rev2006", "2006-01-01")):
            dd = copy.deepcopy(base)
            if cut:
                for k in ("px",):
                    v = dd[k]
                    m = v.index >= pd.Timestamp(cut)
                    lr = np.log(v.ffill()).diff()
                    lr[m] = -lr[m]
                    newp = np.exp(lr.fillna(0).cumsum()) * v.ffill().iloc[0]
                    newp[v.isna()] = np.nan
                    dd["px"] = newp
                    dd["quote"] = pd.DataFrame({c: (newp[c] if load_g3.CCY[c]["quote"] == "XXXUSD" else 1 / newp[c])
                                                for c in newp.columns})
            for g in load_g3.GROUPS:
                r = eval_g3.evaluate_group(dd, g, 3, 1)
                dirs[(tag, g)] = (r["direction"], r["configs"]["W52_H4"]["wfo"]["ann_ret"])
        check("f_spy_only_train_seen", all(a <= b for a, b in seen), "calls=%d" % len(seen))
        for g in load_g3.GROUPS:
            check("f_wfo_change_no_dir_change_2013_%s" % g, dirs[("orig", g)][0] == dirs[("rev2013", g)][0],
                  str((dirs[("orig", g)], dirs[("rev2013", g)])))
        g = "NonComm_LEG"
        check("f_wfo_change_no_dir_change_2006_LEG", dirs[("orig", g)][0] == dirs[("rev2006", g)][0] and
              np.sign(dirs[("orig", g)][1]) != np.sign(dirs[("rev2006", g)][1]), str((dirs[("orig", g)], dirs[("rev2006", g)])))
    finally:
        eval_g3.choose_direction = orig


def test_h():
    for tag, eff, want_dir, want in (("cont", 1, "H_TD", "DAT"), ("rev", -1, "H_ND", None), ("noise", 0, None, "KHONG DAT")):
        t = time.time()
        rep = eval_g3.evaluate(synth(seed=5, effect=eff), n_rand=500)
        dirs = {g: r["direction"] for g, r in rep["groups"].items()}
        concl = {g: r["conclusion"] for g, r in rep["groups"].items()}
        c = rep["combined"]
        ok = True
        if want_dir:
            ok &= all(v == want_dir for v in dirs.values())
        if want:
            ok &= c["conclusion"] == want
        if tag == "noise":
            ok &= all(v != "DAT" for v in concl.values())
        check("h_%s" % tag, ok, "dirs=%s groups=%s combined=%s p=%.3f sharpe=%.2f (%.0fs)" % (
            dirs, concl, c["conclusion"], c["random_p"], c["sharpe"], time.time() - t))
        with open(os.path.join(OUT, "synthetic_h_%s.md" % tag), "w") as f:
            f.write(eval_g3.to_markdown(rep))


def test_i():
    s1 = eval_g3.dumps(eval_g3.evaluate(synth(seed=9, effect=1), n_rand=50, allow_small=True))
    s2 = eval_g3.dumps(eval_g3.evaluate(synth(seed=9, effect=1), n_rand=50, allow_small=True))
    check("i_deterministic", s1 == s2, "len=%d" % len(s1))
    try:
        eval_g3.evaluate(synth(seed=9), n_rand=100)
        ok = False
    except ValueError:
        ok = True
    check("i_nrand_lt_500_refused", ok)


def _book5():
    tues = pd.date_range("2010-01-05", periods=5, freq="W-TUE")
    return pd.DataFrame(dict(date=tues, ccy="EUR", anchor=tues + pd.Timedelta(days=7), entry_date=tues + pd.Timedelta(days=7),
                             eligible=True, signal=[1, 1, -1, 0, 1], N_dt=2, z=[2.0, 2.0, -2.0, 0.0, 2.0]))


def test_k():
    """ERRATA3 K1-K3, K6: constants and hand answers that kill A1's surviving mutants."""
    z = [1.2, 1.4999, 1.5, -1.0, -1.5, 2.0, 3.0]
    el = [True, True, True, True, True, True, False]
    check("k_threshold_1_5", list(sig_g3.signal_from_z(z, el)) == [0, 0, 1, 0, -1, 1, 0] and sig_g3.THRESH == 1.5)
    check("k_d9_150", eval_g3.D9_MIN == 150 and not eval_g3.d9_ok(149) and eval_g3.d9_ok(150) and not eval_g3.d9_ok(15))
    check("k_perm_p_plus1", abs(eval_g3.perm_p([0.0, 1.0, 2.0], 1.5) - 0.5) < 1e-15
          and abs(eval_g3.perm_p([0.0] * 499, 1.0) - 1 / 500) < 1e-15)
    # swap sign: EUR 5 %, USD 1 %, flat price; one tranche w = +/-0.25 held 01-12 -> 02-09 (28 calendar days)
    m = _mini_market()
    m["rates"] = pd.DataFrame({"USD": 1.0, "EUR": 5.0}, index=m["rates"].index)
    for sg in (1, -1):
        tr = pd.DataFrame(dict(ccy=["EUR"], entry_date=[pd.Timestamp("2010-01-12")], exit_date=[pd.Timestamp("2010-02-09")],
                               w=[0.25 * sg], sign=[float(sg)]))
        d = sim_g3.simulate(dict(m), tr)["daily"]
        hs = sg * 0.25 * 0.04 * 28 / 360
        hm = -0.25 * 28 * 0.01 / 360
        check("k_swap_sign_%+d" % sg, abs(d["swap"].sum() - hs) < 1e-15, "swap=%.3e hand=%.3e" % (d["swap"].sum(), hs))
        check("k_margin_single_%+d" % sg, abs(d["margin"].sum() - hm) < 1e-15)
    # K2 margin per tranche, H=4 overlap (A+,B+,C-,E+ each 1/8, 28 days each), equal rates
    m = _mini_market()
    tr = sim_g3.make_tranches(m, _book5(), 4, +1)
    d = sim_g3.simulate(m, tr)["daily"]
    hand_tot = -4 * 0.125 * 28 * 0.01 / 360
    day = d["margin"][pd.Timestamp("2010-02-16")]  # held over 02-15 -> 02-16: B, C, E open -> gross 3/8 (net only 1/8)
    check("k_margin_per_tranche_H4", abs(d["margin"].sum() - hand_tot) < 1e-15 and abs(day + 0.375 * 0.01 / 360) < 1e-15,
          "tot=%.4e hand=%.4e day=%.4e" % (d["margin"].sum(), hand_tot, day))
    check("k_margin_x2", abs(sim_g3.simulate(m, tr, cost_mult=2.0)["daily"]["margin"].sum() - 2 * hand_tot) < 1e-15)
    # K3 force close at close_at with closing cost
    r = sim_g3.simulate(m, tr.iloc[:1], close_at="2010-02-01")
    half = 0.8e-4 / 2
    check("k_close_at_cost", abs(r["daily"]["cost"][pd.Timestamp("2010-02-01")] + 0.125 * half) < 1e-15
          and r["net_pos"]["EUR"][pd.Timestamp("2010-02-01"):].abs().max() == 0)
    r = sim_g3.simulate(m, pd.DataFrame(dict(ccy=["EUR"], entry_date=[pd.Timestamp("2010-04-20")], exit_date=[pd.NaT],
                                             w=[0.1], sign=[1.0])))
    check("k_data_end_close_cost", abs(r["daily"]["cost"].iloc[-1] + 0.1 * half) < 1e-15)
    # random control keeps real long/short multiset per ccy-year (not all long)
    syn = synth(seed=3, effect=1)
    b = sig_g3.build_book(syn, "NonComm_LEG", 52)
    tw = sim_g3.make_tranches(syn, b, 4, +1, start="2006-01-01", end="2019-12-31")
    pool = eval_g3.random_pool(syn, b, tw, 4, "2006-01-01", "2019-12-31")
    rt = eval_g3.random_tranches(pool, np.random.default_rng(0))
    key = lambda t: {k: sorted(g["sign"].tolist()) for k, g in
                     t.assign(y=pd.DatetimeIndex(t["entry_date"]).year).groupby(["ccy", "y"])}
    check("k_random_keeps_sign_mix", key(rt) == key(tw) and (rt["sign"] < 0).any() and (rt["sign"] > 0).any()
          and len(rt) == len(tw), "n=%d short=%d" % (len(rt), int((rt["sign"] < 0).sum())))
    st = eval_g3.shift_tranches(eval_g3.shift_pool(syn, b, 1, 4, "2006-01-01", "2019-12-31"), np.random.default_rng(0))
    check("k_block_shift_same_count_per_ccy", st.groupby("ccy").size().to_dict() == tw.groupby("ccy").size().to_dict())


TESTS = dict(a=test_a, b=test_b, c=test_c, d=test_d, e=test_e, f=test_f, g=test_g, h=test_h, i=test_i, j=test_j, k=test_k)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("g3.load").setLevel(logging.WARNING)
    sel = sys.argv[1] if len(sys.argv) > 1 else "".join(TESTS)
    for k in sel:
        t = time.time()
        try:
            TESTS[k]()
        except Exception as e:  # report and continue
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
