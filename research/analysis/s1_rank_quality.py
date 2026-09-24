"""S1 RANKING QUALITY (STANDALONE, CRYPTO DEV) — lan dau do TRUC TIEP chat luong xep hang cua S1.

PRE-REG: docs/prereg/PREREG_S1_RANK_QUALITY.md (commit da0ea2f). Chay DUNG MOT lan, khong tune.
Tai su dung data-loading da xac minh trong trend_rank_ic.py (cung binary close 1h + S1
parquet). Cau hoi: "S1 xep hang coin tot den dau, manh o dau, yeu o dau?"

QUY UOC DAU (khoa): rank_ic = Spearman(-score, fwd_return) = Spearman(pred, ret).
score THAP = tot => -score CAO = tot => rank_ic DUONG = S1 lam dung viec.
Top-K = K coin -score cao nhat (= K score thap nhat), K = SELECTOR_RANK_TOPK = 8.

LUAT LOG REPO: dung module `logging`, KHONG dung print().
"""
import logging as _logging
import sys as _sys
import json
import os
import numpy as np
import pandas as pd

_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
L = _logging.getLogger("s1rankq")


def _p(*a):
    L.info(" ".join(str(x) for x in a))


import trend_rank_ic as T  # reuse: load_closes / add_forward / add_s1 / block_ci / _ic_series

OUTDIR = T.OUTDIR
os.makedirs(OUTDIR, exist_ok=True)

HORIZONS = T.HORIZONS          # (1, 4, 24)
MIN_N = T.MIN_N                # 10
TOPK = 8                       # SELECTOR_RANK_TOPK
QUINTILE_K = 5
YEARS = (2022, 2023, 2024, 2025)


def _year(ms):
    return pd.to_datetime(ms, unit="ms").year


def _block_ci(series):
    """Reuse block-72h bootstrap (x1.21, 2000 rep, seed). series indexed by ctime ms."""
    return T.block_ci(series)


def rank_ic_series(df, r, min_n=MIN_N):
    """Per-snapshot Spearman(-score, ret). Indexed by ctime (ms)."""
    return T._ic_series(df, "s1", r, min_n=min_n)


def topk_diff_series(df, r, k=TOPK, min_n=MIN_N):
    """Per-snapshot: mean(ret top-k by -score) - mean(ret universe). Indexed by ctime."""
    d = df[["ctime", "s1", r]].dropna().copy()
    cnt = d.groupby("ctime").size()
    good = cnt[cnt >= max(k, min_n)].index
    d = d[d["ctime"].isin(good)]
    if len(d) == 0:
        return pd.Series(dtype=float)
    # rank by -score (s1) descending -> top k = lowest score
    d["rank"] = d.groupby("ctime")["s1"].rank(method="first", ascending=False)
    top = d[d["rank"] <= k].groupby("ctime")[r].mean()
    uni = d.groupby("ctime")[r].mean()
    return (top - uni).reindex(uni.index)


def quintile_table(df, r, min_n=MIN_N, q=QUINTILE_K):
    """Per-snapshot mean ret per quintile of -score; return (long mean table, spread series)."""
    d = df[["ctime", "s1", r]].dropna().copy()
    cnt = d.groupby("ctime").size()
    good = cnt[cnt >= max(q, min_n)].index
    d = d[d["ctime"].isin(good)]
    if len(d) == 0:
        return pd.DataFrame(), pd.Series(dtype=float)
    # rank by s1 ascending within snapshot (1 = worst, n = best), unique via first
    d["rrank"] = d.groupby("ctime")["s1"].rank(method="first")
    # qcut on unique ranks -> 5 equal-count bins, labels 0..4 (0 = worst, 4 = best)
    d["q"] = d.groupby("ctime")["rrank"].transform(
        lambda x: pd.qcut(x, q, labels=False))
    # per (snapshot, q) mean ret
    g = d.groupby(["ctime", "q"])[r].mean().reset_index()
    # long-table: mean across snapshots per q
    qmean = g.groupby("q")[r].mean()
    # spread Q_best - Q_worst (q=4 - q=0) per snapshot
    piv = g.pivot(index="ctime", columns="q", values=r)
    spread = piv.get(4, np.nan) - piv.get(0, np.nan)
    return qmean, spread.dropna()


