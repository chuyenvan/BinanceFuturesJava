#!/usr/bin/env python3
"""OB_SR 08: descriptive bootstrap CI for the strongest 2024 combos + missing-reason table."""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT = os.path.dirname(os.path.abspath(__file__))
NREP = 2000
SEED = 20261023


def sp(x, y):
    if len(x) < 30:
        return np.nan
    r = spearmanr(x, y).correlation
    return float(r) if np.isfinite(r) else np.nan


def boot(x, y, days, rng):
    ud = np.unique(days)
    idx = {d: np.flatnonzero(days == d) for d in ud}
    out = []
    for _ in range(NREP):
        pick = rng.choice(ud, len(ud), replace=True)
        ii = np.concatenate([idx[d] for d in pick])
        r = spearmanr(x[ii], y[ii]).correlation
        if np.isfinite(r):
            out.append(r)
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))] if out else [np.nan, np.nan]


def main():
    F = pd.read_parquet(OUT + "/features.parquet")
    R = pd.read_parquet(OUT + "/price_out.parquet")
    F["t0"] = pd.to_datetime(F["t0"]); R["t0"] = pd.to_datetime(R["t0"])
    F = F.merge(R[["sym", "t0", "arm_j", "mfe24_bps", "mfe72_bps", "gb_med", "pt_med",
                    "extra24_bps", "extra72_bps"]], on=["sym", "t0"], how="left")
    F["arm168"] = (F["arm_j"] > 0).astype(float)
    F["day"] = F["t0"].dt.floor("D")
    ic = pd.read_csv(OUT + "/ic.csv")
    rng = np.random.default_rng(SEED)
    rows = []
    OUTS = {"entry": ["arm168", "mfe24_bps", "mfe72_bps"], "arm": ["gb_med", "pt_med"],
            "h168": ["extra24_bps", "extra72_bps"]}
    for p, outs in OUTS.items():
        z24 = ic[(ic.point == p) & (ic.year == 2024)].copy()
        top = z24.reindex(z24["ic"].abs().sort_values(ascending=False).index).head(6)
        for r in top.itertuples():
            D = F[F["point"] == p]
            z = D[D["year"] == 2024][[r.feat, r.out, "day"]].dropna()
            ci = boot(z[r.feat].to_numpy(float), z[r.out].to_numpy(float), z["day"].to_numpy(), rng)
            zp = D[D["year"].isin([2023, 2025])][[r.feat, r.out, "day"]].dropna()
            cip = boot(zp[r.feat].to_numpy(float), zp[r.out].to_numpy(float), zp["day"].to_numpy(), rng)
            rows.append(dict(point=p, feat=r.feat, out=r.out, ic2024=r.ic, ci_lo=ci[0], ci_hi=ci[1],
                             n2024=len(z), days2024=int(z["day"].nunique()),
                             ic_pool=sp(zp[r.feat].to_numpy(float), zp[r.out].to_numpy(float)),
                             pool_lo=cip[0], pool_hi=cip[1], n_pool=len(zp)))
    pd.DataFrame(rows).to_csv(OUT + "/ci_top.csv", index=False)
    # missing reasons
    M = F[F["ok"] != 1].groupby(["point", "year", "why"]).size().unstack(fill_value=0)
    M.to_csv(OUT + "/missing.csv")
    print(pd.DataFrame(rows).to_string(index=False))
    print(M.to_string())


if __name__ == "__main__":
    main()
