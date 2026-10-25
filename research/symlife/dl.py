"""SYMLIFE A1b: Vision giu file kline ZOMBIE (nen phang, 0 trade) sau delist => song/chet phai do bang n_trades>0.
(1) tai file 1m ngay 2026-10-21..23 (+10-24 neu co) cho moi USDT perp co file den >=10-21;
(2) binary search ngay giao dich cuoi trong 2026 cho symbol chet (khong trade 10-23) ma raw con trade cuoi 2025;
(3) ngay dau cho symbol niem yet 2026. Moi file: n_bars, n_trade_pos, first/last trade ts. Khong luu zip.
Output symlife_wk/vision_act.parquet (sym, day, n_bars, n_tr, ft, lt, ok)"""
import os, io, json, zipfile, time, datetime as dt, urllib.request, urllib.error, urllib.parse, sys
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
WK = os.path.expanduser("~/claude_master/symlife_wk")
BASE = "https://data.binance.vision/data/futures/um/daily/klines/"
L = json.load(open(WK + "/vision_listing.json"))["daily"]
T = pd.read_parquet(WK + "/lifecycle.parquet"); T = T[T.usdt_perp]
R = pd.read_parquet(WK + "/raw_daycov.parquet")
rlt = R[R.n_trade_pos > 0].groupby("sym").day.max()
CACHE = {}


def act(sym, day):
    k = (sym, day)
    if k in CACHE:
        return CACHE[k]
    u = BASE + urllib.parse.quote(f"{sym}/1m/{sym}-1m-{day}.zip")
    r = None
    for i in range(5):
        try:
            b = urllib.request.urlopen(u, timeout=60).read(); break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                CACHE[k] = dict(sym=sym, day=day, ok=False, n_bars=0, n_tr=0, ft=None, lt=None); return CACHE[k]
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    else:
        raise RuntimeError(u)
    z = zipfile.ZipFile(io.BytesIO(b)); txt = z.read(z.namelist()[0]).decode()
    n = ntr = 0; ft = lt = None
    for line in txt.splitlines():
        p = line.split(",")
        if not p[0].isdigit():
            continue
        n += 1
        if int(p[8]) > 0:
            t = int(p[0]); t = t // 1000 if t > 10**14 else t   # us -> ms neu can
            ntr += 1; ft = t if ft is None else ft; lt = t
    r = dict(sym=sym, day=day, ok=True, n_bars=n, n_tr=ntr, ft=ft, lt=lt)
    CACHE[k] = r
    return r


days_recent = ["2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24"]
jobs = []
for s in T.symbol:
    ds = set(L.get(s, []))
    for d in days_recent:
        if d in ds:
            jobs.append((s, d))
print("recent jobs", len(jobs), flush=True)
with ThreadPoolExecutor(16) as ex:
    list(ex.map(lambda a: act(*a), jobs))
print("recent done", flush=True)


def last_trade_day(s):
    ds = sorted(d for d in L.get(s, []) if d >= "2026-01-01")
    if not ds:
        return s, None
    if act(s, ds[-1])["n_tr"] > 0:
        return s, ds[-1]
    lo, hi = -1, len(ds) - 1          # invariant: ds[hi] khong trade; ds[lo] trade (lo=-1 => truoc 2026)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if act(s, ds[mid])["n_tr"] > 0:
            lo = mid
        else:
            hi = mid
    return s, (ds[lo] if lo >= 0 else None)


cand = []
for s in T.symbol:
    ds = L.get(s, [])
    if not ds or ds[-1] < "2026-01-01":
        continue
    last_raw = rlt.get(s)
    rec = CACHE.get((s, "2026-10-23"))
    alive = rec is not None and rec["n_tr"] > 0
    if alive:
        continue
    cand.append(s)
print("binary-search cand", len(cand), flush=True)
with ThreadPoolExecutor(16) as ex:
    LT = dict(ex.map(last_trade_day, cand))
first_jobs = [(s, L[s][0]) for s in T.symbol if L.get(s) and L[s][0] >= "2025-12-31"]
print("first-day jobs", len(first_jobs), flush=True)
with ThreadPoolExecutor(16) as ex:
    list(ex.map(lambda a: act(*a), first_jobs))
A = pd.DataFrame(list(CACHE.values()))
A["ft"] = A["ft"].astype("Int64"); A["lt"] = A["lt"].astype("Int64")
A.to_parquet(WK + "/vision_act.parquet", index=False)
json.dump({k: v for k, v in LT.items()}, open(WK + "/lt2026.json", "w"))
print("DONE files", len(A), "downloaded ok", int(A.ok.sum()))
