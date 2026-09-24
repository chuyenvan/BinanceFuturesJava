#!/usr/bin/env python3
"""PRESCREEN Stage 0 — DO 20 feature moi va AP TIEU CHI LOC da chot TRUOC.
Pre-reg: docs/PREREG_PRESCREEN_FEAT.md (commit 6695a8c). THUAN PYTHON OFFLINE, khong train/sim.
Ra: /tmp/prefeat/metrics.csv, /tmp/prefeat/maxrho.csv, /tmp/prefeat/verdict.json (in ra man hinh).
CI: block-72h, 2000 rep, seed 20260905, x inflate(k=23)=2.5042.
"""
import os, sys, json, time, math, logging
import numpy as np, pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("eval")
OUT = "/tmp/prefeat"
JOINED = "/tmp/evfeat/joined.parquet"
H = 3600000
NREP = 2000
SEED = 20260905
K_CAND = 23
INFL = math.sqrt(2 * math.log(K_CAND))

KEEPERS21 = ["f20", "f24", "f5", "f30", "f6", "f32", "f14", "f18", "ls_global", "f2", "f17",
             "f7", "oi_z", "f29", "f8", "f35", "f31", "taker_buy", "f10", "oi_delta24h", "f28"]
KNAME = {"f20": "fundingRateTrend", "f24": "fundingSum24h", "f5": "rateDown15MAvg", "f30": "atrSqueeze",
         "f6": "momentum1H", "f32": "fundingRankCS", "f14": "basketMomentum24H", "f18": "basketFundingAvg",
         "ls_global": "ls_global", "f2": "btcMomentum24H", "f17": "coinFundingRate", "f7": "momentum4H",
         "oi_z": "oi_z", "f29": "rangePosition24H", "f8": "momentum24H", "f35": "ret15m",
         "f31": "relStrengthBtc24H", "taker_buy": "taker_buy", "f10": "distFromLow24H",
         "oi_delta24h": "oi_delta24h", "f28": "distFromHigh24H"}
A_FEATS = ["mom7d", "mom30d", "distFromHigh30D", "distFromHigh90D", "rangePosition7D", "rvol7d",
           "rvolRatio", "squeezeLong", "trendConsistency7d", "daysSinceHigh30D", "oi_delta7d", "oiPersistence"]
A_BUILT = [f for f in A_FEATS if f != "rvolRatio"]
B_FEATS = ["btcMom7d", "btcMom30d", "marketBreadth7D", "mktRealizedVol7D", "volRegime", "dispersion7D",
           "avgCorrToBtc7D", "altBreadthMom7D"]
NEW = A_FEATS + B_FEATS
GROUP = {f: "A" for f in A_FEATS}
GROUP.update({f: "B" for f in B_FEATS})
DROP_NODATA = ["fundingCum7d", "mktFundingPercentile", "listingAgeDays"]

rng = np.random.default_rng(SEED)


