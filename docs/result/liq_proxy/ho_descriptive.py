#!/usr/bin/env python3
"""HO 2026 DESCRIPTIVE ONLY (prereg §2: HO chi mo ta sau cung, khong cham).
Separate from the frozen DEV pipeline; uses the same proxy definitions.
Outputs ho_samples*.csv, ho_aux_*.csv, ho_ic.json.
"""
import gc
import json
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
KSOUT = "/home/ubuntu/kaggle_sim/out"
MET = "/home/ubuntu/vz/out/metrics5m"
KL = "/home/ubuntu/vz_e1/raw"
TAGS = ["42", "7", "13", "21", "99", "123", "777", "2024"]
M = 60_000
G5 = 5 * M
LAG = 10 * M
H7 = pd.Timedelta(hours=7)


def month_iter(y0, m0, y1, m1):
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def kf(y, m):
    return os.path.join(KL, "kline1m-%04d-%02d.parquet" % (y, m))


def mf(y, m):
    return os.path.join(MET, str(y), "%04d-%02d.parquet" % (y, m))


def samples():
    fr = []
    for tag in TAGS:
        p = os.path.join(KSOUT, "tsx-ho-x14-s" + tag, "storage", "printDone.csv")
        d = pd.read_csv(p, index_col=False)
        d.columns = [c.strip() for c in d.columns]
        for c in ("entry", "pnl", "pred15m"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["sym"] = d["sym"].astype(str).str.strip()
        d["sym"] = np.where(d["sym"].str.endswith("USDT"), d["sym"], d["sym"] + "USDT")
        d = d.dropna(subset=["entry", "pnl"])
        d = d[d.entry > 0]
        d["start_u"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - H7
        d["end_u"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M") - H7
        d["seed"] = tag
        fr.append(d[["sym", "entry", "pnl", "pred15m", "start_u", "end_u", "seed"]])
    d = pd.concat(fr, ignore_index=True)
    d["hour_u"] = d.end_u.dt.floor("h")
    g = d.groupby(["sym", "hour_u", "seed"], as_index=False).agg(anchor=("start_u", "min"),
                                                                 pnl=("pnl", "sum"), nleg=("pnl", "size"))
    a = d.merge(g[["sym", "hour_u", "seed", "anchor"]], on=["sym", "hour_u", "seed"])
    a = a[a.start_u == a.anchor].sort_values("start_u").drop_duplicates(["sym", "hour_u", "seed"])
    g = g.merge(a[["sym", "hour_u", "seed", "entry", "pred15m"]], on=["sym", "hour_u", "seed"], how="left")
    cl = g.groupby(["sym", "anchor"], as_index=False).agg(pnl=("pnl", "mean"), nseed=("seed", "nunique"),
                                                          entry=("entry", "first"), pred15m=("pred15m", "mean"))
    cl["kind"] = "cluster"
    s = cl[(cl.anchor >= "2026-01-01") & (cl.anchor < "2026-10-01")].copy()
    s["t_ms"] = s.anchor.astype("int64") // 10 ** 6
    s["g_ms"] = (((s.t_ms - LAG) // G5) * G5).astype("int64")
    s["year"] = 2026
    s.to_csv(os.path.join(HERE, "ho_samples.csv"), index=False)
    print("HO samples", len(s), s.anchor.min(), s.anchor.max(), s.groupby(s.anchor.dt.month).size().to_dict())


def aux():
    s = pd.read_csv(os.path.join(HERE, "ho_samples.csv"))
    need = set()
    for g in s.g_ms.astype("int64"):
        for j in range(3):
            need.add(int(g - 15 * M + j * G5))
    daily, l2 = {}, {}
    for y, m in month_iter(2025, 12, 2026, 9):
        pf = pq.ParquetFile(kf(y, m))
        for batch in pf.iter_batches(batch_size=1_500_000, columns=["ts", "sym", "taker_buy_quote", "quote_volume"]):
            d = batch.to_pandas()
            d["sym"] = d.sym.astype(str)
            d["tbq"] = d.taker_buy_quote.astype("float32"); d["qv"] = d.quote_volume.astype("float32")
            d["day"] = pd.to_datetime(d.ts, unit="ms").dt.normalize()
            z = d.groupby(["sym", "day"], as_index=False)[["tbq", "qv"]].sum()
            for r in z.itertuples():
                k = (r.sym, r.day); v = daily.get(k)
                daily[k] = (float(r.tbq), float(r.qv)) if v is None else (v[0] + float(r.tbq), v[1] + float(r.qv))
            d["b5"] = (d.ts // G5) * G5
            z2 = d[d.b5.isin(need)]
            if len(z2):
                z2 = z2.groupby(["sym", "b5"], as_index=False)[["tbq", "qv"]].sum()
                for r in z2.itertuples():
                    k = (r.sym, int(r.b5)); v = l2.get(k)
                    l2[k] = (float(r.tbq), float(r.qv)) if v is None else (v[0] + float(r.tbq), v[1] + float(r.qv))
            del d, z, z2
        print("aux", y, m, flush=True)
        gc.collect()
    pd.DataFrame([(k[0], k[1], v[0], v[1]) for k, v in daily.items()], columns=["sym", "day", "tbq", "qv"]).to_csv(
        os.path.join(HERE, "ho_aux_daily.csv"), index=False)
    pd.DataFrame([(k[0], k[1], v[0], v[1]) for k, v in l2.items()], columns=["sym", "b5", "tbq", "qv"]).to_csv(
        os.path.join(HERE, "ho_aux_l2.csv"), index=False)
    print("aux done", len(daily), len(l2))


def proxies():
    s = pd.read_csv(os.path.join(HERE, "ho_samples.csv"))
    for c in ("L1", "L2", "L3", "LM", "oi_val_g"):
        s[c] = np.nan
    daily = pd.read_csv(os.path.join(HERE, "ho_aux_daily.csv"))
    daily["day"] = pd.to_datetime(daily.day)
    sell = (daily.assign(sell=1 - daily.tbq / daily.qv)).pivot_table(index="day", columns="sym", values="sell")
    qv = daily.pivot_table(index="day", columns="sym", values="qv")
    l2 = pd.read_csv(os.path.join(HERE, "ho_aux_l2.csv"))
    for y, m in month_iter(2026, 1, 2026, 9):
        mon = pd.Timestamp(y, m, 1); nxt = mon + pd.offsets.MonthBegin(1)
        idx = [i for i in s.index if mon - pd.Timedelta(days=2) <= pd.Timestamp(s.at[i, "anchor"]) < nxt + pd.Timedelta(days=2)]
        md = pd.read_parquet(mf(y, m), columns=["ts", "sym", "oi", "oi_value"])
        md["sym"] = md.sym.astype(str); md["avail"] = md.ts + 300_000
        if idx:
            G = set(s.loc[idx, "g_ms"].astype("int64"))
            Ts = set()
            for o in (0, -60 * M, -15 * M, -30 * M):
                Ts |= {int(x) + o for x in G}
            mp = md[md.avail.isin(Ts)]
            oi = mp.pivot_table(index="avail", columns="sym", values="oi", aggfunc="last")
            oiv = mp.pivot_table(index="avail", columns="sym", values="oi_value", aggfunc="last")
            syms = oi.columns
            needp = set()
            for i in idx:
                g = int(s.at[i, "g_ms"]); needp |= {g - M, g - 16 * M, g - 31 * M, g - 61 * M}
            kp = pd.read_parquet(kf(y, m), columns=["ts", "sym", "close"], filters=[("ts", "in", sorted(needp))])
            kp["sym"] = kp.sym.astype(str)
            px = kp.pivot_table(index="ts", columns="sym", values="close", aggfunc="last")
        else:
            oi = oiv = px = pd.DataFrame(); syms = pd.Index([])
        def S(tab, t):
            return tab.loc[t].reindex(syms) if (not tab.empty and t in tab.index) else pd.Series(np.nan, index=syms)
        for i in idx:
            g = int(s.at[i, "g_ms"]); sym = s.at[i, "sym"]
            oi_n, oi_p = S(oi, g), S(oi, g - 60 * M); oiv_n = S(oiv, g)
            r60 = S(px, g - M) / S(px, g - 61 * M) - 1
            l1 = (-(oi_n / oi_p - 1)).where(r60 < 0, 0.0)
            l1 = l1.where(np.isfinite(l1) & np.isfinite(oiv_n) & (oiv_n > 0))
            if sym not in l1.index or not np.isfinite(l1.get(sym, np.nan)):
                continue
            s.at[i, "L1"] = float(l1[sym]); s.at[i, "oi_val_g"] = float(oiv_n[sym])
            q = l2[(l2.sym == sym) & (l2.b5 >= g - 15 * M) & (l2.b5 < g)]
            if len(q) == 3 and q.qv.sum() > 0:
                sell15 = 1 - q.tbq.sum() / q.qv.sum()
                d0 = pd.Timestamp(g, unit="ms").normalize()
                vals = [float(sell.at[d0 - pd.Timedelta(days=k), sym]) for k in range(1, 8)
                        if (d0 - pd.Timedelta(days=k)) in sell.index and sym in sell.columns
                        and np.isfinite(sell.at[d0 - pd.Timedelta(days=k), sym])]
                if len(vals) >= 5:
                    s.at[i, "L2"] = sell15 - float(np.median(vals))
            def l15(c):
                v = (-(S(oi, c) / S(oi, c - 15 * M) - 1)).where(S(px, c - M) / S(px, c - 16 * M) - 1 < 0, 0.0)
                return float(v.get(sym, np.nan))
            a, b = l15(g), l15(g - 15 * M)
            if np.isfinite(a) and np.isfinite(b):
                s.at[i, "L3"] = a - b
            prev = pd.Timestamp(g, unit="ms").normalize() - pd.Timedelta(days=1)
            if prev in qv.index:
                qd = qv.loc[prev].dropna(); uni = qd.index[qd >= 20e6].intersection(l1.index)
                w = oiv_n.reindex(uni); v = l1.reindex(uni)
                msk = np.isfinite(w) & np.isfinite(v) & (w > 0)
                if msk.sum() >= 5:
                    s.at[i, "LM"] = float((v[msk] * w[msk]).sum() / w[msk].sum())
        print("proxy", y, m, len(idx), flush=True)
        del md, oi, oiv, px, kp
        gc.collect()
    s.to_csv(os.path.join(HERE, "ho_samples_proxy.csv"), index=False)
    print("coverage", {c: round(float(s[c].notna().mean()), 4) for c in ["L1", "L2", "L3", "LM"]})


def outcomes():
    s = pd.read_csv(os.path.join(HERE, "ho_samples_proxy.csv"))
    for c in ("maxh168", "maxh24", "minl24"):
        s[c] = np.nan
    s["win_complete"] = False
    s["t_end"] = s.t_ms + 168 * 60 * M
    for y, m in month_iter(2026, 1, 2026, 10):
        mon = pd.Timestamp(y, m, 1); nxt = mon + pd.offsets.MonthBegin(1)
        lo_m = int(mon.value // 10 ** 6); hi_m = int(nxt.value // 10 ** 6)
        idx = [i for i in s.index if s.at[i, "t_ms"] < hi_m and s.at[i, "t_end"] > lo_m]
        if not idx:
            continue
        try:
            kd = pd.read_parquet(kf(y, m), columns=["ts", "sym", "high", "low"])
        except FileNotFoundError:
            print("missing", y, m, flush=True); continue
        by_sym = {}
        for i in idx:
            by_sym.setdefault(s.at[i, "sym"], []).append(i)
        kd = kd[kd.sym.isin(by_sym.keys())]
        for sym, g in kd.groupby("sym", sort=False):
            ts = g.ts.to_numpy(np.int64); hi = g.high.to_numpy(np.float64); low = g.low.to_numpy(np.float64)
            for i in by_sym.get(sym, []):
                t = int(s.at[i, "t_ms"]); t24 = t + 24 * 60 * M; t168 = int(s.at[i, "t_end"])
                a = np.searchsorted(ts, max(t, lo_m)); b = np.searchsorted(ts, min(t168, hi_m))
                if b > a:
                    h = float(np.nanmax(hi[a:b]))
                    if not np.isfinite(s.at[i, "maxh168"]) or h > s.at[i, "maxh168"]:
                        s.at[i, "maxh168"] = h
                b24 = np.searchsorted(ts, min(t24, hi_m))
                if b24 > a:
                    h = float(np.nanmax(hi[a:b24])); l = float(np.nanmin(low[a:b24]))
                    if not np.isfinite(s.at[i, "maxh24"]) or h > s.at[i, "maxh24"]:
                        s.at[i, "maxh24"] = h
                    if not np.isfinite(s.at[i, "minl24"]) or l < s.at[i, "minl24"]:
                        s.at[i, "minl24"] = l
                if t168 <= hi_m:
                    s.at[i, "win_complete"] = True
        print("outcome", y, m, len(idx), flush=True)
        del kd
        gc.collect()
    e = s.entry.to_numpy(float)
    s["arm168"] = np.where(np.isfinite(s.maxh168), (s.maxh168.to_numpy(float) >= e * 1.07).astype(float), np.nan)
    s["MFE24"] = s.maxh24.to_numpy(float) / e - 1
    s["MAE24"] = s.minl24.to_numpy(float) / e - 1
    s.to_csv(os.path.join(HERE, "ho_samples_outcome.csv"), index=False)
    print("HO outcome", s[["arm168", "MFE24", "MAE24"]].notna().mean().to_dict(), "complete", s.win_complete.mean())


def score():
    d = pd.read_csv(os.path.join(HERE, "ho_samples_outcome.csv"))
    res = {}
    for p in ("L1", "L2", "L3", "LM"):
        for o in ("arm168", "pnl", "MFE24", "MAE24"):
            z = d[[p, o]].dropna()
            res["%s|%s" % (p, o)] = None if len(z) < 30 else round(float(spearmanr(z[p], z[o]).correlation), 4)
    out = dict(n=len(d), coverage={c: round(float(d[c].notna().mean()), 4) for c in ("L1", "L2", "L3", "LM", "arm168")},
               arm=round(float(d.arm168.mean()), 4), pnl_mean=round(float(d.pnl.mean()), 1),
               complete=round(float(d.win_complete.mean()), 4), ic=res)
    json.dump(out, open(os.path.join(HERE, "ho_ic.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "samples"
    {"samples": samples, "aux": aux, "proxies": proxies, "outcomes": outcomes, "score": score}[cmd]()
