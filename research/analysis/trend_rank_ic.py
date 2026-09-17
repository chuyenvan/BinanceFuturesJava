"""TREND/VOL RANK-IC SCREENING (STANDALONE, CRYPTO DEV).

PRE-REG: docs/PREREG_TREND_RANK_IC.md (commit e26e3c3). Chay DUNG MOT LAN, khong tune.
Cau hoi: tap dac trung trend/vol (tinh than holdout) co xep hang duoc coin theo
forward return khong, tren crypto DEV? Do Spearman rank-IC cross-section moi snapshot
1h + bootstrap block-72h (x1.21, 2000 rep, seed 20260905). Doi chung S1 (pred_s1a2x1).

LUAT LOG REPO: dung module `logging`, KHONG dung print().
"""
import logging as _logging
import sys as _sys
import json
import os
import numpy as np
import pandas as pd

_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
L = _logging.getLogger("trendic")


def _p(*a):
    L.info(" ".join(str(x) for x in a))


H = 3600000
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
S1 = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
OUTDIR = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/out"
os.makedirs(OUTDIR, exist_ok=True)

SEAL_2026 = 1767225600000          # 2026-01-01 00:00 UTC (open_time) -> LOAI
DECISION_MAX = 1767139200000       # 2025-12-31 00:00 UTC (snapshot toi da)
MA_LBS = (50, 100, 200)
MOM_LB = 168
VOL_LB = 168
WARMUP = 200
HORIZONS = (1, 4, 24)
MIN_N = 10
BLOCK_H = 72
NREP = 2000
SEED = 20260905
CI_INFLATE = 1.21


def load_closes():
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64)
    sym = a["sym"].astype(np.int64)
    c = a["c"].astype(np.float64)
    m = ts < SEAL_2026
    ts, sym, c = ts[m], sym[m], c[m]
    ctime = ts + H                     # close_time = open_time + 1h (quy uoc causal)
    df = pd.DataFrame({"ctime": ctime, "sym": sym, "close": c})
    df = df.drop_duplicates(["sym", "ctime"], keep="first")
    df = df.sort_values(["sym", "ctime"]).reset_index(drop=True)
    return df


def add_features(df):
    close = df["close"].to_numpy()
    n = len(df)
    trend = np.full(n, np.nan)
    mom = np.full(n, np.nan)
    vol = np.full(n, np.nan)
    uniq, first = np.unique(df["sym"].to_numpy(), return_index=True)
    ends = np.append(first[1:], n)
    for s, e in zip(first, ends):
        cc = close[s:e]
        ln = e - s
        if ln < 2:
            continue
        sig = np.zeros(ln)
        for k in MA_LBS:
            sma = pd.Series(cc).rolling(k, min_periods=k).mean().to_numpy()
            sig += (cc > sma).astype(np.float64)
        sig = sig / len(MA_LBS)
        sig[np.arange(ln) < (WARMUP - 1)] = np.nan
        trend[s:e] = sig
        if ln > MOM_LB:
            mom[s + MOM_LB:e] = cc[MOM_LB:] / cc[:-MOM_LB] - 1.0
        ret = np.full(ln, np.nan)
        ret[1:] = cc[1:] / cc[:-1] - 1.0
        vol[s:e] = pd.Series(ret).rolling(VOL_LB, min_periods=VOL_LB).std().to_numpy()
    df["trend"] = trend
    df["mom"] = mom
    df["vol"] = vol
    return df


def add_forward(df):
    ctime = df["ctime"].to_numpy()
    close = df["close"].to_numpy()
    syms = df["sym"].to_numpy()
    n = len(df)
    u, first = np.unique(syms, return_index=True)
    ends = np.append(first[1:], n)
    for h in HORIZONS:
        fwd = np.full(n, np.nan)
        for f, e in zip(first, ends):
            ct = ctime[f:e]
            cl = close[f:e]
            m = e - f
            if m < 2:
                continue
            tgt = ct + h * H
            idx = np.searchsorted(ct, tgt, side="left")
            ok = (idx < m) & (ct[np.minimum(idx, m - 1)] == tgt)
            if ok.any():
                fwd[f + np.where(ok)[0]] = cl[idx[ok]] / cl[ok] - 1.0
        df[f"ret{h}"] = fwd
    return df


def add_s1(df):
    sp = pd.read_parquet(S1)
    sp = sp.sort_values(["sym", "ts"]).reset_index(drop=True)
    s_sym = sp["sym"].to_numpy()
    s_ts = sp["ts"].to_numpy()
    s_sc = sp["score"].to_numpy()
    u, first = np.unique(s_sym, return_index=True)
    ends = np.append(first[1:], len(s_sym))
    ts_by = {int(uu): s_ts[f:e] for uu, f, e in zip(u, first, ends)}
    sc_by = {int(uu): s_sc[f:e] for uu, f, e in zip(u, first, ends)}

    syms = df["sym"].to_numpy()
    ctime = df["ctime"].to_numpy()
    n = len(df)
    s1 = np.full(n, np.nan)
    du, dfirst = np.unique(syms, return_index=True)
    dends = np.append(dfirst[1:], n)
    for uu, f, e in zip(du, dfirst, dends):
        ta = ts_by.get(int(uu))
        if ta is None or len(ta) == 0:
            continue
        ct = ctime[f:e]
        idx = np.searchsorted(ta, ct, side="right") - 1
        valid = idx >= 0
        vals = np.full(e - f, np.nan)
        vals[valid] = sc_by[int(uu)][idx[valid]]
        s1[f:e] = -vals                     # doi dau: cao = tot
    df["s1"] = s1
    return df


