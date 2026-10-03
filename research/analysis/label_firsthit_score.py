#!/usr/bin/env python3
"""label_firsthit_score.py — cham TANG MODEL LABEL_FIRSTHIT (pre-reg docs/prereg/PREREG_LABEL_FIRSTHIT.md §3).

Diem (bins 26B/rec, p0 = P(y=1)): RAW  FH, CTRL (Kaggle), ORIG (= predwf_G015x26 tai lap ~/f0_repro/g015x26_regen)
                                  MAP  FHm, CTRLm (x1_build_map s1a2x1), B0 (~/predwf_map_s1a2_x1 deploy).
Nhan OOS: y_FH / hit / ret168 (fh_all.parquet), y_old = 1[retEnd_4h > 0.015] (ds_label15m, nBars_4h >= 16).
Thuoc: (i) rank-IC per-tick (MIN_N 30) score x {y_FH, y_old}, mean theo fold; (ii) top-16/tick theo p giam dan
(vu tru = dong co nhan FH hop le): yFH, ret168, proxy SL (hit in {2,3}), y_old; (iii) xs-rank-corr per-tick.
CI: paired theo tick FH - CTRL, bootstrap khoi 72h (sens. 168h), NREP 2000, seed 20260905, k = 1.
Usage: python3 label_firsthit_score.py [--out json]
"""
import argparse, glob, json, logging, os, sys
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("fhs")
D = "/home/ubuntu/claude_master/1003/fh"
SRC = {"FH": D + "/out_FH", "CTRL": D + "/out_CTRL", "ORIG": "/home/ubuntu/f0_repro/g015x26_regen",
       "FHm": D + "/map_FH", "CTRLm": D + "/map_CTRL", "B0": "/home/ubuntu/predwf_map_s1a2_x1"}
CUTS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701", "20231001",
        "20240101", "20240401", "20240701", "20241001", "20250101", "20250401", "20250701", "20251001"]
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
MIN_N, K = 30, 16
NREP, SEED = 2000, 20260905
H = 3600000


def old_labels():
    """y_old = 1[retEnd_4h > 0.015] (nBars_4h >= 16), 2021-10..2025-12; cache parquet."""
    cp = D + "/yold_cache.parquet"
    if os.path.exists(cp):
        return pd.read_parquet(cp)
    sys.path.insert(0, "/home/ubuntu/sel1m_code")
    import funding_label_pb as FLPB
    smap = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int64)))
    parts = []
    for fp in sorted(glob.glob("/home/ubuntu/ds_label15m/funding_label_*.pb")):
        a = os.path.basename(fp).split("_")[2]
        if a < "20211001" or a >= "20260101":
            continue
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol", "retEnd_4h", "nBars_4h"])
        d = d[(d.nBars_4h >= 16) & d.retEnd_4h.notna()]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        parts.append(pd.DataFrame({"ts": d.tEpochMs.to_numpy(np.int64)[k], "sym": sid[k].to_numpy(np.int64),
                                   "y_old": (d.retEnd_4h.to_numpy()[k] > 0.015).astype(np.int8)}))
        log.info("old %s: %d", os.path.basename(fp), k.sum())
    Y = pd.concat(parts, ignore_index=True).drop_duplicates(["ts", "sym"])
    Y.to_parquet(cp, index=False)
    return Y


def load_bin(name, f):
    a = np.fromfile(os.path.join(SRC[name], "predict_wf_%s.bin" % f), dtype=DT)
    return pd.DataFrame({"ts": a["ts"].astype(np.int64), "sym": a["sym"].astype(np.int64), name: a["p0"].astype(np.float64)})


