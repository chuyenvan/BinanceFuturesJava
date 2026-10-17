#!/usr/bin/env python3
"""GATE_VZ feature builder (PREREG_GATE_VZ.md ee97237b muc 3). Dong T dung nen open time <= T-1m; metrics ts <= T-10m.
Usage: python3 gvz_feat.py kline 2021-01 2025-12 | met | merge
Out: ~/claude_master/gvz/feat/kl-YYYY-MM.parquet, met5.parquet, vz_feat.parquet
"""
import glob
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("gvzf")
OUT = "/home/ubuntu/claude_master/gvz/feat"
K21 = "/home/ubuntu/claude_master/gvz/k2021"
KRAW = "/home/ubuntu/vz_e1/raw"
MET = "/home/ubuntu/claude_master/rex/met"
MIN = 60_000
LOOK = 1500                      # phut lookback tu thang truoc (>= 1440 + 1 + du)
KCOLS = ["ts", "sym", "quote_volume", "taker_buy_quote", "n_trades"]
VZA = ["vzTkr5", "vzTkr15", "vzTkr60", "vzTkr240", "vzTkrBtc15", "vzTkrMed15", "vzQvR60", "vzNtR15"]
VZB = ["vzOiC1h", "vzOiC4h", "vzOiC24h", "vzLsTop", "vzLsAcc"]


def kpath(ym):
    p = os.path.join(K21 if ym < "2021-12" else KRAW, "kline1m-%s.parquet" % ym)
    assert os.path.exists(p), p
    return p


def load_k(ym):
    d = pd.read_parquet(kpath(ym), columns=KCOLS)
    d["ts"] = d["ts"].astype(np.int64)
    assert d["ts"].max() < 1e13 and d["ts"].min() > 1e12, "ts khong phai ms"
    d = d[d["quote_volume"] > 0]
    d = d.drop_duplicates(["sym", "ts"], keep="last")
    return d


def roll_prev(a, w):
    """Tong w phan tu KET THUC tai i-1 (khong gom i). a: (n,) hoac (n,m), NaN=0 da xu ly."""
    c = np.cumsum(a, axis=0, dtype=np.float64)
    c = np.concatenate([np.zeros((1,) + a.shape[1:]), c], axis=0)        # c[k] = sum a[0:k]
    n = a.shape[0]
    i = np.arange(n)
    hi = i                                                                  # sum a[i-w : i]
    lo = i - w
    out = c[hi] - c[np.clip(lo, 0, None)]
    out[lo < 0] = np.nan
    return out


