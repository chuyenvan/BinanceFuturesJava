#!/usr/bin/env python3
"""V4: independent manual recomputation for 3 clusters (targeted reads)."""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MET = "/home/ubuntu/vz/out/metrics5m"
KL = "/home/ubuntu/vz_e1/raw"
M = 60_000
G5 = 5 * M
LAG = 10 * M


def kfile(y, m):
    return os.path.join(KL, "kline1m-%04d-%02d.parquet" % (y, m))


def mfile(y, m):
    return os.path.join(MET, str(y), "%04d-%02d.parquet" % (y, m))


def kl(y, m, cols, filters):
    return pd.read_parquet(kfile(y, m), columns=cols, filters=filters)


def one(sym, t_ms):
    g = ((t_ms - LAG) // G5) * G5
    ts = pd.Timestamp(g, unit="ms")
    ym = [(ts.year, ts.month)]
    if (ts - pd.Timedelta(hours=1)).month != ts.month:
        ym.append(((ts - pd.Timedelta(hours=1)).year, (ts - pd.Timedelta(hours=1)).month))
    md = pd.concat([pd.read_parquet(mfile(y, m), columns=["ts", "sym", "oi", "oi_value", "ls_cnt"],
                                    filters=[("ts", "in", [g - 300_000 + o for o in (0, -60 * M, -15 * M, -30 * M)])])
                   for y, m in ym], ignore_index=True)
    md["sym"] = md["sym"].astype(str); md["avail"] = md.ts + 300_000
    oi = md.pivot_table(index="avail", columns="sym", values="oi", aggfunc="last")
    oiv = md.pivot_table(index="avail", columns="sym", values="oi_value", aggfunc="last")
    syms = oi.columns
    def S(tab, t):
        return tab.loc[t].reindex(syms) if t in tab.index else pd.Series(np.nan, index=syms)
    # price cross-section at g-1,g-61
    kp = kl(ts.year, ts.month, ["ts", "sym", "close"], [("ts", "in", [g - M, g - 61 * M])])
    kp["sym"] = kp["sym"].astype(str)
    px = kp.pivot_table(index="ts", columns="sym", values="close", aggfunc="last")
    r60 = S(px, g - M) / S(px, g - 61 * M) - 1
    l1 = (-(S(oi, g) / S(oi, g - 60 * M) - 1)).where(r60 < 0, 0.0)
    l1 = l1.where(np.isfinite(l1) & np.isfinite(S(oiv, g)) & (S(oiv, g) > 0))
    # L2 raw 15m + daily 7d
    k15 = kl(ts.year, ts.month, ["ts", "sym", "taker_buy_quote", "quote_volume"],
             [("ts", ">=", g - 15 * M), ("ts", "<", g), ("sym", "==", sym)])
    tb = float(k15.taker_buy_quote.sum()); qv = float(k15.quote_volume.sum())
    d0 = ts.normalize()
    k7 = kl(ts.year, ts.month, ["ts", "sym", "taker_buy_quote", "quote_volume"],
            [("ts", ">=", int((d0 - pd.Timedelta(days=7)).value // 10 ** 6)),
             ("ts", "<", int(d0.value // 10 ** 6)), ("sym", "==", sym)])
    k7["day"] = pd.to_datetime(k7.ts, unit="ms").dt.normalize()
    dd = k7.groupby("day").agg(tbq=("taker_buy_quote", "sum"), qv=("quote_volume", "sum"))
    vals = [1 - r.tbq / r.qv for _, r in dd.iterrows() if r.qv > 0]
    base7 = float(np.median(vals)) if len(vals) >= 5 else np.nan
    sell15 = 1 - tb / qv if qv > 0 else np.nan
    L2 = sell15 - base7 if np.isfinite(base7) else np.nan
    # L3
    def l15(c):
        o1, o0 = S(oi, c), S(oi, c - 15 * M)
        k = kl(ts.year, ts.month, ["ts", "sym", "close"], [("ts", "in", [c - M, c - 16 * M])])
        k["sym"] = k["sym"].astype(str)
        p = k.pivot_table(index="ts", columns="sym", values="close", aggfunc="last")
        r = S(p, c - M) / S(p, c - 16 * M) - 1
        v = (-(o1 / o0 - 1)).where(r < 0, 0.0)
        return float(v.get(sym, np.nan))
    L3 = l15(g) - l15(g - 15 * M)
    # LM
    prev = d0 - pd.Timedelta(days=1)
    kd = kl(ts.year, ts.month, ["ts", "sym", "quote_volume"],
            [("ts", ">=", int(prev.value // 10 ** 6)), ("ts", "<", int(d0.value // 10 ** 6))])
    kd["sym"] = kd["sym"].astype(str)
    qd = kd.groupby("sym").quote_volume.sum()
    uni = qd.index[qd >= 20e6].intersection(l1.index)
    w = S(oiv, g).reindex(uni); v = l1.reindex(uni)
    msk = np.isfinite(w) & np.isfinite(v) & (w > 0)
    LM = float((v[msk] * w[msk]).sum() / w[msk].sum()) if msk.sum() >= 5 else np.nan
    raw = dict(sym=sym, g=int(g), g_utc=str(ts), oi_g=float(S(oi, g)[sym]), oi_g60=float(S(oi, g - 60 * M)[sym]),
               oiv_g=float(S(oiv, g)[sym]), px_g1=float(S(px, g - M)[sym]), px_g61=float(S(px, g - 61 * M)[sym]),
               oi_g15=float(S(oi, g - 15 * M)[sym]), oi_g30=float(S(oi, g - 30 * M)[sym]),
               tbq15=tb, qv15=qv, base7=base7, nbase=len(vals), prev_qv_n=int((qd >= 20e6).sum()))
    return dict(L1=float(l1[sym]), L2=L2, L3=L3, LM=LM, raw=raw)


def main():
    s = pd.read_csv(os.path.join(HERE, "samples_outcome.csv"))
    s = s[(s.kind == "cluster") & s.L2.notna() & (pd.to_datetime(s.anchor).dt.day > 10)]
    picks = [s[s.period == "disc"].iloc[0], s[s.period == "disc"].iloc[-1],
             s[s.period == "test"].iloc[len(s[s.period == "test"]) // 2]]
    out = []
    for r in picks:
        a = one(r.sym, int(r.t_ms))
        rec = dict(anchor=str(r.anchor), pipeline=dict(L1=float(r.L1), L2=float(r.L2), L3=float(r.L3), LM=float(r.LM)),
                   manual=a, match={k: (abs(float(r[k]) - a[k]) < 1e-6 if np.isfinite(a[k]) else None)
                                    for k in ("L1", "L2", "L3", "LM")})
        out.append(rec)
        print(json.dumps(rec, indent=1, default=str))
    with open(os.path.join(HERE, "v4_manual.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()
