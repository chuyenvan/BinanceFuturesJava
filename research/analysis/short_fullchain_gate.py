#!/usr/bin/env python3
"""short_fullchain_gate.py — BUOC 2 (SHORT_FULLCHAIN): ghep gate predRisk4H vao tung ung vien SHORT.

Chot TRUOC: docs/prereg/PREREG_SHORT_FULLCHAIN.md (9ac83699). 0-sim, chi DOC.
Ung vien SHORT = decile 0 cua s1 (= score cao nhat) moi tick (1h grid, dong bo buoc 1).
Gate = predRisk4H (market-level, p15_dev.csv), nguong q10/q20/q80/q90 tren DEV.
2 huong: (a) CHAN (bo khi g<=q10) ; (b) THUAN (chi vao khi g>=q90). (c) NGHICH (g<=q10) doi chung.
Output: research/analysis/out/short_fullchain_gate.json
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_rank_ic as T  # noqa

GATE = "/home/ubuntu/src/BinanceFuturesJava/research/parity/data/p15_dev.csv"
OUT = os.path.join(HERE, "out", "short_fullchain_gate.json")
Q = (0.10, 0.20, 0.80, 0.90)


def spearman_ic(sub, f="s1", r="ret24", min_n=10):
    d = sub[["ctime", f, r]].dropna()
    if len(d) == 0:
        return float("nan"), 0
    d = d.copy()
    d["cf"] = d.groupby("ctime")[f].rank(method="average")
    d["cr"] = d.groupby("ctime")[r].rank(method="average")
    d["cf"] -= d.groupby("ctime")["cf"].transform("mean")
    d["cr"] -= d.groupby("ctime")["cr"].transform("mean")
    g = d.groupby("ctime").apply(lambda x: (x.cf * x.cr).sum() /
                                 np.sqrt((x.cf ** 2).sum() * (x.cr ** 2).sum())
                                 if len(x) >= min_n else np.nan)
    g = g.dropna()
    return (float(g.mean()) if len(g) else float("nan")), int(len(g))


def by_year(sub, r="ret24"):
    if len(sub) == 0:
        return {}
    y = pd.to_datetime(sub["ctime"], unit="ms").dt.year
    g = sub.assign(y=y).groupby("y")[r].mean()
    return {int(k): round(float(v), 6) for k, v in g.items()}


def summarise(sub, name, res):
    n = len(sub)
    ic, ns = spearman_ic(sub)
    res[name] = {"n_pick": int(n), "ret24_mean": round(float(sub["ret24"].mean()), 6) if n else None,
                 "ic_s1_ret24": round(ic, 6), "n_ic_snap": ns, "by_year_ret24": by_year(sub)}
    return res[name]


def main():
    print("=== SHORT_FULLCHAIN BUOC 2: gate ===", flush=True)
    df = T.load_closes()
    df = T.add_forward(df)
    df = T.add_s1(df)
    df = df[df["ctime"] <= T.DECISION_MAX].copy()
    # ung vien SHORT = decile 0 cua s1 moi tick
    d = df[["ctime", "sym", "s1", "ret1", "ret4", "ret24"]].dropna(subset=["s1"]).copy()
    cnt = d.groupby("ctime")["s1"].transform("size")
    d["rk"] = d.groupby("ctime")["s1"].rank(method="first")
    d["q"] = d.groupby("ctime")["rk"].transform(lambda x: pd.qcut(x, 10, labels=False))
    d0 = d[d["q"] == 0].copy()
    print("d0 picks n=%d" % len(d0), flush=True)
    # gate join (minute = ctime//60000, causal)
    g = pd.read_csv(GATE, usecols=["ts", "predRisk4H"])
    g["min"] = g["ts"] // 60000
    gmin = g.groupby("min")["predRisk4H"].first()
    th = {f"q{int(q*100)}": float(gmin.quantile(q)) for q in Q}
    d0["g"] = (d0["ctime"] // 60000).map(gmin)
    d0 = d0.dropna(subset=["g"]).copy()
    res = {"prereg": "PREREG_SHORT_FULLCHAIN", "gate": "predRisk4H", "gate_src": GATE,
           "conv": "risk CAO <=> predRisk4H thap (am hon); risk THAP <=> cao",
           "thresholds": {k: round(v, 6) for k, v in th.items()},
           "n_d0": int(len(d0)), "variants": {}}
    summarise(d0, "A_all", res["variants"])
    q10, q90 = th["q10"], th["q90"]
    summarise(d0[d0["g"] > q10], "B_gate_CHAN_drop_le_q10", res["variants"])
    summarise(d0[d0["g"] >= q90], "C_gate_THUAN_keep_ge_q90", res["variants"])
    summarise(d0[d0["g"] <= q10], "D_gate_NGHICH_keep_le_q10", res["variants"])
    summarise(d0[d0["g"] > th["q20"]], "B2_CHAN_drop_le_q20", res["variants"])
    summarise(d0[d0["g"] >= th["q80"]], "C2_THUAN_keep_ge_q80", res["variants"])
    # ty le bi chan / giu
    for k in res["variants"]:
        res["variants"][k]["frac_of_all"] = round(res["variants"][k]["n_pick"] / len(d0), 4)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "by_year_ret24"}
                      for k, v in res["variants"].items()}, indent=1), flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
