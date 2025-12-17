package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class DcaFeatureExtractor {

    private final Map<String, Deque<KlineObjectSimple>> symbolHistoryMap = new ConcurrentHashMap<>();
    private final int maxHistorySize = 1500;

    public void updateMarketHistory(Map<String, KlineObjectSimple> currentMarketData) {
        for (Map.Entry<String, KlineObjectSimple> entry : currentMarketData.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();
            Deque<KlineObjectSimple> history = symbolHistoryMap.computeIfAbsent(symbol, k -> new ArrayDeque<>());

            if (!history.isEmpty() && (long)history.getLast().startTime.doubleValue() == (long)kline.startTime.doubleValue()) {
                history.removeLast();
            }
            history.addLast(kline);
            if (history.size() > maxHistorySize) history.removeFirst();
        }
    }

    // [UPDATE] Thêm tham số dcaImpactRatio
    public DcaMarketFeatures extractFeatures(long timestamp,
                                             OrderTargetInfoTest order,
                                             MarketRateChange marketRate,
                                             Map<String, KlineObjectSimple> currentSnapshots,
                                             double dcaImpactRatio) {

        DcaMarketFeatures f = new DcaMarketFeatures();
        f.timestamp = timestamp;
        f.dateKey = Utils.normalizeDateYYYYMMDD(timestamp);

        KlineObjectSimple coinKline = currentSnapshots.get(order.symbol);
        KlineObjectSimple btcKline = currentSnapshots.get("BTCUSDT");

        if (coinKline == null || btcKline == null) return null;

        // --- GROUP 1: POSITION HEALTH ---
        f.currentDrawdown = (coinKline.priceClose - order.priceEntry) / order.priceEntry;

        double price1HAgo = getPriceAgo(order.symbol, 60);
        double pnlNow = f.currentDrawdown;
        double pnl1HAgo = (price1HAgo > 0) ? (price1HAgo - order.priceEntry) / order.priceEntry : pnlNow;
        f.lossVelocity1H = pnlNow - pnl1HAgo;

        // --- GROUP 2: FEASIBILITY ---
        f.dcaImpactRatio = dcaImpactRatio; // [UPDATE] Sử dụng giá trị random từ bên ngoài

        // --- GROUP 3: RELATIVE STRENGTH ---
        double coinRet15 = getReturn(order.symbol, 15);
        double btcRet15 = getReturn("BTCUSDT", 15);

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
            f.crashVelocity = marketRate.rateDownAvg - marketRate.rateDown15MAvg;
        }

        Double funding = FundingFeeManager.getInstance().getNearestFundingFee(order.symbol, timestamp);
        f.fundingRate = (funding != null) ? funding : 0.0;

        // BTC Indicators
        f.btcMomentum15M = btcRet15;
        f.btcMomentum1H = getReturn("BTCUSDT", 60);
        f.btcMomentum4H = getReturn("BTCUSDT", 240);
        f.btcMomentum24H = getReturn("BTCUSDT", 1440);

        double btcRet5 = getReturn("BTCUSDT", 5);
        f.btcMomentumAcceleration = btcRet5 - f.btcMomentum15M;
        f.ethTrendStrength = getReturn("ETHUSDT", 60);

        // --- GROUP 5: TECHNICAL ---
        f.rsi1H = calculateRSIHighTimeframe(order.symbol, 14, 60);
        double avgVol4H = getAvgVolume(order.symbol, 240);
        f.volumeAnomaly = (avgVol4H > 0) ? coinKline.totalUsdt / avgVol4H : 1.0;

        double low24H = getLowInPeriod(order.symbol, 1440);
        f.distFromLow24H = (low24H > 0) ? (coinKline.priceClose - low24H) / low24H : 0;

        f.maxRateChange60M = calculateMaxRateChange(order.symbol, 60);

        return f;
    }

    // --- Helpers (Giữ nguyên) ---
    private double calculateMaxRateChange(String symbol, int minutes) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.isEmpty()) return 0.0;
        long lastTime = (long) h.getLast().startTime.doubleValue();
        long cutoff = lastTime - (minutes * 60000L);
        double maxPrice = -Double.MAX_VALUE;
        double minPrice = Double.MAX_VALUE;
        Iterator<KlineObjectSimple> it = h.descendingIterator();
        while (it.hasNext()) {
            KlineObjectSimple k = it.next();
            if ((long)k.startTime.doubleValue() < cutoff) break;
            if (k.maxPrice > maxPrice) maxPrice = k.maxPrice;
            if (k.minPrice < minPrice) minPrice = k.minPrice;
        }
        if (maxPrice == -Double.MAX_VALUE || minPrice == Double.MAX_VALUE || minPrice == 0) return 0.0;
        return (maxPrice - minPrice) / minPrice;
    }

    private double getPriceAgo(String symbol, int minutes) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.isEmpty()) return -1;
        long lastTime = (long) h.getLast().startTime.doubleValue();
        long targetTime = lastTime - (minutes * 60000L);
        for (KlineObjectSimple k : h) {
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
        long lastTime = (long) h.getLast().startTime.doubleValue();
        long cutoff = lastTime - (minutes * 60000L);
        double min = Double.MAX_VALUE;
        Iterator<KlineObjectSimple> it = h.descendingIterator();
        while (it.hasNext()) {
            KlineObjectSimple k = it.next();
            if ((long)k.startTime.doubleValue() < cutoff) break;
            if (k.minPrice < min) min = k.minPrice;
        }
        return (min == Double.MAX_VALUE) ? -1 : min;
    }

    private double getAvgVolume(String symbol, int minutes) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.isEmpty()) return 0;
        long lastTime = (long) h.getLast().startTime.doubleValue();
        long cutoff = lastTime - (minutes * 60000L);
        double sum = 0;
        int count = 0;
        Iterator<KlineObjectSimple> it = h.descendingIterator();
        while (it.hasNext()) {
            KlineObjectSimple k = it.next();
            if ((long)k.startTime.doubleValue() < cutoff) break;
            sum += k.totalUsdt;
            count++;
        }
        return (count == 0) ? 0 : sum / count;
    }

    private double calculateRSIHighTimeframe(String symbol, int period, int intervalMinutes) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.size() < period * intervalMinutes) return 50.0;
        List<KlineObjectSimple> data = new ArrayList<>(h);
        int size = data.size();
        double sumGain = 0, sumLoss = 0;
        List<Double> closes = new ArrayList<>();
        for (int i = size - 1; i >= 0; i -= intervalMinutes) {
            closes.add(data.get(i).priceClose);
            if (closes.size() > period + 1) break;
        }
        Collections.reverse(closes);
        if (closes.size() < period + 1) return 50.0;
        for (int i = 1; i < closes.size(); i++) {
            double change = closes.get(i) - closes.get(i - 1);
            if (change > 0) sumGain += change; else sumLoss -= change;
        }
        if (sumLoss == 0) return 100.0;
        return 100.0 - (100.0 / (1.0 + (sumGain / sumLoss)));
    }
}