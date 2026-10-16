#!/usr/bin/env python3
"""VZ R2X bookDepth 2023+2025 (pre-reg docs/prereg/PREREG_VZ_R2X_BOOKDEPTH.md). Usage: plan | fetch | feat | check | test
Sinh tu r2_bookdepth.py; chi doi: nhieu nam, ten file, V2 = addendum 1 R2 (kline Vision daily), test bao them theo nam."""
import concurrent.futures as cf
import io
import json
import logging
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("r2")
PD = "/home/ubuntu/kaggle_sim/out/gqsf-a1/storage/printDone.csv"
W = "/home/ubuntu/vz_bd"
RAW = W + "/raw"
URL = "https://data.binance.vision/data/futures/um/daily/bookDepth/{s}/{s}-bookDepth-{d}.zip"
YEARS = (2023, 2025)
TAG = "2023_2025"
KURL = "https://data.binance.vision/data/futures/um/daily/klines/{s}/1m/{s}-1m-{d}.zip"
KRAW = W + "/kraw"
MIN_BURST = 6
SEED = 20261016


def legs():
    d = pd.read_csv(PD, index_col=False)
    d["t0_local"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
    d["t0"] = d["t0_local"] - pd.Timedelta(hours=7)  # GMT+7 -> UTC
    d["burst_n"] = d.groupby("t0").pnl.transform("size")
    d = d[(d.burst_n >= MIN_BURST) & (d.t0.dt.year.isin(YEARS))].copy()
    d["symbol"] = d["sym"].astype(str) + "USDT"
    d["ret"] = d.pnl / d.margin
    d["t_dec"] = d.t0 + pd.Timedelta(seconds=60)
    return d.reset_index(drop=True)


def plan():
    d = legs()
    need = set()
    for s, t in zip(d.symbol, d.t_dec):
        for k in (0, 1):
            need.add((s, (t - pd.Timedelta(days=k)).strftime("%Y-%m-%d")))
    log.info("legs=%d bursts=%d days=%d files=%d", len(d), d.t0.nunique(), d.t0.dt.date.nunique(), len(need))
    return d, sorted(need)


def get(sd):
    s, day = sd
    p = "%s/%s/%s.zip" % (RAW, s, day)
    if os.path.exists(p):
        return s, day, "have"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for i in range(3):
        try:
            with urllib.request.urlopen(URL.format(s=s, d=day), timeout=60) as r:
                b = r.read()
            open(p + ".tmp", "wb").write(b)
            os.replace(p + ".tmp", p)
            return s, day, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return s, day, "404"
            time.sleep(2 * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    return s, day, "fail"


def kget(sd):
    s, day = sd
    p = "%s/%s/%s.zip" % (KRAW, s, day)
    if os.path.exists(p):
        return s, day, "have"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for i in range(3):
        try:
            with urllib.request.urlopen(KURL.format(s=s, d=day), timeout=60) as r:
                b = r.read()
            open(p + ".tmp", "wb").write(b)
            os.replace(p + ".tmp", p)
            return s, day, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return s, day, "404"
            time.sleep(2 * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    return s, day, "fail"


def fetch():
    d0, need = plan()
    kneed = sorted({(s, t.strftime("%Y-%m-%d")) for s, t in zip(d0.symbol, d0.t0)} |
                   {(s, (t - pd.Timedelta(minutes=1)).strftime("%Y-%m-%d")) for s, t in zip(d0.symbol, d0.t0)})
    kst = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for s_, day_, r in ex.map(kget, kneed):
            kst[r] = kst.get(r, 0) + 1
    log.info("kline fetch DONE %s", kst)
    st = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for i, (s, day, r) in enumerate(ex.map(get, need)):
            st[r] = st.get(r, 0) + 1
            if i % 200 == 0:
                log.info("fetch %d/%d %s", i, len(need), st)
    log.info("fetch DONE %s", st)


def load_day(s, day):
    p = "%s/%s/%s.zip" % (RAW, s, day)
    if not os.path.exists(p):
        return None
    with zipfile.ZipFile(p) as z:
        b = z.read(z.namelist()[0])
    x = pd.read_csv(io.BytesIO(b))
    x["ts"] = pd.to_datetime(x["timestamp"])
    return x[["ts", "percentage", "depth", "notional"]]


def feat():
    d, _ = plan()
    rows = []
    for s, g in d.groupby("symbol"):
        cache = {}
        for i, r in g.iterrows():
            t = r.t_dec
            parts = []
            for k in (1, 0):
                day = (t - pd.Timedelta(days=k)).strftime("%Y-%m-%d")
                if day not in cache:
                    cache[day] = load_day(s, day)
                if cache[day] is not None:
                    parts.append(cache[day])
            out = dict(idx=i, snap_ts=pd.NaT, F1=np.nan, F2=np.nan, F3=np.nan, mid=np.nan, cov24=0)
            if parts:
                x = pd.concat(parts)
                x = x[(x.ts <= t) & (x.ts > t - pd.Timedelta(hours=24))]
                if len(x):
                    piv = x.pivot_table(index="ts", columns="percentage", values="notional", aggfunc="last")
                    dep = x.pivot_table(index="ts", columns="percentage", values="depth", aggfunc="last")
                    last = piv.index.max()
                    if last >= t - pd.Timedelta(minutes=5) and all(c in piv.columns for c in (-1, 1, -5)):
                        b1, a1, b5 = piv.loc[last, -1], piv.loc[last, 1], piv.loc[last, -5]
                        out.update(snap_ts=last, cov24=int(len(piv)),
                                   F1=b1 / np.nanmedian(piv[-1]), F2=(b1 - a1) / (b1 + a1), F3=b5 / np.nanmedian(piv[-5]),
                                   mid=0.5 * (b1 / dep.loc[last, -1] + a1 / dep.loc[last, 1]))
            rows.append(out)
    f = pd.DataFrame(rows).set_index("idx")
    d = d.join(f)
    d.to_parquet(W + "/r2x_legs_%s.parquet" % TAG + "")
    log.info("feat rows=%d with F1=%d", len(d), int(d.F1.notna().sum()))


def kline_day(s, day):
    p = "%s/%s/%s.zip" % (KRAW, s, day)
    if not os.path.exists(p):
        return None
    with zipfile.ZipFile(p) as z:
        b = z.read(z.namelist()[0])
    x = pd.read_csv(io.BytesIO(b), header=None)
    if not str(x.iloc[0, 0]).isdigit():
        x = x.iloc[1:]
    x = x.iloc[:, :5].astype(float)
    x.columns = ["ot", "open", "high", "low", "close"]
    return x.set_index(x.ot.astype("int64"))


def check():
    d = pd.read_parquet(W + "/r2x_legs_%s.parquet" % TAG)
    v1 = bool((d.snap_ts.dropna() <= d.t_dec[d.snap_ts.notna()]).all())
    cov = float(d.F1.notna().mean())
    cache, inband = {}, []
    for i, r in d.iterrows():
        if pd.isna(r.mid):
            continue
        lo, hi = np.inf, -np.inf
        for tb in (r.t0 - pd.Timedelta(minutes=1), r.t0):
            key = (r.symbol, tb.strftime("%Y-%m-%d"))
            if key not in cache:
                cache[key] = kline_day(*key)
            k = cache[key]
            ms = int(tb.value // 10**6)
            if k is not None and ms in k.index:
                lo, hi = min(lo, k.at[ms, "low"]), max(hi, k.at[ms, "high"])
        if np.isfinite(lo):
            inband.append(lo * 0.998 <= r.mid <= hi * 1.002)
    v2 = float(np.mean(inband)) if inband else 0.0
    miss = sorted(d.loc[d.F1.isna(), "symbol"].unique())[:30]
    res = dict(V1_causal=v1, V2_mid_in_band=v2, V2_n=len(inband), V3_coverage=cov, V3_ok=cov >= 0.8, V2_ok=v2 >= 0.95,
               missing_syms=miss, n_legs=len(d), by_year={int(y): int(n) for y, n in d.t0.dt.year.value_counts().items()})
    log.info("CHECK %s", json.dumps(res))
    json.dump(res, open(W + "/r2x_check_%s.json" % TAG, "w"), indent=1)


def boot_ci(day_vals, nrep=2000, block=5):
    """day_vals: Series index=date -> list of values; block bootstrap theo ngay (block 5 ngay lien tiep)."""
    days = sorted(day_vals.index)
    rng = np.random.default_rng(SEED)
    nb = max(1, len(days) // block)
    blocks = [days[i:i + block] for i in range(0, len(days), block)]
    stats = []
    for _ in range(nrep):
        pick = rng.integers(0, len(blocks), size=nb)
        vals = [v for j in pick for dd in blocks[j] for v in day_vals[dd]]
        stats.append(np.mean(vals))
    return [float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))]


def test():
    d = pd.read_parquet(W + "/r2x_legs_%s.parquet" % TAG + "")
    chk = json.load(open(W + "/r2x_check_%s.json" % TAG + ""))
    assert chk["V1_causal"] and chk["V2_ok"] and chk["V3_ok"], ("kiem du lieu FAIL -> khong tinh outcome", chk)
    out = {}
    for fk in ("F1", "F2", "F3"):
        ics, spreads = {}, {}
        for t0, g in d.dropna(subset=[fk]).groupby("t0"):
            if len(g) < MIN_BURST:
                continue
            ic = g[fk].rank().corr(g.ret.rank())
            hi = g[g[fk] >= g[fk].median()].ret.mean()
            lo = g[g[fk] < g[fk].median()].ret.mean()
            day = t0.date()
            ics.setdefault(day, []).append(ic)
            spreads.setdefault(day, []).append(hi - lo)
        ics_s = pd.Series(ics)
        allv = [v for vs in ics.values() for v in vs]
        out[fk] = dict(n_bursts=len(allv), mean_ic=float(np.mean(allv)), ci=boot_ci(ics_s),
                       mean_spread_hi_lo=float(np.mean([v for vs in spreads.values() for v in vs])))
        log.info("T %s %s", fk, out[fk])
    b = d.dropna(subset=["F1"]).groupby("t0").agg(f1=("F1", "median"), pnl=("pnl", "sum"), mg=("margin", "sum"))
    b["ret"] = b.pnl / b.mg
    rho = float(b.f1.rank().corr(b.ret.rank()))
    vals = {}
    rng_days = b.index.date
    # bootstrap Spearman theo ngay
    days = sorted(set(rng_days))
    blocks = [days[i:i + 5] for i in range(0, len(days), 5)]
    rng = np.random.default_rng(SEED)
    bs = []
    for _ in range(2000):
        pick = rng.integers(0, len(blocks), size=len(blocks))
        sel = [dd for j in pick for dd in blocks[j]]
        sub = pd.concat([b[b.index.date == dd] for dd in sel])
        if len(sub) > 3:
            bs.append(sub.f1.rank().corr(sub.ret.rank()))
    out["T4_burst_veto"] = dict(n_bursts=len(b), rho=rho, ci=[float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))])
    log.info("T4 %s", out["T4_burst_veto"])
    for y in YEARS:
        dy = d[d.t0.dt.year == y]
        yo = {}
        for fk in ("F1", "F2", "F3"):
            v = [g[fk].rank().corr(g.ret.rank()) for _, g in dy.dropna(subset=[fk]).groupby("t0") if len(g) >= MIN_BURST]
            yo[fk] = dict(n=len(v), mean_ic=float(np.mean(v)) if v else None)
        by = dy.dropna(subset=["F1"]).groupby("t0").agg(f1=("F1", "median"), pnl=("pnl", "sum"), mg=("margin", "sum"))
        by["ret"] = by.pnl / by.mg
        yo["T4_rho"] = float(by.f1.rank().corr(by.ret.rank())) if len(by) > 3 else None
        out["year_%d" % y] = yo
        log.info("NAM %d %s", y, yo)
    json.dump(out, open(W + "/r2x_test_%s.json" % TAG, "w"), indent=1)


if __name__ == "__main__":
    {"plan": plan, "fetch": fetch, "feat": feat, "check": check, "test": test}[sys.argv[1]]()