def tick_spear(ts, a, b):
    """Spearman per tick (rank trung binh), chi tick n >= MIN_N; tra ve Series index ts."""
    df = pd.DataFrame({"ts": ts, "a": a, "b": b})
    g = df.groupby("ts", sort=False)
    df["ra"] = g.a.rank(); df["rb"] = g.b.rank()
    df["ab"] = df.ra * df.rb; df["aa"] = df.ra ** 2; df["bb"] = df.rb ** 2
    s = df.groupby("ts")[["ra", "rb", "ab", "aa", "bb"]].sum()
    n = df.groupby("ts").size()
    cov = s.ab - s.ra * s.rb / n
    va = s.aa - s.ra ** 2 / n
    vb = s.bb - s.rb ** 2 / n
    with np.errstate(all="ignore"):
        r = cov / np.sqrt(va * vb)
    r[(n < MIN_N) | (va <= 0) | (vb <= 0)] = np.nan
    return r


def boot(d, ts, block_h, rng_seed=SEED):
    """mean(d) + CI95 bootstrap khoi (block_h gio) tren luoi chung."""
    ok = np.isfinite(d)
    d, ts = d[ok], ts[ok]
    b = (ts - ts.min()) // (block_h * H)
    _, inv = np.unique(b, return_inverse=True)
    S = np.bincount(inv, weights=d); C = np.bincount(inv).astype(np.float64)
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, len(S), size=(NREP, len(S)))
    bs = S[idx].sum(1) / C[idx].sum(1)
    return {"mean": float(d.mean()), "ci": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
            "n_ticks": int(len(d)), "n_blocks": int(len(S))}


