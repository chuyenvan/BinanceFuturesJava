#!/usr/bin/env python3
"""S1-V (PREREG_PARITY_V11_WINDOW §4): tinh lai f0..f6 cua S1 tu close 1h Vision (code S1FeatureLive decompiled:
vol7d/dd7d/hrsSinceHigh7d/ret/rankPct), tiem f7/f8 live, cham ONNX s1a2x1 => score/top-24 vs live s1_dump.
Tham so hoa tu d1_s1v.py (5f8e7291) theo PV_DAY (py/pv_cfg.py): ngay Vision = D-15..D. Khong doc 242.
"""
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd
import onnxruntime as ort

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pv_cfg import cfg, globs, VIS_GAP  # noqa: E402

C = cfg()
W, WORK, TAG = C["ROOT"], C["WORK"], C["tag"]
T0, T1 = C["T0"], C["T1"]
MINP = 84
MOD = C["MOD"] + "/c3_models/s1a2x1_cut20251231.onnx"


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


def hrs_since_high(th, c, i):
    """D3 fix: cua so 168 MOC GIO theo thoi gian (live dem moc truoc niem yet/thieu la NaN), can >= 84 moc co gia.
    Ban cu doi i >= 167 phan tu => symbol co 84..167 gio lich su (vd BAC/CEG/IBKR tu 10-24 21:00 UTC) bi NaN sai."""
    if i < 0 or i >= len(c):
        return np.nan
    t_st = th[i] - 167 * 3600000
    lo = int(np.searchsorted(th, t_st, "left"))
    seg, seg_t = c[lo:i + 1], th[lo:i + 1]
    if 168 - int(np.sum(~np.isnan(seg))) > 84:
        return np.nan
    j = int((seg_t[int(np.nanargmax(seg))] - t_st) // 3600000)
    return (167 - j) / 168.0


def rank_pct(v):
    v = np.asarray(v, float)
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
HMS = 3600000


class KDD(Exception):
    """[ADD13] gio thieu sau gio dau tien trong cua so can dung => KHONG DO DUOC (khong truot cua so)."""


def feats_time(th, cv, h):
    """[ADD13] (vol, dd, hs, ret72, ret336) theo MOC GIO; None neu chua co gio dau (nhu ban cu idx<0); nem KDD neu gio thieu."""
    if len(th) == 0:
        return None
    first = int(th[0])
    pos = {int(t): i for i, t in enumerate(th)}
    T = int(th[np.searchsorted(th, h - HMS, "right") - 1]) if np.searchsorted(th, h - HMS, "right") > 0 else None
    if T is None:
        return None
    Tw = ((h - HMS) // HMS) * HMS
    if T != Tw:                       # gio muc tieu thieu (sau niem yet) => ban cu lay gio truoc do: KDD
        raise KDD("T")

    def get(t):
        if t < first:
            return np.nan                # truoc niem yet / truoc cua so du lieu: NaN nhu live
        if t not in pos:
            raise KDD(t)
        return cv[pos[t]]

    rs = []
    for k in range(167, -1, -1):
        t = T - k * HMS
        a = get(t)
        b = get(t - HMS) if t - HMS >= first else np.nan
        if not (np.isnan(a) or np.isnan(b) or b == 0):
            rs.append(a / b - 1)
    r = np.array(rs)
    vol = np.nan if (len(r) < MINP or len(r) < 2) else float(np.sqrt(((r - r.mean()) ** 2).sum() / (len(r) - 1)))
    cl = np.array([get(T - k * HMS) for k in range(167, -1, -1)])
    cl = cl[~np.isnan(cl)]
    mx = np.nan if len(cl) < MINP else float(np.max(cl))
    cT = get(T)
    dd = np.nan if (np.isnan(mx) or mx == 0 or np.isnan(cT)) else cT / mx - 1
    hs = hrs_since_high(th, cv, pos[T])     # cua so 168 gio da kiem khong thieu o tren

    def rett(k):
        b = get(T - k * HMS) if T - k * HMS >= first else np.nan
        return np.nan if (np.isnan(cT) or np.isnan(b) or b == 0) else cT / b - 1
    return vol, dd, hs, rett(72), rett(336)


def build_closes(syms):
    """sym -> (hour_ts array, close array) tu Vision 1m daily (pandas C parser)."""
    out = {}
    for s in syms:
        ts, cl = [], []
        for d in C["s1v_days"]:
            p = "%s/%s/%s.zip" % (C["VIS"], d, s)
            if not os.path.exists(p) and d in VIS_GAP:      # [ADD13] Vision thieu ngay (10-28) -> REST ADD7
                p = VIS_GAP[d].format(s=s)
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
    fs = globs(C["s1_globs"])
    S = pd.concat([pd.read_csv(p) for p in fs], ignore_index=True)
    S = S[(S.ts >= T0) & (S.ts <= T1)]
    syms = sorted(S.symbol.unique())
    cache = WORK + "/closes_cache.pkl"
    if os.path.exists(cache):
        C1 = pickle.load(open(cache, "rb"))
    else:
        C1 = build_closes(syms)
        pickle.dump(C1, open(cache, "wb"))
    print("closes syms=%d" % len(C1), flush=True)
    sess = ort.InferenceSession(MOD, providers=["CPUExecutionProvider"])
    nm = sess.get_inputs()[0].name
    rows = []
    KDDH = {}
    hours = sorted(S.ts.unique())
    for h in hours:
        sh = S[S.ts == h]
        feats = {}
        kdd_h = []
        for s in sh.symbol.values:
            if s not in C1:
                continue
            th, cv = C1[s]
            try:
                f = feats_time(th, cv, h)          # [ADD13] theo thoi gian, gio thieu -> KDD
            except KDD:
                kdd_h.append(s)
                continue
            if f is not None:
                feats[s] = f
        if kdd_h:                                   # feature hang phu thuoc ca tap -> ca gio KDD, loai khoi so sanh/K5
            KDDH[int(h)] = kdd_h
            continue
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

    res = {"n_rows": int(len(D)), "n_hours": int(D.ts.nunique()), "kdd_hours": len(KDDH),
           "kdd_syms": sorted({s for v in KDDH.values() for s in v}), "ADD13": True}
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
    D.to_csv(WORK + "/s1v_rows.csv.gz", index=False)
    json.dump(res, open(WORK + "/s1v_" + TAG + ".json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    main()
