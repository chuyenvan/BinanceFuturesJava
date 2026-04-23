package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class FundingFeatureExtractor {
    private static final Logger LOG = LoggerFactory.getLogger(FundingFeatureExtractor.class);
    private final HistoryManager historyManager = HistoryManager.getInstance();

    public void updateMarketHistory(Map<String, KlineObjectSimple> snapshot) {
        historyManager.updateHistory(snapshot);
    }


    public FundingMarketFeatures extractFeatures(long currentTimestamp, OrderTargetInfoTest order,
                                                 Map<String, KlineObjectSimple> currentSnapshot,
                                                 MarketDataObject rate) {

        KlineObjectSimple kline = currentSnapshot.get(order.symbol);
        if (kline == null) return null;

        FundingMarketFeatures f = new FundingMarketFeatures();

        // --- 1. MACRO (BTC) ---
        f.btcMomentum1H = calculateReturn("BTCUSDT", 60);
        f.btcMomentum4H = calculateReturn("BTCUSDT", 240);
        f.btcMomentum24H = calculateReturn("BTCUSDT", 1440);
        extractMarketContext(f, currentSnapshot);

        // --- 2. COIN SPECIFIC ---
        // ✅ GÁN TRỰC TIẾP TỪ MarketDataObject
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

        f.rsi1H = historyManager.getRsi14(order.symbol);
        f.distFromLow24H = calculateDistFromLow24H(order.symbol, kline);
        f.volatilityShock = calculateVolatilityShock(order.symbol, kline);

        // --- 3. BASKET SPECIFIC ---
        List<String> targetBasket = CoinRankManager.getInstance().getTopCoin(currentTimestamp);
        if (targetBasket == null || targetBasket.isEmpty()) targetBasket = Collections.singletonList("BTCUSDT");
        extractBasketFeatures(f, targetBasket, currentTimestamp);

        // --- 4. FUNDING FEE ---
        extractFundingFeatures(f, order.symbol, targetBasket, currentTimestamp);

        return f;
    }

    // ================= HELPER METHODS =================

    private void extractBasketFeatures(FundingMarketFeatures f, List<String> basket, long currentTime) {
        float sumMom15m = 0, sumMom1h = 0, sumMom24h = 0, sumRsi = 0, sumVolSpike = 0;
        int count = 0;
        for (String symbol : basket) {
            Float rsi = historyManager.getRsi14(symbol);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);
                sumMom24h += calculateReturn(symbol, 1440);
                float currentVol = historyManager.getSumVolume(symbol, 1);
                float avgVol = historyManager.getAverageVolume(symbol, 20);
                if (avgVol > 0) sumVolSpike += currentVol / avgVol;
                else sumVolSpike += 1.0;
                count++;
            }
        }
        if (count > 0) {
            f.basketMomentum15M = sumMom15m / count;
            f.basketMomentum1H = sumMom1h / count;
            f.basketMomentum24H = sumMom24h / count;
            f.basketRsi14 = sumRsi / count;
            f.basketVolSpike = sumVolSpike / count;
        }
    }

    private void extractFundingFeatures(FundingMarketFeatures f, String symbol, List<String> basket, long currentTime) {
        try {
            FundingFeeManager fm = FundingFeeManager.getInstance();
            Float cf = fm.getNearestFundingFee(symbol, currentTime);
            f.coinFundingRate = (cf != null) ? cf : 0.0f;
            float totalBasketFunding = 0;
            int validCount = 0;
            for (String s : basket) {
                Float rate = fm.getNearestFundingFee(s, currentTime);
                if (rate != null) {
                    totalBasketFunding += rate;
                    validCount++;
                }
            }
            f.fundingRateRaw = (validCount > 0) ? totalBasketFunding / validCount : 0.0f;
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
            f.fundingRateRaw = 0;
            f.fundingRateAvg24H = 0;
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

    private void extractMarketContext(FundingMarketFeatures f, Map<String, KlineObjectSimple> marketData) {
        int upCount = 0;
        int totalValid = 0;
        float upVol = 0, downVol = 0;
        for (Map.Entry<String, KlineObjectSimple> entry : marketData.entrySet()) {
            KlineObjectSimple k = entry.getValue();
            if (k.totalUsdt < 5000) continue;
            totalValid++;
            if (k.priceClose > k.priceOpen) {
                upCount++;
                upVol += k.totalUsdt;
            } else {
                downVol += k.totalUsdt;
            }
        }
        f.marketBreadthStrength = (totalValid > 0) ? (float) upCount / totalValid : 0.5f;
        float btcVol = marketData.containsKey("BTCUSDT") ? marketData.get("BTCUSDT").totalUsdt : 0;
        f.btcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0f;
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