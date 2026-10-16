"""REX Buoc 2a (PREREG_REX_S2A.md): regime cho long top-20 C7. KHONG doc 2026."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/rex"))
import rex_s1 as S1  # noqa: E402
import rex_s1b as S1B  # noqa: E402

log = logging.getLogger("rex2a")
OUT = S1.OUT
K, H = 20, 7


def regimes(P, C):
    btc = C["BTCUSDT"]
    ctx = P.groupby("day")[["br50", "btc_mom28"]].first()
    uni = P.groupby("day").y1.mean()                      # loi suat t -> t+1 cua universe quyet dinh ngay t
    idx = (1 + uni.shift(1).fillna(0)).cumprod()          # muc chi so tai close t (chi dung ret <= t)
    d = ctx.index
    r = pd.DataFrame(index=d)
    r["R0"] = 1.0
    r["R1"] = (btc > btc.rolling(50, min_periods=45).mean()).reindex(d).astype(float)
    r["R2"] = (ctx.br50 > 0.5).astype(float)
    r["R3"] = (ctx.btc_mom28 > 0).astype(float)
    r["R4"] = r.R1 * r.R2
    r["R5"] = (idx > idx.rolling(50, min_periods=45).mean()).astype(float)
    return r.fillna(0.0), uni


def run(W, e, RET, FD, ca):
    We = W.mul(e.reindex(W.index).fillna(0.0), axis=0)
    nxt = RET.shift(-1).reindex(We.index); fn = FD.shift(-1).reindex(We.index)
    turn = We.diff().abs().sum(axis=1).fillna(We.iloc[0].abs().sum())
    net = (We * nxt).sum(axis=1) - (We * fn).sum(axis=1) - turn * ca
    df = pd.DataFrame({"net": net, "turn": turn, "e": e.reindex(We.index).fillna(0.0), "btc": nxt["BTCUSDT"]})
    df.index = df.index + pd.Timedelta(days=1)
    return df.dropna()


def st(df, a, b):
    s = df[(df.index > a) & (df.index <= b + pd.Timedelta(days=1))]
    r = s.net; eq = (1 + r).cumprod(); dd = float((eq / eq.cummax() - 1).min())
    yr = {int(y): round(float(g.sum()), 4) for y, g in r.groupby(r.index.year)}
    return {"sh": float(r.mean() / r.std() * np.sqrt(365)) if r.std() > 0 else 0.0, "ann": float(r.mean() * 365), "maxdd": dd,
            "calmar": float(r.mean() * 365 / abs(dd)) if dd < 0 else None, "year_sum": yr,
            "in_mkt": float(s.e.mean()), "switches": int(s.e.diff().abs().sum()), "corr_btc": float(r.corr(s.btc))}


def main():
    P, C, FD, RET, beta, first = S1B.prep()
    pred = pd.read_parquet(OUT + "/pred_s1_C7.parquet"); pred = pred[pred.day < S1.HO]
    days = pd.DatetimeIndex(sorted(pred.day.unique()))
    top = pred.sort_values("score", ascending=False).groupby("day").head(K)
    W1 = (pd.crosstab(top.day, top.sym).astype(float) / K).reindex(index=days, columns=RET.columns, fill_value=0.0)
    W = W1.rolling(H, min_periods=1).sum() / H
    WB = pd.DataFrame(0.0, index=days, columns=RET.columns); WB["BTCUSDT"] = 1.0
    pu = P[P.day.isin(days)]
    WU = (pd.crosstab(pu.day, pu.sym).astype(float)).reindex(index=days, columns=RET.columns, fill_value=0.0)
    WU = WU.div(WU.sum(axis=1), axis=0).fillna(0.0)
    reg, _ = regimes(P, C)
    assert reg.index.max() < S1.HO
    res = {}
    for k in reg.columns:
        e = reg[k]
        pf = run(W, e, RET, FD, 0.001); pf2 = run(W, e, RET, FD, 0.002)
        bt = run(WB, e, RET, FD, 0.0006); un = run(WU, e, RET, FD, 0.001)
        o = {"pf": st(pf, S1.DEV0, S1.DEV1), "pf_x2_sh": st(pf2, S1.DEV0, S1.DEV1)["sh"],
             "btc_reg": st(bt, S1.DEV0, S1.DEV1), "uni_reg": st(un, S1.DEV0, S1.DEV1)}
        cbv = S1B.corr_cb(pf, S1.DEV0, S1.DEV1); o["corr_cb_week"] = cbv
        res[k] = o
        log.info("%s PF Sh %+.2f ann %+.1f%% dd %.2f calmar %s yr %s in %.2f sw %d x2 %+.2f corrBTC %+.2f cb %+.2f | BTCreg Sh %+.2f ann %+.1f%% dd %.2f | UNIreg Sh %+.2f dd %.2f",
                 k, o["pf"]["sh"], 100 * o["pf"]["ann"], o["pf"]["maxdd"], o["pf"]["calmar"] and round(o["pf"]["calmar"], 2), o["pf"]["year_sum"], o["pf"]["in_mkt"],
                 o["pf"]["switches"], o["pf_x2_sh"], o["pf"]["corr_btc"], cbv[0], o["btc_reg"]["sh"], 100 * o["btc_reg"]["ann"], o["btc_reg"]["maxdd"],
                 o["uni_reg"]["sh"], o["uni_reg"]["maxdd"])
    win = max([k for k in reg.columns if k != "R0"], key=lambda k: res[k]["pf"]["sh"])
    d = res[win]
    e = reg[win]
    pf = run(W, e, RET, FD, 0.001); bt = run(WB, e, RET, FD, 0.0006)
    val = st(pf, S1.VAL0, S1.VAL1); valb = st(bt, S1.VAL0, S1.VAL1)
    G = {"G1": d["pf"]["sh"] >= 1.0, "G2": all(d["pf"]["year_sum"].get(y, -1) >= 0 for y in (2022, 2023, 2024)),
         "G3": d["pf"]["maxdd"] >= -0.30, "G4": d["pf_x2_sh"] >= 0.7, "G5": d["pf"]["sh"] >= d["btc_reg"]["sh"],
         "G6": val["sh"] >= 0.5 and val["ann"] > 0}
    res["winner"] = {"name": win, "gates": {k: bool(v) for k, v in G.items()}, "val": val, "val_btc_reg": valb,
                     "verdict": "GO" if all(G.values()) else ("BTC_REGIME_CANDIDATE" if all(G[g] for g in ("G1", "G2", "G3", "G4", "G6")) else "NO-GO")}
    log.info("WINNER %s gates %s | VAL PF Sh %+.2f ann %+.1f%% dd %.2f in %.2f | VAL BTCreg Sh %+.2f ann %+.1f%% | %s", win, res["winner"]["gates"], val["sh"],
             100 * val["ann"], val["maxdd"], val["in_mkt"], valb["sh"], 100 * valb["ann"], res["winner"]["verdict"])
    pf.to_csv(OUT + "/s2a_winner.csv")
    json.dump(res, open(OUT + "/s2a_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
