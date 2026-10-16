"""SQ ho #3 (PREREG_SQ.md): long sau funding am sau 2 ky lien tiep, giu 24h/72h. KHONG doc 2026."""
import glob
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/fw"))
import fw as FW  # noqa: E402

log = logging.getLogger("sq")
OUT = os.path.expanduser("~/claude_master/sq"); os.makedirs(OUT, exist_ok=True)
THR, COOL = -0.001, 72 * 3_600_000
HS = {"H24": 1440, "H72": 4320}


def build():
    F = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(FW.FUND + "/funding-202[1-5].parquet"))])
    F["T"] = F.ts // FW.MIN * FW.MIN
    F = F.drop_duplicates(["sym", "T"]).sort_values(["sym", "T"]).reset_index(drop=True)
    F["r8"] = F.rate * 8.0 / F.interval_h
    F["r8_prev"] = F.groupby("sym").r8.shift(1)
    F["day"] = pd.to_datetime(F["T"], unit="ms").dt.floor("D")
    D = pd.read_parquet(FW.D1, columns=["sym", "day", "qv", "close"])
    piv = D.pivot(index="day", columns="sym", values="qv").sort_index()
    q = piv.rolling(30, min_periods=20).median().stack().rename("qv30").reset_index()
    first = D.groupby("sym").day.min().rename("first")
    trig = F[(F.r8 <= THR) & (F.r8_prev <= THR) & (F.day >= "2022-01-01") & (F.day <= "2025-12-31")]
    trig = trig.merge(q, on=["day", "sym"], how="left").merge(first, on="sym", how="left")
    trig = trig[(trig.qv30 >= 20e6) & ((trig.day - trig["first"]).dt.days >= 60) & ~trig.sym.str[:-4].isin(FW_STABLE)]
    ev, last = [], {}
    for r in trig.sort_values("T").itertuples():
        if r.sym in last and r.T <= last[r.sym] + COOL:
            continue
        last[r.sym] = r.T; ev.append(r)
    E = pd.DataFrame(ev)[["sym", "T", "r8", "r8_prev", "rate", "day"]]
    log.info("trigger %d -> su kien sau cooldown %d, sym %d", len(trig), len(E), E.sym.nunique())
    return E, F


FW_STABLE = ("USDC", "FDUSD", "TUSD", "BUSD", "DAI", "EUR", "PAXG", "WBTC", "USDP", "UST", "AEUR", "XUSD", "USD1", "BFUSD")


def funding_recv(E, F, mins):
    g = {s: d[["T", "rate"]].values for s, d in F.groupby("sym")}
    out = []
    for r in E.itertuples():
        a = g[r.sym]; m = (a[:, 0] > r.T) & (a[:, 0] <= r.T + mins * FW.MIN)
        out.append(float(-a[m, 1].sum()))
    return np.array(out)


def tstat_day(x, day):
    g = pd.Series(x.values, index=day.values).groupby(level=0).mean()
    return float(g.mean() / (g.std() / np.sqrt(len(g)))) if len(g) > 10 and g.std() > 0 else 0.0


