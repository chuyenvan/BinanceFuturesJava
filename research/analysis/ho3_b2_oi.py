#!/usr/bin/env python3
"""HO3 B2-O: OI per-coin — dung lai tu Vision daily metrics (quy uoc create_time theo tung (symbol,ngay):
file bat dau 00:00 => NEW => ts = create_time + 5m; bat dau 00:05 => OLD => ts = create_time; OI_FIX_LOG §4)
va so voi file ghim oi_percoin_full.bin (e3887f63) tren mau (symbol, ngay) H1 2026.
So 4 cot khong phu thuoc lich su: oi_delta24h, ls_global, ls_toptrader, taker_buy (float32 bang nhau, NaN==NaN).
oi_z (expanding tu 2021) KHONG so duoc bang mau ngay — ghi chu. Chi in dem/ty le.
"""
import datetime, io, json, logging, random, sys, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ho3o")
OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
ODT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
URL = "https://data.binance.vision/data/futures/um/daily/metrics/{s}/{s}-metrics-{d}.zip"
DAYS = ["2026-01-15", "2026-02-15", "2026-03-15", "2026-04-15", "2026-05-15", "2026-06-15"]
STALE = 3600000
DAY = 86400000


def vday(sym, d):
    try:
        with urllib.request.urlopen(URL.format(s=sym, d=d), timeout=30) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        df = pd.read_csv(z.open(z.namelist()[0]))
    except Exception:
        return None
    if df.empty:
        return None
    ct = pd.to_datetime(df["create_time"], utc=True).astype("int64").to_numpy() // 10**6
    return ct, df


