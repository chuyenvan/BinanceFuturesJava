"""REX Buoc 1b (PREREG_REX_S1B.md): market-neutral long top / short bottom tu du bao S1 dong bang. KHONG doc 2026."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/rex"))
import rex_s1 as S1  # noqa: E402

log = logging.getLogger("rex1b")
OUT = S1.OUT
NL = NS = 20
CB = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/gate_skipfull_detail_equity.csv")


def prep():
    P = S1.load()
    D = pd.read_parquet(S1.R0.S.W + "/d1.parquet", columns=["sym", "day", "close", "fund_day"])
    D = D[D.day < S1.HO]
    C = D.pivot(index="day", columns="sym", values="close").sort_index()
    FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
    CF = C.ffill(); RET = (CF / CF.shift(1) - 1).fillna(0.0)
    R = C.pct_change(); btc = R["BTCUSDT"]
    beta = R.rolling(90, min_periods=60).cov(btc).div(btc.rolling(90, min_periods=60).var(), axis=0)
    first = C.apply(lambda s: s.first_valid_index())
    return P, C, FD, RET, beta, first


def legs(pred, P, beta, first, buffer=False):
    """Tra ve dict day -> (list long, list short, s)."""
    j = pred.merge(P[["day", "sym", "lqv30", "f7"]], on=["day", "sym"])
    out = {}; prevL, prevS = [], []
    for d, g in j.groupby("day"):
        g = g.sort_values("score", ascending=False)
        rank = {s: i for i, s in enumerate(g.sym)}
        elig = g[(g.lqv30 >= np.log(5e7)) & (g.f7 >= -0.003) & g.sym.map(lambda s: (d - first[s]).days >= 90)]
        if buffer and prevL:
            keepL = [s for s in prevL if s in rank and rank[s] < 2 * NL]
            L = keepL + [s for s in g.sym if s not in keepL][: NL - len(keepL)]
            es = list(elig.sym[::-1])
            keepS = [s for s in prevS if s in es[: 2 * NS]]
            S = keepS + [s for s in es if s not in keepS][: NS - len(keepS)]
        else:
            L = list(g.sym[:NL]); S = list(elig.sym[::-1][:NS])
        S = [s for s in S if s not in L]
        bL = beta.loc[d, L].fillna(1.0).mean() if d in beta.index else 1.0
        bS = beta.loc[d, S].fillna(1.0).mean() if (d in beta.index and S) else 1.0
        out[d] = (L, S, float(np.clip(bL / bS, 0.5, 2.0)) if bS > 0 else 1.0)
        prevL, prevS = L, S
    return out


def run(lg, h, C, FD, RET, ca=0.001):
    days = sorted(lg)
    cols = RET.columns
    W1 = pd.DataFrame(0.0, index=pd.DatetimeIndex(days), columns=cols)
    WL = W1.copy(); WS = W1.copy()
    for d, (L, S, s) in lg.items():
        WL.loc[d, L] = 1.0 / NL
        if S:
            WS.loc[d, S] = -s / NS
    WL = WL.rolling(h, min_periods=1).sum() / h; WS = WS.rolling(h, min_periods=1).sum() / h
    W = WL + WS
    nxt = RET.shift(-1).reindex(W.index); fn = FD.shift(-1).reindex(W.index)
    turn = W.diff().abs().sum(axis=1).fillna(W.iloc[0].abs().sum())
    gl = (WL * nxt).sum(axis=1) - (WL * fn).sum(axis=1)
    gs = (WS * nxt).sum(axis=1) - (WS * fn).sum(axis=1)
    net = gl + gs - turn * ca
    worst_name = (WS * nxt).min(axis=1)
    df = pd.DataFrame({"net": net, "long": gl, "short": gs, "turn": turn, "btc": nxt["BTCUSDT"], "worst_short_name": worst_name})
    df.index = df.index + pd.Timedelta(days=1)
    return df.dropna()


def stats(df, a, b):
    s = df[(df.index > a) & (df.index <= b + pd.Timedelta(days=1))]
    r = s.net
    eq = (1 + r).cumprod(); mo = r.groupby(r.index.to_period("M")).sum()
    o = {"sh": float(r.mean() / r.std() * np.sqrt(365)), "ann": float(r.mean() * 365), "maxdd": float((eq / eq.cummax() - 1).min()),
         "worst_day": float(r.min()), "worst_week": float(r.rolling(7).sum().min()), "pos_month": float((mo > 0).mean()),
         "by_year_sh": {int(y): round(float(g.mean() / g.std() * np.sqrt(365)), 2) for y, g in r.groupby(r.index.year) if len(g) > 30},
         "corr_btc": float(r.corr(s.btc)), "long_ann": float(s.long.mean() * 365), "short_ann": float(s.short.mean() * 365),
         "turn": float(s.turn.mean()), "worst_short_name_day": float(s.worst_short_name.min())}
    return o


def corr_cb(df, a, b):
    cb = pd.read_csv(CB, parse_dates=["date_utc"]).set_index("date_utc")["C2_mtm_close"]
    cbr = cb.pct_change()
    j = pd.concat([df.net, cbr.rename("cb")], axis=1).dropna()
    j = j[(j.index > a) & (j.index <= b)]
    w = j.resample("W").sum()
    return float(w.net.corr(w.cb)), int(len(w))


def main():
    P, C, FD, RET, beta, first = prep()
    res = {}
    var = {"N1": ("C1", 1, False), "N3": ("C3", 3, False), "N7": ("C7", 7, False), "N1b": ("C1", 1, True)}
    dfs = {}
    for k, (pv, h, buf) in var.items():
        pred = pd.read_parquet(OUT + f"/pred_s1_{pv}.parquet")
        pred = pred[pred.day < S1.HO]
        lg = legs(pred, P, beta, first, buffer=buf)
        df = run(lg, h, C, FD, RET); df2 = run(lg, h, C, FD, RET, ca=0.002)
        dfs[k] = (df, df2)
        dev = stats(df, S1.DEV0, S1.DEV1); dev2 = stats(df2, S1.DEV0, S1.DEV1)
        cc = corr_cb(df, S1.DEV0, S1.DEV1)
        res[k] = {"dev": dev, "dev_cost2x_sh": dev2["sh"], "corr_cb_week": cc, "n_short_avg": float(np.mean([len(v[1]) for v in lg.values()])),
                  "s_avg": float(np.mean([v[2] for v in lg.values()]))}
        log.info("%s DEV Sh %+.2f ann %+.1f%% dd %.2f wday %.3f wweek %.3f posm %.2f yr %s corrBTC %+.2f | long %+.1f%% short %+.1f%% | turn %.2f | x2 %+.2f | cb %s | nS %.1f s %.2f | worst short name %.3f",
                 k, dev["sh"], 100 * dev["ann"], dev["maxdd"], dev["worst_day"], dev["worst_week"], dev["pos_month"], dev["by_year_sh"], dev["corr_btc"],
                 100 * dev["long_ann"], 100 * dev["short_ann"], dev["turn"], dev2["sh"], cc, res[k]["n_short_avg"], res[k]["s_avg"], dev["worst_short_name_day"])
        df.to_csv(OUT + f"/s1b_{k}.csv")
    win = max(res, key=lambda k: res[k]["dev"]["sh"])
    d = res[win]["dev"]; df, df2 = dfs[win]
    val = stats(df, S1.VAL0, S1.VAL1)
    G = {"G1": d["sh"] >= 1.5, "G2": all(d["by_year_sh"].get(y, -1) > 0 for y in (2022, 2023, 2024)) and d["pos_month"] >= 0.65,
         "G3": d["maxdd"] >= -0.25, "G4": d["worst_day"] >= -0.08, "G5": abs(d["corr_btc"]) <= 0.30, "G6": res[win]["dev_cost2x_sh"] >= 0.8,
         "G7": val["sh"] >= 0.8 and val["ann"] > 0}
    res["winner"] = {"name": win, "gates": {k: bool(v) for k, v in G.items()}, "val": val, "verdict": "GO" if all(G.values()) else "NO-GO"}
    log.info("WINNER %s | gates %s | VAL Sh %+.2f ann %+.1f%% dd %.2f wday %.3f posm %.2f corrBTC %+.2f long %+.1f%% short %+.1f%% | %s", win, res["winner"]["gates"],
             val["sh"], 100 * val["ann"], val["maxdd"], val["worst_day"], val["pos_month"], val["corr_btc"], 100 * val["long_ann"], 100 * val["short_ann"], res["winner"]["verdict"])
    json.dump(res, open(OUT + "/s1b_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