def fold_eval(f, FHL, Y, names):
    M = None
    for nm in names:
        b = load_bin(nm, f)
        M = b if M is None else M.merge(b, on=["ts", "sym"], how="inner")
        log.info("fold %s %s rows %d -> join %d", f, nm, len(b), len(M))
    M = M.merge(FHL, on=["ts", "sym"], how="left").merge(Y, on=["ts", "sym"], how="left")
    ic = {}
    for nm in names:
        for lab in ("y", "y_old"):
            k = M[lab].notna().to_numpy()
            r = tick_spear(M.ts.to_numpy()[k], M[nm].to_numpy()[k], M[lab].to_numpy(np.float64)[k])
            ic["%s|%s" % (nm, lab)] = float(r.mean())
    xs = {}
    for a, b in (("FH", "ORIG"), ("CTRL", "ORIG"), ("FH", "CTRL"), ("FHm", "B0"), ("CTRLm", "B0"), ("FHm", "CTRLm")):
        if a in names and b in names:
            xs["%s~%s" % (a, b)] = float(tick_spear(M.ts.to_numpy(), M[a].to_numpy(), M[b].to_numpy()).mean())
    U = M[M.y.notna()].copy()
    U["sl"] = U.hit.isin([2, 3]).astype(np.float64)
    nU = U.groupby("ts").size()
    good = nU.index[nU >= MIN_N]
    U = U[U.ts.isin(good)]
    tops = []
    for nm in names:
        rk = U.groupby("ts")[nm].rank(ascending=False, method="first")
        T = U[rk <= K].groupby("ts").agg(yfh=("y", "mean"), ret=("ret168", "mean"), sl=("sl", "mean"),
                                          yold=("y_old", "mean"), n=("y", "size"))
        T["score"] = nm
        tops.append(T.reset_index())
    A = U.groupby("ts").agg(yfh=("y", "mean"), ret=("ret168", "mean"), sl=("sl", "mean"), yold=("y_old", "mean"),
                            n=("y", "size")).reset_index().assign(score="ALL")
    tops.append(A)
    T = pd.concat(tops, ignore_index=True)
    T["fold"] = f
    cover = {"rows": int(len(M)), "fh_cov": float(M.y.notna().mean()), "old_cov": float(M.y_old.notna().mean()),
             "ticks_eval": int(len(good))}
    return ic, xs, T, cover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=D + "/label_firsthit_model.json")
    ap.add_argument("--names", default="FH,CTRL,ORIG,FHm,CTRLm,B0")
    a = ap.parse_args()
    names = a.names.split(",")
    FHL = pd.read_parquet(D + "/fh_all.parquet", columns=["ts", "symId", "y", "hit", "ret168"])
    FHL = FHL.rename(columns={"symId": "sym"}).astype({"sym": np.int64, "y": np.float64})
    Y = old_labels()
    ICS, XS, TS, COV = {}, {}, [], {}
    for f in CUTS:
        ic, xs, T, cov = fold_eval(f, FHL, Y, names)
        ICS[f], XS[f], COV[f] = ic, xs, cov
        TS.append(T)
        log.info("fold %s cover %s IC %s XS %s", f, cov, {k: round(v, 4) for k, v in ic.items()},
                 {k: round(v, 3) for k, v in xs.items()})
    T = pd.concat(TS, ignore_index=True)
    T["yr"] = pd.to_datetime(T.ts + 7 * H, unit="ms").dt.year      # nam theo GMT+7 (= quy uoc cutoff fold)
    T.to_parquet(D + "/top16_ticks.parquet", index=False)
    res = {"cover": COV, "ic_fold": ICS, "xs_fold": XS,
           "ic_mean": pd.DataFrame(ICS).T.mean().to_dict(), "xs_mean": pd.DataFrame(XS).T.mean().to_dict()}
    tab = T.groupby(["score", "yr"])[["yfh", "ret", "sl", "yold"]].mean()
    tab_all = T.groupby("score")[["yfh", "ret", "sl", "yold"]].mean()
    res["top16_year"] = {"%s|%d" % k: v for k, v in tab.to_dict("index").items()}
    res["top16_all"] = tab_all.to_dict("index")
    log.info("TOP16 toan ky\n%s\nTOP16 theo nam\n%s", tab_all.round(4).to_string(), tab.round(4).to_string())
    P = T.pivot_table(index="ts", columns="score", values=["sl", "ret", "yfh"])
    tsv = P.index.to_numpy(np.int64)
    ci = {}
    for x, y in (("FH", "CTRL"), ("FH", "ORIG"), ("CTRL", "ORIG"), ("FHm", "CTRLm"), ("FHm", "B0"), ("CTRLm", "B0")):
        if x not in names or y not in names:
            continue
        for met in ("sl", "ret", "yfh"):
            d = (P[(met, x)] - P[(met, y)]).to_numpy(np.float64)
            for bh in (72, 168):
                ci["%s-%s|%s|b%d" % (x, y, met, bh)] = boot(d, tsv, bh)
            yr = pd.to_datetime(tsv + 7 * H, unit="ms").year
            for yy in (2022, 2023, 2024, 2025):
                k = yr == yy
                ci["%s-%s|%s|b72|%d" % (x, y, met, yy)] = boot(d[k], tsv[k], 72)
    res["ci"] = ci
    if "FH-CTRL|sl|b72" not in ci:
        json.dump(res, open(a.out, "w"), indent=1, default=float)
        log.info("SCORE_DONE (khong co FH/CTRL) -> %s", a.out)
        return
    g_sl = ci["FH-CTRL|sl|b72"]; g_ret = ci["FH-CTRL|ret|b72"]
    go = bool(g_sl["ci"][1] < 0 and not (g_ret["ci"][1] < 0))
    res["gate"] = {"dSL": g_sl, "dRet": g_ret, "GO_model": go,
                   "rule": "dSL top16 RAW FH-CTRL CI95 b72 hoan toan <0 VA dRet168 CI95 b72 khong hoan toan <0"}
    for k, v in ci.items():
        if "|b72|" not in k:
            log.info("CI %-24s mean %+.5f CI [%+.5f, %+.5f] ticks %d blocks %d", k, v["mean"], v["ci"][0], v["ci"][1],
                     v["n_ticks"], v["n_blocks"])
    log.info("GO_model = %s", go)
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    log.info("SCORE_DONE -> %s", a.out)


if __name__ == "__main__":
    main()
