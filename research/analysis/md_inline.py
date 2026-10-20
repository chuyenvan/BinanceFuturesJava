#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PORT Python cua `MarketBigChangeDetector.calMarketData` + `MarketDataInlineGenerator`
(AUDIT-ONLY) de tinh `MarketDataObject` (rateDownAvg / rateUpAvg / rateDown15MAvg) TRUC TIEP
tu snapshot kline 1 phut — thay cho viec doc set Aerospike `market_data_object` (da chet tu 2026-08-14).

Nguon su that (Java, KHONG sua):
  src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java (calMarketData, calRateChangeAvg)
  src/main/java/com/binance/chuyennd/ai_ml/features/export/MarketDataInlineGenerator.java (update)
  src/main/java/com/binance/chuyennd/tradecore/Configs.java  NUMBER_TICKER_CAL_RATE_CHANGE (WINDOW)

[V11 2026-10-20] docs/plan/V11_COLLECTOR_SETTLE.md §6 — SUA cho khop Java BIT-EXACT (mac dinh exact=True):
  (1) buffer 15 nen va symbol2MaxPrice CHI nhan nen `isTickerAvailable` (min != max hoac totalUsdt != 0) —
      ban cu nhan moi nen => momentum15M chi khop 6,5-26 %;
  (2) so hoc float32 nhu Java (Float rateOf2Double, TreeMap<Float> gop khoa trung, `Float total += key`);
  (3) guard degenerate (NaN/Inf hoac ca 3 = 0) nhu MarketDataInlineGenerator;
  (4) tap died cua NGUON sim/train = {BTCDOMUSDT, USDCUSDT} (store market_data_object / market.bin sinh voi
      DIED_SYMBOLS=BTCDOM,USDC) — KHONG dung DIED_SYMBOLS dai cua live 242.
  Snapshot phai la sym -> (open, high, low, close, totalUsdt). exact=False giu ban cu (chi de tai lap so cu).

Anh xa feature (ComprehensiveMarketFeatureExtractor.extractMomentumFeatures):
  momentum1M = rateDownAvg ; momentum15M = rateDown15MAvg ; momentumAcceleration = momentum5M - momentum15M
"""
import math

import numpy as np

# WINDOW = Configs.NUMBER_TICKER_CAL_RATE_CHANGE (=15 trong config shadow/export)
WINDOW = 15
MIN_SYMBOLS = 50
PERIOD = 100
SIM_DIED = frozenset({"BTCDOMUSDT", "USDCUSDT"})
F32 = np.float32


def _rate32(start, end):
    """Utils.rateOf2Double(Float start, Float end) = (start - end) / end, float32."""
    s = F32(start)
    e = F32(end)
    with np.errstate(all="ignore"):
        return F32(F32(s - e) / e)


def cal_rate_change_avg32(keys, period=PERIOD):
    """calRateChangeAvg tren TreeMap<Float,String>: keys = tap float32 PHAN BIET (da gop trung)."""
    if not keys:
        return F32(0.0)
    n = len(keys)
    if period > n * 4 // 5:
        period = n * 4 // 5
    total = F32(0.0)
    counter = 0
    for k in sorted(keys):
        counter += 1
        total = F32(total + F32(k))
        if counter >= period:
            break
    return F32(total / F32(counter))


def cal_rate_change_avg(rate2sym, period=PERIOD):
    """Ban CU (float64) — giu de tai lap so cu (exact=False)."""
    if not rate2sym:
        return 0.0
    n = len(rate2sym)
    if period > n * 4 // 5:
        period = n * 4 // 5
    total = 0.0
    counter = 0
    for k in sorted(rate2sym.keys()):
        counter += 1
        total += k
        if period is not None and counter >= period:
            break
    if counter == 0:
        return 0.0
    return total / counter


def cal_market_data32(snapshot, sym2max, died):
    """calMarketData float32. snapshot: sym -> (o,h,l,c,usdt). Tra (down, up, down15) float32."""
    btc = snapshot.get("BTCUSDT")
    rate_btc = _rate32(btc[3], btc[0]) if btc is not None else F32(0.0)
    rd, ru, rm = set(), set(), set()
    for sym, t in snapshot.items():
        if sym in died:
            continue
        o, c = t[0], t[3]
        rc = _rate32(c, o)
        if float(rate_btc) > -0.004 and float(rc) < -0.15:
            continue
        if float(rc) > 0.3:
            continue
        rd.add(rc)
        ru.add(F32(-rc))
        mx = sym2max.get(sym)
        if mx is not None:
            rm.add(_rate32(c, mx))
    down = cal_rate_change_avg32(rd)
    up = F32(-cal_rate_change_avg32(ru))
    down15 = cal_rate_change_avg32(rm)
    return down, up, down15


def cal_market_data(snapshot, sym2max, sym2min, died):
    """Ban CU float64 (exact=False)."""
    btc = snapshot.get("BTCUSDT")
    rate_btc = ((btc[3] - btc[0]) / btc[0]) if btc is not None else 0.0
    rd, ru, rm = {}, {}, {}
    for sym, t in snapshot.items():
        o, c = t[0], t[3]
        if sym in died:
            continue
        rc = (c - o) / o if o else 0.0
        if rate_btc > -0.004 and rc < -0.15:
            continue
        if rc > 0.3:
            continue
        rd[rc] = sym
        ru[-rc] = sym
        mx = sym2max.get(sym)
        if mx is not None and mx:
            rm[(c - mx) / mx] = sym
    return cal_rate_change_avg(rd, PERIOD), -cal_rate_change_avg(ru, PERIOD), cal_rate_change_avg(rm, PERIOD)


def ticker_available(t):
    """Utils.isTickerAvailable: minPrice != maxPrice || totalUsdt != 0 (so float32)."""
    return F32(t[2]) != F32(t[1]) or F32(t[4]) != F32(0.0)


class InlineMD:
    """Buffer truot per-symbol (high/low, WINDOW nen) — nuoi TUAN TU 1 lan/phut theo thoi gian."""

    def __init__(self, died=SIM_DIED, window=WINDOW, exact=True):
        self.died = set(died)
        self.window = window
        self.exact = exact
        self.hist = {}     # sym -> list[[high, low]] (<= window)

    def update(self, snapshot):
        """snapshot: dict sym -> (open, high, low, close, totalUsdt). Tra (down, up, down15) hoac None (guard)."""
        if not snapshot:
            return None
        sym2max, sym2min = {}, {}
        valid = 0
        warm = 0
        for sym, t in snapshot.items():
            if sym in self.died:
                continue
            if self.exact:
                if len(t) < 5:
                    raise ValueError("md_inline exact: snapshot can 5 cot (o,h,l,c,usdt) de loc isTickerAvailable")
                if not ticker_available(t):
                    continue
            buf = self.hist.setdefault(sym, [])
            buf.append((F32(t[1]), F32(t[2])) if self.exact else (t[1], t[2]))
            if len(buf) > self.window:
                del buf[0]
            valid += 1
            if len(buf) >= self.window:
                warm += 1
            sym2max[sym] = max(x[0] for x in buf)
            sym2min[sym] = min(x[1] for x in buf)
        if valid < MIN_SYMBOLS:
            return None
        if "BTCUSDT" not in snapshot:
            return None
        if warm < MIN_SYMBOLS:
            return None
        if not self.exact:
            return cal_market_data(snapshot, sym2max, sym2min, self.died)
        r = cal_market_data32(snapshot, sym2max, self.died)
        if any(math.isnan(float(x)) or math.isinf(float(x)) for x in r) or all(float(x) == 0.0 for x in r):
            return None
        return tuple(float(x) for x in r)
