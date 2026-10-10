#!/usr/bin/env python3
"""HO3 B2-F: funding — Vision fundingRate (monthly) vs Aerospike local test.funding_data (store DEV/HO26)
vs 242 ticker.funding_data, tren doan chong H1 2026-01-01..06-30 +07. Chi in dem/ty le, KHONG in gia tri.
Usage: ho3_b2_fund.py --out f_h1.json [--months 2026-01,...] [--lo YYYYMMDD --hi YYYYMMDD]
"""
import argparse, datetime, io, json, logging, sys, time, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import devexport_202609 as dx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ho3f")
TZ7 = dx.TZ7
VURL = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip"


def vision(sym, months):
    out = {}
    miss = 0
    for m in months:
        try:
            with urllib.request.urlopen(VURL.format(s=sym, m=m), timeout=30) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
        except Exception:
            miss += 1
            continue
        for ln in z.read(z.namelist()[0]).decode().splitlines():
            p = ln.split(",")
            if not p or not p[0].strip().isdigit():
                continue
            out[int(p[0]) // 60000] = float(p[2])
    return out, miss


def store_map(cli, ns, sym):
    import cramjam
    try:
        r = cli.get((ns, "funding_data", sym))
        d = r[2].get("f_data") if r else None
        if not d:
            return {}
        m = json.loads(bytes(cramjam.snappy.decompress_raw(d)))
        return {int(k) // 60000: float(v) for k, v in m.items()}
    except Exception:
        return {}


def cmp(ref, oth, lo, hi):
    """so moc trong [lo,hi) phut: ref la chuan."""
    a = {k: v for k, v in ref.items() if lo <= k < hi}
    b = {k: v for k, v in oth.items() if lo <= k < hi}
    both = [k for k in a if k in b]
    eq = sum(1 for k in both if np.float32(a[k]) == np.float32(b[k]))
    return dict(ref=len(a), oth=len(b), both=len(both), eq=eq, ref_only=len(a) - len(both), oth_only=len(b) - len(both))


def add(t, r):
    for k, v in r.items():
        t[k] = t.get(k, 0) + v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--months", default="2025-12,2026-01,2026-02,2026-03,2026-04,2026-05,2026-06")
    ap.add_argument("--lo", default="20260101")
    ap.add_argument("--hi", default="20260701")
    a = ap.parse_args()
    months = a.months.split(",")
    lo = int(datetime.datetime.strptime(a.lo, "%Y%m%d").replace(tzinfo=TZ7).timestamp()) // 60
    hi = int(datetime.datetime.strptime(a.hi, "%Y%m%d").replace(tzinfo=TZ7).timestamp()) // 60
    loc = dx.Store("local", pool=4)
    r242 = dx.Store("242", pool=4)
    syms = sorted(loc.get_symbol_mapper().keys())
    syms = [s if s.endswith("USDT") else s + "USDT" for s in syms]
    log.info("symbols=%d months=%s", len(syms), months)
    T = {"vision_vs_local": {}, "s242_vs_local": {}, "vision_vs_242": {}}
    per = {}
    def job(s):
        v, miss = vision(s, months)
        return s, v, miss, store_map(loc.client, "test", s), store_map(r242.client, "ticker", s)
    n_vmiss_all = 0
    with ThreadPoolExecutor(12) as ex:
        for i, (s, v, miss, l, g) in enumerate(ex.map(job, syms)):
            x = dict(v=cmp(l, v, lo, hi), g=cmp(l, g, lo, hi), vg=cmp(g, v, lo, hi), vmiss=miss)
            if not any(x[k]["ref"] or x[k]["oth"] for k in ("v", "g", "vg")):
                continue
            per[s] = x
            add(T["vision_vs_local"], x["v"]); add(T["s242_vs_local"], x["g"]); add(T["vision_vs_242"], x["vg"])
            if i % 100 == 0:
                log.info("%d/%d", i, len(syms))
    for k, t in T.items():
        t["eq_rate_vs_ref"] = t.get("eq", 0) / max(t.get("ref", 0), 1)
    bad = {s: x for s, x in per.items() if x["v"]["eq"] != x["v"]["ref"] or x["v"]["oth_only"]}
    json.dump(dict(window=[a.lo, a.hi], totals=T, n_sym=len(per), n_sym_vision_vs_local_not_100=len(bad),
                   sym_vision_vs_local_not_100=sorted(bad)[:200]), open(a.out, "w"), indent=1)
    log.info("TOTALS %s", json.dumps(T))


if __name__ == "__main__":
    main()