def series(sym, d):
    """tra ve dict col -> (ts np, val float32) gop ngay d-1 va d (cho oi_delta24h), da dich theo quy uoc."""
    out = {}
    conv = None
    for dd in [(datetime.date.fromisoformat(d) - datetime.timedelta(days=k)).isoformat() for k in (2, 1)] + [d]:
        x = vday(sym, dd)
        if x is None:
            continue
        ct, df = x
        day0 = int(pd.Timestamp(dd, tz="UTC").value // 10**6)
        new = (ct.min() - day0) == 0
        sh = 300000 if new else 0
        if dd == d:
            conv = "NEW" if new else ("OLD" if (ct.min() - day0) == 300000 else "UNK%d" % ((ct.min() - day0) // 1000))
        for col, nm in (("sum_open_interest_value", "oi"), ("count_long_short_ratio", "lsg"),
                        ("count_toptrader_long_short_ratio", "lst"), ("sum_taker_long_short_vol_ratio", "tk")):
            v = pd.to_numeric(df[col], errors="coerce").to_numpy(np.float64).astype(np.float32)
            t = ct + sh
            k = ~np.isnan(v)
            a = out.setdefault(nm, ([], []))
            a[0].append(t[k]); a[1].append(v[k])
    return {k: (np.concatenate(a), np.concatenate(b)) for k, (a, b) in out.items()}, conv


def floor_stale(ts, vals, t):
    i = np.searchsorted(ts, t, side="right") - 1
    ok = (i >= 0)
    ii = np.where(ok, i, 0)
    ok &= (t - ts[ii]) <= STALE
    return np.where(ok, vals[ii], np.nan).astype(np.float32), ok


def rebuild(V, t):
    """y het writeCoin (tru oi_z) tai cac ts t cua file ghim."""
    res = {}
    oi_ts, oi_v = V["oi"]
    o = np.argsort(oi_ts, kind="stable"); oi_ts, oi_v = oi_ts[o], oi_v[o]
    i = np.searchsorted(oi_ts, t); i = np.clip(i, 0, len(oi_ts) - 1)
    cur = np.where(oi_ts[i] == t, oi_v[i], np.nan).astype(np.float32)
    past, ok = floor_stale(oi_ts, oi_v, t - DAY)
    ok &= past != 0
    with np.errstate(all="ignore"):
        res["oi_delta24h"] = np.where(ok, cur / np.where(ok, past, np.float32(1)) - np.float32(1), np.nan).astype(np.float32)
    for nm, key in (("ls_global", "lsg"), ("ls_toptrader", "lst")):
        ts, v = V[key]; o = np.argsort(ts, kind="stable")
        res[nm], _ = floor_stale(ts[o], v[o], t)
    ts, v = V["tk"]; o = np.argsort(ts, kind="stable")
    r, okr = floor_stale(ts[o], v[o], t)
    with np.errstate(all="ignore"):
        res["taker_buy"] = np.where(okr & (r >= 0), r / (np.float32(1) + r), np.nan).astype(np.float32)
    return res


def eq(a, b):
    return (a == b) | (np.isnan(a) & np.isnan(b))


def main():
    out = sys.argv[1]
    nsym = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    smap = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
    id2s = dict(zip(smap.symId, smap.symbol))
    mm = np.memmap(OI, dtype=ODT, mode="r")
    los = {d: int(pd.Timestamp(d, tz="UTC").value // 10**6) for d in DAYS}
    parts = {d: [] for d in DAYS}
    for k0 in range(0, len(mm), 5_000_000):
        c = np.asarray(mm[k0:k0 + 5_000_000])
        t = c["ts"].astype(np.int64)
        for d, lo in los.items():
            m = (t >= lo) & (t < lo + DAY)
            if m.any():
                parts[d].append(c[m].copy())
    rows = {}
    for d in DAYS:
        rows[d] = np.concatenate(parts[d]) if parts[d] else np.zeros(0, ODT)
        log.info("pinned %s rows=%d syms=%d", d, len(rows[d]), len(np.unique(rows[d]["sym"])))
    common = set(np.unique(rows[DAYS[0]]["sym"]).tolist())
    for d in DAYS[1:]:
        common &= set(np.unique(rows[d]["sym"]).tolist())
    rnd = random.Random(20261010)
    pick = sorted(rnd.sample(sorted(common), min(nsym, len(common))))
    NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
    T = {n: [0, 0] for n in NAMES if n != "oi_z"}
    T["rows"] = 0; conv = {}; nov = 0; badsd = []
    def job(args):
        sid, d = args
        return sid, d, series(id2s[sid], d)
    jobs = [(sid, d) for sid in pick for d in DAYS]
    with ThreadPoolExecutor(12) as ex:
        for sid, d, (V, cv) in ex.map(job, jobs):
            conv[cv] = conv.get(cv, 0) + 1
            P = rows[d][rows[d]["sym"] == sid]
            if not V or "oi" not in V:
                nov += 1; continue
            t = P["ts"].astype(np.int64)
            R = rebuild(V, t)
            T["rows"] += len(t)
            rl = float(eq(R["ls_global"], P["oi"][:, 2].astype(np.float32)).mean()) if len(t) else 1.0
            ro = float(eq(R["oi_delta24h"], P["oi"][:, 0].astype(np.float32)).mean()) if len(t) else 1.0
            if rl < 1 or ro < 0.999:
                badsd.append([id2s[sid], d, cv, len(t), round(rl, 4), round(ro, 4)])
            for j, n in enumerate(NAMES):
                if n == "oi_z":
                    continue
                T[n][0] += int(eq(R[n], P["oi"][:, j].astype(np.float32)).sum()); T[n][1] += len(t)
    res = dict(days=DAYS, n_sym=len(pick), conv=conv, no_vision=nov,
               match={n: dict(eq=v[0], n=v[1], rate=v[0] / max(v[1], 1)) for n, v in T.items() if n != "rows"},
               rows=T["rows"], bad_symday=badsd, note="oi_z expanding tu dau lich su coin: khong so bang mau ngay")
    json.dump(res, open(out, "w"), indent=1)
    log.info("RESULT %s", json.dumps(res))


if __name__ == "__main__":
    main()
