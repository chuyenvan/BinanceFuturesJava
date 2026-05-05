package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class FundingFeatureExtractorV2 {
    private static final Logger LOG = LoggerFactory.getLogger(FundingFeatureExtractorV2.class);
    private final HistoryManager historyManager = HistoryManager.getInstance();

    // --- BỘ CACHE CHO CÁC FEATURE CHUNG (DÙNG CHUNG CHO TẤT CẢ COIN TRONG CÙNG 1 PHÚT) ---
    private volatile long lastCalculatedTimestamp = -1;

    // Macro Cache
    private float cachedBtcMom1H;
    private float cachedBtcMom4H;
    private float cachedBtcMom24H;
    private float cachedMarketBreadth;
    private float cachedBtcDominance;

    // Basket Cache
    private float cachedBasketMom15M;
    private float cachedBasketMom1H;
    private float cachedBasketMom24H;
    private float cachedBasketRsi14;
    private float cachedBasketVolSpike;
    private float cachedBasketFundingRaw;

    public void updateMarketHistory(Map<String, KlineObjectSimple> snapshot) {
        historyManager.updateHistory(snapshot);
    }

    public FundingMarketFeatures extractFeatures(long currentTimestamp, OrderTargetInfoTest order,
                                                 Map<String, KlineObjectSimple> currentSnapshot,
                                                 MarketDataObject rate, List<String> targetBasket) {

        KlineObjectSimple kline = currentSnapshot.get(order.symbol);
        if (kline == null) return null;
        if (targetBasket == null || targetBasket.isEmpty()) targetBasket = Collections.singletonList("BTCUSDT");

        // 1. KIỂM TRA VÀ CẬP NHẬT CACHE CHUNG (Chỉ luồng đầu tiên của phút đó phải tính)
        if (currentTimestamp != lastCalculatedTimestamp) {
            synchronized (this) {
                // Double-checked locking để an toàn tuyệt đối trong parallelStream
                if (currentTimestamp != lastCalculatedTimestamp) {
                    updateSharedFeatures(currentTimestamp, currentSnapshot, targetBasket);
                    lastCalculatedTimestamp = currentTimestamp;
                }
            }
        }

        FundingMarketFeatures f = new FundingMarketFeatures();

        // --- 2. GÁN CÁC FEATURE CHUNG TỪ CACHE (Tốc độ O(1)) ---
        f.btcMomentum1H = cachedBtcMom1H;
        f.btcMomentum4H = cachedBtcMom4H;
        f.btcMomentum24H = cachedBtcMom24H;
        f.marketBreadthStrength = cachedMarketBreadth;
        f.btcDominance = cachedBtcDominance;

        f.basketMomentum15M = cachedBasketMom15M;
        f.basketMomentum1H = cachedBasketMom1H;
        f.basketMomentum24H = cachedBasketMom24H;
        f.basketRsi14 = cachedBasketRsi14;
        f.basketVolSpike = cachedBasketVolSpike;
        f.fundingRateRaw = cachedBasketFundingRaw;

        // --- 3. TÍNH TOÁN COIN SPECIFIC (Bắt buộc tính riêng cho từng coin) ---
        if (rate != null) {
            f.momentum1M = rate.rateDownAvg;
            f.momentum15M = rate.rateDown15MAvg;
        } else {
            f.momentum1M = 0;
            f.momentum15M = 0;
        }

        f.momentum1H = calculateReturn(order.symbol, 60);
        f.momentum4H = calculateReturn(order.symbol, 240);
        f.momentum24H = calculateReturn(order.symbol, 1440);

        Float rsi = historyManager.getRsi14(order.symbol);
        f.rsi1H = (rsi != null) ? rsi : 0.0f;
        f.distFromLow24H = calculateDistFromLow24H(order.symbol, kline);
        f.volatilityShock = calculateVolatilityShock(order.symbol, kline);

        // Funding riêng của coin
        extractCoinFundingFeatures(f, order.symbol, currentTimestamp);

        return f;
    }

    // ================= HELPER METHODS (CHỈ CHẠY 1 LẦN/PHÚT) =================

    private void updateSharedFeatures(long currentTime, Map<String, KlineObjectSimple> marketData, List<String> basket) {
        // 1. BTC Macro
        cachedBtcMom1H = calculateReturn("BTCUSDT", 60);
        cachedBtcMom4H = calculateReturn("BTCUSDT", 240);
        cachedBtcMom24H = calculateReturn("BTCUSDT", 1440);

        // 2. Market Context
        int upCount = 0;
        int totalValid = 0;
        float upVol = 0, downVol = 0;
        for (KlineObjectSimple k : marketData.values()) {
            if (k.totalUsdt < 5000) continue;
            totalValid++;
            if (k.priceClose > k.priceOpen) {
                upCount++;
                upVol += k.totalUsdt;
            } else {
                downVol += k.totalUsdt;
            }
        }
        cachedMarketBreadth = (totalValid > 0) ? (float) upCount / totalValid : 0.5f;
        float btcVol = marketData.containsKey("BTCUSDT") ? marketData.get("BTCUSDT").totalUsdt : 0;
        cachedBtcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0f;

        // 3. Basket Context & Basket Funding
        float sumMom15m = 0, sumMom1h = 0, sumMom24h = 0, sumRsi = 0, sumVolSpike = 0, totalBasketFunding = 0;
        int count = 0, validFundingCount = 0;
        FundingFeeManager fm = FundingFeeManager.getInstance();

        for (String symbol : basket) {
            // Basket Price Features
            Float rsi = historyManager.getRsi14(symbol);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);
                sumMom24h += calculateReturn(symbol, 1440);
                float currentVol = historyManager.getSumVolume(symbol, 1);
                float avgVol = historyManager.getAverageVolume(symbol, 20);
                sumVolSpike += (avgVol > 0) ? currentVol / avgVol : 1.0f;
                count++;
            }
            // Basket Funding Features
            try {
                Float rate = fm.getNearestFundingFee(symbol, currentTime);
                if (rate != null) {
                    totalBasketFunding += rate;
                    validFundingCount++;
                }
            } catch (Exception ignored) {}
        }

        if (count > 0) {
            cachedBasketMom15M = sumMom15m / count;
            cachedBasketMom1H = sumMom1h / count;
            cachedBasketMom24H = sumMom24h / count;
            cachedBasketRsi14 = sumRsi / count;
            cachedBasketVolSpike = sumVolSpike / count;
        } else {
            cachedBasketMom15M = cachedBasketMom1H = cachedBasketMom24H = cachedBasketRsi14 = cachedBasketVolSpike = 0;
        }

        cachedBasketFundingRaw = (validFundingCount > 0) ? totalBasketFunding / validFundingCount : 0.0f;
    }

    private void extractCoinFundingFeatures(FundingMarketFeatures f, String symbol, long currentTime) {
        try {
            FundingFeeManager fm = FundingFeeManager.getInstance();
            Float cf = fm.getNearestFundingFee(symbol, currentTime);
            f.coinFundingRate = (cf != null) ? cf : 0.0f;

            float sum24h = 0;
            int count24h = 0;
            for (int i = 0; i <= 24; i += 4) {
                long pastTime = currentTime - (i * 3600 * 1000L);
                Float past = fm.getNearestFundingFee(symbol, pastTime);
                if (past != null) {
                    sum24h += past;
                    count24h++;
                }
            }
            f.fundingRateAvg24H = (count24h > 0) ? sum24h / count24h : f.coinFundingRate;
            f.fundingRateTrend = f.coinFundingRate - f.fundingRateAvg24H;
        } catch (Exception e) {
            f.coinFundingRate = 0;
            f.fundingRateAvg24H = 0;
            f.fundingRateTrend = 0;
        }
    }

    public float calculateReturn(String symbol, int minutes) {
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h == null || h.isEmpty()) return 0.0f;
        KlineObjectSimple current = h.get(h.size() - 1);
        long pastTime = current.startTime.longValue() - (minutes * 60000L);
        Float pastPrice = historyManager.getPriceAt(symbol, pastTime);
        if (pastPrice != null && pastPrice > 0) return (current.priceClose - pastPrice) / pastPrice;
        return 0.0f;
    }

    private float calculateDistFromLow24H(String symbol, KlineObjectSimple kline) {
        Float low24 = historyManager.getLow24H(symbol);
        return (low24 != null && low24 > 0) ? (kline.priceClose - low24) / low24 : 0.0f;
    }

    private float calculateVolatilityShock(String symbol, KlineObjectSimple kline) {
        float avgRange = historyManager.getAverageRange(symbol, 20);
        float currentRange = kline.maxPrice - kline.minPrice;
        return (avgRange > 0) ? currentRange / avgRange : 1.0f;
    }
}