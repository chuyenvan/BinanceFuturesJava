#!/usr/bin/env python3
"""SHORT_V2 Pha 0B — squeeze-predictability cua model LONG (S1 / p15 / predRisk4H[in-sample]).

Pre-reg: docs/prereg/PREREG_SHORT_V2_P0B.md (commit 11df71fd). Chay MOT lan, khong tune.
Nhan tu 1h closes: retEnd_7d, maxFav_7d (can DUOI squeeze). lp = -score (lp CAO = long thich).
Output: docs/result/RESULT_SHORT_V2_P0B.json
"""
import json
import logging
import sys
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger("p0b")

H = 3600000
DAY = 86400000
MIN = 60000
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
S1 = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
REPO = "/home/ubuntu/src/BinanceFuturesJava"
P15 = REPO + "/research/parity/data/p15_dev.csv"
OUTJ = REPO + "/docs/result/RESULT_SHORT_V2_P0B.json"
SEAL = 1767225600000          # 2026-01-01 00:00 UTC
DEV0 = 1640995200000          # 2022-01-01 00:00 UTC
GRID_LAST = 1766534400000     # 2025-12-24 00:00 UTC
WIN = 168
MINBARS = 160
HIST_MIN = 720
MIN_DEC = 20
NREP = 2000
SEED = 20260905
BLOCK = 7 * DAY
YEARS = (2022, 2023, 2024, 2025)


