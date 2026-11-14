#!/usr/bin/env python3
"""IND_COMBO P0 (prereg vz_e1_wt 14ed6c00, plan IND_COMBO_P0_PLAN.md) — tinh X causal (nen DA DONG truoc phut vao).
Output ~/claude_master/ind1114/legs_x.parquet, mkt_h.parquet, build.json. Khong tinh thong ke tren Y o day."""
import glob
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("indb")
W = "/home/ubuntu/claude_master/ind1114/"
H, D4, DAY, M1 = 3600000, 4 * 3600000, 86400000, 60000
TZ = 7 * H
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
P0, P1, P2, P3 = 1640970000000, 1704042000000, 1767200400000, 1782838800000  # 2022 / 2024 / 2026 / 2026-07 (+07)
CN = ["C%d" % i for i in range(1, 21)]
MN = ["M%d" % i for i in range(1, 7)]


def load_store():
    dt = np.dtype([("t", ">i8"), ("s", ">i2"), ("o", ">f4"), ("h", ">f4"), ("l", ">f4"), ("c", ">f4"), ("v", ">f4")])
    a = np.fromfile("/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin", dtype=dt)
    mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
    id2s = dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))
    df = pd.DataFrame(dict(sym=pd.Series(a["s"].astype(np.int32)).map(id2s).values, th=a["t"].astype(np.int64),
                           o=a["o"].astype(np.float32), h=a["h"].astype(np.float32), l=a["l"].astype(np.float32),
                           c=a["c"].astype(np.float32), qv=a["v"].astype(np.float32)))
    del a
    log.info("store rec %d sym %d unmapped %d", len(df), df.sym.nunique(), int(df.sym.isna().sum()))
    df = df[df.sym.notna()]
    ho = W + "ho26out/ho26_1h.parquet"
    if os.path.exists(ho):
        x = pd.read_parquet(ho)
        x = x[(x.th > df.th.max()) & (x.th <= P3 + DAY)][["sym", "th", "o", "h", "l", "c", "qv"]]
        for col in ("o", "h", "l", "c", "qv"):
            x[col] = x[col].astype(np.float32)
        df = pd.concat([df, x], ignore_index=True)
        log.info("+HO26 %d rec, th max %s", len(x), pd.to_datetime(df.th.max(), unit="ms"))
    return df.sort_values(["sym", "th"]).reset_index(drop=True)


def wilder(x, n):
    return x.ewm(alpha=1.0 / n, adjust=False).mean()


def rsi(c, n=14):
    d = c.diff()
    au, ad = wilder(d.clip(lower=0), n), wilder((-d).clip(lower=0), n)
    r = 100 - 100 / (1 + au / ad)
    r[(ad == 0) & (au > 0)] = 100.0
    r.iloc[:3 * n] = np.nan
    return r


def atr(h, l, c, n=14):
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    a = wilder(tr, n)
    a.iloc[:3 * n] = np.nan
    return a, tr


def stoch(h, l, c, n=14):
    ll, hh = l.rolling(n).min(), h.rolling(n).max()
    return (100 * (c - ll) / (hh - ll)).where(hh > ll)


def pctb(c, n=20):
    m, sd = c.rolling(n).mean(), c.rolling(n).std(ddof=0)
    return ((c - (m - 2 * sd)) / (4 * sd)).where(sd > 0)


def macdh(c, a):
    e12, e26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    m = e12 - e26
    hst = m - m.ewm(span=9, adjust=False).mean()
    hst.iloc[:78] = np.nan
    return (hst / a).where(a > 0)


def dmi(h, l, c, n=14):
    a, tr = atr(h, l, c, n)
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=h.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=h.index)
    tw = wilder(tr, n)
    pdi, mdi = 100 * wilder(pdm, n) / tw, 100 * wilder(mdm, n) / tw
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    adx = wilder(dx, n)
    adx.iloc[:4 * n] = np.nan
    pdi.iloc[:3 * n] = np.nan
    mdi.iloc[:3 * n] = np.nan
    return adx, pdi - mdi


def pct_rank(x, n=180, mn=90):
    v = x.to_numpy()
    out = np.full(len(v), np.nan)
    for i in range(len(v)):
        if np.isnan(v[i]):
            continue
        w = v[max(0, i - n + 1):i + 1]
        w = w[~np.isnan(w)]
        if len(w) >= mn:
            out[i] = float((w <= v[i]).mean())
    return pd.Series(out, index=x.index)


