#!/usr/bin/env python3
"""OB_SR 03: fetch/compact Vision bookDepth for all needed symbol-days.

Needed days = for each decision point t (entry, arm, 168h) the UTC days of
[t-24h, t]. Stores per-symbol compact parquet in ~/vz_bd/ob_sr/{SYM}.parquet
(ts + notional for +-1,2,3,5% + implied mid). Static Vision files only.
"""
import concurrent.futures as cf
import io
import json
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
RAW = "/home/ubuntu/vz_bd/raw"
DST = "/home/ubuntu/vz_bd/ob_sr"
URL = "https://data.binance.vision/data/futures/um/daily/bookDepth/{s}/{s}-bookDepth-{d}.zip"
BANDS = [-5, -3, -2, -1, 1, 2, 3, 5]


def needed_days():
    G = pd.read_parquet(OUT + "/anchor.parquet")
    R = pd.read_parquet(OUT + "/price_out.parquet")
    G["t0"] = pd.to_datetime(G["t0"])
    R["t0"] = pd.to_datetime(R["t0"])
    M = G.merge(R[["sym", "t0", "arm_j"]], on=["sym", "t0"], how="left")
    pts = []
    for r in M.itertuples():
        ts = [r.t0]
        if pd.notna(r.arm_j) and r.arm_j > 0:
            ts.append(r.t0 + pd.Timedelta(minutes=int(r.arm_j)))
        if r.age_max is not None and r.age_max >= 10081:
            ts.append(r.t0 + pd.Timedelta(minutes=10081))
        for t in ts:
            pts.append((r.sym, t))
    need = set()
    for s, t in pts:
        for k in range(2):
            need.add((s + "USDT", (t - pd.Timedelta(days=k)).strftime("%Y-%m-%d")))
    return need, len(pts)


def parse(b):
    x = pd.read_csv(io.BytesIO(b))
    p = x.pivot(index="timestamp", columns="percentage", values="notional")
    d = x.pivot(index="timestamp", columns="percentage", values="depth")
    if not all(c in p.columns for c in BANDS):
        return None
    ts = pd.to_datetime(p.index).astype("int64").to_numpy() // 10 ** 6
    noti = {c: p[c].to_numpy(np.float32) for c in BANDS}
    with np.errstate(divide="ignore", invalid="ignore"):
        mid = 0.5 * (noti[-1] / d[-1].to_numpy(np.float64) + noti[1] / d[1].to_numpy(np.float64))
    return ts, noti, mid.astype(np.float32)


def get(sd):
    s, day = sd
    p = "%s/%s/%s.zip" % (RAW, s, day)
    if os.path.exists(p):
        try:
            with zipfile.ZipFile(p) as z:
                return s, day, parse(z.read(z.namelist()[0])), "raw"
        except Exception:
            return s, day, None, "badraw"
    for i in range(3):
        try:
            with urllib.request.urlopen(URL.format(s=s, d=day), timeout=60) as r:
                b = r.read()
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                return s, day, parse(z.read(z.namelist()[0])), "dl"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return s, day, None, "404"
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return s, day, None, "fail"


def main():
    need, npts = needed_days()
    print("decision points", npts, "symbol-days", len(need), flush=True)
    os.makedirs(DST, exist_ok=True)
    by = {}
    stat = {}
    t0 = time.time()
    with cf.ThreadPoolExecutor(8) as ex:
        for i, (s, day, res, how) in enumerate(ex.map(get, sorted(need))):
            stat[how] = stat.get(how, 0) + 1
            if res is not None:
                by.setdefault(s, []).append((day, res))
            if i % 1000 == 0:
                print("fetch %d/%d %s %.0fs" % (i, len(need), stat, time.time() - t0), flush=True)
    print("fetch done", stat, "%.0fs" % (time.time() - t0), flush=True)
    nrow = {}
    for s, parts in by.items():
        ts, noti, mid = [], [], []
        for day, (t, nt, m) in sorted(parts):
            ts.append(t); mid.append(m)
            noti.append(np.stack([nt[c] for c in BANDS], axis=1))
        T = np.concatenate(ts); Mi = np.concatenate(mid); N = np.concatenate(noti)
        o = np.argsort(T, kind="stable")
        T, Mi, N = T[o], Mi[o], N[o]
        keep = np.concatenate([[True], np.diff(T) > 0])
        T, Mi, N = T[keep], Mi[keep], N[keep]
        df = pd.DataFrame(N, columns=["n%d" % c for c in BANDS])
        df.insert(0, "ts", T)
        df["mid"] = Mi
        df.to_parquet("%s/%s.parquet" % (DST, s), index=False)
        nrow[s] = len(df)
    json.dump(dict(need=len(need), status=stat, symbols=len(by),
                   rows={k: int(v) for k, v in nrow.items()}), open(OUT + "/book_fetch.json", "w"), indent=1)
    print("symbols", len(by), "rows median", int(np.median(list(nrow.values()))) if nrow else 0, flush=True)


if __name__ == "__main__":
    main()
