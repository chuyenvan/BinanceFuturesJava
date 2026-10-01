"""BD_DEEP raw recompute: tai lap calMarketData tu ticker_*.bin.gz de quet N / cua so / dinh nghia."""
import gzip
import json
import logging
import os
import struct
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jbin  # noqa: E402

log = logging.getLogger("bd_deep_raw")
TICKDIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])


def load_market_day(day):
    """day: 'YYYYMMDD' (UTC). Tra (ts_ms sorted, down, up, down15) cho ngay do (UTC)."""
    lo = int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)
    hi = lo + 86400000
    with open("/home/ubuntu/wfo_ds_x1_2021/market.bin", "rb") as f:
        n = int(np.frombuffer(f.read(4), dtype=">i4")[0])
        a = np.frombuffer(f.read(n * 20), dtype=DT)
    ts = a["ts"].astype(np.int64)
    k = (ts >= lo) & (ts < hi)
    return ts[k], a["down"][k].astype(float), a["up"][k].astype(float), a["down15"][k].astype(float)


def day_minutes(day):
    p = os.path.join(TICKDIR, "ticker_%s.bin.gz" % day)
    with gzip.open(p, "rb") as g:
        b = g.read()
    return list(jbin.iter_minutes(b))


def cal_avg(sorted_keys, period):
    """Tai lap MarketBigChangeDetector.calRateChangeAvg tren list key DA SORT tang dan."""
    n = len(sorted_keys)
    if n == 0:
        return 0.0
    p = int(period)
    if p > n * 4 // 5:
        p = n * 4 // 5
    if p <= 0:
        return 0.0
    return sum(sorted_keys[:p]) / p


def recompute(minutes, N=100, WIN=15, mode="avg"):
    """minutes = list (ms, {sym:(st,maxP,minP,close,open,vol)}).
    mode: 'avg'  = trung binh N am nhat (goc)
          'pct_k' = phan vi: lay key tai vi tri floor(k*n)
    Tra dict ms -> (down, up, down15).
    """
    hist = {}   # sym -> list maxPrice (giu WIN phan tu cuoi)
    hmin = {}
    out = {}
    for ms, m in minutes:
        rateDown, rateUp, rateMax, rateMin = [], [], [], []
        btc = m.get("BTCUSDT")
        rbtc = (btc[3] / btc[4] - 1.0) if btc is not None and btc[4] else 0.0
        for sym, v in m.items():
            st, maxP, minP, close, op, vol = v
            if not op or not close:
                continue
            rc = close / op - 1.0
            if rbtc > -0.004 and rc < -0.15:
                continue
            if rc > 0.3:
                continue
            rateDown.append((rc, sym))
            rateUp.append((-rc, sym))
            h = hist.setdefault(sym, [])
            h.append(maxP)
            if len(h) > WIN:
                del h[0:len(h) - WIN]
            hm = hmin.setdefault(sym, [])
            hm.append(minP)
            if len(hm) > WIN:
                del hm[0:len(hm) - WIN]
            rateMax.append((close / max(h) - 1.0, sym))
            rateMin.append((-(close / min(hm) - 1.0), sym))
        def agg(pairs):
            pairs.sort(key=lambda t: t[0])
            keys = [k for k, _ in pairs]
            if mode == "avg":
                return cal_avg(keys, N)
            k = int(mode.split("_")[1])
            if not keys:
                return 0.0
            return keys[int(np.floor(k * (len(keys) - 1)))]
        dn = agg(rateDown)
        upv = -agg(rateUp)
        d15 = agg(rateMax)
        out[ms] = (dn, upv, d15)
    return out


def parity_check(day):
    minutes = day_minutes(day)
    got = recompute(minutes)
    ts, down, up, d15 = load_market_day(day)
    res = {}
    for name, arr, i in (("down", down, 0), ("up", up, 1), ("down15", d15, 2)):
        d = []
        for t, v in zip(ts, arr):
            if t in got:
                d.append(abs(float(v) - got[t][i]))
        d = np.array(d)
        res[name] = dict(n=len(d), maxabs=float(d.max()) if len(d) else None,
                         mean=float(d.mean()) if len(d) else None,
                         pct_within_1e3=float((d < 1e-3).mean() * 100) if len(d) else None)
    log.info("PARITY %s: %s", day, json.dumps(res))
    return res


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    d = sys.argv[1] if len(sys.argv) > 1 else "20241026"
    parity_check(d)
