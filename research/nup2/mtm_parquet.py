#!/usr/bin/env python3
"""NUP MTM bang kline parquet (ticker bins goc da bi xoa khoi Oracle).

Vi `~/kaggle_data_hpo` (ticker_*.bin.gz) khong con, pipeline gvz_mtm khong doc duoc gia.
Script nay tai tao DUNG cong thuc legacy cua `reset_rule_score._work`:
  u(t) = Σ q*(close(t) - entry) cho leg mo;  sp(t) = cumsum(pnl tai m1);
  eq(t) = CAP0 + sp(t) + u(t)
Nguon gia: kline1m parquet 2021-01..2025-12 (close 1m, UTC) — cung nguon Vision.
Kiem chung: eq cua tsx-x14-* phai trung deep_cache/eq_dev.npz (sai so <= 0.05 USD).
Out: ~/claude_master/nup_wk/eq_parquet.npz
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import reset_rule_score as R  # noqa: E402

W = "/home/ubuntu/claude_master/nup_wk"
KS = "/home/ubuntu/kaggle_sim/out/"
CAP0 = 35000.0
DAY0 = pd.Timestamp("2021-07-01")
NDEV = int((pd.Timestamp("2026-01-01") - DAY0) // pd.Timedelta(minutes=1))


def month_paths():
    out = {}
    for y in range(2021, 2026):
        for m in range(1, 13):
            if y == 2021:
                p = "/home/ubuntu/claude_master/gvz/k2021/kline1m-%04d-%02d.parquet" % (y, m)
            else:
                p = "/home/ubuntu/vz_e1/raw/kline1m-%04d-%02d.parquet" % (y, m)
            if os.path.exists(p):
                out[(y, m)] = p
    return out


def load_month(path, wanted):
    pf = pq.ParquetFile(path)
    rgs = []
    for i in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(i).column(1).statistics
        s = str(st.min) if st and st.min is not None else None
        if s is None or s in wanted:
            rgs.append(i)
    if not rgs:
        return {}
    tabs = [pf.read_row_group(i, columns=["ts", "sym", "close"]) for i in rgs]
    t = pa.concat_tables(tabs)
    df = t.to_pandas()
    df["sym"] = df["sym"].astype(str)
    df = df[df["sym"].isin(wanted)]
    out = {}
    for sym, g in df.groupby("sym", sort=False):
        g = g.sort_values("ts", kind="mergesort")
        out[sym] = (g["ts"].to_numpy(np.int64), g["close"].to_numpy(np.float64))
    return out


def build(tags, verify=None):
    legs = {}
    for t in tags:
        legs[t] = R.load_legs_minute(R.load_legs(t))
    U = {t: np.zeros(NDEV, np.float64) for t in tags}
    REAL = {t: np.zeros(NDEV + 1, np.float64) for t in tags}
    missing = {t: 0 for t in tags}
    lastpx = {}
    mp = month_paths()
    months = sorted(mp)
    for (y, m) in months:
        ms = int((pd.Timestamp(year=y, month=m, day=1) - DAY0) // pd.Timedelta(minutes=1))
        me = int((pd.Timestamp(year=y, month=m, day=1) + pd.DateOffset(months=1) - DAY0) // pd.Timedelta(minutes=1))
        act = {}
        want = set()
        for t, d in legs.items():
            sub = d[(d.m0 < me) & (d.m1 > ms)]
            if len(sub):
                act[t] = sub
                want |= {s + "USDT" for s in sub["sym"].unique()}
        if not want:
            continue
        px = load_month(mp[(y, m)], want)
        for t, sub in act.items():
            for sym, q, e, m0, m1 in zip(sub["sym"], sub["quantity"], sub["entry"],
                                         sub["m0"].to_numpy(), sub["m1"].to_numpy()):
                a, b = max(int(m0), ms), min(int(m1), me)
                if b <= a:
                    continue
                key = sym + "USDT"
                arr = px.get(key)
                L = b - a
                p = np.full(L, np.nan)
                if arr is not None:
                    ts, cl = arr
                    tgt = DAY0.value // 10 ** 6 + np.arange(a, b, dtype=np.int64) * 60000
                    j = np.searchsorted(ts, tgt)
                    ok = (j < len(ts)) & (ts[np.minimum(j, len(ts) - 1)] == tgt)
                    p[ok] = cl[j[ok]]
                last = lastpx.get((t, key))
                if last is not None:
                    p = np.where(np.isnan(p), last, p)
                if np.isnan(p).all():
                    missing[t] += 1
                    continue
                p = pd.Series(p).ffill().bfill().to_numpy()
                lastpx[(t, key)] = float(p[-1])
                U[t][a:b] += q * p - q * e
            cl = sub[(sub.m1 >= ms) & (sub.m1 < me)]
            for pnl, i1 in zip(cl["pnl"], cl["m1"]):
                REAL[t][int(i1)] += pnl
    out = {}
    for t in tags:
        pref = np.cumsum(REAL[t])[:NDEV]
        out[t] = (CAP0 + pref + U[t]).astype(np.float32)
    if verify:
        z = np.load("/home/ubuntu/claude_master/tsx/deep_cache/eq_dev.npz")
        rep = {}
        for t in verify:
            key = "X14_" + t.split("-")[-1].upper()
            d = z[key]
            m0 = int(z[key + "__m0"][0])
            n = min(len(d), len(out[t]) - m0)
            rep[t] = dict(maxabs=float(np.abs(out[t][m0:m0 + n] - d[:n]).max()),
                          end_diff=float(out[t][m0 + n - 1] - d[n - 1]))
        print(json.dumps(rep, indent=1))
    return out, missing


if __name__ == "__main__":
    tags = sys.argv[1:]
    verify = [t for t in tags if t.startswith("tsx-x14")]
    out, miss = build(tags, verify)
    np.savez(W + "/eq_parquet.npz", **{k: v for k, v in out.items()},
             **{k + "__m0": np.array([0], np.int64) for k in out})
    json.dump(dict(missing=miss, n=len(tags)), open(W + "/mtm_parquet.json", "w"), indent=1)
    print("saved", len(out), "missing", miss)
