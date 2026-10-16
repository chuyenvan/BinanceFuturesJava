"""REX-TF tang 1 (PREREG_REX_TF.md): trend-following Donchian ensemble (Zarattini-Pagani-Barbon 2025). KHONG doc 2026."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/rex"))
import rex_s1 as S1  # noqa: E402
import rex_s1b as S1B  # noqa: E402

log = logging.getLogger("rextf")
OUT = S1.OUT
NS = (5, 10, 20, 30, 60, 90, 150, 250, 360)
HO = pd.Timestamp("2026-01-01")


def load():
    D = pd.read_parquet(S1.R0.S.W + "/d1.parquet", columns=["sym", "day", "close", "qv", "fund_day"])
    D = D[D.day < HO]
    C = D.pivot(index="day", columns="sym", values="close").sort_index()
    Q = D.pivot(index="day", columns="sym", values="qv").reindex(C.index)
    FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
    assert C.index.max() < HO
    return C, Q, FD


def states(c, N):
    """c: np.array close (NaN cho phep). Tra ve mang 0/1 trang thai giu tu close t -> t+1."""
    s = pd.Series(c)
    pmx = s.shift(1).rolling(N, min_periods=N).max().values
    mx = s.rolling(N, min_periods=N).max().values; mn = s.rolling(N, min_periods=N).min().values
    mid = (mx + mn) / 2
    out = np.zeros(len(c)); inn = False; stop = np.nan
    for t in range(len(c)):
        if np.isnan(c[t]):
            inn = False; stop = np.nan; continue
        if inn:
            if not np.isnan(mid[t]):
                stop = max(stop, mid[t])
            if c[t] < stop:
                inn = False
        elif not np.isnan(pmx[t]) and c[t] > pmx[t]:
            inn = True; stop = mid[t]
        out[t] = 1.0 if inn else 0.0
    return out


def build(C, Q, elig_extra=None):
    qv30 = Q.rolling(30, min_periods=20).median()
    first = C.apply(lambda s: s.first_valid_index())
    age = pd.DataFrame({s: (C.index - first[s]).days for s in C.columns}, index=C.index)
    E = (age >= 365) & C.notna() & qv30.notna()
    if elig_extra is not None:
        E = E & elig_extra.reindex(index=C.index, columns=C.columns).fillna(False)
    rk = qv30.where(E).rank(axis=1, ascending=False)
    U = rk <= 20
    cand = U.any()[U.any()].index
    R = C.pct_change()
    sig = R.rolling(90, min_periods=60).std() * np.sqrt(365)
    lev = (0.25 / sig).clip(upper=2.0)
    frac = pd.DataFrame(0.0, index=C.index, columns=cand)
    st_store = {}
    for s in cand:
        c = C[s].values
        acc = np.zeros(len(c))
        for N in NS:
            x = states(c, N); acc += x; st_store[(s, N)] = x
        frac[s] = acc / len(NS)
    W = (frac * lev[cand]).where(U[cand], 0.0).fillna(0.0) / 20.0
    return W, frac, lev, U, st_store


def pnl(W, C, FD, ca=0.001):
    CF = C.ffill(); RET = (CF / CF.shift(1) - 1).fillna(0.0)
    W = W.reindex(columns=RET.columns, fill_value=0.0)
    nxt = RET.shift(-1); fn = FD.shift(-1)
    turn = W.diff().abs().sum(axis=1).fillna(0.0)
    net = (W * nxt).sum(axis=1) - (W * fn).sum(axis=1) - turn * ca
    df = pd.DataFrame({"net": net, "gross_exp": W.sum(axis=1), "turn": turn, "btc": nxt["BTCUSDT"]})
    df.index = df.index + pd.Timedelta(days=1)
    return df.iloc[:-1]


def stats(df, a, b):
    s = df[(df.index > a) & (df.index <= b + pd.Timedelta(days=1))]
    r = s.net; eq = (1 + r).cumprod(); dd = float((eq / eq.cummax() - 1).min())
    beta, alpha = np.polyfit(s.btc.values, r.values, 1)
    bh = s.btc; eqb = (1 + bh).cumprod()
    return {"sh": float(r.mean() / r.std() * np.sqrt(365)), "ann": float(r.mean() * 365), "maxdd": dd,
            "year_sum": {int(y): round(float(g.sum()), 4) for y, g in r.groupby(r.index.year)},
            "alpha_ann": float(alpha * 365), "beta": float(beta), "corr_btc": float(r.corr(bh)),
            "exp_avg": float(s.gross_exp.mean()), "turn": float(s.turn.mean()),
            "btc_bh_sh": float(bh.mean() / bh.std() * np.sqrt(365)), "btc_bh_dd": float((eqb / eqb.cummax() - 1).min())}


def check_states(C, st_store, rng, n=10):
    keys = list(st_store); errs = 0; done = 0
    for _ in range(400):
        s, N = keys[rng.integers(len(keys))]; x = st_store[(s, N)]
        flips = np.where(np.diff(x) != 0)[0] + 1
        if len(flips) == 0:
            continue
        t = flips[rng.integers(len(flips))]; c = C[s].values
        if t < N + 1 or np.isnan(c[t]):
            continue
        if x[t] == 1:   # vao: close > max N ngay truoc
            ok = c[t] > np.nanmax(c[t - N:t]) and not np.isnan(c[t - N:t]).any()
        else:           # ra: close < stop chay tu ngay vao
            t0 = t - 1
            while t0 > 0 and x[t0 - 1] == 1:
                t0 -= 1
            stop = -np.inf
            for u in range(t0, t + 1):
                w = c[u - N + 1:u + 1]
                if len(w) == N and not np.isnan(w).any():
                    stop = max(stop, (w.max() + w.min()) / 2)
            ok = c[t] < stop
        errs += 0 if ok else 1; done += 1
        if done >= n * 2:
            break
    return {"checked": done, "errors": errs, "pass": errs == 0 and done >= n}


def corr_cb(df):
    return S1B.corr_cb(df, S1.DEV0, S1.DEV1)


def main():
    C, Q, FD = load()
    res = {}
    W, frac, lev, U, st = build(C, Q)
    res["TF_V3_univ_min"] = int(U.loc["2022-01-01":].sum(axis=1).min())
    res["TF_V2"] = check_states(C.where(C.notna()), {k: v for k, v in st.items()}, np.random.default_rng(1017))
    # TFBTC
    WB = pd.DataFrame(0.0, index=C.index, columns=["BTCUSDT"])
    WB["BTCUSDT"] = (frac["BTCUSDT"] * lev["BTCUSDT"]).fillna(0.0) if "BTCUSDT" in frac else 0.0
    if "BTCUSDT" not in frac:
        acc = sum(states(C["BTCUSDT"].values, N) for N in NS) / len(NS)
        WB["BTCUSDT"] = (pd.Series(acc, index=C.index) * lev["BTCUSDT"]).fillna(0.0)
    # TF20R: score S1 C7 >= median trong ngay
    pr = pd.read_parquet(OUT + "/pred_s1_C7.parquet")
    pr = pr[pr.day < HO]
    med = pr.groupby("day").score.transform("median")
    ok = pr.assign(ok=pr.score >= med).pivot(index="day", columns="sym", values="ok")
    WR = build(C, Q, elig_extra=ok)[0]
    W = W.loc["2021-06-01":]; WR = WR.loc["2021-06-01":]; WB = WB.loc["2021-06-01":]
    for name, w in (("TF20", W), ("TFBTC", WB), ("TF20R", WR)):
        df = pnl(w, C, FD); df2 = pnl(w, C, FD, ca=0.002)
        o = {"dev": stats(df, S1.DEV0, S1.DEV1), "dev_x2_sh": stats(df2, S1.DEV0, S1.DEV1)["sh"], "val": stats(df, S1.VAL0, S1.VAL1),
             "cb_week": corr_cb(df)}
        res[name] = o
        df.to_csv(OUT + f"/tf_{name}.csv")
        for per in ("dev", "val"):
            x = o[per]
            log.info("%s %s Sh %+.2f ann %+.1f%% dd %.2f yr %s alpha %+.1f%% beta %.2f corrBTC %+.2f exp %.2f turn %.3f | BTC BH Sh %+.2f dd %.2f",
                     name, per.upper(), x["sh"], 100 * x["ann"], x["maxdd"], x["year_sum"], 100 * x["alpha_ann"], x["beta"], x["corr_btc"],
                     x["exp_avg"], x["turn"], x["btc_bh_sh"], x["btc_bh_dd"])
        log.info("%s x2 DEV Sh %+.2f | cb week %s", name, o["dev_x2_sh"], o["cb_week"])
    d = res["TF20"]["dev"]; v = res["TF20"]["val"]
    G = {"G1": d["sh"] >= 0.8, "G2": all(d["year_sum"].get(y, -1) >= -0.05 for y in (2022, 2023, 2024)), "G3": d["maxdd"] >= -0.35,
         "G4": res["TF20"]["dev_x2_sh"] >= 0.5, "G5": d["alpha_ann"] > 0, "G6": v["sh"] >= 0.4 and v["ann"] > 0,
         "G7": res["TF20"]["cb_week"][0] <= 0.5}
    vok = res["TF_V2"]["pass"] and res["TF_V3_univ_min"] >= 20
    res["gates"] = {k: bool(x) for k, x in G.items()}
    res["selector_adds"] = bool(res["TF20R"]["dev"]["sh"] > d["sh"] and res["TF20R"]["val"]["sh"] > v["sh"])
    res["verdict"] = ("GO" if all(G.values()) else "NO-GO") if vok else "DATA-FAIL"
    log.info("TF_V2 %s | V3 univ_min %d | gates %s | selector_adds %s | VERDICT %s", res["TF_V2"], res["TF_V3_univ_min"], res["gates"],
             res["selector_adds"], res["verdict"])
    json.dump(res, open(OUT + "/tf_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
