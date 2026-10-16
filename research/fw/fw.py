"""FW tang 1 (PREREG_FW.md): event study quanh moc thanh toan funding tren 1m. KHONG doc 2026."""
import glob
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("fw")
FUND = os.path.expanduser("~/claude_master/1016/carry/fund")
K1M = os.path.expanduser("~/vz_e1/raw")
D1 = os.path.expanduser("~/claude_master/1016/screen/d1.parquet")
OUT = os.path.expanduser("~/claude_master/fw"); os.makedirs(OUT, exist_ok=True)
MIN = 60_000
OFF = [-180, -125, -120, -115, -60, -5, 0, 1, 5, 60, 240]
COST = 0.0014
THR = 0.0005
E0, E1, V0, V1 = "2022-01-01", "2024-12-31", "2025-01-01", "2025-12-31"


def events():
    F = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(FUND + "/funding-202[1-5].parquet"))])
    v1 = float(((F.ts % 3_600_000) < 60_000).mean())
    F["T"] = F.ts // MIN * MIN
    F = F.drop_duplicates(["sym", "T"]).sort_values(["sym", "T"])
    F["r8"] = F.rate * 8.0 / F.interval_h
    F["s"] = F.groupby("sym").r8.shift(1)
    F["day"] = pd.to_datetime(F["T"], unit="ms").dt.floor("D")
    F = F[(F.day >= "2022-01-01") & (F.day <= "2025-12-31")]
    D = pd.read_parquet(D1, columns=["sym", "day", "qv"])
    q = D.pivot(index="day", columns="sym", values="qv").sort_index().rolling(30, min_periods=20).median()
    q = q.stack().rename("qv30").reset_index()
    F = F.merge(q, on=["day", "sym"], how="left")
    F = F[(F.qv30 >= 20e6) & F.s.notna()].reset_index(drop=True)
    log.info("su kien universe: %d, sym %d, V1 ts dung gio: %.4f", len(F), F.sym.nunique(), v1)
    return F, v1