def resample(g, step):
    k = (g.index.to_numpy() - 1) // step
    a = g.groupby(k).agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), qv=("qv", "sum"), nh=("c", "size"))
    a.index = (a.index.to_numpy() + 1) * step
    a = a[a.nh == step // H]
    return a


def asof(bar_t, vals, q):
    j = np.searchsorted(bar_t, q, "right") - 1
    out = np.where(j >= 0, vals[np.clip(j, 0, len(vals) - 1)], np.nan)
    return out


def coin_ind(g):
    """g: DataFrame index = th (gio dong, luoi day du), cot o h l c qv. Tra (bang gio C*, bang ngay (c, sma50) cho breadth)."""
    c, h, l, o = g.c, g.h, g.l, g.o
    out = pd.DataFrame(index=g.index)
    a1, _ = atr(h, l, c)
    out["C1"] = rsi(c)
    out["C4"] = stoch(h, l, c)
    out["C6"] = pctb(c)
    out["C9"] = macdh(c, a1)
    out["C15"] = c / c.rolling(720, min_periods=360).max() - 1
    out["C18"] = np.nan
    base = g.qv.shift(1).rolling(168, min_periods=120)
    out["C19"] = ((g.qv - base.mean()) / base.std()).where(base.std() > 0)
    f4 = resample(g, D4)
    t4 = f4.index.to_numpy()
    x4 = pd.DataFrame(index=f4.index)
    a4, _ = atr(f4.h, f4.l, f4.c)
    x4["C2"] = rsi(f4.c)
    x4["C5"] = stoch(f4.h, f4.l, f4.c)
    x4["C7"] = pctb(f4.c)
    x4["C10"] = macdh(f4.c, a4)
    x4["C11"], _ = dmi(f4.h, f4.l, f4.c)
    red = f4.c < f4.o
    x4["C20"] = red.astype(int).groupby((~red).cumsum()).cumsum().astype(float)
    fd = resample(g, DAY)
    xd = pd.DataFrame(index=fd.index)
    ad, _ = atr(fd.h, fd.l, fd.c)
    xd["C3"] = rsi(fd.c)
    m20, s20 = fd.c.rolling(20).mean(), fd.c.rolling(20).std(ddof=0)
    xd["C8"] = pct_rank((4 * s20 / m20).where(m20 > 0))
    xd["C12"], xd["C13"] = dmi(fd.h, fd.l, fd.c)
    xd["C14"] = ((fd.c - fd.h.rolling(20).max()) / ad).where(ad > 0)
    s50, s200 = fd.c.rolling(50).mean(), fd.c.rolling(200).mean()
    xd["C16"], xd["C17"] = fd.c / s50 - 1, fd.c / s200 - 1
    th = g.index.to_numpy()
    for col in x4.columns:
        out[col] = asof(t4, x4[col].to_numpy(), th)
    for col in xd.columns:
        out[col] = asof(fd.index.to_numpy(), xd[col].to_numpy(), th)
    return out, fd.c, s50, f4, fd


def grid(g):
    g = g.set_index("th")[["o", "h", "l", "c", "qv"]].astype(np.float64)
    full = np.arange(g.index.min(), g.index.max() + H, H)
    g = g.reindex(full)
    miss = g.c.isna()
    g["c"] = g.c.ffill()
    for col in ("o", "h", "l"):
        g[col] = g[col].fillna(g.c)
    g["qv"] = g.qv.fillna(0.0)
    return g, int(miss.sum())


def load_legs():
    rows = []
    for s in SEEDS:
        f = "/home/ubuntu/kaggle_sim/out/nt-x14-s%d/storage/printDone.csv" % s
        d = pd.read_csv(f, on_bad_lines="skip")
        d.columns = [x.strip() for x in d.columns]
        d = d[d.level.astype(str).str.strip() == "PREDICT_SYMBOL_TRADE"].copy()
        d["seed"] = s
        rows.append(d[["seed", "sym", "start", "end", "margin", "pnl", "symbolPred"]])
    d = pd.concat(rows, ignore_index=True)
    d["sym"] = d.sym.astype(str).str.strip() + "USDT"
    t = pd.to_datetime(d.start.astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["M"] = (t.values.astype("datetime64[ms]").astype(np.int64) - TZ)
    d["yr"] = t.dt.year
    for col in ("margin", "pnl", "symbolPred"):
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d[(d.M >= P0) & (d.M < P3)].copy()
    d["per"] = np.where(d.M < P1, "E", np.where(d.M < P2, "C", "H"))
    d["y"] = 100.0 * d.pnl / d.margin
    return d.reset_index(drop=True)


def s1_rank(L):
    B = np.load("/home/ubuntu/claude_master/1004/gqd/cand_base.npz")
    mts, fi, SY = B["mts"], B["fi"], B["SY15"]
    mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
    s2id = dict(zip(mp.symbol.astype(str), mp.symId.astype(int)))
    i = np.searchsorted(mts, L.M.to_numpy())
    ok = (i < len(mts)) & (mts[np.clip(i, 0, len(mts) - 1)] == L.M.to_numpy())
    rk = np.full(len(L), np.nan)
    sid = L.sym.map(s2id).to_numpy()
    for k in np.nonzero(ok)[0]:
        if sid[k] != sid[k]:
            continue
        row = SY[fi[i[k]]][:24]
        w = np.nonzero(row == int(sid[k]))[0]
        if len(w):
            rk[k] = w[0] + 1
    return rk


def c18(L):
    """std r1m gio dong cuoi / std 24 gio dong cuoi, tu Vision close (2021-12..2025-12) + HO26 kernel."""
    th_last = (L.M.to_numpy() // H) * H
    need = {}
    for s, t in zip(L.sym.tolist(), th_last.tolist()):
        need.setdefault(s, set()).update(range(t - 23 * H, t + H, H))
    agg = {}
    fs = sorted(glob.glob("/home/ubuntu/claude_master/res1109/r1_s1/kl/kline1m-*.parquet"))
    for f in fs:
        t = pq.read_table(f, columns=["ts", "sym", "close"]).to_pandas()
        cat = t["sym"].astype("category")
        names = np.array([str(x) for x in cat.cat.categories])
        idx = cat.cat.codes.to_numpy().astype(np.int64)
        ts = t["ts"].to_numpy().astype(np.int64)
        cl = t["close"].to_numpy().astype(np.float64)
        del t, cat
        o = np.lexsort((ts, idx))
        idx, ts, cl = idx[o], ts[o], cl[o]
        same = (idx[1:] == idx[:-1]) & (np.diff(ts) == M1)
        r = np.where(same, np.log(cl[1:] / cl[:-1]), np.nan)
        idx, ts = idx[1:], ts[1:]
        ok = np.isfinite(r)
        idx, ts, r = idx[ok], ts[ok], r[ok]
        th = (ts // H) * H + H
        key = idx.astype(np.int64) * (1 << 42) + th
        u, inv = np.unique(key, return_inverse=True)
        sr, sr2, n = np.bincount(inv, r), np.bincount(inv, r * r), np.bincount(inv)
        ui, ut = u >> 42, u & ((1 << 42) - 1)
        for k in range(len(u)):
            s = names[ui[k]]
            if s in need and int(ut[k]) in need[s]:
                agg[(s, int(ut[k]))] = (sr[k], sr2[k], n[k])
        log.info("C18 %s agg %d", os.path.basename(f), len(agg))
    ho = W + "ho26out/ho26_1h.parquet"
    if os.path.exists(ho):
        x = pd.read_parquet(ho, columns=["sym", "th", "sr", "sr2", "n"])
        x = x[x.th > 1767225600000]
        for s, t, a, b, n in zip(x.sym, x.th, x.sr, x.sr2, x.n):
            if s in need and int(t) in need[s] and n == n:
                agg[(s, int(t))] = (a, b, n)
    out = np.full(len(L), np.nan)
    for k, (s, t) in enumerate(zip(L.sym.tolist(), th_last.tolist())):
        a = agg.get((s, t))
        if a is None or a[2] < 45:
            continue
        S = Q = N = 0.0
        for h in range(t - 23 * H, t + H, H):
            b = agg.get((s, h))
            if b is not None:
                S, Q, N = S + b[0], Q + b[1], N + b[2]
        if N < 1080:
            continue
        v1 = a[1] / a[2] - (a[0] / a[2]) ** 2
        v24 = Q / N - (S / N) ** 2
        if v1 > 0 and v24 > 0:
            out[k] = np.sqrt(v1 / v24)
    return out


def market(BTC4, BTCD, breadth):
    Z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
    t = Z["ew_ts"].astype(np.int64)
    if t[0] < 10 ** 12:
        t = t * 60000
    r = np.nan_to_num(Z["ew_r"].astype(np.float64))
    ho = W + "ho26out/ho26_ew.parquet"
    if os.path.exists(ho):
        x = pd.read_parquet(ho)
        m = x.ts.to_numpy() > t.max()
        t = np.concatenate([t, x.ts.to_numpy()[m].astype(np.int64)])
        r = np.concatenate([r, np.nan_to_num(x.ew.to_numpy()[m])])
    o = np.argsort(t)
    t, r = t[o], r[o]
    th = (t // H) * H + H
    hs = pd.DataFrame(dict(th=th, r=r, q=r * r)).groupby("th").agg(S=("r", "sum"), Q=("q", "sum"), N=("r", "size"))
    full = np.arange(hs.index.min(), hs.index.max() + H, H)
    hs = hs.reindex(full).fillna(0.0)
    I = hs.S.cumsum()
    M5 = np.exp(I - I.rolling(720, min_periods=360).max()) - 1
    def rv(n, mn):
        S, Q, N = hs.S.rolling(n).sum(), hs.Q.rolling(n).sum(), hs.N.rolling(n).sum()
        v = (Q / N - (S / N) ** 2).where(N >= mn)
        return np.sqrt(v.clip(lower=0))
    M6 = (rv(24, 1200) / rv(720, 30000)).replace([np.inf], np.nan)
    tg = hs.index.to_numpy()
    mk = pd.DataFrame(dict(th=tg))
    mk["M1"] = asof(BTC4.index.to_numpy(), BTC4.to_numpy(), tg)
    mk["M2"] = asof(BTCD["rsi"].index.to_numpy(), BTCD["rsi"].to_numpy(), tg)
    mk["M3"] = asof(BTCD["s200"].index.to_numpy(), BTCD["s200"].to_numpy(), tg)
    bd = pd.Series(breadth)
    mk["M4"] = asof(bd.index.to_numpy(), bd.to_numpy(), tg)
    mk["M5"] = M5.to_numpy()
    mk["M6"] = M6.to_numpy()
    return mk


def main():
    t0 = time.time()
    L = load_legs()
    log.info("legs %d per %s", len(L), L.per.value_counts().to_dict())
    L["rank"] = s1_rank(L)
    S = load_store()
    th_last = (L.M.to_numpy() // H) * H
    X = np.full((len(L), 20), np.nan)
    bnum, bden = {}, {}
    miss_tot, nsym = 0, 0
    legs_by = {s: np.nonzero(L.sym.to_numpy() == s)[0] for s in L.sym.unique()}
    BTC4 = BTCD = None
    for s, g in S.groupby("sym", sort=False):
        if len(g) < 48:
            continue
        gg, miss = grid(g)
        miss_tot += miss
        nsym += 1
        ind, dc, s50, f4, fd = coin_ind(gg)
        ok = s50.notna()
        for dd, a in zip(dc.index[ok].tolist(), (dc[ok] > s50[ok]).tolist()):
            bnum[dd] = bnum.get(dd, 0) + int(a)
            bden[dd] = bden.get(dd, 0) + 1
        if s == "BTCUSDT":
            BTC4 = rsi(f4.c)
            BTCD = dict(rsi=rsi(fd.c), s200=fd.c / fd.c.rolling(200).mean() - 1)
        if s in legs_by:
            k = legs_by[s]
            j = np.searchsorted(ind.index.to_numpy(), th_last[k], "right") - 1
            okj = (j >= 0) & (ind.index.to_numpy()[np.clip(j, 0, len(ind) - 1)] == th_last[k])
            vals = ind[CN].to_numpy()
            X[k[okj]] = vals[j[okj]]
    log.info("coin %d, gio thieu (ffill) %d, %ds", nsym, miss_tot, round(time.time() - t0))
    for i, cn in enumerate(CN):
        L[cn] = X[:, i]
    L["C18"] = c18(L)
    breadth = {d: 100.0 * bnum[d] / bden[d] for d in sorted(bden) if bden[d] >= 20}
    MK = market(BTC4, BTCD, breadth)
    MK.to_parquet(W + "mkt_h.parquet", index=False)
    j = np.searchsorted(MK.th.to_numpy(), th_last, "right") - 1
    okm = (j >= 0) & (MK.th.to_numpy()[np.clip(j, 0, len(MK) - 1)] == th_last)
    for mn in MN:
        L[mn] = np.where(okm, MK[mn].to_numpy()[np.clip(j, 0, len(MK) - 1)], np.nan)
    # cum (dot): hop phut vao 8 seed, cach <= 60'
    u = np.unique(L.M.to_numpy())
    cid = np.cumsum(np.r_[True, np.diff(u) > 60 * M1])
    L["clu"] = cid[np.searchsorted(u, L.M.to_numpy())]
    L.to_parquet(W + "legs_x.parquet", index=False)
    nan = {c: round(float(L[c].isna().mean()), 4) for c in CN + MN}
    info = dict(n=len(L), per=L.per.value_counts().to_dict(), rank_nan=int(L["rank"].isna().sum()),
                y_nan=int(L.y.isna().sum()), nan_frac=nan, clusters={p: int(L[L.per == p].clu.nunique()) for p in "ECH"},
                legs_yr=L.groupby("yr").size().to_dict(), sec=round(time.time() - t0))
    json.dump(info, open(W + "build.json", "w"), indent=1, default=str)
    log.info("XONG %s", json.dumps(info, default=str))


if __name__ == "__main__":
    main()