def _ic_series(df, f, r, min_n=MIN_N, pearson=False):
    d = df[["ctime", f, r]].dropna().copy()
    if len(d) == 0:
        return pd.Series(dtype=float)
    if pearson:
        d["cf"] = d[f] - d.groupby("ctime")[f].transform("mean")
        d["cr"] = d[r] - d.groupby("ctime")[r].transform("mean")
    else:
        d["cf"] = d.groupby("ctime")[f].rank(method="average")
        d["cr"] = d.groupby("ctime")[r].rank(method="average")
        d["cf"] = d["cf"] - d.groupby("ctime")["cf"].transform("mean")
        d["cr"] = d["cr"] - d.groupby("ctime")["cr"].transform("mean")
    d["cov"] = d["cf"] * d["cr"]
    d["vf"] = d["cf"] ** 2
    d["vr"] = d["cr"] ** 2
    g = d.groupby("ctime").agg(cov=("cov", "sum"), vf=("vf", "sum"),
                               vr=("vr", "sum"), n=("cf", "size"))
    g = g[g["n"] >= min_n]
    return g["cov"] / np.sqrt(g["vf"] * g["vr"])


def block_ci(ic):
    if len(ic) == 0:
        return dict(mean=float("nan"), lo=float("nan"), hi=float("nan"),
                    n_snap=0, n_blocks=0, contains_zero=True)
    ic = ic.dropna()
    blk = ic.index // (BLOCK_H * H)
    gb = ic.groupby(blk).mean()
    cnt = ic.groupby(blk).size()
    nb = len(gb)
    rng = np.random.default_rng(SEED)
    obs = float(ic.mean())
    bv = gb.to_numpy()
    cv = cnt.to_numpy()
    draws = np.empty(NREP)
    for i in range(NREP):
        pick = rng.integers(0, nb, size=nb)
        w = cv[pick]
        m = bv[pick]
        draws[i] = np.sum(m * w) / np.sum(w)
    lo, hi = np.percentile(draws, [2.5, 97.5])
    lo = obs - (obs - lo) * CI_INFLATE
    hi = obs + (hi - obs) * CI_INFLATE
    return dict(mean=obs, lo=float(lo), hi=float(hi),
                n_snap=int(len(ic)), n_blocks=int(nb),
                contains_zero=bool(lo <= 0.0 <= hi))


def ncoins_series(df, r):
    d = df[["ctime", r]].dropna()
    return d.groupby("ctime").size()


def main():
    _p("=== TREND/VOL RANK-IC (PRE-REG e26e3c3) ===")
    df = load_closes()
    _p("closes sau loai 2026: n=%d sym=%d ctime %s -> %s",
       len(df), df["sym"].nunique(),
       pd.Timestamp(df.ctime.min(), unit="ms"), pd.Timestamp(df.ctime.max(), unit="ms"))
    df = add_features(df)
    _p("features: trend nnz=%.3f mom nnz=%.3f vol nnz=%.3f",
       df.trend.notna().mean(), df.mom.notna().mean(), df.vol.notna().mean())
    df = add_forward(df)
    df = add_s1(df)
    df = df[df["ctime"] <= DECISION_MAX].copy()
    _p("snapshots (ctime <= 2025-12-31 00:00): %d", df.ctime.nunique())

    feat = {"trend": "trend", "mom": "mom", "vol": "vol", "S1": "s1"}
    results = {}
    snap_count = {}
    for h in HORIZONS:
        r = f"ret{h}"
        results[h] = {}
        snap_count[h] = int(df[df[r].notna()].ctime.nunique())
        for nm, fc in feat.items():
            ic = _ic_series(df, fc, r)
            pc = _ic_series(df, fc, r, pearson=True)
            ci = block_ci(ic)
            ci["pearson_mean"] = float(pc.mean()) if len(pc) else float("nan")
            nc = ncoins_series(df, r)
            ci["ncoins_median"] = float(nc.median()) if len(nc) else float("nan")
            ci["ncoins_mean"] = round(float(nc.mean()), 1) if len(nc) else float("nan")
            results[h][nm] = ci
            _p("h=%2dh %-5s rankIC=%+.5f CI[%+.5f,%+.5f] pearson=%+.5f snap=%d coins_med=%d",
               h, nm, ci["mean"], ci["lo"], ci["hi"], ci["pearson_mean"],
               ci["n_snap"], ci["ncoins_median"])

    out = {"meta": {"closes": CLOSES, "s1": S1, "seed": SEED, "nrep": NREP,
                    "block_h": BLOCK_H, "inflate": CI_INFLATE, "min_n": MIN_N,
                    "horizons": HORIZONS, "snapshots_per_horizon": snap_count,
                    "ma_lbs": MA_LBS, "mom_lb": MOM_LB, "vol_lb": VOL_LB,
                    "warmup": WARMUP},
           "results": results}
    jp = os.path.join(OUTDIR, "trend_rank_ic.json")
    with open(jp, "w") as f:
        json.dump(out, f, indent=2)
    _p("wrote %s", jp)

    rows = []
    for h in HORIZONS:
        for nm, ci in results[h].items():
            rows.append(dict(horizon_h=h, feature=nm,
                             rankIC_mean=round(ci["mean"], 5),
                             rankIC_lo=round(ci["lo"], 5),
                             rankIC_hi=round(ci["hi"], 5),
                             pearson_mean=round(ci["pearson_mean"], 5),
                             n_snap=ci["n_snap"], n_blocks=ci["n_blocks"],
                             ncoins_median=ci["ncoins_median"],
                             contains_zero=ci["contains_zero"]))
    csvp = os.path.join(OUTDIR, "trend_rank_ic.csv")
    pd.DataFrame(rows).to_csv(csvp, index=False)
    _p("wrote %s", csvp)
    _p("=== DONE ===")


if __name__ == "__main__":
    main()
