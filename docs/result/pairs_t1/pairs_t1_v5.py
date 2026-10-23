#!/usr/bin/env python3
"""PAIRS_T1 V5 - independent re-computation ("tinh tay") of one pre-registered week for M1:
window k* = first trading window with start >= 2023-06-01 00:00Z.
Independent path: raw Vision 1m parquet -> pandas hourly bars; pandas universe; statsmodels coint (library);
plain-loop trade rule; direct PnL arithmetic; raw funding parquet. Compared with the engine output.
Also: equivalence of the engine's fast ADF with statsmodels coint on 400 random formation pairs."""
import json
import logging
import os
import pickle
import sys

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pairs_t1_core as K  # noqa: E402  (constants + engine output comparison only)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("v5")
OUT = os.path.expanduser("~/claude_master/pairs/out")
RAWS = [os.path.expanduser("~/claude_master/pairs/data/kline1m"), os.path.expanduser("~/vz_e1/raw")]
HMS = 3600000


def raw_hourly(months):
    fr = []
    for mm in months:
        p = [os.path.join(r, "kline1m-%s.parquet" % mm) for r in RAWS]
        p = [x for x in p if os.path.exists(x)][0]
        d = pd.read_parquet(p, columns=["ts", "sym", "open", "close", "quote_volume", "active"])
        d = d[d.active]
        d["sym"] = d["sym"].astype(str)
        d["h"] = (d.ts - K.H0_MS) // HMS
        d = d.sort_values(["sym", "ts"])
        g = d.groupby(["sym", "h"]).agg(o=("open", "first"), c=("close", "last"), q=("quote_volume", "sum"))
        fr.append(g)
    return pd.concat(fr)


