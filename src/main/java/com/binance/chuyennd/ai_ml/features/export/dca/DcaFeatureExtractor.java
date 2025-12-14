package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class DcaFeatureExtractor {

    private final Map<String, Deque<KlineObjectSimple>> symbolHistoryMap = new ConcurrentHashMap<>();
    private final int maxHistorySize = 1000;

    public void updateMarketHistory(Map<String, KlineObjectSimple> currentMarketData) {
        for (Map.Entry<String, KlineObjectSimple> entry : currentMarketData.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();
            Deque<KlineObjectSimple> history = symbolHistoryMap.computeIfAbsent(symbol, k -> new ArrayDeque<>());

            // Fix: Ép kiểu startTime từ Double sang long để so sánh
            if (!history.isEmpty() && (long)history.getLast().startTime.doubleValue() == (long)kline.startTime.doubleValue()) {
                history.removeLast();
            }
            history.addLast(kline);
            if (history.size() > maxHistorySize) history.removeFirst();
        }
    }

    public DcaMarketFeatures extractFeatures(long timestamp,
                                             OrderTargetInfoTest order,
                                             MarketRateChange marketRate,
                                             Map<String, KlineObjectSimple> currentSnapshots) {

        DcaMarketFeatures f = new DcaMarketFeatures();
        f.timestamp = timestamp;
        f.symbol = order.symbol;
        f.dateKey = Utils.normalizeDateYYYYMMDD(timestamp);

        KlineObjectSimple coinKline = currentSnapshots.get(order.symbol);
        KlineObjectSimple btcKline = currentSnapshots.get("BTCUSDT");

        if (coinKline == null || btcKline == null) return null;

        // --- GROUP 1: POSITION HEALTH ---
        f.currentDrawdown = (coinKline.priceClose - order.priceEntry) / order.priceEntry;

        double price15mAgo = getPriceAgo(order.symbol, 15);
        double pnlNow = f.currentDrawdown;
        double pnl15mAgo = (price15mAgo > 0) ? (price15mAgo - order.priceEntry) / order.priceEntry : pnlNow;
        f.lossVelocity = pnlNow - pnl15mAgo;

        f.orderAgeHours = (double) (timestamp - order.timeStart) / (3600 * 1000);

        // --- GROUP 2: FEASIBILITY ---
        double volOld = order.quantity;
        double volNew = order.quantity;
        f.dcaImpactRatio = volNew / volOld;

        double avgPriceNew = (order.priceEntry * volOld + coinKline.priceClose * volNew) / (volOld + volNew);
        f.simulatedRecoveryDiff = (avgPriceNew - coinKline.priceClose) / coinKline.priceClose;

        // --- GROUP 3: RELATIVE STRENGTH ---
        double coinRet15 = getReturn(order.symbol, 15);
        double btcRet15 = getReturn("BTCUSDT", 15); // Tự tính BTC return 15m từ lịch sử

        f.instantAlpha = coinRet15 - btcRet15;

        double coinLow1H = getLowInPeriod(order.symbol, 60);
        double btcLow1H = getLowInPeriod("BTCUSDT", 60);

        double coinBounce = (coinLow1H > 0) ? (coinKline.priceClose - coinLow1H) / coinLow1H : 0;
        double btcBounce = (btcLow1H > 0) ? (btcKline.priceClose - btcLow1H) / btcLow1H : 0;

        f.recoveryElasticity = (btcBounce > 0.0001) ? coinBounce / btcBounce : 0;

        f.dangerIndex = f.currentDrawdown * (btcRet15 - coinRet15);

        // --- GROUP 4: MARKET CONTEXT ---
        if (marketRate != null) {
            f.globalRateDownAvg = marketRate.rateDownAvg;
            // Fix: Sử dụng btcRet15 vừa tính thay vì marketRate.rateBtcDown15M (không tồn tại)
            f.isPanicMode = (marketRate.rateDownAvg < -0.04 || btcRet15 < -0.02) ? 1 : 0;
            f.crashVelocity = marketRate.rateDownAvg - marketRate.rateDown15MAvg;
        }

        // --- GROUP 5: TECHNICAL ---
        f.rsi14 = calculateRSI(order.symbol, 14);
        double avgVol4H = getAvgVolume(order.symbol, 240);
        f.volumeAnomaly = (avgVol4H > 0) ? coinKline.totalUsdt / avgVol4H : 1.0;

        double low24H = getLowInPeriod(order.symbol, 1440);
        f.distFromLow24H = (low24H > 0) ? (coinKline.priceClose - low24H) / low24H : 0;

        return f;
    }

    // --- Helpers (Fix kiểu Double -> Long) ---
    private double getPriceAgo(String symbol, int minutes) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.isEmpty()) return -1;

        // Fix: Ép kiểu Double -> Long
        long lastTime = (long) h.getLast().startTime.doubleValue();
        long targetTime = lastTime - (minutes * 60000L);

        for (KlineObjectSimple k : h) {
            // Fix: Ép kiểu khi so sánh
            if ((long)k.startTime.doubleValue() >= targetTime) return k.priceClose;
        }
        return h.getFirst().priceClose;
    }

    private double getReturn(String symbol, int minutes) {
        double pAgo = getPriceAgo(symbol, minutes);
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.isEmpty() || pAgo <= 0) return 0;
        return (h.getLast().priceClose - pAgo) / pAgo;
    }

    private double getLowInPeriod(String symbol, int minutes) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.isEmpty()) return -1;

        // Fix: Ép kiểu Double -> Long
        long lastTime = (long) h.getLast().startTime.doubleValue();
        long cutoff = lastTime - (minutes * 60000L);

        double min = Double.MAX_VALUE;
        Iterator<KlineObjectSimple> it = h.descendingIterator();
        while (it.hasNext()) {
            KlineObjectSimple k = it.next();
            // Fix: Ép kiểu khi so sánh
            if ((long)k.startTime.doubleValue() < cutoff) break;
            if (k.minPrice < min) min = k.minPrice;
        }
        return (min == Double.MAX_VALUE) ? -1 : min;
    }

    private double getAvgVolume(String symbol, int minutes) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.isEmpty()) return 0;

        // Fix: Ép kiểu Double -> Long
        long lastTime = (long) h.getLast().startTime.doubleValue();
        long cutoff = lastTime - (minutes * 60000L);

        double sum = 0;
        int count = 0;
        Iterator<KlineObjectSimple> it = h.descendingIterator();
        while (it.hasNext()) {
            KlineObjectSimple k = it.next();
            // Fix: Ép kiểu khi so sánh
            if ((long)k.startTime.doubleValue() < cutoff) break;
            sum += k.totalUsdt;
            count++;
        }
        return (count == 0) ? 0 : sum / count;
    }

    private double calculateRSI(String symbol, int period) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.size() <= period) return 50.0;
        List<KlineObjectSimple> data = new ArrayList<>(h);
        double sumGain = 0, sumLoss = 0;
        for (int i = data.size() - period; i < data.size(); i++) {
            double change = data.get(i).priceClose - data.get(i - 1).priceClose;
            if (change > 0) sumGain += change; else sumLoss -= change;
        }
        if (sumLoss == 0) return 100.0;
        return 100.0 - (100.0 / (1.0 + (sumGain / sumLoss)));
    }
}