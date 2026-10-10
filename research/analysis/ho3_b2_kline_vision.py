#!/usr/bin/env python3
"""HO3 B2-K2/K3: Binance Vision klines 1m (monthly, futures/um) vs
  --ref ticker : ticker HO26 (Java-serialized) cho thang --month (doan chong H1)
  --ref as242  : Aerospike 242 ticker.kline_1m_opt (CHI DOC) cho cua so --lo..--hi (+07)
Khop = OHLC float32 bang nhau (rel<=1e-8) va volume (quote) bang nhau. Chi in dem/ty le.
"""
import argparse, datetime, gzip, io, json, logging, os, sys, time, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import jbin
import devexport_202609 as dx
import ho3_b2_kline_as as k1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ho3k2")
TZ7 = dx.TZ7
VURL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"


class Acc:
    """Gom theo NGAY -> numpy (tranh 25M tuple Python)."""
    def __init__(self):
        self.d = {}

    def add_day(self, mm, lo, hi):
        tmp = {}
        for ms, m in mm.items():
            mi = ms // 60000
            if not (lo <= mi < hi):
                continue
            for s, v in m.items():
                t = tmp.setdefault(s, ([], []))
                t[0].append(mi); t[1].append(v)
        for s, (a, b) in tmp.items():
            x = self.d.setdefault(s, ([], []))
            x[0].append(np.asarray(a, np.int64)); x[1].append(np.asarray(b, np.float32).reshape(-1, 5))

    def finish(self):
        return {s: (np.concatenate(a), np.concatenate(b)) for s, (a, b) in self.d.items()}


def vision(sym, months, lo, hi):
    parts = []
    for m in months:
        try:
            with urllib.request.urlopen(VURL.format(s=sym, m=m), timeout=60) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            df = pd.read_csv(z.open(z.namelist()[0]), header=None, dtype=str)
        except Exception:
            continue
        df = df[df[0].str.isdigit()]
        parts.append(df)
    if not parts:
        return None
    df = pd.concat(parts)
    mi = df[0].astype(np.int64).to_numpy() // 60000
    k = (mi >= lo) & (mi < hi)
    # open,high,low,close,quote_volume(7),volume(5)
    v = df[[1, 2, 3, 4, 7, 5]].astype(np.float64).to_numpy()[k].astype(np.float32)
    return mi[k], v


def relq(a, b):
    return (a == b) | (np.abs(a.astype(np.float64) - b.astype(np.float64)) <= 1e-8 * np.abs(b.astype(np.float64)))


def compare(ref, sym, vis):
    r = dict(ref=0, vis=0, both=0, eq_ohlc=0, eq5_quote=0, eq5_base=0, ref_only=0, vis_only=0, nosym_vis=0)
    if sym in ref:
        ri, rv = ref[sym]
        r["ref"] = len(ri)
    else:
        ri, rv = np.zeros(0, np.int64), np.zeros((0, 5), np.float32)
    if vis is None:
        r["nosym_vis"] = 1; r["ref_only"] = len(ri); return r
    vi, vv = vis
    r["vis"] = len(vi)
    _, ia, ib = np.intersect1d(ri, vi, assume_unique=False, return_indices=True)
    r["both"] = len(ia)
    r["ref_only"] = len(ri) - len(ia); r["vis_only"] = len(vi) - len(ib)
    a, b = rv[ia], vv[ib]
    ohlc = relq(a[:, 0], b[:, 0]) & relq(a[:, 1], b[:, 1]) & relq(a[:, 2], b[:, 2]) & relq(a[:, 3], b[:, 3])
    r["eq_ohlc"] = int(ohlc.sum())
    r["eq5_quote"] = int((ohlc & relq(a[:, 4], b[:, 4])).sum())
    r["eq5_base"] = int((ohlc & relq(a[:, 4], b[:, 5])).sum())
    day = (ri[ia] + 420) // 1440  # ngay +07
    e5 = ohlc & relq(a[:, 4], b[:, 4])
    r["_byday"] = {int(dd): (int(n), int(k)) for dd, n, k in zip(*np.unique(day, return_counts=True),
                   np.bincount(np.searchsorted(np.unique(day), day), weights=e5).astype(int))} if len(day) else {}
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", choices=["ticker", "as242"], required=True)
    ap.add_argument("--lo", required=True, help="YYYYMMDD +07 (bao gom)")
    ap.add_argument("--hi", required=True, help="YYYYMMDD +07 (khong gom)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo_dt = datetime.datetime.strptime(a.lo, "%Y%m%d").replace(tzinfo=TZ7)
    hi_dt = datetime.datetime.strptime(a.hi, "%Y%m%d").replace(tzinfo=TZ7)
    lo, hi = int(lo_dt.timestamp()) // 60, int(hi_dt.timestamp()) // 60
    acc = Acc()
    st = dx.Store("242", pool=40) if a.ref == "as242" else None
    d = (lo_dt.astimezone(datetime.timezone.utc)).replace(hour=0, minute=0)
    while d < hi_dt:
        if a.ref == "ticker":
            mm = k1.load_ticker(d.strftime("%Y%m%d"))
        else:
            mm = k1.fetch_as(st, int(d.timestamp() * 1000))
        acc.add_day(mm, lo, hi)
        del mm
        log.info("ref day %s", d.strftime("%Y%m%d"))
        d += datetime.timedelta(days=1)
    ref = acc.finish(); del acc
    months = sorted({(lo_dt + datetime.timedelta(minutes=x)).astimezone(datetime.timezone.utc).strftime("%Y-%m")
                     for x in range(0, hi - lo, 1440)} | {(hi_dt - datetime.timedelta(minutes=1)).astimezone(datetime.timezone.utc).strftime("%Y-%m")})
    log.info("ref symbols=%d months=%s", len(ref), months)
    T = {}; nos = []; BYD = {}
    with ThreadPoolExecutor(8) as ex:
        for s, r in ex.map(lambda s: (s, compare(ref, s, vision(s, months, lo, hi))), sorted(ref)):
            for dd, (n, k) in r.pop("_byday", {}).items():
                x = BYD.setdefault(dd, [0, 0]); x[0] += n; x[1] += k
            for k, v in r.items():
                T[k] = T.get(k, 0) + v
            if r["nosym_vis"]:
                nos.append(s)
    for k in ("eq_ohlc", "eq5_quote", "eq5_base"):
        T[k + "_rate_vs_ref"] = T[k] / max(T["ref"], 1)
        T[k + "_rate_vs_both"] = T[k] / max(T["both"], 1)
    json.dump(dict(ref=a.ref, window=[a.lo, a.hi], months=months, totals=T, n_sym=len(ref),
                   sym_no_vision=nos, byday_eq5={(datetime.datetime(1970,1,1)+datetime.timedelta(days=d)).strftime('%Y-%m-%d'): round(v[1]/max(v[0],1), 6) for d, v in sorted(BYD.items())}), open(a.out, "w"), indent=1)
    log.info("TOTALS %s nosym=%d", json.dumps(T), len(nos))


if __name__ == "__main__":
    main()
