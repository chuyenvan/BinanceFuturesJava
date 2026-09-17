"""Bo sung cho trend_rank_ic.py: so sanh "cung moc" — chi tren snapshot co S1.
Doc lai cung data, tinh rank-IC trend/mom/vol/S1 tren TAP SNAPSHOT CHUNG (co s1 va
feature khong NaN) de doi chung S1 dung nghia. Khong phai tune — chi can chinh mo sanh.
"""
import logging as _logging
import sys as _sys
import numpy as np
import pandas as pd

_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
L = _logging.getLogger("trendic2")


def _p(*a):
    L.info(" ".join(str(x) for x in a))


import trend_rank_ic as T


def rank_ic_common(df, f, r, min_n=10):
    cols = ["ctime", f, r] if f == "s1" else ["ctime", f, "s1", r]
    d = df[cols].dropna().copy()
    if len(d) == 0:
        return float("nan"), 0
    # chi giu snapshot co du ca s1 va feature
    d["rf"] = d.groupby("ctime")[f].rank(method="average")
    d["rr"] = d.groupby("ctime")[r].rank(method="average")
    d["cf"] = d["rf"] - d.groupby("ctime")["rf"].transform("mean")
    d["cr"] = d["rr"] - d.groupby("ctime")["rr"].transform("mean")
    d["cov"] = d["cf"] * d["cr"]
    d["vf"] = d["cf"] ** 2
    d["vr"] = d["cr"] ** 2
    g = d.groupby("ctime").agg(cov=("cov", "sum"), vf=("vf", "sum"),
                               vr=("vr", "sum"), n=("cf", "size"))
    g = g[g["n"] >= min_n]
    ic = g["cov"] / np.sqrt(g["vf"] * g["vr"])
    return float(ic.mean()), int(len(ic))


def main():
    df = T.load_closes()
    df = T.add_features(df)
    df = T.add_forward(df)
    df = T.add_s1(df)
    df = df[df["ctime"] <= T.DECISION_MAX].copy()
    _p("=== rank-IC (cung moc: chi snapshot co S1) ===")
    for h in T.HORIZONS:
        r = f"ret{h}"
        row = {}
        for nm, fc in (("trend", "trend"), ("mom", "mom"), ("vol", "vol"), ("S1", "s1")):
            mean, ns = rank_ic_common(df, fc, r)
            row[nm] = round(mean, 5)
        _p("h=%2dh trend=%+.5f mom=%+.5f vol=%+.5f S1=%+.5f  (n_snap chung=%d)",
           h, row["trend"], row["mom"], row["vol"], row["S1"], ns)


if __name__ == "__main__":
    main()
