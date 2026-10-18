#!/usr/bin/env python3
"""EDGE_ATTR build (PREREG_EDGE_ATTR 4852f57e) - CHI DO.
Ghep chan lenh printDone (ECMEAS bucket DEV + HO4 W9 mo ta) voi kline1m Vision:
 - chi so ALT_EW (TB log-return 1m, tru BTC/ETH, qv>0 ca hai nen, cat +-0.5) va BTC theo phut
 - moi chan: L24, sigma_d (cua so [M-1439, M]), so nen, close(M), m_alt, m_btc tu close(M) den close(E).
Output: ~/claude_master/edge_attr/{legs.parquet, index.npz, build.json}
"""
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("eab")
O = "/home/ubuntu/kaggle_sim/out/"
OUT = "/home/ubuntu/claude_master/edge_attr"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
MIN = 60000
H7 = pd.Timedelta(hours=7)


def tag(win, s):
    if win == "D":
        return "ec-s-s42" if s == 42 else "ecm-d-s%d" % s
    return "ecm-h-s%d" % s


def kp(ym):
    a = "/home/ubuntu/claude_master/gvz/k2021/kline1m-%s.parquet" % ym
    b = "/home/ubuntu/vz_e1/raw/kline1m-%s.parquet" % ym
    if ym < "2021-12" and os.path.exists(a):
        return a
    return b if os.path.exists(b) else (a if os.path.exists(a) else None)


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def load_legs():
    rows, md5 = [], {}
    for win in ("D", "H"):
        for s in SEEDS:
            t = tag(win, s)
            p = O + t + "/storage/printDone.csv"
            if not os.path.exists(p):
                log.warning("missing %s", p)
                continue
            md5[t] = md5f(p)
            d = pd.read_csv(p, index_col=False,
                            usecols=["sym", "entry", "profit", "status", "start", "end", "level", "margin", "pnl"])
            d["win"], d["seed"], d["run"] = win, s, t
            d["b"] = d.groupby("start")["sym"].transform("size").astype(int)
            rows.append(d)
    d = pd.concat(rows, ignore_index=True)
    d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
    d["t1"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d["M"] = ((d["t0"] - H7).astype("int64") // 10**6).astype(np.int64)
    d["E"] = np.where(d["t1"].notna(), (d["t1"] - H7).astype("int64") // 10**6, -1).astype(np.int64)
    d["vs"] = d["sym"].astype(str) + "USDT"
    d["ym"] = (d["t0"] - H7).dt.strftime("%Y-%m")
    log.info("legs=%d runs=%d", len(d), d["run"].nunique())
    return d, md5


def months(a, b):
    out, y, m = [], int(a[:4]), int(a[5:])
    while "%04d-%02d" % (y, m) <= b:
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def read_month(ym, syms=None):
    p = kp(ym)
    if p is None:
        return None
    t = pq.read_table(p, columns=["ts", "sym", "close", "quote_volume"]).to_pandas()
    t["sym"] = t["sym"].astype(str)
    if syms is not None:
        t = t[t["sym"].isin(syms)]
    t = t.drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"], kind="mergesort").reset_index(drop=True)
    return t


def logret(t):
    ts = t["ts"].to_numpy(np.int64)
    sy = t["sym"].to_numpy()
    lc = np.log(t["close"].to_numpy(np.float64))
    qv = t["quote_volume"].to_numpy(np.float64)
    r = np.full(len(t), np.nan)
    ok = np.zeros(len(t), bool)
    if len(t) > 1:
        same = (sy[1:] == sy[:-1]) & (ts[1:] - ts[:-1] == MIN)
        r[1:] = np.where(same, lc[1:] - lc[:-1], np.nan)
        ok[1:] = same & (qv[1:] > 0) & (qv[:-1] > 0)
    return ts, sy, lc, qv, r, ok


def build_index(mlist):
    ew_ts, ew_r, bt_ts, bt_r, miss = [], [], [], [], []
    for ym in mlist:
        t = read_month(ym)
        if t is None:
            miss.append(ym)
            continue
        ts, sy, lc, qv, r, ok = logret(t)
        alt = ok & ~np.isin(sy, ["BTCUSDT", "ETHUSDT"]) & np.isfinite(r)
        s = pd.Series(np.clip(r[alt], -0.5, 0.5)).groupby(ts[alt]).mean()
        ew_ts.append(s.index.to_numpy(np.int64))
        ew_r.append(s.to_numpy(np.float64))
        b = (sy == "BTCUSDT") & np.isfinite(r)
        bt_ts.append(ts[b])
        bt_r.append(r[b])
        log.info("index %s rows=%d ew_min=%d nsym=%d", ym, len(t), len(s), len(np.unique(sy)))
    return (np.concatenate(ew_ts), np.concatenate(ew_r), np.concatenate(bt_ts), np.concatenate(bt_r), miss)


def cum_lookup(ts, r, q):
    """cum log-return tai phut q (bao gom nen q); NaN neu q khong co trong index."""
    o = np.argsort(ts, kind="mergesort")
    ts, c = ts[o], np.cumsum(r[o])
    i = np.searchsorted(ts, q)
    hit = (i < len(ts)) & (ts[np.minimum(i, len(ts) - 1)] == q)
    out = np.full(len(q), np.nan)
    out[hit] = c[i[hit]]
    return out


def leg_features(d):
    res = {k: np.full(len(d), np.nan) for k in ("L24", "sig_d", "nbar", "closeM")}
    prev_ym, prev = None, None
    for ym in sorted(d["ym"].unique()):
        idx = np.where(d["ym"].to_numpy() == ym)[0]
        syms = set(d["vs"].to_numpy()[idx])
        cur = read_month(ym, syms)
        if cur is None:
            log.warning("no kline %s (%d legs)", ym, len(idx))
            prev_ym, prev = ym, None
            continue
        y, m = int(ym[:4]), int(ym[5:])
        pym = "%04d-%02d" % (y - (m == 1), 12 if m == 1 else m - 1)
        pv = prev if (prev_ym == pym and prev is not None) else read_month(pym, syms)
        if pv is not None:
            pv = pv[pv["sym"].isin(syms)]
        t = pd.concat([pv, cur], ignore_index=True) if pv is not None else cur
        t = t.drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"], kind="mergesort").reset_index(drop=True)
        ts, sy, lc, qv, r, ok = logret(t)
        bounds = {}
        u, first = np.unique(sy, return_index=True)
        last = np.r_[first[1:], len(sy)]
        for s_, a_, b_ in zip(u, first, last):
            bounds[s_] = (a_, b_)
        cqv = np.r_[0.0, np.cumsum(qv)]
        rv = np.where(np.isfinite(r), r, 0.0)
        c1 = np.r_[0.0, np.cumsum(rv)]
        c2 = np.r_[0.0, np.cumsum(rv * rv)]
        cn = np.r_[0, np.cumsum(np.isfinite(r).astype(np.int64))]
        Ms = d["M"].to_numpy()[idx]
        vss = d["vs"].to_numpy()[idx]
        for j, (Mi, vsi) in enumerate(zip(Ms, vss)):
            if vsi not in bounds:
                continue
            a_, b_ = bounds[vsi]
            tsx = ts[a_:b_]
            i0 = a_ + np.searchsorted(tsx, Mi - 1439 * MIN, "left")
            i1 = a_ + np.searchsorted(tsx, Mi, "right")
            k = idx[j]
            res["nbar"][k] = i1 - i0
            res["L24"][k] = cqv[i1] - cqv[i0]
            n = cn[i1] - cn[i0 + 1] if i1 > i0 + 1 else 0  # r trong cua so: chi so i0+1..i1-1
            if n > 1:
                s1 = c1[i1] - c1[i0 + 1]
                s2 = c2[i1] - c2[i0 + 1]
                var = max((s2 - s1 * s1 / n) / (n - 1), 0.0)
                res["sig_d"][k] = np.sqrt(var) * np.sqrt(1440.0)
            if i1 > a_ and ts[i1 - 1] == Mi:
                res["closeM"][k] = np.exp(lc[i1 - 1])
        log.info("legs %s n=%d", ym, len(idx))
        prev_ym, prev = ym, cur
    for k, v in res.items():
        d[k] = v
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    d, md5 = load_legs()
    lo = (pd.to_datetime(d["M"].min(), unit="ms") - pd.Timedelta(days=2)).strftime("%Y-%m")
    e_ok = d["E"] > 0
    hi = pd.to_datetime(max(d["M"].max(), d.loc[e_ok, "E"].max()), unit="ms").strftime("%Y-%m")
    ml = months(lo, hi)
    log.info("months %s..%s (%d)", lo, hi, len(ml))
    ew_ts, ew_r, bt_ts, bt_r, miss = build_index(ml)
    np.savez_compressed(OUT + "/index.npz", ew_ts=ew_ts, ew_r=ew_r, bt_ts=bt_ts, bt_r=bt_r)
    for nm, (a, b) in {"alt": (ew_ts, ew_r), "btc": (bt_ts, bt_r)}.items():
        cM = cum_lookup(a, b, d["M"].to_numpy())
        cE = cum_lookup(a, b, d["E"].to_numpy())
        d["m_" + nm] = np.expm1(cE - cM)
        d["hasM_" + nm] = np.isfinite(cM)
        d["hasE_" + nm] = np.isfinite(cE)
    d = leg_features(d)
    d.drop(columns=["t0", "t1"]).to_parquet(OUT + "/legs.parquet", index=False)
    json.dump({"prereg": "4852f57e", "md5": md5, "months_missing": miss, "n_legs": int(len(d))},
              open(OUT + "/build.json", "w"), indent=1)
    log.info("DONE legs=%d missing_months=%s", len(d), miss)


if __name__ == "__main__":
    main()
