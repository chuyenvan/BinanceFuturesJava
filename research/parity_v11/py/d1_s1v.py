#!/usr/bin/env python3
"""S1-V (PREREG_PARITY_V11_WINDOW §4): tinh lai f0..f6 cua S1 tu close 1h Vision (code S1FeatureLive decompiled:
vol7d/dd7d/hrsSinceHigh7d/ret/rankPct), tiem f7/f8 live, cham ONNX s1a2x1 => score/top-24 vs live s1_dump.
Khong doc 242. Input: vision/klines_1m/2026-10-0*..21, live/s1.
"""
import glob
import json
import os
import zipfile

import numpy as np
import pandas as pd
import onnxruntime as ort

W = os.path.expanduser("~/claude_master/parity_v11w")
T0, T1 = 1792543980000, 1792627140000
MINP = 84
MOD = os.path.expanduser("~/claude_master/parity_1020/raw242/models/c3_models/s1a2x1_cut20251231.onnx")


def ret(c, i, k):
    if c is None or i < 0 or i >= len(c) or i - k < 0:
        return np.nan
    a, b = c[i], c[i - k]
    if np.isnan(a) or np.isnan(b) or b == 0:
        return np.nan
    return a / b - 1


def roll_max(c, i, w, minp):
    if c is None or i < 0 or i >= len(c):
        return np.nan
    lo = max(0, i - w + 1)
    a = c[lo:i + 1]
    a = a[~np.isnan(a)]
    if len(a) < minp:
        return np.nan
    return float(np.max(a))


def dd7d(c, i):
    m = roll_max(c, i, 168, MINP)
    if np.isnan(m) or m == 0 or np.isnan(c[i]):
        return np.nan
    return c[i] / m - 1


def hrs_since_high(c, i):
    if i < 167 or i >= len(c):
        return np.nan
    st = i - 168 + 1
    if np.isnan(c[st:i + 1]).sum() > 84:
        return np.nan
    j = int(np.nanargmax(c[st:i + 1]))
    return (167 - j) / 168.0


def vol7d(c, i):
    st = max(0, i - 168 + 1)
    r = np.array([ret(c, j, 1) for j in range(st, i + 1)])
    r = r[~np.isnan(r)]
    if len(r) < MINP or len(r) < 2:
        return np.nan
    mu = r.mean()
    return float(np.sqrt(((r - mu) ** 2).sum() / len(r)))


def rank_pct(v):
    v = np.asarray(v, float)
    n = np.isnan(v).sum()
    out = np.full(len(v), np.nan)
    ok = ~np.isnan(v)
    m = ok.sum()
    if m == 0:
        return out
    order = np.argsort(v[ok], kind="mergesort")
    vals = v[ok][order]
    ranks = np.empty(m)
    i = 0
    while i < m:
        j = i
        while j + 1 < m and vals[j + 1] == vals[i]:
            j += 1
        rr = ((i + 1) + (j + 1)) / 2.0
        ranks[i:j + 1] = rr
        i = j + 1
    out[np.where(ok)[0][order]] = ranks / m
    return out


RCACHE = {}