def main():
    univ = pickle.load(open(os.path.join(OUT, "univ.pkl"), "rb"))
    wins = pickle.load(open(os.path.join(OUT, "pairs_main.pkl"), "rb"))
    h_target = (pd.Timestamp("2023-06-01").value // 10 ** 6 - K.H0_MS) // HMS
    kstar = min(k for k, t, U in univ if t >= h_target)
    w = wins[kstar]
    t = w["t"]
    months = sorted({pd.Timestamp(K.H0_MS + h * HMS, unit="ms").strftime("%Y-%m") for h in (t - K.FORM, t, t + K.TRAD + 2)})
    H = raw_hourly(months)
    C = H["c"].unstack(0)
    O = H["o"].unstack(0)
    Qv = H["q"].unstack(0).fillna(0.0)
    hrs = np.arange(t - K.FORM, t + K.TRAD + 1)
    C = C.reindex(hrs)
    O = O.reindex(hrs)
    Qv = Qv.reindex(hrs).fillna(0.0)
    C = C[[s for s in C.columns if s.endswith("USDT") and "_" not in s]]
    # ---- universe (pandas)
    fc = C.loc[t - K.FORM:t - 1]
    cov = fc.notna().mean()
    rngp = fc.max() / fc.min() - 1
    ok = (cov >= 0.95) & fc.loc[t - 1].notna() & (rngp >= 0.01) & ~C.columns.isin(list(K.EXCL))
    qs = Qv.loc[t - K.FORM:t - 1, C.columns].sum()[ok].sort_values(ascending=False, kind="stable")
    U_ind = sorted(qs.index[:50])
    P = K.Panel()
    U_eng = sorted(str(P.syms[j]) for j in w["U"])
    res = dict(kstar=kstar, t=int(t), start=str(pd.Timestamp(K.H0_MS + t * HMS, unit="ms")),
               universe_match=U_ind == U_eng, n_univ=len(U_ind))
    # ---- hourly bars equal to panel
    dmax = 0.0
    for s in U_eng:
        j = int(np.where(P.syms == s)[0][0])
        a = P.C[hrs, j]
        b = C[s].values
        m = np.isfinite(a) | np.isfinite(b)
        dmax = max(dmax, float(np.nanmax(np.abs(a[m] - b[m]))) if m.any() else 0.0)
    res["max_abs_close_diff_vs_panel"] = dmax
    # ---- EG with statsmodels coint
    lp = np.log(fc[U_ind].ffill().bfill())
    cand = []
    for a_ in range(len(U_ind)):
        for b_ in range(a_ + 1, len(U_ind)):
            ya, yb = lp.iloc[:, a_].values, lp.iloc[:, b_].values
            if not np.corrcoef(ya, yb)[0, 1] > 0:
                continue
            r1 = coint(ya, yb, trend="c", autolag="aic")
            r2 = coint(yb, ya, trend="c", autolag="aic")
            (st, p_, (y, x)) = (r1[0], r1[1], (a_, b_)) if r1[0] <= r2[0] else (r2[0], r2[1], (b_, a_))
            Y, X = lp.iloc[:, y].values, lp.iloc[:, x].values
            beta, alpha = np.polyfit(X, Y, 1)
            e = Y - beta * X - alpha
            if beta <= 0 or not p_ < 0.05:
                continue
            de = np.diff(e)
            lam = np.polyfit(e[:-1], de, 1)[0]
            hl = -np.log(2) / lam if lam < 0 else np.inf
            if 6 <= hl <= 168:
                cand.append(dict(y=U_ind[y], x=U_ind[x], stat=st, p=p_, beta=beta, alpha=alpha, sigma=e.std(ddof=1), hl=hl))
    cand.sort(key=lambda d: d["stat"])
    top = cand[:10]
    eng = [(str(P.syms[d["y"]]), str(P.syms[d["x"]])) for d in w["p1"]]
    res["m1_pairs_independent"] = [(d["y"], d["x"], round(d["stat"], 4), round(d["hl"], 2)) for d in top]
    res["m1_pairs_engine"] = [(str(P.syms[d["y"]]), str(P.syms[d["x"]]), round(d["stat"], 4), round(d["hl"], 2)) for d in w["p1"]]
    res["m1_pairs_match"] = [(d["y"], d["x"]) for d in top] == eng
    res["m1_n_pass_independent"] = len(cand)
    res["m1_n_pass_engine"] = w["npass"]
    # ---- trade rule, plain loop, direct arithmetic
    fund = pd.read_parquet(os.path.expanduser("~/claude_master/pairs/data/funding/funding-%s.parquet" % months[0][:4]))
    fund["sym"] = fund["sym"].astype(str)
    trades = []
    for d in top:
        y, x = d["y"], d["x"]
        pos, dis = 0, False
        for h in range(t, t + K.TRAD - 1):
            cy, cx = C.at[h, y], C.at[h, x]
            if not (np.isfinite(cy) and np.isfinite(cx)):
                continue
            zz = (np.log(cy) - d["beta"] * np.log(cx) - d["alpha"]) / d["sigma"]
            if pos == 0:
                if not dis and 2 <= abs(zz) < 4 and np.isfinite(O.at[h + 1, y]) and np.isfinite(O.at[h + 1, x]):
                    pos, e = (-1 if zz > 0 else 1), h + 1
            else:
                why = "mr" if (pos == -1 and zz <= 0) or (pos == 1 and zz >= 0) else (
                    "stop" if abs(zz) >= 4 else ("time" if h + 1 - e >= 2 * d["hl"] else None))
                if why:
                    trades.append((y, x, pos, e, h + 1, why, d["beta"]))
                    pos = 0
                    dis = dis or why != "mr"
        if pos != 0:
            trades.append((y, x, pos, e, t + K.TRAD, "end", d["beta"]))
    rows = []
    for (y, x, pos, e, xh, why, beta) in trades:
        tot = dict(gross=0.0, fee_base=0.0, fund=0.0)
        legs = []
        for s, wv in ((y, pos * 0.1 / (1 + beta)), (x, -pos * 0.1 * beta / (1 + beta))):
            pe, px = O.at[e, s], O.at[xh, s]
            q = wv / pe
            fr = fund[(fund.sym == s) & (fund.ts > K.H0_MS + (e + 0.5) * HMS) & (fund.ts < K.H0_MS + (xh + 0.5) * HMS)]
            fs = 0.0
            for _, r in fr.iterrows():
                hf = int(round((r.ts - K.H0_MS) / HMS))
                mk = O.at[hf, s] if np.isfinite(O.at[hf, s]) else C[s].loc[:hf - 1].ffill().iloc[-1]
                fs -= q * mk * r.rate
            legs.append(dict(sym=s, w=wv, pe=pe, px=px, qty=q, gross=q * (px - pe), fee=0.0007 * (abs(q) * pe + abs(q) * px), fund=fs))
            tot["gross"] += q * (px - pe)
            tot["fee_base"] += 0.0007 * (abs(q) * pe + abs(q) * px)
            tot["fund"] += fs
        rows.append(dict(y=y, x=x, pos=pos, e=e, x_h=xh, why=why, legs=legs, **tot))
    et = w["res"]["M1"]["trades"]
    eng_rows = [dict(y=str(P.syms[tr["key"][0]]), x=str(P.syms[tr["key"][1]]), e=tr["e"], x_h=tr["x"], why=tr["why"],
                     gross=tr["gross"], fee_base=0.0007 * tr["turn"], fund=tr["fund"]) for tr in et]
    key = lambda r: (r["y"], r["x"], r["e"])  # noqa: E731
    a = sorted(rows, key=key)
    b = sorted(eng_rows, key=key)
    res["n_trades_independent"], res["n_trades_engine"] = len(a), len(b)
    res["trades_match"] = len(a) == len(b) and all(
        (r1["y"], r1["x"], r1["e"], r1["x_h"], r1["why"]) == (r2["y"], r2["x"], r2["e"], r2["x_h"], r2["why"])
        and abs(r1["gross"] - r2["gross"]) < 1e-12 and abs(r1["fee_base"] - r2["fee_base"]) < 1e-12
        and abs(r1["fund"] - r2["fund"]) < 1e-12 for r1, r2 in zip(a, b))
    res["week_net_independent"] = float(sum(r["gross"] + r["fund"] - r["fee_base"] for r in a))
    res["week_net_engine"] = float(w["res"]["M1"]["g"][-1] + w["res"]["M1"]["f"][-1] - 0.0007 * w["res"]["M1"]["u"][-1])
    res["example_trades"] = a[:2]
    # ---- fast ADF vs statsmodels coint on 400 random formation pairs
    rng = np.random.default_rng(20261023)
    diffs, flipdec = [], 0
    for _ in range(400):
        k, tt, U = univ[int(rng.integers(len(univ)))]
        i, j = rng.choice(len(U), 2, replace=False)
        lpp = K.form_logprices(P, tt, U)
        s_eng = K.eg_test(lpp[:, i], lpp[:, j])[0]
        s_sm, p_sm, _ = coint(lpp[:, i], lpp[:, j], trend="c", autolag="aic")
        diffs.append(abs(s_eng - s_sm))
        from statsmodels.tsa.adfvalues import mackinnonp
        if (mackinnonp(s_eng, regression="c", N=2) < 0.05) != (p_sm < 0.05):
            flipdec += 1
    diffs = np.array(diffs)
    res["adf_equiv"] = dict(n=400, max_abs_diff=float(diffs.max()), frac_lt_1e8=float((diffs < 1e-8).mean()),
                            p05_decision_flips=flipdec)
    res["PASS"] = bool(res["universe_match"] and res["m1_pairs_match"] and res["trades_match"] and dmax == 0.0
                       and res["adf_equiv"]["p05_decision_flips"] == 0)
    json.dump(res, open(os.path.join(OUT, "v5.json"), "w"), indent=1, default=str)
    log.info("V5 PASS=%s univ=%s pairs=%s trades=%s (%d/%d) dmax=%g adf=%s", res["PASS"], res["universe_match"],
             res["m1_pairs_match"], res["trades_match"], len(a), len(b), dmax, res["adf_equiv"])


if __name__ == "__main__":
    main()
