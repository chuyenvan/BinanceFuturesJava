#!/usr/bin/env python3
"""OB_SR 10: V2 - mid vs 1m close at the snapshot minute (all decision snapshots)."""
import os

import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
KRAW = "/home/ubuntu/vz_e1/raw"


def kfile(ym):
    return KRAW + "/kline1m-%s.parquet" % ym


def main():
    F = pd.read_parquet(OUT + "/features.parquet")
    F = F[(F["ok"] == 1) & F["snap_ts"].notna()].copy()
    F["snap_ts"] = F["snap_ts"].astype("int64")
    F["minute"] = (F["snap_ts"] // 60000) * 60000
    F["ym"] = pd.to_datetime(F["minute"], unit="ms").dt.strftime("%Y-%m")
    rows = []
    for ym, g in F.groupby("ym"):
        fn = kfile(ym)
        if not os.path.exists(fn):
            continue
        syms = set(g["sym"] + "USDT")
        k = pd.read_parquet(fn, columns=["ts", "sym", "close"])
        k = k[k["sym"].isin(syms)]
        k["sym"] = k["sym"].str.replace("USDT", "", regex=False)
        z = g.merge(k, left_on=["minute", "sym"], right_on=["ts", "sym"], how="left")
        rows.append(z[["point", "year", "sym", "mid", "close"]])
    Z = pd.concat(rows)
    Z["r"] = np.abs(np.log(Z["mid"] / Z["close"])).replace([np.inf, -np.inf], np.nan)
    Z = Z.dropna(subset=["r"])
    out = Z.groupby(["point", "year"])["r"].agg(["size", "median", lambda x: x.quantile(.99)])
    out.columns = ["n", "median", "p99"]
    out.to_csv(OUT + "/v2.csv")
    print(out.to_string())
    print("overall median %.5f p99 %.5f" % (Z["r"].median(), Z["r"].quantile(.99)))


if __name__ == "__main__":
    main()