def main():
    _p("=== S1 RANKING QUALITY (PRE-REG da0ea2f) ===")
    df = T.load_closes()
    _p("closes sau loai 2026: n=%d sym=%d ctime %s -> %s",
       len(df), df["sym"].nunique(),
       pd.Timestamp(df.ctime.min(), unit="ms"), pd.Timestamp(df.ctime.max(), unit="ms"))
    df = T.add_forward(df)
    df = T.add_s1(df)                 # s1 = -score (CAO = tot)
    df = df[df["ctime"] <= T.DECISION_MAX].copy()
    _p("s1 non-null rows: %d (%.3f), snapshots(co s1) <=2025: %d",
       df.s1.notna().sum(), df.s1.notna().mean(), df[df.s1.notna()].ctime.nunique())

    results = {}
    coverage = {}
    for h in HORIZONS:
        r = f"ret{h}"
        ic = rank_ic_series(df, r)
        ci = _block_ci(ic)
        ci["n_snap"] = int(len(ic))
        results.setdefault("rank_ic", {})[h] = ci
        _p("h=%2dh rankIC=%+.5f CI[%+.5f,%+.5f] snap=%d blocks=%d zero=%s",
           h, ci["mean"], ci["lo"], ci["hi"], ci["n_snap"], ci["n_blocks"],
           ci["contains_zero"])

        # per-year
        per_year = {}
        for y in YEARS:
            sub = ic[ic.index.map(lambda t: _year(t)) == y]
            if len(sub) < 20:
                per_year[y] = dict(mean=float("nan"), lo=float("nan"), hi=float("nan"),
                                   n_snap=int(len(sub)))
                continue
            py = _block_ci(sub)
            per_year[y] = dict(mean=py["mean"], lo=py["lo"], hi=py["hi"],
                               n_snap=int(len(sub)))
            _p("  year=%d rankIC=%+.5f CI[%+.5f,%+.5f] snap=%d",
               y, py["mean"], py["lo"], py["hi"], len(sub))
        results.setdefault("rank_ic_year", {})[h] = per_year

        # quintile
        qmean, spread = quintile_table(df, r)
        spr_ci = _block_ci(spread) if len(spread) else dict(mean=float("nan"), lo=float("nan"), hi=float("nan"), n_snap=0)
        results.setdefault("quintile", {})[h] = {
            "mean_ret_per_q": {int(k): float(v) for k, v in qmean.items()},
            "spread_qbest_qworst": spr_ci,
        }
        _p("  h=%2dh quintile mean_ret: %s", {int(k): round(float(v), 6) for k, v in qmean.items()})
        _p("  h=%2dh spread Qbest-Qworst = %+.6f CI[%+.6f,%+.6f] snap=%d",
           h, spr_ci["mean"], spr_ci["lo"], spr_ci["hi"], spr_ci["n_snap"])

        # top-K vs universe
        diff = topk_diff_series(df, r)
        dci = _block_ci(diff)
        results.setdefault("topk", {})[h] = {
            "k": TOPK, "diff_mean": dci["mean"], "diff_lo": dci["lo"],
            "diff_hi": dci["hi"], "n_snap": int(len(diff)),
            "contains_zero": dci["contains_zero"],
            "universe_mean_ret": float(df[df[r].notna()][r].mean()),
        }
        _p("  h=%2dh top-%d vs universe diff=%+.6f CI[%+.6f,%+.6f] snap=%d zero=%s",
           h, TOPK, dci["mean"], dci["lo"], dci["hi"], len(diff), dci["contains_zero"])

    # coverage per year (snapshots + coins with S1)
    df_s1 = df[df.s1.notna()]
    df_s1 = df_s1.assign(year=_year(df_s1.ctime.to_numpy()))
    cov = {}
    for y in YEARS:
        sy = df_s1[df_s1.year == y]
        cov[y] = dict(n_snap=int(sy.ctime.nunique()),
                      n_coins=int(sy.sym.nunique()),
                      median_coins_per_snap=float(sy.groupby("ctime").size().median())
                      if len(sy) else float("nan"))
    coverage["s1_by_year"] = cov

    out = {
        "meta": {
            "closes": T.CLOSES, "s1": T.S1, "pre_reg_commit": "da0ea2f",
            "seed": T.SEED, "nrep": T.NREP, "block_h": T.BLOCK_H,
            "inflate": T.CI_INFLATE, "min_n": MIN_N, "topk": TOPK,
            "quintile_k": QUINTILE_K, "horizons": list(HORIZONS),
            "years": list(YEARS),
            "sign_convention": "rank_ic=Spearman(-score,ret)=Spearman(pred,ret); >0 = S1 dung",
        },
        "coverage": coverage,
        "results": results,
    }
    jp = os.path.join(OUTDIR, "s1_rank_quality.json")
    with open(jp, "w") as f:
        json.dump(out, f, indent=2, default=str)
    _p("wrote %s", jp)

    # CSV rows
    rows = []
    for h in HORIZONS:
        r = f"ret{h}"
        ci = results["rank_ic"][h]
        rows.append(dict(kind="rank_ic", horizon_h=h, metric="mean", value=ci["mean"],
                         lo=ci["lo"], hi=ci["hi"], n_snap=ci["n_snap"],
                         contains_zero=ci["contains_zero"]))
        for y in YEARS:
            py = results["rank_ic_year"][h][y]
            rows.append(dict(kind="rank_ic_year", horizon_h=h, metric=f"year_{y}",
                             value=py["mean"], lo=py["lo"], hi=py["hi"],
                             n_snap=py["n_snap"],
                             contains_zero=bool(py["lo"] <= 0 <= py["hi"])
                             if not (py["lo"] != py["lo"]) else True))
        t = results["topk"][h]
        rows.append(dict(kind="topk_vs_universe", horizon_h=h, metric=f"diff_top{TOPK}_uni",
                         value=t["diff_mean"], lo=t["diff_lo"], hi=t["diff_hi"],
                         n_snap=t["n_snap"], contains_zero=t["contains_zero"]))
        for qi, v in results["quintile"][h]["mean_ret_per_q"].items():
            rows.append(dict(kind="quintile_mean_ret", horizon_h=h, metric=f"q{qi}",
                             value=v, lo=None, hi=None, n_snap=None, contains_zero=None))
        sq = results["quintile"][h]["spread_qbest_qworst"]
        rows.append(dict(kind="quintile_spread", horizon_h=h, metric="spread_qbest_qworst",
                         value=sq["mean"], lo=sq["lo"], hi=sq["hi"],
                         n_snap=sq["n_snap"],
                         contains_zero=bool(sq["lo"] <= 0 <= sq["hi"])
                         if not (sq["lo"] != sq["lo"]) else True))
    csvp = os.path.join(OUTDIR, "s1_rank_quality.csv")
    pd.DataFrame(rows).to_csv(csvp, index=False)
    _p("wrote %s", csvp)
    _p("=== DONE ===")


if __name__ == "__main__":
    main()
