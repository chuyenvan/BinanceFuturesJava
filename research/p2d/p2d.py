"""P2-D (PREREG_P2D.md): diem REX S1 tren lenh sim K24+skipFull 8 seed. Chi doc."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("p2d")
SIM = "/home/ubuntu/kaggle_sim/out/gqsf-%s/storage/printDone.csv"
SEEDS = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]
REX = os.path.expanduser("~/claude_master/rex")
K1M = os.path.expanduser("~/vz_e1/raw")
OUT = os.path.expanduser("~/claude_master/p2d"); os.makedirs(OUT, exist_ok=True)
TZ = pd.Timedelta(hours=7)
RNG = 1017


def trades(seed):
    T = pd.read_csv(SIM % seed)
    T = T.loc[:, ~T.columns.str.startswith("Unnamed")]
    T["t_utc"] = pd.to_datetime(T.start, format="%Y%m%d %H:%M") - TZ
    T["dU"] = T.t_utc.dt.floor("D")
    T["sday"] = T.dU - pd.Timedelta(days=1)
    T["symU"] = T.sym + "USDT"
    T["year"] = T.t_utc.dt.year
    T["sl"] = (T.status == "STOP_LOSS_DONE").astype(float)
    return T


def scores(model):
    p = pd.read_parquet(f"{REX}/pred_s1_{model}.parquet")
    p["r"] = p.groupby("day").score.rank(pct=True)
    return p[["day", "sym", "r"]].rename(columns={"day": "sday", "sym": "symU"})


def attach(T, S, V):
    x = T.merge(S, on=["sday", "symU"], how="left").merge(V, on=["sday", "symU"], how="left")
    assert (x.sday < x.dU).all()
    x["b"] = [("NA" if np.isnan(r) else "Q%d" % (min(int(r * 5), 4) + 1)) for r in x.r.values]
    return x


def boot_delta(x, B=5000, seed=RNG):
    """Delta = mean(Q1) - mean(Q2..Q5), bootstrap cum theo ngay UTC."""
    x = x[x.b != "NA"]
    if (x.b == "Q1").sum() < 5:
        return np.nan, (np.nan, np.nan), 0
    d0 = x[x.b == "Q1"].profit.mean() - x[x.b != "Q1"].profit.mean()
    g = {k: v for k, v in x.groupby("dU")}
    keys = list(g); rng = np.random.default_rng(seed)
    agg = np.array([[v[v.b == "Q1"].profit.sum(), (v.b == "Q1").sum(), v[v.b != "Q1"].profit.sum(), (v.b != "Q1").sum()] for v in g.values()])
    res = np.empty(B)
    for i in range(B):
        idx = rng.integers(0, len(keys), len(keys)); a = agg[idx].sum(axis=0)
        res[i] = a[0] / max(a[1], 1) - a[2] / max(a[3], 1)
    return float(d0), (float(np.percentile(res, 2.5)), float(np.percentile(res, 97.5))), int((x.b == "Q1").sum())


def table(x):
    g = x.groupby("b").agg(n=("profit", "size"), mean=("profit", "mean"), med=("profit", "median"), win=("profit", lambda s: float((s > 0).mean())),
                           sl=("sl", "mean"), pnl=("pnl", "sum"))
    return g.round(3)


def v1_price(T, n=20):
    s = T[(T.t_utc >= "2022-01-01") & (T.t_utc < "2025-12-01")].sample(n, random_state=RNG)
    ok = 0
    for r in s.itertuples():
        m = r.t_utc.to_period("M")
        k = pd.read_parquet(f"{K1M}/kline1m-{m}.parquet", columns=["ts", "sym", "close"], filters=[("sym", "==", r.symU)])
        v = k.loc[k.ts == int(r.t_utc.value // 1_000_000), "close"]
        if len(v) and abs(float(v.iloc[0]) / r.entry - 1) <= 1e-9:
            ok += 1
    return {"n": n, "match": ok, "pass": ok >= 19}


def dev(x):
    return x[(x.year >= 2022) & (x.year <= 2024)]


def main():
    P = pd.read_parquet(f"{REX}/panel.parquet", columns=["day", "sym", "r_vol30"]).rename(columns={"day": "sday", "sym": "symU", "r_vol30": "vr"})
    res = {}
    T0 = trades("a1")
    res["V1"] = v1_price(T0)
    log.info("V1 %s", res["V1"])
    S = {m: scores(m) for m in ("C1", "C3", "C7")}
    X = {m: attach(T0, S[m], P) for m in S}
    x = X["C1"]
    dv = dev(x); vl = x[x.year == 2025]
    res["V2_cov_dev"] = float((dv.b != "NA").mean())
    d, ci, nq1 = boot_delta(dv)
    res["primary"] = {"delta": d, "ci": ci, "n_q1": nq1, "n_dev": int(len(dv)),
                      "by_year": {int(y): boot_delta(dev(x)[dev(x).year == y], B=1000)[0] for y in (2022, 2023, 2024)},
                      "val_delta": boot_delta(vl, B=2000)[0], "val_ci": boot_delta(vl, B=2000)[1],
                      "q1_pnl_dev": float(dv[dv.b == "Q1"].pnl.sum()), "total_pnl_dev": float(dv.pnl.sum())}
    log.info("PRIMARY C1/a1 DEV delta %+.3f CI %s nQ1 %d / %d | nam %s | VAL %+.3f CI %s | pnl Q1 DEV %.0f / tong %.0f | cov %.3f",
             d, ci, nq1, len(dv), res["primary"]["by_year"], res["primary"]["val_delta"], res["primary"]["val_ci"],
             res["primary"]["q1_pnl_dev"], res["primary"]["total_pnl_dev"], res["V2_cov_dev"])
    log.info("BANG DEV C1/a1:\n%s", table(dv).to_string())
    log.info("BANG VAL C1/a1:\n%s", table(vl).to_string())
    # do ben seed
    seeds = {}
    for s in SEEDS:
        xs = attach(trades(s), S["C1"], P)
        dd, cc, nn = boot_delta(dev(xs), B=2000)
        seeds[s] = {"delta": dd, "ci": cc, "n_q1": nn, "val": boot_delta(xs[xs.year == 2025], B=500)[0]}
        log.info("SEED %-5s DEV delta %+.3f CI %s nQ1 %d | VAL %+.3f", s, dd, cc, nn, seeds[s]["val"])
    res["seeds"] = seeds
    # model khac
    for m in ("C3", "C7"):
        xm = X[m]; dd, cc, nn = boot_delta(dev(xm), B=2000)
        res[f"model_{m}"] = {"delta": dd, "ci": cc, "val": boot_delta(xm[xm.year == 2025], B=500)[0]}
        log.info("MODEL %s DEV delta %+.3f CI %s | VAL %+.3f\n%s", m, dd, cc, res[f"model_{m}"]["val"], table(dev(xm)).to_string())
    # G6: trong tung tercile vol
    dvv = dv[dv.vr.notna() & (dv.b != "NA")].copy()
    dvv["vt"] = pd.qcut(dvv.vr, 3, labels=["lo", "mid", "hi"])
    terc = {}
    for t, g in dvv.groupby("vt"):
        dd, cc, nn = boot_delta(g, B=1000)
        terc[str(t)] = {"delta": dd, "ci": cc, "n_q1": nn, "n": int(len(g))}
    res["vol_terciles"] = terc
    log.info("G6 tercile vol: %s", terc)
    # veto vol don gian de so sanh
    vv = dv[dv.vr.notna()]
    res["vol_veto"] = {"delta_top20vol": float(vv[vv.vr >= 0.8].profit.mean() - vv[vv.vr < 0.8].profit.mean()),
                       "pnl_top20vol": float(vv[vv.vr >= 0.8].pnl.sum())}
    log.info("VETO VOL top20%%: delta %+.3f pnl %.0f", res["vol_veto"]["delta_top20vol"], res["vol_veto"]["pnl_top20vol"])
    # theo loai lenh
    for lv, g in dv.groupby("level"):
        log.info("LEVEL %s:\n%s", lv, table(g).to_string())
    p = res["primary"]
    G = {"G1": p["delta"] < 0 and p["ci"][1] < 0, "G2": all(v < 0 for v in p["by_year"].values()), "G3": p["val_delta"] < 0,
         "G4": p["q1_pnl_dev"] < 0, "G5": sum(v["delta"] < 0 for v in seeds.values()) >= 7 and sum(v["ci"][1] < 0 for v in seeds.values()) >= 6,
         "G6": sum(v["delta"] < 0 for v in terc.values()) >= 2}
    res["gates"] = {k: bool(v) for k, v in G.items()}
    res["data_pass"] = bool(res["V1"]["pass"])
    res["verdict"] = ("GO_STAGE_B" if all(G.values()) else ("VOL_ONLY" if all(G[k] for k in ("G1", "G2", "G3", "G4", "G5")) else "NO-GO")) if res["data_pass"] else "DATA-FAIL"
    log.info("GATES %s -> %s", res["gates"], res["verdict"])
    x.to_parquet(OUT + "/p2d_trades_a1_C1.parquet")
    json.dump(res, open(OUT + "/p2d_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