def build_closes(syms):
    """sym -> (hour_ts array, close array) tu Vision 1m daily (pandas C parser)."""
    days = ["2026-10-%02d" % d for d in range(6, 22)]
    out = {}
    for s in syms:
        ts, cl = [], []
        for d in days:
            p = "%s/vision/klines_1m/%s/%s.zip" % (W, d, s)
            if not os.path.exists(p):
                continue
            try:
                df = pd.read_csv(p, compression="zip", header=0, usecols=[0, 4])
            except Exception:
                continue
            if df.empty:
                continue
            t = df.iloc[:, 0].astype("int64").values
            c = df.iloc[:, 1].astype("float64").values
            hh = (t // 3600000) * 3600000
            g = pd.DataFrame({"h": hh, "t": t, "c": c}).sort_values("t").groupby("h").c.last()
            ts.append(g.index.values)
            cl.append(g.values)
        if ts:
            t = np.concatenate(ts)
            v = np.concatenate(cl)
            o = np.argsort(t)
            out[s] = (t[o], v[o])
    return out


def main():
    fs = sorted(glob.glob(W + "/live/s1/s1_dump_2026102[12]_*.csv.gz"))
    S = pd.concat([pd.read_csv(p) for p in fs], ignore_index=True)
    S = S[(S.ts >= T0) & (S.ts <= T1)]
    syms = sorted(S.symbol.unique())
    cache = W + "/work/closes_cache.pkl"
    if os.path.exists(cache):
        import pickle
        C = pickle.load(open(cache, "rb"))
    else:
        C = build_closes(syms)
        import pickle
        pickle.dump(C, open(cache, "wb"))
    print("closes syms=%d" % len(C), flush=True)
    sess = ort.InferenceSession(MOD, providers=["CPUExecutionProvider"])
    nm = sess.get_inputs()[0].name
    rows = []
    hours = sorted(S.ts.unique())
    per_hour = {}
    for h in hours:
        sh = S[S.ts == h]
        feats = {}
        for s in sh.symbol.values:
            if s not in C:
                continue
            th, cv = C[s]
            idx = np.searchsorted(th, h - 3600000, "right") - 1
            if idx < 0:
                continue
            if s not in per_hour:
                per_hour[s] = (th, cv)
            # tinh truc tiep (nhanh: chi 1 chi so)
            st = max(0, idx - 167)
            key = (id(cv), len(cv))
            r_all = RCACHE.get(s)
            if r_all is None or len(r_all) != len(cv):
                r_all = np.full(len(cv), np.nan)
                pv = cv[:-1]
                with np.errstate(divide="ignore", invalid="ignore"):
                    r_all[1:] = np.where(pv != 0, cv[1:] / np.where(pv == 0, 1, pv) - 1, np.nan)
                RCACHE[s] = r_all
            r = r_all[st:idx + 1]
            r = r[~np.isnan(r)]
            vol = np.nan if (len(r) < MINP or len(r) < 2) else float(np.sqrt(((r - r.mean()) ** 2).sum() / (len(r) - 1)))
            mx = roll_max(cv, idx, 168, MINP)
            dd = np.nan if (np.isnan(mx) or mx == 0 or np.isnan(cv[idx])) else cv[idx] / mx - 1
            hs = hrs_since_high(cv, idx)
            feats[s] = (vol, dd, hs, ret(cv, idx, 72), ret(cv, idx, 336))
        if not feats:
            continue
        names = list(feats)
        F = np.full((len(names), 9), np.nan)
        for j, s in enumerate(names):
            F[j, 0], F[j, 1], F[j, 3], F[j, 4], F[j, 6] = feats[s]
        F[:, 2] = rank_pct(F[:, 1])
        F[:, 5] = rank_pct(F[:, 4])
        live = sh.set_index("symbol")
        F[:, 7] = [live.loc[s, "f7"] for s in names]
        F[:, 8] = [live.loc[s, "f8"] for s in names]
        for j, s in enumerate(names):
            rows.append((int(h), s, *F[j], live.loc[s, "score"], live.loc[s, "f0"], live.loc[s, "f1"],
                         live.loc[s, "f2"], live.loc[s, "f3"], live.loc[s, "f4"], live.loc[s, "f5"],
                         live.loc[s, "f6"], live.loc[s, "f7"], live.loc[s, "f8"]))
    D = pd.DataFrame(rows, columns=["ts", "symbol", "c0", "c1", "c2", "c3", "c4", "c5", "c6", "f7", "f8",
                                    "score_live", "l0", "l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8"])
    X = D[["c%d" % i for i in range(7)] + ["f7", "f8"]].values.astype(np.float32)
    D["score_calc"] = (-sess.run(None, {nm: X})[0].reshape(-1)).astype(np.float32)

    def eq(a, b):
        a = np.asarray(a, float)
        b = np.asarray(b, float)
        return (np.abs(a - b) <= 1e-6 * (1 + np.abs(b))) | (np.isnan(a) & np.isnan(b))

    res = {"n_rows": int(len(D)), "n_hours": int(D.ts.nunique())}
    for i in range(7):
        res["f%d" % i] = float(eq(D["c%d" % i], D["l%d" % i]).mean())
    res["score_le1e-6"] = float(eq(D.score_calc, D.score_live).mean())
    res["score_max_abs"] = float(np.nanmax(np.abs(D.score_calc - D.score_live)))
    res["spearman"] = float(pd.Series(D.score_calc).rank().corr(pd.Series(D.score_live).rank()))
    TOP = {}
    for ts, g in D.groupby("ts"):
        mine = list(g.sort_values(["score_calc", "symbol"]).symbol.head(24))
        liv = list(g.sort_values(["score_live", "symbol"]).symbol.head(24))
        TOP[ts] = {"jaccard": len(set(mine) & set(liv)) / 24.0, "same_order": mine == liv}
    res["top24_jaccard_mean"] = float(np.mean([v["jaccard"] for v in TOP.values()]))
    res["top24_same_order_frac"] = float(np.mean([v["same_order"] for v in TOP.values()]))
    res["top24_jaccard_min"] = float(np.min([v["jaccard"] for v in TOP.values()]))
    D.to_csv(W + "/work/s1v_rows.csv.gz", index=False)
    json.dump(res, open(W + "/work/s1v_d1.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
