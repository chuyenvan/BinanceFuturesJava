"""S1 RANKING QUALITY — CORRECT MEASURE (đúng horizon 72h + đúng mốc quyết định + test đảo dấu).

PRE-REG: docs/PREREG_S1_RANK_CORRECT_MEASURE.md (commit 69fb2d1). Chạy ĐÚNG MỘT lần, không tune.
Sửa 2 lệch cấu trúc của RESULT_S1_RANK_QUALITY.md (commit 57223a0):
  (i)  S1 train trên nhãn g1lite = 72h, đo lần này ở 72h (so sánh 24h).
  (ii) đo ở MỐC QUYẾT ĐỊNH THẬT (market.bin, levelChange != null = BIG_DOWN), không mọi snapshot 1h.
Tái sử dụng trend_rank_ic.py (load_closes / block_ci / cấu trúc _ic_series).

QUY ƯỚC DẤU: s1 = -score (CAO = tốt). rank_ic xuôi = Spearman(-score, ret) = Spearman(s1, ret);
> 0 = S1 làm đúng. rank_ic ngược = Spearman(score, ret) = -rank_ic xuôi. top-8 xuôi = score THẤP
nhất; top-8 ngược = score CAO nhất.

LUAT LOG REPO: dùng module `logging`, KHÔNG dùng print().
"""
import logging as _logging
import sys as _sys
import json
import os
import numpy as np
import pandas as pd

_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
L = _logging.getLogger("s1correct")


def _p(*a):
    L.info(" ".join(str(x) for x in a))


import trend_rank_ic as T  # reuse: load_closes / block_ci / _ic_series

H = 3600000
MARKET = "/home/ubuntu/simbundle/market.bin"
MS_DOWN_BIG_AVG = np.float32(-0.03157)   # Configs.java:392 (so sánh float32 exact)
HORIZONS = (24, 72)                       # 72h = g1lite horizon (chính); 24h = so sánh lần cũ
TOPK = 8
MIN_N = 10
OUTDIR = T.OUTDIR
os.makedirs(OUTDIR, exist_ok=True)
SEAL_2026 = T.SEAL_2026


def load_decision_points():
    """Đọc market.bin (big-endian), trả các ts 1-phút mà getMarketStatus1M != null (BIG_DOWN),
    giới hạn DEV 2022-01-01 .. 2025-12-31."""
    dt = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])
    a = np.fromfile(MARKET, dtype=dt, offset=4)
    ts = a["ts"].astype(np.int64)
    down = a["down"]                       # float32 gốc
    bd = down < MS_DOWN_BIG_AVG
    t = np.sort(ts[bd])
    lo = pd.Timestamp("2022-01-01").value // 10 ** 6
    hi = pd.Timestamp("2026-01-01").value // 10 ** 6
    t = t[(t >= lo) & (t < hi)]
    return t


def decision_buckets(t_dec):
    """Map mốc 1-phút -> bucket giờ (ctime = ceil(t/H)*H), giữ t_dec sớm nhất mỗi giờ."""
    ctime = (t_dec + H - 1) // H * H
    d = pd.DataFrame({"t_dec": t_dec, "ctime": ctime})
    g = d.groupby("ctime")["t_dec"].min().reset_index()
    return g


def add_forward(df, horizons=HORIZONS):
    """Forward return close(ctime + h*H)/close(ctime) - 1 trên lưới 1h (logic y hệt trend_rank_ic)."""
    ctime = df["ctime"].to_numpy()
    close = df["close"].to_numpy()
    syms = df["sym"].to_numpy()
    n = len(df)
    u, first = np.unique(syms, return_index=True)
    ends = np.append(first[1:], n)
    for h in horizons:
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


def build_cross_sections(df, buckets):
    """Cross-section per bucket: score (ff tới t_dec), s1=-score, ret24/ret72 từ close 1h."""
    sp = pd.read_parquet(T.S1).sort_values(["sym", "ts"]).reset_index(drop=True)
    s_sym = sp["sym"].to_numpy()
    s_ts = sp["ts"].to_numpy()
    s_sc = sp["score"].to_numpy()
    u, first = np.unique(s_sym, return_index=True)
    ends = np.append(first[1:], len(s_sym))
    ts_by = {int(uu): s_ts[f:e] for uu, f, e in zip(u, first, ends)}
    sc_by = {int(uu): s_sc[f:e] for uu, f, e in zip(u, first, ends)}

    rows = []
    for _, b in buckets.iterrows():
        ctime = int(b["ctime"])
        t_dec = int(b["t_dec"])
        sub = df[df["ctime"] == ctime]
        if len(sub) == 0:
            continue
        syms = sub["sym"].to_numpy()
        scores = np.full(len(sub), np.nan)
        for i, sym in enumerate(syms):
            ta = ts_by.get(int(sym))
            if ta is None or len(ta) == 0:
                continue
            idx = np.searchsorted(ta, t_dec, side="right") - 1
            if idx >= 0:
                scores[i] = sc_by[int(sym)][idx]
        sub = sub.copy()
        sub["score"] = scores
        sub["s1"] = -scores
        rows.append(sub[["ctime", "sym", "score", "s1", "ret24", "ret72"]])
    if not rows:
        return pd.DataFrame(columns=["ctime", "sym", "score", "s1", "ret24", "ret72"])
    return pd.concat(rows, ignore_index=True)


