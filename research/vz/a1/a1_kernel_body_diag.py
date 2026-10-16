
# ---- body (LEGS JSON duoc chen o tren) ----
import glob
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("/kaggle/working/a1_log.txt")])
log = logging.getLogger("a1")
L = pd.DataFrame(json.loads(LEGS))  # cot: sym, t0 (ms UTC, open time nen b), entry
L["ym"] = pd.to_datetime(L.t0, unit="ms").dt.strftime("%Y-%m")
MIN = 60_000


def find(kind, ym):
    hits = glob.glob(f"/kaggle/input/**/{kind}-{ym}.parquet", recursive=True)
    return hits[0] if hits else None


def prev_ym(ym):
    y, m = map(int, ym.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def load(kind, yms, syms, cols):
    parts = []
    for ym in yms:
        p = find(kind, ym)
        if p is None:
            log.warning("thieu file %s %s", kind, ym)
            continue
        t = ds.dataset(p).to_table(columns=cols, filter=ds.field("sym").isin(list(syms)))
        parts.append(t.to_pandas())
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)


# map symbol: thu ten goc, roi them USDT
probe = find("basis1m", L.ym.iloc[0])
lake_syms = set(ds.dataset(probe).to_table(columns=["sym"]).column("sym").unique().to_pylist())
log.info("vi du sym lake: %s", sorted(lake_syms)[:8])
def mapsym(s):
    for c in (s, s + "USDT"):
        if c in lake_syms:
            return c
    return s + "USDT"
L["lsym"] = L.sym.map(mapsym)

rows = []
for ym, g in L.groupby("ym"):
    syms = set(g.lsym)
    yms = [prev_ym(ym), ym]
    B = load("basis1m", yms, syms, ["ts", "sym", "prem_close", "mark_close", "index_close"])
    K = load("kline1m", yms, syms, ["ts", "sym", "high", "low", "close"])
    if len(B) and B.ts.max() < 10**11:
        log.error("ts khong phai ms?")
    Bg = {s: d.set_index("ts").sort_index() for s, d in B.groupby("sym")}
    Kg = {s: d.set_index("ts").sort_index() for s, d in K.groupby("sym")}
    for r in g.itertuples():
        t0 = int(r.t0)
        o = {"sym": r.sym, "lsym": r.lsym, "t0": t0, "F1": np.nan, "F2": np.nan, "v2": np.nan,
             "v3_n": 0, "v3_corr": np.nan, "v3b_corr": np.nan, "v3b_mad": np.nan, "prem_abs_med": np.nan, "v3c_corr": np.nan, "max_ts_used": np.nan, "n_prem24": 0}
        b = Bg.get(r.lsym)
        k = Kg.get(r.lsym)
        if b is not None:
            w = b.loc[t0 - 1440 * MIN: t0 - 60 * MIN, "prem_close"].dropna()
            o["n_prem24"] = len(w)
            if t0 in b.index and len(w) >= 600:
                o["F1"] = float(b.at[t0, "prem_close"] - w.median())
            ww = b.loc[t0 - 1440 * MIN: t0].dropna()
            if len(ww) >= 100:
                x = (ww.mark_close - ww.index_close) / ww.index_close
                o["v3_corr"] = float(np.corrcoef(x, ww.prem_close)[0, 1]); o["v3_n"] = len(ww)
                # [DIAG addendum] chan doan V3, KHONG doi F1/F2: (a) basis gia cuoi perp vs prem;
                # (b) mark-basis vs trung binh truot 30' cua prem (mark = index + MA basis)
                o["v3c_corr"] = float(np.corrcoef(x, ww.prem_close.rolling(30, min_periods=10).mean().bfill())[0, 1])
                if k is not None:
                    kk = k.loc[t0 - 1440 * MIN: t0, "close"]
                    j = ww.join(kk, how="inner")
                    if len(j) >= 100:
                        xb = (j.close - j.index_close) / j.index_close
                        o["v3b_corr"] = float(np.corrcoef(xb, j.prem_close)[0, 1])
                        o["v3b_mad"] = float(np.median(np.abs(xb - j.prem_close)))
                        o["prem_abs_med"] = float(np.median(np.abs(j.prem_close)))
        if b is not None and k is not None and t0 in k.index and (t0 - 60 * MIN) in k.index \
                and t0 in b.index and (t0 - 60 * MIN) in b.index:
            rp = k.at[t0, "close"] / k.at[t0 - 60 * MIN, "close"] - 1
            ri = b.at[t0, "index_close"] / b.at[t0 - 60 * MIN, "index_close"] - 1
            o["F2"] = float(rp - ri)
            o["max_ts_used"] = t0
        if k is not None:
            ok = False
            for tb in (t0, t0 + MIN):
                if tb in k.index:
                    lo, hi = k.at[tb, "low"] * 0.998, k.at[tb, "high"] * 1.002
                    ok = ok or (lo <= r.entry <= hi)
            o["v2"] = float(ok)
        rows.append(o)
    log.info("%s: %d chan, basis sym %d/%d, kline sym %d/%d", ym, len(g), len(Bg), len(syms), len(Kg), len(syms))
F = pd.DataFrame(rows)
F.to_csv("/kaggle/working/a1_feat_v2.csv", index=False)
log.info("xong: %d chan; F1 co %.1f%% F2 co %.1f%% v2 %.1f%% v3 corr med %.3f",
         len(F), 100 * F.F1.notna().mean(), 100 * F.F2.notna().mean(), 100 * F.v2.mean(), F.v3_corr.median())
log.info("diag: v3b corr med %.3f p10 %.3f | v3b mad med %.2e vs |prem| med %.2e | v3c corr med %.3f", F.v3b_corr.median(), F.v3b_corr.quantile(.1), F.v3b_mad.median(), F.prem_abs_med.median(), F.v3c_corr.median())
