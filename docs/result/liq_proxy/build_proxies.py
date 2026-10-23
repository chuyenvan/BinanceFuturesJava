#!/usr/bin/env python3
"""LIQ_PROXY build (v2, memory-bounded) — samples, aux tables, proxies, outcomes.

Prereg: docs/prereg/PREREG_LIQ_PROXY.md (a468b743, sha256 e304fa44...).
UTC everywhere; printDone start local +07 -> -7h.
"""
import argparse
import gc
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
KSOUT = "/home/ubuntu/kaggle_sim/out"
MET = "/home/ubuntu/vz/out/metrics5m"
KL = "/home/ubuntu/vz_e1/raw"
FLAGS = "/home/ubuntu/claude_master/tsx/flags.json"
TAGS = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]
M = 60_000
G5 = 5 * M
LAG = 10 * M
H7 = pd.Timedelta(hours=7)
P_START = pd.Timestamp("2022-01-01")
P_END = pd.Timestamp("2026-01-01")


def month_iter(y0, m0, y1, m1):
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def mpath(prefix, y, m):
    return os.path.join(prefix, str(y), "%04d-%02d.parquet" % (y, m)) if prefix == MET else \
        os.path.join(prefix, "kline1m-%04d-%02d.parquet" % (y, m))


# ---------------------------------------------------------------- samples
def build_samples():
    frames = []
    for tag in TAGS:
        d = pd.read_csv(os.path.join(KSOUT, "tsx-x14-" + tag, "storage", "printDone.csv"), index_col=False)
        d.columns = [c.strip() for c in d.columns]
        for c in ("entry", "pnl", "margin", "pred15m"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["sym"] = d["sym"].astype(str).str.strip()
        d["sym"] = np.where(d["sym"].str.endswith("USDT"), d["sym"], d["sym"] + "USDT")
        d = d.dropna(subset=["entry", "pnl", "pred15m"])
        d = d[d["entry"] > 0]
        d["start_u"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - H7
        d["end_u"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M") - H7
        d["seed"] = tag
        frames.append(d[["sym", "entry", "pnl", "pred15m", "start_u", "end_u", "seed"]])
    d = pd.concat(frames, ignore_index=True)
    d["hour_u"] = d["end_u"].dt.floor("h")

    g = (d.groupby(["sym", "hour_u", "seed"], as_index=False)
           .agg(anchor=("start_u", "min"), pnl=("pnl", "sum"), nleg=("pnl", "size")))
    a = d.merge(g[["sym", "hour_u", "seed", "anchor"]], on=["sym", "hour_u", "seed"])
    a = a[a.start_u == a.anchor].sort_values("start_u").drop_duplicates(["sym", "hour_u", "seed"])
    g = g.merge(a[["sym", "hour_u", "seed", "entry", "pred15m"]], on=["sym", "hour_u", "seed"], how="left")
    cl = (g.groupby(["sym", "anchor"], as_index=False)
            .agg(pnl=("pnl", "mean"), nseed=("seed", "nunique"), nleg=("nleg", "mean"),
                 entry=("entry", "first"), pred15m=("pred15m", "mean")))
    cl["kind"] = "cluster"

    lg = (d.groupby(["sym", "start_u", "entry"], as_index=False)
            .agg(pnl=("pnl", "mean"), nseed=("seed", "nunique"), pred15m=("pred15m", "mean")))
    lg["anchor"] = lg["start_u"]
    lg["nleg"] = 1.0
    lg["kind"] = "leg"

    out = []
    for x in (cl, lg):
        x = x[(x.anchor >= P_START) & (x.anchor < P_END)].copy()
        x["t_ms"] = (x.anchor.astype("int64") // 10 ** 6)
        x["g_ms"] = (((x.t_ms - LAG) // G5) * G5).astype("int64")
        out.append(x)
    cols = ["kind", "sym", "anchor", "t_ms", "g_ms", "entry", "pnl", "pred15m", "nseed", "nleg"]
    s = pd.concat([x[cols] for x in out], ignore_index=True)

    fl = json.load(open(FLAGS))["ranges"].split(",")
    ranges = []
    for r in fl:
        a0, b0 = r.split("-")
        ranges.append((pd.Timestamp(a0), pd.Timestamp(b0) + pd.Timedelta(days=1)))
    day = s.anchor.dt.normalize()
    ep = np.array(["NA"] * len(s), dtype=object)
    for a0, b0 in ranges:
        m = (day >= a0) & (day < b0)
        ep[m] = a0.strftime("%Y%m%d") + "-" + (b0 - pd.Timedelta(days=1)).strftime("%Y%m%d")
    for i in np.where(ep == "NA")[0]:
        ep[i] = day.iloc[i].strftime("%Y-%m")
    s["episode"] = ep
    s["year"] = s.anchor.dt.year
    s["period"] = np.where(s.year <= 2023, "disc", np.where(s.year <= 2025, "test", "ho"))
    s.to_csv(os.path.join(HERE, "samples.csv"), index=False)
    print("samples", s.kind.value_counts().to_dict())
    print(s.groupby(["period", "kind"]).size().to_string())


# ---------------------------------------------------------------- aux (kline)
def build_aux():
    import pyarrow.parquet as pq
    s = pd.read_csv(os.path.join(HERE, "samples.csv"))
    need = {}
    for r in s.itertuples():
        g = int(r.g_ms)
        for j in range(3):
            need.setdefault(pd.Timestamp(g, unit="ms").year, set()).add(int(g - 15 * M + j * G5))
    daily, l2 = {}, {}
    for y, m in month_iter(2021, 12, 2025, 12):
        f = mpath(KL, y, m)
        pf = pq.ParquetFile(f)
        nb = need.get(y, set())
        for batch in pf.iter_batches(batch_size=1_500_000, columns=["ts", "sym", "taker_buy_quote", "quote_volume"]):
            d = batch.to_pandas()
            d["sym"] = d["sym"].astype(str)
            d["tbq"] = d["taker_buy_quote"].astype("float32")
            d["qv"] = d["quote_volume"].astype("float32")
            d["day"] = pd.to_datetime(d.ts, unit="ms").dt.normalize()
            z = d.groupby(["sym", "day"], sort=False)[["tbq", "qv"]].sum()
            for (sym, day), r in z.iterrows():
                k = (sym, day)
                v = daily.get(k)
                daily[k] = (float(r.tbq), float(r.qv)) if v is None else (v[0] + float(r.tbq), v[1] + float(r.qv))
            d["b5"] = (d.ts // G5) * G5
            z2 = d[d.b5.isin(nb)]
            if len(z2):
                z2 = z2.groupby(["sym", "b5"], sort=False)[["tbq", "qv"]].sum()
                for (sym, b5), r in z2.iterrows():
                    k = (sym, int(b5))
                    v = l2.get(k)
                    l2[k] = (float(r.tbq), float(r.qv)) if v is None else (v[0] + float(r.tbq), v[1] + float(r.qv))
            del d, z, z2
        print("aux", y, m, flush=True)
        gc.collect()
    pd.DataFrame([(k[0], k[1], v[0], v[1]) for k, v in daily.items()],
                 columns=["sym", "day", "tbq", "qv"]).to_csv(os.path.join(HERE, "aux_daily.csv"), index=False)
    pd.DataFrame([(k[0], k[1], v[0], v[1]) for k, v in l2.items()],
                 columns=["sym", "b5", "tbq", "qv"]).to_csv(os.path.join(HERE, "aux_l2.csv"), index=False)
    print("aux done", len(daily), len(l2))


# ---------------------------------------------------------------- proxies
def build_proxies():
    s = pd.read_csv(os.path.join(HERE, "samples.csv"))
    s["anchor"] = pd.to_datetime(s["anchor"])
    for c in ("L1", "L2", "L3", "LM", "oi_z", "oi_delta24h", "ls_global", "ls_toptrader",
              "taker_buy15", "oi_val_g"):
        s[c] = np.nan
    daily = pd.read_csv(os.path.join(HERE, "aux_daily.csv"))
    daily["day"] = pd.to_datetime(daily.day)
    sell = (daily.assign(sell=1 - daily.tbq / daily.qv)
                 .pivot_table(index="day", columns="sym", values="sell"))
    qv = daily.pivot_table(index="day", columns="sym", values="qv")
    l2 = pd.read_csv(os.path.join(HERE, "aux_l2.csv"))

    carry = {}  # sym -> [n, sum, sumsq]
    for y, m in month_iter(2021, 12, 2025, 12):
        mon = pd.Timestamp(y, m, 1); nxt = mon + pd.offsets.MonthBegin(1)
        idx = [i for i in s.index if mon - pd.Timedelta(days=2) <= s.at[i, "anchor"] < nxt + pd.Timedelta(days=2)]
        md = pd.read_parquet(mpath(MET, y, m), columns=["ts", "sym", "oi", "oi_value", "ls_cnt", "toptrader_ls_cnt"])
        md["sym"] = md["sym"].astype(str)
        md["avail"] = md["ts"] + 300_000
        md = md.sort_values(["sym", "avail"])
        md["cz"] = md.groupby("sym", sort=False)["oi"].cumsum()
        md["cz2"] = (md["oi"].astype("float64") ** 2).groupby(md["sym"], sort=False).cumsum()
        md["cn"] = md.groupby("sym", sort=False).cumcount() + 1

        if idx:
            sub = s.loc[idx]
            G = set(sub.g_ms.astype("int64"))
            Ts = set()
            for o in (0, -60 * M, -15 * M, -30 * M, -40 * M, -1440 * M):
                Ts |= {int(x) + o for x in G}
            mp = md[md.avail.isin(Ts)]
            oi = mp.pivot_table(index="avail", columns="sym", values="oi", aggfunc="last")
            oiv = mp.pivot_table(index="avail", columns="sym", values="oi_value", aggfunc="last")
            ls = mp.pivot_table(index="avail", columns="sym", values="ls_cnt", aggfunc="last")
            lst = mp.pivot_table(index="avail", columns="sym", values="toptrader_ls_cnt", aggfunc="last")
            zg = md[md.avail.isin(G)][["avail", "sym", "oi", "cz", "cz2", "cn"]]
            syms = oi.columns

            needp = set()
            for i in idx:
                g = int(s.at[i, "g_ms"])
                needp |= {g - M, g - 16 * M, g - 31 * M, g - 61 * M}
            kp = pd.read_parquet(mpath(KL, y, m), columns=["ts", "sym", "close"],
                                 filters=[("ts", "in", sorted(needp))])
            kp["sym"] = kp["sym"].astype(str)
            px = kp.pivot_table(index="ts", columns="sym", values="close", aggfunc="last")
        else:
            oi = oiv = ls = lst = px = pd.DataFrame()
            mp = kp = pd.DataFrame()
            zg = pd.DataFrame(columns=["avail", "sym", "oi", "cz", "cz2", "cn"])
            syms = pd.Index([])

        def S(tab, t):
            return tab.loc[t].reindex(syms) if (not tab.empty and t in tab.index) else pd.Series(np.nan, index=syms)

        for i in idx:
            g = int(s.at[i, "g_ms"]); sym = s.at[i, "sym"]
            oi_n, oi_p = S(oi, g), S(oi, g - 60 * M)
            oiv_n = S(oiv, g)
            px_n, px_p = S(px, g - M), S(px, g - 61 * M)
            r60 = px_n / px_p - 1
            l1 = (-(oi_n / oi_p - 1)).where(r60 < 0, 0.0)
            l1 = l1.where(np.isfinite(l1) & np.isfinite(oiv_n) & (oiv_n > 0))
            if sym not in l1.index or not np.isfinite(l1.get(sym, np.nan)):
                continue
            s.at[i, "L1"] = float(l1[sym]); s.at[i, "oi_val_g"] = float(oiv_n[sym])

            # L2
            q = l2[(l2.sym == sym) & (l2.b5 >= g - 15 * M) & (l2.b5 < g)]
            if len(q) == 3 and q.qv.sum() > 0:
                sell15 = 1 - q.tbq.sum() / q.qv.sum()
                d0 = pd.Timestamp(g, unit="ms").normalize()
                dts = [d0 - pd.Timedelta(days=k) for k in range(1, 8)]
                vals = []
                for dday in dts:
                    if dday in sell.index and sym in sell.columns and np.isfinite(sell.at[dday, sym]):
                        vals.append(float(sell.at[dday, sym]))
                if len(vals) >= 5:
                    s.at[i, "L2"] = sell15 - float(np.median(vals))
                s.at[i, "taker_buy15"] = float(q.tbq.sum() / q.qv.sum())

            # L3
            def l15(c):
                o1, o0 = S(oi, c), S(oi, c - 15 * M)
                p1, p0 = S(px, c - M), S(px, c - 16 * M)
                v = (-(o1 / o0 - 1)).where(p1 / p0 - 1 < 0, 0.0)
                return float(v.get(sym, np.nan))
            a, b = l15(g), l15(g - 15 * M)
            if np.isfinite(a) and np.isfinite(b):
                s.at[i, "L3"] = a - b

            o24 = S(oi, g - 1440 * M)
            s.at[i, "oi_delta24h"] = float((oi_n / o24 - 1).get(sym, np.nan))
            s.at[i, "ls_global"] = float(S(ls, g).get(sym, np.nan))
            s.at[i, "ls_toptrader"] = float(S(lst, g).get(sym, np.nan))
            zz = zg[(zg.avail == g) & (zg.sym == sym)]
            if len(zz):
                r = zz.iloc[0]
                pn, ps, ps2 = carry.get(sym, (0, 0.0, 0.0))
                n = pn + r.cn; sm = ps + r.cz; sm2 = ps2 + r.cz2
                mu = sm / n; var = max(sm2 / n - mu * mu, 0.0)
                if var > 0:
                    s.at[i, "oi_z"] = float((r.oi - mu) / np.sqrt(var))

            prev = pd.Timestamp(g, unit="ms").normalize() - pd.Timedelta(days=1)
            if prev in qv.index:
                qd = qv.loc[prev].dropna()
                uni = qd.index[qd >= 20e6].intersection(l1.index)
                w = oiv_n.reindex(uni); v = l1.reindex(uni)
                msk = np.isfinite(w) & np.isfinite(v) & (w > 0)
                if msk.sum() >= 5:
                    s.at[i, "LM"] = float((v[msk] * w[msk]).sum() / w[msk].sum())

        # carry expanding stats
        agg = md.groupby("sym", sort=False).agg(n=("oi", "size"), s=("oi", "sum"))
        agg2 = (md["oi"].astype("float64") ** 2).groupby(md["sym"], sort=False).sum()
        for sym in agg.index:
            pn, ps, ps2 = carry.get(sym, (0, 0.0, 0.0))
            carry[sym] = (pn + int(agg.at[sym, "n"]), ps + float(agg.at[sym, "s"]), ps2 + float(agg2.get(sym, 0.0)))
        print("proxy", y, m, len(idx), flush=True)
        del md, mp, oi, oiv, ls, lst, px, kp, zg
        gc.collect()

    s.to_csv(os.path.join(HERE, "samples_proxy.csv"), index=False)
    print("coverage", {c: int(s[c].notna().sum()) for c in ["L1", "L2", "L3", "LM", "oi_z", "oi_delta24h"]})
    print(s.groupby("period")[["L1", "L2", "L3", "LM"]].apply(lambda y: y.notna().mean()).to_string())


# ---------------------------------------------------------------- outcomes
def build_outcomes():
    s = pd.read_csv(os.path.join(HERE, "samples_proxy.csv"))
    for c in ("maxh168", "minl168", "maxh24", "minl24"):
        s[c] = np.nan
    s["win_complete"] = False
    s["t_end"] = s.t_ms + 168 * 60 * M
    for y, m in month_iter(2022, 1, 2026, 1):
        mon = pd.Timestamp(y, m, 1); nxt = mon + pd.offsets.MonthBegin(1)
        lo_m = int(mon.value // 10 ** 6); hi_m = int(nxt.value // 10 ** 6)
        idx = [i for i in s.index if s.at[i, "t_ms"] < hi_m and s.at[i, "t_end"] > lo_m]
        if not idx:
            continue
        try:
            kd = pd.read_parquet(mpath(KL, y, m), columns=["ts", "sym", "high", "low"])
        except FileNotFoundError:
            print("MISSING kline", y, m, flush=True); continue
        kd["sym"] = kd["sym"].astype(str)
        G = {sym: (g.ts.to_numpy(np.int64), g.high.to_numpy(np.float64), g.low.to_numpy(np.float64))
             for sym, g in kd.groupby("sym", sort=False)}
        for i in idx:
            sym = s.at[i, "sym"]
            if sym not in G:
                continue
            ts, hi, low = G[sym]
            t = int(s.at[i, "t_ms"]); t24 = t + 24 * 60 * M; t168 = int(s.at[i, "t_end"])
            a = np.searchsorted(ts, max(t, lo_m), "left")
            b = np.searchsorted(ts, min(t168, hi_m), "left")
            if b > a:
                h = np.nanmax(hi[a:b]); l = np.nanmin(low[a:b])
                if not np.isfinite(s.at[i, "maxh168"]) or h > s.at[i, "maxh168"]:
                    s.at[i, "maxh168"] = float(h)
                if not np.isfinite(s.at[i, "minl168"]) or l < s.at[i, "minl168"]:
                    s.at[i, "minl168"] = float(l)
            b24 = np.searchsorted(ts, min(t24, hi_m), "left")
            if b24 > a:
                h = np.nanmax(hi[a:b24]); l = np.nanmin(low[a:b24])
                if not np.isfinite(s.at[i, "maxh24"]) or h > s.at[i, "maxh24"]:
                    s.at[i, "maxh24"] = float(h)
                if not np.isfinite(s.at[i, "minl24"]) or l < s.at[i, "minl24"]:
                    s.at[i, "minl24"] = float(l)
            if t168 <= hi_m:
                s.at[i, "win_complete"] = True
        print("outcome", y, m, len(idx), flush=True)
        del kd, G
        gc.collect()
    e = s.entry.to_numpy(float)
    s["arm168"] = np.where(np.isfinite(s.maxh168), (s.maxh168.to_numpy(float) >= e * 1.07).astype(float), np.nan)
    s["MFE24"] = s.maxh24.to_numpy(float) / e - 1.0
    s["MAE24"] = s.minl24.to_numpy(float) / e - 1.0
    s.loc[~np.isfinite(s.maxh24), ["MFE24", "MAE24"]] = np.nan
    s.to_csv(os.path.join(HERE, "samples_outcome.csv"), index=False)
    print("outcome coverage", s.groupby("kind")[["arm168", "MFE24", "MAE24"]].apply(lambda x: x.notna().mean()).to_string())
    print("win_complete", s.groupby("kind").win_complete.mean().to_dict())
    print("arm rate", s.groupby("kind").arm168.mean().to_dict())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["samples", "aux", "proxies", "outcomes"])
    a = ap.parse_args()
    if a.stage == "samples":
        build_samples()
    elif a.stage == "aux":
        build_aux()
    elif a.stage == "proxies":
        build_proxies()
    else:
        build_outcomes()