def main():
    E, F = build()
    FW.OFF = [1, 1440, 4320]
    P = FW.prices(E.copy())
    B = FW.prices(pd.DataFrame({"T": E["T"].unique(), "sym": "BTCUSDT"}))
    P = P.merge(B[["T", "p1", "p1440", "p4320"]].rename(columns={"p1": "b1", "p1440": "b1440", "p4320": "b4320"}), on="T", how="left")
    cov = float(P[["p1", "p1440"]].notna().all(axis=1).mean())
    P["year"] = P.day.dt.year; P["per"] = np.where(P.year <= 2024, "DEV", "VAL")
    res = {"n_events": int(len(P)), "V2_cov": cov}
    for name, mins in HS.items():
        fr = funding_recv(P, F, mins)
        ret = P[f"p{mins}"] / P.p1 - 1
        P[f"net_{name}"] = ret - FW.COST + fr
        P[f"exc_{name}"] = P[f"net_{name}"] - (P[f"b{mins}"] / P.b1 - 1)
        P[f"fund_{name}"] = fr
        o = {}
        for per in ("DEV", "VAL"):
            x = P[(P.per == per)].dropna(subset=[f"net_{name}"])
            n = x[f"net_{name}"]
            q99 = n.quantile(0.99)
            o[per] = {"n": int(len(x)), "mean": float(n.mean()), "median": float(n.median()), "hit": float((n > 0).mean()), "t": tstat_day(n, x.day),
                      "exc": float(x[f"exc_{name}"].mean()), "t_exc": tstat_day(x[f"exc_{name}"].fillna(0), x.day), "fund": float(x[f"fund_{name}"].mean()),
                      "p5": float(n.quantile(0.05)), "mean_trim1": float(n[n <= q99].mean()),
                      "by_year": {int(y): round(float(g.mean()), 4) for y, g in x.groupby("year")[f"net_{name}"]}}
            log.info("%s %s n %d mean %+.3f%% med %+.3f%% hit %.3f t %+.2f | exc %+.3f%% t %+.2f | funding %+.3f%% | p5 %+.2f%% | trim1 %+.3f%% | nam %s",
                     name, per, o[per]["n"], 100 * o[per]["mean"], 100 * o[per]["median"], o[per]["hit"], o[per]["t"], 100 * o[per]["exc"], o[per]["t_exc"],
                     100 * o[per]["fund"], 100 * o[per]["p5"], 100 * o[per]["mean_trim1"], o[per]["by_year"])
        dv, vl = o["DEV"], o["VAL"]
        o["gates"] = {"G1": dv["mean"] > 0 and dv["t"] >= 3, "G2": all(dv["by_year"].get(y, -1) > 0 for y in (2022, 2023, 2024)),
                      "G3": vl["mean"] > 0 and vl["t"] >= 2, "G4": dv["exc"] > 0, "G5": dv["mean_trim1"] > 0}
        o["verdict"] = "GO" if all(o["gates"].values()) else "NO-GO"
        log.info("%s gates %s -> %s", name, o["gates"], o["verdict"])
        res[name] = o
    # V1: kiem tay 10 su kien
    rng = np.random.default_rng(1017); chk = []
    for r in P.dropna(subset=["p1440"]).sample(10, random_state=1017).itertuples():
        f = F[(F.sym == r.sym) & (F["T"] <= r.T)].tail(2)
        trig_ok = bool((f.r8 <= THR).all() and len(f) == 2 and int(f["T"].iloc[-1]) == r.T)
        m = pd.Timestamp(r.T, unit="ms").to_period("M")
        k = pd.read_parquet(f"{FW.K1M}/kline1m-{m}.parquet", columns=["ts", "sym", "close"], filters=[("sym", "==", r.sym)]).set_index("ts").close
        m2 = pd.Timestamp(r.T + 1440 * FW.MIN, unit="ms").to_period("M")
        k2 = k if m2 == m else pd.read_parquet(f"{FW.K1M}/kline1m-{m2}.parquet", columns=["ts", "sym", "close"], filters=[("sym", "==", r.sym)]).set_index("ts").close
        e1 = abs(float(k.get(r.T, np.nan)) - r.p1); e2 = abs(float(k2.get(r.T + 1439 * FW.MIN, np.nan)) - r.p1440)
        chk.append((trig_ok, e1, e2))
    res["V1"] = {"n": len(chk), "trigger_ok": int(sum(c[0] for c in chk)), "max_px_err": float(max(max(c[1], c[2]) for c in chk))}
    res["data_pass"] = bool(res["V1"]["trigger_ok"] == 10 and res["V1"]["max_px_err"] <= 1e-12 and cov >= 0.97)
    log.info("V1 %s | V2 cov %.4f | data_pass %s", res["V1"], cov, res["data_pass"])
    P.to_parquet(OUT + "/sq_events.parquet")
    json.dump(res, open(OUT + "/sq_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