def _ic_series(df, f, r, min_n=MIN_N):
    """Spearman rank-IC per-bucket (tái dùng logic _ic_series của trend_rank_ic)."""
    return T._ic_series(df, f, r, min_n=min_n)


def topk_diff(df, r, ascending, k=TOPK, min_n=MIN_N):
    """Per-bucket mean(ret top-k theo score) - mean(ret universe). ascending=True = score thấp nhất (xuôi)."""
    d = df[["ctime", "score", r]].dropna().copy()
    cnt = d.groupby("ctime").size()
    good = cnt[cnt >= max(k, min_n)].index
    d = d[d["ctime"].isin(good)]
    if len(d) == 0:
        return pd.Series(dtype=float)
    d["rank"] = d.groupby("ctime")["score"].rank(method="first", ascending=ascending)
    top = d[d["rank"] <= k].groupby("ctime")[r].mean()
    uni = d.groupby("ctime")[r].mean()
    return (top - uni)


def _year(ms):
    return pd.to_datetime(ms, unit="ms").year


def main():
    _p("=== S1 RANKING QUALITY — CORRECT MEASURE (PRE-REG 69fb2d1) ===")

    t_dec = load_decision_points()
    _p("decision minutes (2022-2025, BIG_DOWN): %d", len(t_dec))
    buckets = decision_buckets(t_dec)
    _p("decision hour buckets: %d", len(buckets))

    df = T.load_closes()
    df = add_forward(df)
    _p("closes: n=%d sym=%d ctime %s -> %s", len(df), df["sym"].nunique(),
       pd.Timestamp(df.ctime.min(), unit="ms"), pd.Timestamp(df.ctime.max(), unit="ms"))

    cs = build_cross_sections(df, buckets)
    _p("cross-section rows (bucket x coin): %d | buckets co du lieu: %d",
       len(cs), cs.ctime.nunique())

    # coverage theo năm (decision minutes + buckets)
    dyr = pd.DataFrame({"t_dec": t_dec, "year": [_year(x) for x in t_dec]})
    cov_year = {}
    for y in (2022, 2023, 2024, 2025):
        sub = dyr[dyr.year == y]
        cov_year[y] = dict(n_decision_min=int(len(sub)),
                           n_buckets=int(sub.assign(c=(sub.t_dec + H - 1) // H * H).c.nunique()))
    _p("coverage theo nam (decision_min / bucket): %s",
       {y: f"{v['n_decision_min']}/{v['n_buckets']}" for y, v in cov_year.items()})

    results = {}
    for h in HORIZONS:
        r = f"ret{h}"
        d = cs[["ctime", "score", "s1", r]].dropna().copy()

        # rank_ic xuôi = Spearman(s1, ret) = Spearman(-score, ret)
        ic_f = _ic_series(d, "s1", r)
        ci_f = T.block_ci(ic_f)
        ci_f["n_snap"] = int(len(ic_f))
        # rank_ic ngược = Spearman(score, ret)
        ic_i = _ic_series(d, "score", r)
        ci_i = T.block_ci(ic_i)
        ci_i["n_snap"] = int(len(ic_i))

        # top-8 xuôi (score thấp nhất) và ngược (score cao nhất)
        tf = topk_diff(d, r, ascending=True)
        cf = T.block_ci(tf)
        cf["n_snap"] = int(len(tf))
        ti = topk_diff(d, r, ascending=False)
        cih = T.block_ci(ti)
        cih["n_snap"] = int(len(ti))

        results[h] = {
            "rank_ic_forward": ci_f,      # Spearman(-score, ret)
            "rank_ic_inverted": ci_i,     # Spearman(score, ret)  (đảo dấu)
            "top8_forward_vs_universe": cf,
            "top8_inverted_vs_universe": cih,
            "universe_mean_ret": float(d[r].mean()),
            "median_coins_per_bucket": float(d.groupby("ctime").size().median()) if len(d) else float("nan"),
        }
        _p("h=%2dh xuoi  rankIC=%+.5f CI[%+.5f,%+.5f] snap=%d blocks=%d zero=%s",
           h, ci_f["mean"], ci_f["lo"], ci_f["hi"], ci_f["n_snap"], ci_f["n_blocks"], ci_f["contains_zero"])
        _p("h=%2dh nguoc rankIC=%+.5f CI[%+.5f,%+.5f] snap=%d blocks=%d zero=%s",
           h, ci_i["mean"], ci_i["lo"], ci_i["hi"], ci_i["n_snap"], ci_i["n_blocks"], ci_i["contains_zero"])
        _p("h=%2dh top8 xuoi  diff=%+.6f CI[%+.6f,%+.6f] snap=%d zero=%s",
           h, cf["mean"], cf["lo"], cf["hi"], cf["n_snap"], cf["contains_zero"])
        _p("h=%2dh top8 nguoc diff=%+.6f CI[%+.6f,%+.6f] snap=%d zero=%s",
           h, cih["mean"], cih["lo"], cih["hi"], cih["n_snap"], cih["contains_zero"])

    out = {
        "meta": {
            "pre_reg_commit": "69fb2d1",
            "market": MARKET, "ms_down_big_avg": float(MS_DOWN_BIG_AVG),
            "closes": T.CLOSES, "s1": T.S1,
            "seed": T.SEED, "nrep": T.NREP, "block_h": T.BLOCK_H,
            "inflate": T.CI_INFLATE, "min_n": MIN_N, "topk": TOPK,
            "horizons": list(HORIZONS),
            "g1lite": "maxFav_72h>=0.05 ? maxFav_72h-min(0.5*maxFav_72h,0.08) : retEnd_72h (ledger.py:40)",
            "sign_convention": "s1=-score; rank_ic_forward=Spearman(s1,ret)=Spearman(-score,ret) (>0 = dung); "
                               "rank_ic_inverted=Spearman(score,ret); top8_forward=score thap nhat; "
                               "top8_inverted=score cao nhat.",
            "n_decision_min": int(len(t_dec)),
            "n_decision_buckets": int(len(buckets)),
        },
        "coverage_by_year": cov_year,
        "results": results,
    }
    jp = os.path.join(OUTDIR, "s1_correct_measure.json")
    with open(jp, "w") as f:
        json.dump(out, f, indent=2, default=str)
    _p("wrote %s", jp)

    rows = []
    for h in HORIZONS:
        R = results[h]
        rows.append(dict(horizon_h=h, metric="rank_ic_forward",
                         value=R["rank_ic_forward"]["mean"], lo=R["rank_ic_forward"]["lo"],
                         hi=R["rank_ic_forward"]["hi"], n_snap=R["rank_ic_forward"]["n_snap"],
                         contains_zero=R["rank_ic_forward"]["contains_zero"]))
        rows.append(dict(horizon_h=h, metric="rank_ic_inverted",
                         value=R["rank_ic_inverted"]["mean"], lo=R["rank_ic_inverted"]["lo"],
                         hi=R["rank_ic_inverted"]["hi"], n_snap=R["rank_ic_inverted"]["n_snap"],
                         contains_zero=R["rank_ic_inverted"]["contains_zero"]))
        rows.append(dict(horizon_h=h, metric="top8_forward_vs_universe",
                         value=R["top8_forward_vs_universe"]["mean"], lo=R["top8_forward_vs_universe"]["lo"],
                         hi=R["top8_forward_vs_universe"]["hi"], n_snap=R["top8_forward_vs_universe"]["n_snap"],
                         contains_zero=R["top8_forward_vs_universe"]["contains_zero"]))
        rows.append(dict(horizon_h=h, metric="top8_inverted_vs_universe",
                         value=R["top8_inverted_vs_universe"]["mean"], lo=R["top8_inverted_vs_universe"]["lo"],
                         hi=R["top8_inverted_vs_universe"]["hi"], n_snap=R["top8_inverted_vs_universe"]["n_snap"],
                         contains_zero=R["top8_inverted_vs_universe"]["contains_zero"]))
    csvp = os.path.join(OUTDIR, "s1_correct_measure.csv")
    pd.DataFrame(rows).to_csv(csvp, index=False)
    _p("wrote %s", csvp)
    _p("=== DONE ===")


if __name__ == "__main__":
    main()
