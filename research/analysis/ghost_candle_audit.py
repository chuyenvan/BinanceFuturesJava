#!/usr/bin/env python3
"""GHOST_CANDLE_AUDIT — đo nến ma vol=0 (ticker bundle) lên rateDownAvg / rateDown15MAvg / BIG_DOWN trigger.

Câu hỏi (AUDIT_CHAIN_AND_N §1 #1): nến ma vol=0 (delist/rename settle) có làm méo
rateDownAvg (BIG_DOWN) và feature gate (momentum1M/15M = rateDownAvg/rateDown15MAvg) không?
Cách đo: tái lập calMarketData (bd_deep_raw, đã parity) 2 lần — CÓ ghost (hiện trạng) vs KHÔNG
ghost (bỏ symbol vol==0 trong phút đó), rồi đếm chênh BIG_DOWN trigger + phân bố delta.
0-sim, đọc ticker_*.bin.gz. DEV <= 2025-12-30.
"""
import gzip
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jbin  # noqa: E402

TICKDIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
MS_DOWN_BIG_AVG = -0.03157


def day_minutes(day):
    p = os.path.join(TICKDIR, "ticker_%s.bin.gz" % day)
    with gzip.open(p, "rb") as g:
        b = g.read()
    return list(jbin.iter_minutes(b))


def cal_avg(sorted_keys, period):
    n = len(sorted_keys)
    if n == 0:
        return 0.0
    p = int(period)
    if p > n * 4 // 5:
        p = n * 4 // 5
    if p <= 0:
        return 0.0
    return sum(sorted_keys[:p]) / p


def recompute(minutes, skip_ghost=False, N=100, WIN=15):
    """Tai lap calMarketData. skip_ghost=True => bo symbol co totalUsdt(vol)==0 trong phut do."""
    hist, hmin, out = {}, {}, {}
    for ms, m in minutes:
        rateDown, rateUp, rateMax = [], [], []
        btc = m.get("BTCUSDT")
        rbtc = (btc[3] / btc[4] - 1.0) if btc is not None and btc[4] else 0.0
        for sym, v in m.items():
            st, maxP, minP, close, op, vol = v
            if not op or not close:
                continue
            if skip_ghost and (vol is None or vol == 0.0):
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
            rateMax.append((close / max(h) - 1.0, sym))
        def agg(pairs):
            pairs.sort(key=lambda t: t[0])
            return cal_avg([k for k, _ in pairs], N)
        out[ms] = (agg(rateDown), -agg(rateUp), agg(rateMax))
    return out


def main():
    days = sys.argv[1:] or ["20250115", "20220115", "20230115", "20240115", "20250115"]
    rows = []
    for day in sorted(set(days)):
        minutes = day_minutes(day)
        base = recompute(minutes, skip_ghost=False)
        filt = recompute(minutes, skip_ghost=True)
        ms = sorted(set(base) & set(filt))
        d_down, d_down15, trig_chg = [], [], 0
        for t in ms:
            b, f = base[t], filt[t]
            d_down.append(f[0] - b[0])
            d_down15.append(f[2] - b[2])
            tb = b[0] < MS_DOWN_BIG_AVG
            tf = f[0] < MS_DOWN_BIG_AVG
            if tb != tf:
                trig_chg += 1
        d_down = np.array(d_down)
        d_down15 = np.array(d_down15)
        rows.append(dict(day=day, n_min=len(ms),
                         ghost_trig_chg=int(trig_chg),
                         d_down_maxabs=float(np.abs(d_down).max()) if len(d_down) else None,
                         d_down_mean=float(d_down.mean()) if len(d_down) else None,
                         d_down_p99=float(np.abs(d_down).max()) if len(d_down) else None,
                         d_down15_maxabs=float(np.abs(d_down15).max()) if len(d_down15) else None,
                         d_down15_mean=float(d_down15.mean()) if len(d_down15) else None))
        print(json.dumps(rows[-1], default=str))
    print("--- TONG ---")
    print(json.dumps(rows, default=str, indent=1))


if __name__ == "__main__":
    main()