def block_boot(vals, ts):
    ts = np.asarray(ts).astype(np.int64)
    vals = np.asarray(vals, dtype=np.float64)
    bk = ts // (72 * H)
    ub = np.unique(bk)
    pos = {int(b): i for i, b in enumerate(ub)}
    bi = np.fromiter((pos[int(b)] for b in bk), dtype=np.int64, count=len(bk))
    sums = np.bincount(bi, weights=vals, minlength=len(ub))
    cnts = np.bincount(bi, minlength=len(ub)).astype(np.float64)
    keep = cnts > 0
    sums, cnts = sums[keep], cnts[keep]
    out = np.empty(NREP)
    for b in range(NREP):
        pick = rng.integers(0, len(sums), len(sums))
        out[b] = sums[pick].sum() / cnts[pick].sum()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    t0 = time.time()
    D = pd.read_parquet(JOINED, columns=["ts", "symId", "retEnd_4h", "f36"] + KEEPERS21)
    A = pd.read_parquet(os.path.join(OUT, "A.parquet"))
    B = pd.read_parquet(os.path.join(OUT, "B.parquet"))
    B["avail_ms"] = B["day_ms"] + H          # gia tri ngay D chi dung duoc tu 00:00 ngay D+1
    D = D.merge(A[["ts", "symId"] + A_BUILT], on=["ts", "symId"], how="left")
    D = D.sort_values("ts", kind="stable").reset_index(drop=True)
    D = pd.merge_asof(D, B[["avail_ms"] + B_FEATS].sort_values("avail_ms"), left_on="ts",
                      right_on="avail_ms", direction="backward")
    D["rvolRatio"] = D["f36"] / D["rvol7d"].replace(0, np.nan)
    log.info("merged rows=%d cols=%d (%.0fs)", len(D), len(D.columns), time.time() - t0)

    # ---- (3) max|rho| voi 21 keeper (lam NGAY tren mau 250k, roi bo cot keeper de tiet kiem RAM) ----
    S = D.sample(min(250000, len(D)), random_state=7)
    rows = []
    for f in NEW:
        for k in KEEPERS21:
            sub = S[[f, k]].dropna()
            if len(sub) < 1000:
                rows.append({"feat": f, "keeper": KNAME[k], "rho": np.nan, "n": len(sub)})
                continue
            rows.append({"feat": f, "keeper": KNAME[k], "rho": float(sub[f].corr(sub[k], method="spearman")),
                         "n": len(sub)})
    MR = pd.DataFrame(rows)
    MR.to_csv(os.path.join(OUT, "maxrho.csv"), index=False)
    mr = MR.dropna(subset=["rho"]).groupby("feat")["rho"].apply(lambda s: s.abs().max())
    mrw = MR.dropna(subset=["rho"]).assign(a=lambda x: x.rho.abs()).sort_values("a").groupby("feat").tail(1).set_index("feat")
    log.info("maxrho done (%.0fs)", time.time() - t0)
    del S
    D.drop(columns=KEEPERS21, inplace=True)

    # ---- (1) coverage ----
    cov = {f: float(D[f].notna().mean()) for f in NEW}
    # ---- (2) frac_tick_constant ----
    g = D.groupby("ts")
    gsize = g.size()
    ftc = {}
    for f in NEW:
        sd = g[f].std(ddof=0)
        m = sd.notna()
        if len(m) and m.any():
            ok = gsize.reindex(sd.index[m]) >= 2
            ftc[f] = float((sd[m][ok.values] <= 0).mean()) if ok.any() else float("nan")
        else:
            ftc[f] = float("nan")
    log.info("coverage+ftc done (%.0fs)", time.time() - t0)

    # ---- (4) rank-IC + CI ; (5) decile edge + CI ----
    D["_lr"] = D.groupby("ts")["retEnd_4h"].rank(method="average")
    lr_mean = D["_lr"].groupby(D.ts).transform("mean")
    lr_ss = ((D["_lr"] - lr_mean) ** 2).groupby(D.ts).sum()
    out = {}
    for f in NEW:
        fr = D[f].rank(method="average")
        fm = fr.groupby(D.ts).transform("mean")
        num = ((fr - fm) * (D["_lr"] - lr_mean)).groupby(D.ts).sum()
        fss = ((fr - fm) ** 2).groupby(D.ts).sum()
        ic = (num / np.sqrt(fss * lr_ss).replace(0, np.nan)).dropna()
        lo, hi = block_boot(ic.values, ic.index.values)
        p = D.groupby("ts")[f].rank(pct=True, method="average")
        dec = np.floor(p * 10).clip(0, 9)
        gg = D.assign(_d=dec.values).groupby(["ts", "_d"])["retEnd_4h"].mean().unstack()
        edge = (gg[9] - gg[0]).dropna() if (9 in gg.columns and 0 in gg.columns) else pd.Series(dtype=float)
        if len(edge):
            elo, ehi = block_boot(edge.values, edge.index.values)
            em = float(edge.mean())
        else:
            elo = ehi = em = np.nan
        out[f] = dict(ic=float(ic.mean()), ic_lo=lo, ic_hi=hi, n_tick=int(len(ic)),
                      ic_lo_inf=float(ic.mean() - (ic.mean() - lo) * INFL),
                      ic_hi_inf=float(ic.mean() + (hi - ic.mean()) * INFL),
                      edge_bp=em * 1e4, edge_lo=elo * 1e4, edge_hi=ehi * 1e4,
                      edge_lo_inf=(em - (em - elo) * INFL) * 1e4, edge_hi_inf=(em + (ehi - em) * INFL) * 1e4)
        log.info(" ic %s %.4f [%.4f,%.4f] edge %.2fbp (%.0fs)", f, out[f]["ic"], lo, hi, out[f]["edge_bp"], time.time() - t0)
    M = pd.DataFrame(out).T.reset_index().rename(columns={"index": "feat"})
    M["coverage"] = M.feat.map(cov)
    M["frac_tick_constant"] = M.feat.map(ftc)
    M["max_abs_rho"] = M.feat.map(mr)
    M["rho_partner"] = M.feat.map(mrw["keeper"])
    M["rho_signed"] = M.feat.map(mrw["rho"])
    M["group"] = M.feat.map(GROUP)
    M["abs_ic"] = M.ic.abs()
    # ---- ap tieu chi ----
    M["a_cov"] = M.coverage >= 0.90
    M["b_rho"] = M.max_abs_rho <= 0.70
    M["c_ftc"] = M.frac_tick_constant <= 0.95
    M["d_ci_ic"] = (M.ic_lo_inf > 0) | (M.ic_hi_inf < 0)
    M["d_ci_edge"] = (M.edge_lo_inf > 0) | (M.edge_hi_inf < 0)
    M["d_absic"] = M.abs_ic >= 0.02
    M["d_sig"] = M.d_ci_ic | M.d_ci_edge | M.d_absic
    M["PASS"] = M.a_cov & M.b_rho & M.c_ftc & M.d_sig
    M.to_csv(os.path.join(OUT, "metrics.csv"), index=False)
    keep = M[M.PASS].sort_values("abs_ic", ascending=False)
    verdict = {"n_proposed": 23, "n_dropped_nodata": DROP_NODATA, "n_measured": len(NEW),
               "ci_inflate_k": K_CAND, "ci_inflate": INFL, "nrep": NREP, "seed": SEED,
               "n_pass": int(len(keep)), "pass_list": keep.feat.tolist(),
               "final_top8_by_abs_ic": keep.head(8).feat.tolist()}
    json.dump(verdict, open(os.path.join(OUT, "verdict.json"), "w"), indent=1)
    pd.set_option("display.width", 250)
    log.info("VERDICT %s", json.dumps(verdict))
    log.info("\n%s", M[["group", "feat", "coverage", "frac_tick_constant", "max_abs_rho", "rho_partner",
                        "ic", "ic_lo_inf", "ic_hi_inf", "edge_bp", "edge_lo_inf", "edge_hi_inf",
                        "a_cov", "b_rho", "c_ftc", "d_sig", "PASS"]].to_string(index=False))
    log.info("DONE %.0fs", time.time() - t0)


if __name__ == "__main__":
    main()