def kline_month(ym):
    prev = (pd.Period(ym) - 1).strftime("%Y-%m")
    parts = []
    if prev >= "2021-01":
        p = load_k(prev)
        parts.append(p[p["ts"] >= p["ts"].max() - LOOK * MIN])
    cur = load_k(ym)
    parts.append(cur)
    d = pd.concat(parts, ignore_index=True)
    t0 = pd.Timestamp(ym + "-01").value // 10**6
    t1 = pd.Timestamp((pd.Period(ym) + 1).strftime("%Y-%m") + "-01").value // 10**6
    g0 = d["ts"].min()
    grid = np.arange(g0, t1, MIN, dtype=np.int64)
    n = len(grid)
    ix = ((d["ts"].to_numpy() - g0) // MIN).astype(np.int64)
    assert ((d["ts"].to_numpy() - g0) % MIN == 0).all(), "ts lech phut"
    qv = np.bincount(ix, d["quote_volume"].to_numpy(), n)
    tb = np.bincount(ix, d["taker_buy_quote"].to_numpy(), n)
    nt = np.bincount(ix, d["n_trades"].to_numpy().astype(np.float64), n)
    f = {}
    for w in (5, 15, 60, 240):
        q, b = roll_prev(qv, w), roll_prev(tb, w)
        f["vzTkr%d" % w] = np.where(q > 0, b / np.where(q > 0, q, 1), np.nan)
    bt = d[d["sym"] == "BTCUSDT"]
    bix = ((bt["ts"].to_numpy() - g0) // MIN).astype(np.int64)
    bq = roll_prev(np.bincount(bix, bt["quote_volume"].to_numpy(), n), 15)
    bb = roll_prev(np.bincount(bix, bt["taker_buy_quote"].to_numpy(), n), 15)
    f["vzTkrBtc15"] = np.where(bq > 0, bb / np.where(bq > 0, bq, 1), np.nan)
    syms, sj = np.unique(d["sym"].to_numpy(), return_inverse=True)
    m = len(syms)
    Q = np.zeros((n, m), np.float64)
    B = np.zeros((n, m), np.float64)
    np.add.at(Q, (ix, sj), d["quote_volume"].to_numpy())
    np.add.at(B, (ix, sj), d["taker_buy_quote"].to_numpy())
    Q15, B15 = roll_prev(Q, 15), roll_prev(B, 15)
    del Q, B
    with np.errstate(invalid="ignore", divide="ignore"):
        R = np.where(Q15 >= 10_000.0, B15 / Q15, np.nan)
    del Q15, B15
    allnan = np.isnan(R).all(axis=1)
    med = np.full(n, np.nan)
    med[~allnan] = np.nanmedian(R[~allnan], axis=1)
    f["vzTkrMed15"] = med
    del R
    q60, q1440 = roll_prev(qv, 60), roll_prev(qv, 1440)
    n15, n1440 = roll_prev(nt, 15), roll_prev(nt, 1440)
    with np.errstate(invalid="ignore", divide="ignore"):
        f["vzQvR60"] = np.log(q60 / (q1440 / 24.0))
        f["vzNtR15"] = np.log(n15 / (n1440 / 96.0))
    out = pd.DataFrame({"timestamp": grid, **{k: f[k].astype(np.float32) for k in VZA}})
    out = out[(out["timestamp"] >= t0) & (out["timestamp"] < t1)]
    for k in VZA:
        out.loc[~np.isfinite(out[k]), k] = np.nan
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "kl-%s.parquet" % ym)
    out.to_parquet(p, index=False)
    log.info("KL %s rows=%d syms=%d nan%%=%s", ym, len(out), m,
             {k: round(100 * float(out[k].isna().mean()), 2) for k in VZA})


def kline(a, b):
    for ym in pd.period_range(a, b, freq="M").strftime("%Y-%m"):
        if os.path.exists(os.path.join(OUT, "kl-%s.parquet" % ym)):
            log.info("KL %s da co", ym)
            continue
        kline_month(ym)


def met():
    # CHI 2021-2025 (pre-reg: 2026 khong doc toi buoc HO); doc tung nam, giu mang gon (RAM Oracle 23G)
    fs = [MET + "/metrics5m-%d.parquet" % y for y in range(2021, 2026)]
    log.info("met files %s", [os.path.basename(x) for x in fs])
    parts, symset = [], set()
    for x in fs:
        e = pd.read_parquet(x, columns=["ts", "sym", "oi_value", "toptrader_ls_sum", "ls_cnt"])
        e["sym"] = e["sym"].astype(str)
        e["g"] = (e["ts"].astype(np.int64) // 300_000) * 300_000
        e = e.sort_values(["sym", "ts"]).drop_duplicates(["sym", "g"], keep="last")
        e = e[np.isfinite(e["oi_value"]) & (e["oi_value"] > 0)]
        symset |= set(e["sym"].unique())
        parts.append((e["g"].to_numpy(np.int64), e["sym"].to_numpy(), e["oi_value"].to_numpy(np.float32),
                      e["toptrader_ls_sum"].to_numpy(np.float32), e["ls_cnt"].to_numpy(np.float32)))
        log.info("met %s rows=%d", os.path.basename(x), len(e))
        del e
    syms = np.array(sorted(symset))
    sidx = {s: i for i, s in enumerate(syms)}
    gg = np.concatenate([p[0] for p in parts])
    sj = np.concatenate([np.fromiter((sidx[s] for s in p[1]), np.int32, len(p[1])) for p in parts])
    ov = np.concatenate([p[2] for p in parts])
    lsv = {"toptrader_ls_sum": np.concatenate([p[3] for p in parts]), "ls_cnt": np.concatenate([p[4] for p in parts])}
    del parts
    g0, g1 = int(gg.min()), int(gg.max())
    grid = np.arange(g0, g1 + 300_000, 300_000, dtype=np.int64)
    n = len(grid)
    gi = ((gg - g0) // 300_000).astype(np.int64)
    log.info("met rows=%d grid=%d syms=%d", len(gg), n, len(syms))
    V = np.full((n, len(syms)), np.nan, np.float32)
    V[gi, sj] = ov
    f = {"g": grid}
    fin = np.isfinite(V)
    for name, k in (("vzOiC1h", 12), ("vzOiC4h", 48), ("vzOiC24h", 288)):
        num = np.zeros(n)
        den = np.zeros(n)
        for a in range(k, n, 20000):                       # theo khoi hang, tranh mang tam (n,m) lon
            b = min(n, a + 20000)
            cur, prv = V[a:b], V[a - k:b - k]
            both = fin[a:b] & fin[a - k:b - k]
            num[a:b] = np.where(both, cur, 0).sum(1, dtype=np.float64)
            den[a:b] = np.where(both, prv, 0).sum(1, dtype=np.float64)
        with np.errstate(invalid="ignore", divide="ignore"):
            f[name] = np.where((num > 0) & (den > 0), np.log(num / np.where(den > 0, den, 1)), np.nan)
    big = fin & (V >= 1e6)
    del fin
    for name, col in (("vzLsTop", "toptrader_ls_sum"), ("vzLsAcc", "ls_cnt")):
        L = np.full((n, len(syms)), np.nan, np.float32)
        L[gi, sj] = lsv[col]
        L = np.where(big & np.isfinite(L) & (L > 0), L, np.nan)
        an = np.isnan(L).all(1)
        md = np.full(n, np.nan)
        md[~an] = np.nanmedian(L[~an], axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            f[name] = np.log(md)
        del L
    out = pd.DataFrame({k: (v.astype(np.float32) if k != "g" else v) for k, v in f.items()})
    out.to_parquet(os.path.join(OUT, "met5.parquet"), index=False)
    log.info("MET grid %s..%s nan%%=%s", pd.to_datetime(g0, unit="ms"), pd.to_datetime(g1, unit="ms"),
             {k: round(100 * float(out[k].isna().mean()), 2) for k in VZB})


def merge():
    kl = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(OUT + "/kl-*.parquet"))], ignore_index=True)
    assert kl["timestamp"].is_unique and kl["timestamp"].is_monotonic_increasing
    m5 = pd.read_parquet(os.path.join(OUT, "met5.parquet")).set_index("g")
    g = ((kl["timestamp"].to_numpy() - 600_000) // 300_000) * 300_000
    vb0 = pd.Timestamp("2021-12-02").value // 10**6     # addendum 2: metrics 2021-01..11 chi 1 symbol -> NaN (+24h warm-up)
    for k in VZB:
        x = m5[k].reindex(g).to_numpy(np.float32)
        x[kl["timestamp"].to_numpy() < vb0] = np.nan
        kl[k] = x
    kl.to_parquet(os.path.join(OUT, "vz_feat.parquet"), index=False)
    log.info("MERGE rows=%d %s..%s", len(kl), pd.to_datetime(kl.timestamp.iloc[0], unit="ms"),
             pd.to_datetime(kl.timestamp.iloc[-1], unit="ms"))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "kline":
        kline(sys.argv[2], sys.argv[3])
    elif c == "met":
        met()
    elif c == "merge":
        merge()