def load_grid():
    """sym -> (t0_ctime, float32 hourly array indexed (ctime-t0)//H, exclusive cumcount finite)."""
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64)
    m = ts < SEAL
    ct = ts[m] + H
    sym = a["sym"][m].astype(np.int32)
    c = a["c"][m].astype(np.float32)
    del a, ts
    o = np.lexsort((ct, sym))
    ct, sym, c = ct[o], sym[o], c[o]
    keep = np.r_[True, (ct[1:] != ct[:-1]) | (sym[1:] != sym[:-1])]   # dup -> giu dong DAU
    ct, sym, c = ct[keep], sym[keep], c[keep]
    assert np.all(ct % H == 0), "ctime khong tron gio"
    u, first = np.unique(sym, return_index=True)
    ends = np.append(first[1:], len(sym))
    grid = {}
    for s, f, e in zip(u, first, ends):
        t = ct[f:e]
        t0 = int(t[0])
        n = int((t[-1] - t0) // H) + 1
        arr = np.full(n, np.nan, dtype=np.float32)
        arr[(t - t0) // H] = c[f:e]
        arr[~(arr > 0)] = np.nan
        cs = np.concatenate([[0], np.cumsum(np.isfinite(arr))]).astype(np.int32)
        grid[int(s)] = (t0, arr, cs)
    L.info("closes: %d sym, ctime max %s", len(grid), pd.Timestamp(int(ct.max()), unit="ms"))
    return grid


def label_sym(g, entry_ct):
    """entry_ct int64 array (gio tron). Tra ve retEnd, maxFav (float32), hist (int32), valid (bool)."""
    t0, arr, cs = g
    n = len(entry_ct)
    ret = np.full(n, np.nan, dtype=np.float32)
    mf = np.full(n, np.nan, dtype=np.float32)
    hist = np.zeros(n, dtype=np.int32)
    i = (entry_ct - t0) // H
    ok = (i >= 0) & (i + WIN < len(arr)) & (entry_ct + WIN * H <= SEAL)
    if not ok.any():
        return ret, mf, hist, np.zeros(n, dtype=bool)
    ii = i[ok]
    c0 = arr[ii].astype(np.float64)
    W = arr[ii[:, None] + np.arange(1, WIN + 1)[None, :]].astype(np.float64)
    nb = np.isfinite(W).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mx = np.nanmax(np.where(np.isfinite(W), W, -np.inf), axis=1)
        end = W[:, -1]
        r = end / c0 - 1.0
        f = mx / c0 - 1.0
    v = np.isfinite(c0) & np.isfinite(end) & (nb >= MINBARS)
    ret[ok] = np.where(v, r, np.nan)
    mf[ok] = np.where(v, f, np.nan)
    hist[ok] = cs[ii]
    valid = np.zeros(n, dtype=bool)
    valid[ok] = v
    return ret, mf, hist, valid


def label_panel(grid, sym, entry_ct):
    """Gan nhan cho panel (sym, entry_ct) bat ky."""
    n = len(sym)
    ret = np.full(n, np.nan, dtype=np.float32)
    mf = np.full(n, np.nan, dtype=np.float32)
    hist = np.zeros(n, dtype=np.int32)
    valid = np.zeros(n, dtype=bool)
    o = np.argsort(sym, kind="stable")
    ss = sym[o]
    u, first = np.unique(ss, return_index=True)
    ends = np.append(first[1:], n)
    for s, f, e in zip(u, first, ends):
        g = grid.get(int(s))
        if g is None:
            continue
        idx = o[f:e]
        r, m, h, v = label_sym(g, entry_ct[idx])
        ret[idx], mf[idx], hist[idx], valid[idx] = r, m, h, v
    return ret, mf, hist, valid


def auc_rank(score, y):
    """AUC Mann-Whitney voi rank average (xu ly ties)."""
    score = np.asarray(score, dtype=np.float64)
    y = np.asarray(y, dtype=bool)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    rk = pd.Series(score).rank(method="average").to_numpy()
    return float((rk[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def stats4(d):
    if len(d) == 0:
        return {"n": 0}
    m = d["mf"].to_numpy(np.float64)
    r = d["ret"].to_numpy(np.float64)
    return {"n": int(len(d)), "pSQ10": round(float((m >= 0.10).mean()), 5),
            "pSQ20": round(float((m >= 0.20).mean()), 5),
            "mean_ret": round(float(r.mean()), 5), "median_ret": round(float(np.median(r)), 5)}


def dec_table(d, qcol):
    out = {"universe": stats4(d)}
    for q in range(10):
        out["d%d" % q] = stats4(d[d[qcol] == q])
    return out


def block_ci(series_ts, vals):
    """mean + CI95 block-7d (khoi lich 7 ngay, trong so = so snapshot/khoi), khong inflate."""
    s = pd.Series(np.asarray(vals, dtype=np.float64), index=np.asarray(series_ts)).dropna()
    if len(s) < 2:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n_snap": int(len(s))}
    blk = (s.index.to_numpy() - DEV0) // BLOCK
    gm = s.groupby(blk).mean().to_numpy()
    gc = s.groupby(blk).size().to_numpy()
    nb = len(gm)
    rng = np.random.default_rng(SEED)
    dr = np.empty(NREP)
    for k in range(NREP):
        p = rng.integers(0, nb, size=nb)
        dr[k] = np.sum(gm[p] * gc[p]) / np.sum(gc[p])
    lo, hi = np.percentile(dr, [2.5, 97.5])
    return {"mean": round(float(s.mean()), 5), "lo": round(float(lo), 5), "hi": round(float(hi), 5),
            "n_snap": int(len(s)), "n_blocks": int(nb)}


def load_p15():
    p = pd.read_csv(P15, dtype={"ts": np.int64, "predReturn15M": np.float32, "predRisk4H": np.float32})
    p = p.sort_values("ts").reset_index(drop=True)
    L.info("p15: %d dong, %s -> %s", len(p), pd.Timestamp(int(p.ts.iloc[0]), unit="ms"),
           pd.Timestamp(int(p.ts.iloc[-1]), unit="ms"))
    return p["ts"].to_numpy(), p["predReturn15M"].to_numpy(), p["predRisk4H"].to_numpy()


def p15_at(pts, pv, snap):
    """Dong phut cuoi co ts <= snap - 2'. Tra ve (gia tri, ts dung)."""
    i = np.searchsorted(pts, np.asarray(snap) - 2 * MIN, side="right") - 1
    v = np.where(i >= 0, pv[np.maximum(i, 0)], np.nan).astype(np.float32)
    return v, np.where(i >= 0, pts[np.maximum(i, 0)], -1)


def year_of(ms):
    return pd.to_datetime(np.asarray(ms), unit="ms").year.to_numpy()


def entry_from_tick(ts):
    """Tick S1 tai ts -> entry ctime = tran-gio(ts + 15')."""
    x = np.asarray(ts, dtype=np.int64) + 15 * MIN
    return ((x + H - 1) // H) * H


def assign_decile(d, col, key="snap"):
    cnt = d.groupby(key)[col].transform("size")
    d = d[cnt >= MIN_DEC].copy()
    rk = d.groupby(key)[col].rank(method="first")
    d["_rk"] = rk
    d["q"] = d.groupby(key)["_rk"].transform(lambda x: pd.qcut(x, 10, labels=False)).astype(int)
    return d.drop(columns="_rk")


def within_auc(d, col, ycol):
    rows = []
    for s, g in d.groupby("snap"):
        y = g[ycol].to_numpy()
        if y.sum() >= 3 and (len(y) - y.sum()) >= 3:
            rows.append((s, auc_rank(g[col].to_numpy(), y)))
    return pd.Series([r[1] for r in rows], index=[r[0] for r in rows], dtype=float)


def spearman_snap(d, col):
    rows = []
    for s, g in d.groupby("snap"):
        if len(g) >= MIN_DEC:
            a = g[col].rank().to_numpy()
            b = g["mf"].rank().to_numpy()
            rows.append((s, float(np.corrcoef(a, b)[0, 1])))
    return pd.Series([r[1] for r in rows], index=[r[0] for r in rows], dtype=float)


def auc_years(d, col, ycols=("sq10", "sq20")):
    out = {}
    for yc in ycols:
        o = {}
        for y in YEARS:
            g = d[d.year == y]
            o[str(y)] = round(auc_rank(g[col].to_numpy(), g[yc].to_numpy()), 5) if len(g) else None
        o["all"] = round(auc_rank(d[col].to_numpy(), d[yc].to_numpy()), 5)
        out[yc] = o
    return out


def build_s1(grid, pts, p15v, rkv):
    sp = pd.read_parquet(S1, columns=["ts", "sym", "score"])
    n_raw = len(sp)
    sp = sp[sp.ts >= DEV0].reset_index(drop=True)
    L.info("S1: %d dong raw, %d dong ts>=2022-01-01", n_raw, len(sp))
    sp["lp"] = (-sp["score"]).astype(np.float32)
    sp["entry"] = entry_from_tick(sp.ts.to_numpy())
    ret, mf, hist, valid = label_panel(grid, sp.sym.to_numpy().astype(np.int64), sp.entry.to_numpy())
    sp["ret"], sp["mf"], sp["valid"] = ret, mf, valid
    sp = sp.rename(columns={"ts": "snap"})
    sp["year"] = year_of(sp.entry.to_numpy())
    sp["sq10"] = sp.mf >= 0.10
    sp["sq20"] = sp.mf >= 0.20
    allt = sp[sp.valid & sp.year.isin(YEARS)].copy()
    # snapshot chinh: tick dau tien moi ngay UTC
    first = sp.groupby(sp.snap // DAY)["snap"].transform("min")
    d = sp[(sp.snap == first) & sp.valid & sp.year.isin(YEARS)].copy()
    d["p15"], _ = p15_at(pts, p15v, d.snap.to_numpy())
    d["risk"], _ = p15_at(pts, rkv, d.snap.to_numpy())
    allt["p15"], _ = p15_at(pts, p15v, allt.snap.to_numpy())
    return d, allt, {"n_rows_dev": int(n_raw), "n_rows_ge2022": int(len(sp)),
                     "valid_frac_all_ticks": round(float(sp.valid.mean()), 5),
                     "n_invalid_window_beyond_seal": int((sp.entry + WIN * H > SEAL).sum())}


def build_grid_panel(grid, pts, p15v, rkv):
    days = np.arange(DEV0, GRID_LAST + 1, DAY, dtype=np.int64)
    parts = []
    for s, g in grid.items():
        t0, arr, cs = g
        e = days[(days >= t0) & (days <= t0 + (len(arr) - 1) * H)]
        if len(e) == 0:
            continue
        r, m, h, v = label_sym(g, e)
        k = v & (h >= HIST_MIN)
        if k.any():
            parts.append(pd.DataFrame({"snap": e[k], "sym": s, "ret": r[k], "mf": m[k]}))
    d = pd.concat(parts, ignore_index=True)
    d["entry"] = d["snap"]
    d["year"] = year_of(d.snap.to_numpy())
    d["sq10"] = d.mf >= 0.10
    d["sq20"] = d.mf >= 0.20
    d["p15"], _ = p15_at(pts, p15v, d.snap.to_numpy())
    d["risk"], _ = p15_at(pts, rkv, d.snap.to_numpy())
    L.info("grid panel: %d coin-ngay, %d ngay", len(d), d.snap.nunique())
    return d


def market_decile(d, col):
    """Decile NGAY theo col: toan ky (bien toan DEV) + theo nam (bien trong nam)."""
    day = d.groupby("snap")[col].first()
    qa = pd.qcut(day.rank(method="first"), 10, labels=False)
    yr = pd.Series(year_of(day.index.to_numpy()), index=day.index)
    qy = day.groupby(yr).transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
    d = d.copy()
    d["qa"] = d.snap.map(qa).astype(int)
    d["qy"] = d.snap.map(qy).astype(int)
    out = {"all": dec_table(d, "qa"), "by_year": {}}
    for y in YEARS:
        out["by_year"][str(y)] = dec_table(d[d.year == y], "qy")
    out["edges_all"] = [round(float(x), 6) for x in np.quantile(day.to_numpy(), np.linspace(0, 1, 11))]
    return out


def sanity(d, allt, gp, grid, meta):
    out = dict(meta)
    for nm, x in (("s1_daily", d), ("s1_alltick", allt), ("p15_grid", gp)):
        out[nm] = {str(y): {"n_snap": int(x[x.year == y].snap.nunique()), "n_rows": int((x.year == y).sum()),
                            "median_coins": float(x[x.year == y].groupby("snap").size().median())}
                   for y in YEARS}
    out["causal_entry_gt_tick"] = bool((d.entry > d.snap).all() and (allt.entry > allt.snap).all())
    out["min_entry_minus_tick_min"] = int((allt.entry - allt.snap).min() // MIN)
    out["max_window_end"] = str(pd.Timestamp(int(max(d.entry.max(), allt.entry.max(), gp.entry.max()) + WIN * H), unit="ms"))
    out["window_end_le_seal"] = bool(max(d.entry.max(), allt.entry.max(), gp.entry.max()) + WIN * H <= SEAL)
    out["min_s1_tick"] = str(pd.Timestamp(int(allt.snap.min()), unit="ms"))
    out["p15_nan_frac_grid"] = round(float(gp.p15.isna().mean()), 6)
    # AUC 2 cach (2024, S1->SQ10)
    g = d[d.year == 2024]
    a1 = auc_rank(g.lp.to_numpy(), g.sq10.to_numpy())
    try:
        from sklearn.metrics import roc_auc_score
        a2 = float(roc_auc_score(g.sq10.to_numpy(), g.lp.to_numpy()))
    except Exception as ex:  # noqa
        a2 = None
        L.info("sklearn loi: %s", ex)
    out["auc_check_2024"] = {"rank_formula": a1, "sklearn": a2,
                             "match_1e-9": bool(a2 is not None and abs(a1 - a2) < 1e-9)}
    # spot-check nhan
    rng = np.random.default_rng(SEED)
    sc = []
    for i in rng.choice(len(d), 3, replace=False):
        row = d.iloc[i]
        t0, arr, _ = grid[int(row.sym)]
        k = int((row.entry - t0) // H)
        c0 = float(arr[k])
        w = arr[k + 1:k + WIN + 1].astype(np.float64)
        sc.append({"sym": int(row.sym), "entry": str(pd.Timestamp(int(row.entry), unit="ms")),
                   "ret_panel": float(row.ret), "ret_manual": float(w[-1] / c0 - 1),
                   "mf_panel": float(row.mf), "mf_manual": float(np.nanmax(w) / c0 - 1)})
    out["spot_check"] = sc
    out["spot_ok"] = bool(all(abs(s["ret_panel"] - s["ret_manual"]) < 1e-5 and
                              abs(s["mf_panel"] - s["mf_manual"]) < 1e-5 for s in sc))
    return out


def spot_raw(d):
    """Spot-check doc lap: doc lai CLOSES_1H.bin goc, loc sym/ctime bang pandas (khong qua grid)."""
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    raw = pd.DataFrame({"ct": a["ts"].astype(np.int64) + H, "sym": a["sym"].astype(np.int64),
                        "c": a["c"].astype(np.float64)})
    del a
    raw = raw[raw.ct <= SEAL]
    rng = np.random.default_rng(SEED + 1)
    out = []
    for i in rng.choice(len(d), 3, replace=False):
        row = d.iloc[i]
        x = raw[(raw.sym == int(row.sym)) & (raw.ct >= row.entry) & (raw.ct <= row.entry + WIN * H)]
        x = x.drop_duplicates("ct").set_index("ct").c
        c0 = x.loc[row.entry]
        fw = x[x.index > row.entry]
        out.append({"sym": int(row.sym), "entry": str(pd.Timestamp(int(row.entry), unit="ms")),
                    "ret_panel": float(row.ret), "ret_raw": float(fw.loc[row.entry + WIN * H] / c0 - 1),
                    "mf_panel": float(row.mf), "mf_raw": float(fw.max() / c0 - 1), "nbars": int(len(fw))})
    ok = all(abs(s["ret_panel"] - s["ret_raw"]) < 1e-5 and abs(s["mf_panel"] - s["mf_raw"]) < 1e-5 for s in out)
    return out, bool(ok)


def s1_block(d, allt):
    res = {"auc_pooled": auc_years(d, "lp"), "auc_pooled_alltick": auc_years(allt, "lp"),
           "auc_within_snap": {}, "spearman_lp_maxfav": {}, "decile": {}, "useful": {}}
    for yc in ("sq10", "sq20"):
        w = within_auc(d, "lp", yc)
        yr = year_of(w.index.to_numpy())
        res["auc_within_snap"][yc] = {str(y): {"mean": round(float(w[yr == y].mean()), 5),
                                               "n_snap": int((yr == y).sum())} for y in YEARS}
        res["auc_within_snap"][yc]["all"] = {"mean": round(float(w.mean()), 5), "n_snap": int(len(w))}
    sp = spearman_snap(d, "lp")
    yr = year_of(sp.index.to_numpy())
    for y in YEARS:
        s = sp[yr == y]
        res["spearman_lp_maxfav"][str(y)] = block_ci(s.index.to_numpy(), s.to_numpy())
    res["spearman_lp_maxfav"]["all"] = block_ci(sp.index.to_numpy(), sp.to_numpy())
    dq = assign_decile(d, "lp")
    res["decile"]["all"] = dec_table(dq, "q")
    res["decile"]["by_year"] = {str(y): dec_table(dq[dq.year == y], "q") for y in YEARS}
    ok_years = 0
    for y in YEARS:
        t = res["decile"]["by_year"][str(y)]
        u, d0 = t["universe"], t["d0"]
        ratio = d0["pSQ10"] / u["pSQ10"] if u["pSQ10"] > 0 else float("nan")
        hit = bool(ratio <= 0.6)
        ok_years += hit
        res["useful"][str(y)] = {"d0_pSQ10": d0["pSQ10"], "univ_pSQ10": u["pSQ10"], "ratio": round(ratio, 4),
                                 "hit": hit, "d0_mean_ret": d0["mean_ret"], "univ_mean_ret": u["mean_ret"],
                                 "d0_median_ret": d0["median_ret"], "univ_median_ret": u["median_ret"]}
    res["useful"]["years_hit"] = ok_years
    res["useful"]["DAT"] = bool(ok_years == 4)
    return res


def main():
    L.info("=== SHORT_V2 P0B squeeze-predictability (prereg 11df71fd) ===")
    grid = load_grid()
    pts, p15v, rkv = load_p15()
    d, allt, meta = build_s1(grid, pts, p15v, rkv)
    L.info("S1 daily: %d rows, %d snap; alltick %d rows", len(d), d.snap.nunique(), len(allt))
    gp = build_grid_panel(grid, pts, p15v, rkv)
    res = {"prereg": "docs/prereg/PREREG_SHORT_V2_P0B.md@11df71fd",
           "conv": "lp=-score (cao = long thich); d0 = lp thap nhat = it pump nhat theo model; "
                   "maxFav tu 1h close = can duoi squeeze",
           "sanity": sanity(d, allt, gp, grid, meta)}
    res["sanity"]["spot_raw"], res["sanity"]["spot_raw_ok"] = spot_raw(d)
    L.info("sanity: %s", json.dumps(res["sanity"], default=str)[:3000])
    res["S1"] = s1_block(d, allt)
    L.info("S1 AUC: %s", res["S1"]["auc_pooled"])
    res["p15"] = {"auc_grid": auc_years(gp.dropna(subset=["p15"]), "p15"),
                  "auc_on_s1set": auc_years(d.dropna(subset=["p15"]), "p15"),
                  "decile": market_decile(gp.dropna(subset=["p15"]), "p15")}
    res["predRisk4H_INSAMPLE"] = {"label": "IN-SAMPLE (khong leak-free) — chi doi chung",
                                  "auc_grid": auc_years(gp.dropna(subset=["risk"]), "risk"),
                                  "decile": market_decile(gp.dropna(subset=["risk"]), "risk")}
    L.info("p15 AUC: %s", res["p15"]["auc_grid"])
    L.info("risk AUC: %s", res["predRisk4H_INSAMPLE"]["auc_grid"])
    L.info("useful: %s", res["S1"]["useful"])
    with open(OUTJ, "w") as f:
        json.dump(res, f, indent=1, default=str)
    L.info("wrote %s", OUTJ)


if __name__ == "__main__":
    main()
