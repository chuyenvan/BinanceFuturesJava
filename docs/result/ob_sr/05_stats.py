#!/usr/bin/env python3
"""OB_SR 05: IC / bootstrap CI / deciles / verdict (frozen prereg criteria)."""
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
SEED = 20261023
NREP = 2000


def spearman(x, y):
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
    if not out:
        return [np.nan, np.nan]
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def main():
    F = pd.read_parquet(OUT + "/features.parquet")
    R = pd.read_parquet(OUT + "/price_out.parquet")
    G = pd.read_parquet(OUT + "/anchor.parquet")
    A = pd.read_parquet(OUT + "/anchors.parquet")
    for d in (F, R, G, A):
        d["t0"] = pd.to_datetime(d["t0"])
    F = F.merge(R[["sym", "t0", "arm_j", "mfe24_bps", "mfe72_bps", "gb_med", "pt_med",
                    "extra24_bps", "extra72_bps"]], on=["sym", "t0"], how="left")
    F = F.merge(G[["sym", "t0", "E", "pnl", "entry_notional", "age_max"]], on=["sym", "t0"],
                how="left", suffixes=("", "_g"))
    F["arm168"] = (F["arm_j"] > 0).astype(float)
    F["day"] = F["t0"].dt.floor("D")
    F.loc[F["ok"] != 1, FEAT] = np.nan
    # seed-cluster counts per decision point (actual strategy units)
    A2 = A.merge(R[["sym", "t0", "arm_j"]], on=["sym", "t0"], how="left")
    A2 = A2[A2["t0"].dt.year == 2024]
    nseed = {"entry": len(A2) / 8.0,
             "arm": len(A2[A2["arm_j"] > 0]) / 8.0,
             "h168": len(A2[A2["age_min"] >= 10081]) / 8.0}

    res = {"ic": [], "coverage": {}, "screen": [], "decile": [], "nseed_2024": nseed}
    # coverage
    for p, g in F.groupby("point"):
        for y, gy in g.groupby("year"):
            res["coverage"]["%s_%d" % (p, y)] = dict(n=len(gy), ok=int(gy["ok"].sum()),
                                                     frac=float(gy["ok"].mean()))

    # IC tables
    for p, outs in OUTS.items():
        D = F[F["point"] == p]
        for y in (2023, 2025, 2024):
            Dy = D[D["year"] == y]
            for f in FEAT:
                for o in outs:
                    z = Dy[[f, o, "day"]].dropna()
                    if len(z) < 30 or z[f].nunique() < 2:
                        continue
                    r = spearman(z[f].to_numpy(float), z[o].to_numpy(float))
                    res["ic"].append(dict(point=p, year=y, feat=f, out=o, ic=r, n=len(z),
                                          days=int(z["day"].nunique())))
        # pooled 2023+2025
        Dp = D[D["year"].isin([2023, 2025])]
        for f in FEAT:
            for o in outs:
                z = Dp[[f, o, "day"]].dropna()
                if len(z) < 30 or z[f].nunique() < 2:
                    continue
                res["ic"].append(dict(point=p, year=2325, feat=f, out=o,
                                      ic=spearman(z[f].to_numpy(float), z[o].to_numpy(float)),
                                      n=len(z), days=int(z["day"].nunique())))
    IC = pd.DataFrame(res["ic"])

    # screen + bootstrap + deciles
    rng = np.random.default_rng(SEED)
    for p, outs in OUTS.items():
        D = F[F["point"] == p]
        for f in FEAT:
            for o in outs:
                z = {y: D[(D["year"] == y)][[f, o, "day", "pnl", "entry_notional"]].dropna()
                     for y in (2023, 2025, 2024)}
                ics = {y: spearman(z[y][f].to_numpy(float), z[y][o].to_numpy(float)) for y in z}
                if not all(np.isfinite(list(ics.values()))):
                    continue
                if min(abs(v) for v in ics.values()) < 0.10:
                    continue
                if not (np.sign(ics[2023]) == np.sign(ics[2025]) == np.sign(ics[2024])):
                    continue
                zz = z[2024]
                ci = boot(zz[f].to_numpy(float), zz[o].to_numpy(float), zz["day"].to_numpy(), rng)
                # deciles 2024
                try:
                    dec = pd.qcut(zz[f], 10, labels=False, duplicates="drop")
                except ValueError:
                    continue
                dm = zz.groupby(dec)[o].mean()
                if len(dm) < 5:
                    continue
                spread = float(dm.iloc[-1] - dm.iloc[0])
                med_not = float(F[(F["year"] == 2024) & (F["point"] == p)]["entry_notional"].median())
                if o == "arm168":
                    dp = zz.groupby(dec)["pnl"].mean()
                    spread_usd = float(dp.iloc[-1] - dp.iloc[0])
                else:
                    spread_usd = spread / 1e4 * med_not
                nps = nseed[p]
                dhat = 0.10 * nps * spread_usd
                res["screen"].append(dict(point=p, feat=f, out=o, ic2023=ics[2023], ic2025=ics[2025],
                                          ic2024=ics[2024], ci_lo=ci[0], ci_hi=ci[1], n2024=len(zz),
                                          spread=spread, spread_usd=spread_usd, nseed=nps,
                                          dhat_usd=dhat, med_notional=med_not))
                res["decile"].append(dict(point=p, feat=f, out=o,
                                          dec=list(map(float, dm.values)), n=int(len(zz))))

    S = pd.DataFrame(res["screen"])
    if len(S):
        S["pass"] = (S["ci_lo"] > 0) | (S["ci_hi"] < 0)
        S["pass"] &= S["dhat_usd"] >= 5000
    res["verdict"] = dict(n_combos=len(S), pass_combos=int(S["pass"].sum()) if len(S) else 0,
                          any_pass=bool(len(S) and S["pass"].any()))
    res["n_ic_rows"] = len(IC)
    # V2 timezone/price
    E = F[(F["point"] == "entry") & (F["ok"] == 1)].merge(R[["sym", "t0", "px0"]], on=["sym", "t0"], how="left")
    r1 = np.abs(np.log(E["mid"] / E["E"])).replace([np.inf, -np.inf], np.nan).dropna()
    E6 = F[(F["point"] == "h168") & (F["ok"] == 1)].merge(R[["sym", "t0", "px168"]], on=["sym", "t0"], how="left")
    r6 = np.abs(np.log(E6["mid"] / E6["px168"])).replace([np.inf, -np.inf], np.nan).dropna()
    res["v2"] = dict(entry_med=float(r1.median()), entry_p99=float(r1.quantile(.99)), entry_n=len(r1),
                     h168_med=float(r6.median()), h168_p99=float(r6.quantile(.99)), h168_n=len(r6),
                     entry_snap_med=float(np.abs(np.log(E.loc[E["lag_s"] < 60, "mid"] / E.loc[E["lag_s"] < 60, "px0"])).median()))
    res["v1_ok"] = bool((F[F["ok"] == 1]["lag_s"] <= 300).all())
    IC.to_csv(OUT + "/ic.csv", index=False)
    if len(S):
        S.to_csv(OUT + "/screen.csv", index=False)
    json.dump(res, open(OUT + "/stats.json", "w"), indent=1, default=float)
    print("IC rows", len(IC), "screened", len(S), "pass", res["verdict"])
    print("V2", res["v2"], "V1", res["v1_ok"])
    print(pd.DataFrame(res["coverage"]).T.to_string())
    if len(S):
        print(S.sort_values("dhat_usd", ascending=False).head(15).to_string())


if __name__ == "__main__":
    main()