def prices(F):
    F["mon"] = pd.to_datetime(F["T"], unit="ms").dt.to_period("M")
    out = []
    for m, ev in F.groupby("mon"):
        a = int(m.start_time.value // 1_000_000) - 4 * 3_600_000
        b = int((m.end_time + pd.Timedelta(seconds=1)).value // 1_000_000) + 5 * 3_600_000
        syms = list(ev.sym.unique())
        files = [f"{K1M}/kline1m-{p}.parquet" for p in (m - 1, m, m + 1) if os.path.exists(f"{K1M}/kline1m-{p}.parquet")]
        dset = ds.dataset(files, format="parquet")
        k = dset.to_table(columns=["ts", "sym", "close"], filter=(ds.field("ts") >= a) & (ds.field("ts") < b) & ds.field("sym").isin(syms)).to_pandas()
        K = k.drop_duplicates(["sym", "ts"]).set_index(["sym", "ts"]).close
        ev = ev.copy()
        for o in OFF:
            key = ev["T"].values + o * MIN - MIN          # nen co open_time = t-1m -> close la gia tai t
            ev[f"p{o}"] = K.reindex(pd.MultiIndex.from_arrays([ev.sym.values, key])).values
        out.append(ev)
        log.info("gia %s: %d su kien, %d nen", m, len(ev), len(k))
    return pd.concat(out, ignore_index=True)


def lr(E, a, b):
    return np.log(E[f"p{b}"] / E[f"p{a}"])


def cl_t(df, col):
    g = df.groupby("T")[col].mean()
    return float(g.mean() / (g.std() / np.sqrt(len(g)))) if len(g) > 10 and g.std() > 0 else 0.0


def evaluate(E):
    res = {}
    E["pre"] = lr(E, -60, 0); E["post1"] = lr(E, 0, 60); E["post4"] = lr(E, 0, 240)
    E["c_pre"] = lr(E, -180, -120); E["c_post1"] = lr(E, -120, -60)
    E["px10"] = lr(E, -5, 5); E["c_px10"] = lr(E, -125, -115)
    E["year"] = pd.to_datetime(E["T"], unit="ms").dt.year
    E["per"] = np.where(E.year <= 2024, "DEV", "VAL")
    pos = E[E.s >= THR]; neg = E[E.s <= -THR]
    rules = {
        "L_post": (pos, (pos.p60 / pos.p0 - 1), pos.post1 - pos.c_post1),
        "L_pre": (neg, (neg.p1 / neg["p-60"] - 1) - neg.rate, neg.pre - neg.c_pre),
        "L_cap": (neg, (neg.p5 / neg["p-5"] - 1) - neg.rate, neg.px10 - neg.c_px10 - neg.rate),
    }
    for name, (sub, gross, did) in rules.items():
        d = sub.assign(net=gross - COST, net2=gross - 2 * COST, did=did).dropna(subset=["net", "did"])
        o = {}
        for per in ("DEV", "VAL"):
            x = d[d.per == per]
            o[per] = {"n": int(len(x)), "n_T": int(x["T"].nunique()), "mean_net": float(x.net.mean()), "t_net": cl_t(x, "net"),
                      "mean_gross": float((x.net + COST).mean()), "hit": float((x.net > 0).mean()), "mean_net2": float(x.net2.mean()),
                      "did": float(x.did.mean()), "t_did": cl_t(x, "did"),
                      "by_year": {int(y): round(float(g.net.mean()), 5) for y, g in x.groupby("year")}}
        dv, vl = o["DEV"], o["VAL"]
        o["gates"] = {"G1": dv["mean_net"] > 0 and dv["t_net"] >= 3, "G2": all(dv["by_year"].get(y, -1) > 0 for y in (2022, 2023, 2024)),
                      "G3": vl["mean_net"] > 0 and vl["t_net"] >= 2, "G4": dv["did"] > 0 and dv["t_did"] >= 2, "G5": dv["mean_net2"] > 0}
        o["verdict"] = "GO" if all(o["gates"].values()) else "NO-GO"
        res[name] = o
        for per in ("DEV", "VAL"):
            x = o[per]
            log.info("%s %s n %d (T %d) gross %+.4f%% net %+.4f%% t %+.2f hit %.3f | DiD %+.4f%% t %+.2f | x2 %+.4f%% | nam %s", name, per, x["n"], x["n_T"],
                     100 * x["mean_gross"], 100 * x["mean_net"], x["t_net"], x["hit"], 100 * x["did"], x["t_did"], 100 * x["mean_net2"], x["by_year"])
        log.info("%s gates %s -> %s", name, o["gates"], o["verdict"])
    # mo ta theo quintile s (DEV)
    dv = E[E.per == "DEV"].dropna(subset=["pre", "post1", "post4", "c_pre", "c_post1"]).copy()
    dv["q"] = pd.qcut(dv.s.rank(method="first"), 5, labels=False)
    tab = dv.groupby("q").agg(s_mean=("s", "mean"), pre=("pre", "mean"), post1=("post1", "mean"), post4=("post4", "mean"),
                              did_pre=("c_pre", lambda c: 0.0), n=("s", "size"))
    tab["did_pre"] = dv.groupby("q").apply(lambda g: (g.pre - g.c_pre).mean())
    tab["did_post1"] = dv.groupby("q").apply(lambda g: (g.post1 - g.c_post1).mean())
    log.info("QUINTILE s (DEV, log-ret):\n%s", tab.to_string())
    res["quintile_dev"] = tab.reset_index().to_dict(orient="list")
    return res


def manual_check(E, n=10):
    rng = np.random.default_rng(1017)
    sm = E.dropna(subset=["p-60", "p0", "p60"]).iloc[rng.choice(len(E.dropna(subset=["p-60", "p0", "p60"])), n, replace=False)]
    errs = []
    for _, r in sm.iterrows():
        m = pd.Timestamp(r["T"], unit="ms").to_period("M")
        k = pd.read_parquet(f"{K1M}/kline1m-{m}.parquet", columns=["ts", "sym", "close"], filters=[("sym", "==", r.sym)])
        k = k.set_index("ts").close
        def px(t):
            return float(k.get(t - MIN, np.nan))
        p0 = px(r["T"]); pm = px(r["T"] - 60 * MIN); pp = px(r["T"] + 60 * MIN)
        if np.isnan(pm) or np.isnan(pp):
            continue
        errs.append(max(abs(np.log(p0 / pm) - r.pre), abs(np.log(pp / p0) - r.post1)))
    return {"n": len(errs), "max_err": float(max(errs)) if errs else None, "pass": bool(errs) and max(errs) <= 1e-12}


def main():
    F, v1 = events()
    E = prices(F)
    need = ["p-60", "p0", "p60", "p-120", "p-180"]
    cov = float(E[need].notna().all(axis=1).mean())
    res = {"V1_ts_on_hour": v1, "V2_coverage": cov}
    res.update(evaluate(E))
    res["V3"] = manual_check(E)
    res["data_pass"] = bool(v1 >= 0.99 and cov >= 0.98 and res["V3"]["pass"])
    log.info("V1 %.4f | V2 %.4f | V3 %s | data_pass %s", v1, cov, res["V3"], res["data_pass"])
    E[["sym", "T", "s", "rate", "pre", "post1", "post4", "c_pre", "c_post1", "px10", "c_px10", "year"]].to_parquet(OUT + "/fw_events.parquet")
    json.dump(res, open(OUT + "/fw_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
