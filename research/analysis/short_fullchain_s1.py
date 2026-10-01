#!/usr/bin/env python3
"""short_fullchain_s1.py — BUOC 1 (SHORT_FULLCHAIN): chat luong xep hang cua SELECTOR S1.

Chot TRUOC: docs/prereg/PREREG_SHORT_FULLCHAIN.md (9ac83699). 0-sim, chi DOC.
s1 = -score (score thap = tot/cho long). Ung vien SHORT = decile 0 cua s1 (= score CAO nhat).
Do: rank-IC(s1, ret_h) h in {1,4,24}h (tong + theo nam + CI block-72h), bang decile, d0 theo nam,
va moc K=8. Output: research/analysis/out/short_fullchain_s1.json
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_rank_ic as T  # noqa

OUT = os.path.join(HERE, "out", "short_fullchain_s1.json")
K_SEL = 8


def ic_by_year(ic):
    y = pd.to_datetime(ic.index, unit="ms").year
    d = ic.groupby(y).mean()
    return {int(k): round(float(v), 6) for k, v in d.items()}


def decile_table(df, r, q=10, min_n=10):
    d = df[["ctime", "s1", r]].dropna().copy()
    cnt = d.groupby("ctime").size()
    good = cnt[cnt >= max(q, min_n)].index
    d = d[d["ctime"].isin(good)]
    if len(d) == 0:
        return {}
    d["rrank"] = d.groupby("ctime")["s1"].rank(method="first")
    d["q"] = d.groupby("ctime")["rrank"].transform(lambda x: pd.qcut(x, q, labels=False))
    g = d.groupby(["ctime", "q"])[r].mean().reset_index()
    m = g.groupby("q")[r].mean()
    out = {int(k): round(float(m[k]), 6) for k in m.index}
    g["y"] = pd.to_datetime(g["ctime"], unit="ms").dt.year
    out["_by_year_d0"] = {int(y): round(float(g[(g.y == y) & (g.q == 0)][r].mean()), 6)
                          for y in sorted(g["y"].unique())}
    return out


def k8_table(df, r):
    """Moc K=8: moi tick lay 8 score CAO nhat (= s1 thap nhat)."""
    d = df[["ctime", "s1", r]].dropna().copy()
    cnt = d.groupby("ctime").size()
    good = cnt[cnt >= K_SEL].index
    d = d[d["ctime"].isin(good)]
    d["rk"] = d.groupby("ctime")["s1"].rank(method="first")           # nho = s1 thap
    sel = d[d["rk"] <= K_SEL]
    g = sel.groupby("ctime")[r].mean()
    y = pd.to_datetime(g.index, unit="ms").year
    return {"mean": round(float(g.mean()), 6), "n_pick": int(len(sel)),
            "by_year": {int(k): round(float(v), 6) for k, v in g.groupby(y).mean().items()}}


def main():
    print("=== SHORT_FULLCHAIN BUOC 1: S1 selector ===", flush=True)
    df = T.load_closes()
    df = T.add_forward(df)
    df = T.add_s1(df)
    df = df[df["ctime"] <= T.DECISION_MAX].copy()
    print("rows=%d s1nonnull=%d ctime<=%s" % (len(df), df.s1.notna().sum(),
          pd.Timestamp(T.DECISION_MAX, unit="ms")), flush=True)
    res = {"prereg": "PREREG_SHORT_FULLCHAIN", "s1_panel": T.S1, "closes": T.CLOSES,
           "conv": "s1=-score; decile 0 = s1 thap nhat (= score CAO nhat) = ung vien SHORT",
           "ic": {}, "decile": {}, "k8": {}}
    for h in T.HORIZONS:
        r = f"ret{h}"
        ic = T._ic_series(df, "s1", r)
        ci = T.block_ci(ic)
        res["ic"][h] = {"mean": round(float(ic.mean()), 6), "n_snap": int(len(ic)),
                        "ci_raw": [round(ci["lo"], 6), round(ci["hi"], 6)],
                        "contains_zero": ci["contains_zero"],
                        "by_year": ic_by_year(ic)}
        res["decile"][h] = decile_table(df, r)
        res["k8"][h] = k8_table(df, r)
        print("h=%dh IC(s1,ret)=%.5f CI[%.5f,%.5f] cz=%s | d0=%.5f d9=%.5f | K8=%.5f" % (
            h, ic.mean(), ci["lo"], ci["hi"], ci["contains_zero"],
            res["decile"][h].get(0, float("nan")), res["decile"][h].get(9, float("nan")),
            res["k8"][h]["mean"]), flush=True)
    # tong ket dieu kien "selector OK" (khoa §2)
    cost = 2 * 0.000982 + 2 * 0.000067
    d0 = res["decile"][24].get(0)
    byy = res["decile"][24].get("_by_year_d0", {})
    neg_years = sum(1 for y in ("2022", "2023", "2024", "2025") if byy.get(int(y), 0) < 0)
    res["selector_ok"] = {
        "cost_thr_pct": round(cost * 100, 4),
        "d0_ret24_pct": round(d0 * 100, 4) if d0 is not None else None,
        "neg_years_of_4": neg_years,
        "cond_neg": bool(d0 is not None and d0 < 0),
        "cond_persist": bool(neg_years >= 3),
        "cond_beats_cost": bool(d0 is not None and abs(d0) > cost),
        "OK": bool(d0 is not None and d0 < 0 and neg_years >= 3 and abs(d0) > cost),
    }
    print("selector_ok:", res["selector_ok"], flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
