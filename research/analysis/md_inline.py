#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PORT Python cua `MarketBigChangeDetector.calMarketData` + `MarketDataInlineGenerator`
(AUDIT-ONLY) de tinh `MarketDataObject` (rateDownAvg / rateUpAvg / rateDown15MAvg) TRUC TIEP
tu snapshot kline 1 phut — thay cho viec doc set Aerospike `market_data_object` (da chet tu 2026-08-14).

Nguon su that (Java, KHONG sua):
  src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java:48 (calMarketData)
  src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java:149 (calRateChangeAvg)
  src/main/java/com/binance/chuyennd/ai_ml/features/export/MarketDataInlineGenerator.java:50 (update)
  src/main/java/com/binance/chuyennd/tradecore/Configs.java  NUMBER_TICKER_CAL_RATE_CHANGE (WINDOW)

Anh xa feature (ComprehensiveMarketFeatureExtractor.extractMomentumFeatures):
  momentum1M = rateDownAvg ; momentum15M = rateDown15MAvg ; momentumAcceleration = momentum5M - momentum15M
"""
import datetime

# WINDOW = Configs.NUMBER_TICKER_CAL_RATE_CHANGE (=15 trong config shadow/export)
WINDOW = 15
MIN_SYMBOLS = 50
PERIOD = 100


def cal_rate_change_avg(rate2sym, period=PERIOD):
    """Java: TreeMap<Float,String> da sort tang dan; lay `period` phan tu dau / counter.
    period bi kep: neu period > size*4/5 thi period = size*4/5. Rong => 0.0"""
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


def cal_market_data(snapshot, sym2max, sym2min, died):
    """snapshot: dict symbol -> (open, high, low, close). Tra ve (rateDownAvg, rateUpAvg, rateDown15MAvg).

    Giong MarketBigChangeDetector.calMarketData (KHONG gom guard cua InlineGenerator).
    """
    btc = snapshot.get("BTCUSDT")
    rate_btc = ((btc[3] - btc[0]) / btc[0]) if btc is not None else 0.0
    rd, ru, rm = {}, {}, {}
    for sym, (o, h, l, c) in snapshot.items():
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
        mn = sym2min.get(sym)
        # rateMin2Symbols khong dung cho 3 output -> bo qua (giu cho dung cau truc)
    down_avg = cal_rate_change_avg(rd, PERIOD)
    up_avg = -cal_rate_change_avg(ru, PERIOD)
    down15_avg = cal_rate_change_avg(rm, PERIOD)
    return down_avg, up_avg, down15_avg


class InlineMD:
    """Buffer truot per-symbol (high/low,WINDOW nen) — nuoi TUAN TU 1 lan/phut theo thoi gian."""

    def __init__(self, died, window=WINDOW):
        self.died = died
        self.window = window
        self.hist = {}     # sym -> list[[high, low]] (<= window)

    def update(self, snapshot):
        """snapshot: dict sym -> (open, high, low, close). Tra ve md hoac None (guard)."""
        if not snapshot:
            return None
        sym2max, sym2min = {}, {}
        valid = 0
        warm = 0
        for sym, (o, h, l, c) in snapshot.items():
            if sym in self.died:
                continue
            buf = self.hist.setdefault(sym, [])
            buf.append((h, l))
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
        return cal_market_data(snapshot, sym2max, sym2min, self.died)
