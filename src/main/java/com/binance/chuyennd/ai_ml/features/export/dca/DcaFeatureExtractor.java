package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class DcaFeatureExtractor {
    private static final Logger LOG = LoggerFactory.getLogger(DcaFeatureExtractor.class);
    private final HistoryManager historyManager = new HistoryManager();

    public void updateMarketHistory(Map<String, KlineObjectSimple> snapshot) {
        historyManager.updateHistory(snapshot);
    }

    public List<String> identifyTargetBasket(long currentTimestamp) {
        return historyManager.findPotentialLosers(currentTimestamp);
    }

    public DcaMarketFeatures extractFeatures(long currentTimestamp, OrderTargetInfoTest order,
                                             MarketRateChange marketRate,
                                             Map<String, KlineObjectSimple> currentSnapshot,
                                             List<String> targetBasket) {

        KlineObjectSimple kline = currentSnapshot.get(order.symbol);
        KlineObjectSimple btcKline = currentSnapshot.get("BTCUSDT");

        if (kline == null) return null;

        DcaMarketFeatures f = new DcaMarketFeatures();

        // --- 1. MARKET POSITION ---
        Double high24h = historyManager.getHighInPeriod(order.symbol, 1440);
        f.distFromHigh24H = (high24h != null && high24h > 0) ? (kline.priceClose - high24h) / high24h : 0.0;

        Double ma20 = historyManager.getMa(order.symbol, 20);
        f.distMA20 = (ma20 != null && ma20 > 0) ? (kline.priceClose - ma20) / ma20 : 0.0;

        // --- 2. MACRO (BTC & ETH) ---
        // BTC
        f.btcMomentum15M = calculateReturn("BTCUSDT", 15);
        f.btcMomentum1H = calculateReturn("BTCUSDT", 60);
        f.btcMomentum4H = calculateReturn("BTCUSDT", 240);
        f.btcMomentum24H = calculateReturn("BTCUSDT", 1440);

        double btc5m = calculateReturn("BTCUSDT", 5);
        f.btcMomentumAcceleration = btc5m - f.btcMomentum15M;

        // ETH
        f.ethMomentum15M = calculateReturn("ETHUSDT", 15);
        f.ethMomentum4H = calculateReturn("ETHUSDT", 240);


        // --- 3. RELATIVE STRENGTH & CONTEXT ---
        Double coinPrice24h = historyManager.getPriceAt(order.symbol, currentTimestamp - 24 * 3600000);
        double coinRate24H = (coinPrice24h != null && coinPrice24h > 0) ? (kline.priceClose - coinPrice24h) / coinPrice24h : 0.0;

        f.instantAlpha = coinRate24H - f.btcMomentum24H;
        f.recoveryElasticity = calculateElasticity(order.symbol, kline);
        f.crashVelocity = marketRate != null ? marketRate.rateDown15MAvg : 0.0;
        f.globalRateDownAvg = marketRate != null ? marketRate.rateDownAvg : 0.0;

        extractBreadthFeatures(f, currentSnapshot);

        // --- 4. TECHNICALS (COIN SPECIFIC) ---
        // Momentum riêng
        f.momentum15M = calculateReturn(order.symbol, 15);
        f.momentum1H = calculateReturn(order.symbol, 60);
        f.momentum4H = calculateReturn(order.symbol, 240);
        f.momentum24H = calculateReturn(order.symbol, 1440);

        // RSI & RSI Change
        f.rsi1H = historyManager.getRsi14(order.symbol);
        double rsiPast = calculatePastRsi(order.symbol, currentTimestamp - 3600000);
        f.rsiChange = f.rsi1H - rsiPast;

        f.distFromLow24H = calculateDistFromLow24H(order.symbol, kline);
        f.maxRateChange60M = historyManager.getMaxRateChange(order.symbol, 60);
        f.volatilityShock = calculateVolatilityShock(order.symbol, kline);

        // Volatility Structure
        double vol1H_calc = calculateVolatility(order.symbol, 60);
        double vol24H_calc = calculateVolatility(order.symbol, 1440);
        f.volatilityTermStructure = (vol24H_calc > 0) ? vol1H_calc / vol24H_calc : 0.0;

        // Volume Features
        double vol1H = historyManager.getSumVolume(order.symbol, 60);
        double vol24H = historyManager.getSumVolume(order.symbol, 1440);
        double avgVol1H_24H = vol24H / 24.0;

        f.volumeAnomaly = (avgVol1H_24H > 0) ? vol1H / avgVol1H_24H : 1.0;

        double vol15M = historyManager.getSumVolume(order.symbol, 15);
        f.volumeRatio15M_24H = (vol24H > 0) ? vol15M / vol24H : 0.0;


        // --- 5. BASKET SPECIFIC ---
        if (targetBasket == null || targetBasket.isEmpty()) targetBasket = Collections.singletonList(order.symbol);
        extractBasketTechnicalFeatures(f, targetBasket);

        // --- 6. FUNDING ---
        extractBasketFundingFeatures(f, targetBasket, currentTimestamp);

        // Funding riêng của coin
        try {
            Double cf = FundingFeeManager.getInstance().getNearestFundingFee(order.symbol, currentTimestamp);
            f.coinFundingRate = (cf != null) ? cf : 0.0;
        } catch (Exception e) {
            f.coinFundingRate = 0.0;
        }

        // --- 7. TIME ---
        extractTimeFeatures(f, currentTimestamp);

        return f;
    }

    // ================= HELPER METHODS =================

    private double calculatePastRsi(String symbol, long pastTimestamp) {
        List<KlineObjectSimple> history = historyManager.getHistory(symbol);
        if (history == null || history.size() < 15) return 50.0;

        // Lấy sublist cho quá khứ
        List<KlineObjectSimple> pastHistory = new ArrayList<>();
        // Giả sử history đã sort theo time tăng dần
        for (KlineObjectSimple k : history) {
            if (k.startTime <= pastTimestamp) pastHistory.add(k);
            else break; // Dừng khi vượt quá thời gian quá khứ
        }

        if (pastHistory.size() < 15) return 50.0;
        return calculateRSI(pastHistory, 14);
    }

    private double calculateRSI(List<KlineObjectSimple> data, int period) {
        if (data.size() <= period) return 50.0;
        double gain = 0.0, loss = 0.0;
        for (int i = data.size() - period - 1; i < data.size() - 1; i++) {
            double change = data.get(i + 1).priceClose - data.get(i).priceClose;
            if (change > 0) gain += change;
            else loss -= change;
        }
        double avgGain = gain / period;
        double avgLoss = loss / period;
        if (avgLoss == 0) return 100.0;
        double rs = avgGain / avgLoss;
        return 100.0 - (100.0 / (1.0 + rs));
    }

    private double calculateReturn(String symbol, int minutes) {
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h == null || h.isEmpty()) return 0.0;
        KlineObjectSimple current = h.get(h.size() - 1);
        long pastTime = current.startTime.longValue() - (minutes * 60000L);
        Double pastPrice = historyManager.getPriceAt(symbol, pastTime);
        if (pastPrice != null && pastPrice > 0) {
            return (current.priceClose - pastPrice) / pastPrice;
        }
        return 0.0;
    }

    private void extractBreadthFeatures(DcaMarketFeatures features, Map<String, KlineObjectSimple> marketData) {
        int upCount = 0, downCount = 0;
        double upVol = 0, downVol = 0;
        int totalValid = 0;

        for (Map.Entry<String, KlineObjectSimple> entry : marketData.entrySet()) {
            KlineObjectSimple k = entry.getValue();
            if (k.totalUsdt < 5000) continue;
            totalValid++;
            if (k.priceClose > k.priceOpen) { upCount++; upVol += k.totalUsdt; }
            else if (k.priceClose < k.priceOpen) { downCount++; downVol += k.totalUsdt; }
        }

        features.advanceDeclineRatio = (downCount > 0) ? (double) upCount / downCount : 10.0;
        features.marketBreadthStrength = (totalValid > 0) ? (double) upCount / totalValid : 0.5;
        double btcVol = marketData.containsKey("BTCUSDT") ? marketData.get("BTCUSDT").totalUsdt : 0;
        features.btcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0;
    }

    private double calculateVolatility(String symbol, int periods) {
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h == null || h.size() < 5) return 0.0;
        int start = Math.max(0, h.size() - periods);
        double sum = 0, sumSq = 0; int count = 0;
        for (int i = start; i < h.size() - 1; i++) {
            double r = (h.get(i + 1).priceClose - h.get(i).priceClose) / h.get(i).priceClose;
            sum += r; sumSq += r * r; count++;
        }
        return (count < 2) ? 0.0 : Math.sqrt(Math.max(0, (sumSq - (sum * sum) / count) / (count - 1)));
    }

    // Các hàm helper cũ giữ nguyên
    private void extractBasketTechnicalFeatures(DcaMarketFeatures features, List<String> basket) {
        double sumRsi = 0, sumMom15m = 0, sumMom1h = 0, sumMom24h = 0, sumVolSpike = 0;
        int count = 0;
        for (String symbol : basket) {
            Double rsi = historyManager.getRsi14(symbol);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);
                sumMom24h += calculateReturn(symbol, 1440);
                double currentVol = historyManager.getSumVolume(symbol, 1);
                double avgVol = historyManager.getAverageVolume(symbol, 20);
                if (avgVol > 0) sumVolSpike += currentVol / avgVol; else sumVolSpike += 1.0;
                count++;
            }
        }
        if (count > 0) {
            features.basketRsi14 = sumRsi / count;
            features.basketMomentum15M = sumMom15m / count;
            features.basketMomentum1H = sumMom1h / count;
            features.basketMomentum24H = sumMom24h / count;
            features.basketVolSpike = sumVolSpike / count;
        } else {
            features.basketRsi14 = features.rsi1H;
            features.basketMomentum15M = 0.0;
            features.basketMomentum1H = calculateReturn(features.instantAlpha > 0 ? "ETHUSDT" : "BTCUSDT", 60);
            features.basketMomentum24H = 0.0;
            features.basketVolSpike = 1.0;
        }
    }

    private void extractBasketFundingFeatures(DcaMarketFeatures features, List<String> basket, long currentTime) {
        try {
            if (basket == null || basket.isEmpty()) basket = Collections.singletonList("BTCUSDT");
            double totalCurrentFunding = 0; double totalAvg24H = 0; int validCount = 0;
            for (String symbol : basket) {
                Double currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, currentTime);
                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;
                    double sum24h = 0; int count24h = 0;
                    for (int i = 0; i <= 24; i += 4) {
                        long pastTime = currentTime - (i * 3600 * 1000L);
                        Double past = FundingFeeManager.getInstance().getNearestFundingFee(symbol, pastTime);
                        if (past != null) { sum24h += past; count24h++; }
                    }
                    if (count24h > 0) totalAvg24H += (sum24h / count24h); else totalAvg24H += currentFunding;
                    validCount++;
                }
            }
            if (validCount > 0) {
                features.fundingRateRaw = totalCurrentFunding / validCount;
                features.fundingRateAvg24H = totalAvg24H / validCount;
            } else {
                features.fundingRateRaw = 0.0; features.fundingRateAvg24H = 0.0;
            }
            features.fundingRateTrend = features.fundingRateRaw - features.fundingRateAvg24H;
        } catch (Exception e) {
            features.fundingRateRaw = 0.0; features.fundingRateAvg24H = 0.0; features.fundingRateTrend = 0.0;
        }
    }

    private void extractTimeFeatures(DcaMarketFeatures features, long timestamp) {
        Calendar c = Calendar.getInstance(); c.setTimeInMillis(timestamp);
        features.hourOfDay = c.get(Calendar.HOUR_OF_DAY);
        features.dayOfWeek = c.get(Calendar.DAY_OF_WEEK);
        features.weekOfMonth = c.get(Calendar.WEEK_OF_MONTH);
        features.monthOfYear = c.get(Calendar.MONTH) + 1;
    }

    private double calculateElasticity(String symbol, KlineObjectSimple kline) {
        Double ma20 = historyManager.getMa(symbol, 20);

        // Lấy biên độ dao động trung bình (High - Low) của 20 nến gần nhất
        double avgRange = historyManager.getAverageRange(symbol, 20);

        // Bảo vệ chia cho 0 hoặc null
        if (ma20 == null || avgRange <= 0) return 0.0;

        // Tính khoảng cách tuyệt đối từ giá đến MA20
        double distFromMa = kline.priceClose - ma20;

        // Chuẩn hóa theo biên độ (Volatility Normalized)
        return distFromMa / avgRange;
    }
    private double calculateDistFromLow24H(String symbol, KlineObjectSimple kline) {
        Double low24 = historyManager.getLow24H(symbol);
        return (low24 != null && low24 > 0) ? (kline.priceClose - low24) / low24 : 0.0;
    }
    private double calculateVolatilityShock(String symbol, KlineObjectSimple kline) {
        double avgRange = historyManager.getAverageRange(symbol, 20);
        double currentRange = kline.maxPrice - kline.minPrice;
        return (avgRange > 0) ? currentRange / avgRange : 1.0;
    }
}