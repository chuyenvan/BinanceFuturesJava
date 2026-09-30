#!/usr/bin/env python3
"""SHORT_FEASIBILITY proxy (0-sim, light). Reuses trend_rank_ic loaders (S1 decile).
Chot TRUOC o docs/prereg/PREREG_SHORT_FEASIBILITY.md. Chi DOC, khong sua .java.
Output: research/analysis/out/short_feas_proxy.json
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_rank_ic as T  # noqa

OUT = os.path.join(HERE, "out", "short_feas_proxy.json")
FEE_RT = 2 * 0.000982   # round-trip taker (config SIM_RATE_FEE), %as fraction
SLIP_RT = 2 * 0.000067

def decile_table(df, r, q=10, min_n=10, with_year=False):
    d = df[["ctime", "s1", r]].dropna().copy()
    cnt = d.groupby("ctime").size()
    good = cnt[cnt >= max(q, min_n)].index
    d = d[d["ctime"].isin(good)]
    if len(d) == 0:
        return ({}, {}) if with_year else {}
    d["rrank"] = d.groupby("ctime")["s1"].rank(method="first")
    d["q"] = d.groupby("ctime")["rrank"].transform(lambda x: pd.qcut(x, q, labels=False))
    g = d.groupby(["ctime", "q"])[r].mean().reset_index()
    m = g.groupby("q")[r].mean()
    n = g.groupby("q")[r].size()
    out = {int(k): dict(mean=float(m[k]), n_snap=int(n[k])) for k in m.index}
    if not with_year:
        return out
    g["y"] = pd.to_datetime(g["ctime"], unit="ms").dt.year
    ym = g.groupby(["y", "q"])[r].mean()
    yr = {int(y): {int(qq): float(ym[(y, qq)]) for qq in range(q)} for y in sorted(g["y"].unique())}
    return out, yr


def main():
    print("=== SHORT_FEASIBILITY proxy (S1 decile) ===", flush=True)
    df = T.load_closes()
    df = T.add_forward(df)
    df = T.add_s1(df)
    df = df[df["ctime"] <= T.DECISION_MAX].copy()
    print("rows=%d s1nonnull=%d" % (len(df), df.s1.notna().sum()), flush=True)
    res = {"meta": {"closes": T.CLOSES, "s1": T.S1, "fee_rt": FEE_RT, "slip_rt": SLIP_RT,
                    "conv": "s1=-score; decile 0 = lowest s1 (short candidate); decile 9 = highest s1 (long pick)"},
           "decile": {}, "ic": {}}
    for h in T.HORIZONS:
        r = f"ret{h}"
        dt, yr = decile_table(df, r, with_year=True)
        res["decile"][h] = dt
        res.setdefault("decile_year", {})[h] = yr
        ic = T._ic_series(df, "s1", r)
        res["ic"][h] = dict(mean=float(ic.mean()), n_snap=int(len(ic)))
        print("h=%dh IC=%.5f d0=%.6f d9=%.6f" % (h, ic.mean(), dt[0]["mean"], dt[9]["mean"]), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
