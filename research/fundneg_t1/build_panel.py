#!/usr/bin/env python3
"""FUNDNEG_T1 step 1: kline 1m -> hourly panel + daily panel, per month (memory-bounded).
Prereg: docs/prereg/PREREG_FUNDNEG_T1.md (commit 66862db3).
Hourly (sym, hr=ts//3600000): c01 = close of 1m candle open-ts hr*3600000+60000 (entry/exit price),
c59 = close of candle open-ts hr*3600000+3540000 (= price at next settlement hr+1),
hi_a/lo_a = high/low of candles minute 2..59, hi_b/lo_b = minute 0..1, last_close/last_ts, nbar.
Daily (sym, day=ts//86400000): qv = sum quote_volume, dclose = close of last candle of day, nbar.
"""
import os, sys, json
import numpy as np, pandas as pd, pyarrow.parquet as pq

KL = "/home/ubuntu/vz_e1/raw"
OUT = "/home/ubuntu/claude_master/fundneg_t1_wk/panel"
os.makedirs(OUT, exist_ok=True)


def months():
    y, m = 2021, 12
    while (y, m) <= (2025, 12):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def month_bounds(y, m):
    a = int(pd.Timestamp(year=y, month=m, day=1, tz="UTC").value // 10**6)
    b = int((pd.Timestamp(year=y, month=m, day=1, tz="UTC") + pd.offsets.MonthBegin(1)).value // 10**6)
    return a, b


def build(y, m):
    f = os.path.join(KL, "kline1m-%04d-%02d.parquet" % (y, m))
    t = pq.read_table(f, columns=["ts", "sym", "high", "low", "close", "quote_volume"])
    assert str(t.schema.field("ts").type) == "int64"
    df = t.to_pandas()
    del t
    df["sym"] = df["sym"].astype(str).astype("category")
    a, b = month_bounds(y, m)
    assert df.ts.dtype == np.int64
    assert (df.ts >= a).all() and (df.ts < b).all(), "ts outside month"
    assert (df.ts % 60000 == 0).all()
    df.sort_values(["sym", "ts"], inplace=True, kind="mergesort")
    df.reset_index(drop=True, inplace=True)
    dup = int(df.duplicated(["sym", "ts"]).sum())
    assert dup == 0, "dup (sym,ts) %d" % dup
    df["hr"] = df.ts // 3600000
    mi = ((df.ts % 3600000) // 60000).astype(np.int16)
    df["hi_a"] = df.high.where(mi >= 2)
    df["lo_a"] = df.low.where(mi >= 2)
    df["hi_b"] = df.high.where(mi <= 1)
    df["lo_b"] = df.low.where(mi <= 1)
    df["c01"] = df.close.where(mi == 1)
    df["c59"] = df.close.where(mi == 59)
    g = df.groupby(["sym", "hr"], observed=True, sort=True)
    H = g.agg(c01=("c01", "max"), c59=("c59", "max"), hi_a=("hi_a", "max"), lo_a=("lo_a", "min"),
              hi_b=("hi_b", "max"), lo_b=("lo_b", "min"), last_close=("close", "last"),
              last_ts=("ts", "max"), nbar=("ts", "size")).reset_index()
    # c01/c59: one candle per (sym,hr,minute) since no dup -> max == the value
    assert H.nbar.max() <= 60
    assert not H.duplicated(["sym", "hr"]).any()
    df["day"] = df.ts // 86400000
    gd = df.groupby(["sym", "day"], observed=True, sort=True)
    D = gd.agg(qv=("quote_volume", "sum"), dclose=("close", "last"), nbar=("ts", "size")).reset_index()
    assert not D.duplicated(["sym", "day"]).any() and D.nbar.max() <= 1440
    nrow = len(df)
    del df, g, gd
    H["sym"] = H.sym.astype(str)
    D["sym"] = D.sym.astype(str)
    H.to_parquet(os.path.join(OUT, "h-%04d-%02d.parquet" % (y, m)), index=False)
    D.to_parquet(os.path.join(OUT, "d-%04d-%02d.parquet" % (y, m)), index=False)
    return {"rows1m": nrow, "hrows": len(H), "drows": len(D), "nsym": int(H.sym.nunique()),
            "h_nbar_lt60": int((H.nbar < 60).sum()), "h_c01_nan": int(H.c01.isna().sum())}


if __name__ == "__main__":
    log = {}
    for y, m in months():
        k = "%04d-%02d" % (y, m)
        if os.path.exists(os.path.join(OUT, "d-%s.parquet" % k)):
            continue
        log[k] = build(y, m)
        print(k, log[k], flush=True)
    with open(os.path.join(OUT, "build_log_%d.json" % os.getpid()), "w") as fh:
        json.dump(log, fh, indent=1)
    print("DONE")
