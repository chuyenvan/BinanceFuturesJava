#!/usr/bin/env python3
"""LIQ_PROXY hygiene checks V1-V4 (prereg §9)."""
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


def load_metrics(y, m):
    d = pd.read_parquet(os.path.join(MET, str(y), "%04d-%02d.parquet" % (y, m)),
                        columns=["ts", "sym", "oi", "oi_value", "ls_cnt", "toptrader_ls_cnt"])
    d["sym"] = d["sym"].astype(str)
    d["avail"] = d["ts"] + 300_000
    return d


def load_k(y, m):
    d = pd.read_parquet(os.path.join(KL, "kline1m-%04d-%02d.parquet" % (y, m)),
                        columns=["ts", "sym", "close", "taker_buy_quote", "quote_volume"])
    d["sym"] = d["sym"].astype(str)
    return d


def compute_one(sym, t_ms, perturb=None):
    g = ((t_ms - LAG) // G5) * G5
    ts = pd.Timestamp(g, unit="ms")
    # two months to cover g-24h
    months = sorted({((ts - pd.Timedelta(days=k)).year, (ts - pd.Timedelta(days=k)).month) for k in (0, 2, 9)})
    mm = pd.concat([load_metrics(y, m) for y, m in months], ignore_index=True)
    kk = pd.concat([load_k(y, m) for y, m in months], ignore_index=True)
    if perturb is not None:
        mm.loc[mm.ts > perturb, ["oi", "oi_value", "ls_cnt", "toptrader_ls_cnt"]] *= 3.0
        kk.loc[kk.ts > perturb, ["close", "taker_buy_quote", "quote_volume"]] *= 3.0
    times = {g + o for o in (0, -60 * M, -15 * M, -30 * M, -16 * M, -31 * M, -1 * M, -61 * M, -1440 * M)}
    mp = mm[mm.avail.isin(times)]
    oi = mp.pivot_table(index="avail", columns="sym", values="oi", aggfunc="last")
    oiv = mp.pivot_table(index="avail", columns="sym", values="oi_value", aggfunc="last")
    kp = kk[kk.ts.isin({g - M, g - 61 * M, g - 16 * M, g - 31 * M})]
    px = kp.pivot_table(index="ts", columns="sym", values="close", aggfunc="last")
    syms = oi.columns
    def s(tab, t):
        return tab.loc[t].reindex(syms) if t in tab.index else pd.Series(np.nan, index=syms)
    r60 = s(px, g - M) / s(px, g - 61 * M) - 1
    l1 = (-(s(oi, g) / s(oi, g - 60 * M) - 1)).where(r60 < 0, 0.0)
    l1 = l1.where(np.isfinite(l1) & np.isfinite(s(oiv, g)) & (s(oiv, g) > 0))
    L1 = float(l1[sym])
    # L2
    kk["b5"] = (kk.ts // G5) * G5
    b = kk.groupby(["sym", "b5"], as_index=False).agg(tbq=("taker_buy_quote", "sum"), qv=("quote_volume", "sum"))
    b = b[b.sym == sym].set_index("b5")
    tb = sum(float(b.tbq.get(g - 15 * M + j * G5, np.nan)) for j in range(3))
    qv = sum(float(b.qv.get(g - 15 * M + j * G5, np.nan)) for j in range(3))
    d0 = ts.normalize()
    kk["day"] = pd.to_datetime(kk.ts, unit="ms").dt.normalize()
    dd = kk[kk.sym == sym].groupby("day").agg(tbq=("taker_buy_quote", "sum"), qv=("quote_volume", "sum"))
    vals = []
    for k in range(1, 8):
        dday = d0 - pd.Timedelta(days=k)
        if dday in dd.index and dd.loc[dday, "qv"] > 0:
            vals.append(1 - dd.loc[dday, "tbq"] / dd.loc[dday, "qv"])
    L2 = (1 - tb / qv) - float(np.median(vals)) if qv > 0 and len(vals) >= 5 else np.nan
    # L3
    def l15(c):
        r = s(px, c - M) / s(px, c - 16 * M) - 1
        v = (-(s(oi, c) / s(oi, c - 15 * M) - 1)).where(r < 0, 0.0)
        return float(v[sym])
    L3 = l15(g) - l15(g - 15 * M)
    # LM
    prev = d0 - pd.Timedelta(days=1)
    qd = kk[kk.day == prev].groupby("sym").quote_volume.sum()
    uni = qd.index[qd >= 20e6].intersection(l1.index)
    w = s(oiv, g).reindex(uni); v = l1.reindex(uni)
    msk = np.isfinite(w) & np.isfinite(v) & (w > 0)
    LM = float((v[msk] * w[msk]).sum() / w[msk].sum()) if msk.sum() >= 5 else np.nan
    raw = dict(sym=sym, g=int(g), g_utc=str(ts), oi_g=float(s(oi, g)[sym]), oi_g60=float(s(oi, g - 60 * M)[sym]),
               oiv_g=float(s(oiv, g)[sym]), px_g1=float(s(px, g - M)[sym]), px_g61=float(s(px, g - 61 * M)[sym]),
               tbq15=tb, qv15=qv, base7=float(np.median(vals)) if vals else None, nbase=len(vals),
               oi_30=float(s(oi, g - 30 * M)[sym]), oi_15=float(s(oi, g - 15 * M)[sym]),
               px_g16=float(s(px, g - 16 * M)[sym]), px_g31=float(s(px, g - 31 * M)[sym]))
    return dict(L1=L1, L2=L2, L3=L3, LM=LM, raw=raw)


def main():
    s = pd.read_csv(os.path.join(HERE, "samples_outcome.csv"))
    s = s[s.kind == "cluster"]
    picks = [s[(s.period == "disc")].iloc[0], s[(s.period == "disc")].iloc[-1], s[(s.period == "test")].iloc[len(s[s.period == "test"]) // 2]]
    out = {"V1": [], "V2": [], "V4": []}
    for r in picks:
        t = int(r.t_ms)
        a = compute_one(r.sym, t)
        b = compute_one(r.sym, t, perturb=t)
        dv = {k: (abs(a[k] - b[k]) if np.isfinite(a[k]) and np.isfinite(b[k]) else None) for k in ("L1", "L2", "L3", "LM")}
        out["V1"].append(dict(sym=r.sym, t=str(r.anchor), diffs=dv,
                              ok=all(v is None or v == 0 for v in dv.values())))
        # V2: compare r60 at UTC vs local-as-UTC
        t_loc = t + 7 * 3600 * 1000
        c = compute_one(r.sym, t_loc)
        out["V2"].append(dict(sym=r.sym, start_local=str(pd.Timestamp(t, unit="ms") + pd.Timedelta(hours=7)),
                              start_utc=str(pd.Timestamp(t, unit="ms")),
                              L1_utc=a["L1"], L1_local=c["L1"], raw=a["raw"]))
        # V4: pipeline vs manual
        out["V4"].append(dict(sym=r.sym, anchor=str(r.anchor), pipeline=dict(L1=float(r.L1), L2=float(r.L2), L3=float(r.L3), LM=float(r.LM)),
                              manual=a,
                              match=all((not np.isfinite(a[k])) or abs(float(r[k]) - a[k]) < 1e-6 for k in ("L1", "L2", "L3", "LM"))))
    # V3 coverage by year
    d = pd.read_csv(os.path.join(HERE, "samples_outcome.csv"))
    d = d[d.kind == "cluster"]
    cov = {}
    for y, g in d.groupby("year"):
        cov[str(y)] = {c: round(float(g[c].notna().mean()), 4) for c in ["L1", "L2", "L3", "LM", "arm168", "MFE24", "MAE24"]}
    out["V3"] = cov
    with open(os.path.join(HERE, "liq_proxy_v1v4.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps(out["V1"], indent=1))
    print("V1 all", all(x["ok"] for x in out["V1"]))
    print("V4 all", all(x["match"] for x in out["V4"]))
    print(json.dumps(out["V3"], indent=1))


if __name__ == "__main__":
    main()
