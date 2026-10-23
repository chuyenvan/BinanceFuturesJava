#!/usr/bin/env python3
"""OB_SR 07: episode-split IC, 2024 deciles, seed-cluster robustness."""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT = os.path.dirname(os.path.abspath(__file__))
FEAT = ["A%d" % k for k in (1, 2, 3, 5)] + ["B%d" % k for k in (1, 2, 3, 5)] + \
       ["R%d" % k for k in (1, 2, 3, 5)] + ["wA%d" % k for k in (1, 2, 3, 5)] + ["wB%d" % k for k in (1, 2, 3, 5)]
OUTS = {"entry": ["arm168", "mfe24_bps", "mfe72_bps"],
        "arm": ["gb_med", "pt_med"],
        "h168": ["extra24_bps", "extra72_bps"]}


def sp(x, y):
    if len(x) < 30 or len(np.unique(x)) < 2:
        return np.nan
    r = spearmanr(x, y).correlation
    return float(r) if np.isfinite(r) else np.nan


def main():
    F = pd.read_parquet(OUT + "/features.parquet")
    R = pd.read_parquet(OUT + "/price_out.parquet")
    G = pd.read_parquet(OUT + "/anchor.parquet")
    A = pd.read_parquet(OUT + "/anchors.parquet")
    for d in (F, R, G, A):
        d["t0"] = pd.to_datetime(d["t0"])
    F = F.merge(R[["sym", "t0", "arm_j", "mfe24_bps", "mfe72_bps", "gb_med", "pt_med",
                    "extra24_bps", "extra72_bps"]], on=["sym", "t0"], how="left")
    F = F.merge(G[["sym", "t0", "E", "entry_notional", "pnl"]], on=["sym", "t0"], how="left")
    F["arm168"] = (F["arm_j"] > 0).astype(float)
    F["day"] = F["t0"].dt.floor("D")
    F.loc[F["ok"] != 1, FEAT] = np.nan

    # episode split
    er = []
    for p, outs in OUTS.items():
        D = F[F["point"] == p]
        for y in (2023, 2025, 2024):
            for e in (0, 1):
                Dy = D[(D["year"] == y) & (D["episode"] == e)]
                for f in FEAT:
                    for o in outs:
                        z = Dy[[f, o]].dropna()
                        if len(z) < 100:
                            continue
                        er.append(dict(point=p, year=y, episode=e, feat=f, out=o, n=len(z),
                                       ic=sp(z[f].to_numpy(float), z[o].to_numpy(float))))
    E = pd.DataFrame(er)
    E.to_csv(OUT + "/ic_episode.csv", index=False)

    # 2024 deciles for combos with |IC2024| >= 0.08
    ic = pd.read_csv(OUT + "/ic.csv")
    ic24 = ic[ic["year"] == 2024]
    dr, keep = [], ic24[ic24["ic"].abs() >= 0.08]
    for r in keep.itertuples():
        z = F[(F["point"] == r.point) & (F["year"] == 2024)][[r.feat, r.out, "pnl", "entry_notional"]].dropna()
        if len(z) < 100:
            continue
        if z[r.feat].nunique() <= 10:
            dm = z.groupby(z[r.feat])[r.out].mean()
        else:
            try:
                dec = pd.qcut(z[r.feat], 10, labels=False, duplicates="drop")
            except ValueError:
                continue
            dm = z.groupby(dec)[r.out].mean()
        dr.append(dict(point=r.point, feat=r.feat, out=r.out, ic=r.ic, n=len(z),
                       dec=list(map(float, dm.values)), ngrp=list(map(int, z.groupby(z[r.feat]).size().values)),
                       spread=float(dm.iloc[-1] - dm.iloc[0]),
                       med_notional=float(z["entry_notional"].median())))
    json.dump(dr, open(OUT + "/deciles_2024.json", "w"), indent=1)

    # seed-cluster (no dedupe) robustness for the same combos
    A2 = A.merge(F[["sym", "t0", "point", "year", "ok"] + FEAT], on=["sym", "t0"], how="left")
    A2 = A2.merge(R[["sym", "t0", "arm_j", "mfe24_bps", "mfe72_bps", "gb_med", "pt_med",
                     "extra24_bps", "extra72_bps"]], on=["sym", "t0"], how="left")
    A2["arm168"] = (A2["arm_j"] > 0).astype(float)
    sr = []
    for r in keep.itertuples():
        for y in (2023, 2025, 2024):
            z = A2[(A2["point"] == r.point) & (A2["t0"].dt.year == y) & (A2["ok"] == 1)][[r.feat, r.out]].dropna()
            sr.append(dict(point=r.point, feat=r.feat, out=r.out, year=y, n=len(z),
                           ic=sp(z[r.feat].to_numpy(float), z[r.out].to_numpy(float))))
    S = pd.DataFrame(sr)
    S.to_csv(OUT + "/seed_robust.csv", index=False)
    print("episode rows", len(E), "decile combos", len(dr), "seed rows", len(S))
    top = E[E["year"] == 2024].sort_values("ic", key=abs, ascending=False).head(12)
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
