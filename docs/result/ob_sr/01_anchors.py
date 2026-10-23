#!/usr/bin/env python3
"""OB_SR 01: build cluster/anchor table from X14 printDone (8 DEV seeds).

Unit = (sym, t0 UTC). t0 = min start of cluster (printDone start is +07).
Writes anchors.parquet (per seed) and anchor.parquet (deduped).
"""
import glob
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
KS = "/home/ubuntu/kaggle_sim/out/"
SEEDS = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]
H7 = pd.Timedelta(hours=7)
EP = [  # frozen episode ranges (ALT_EW dd<=-25%, lookback 45, gap<=3d), see prereg
    ("2023-03-09", "2023-03-13"), ("2023-05-09", "2023-06-03"), ("2023-06-10", "2023-06-20"),
    ("2024-04-13", "2024-05-24"), ("2024-06-18", "2024-07-26"), ("2024-08-04", "2024-08-19"),
    ("2024-08-29", "2024-09-08"), ("2024-11-05", "2024-11-05"), ("2024-12-19", "2025-03-24"),
    ("2025-03-29", "2025-04-20"), ("2025-05-31", "2025-06-01"), ("2025-06-06", "2025-07-08"),
    ("2025-10-11", "2025-12-31"),
]


def load(seed):
    d = pd.read_csv(KS + "tsx-x14-%s/storage/printDone.csv" % seed, index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "pnl", "funding", "margin"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["status"] = d["status"].astype(str).str.strip()
    d["level"] = d["level"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - H7
    d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M") - H7
    d["seed"] = seed
    return d


def main():
    rows = []
    for s in SEEDS:
        d = load(s)
        for (sym, te), x in d.groupby(["sym", "te"], sort=False):
            x = x.sort_values("ts", kind="mergesort")
            t0 = x["ts"].min()
            age = int((te - t0) // pd.Timedelta(minutes=1))
            legs = [(int((a - t0) // pd.Timedelta(minutes=1)), float(e), float(q))
                    for a, e, q in zip(x["ts"], x["entry"], x["quantity"])]
            init = x[x["level"] == "PREDICT_SYMBOL_TRADE"]
            e0 = float((init if len(init) else x).sort_values("ts")["entry"].iloc[0])
            notional = float((x["entry"] * x["quantity"]).sum())
            rows.append(dict(
                seed=s, sym=sym, te=te, t0=t0, age_min=age, status=x["status"].iloc[0], n_legs=len(x),
                entry0=e0, pnl=float(x["pnl"].sum()), fund=float(x["funding"].fillna(0).sum()),
                notional=notional, margin=float(x["margin"].sum()), legs=legs,
                t0_ms=int(t0.value // 10 ** 6)))
    A = pd.DataFrame(rows)
    os.makedirs(OUT, exist_ok=True)
    A.to_parquet(OUT + "/anchors.parquet", index=False)
    # anchor-level (dedupe seeds)
    G = A.groupby(["sym", "t0"], as_index=False).agg(
        E=("entry0", "median"), entry_notional=("notional", "median"),
        pnl=("pnl", "median"), margin=("margin", "median"), n_seeds=("seed", "nunique"),
        age_max=("age_min", "max"), t0_ms=("t0_ms", "first"))
    G["year"] = G["t0"].dt.year
    ep = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in EP]
    G["episode"] = [int(any(a <= t < b + pd.Timedelta(days=1) for a, b in ep)) for t in G["t0"]]
    G = G[G["year"].isin([2023, 2024, 2025])].reset_index(drop=True)
    G.to_parquet(OUT + "/anchor.parquet", index=False)
    print("clusters", len(A), "anchors", len(G), "seed-clusters in years", int(A["t0"].dt.year.isin([2023, 2024, 2025]).sum()))
    print(G.groupby(["year", "episode"]).size().to_string())
    print("n_seeds per anchor", G["n_seeds"].value_counts().to_dict())
    print("age>=168h anchors", int((G["age_max"] >= 10081).sum()))


if __name__ == "__main__":
    main()
