package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class FundingFeatureExtractorV2_15M {
    private static final Logger LOG = LoggerFactory.getLogger(FundingFeatureExtractorV2_15M.class);
    private final HistoryManager15M historyManager = HistoryManager15M.getInstance();

    // --- BỘ CACHE CHO CÁC FEATURE CHUNG (1 PHÚT TÍNH 1 LẦN) ---
    private volatile long lastCalculatedTimestamp = -1;

    private float cachedBtcMom1H, cachedBtcMom4H, cachedBtcMom24H;
    private float cachedMarketBreadth, cachedBtcDominance;
    private float cachedBasketMom15M, cachedBasketMom1H, cachedBasketMom24H;
    private float cachedBasketRsi14, cachedBasketVolSpike, cachedBasketFundingRaw;

    public void updateMarketHistory(Map<Short, KlineObjectSimple> snapshot) {
        historyManager.updateHistory(snapshot);
    }

    public FundingMarketFeatures15M extractFeatures(long currentTimestamp, OrderTargetInfoTest order,
                                                    Map<Short, KlineObjectSimple> currentSnapshot,
                                                    MarketDataObject15M rate, List<Short> targetBasket) {

        short symbolId = SimpleSymbolMapper.getInstance().getId(order.symbol);
        KlineObjectSimple kline = currentSnapshot.get(symbolId);
        if (kline == null) return null;

        if (targetBasket == null || targetBasket.isEmpty()) {
            targetBasket = Collections.singletonList(SimpleSymbolMapper.getInstance().getId("BTCUSDT"));
        }

        // 1. CẬP NHẬT CACHE CHUNG (Chỉ luồng đầu tiên của phút đó tính)
        if (currentTimestamp != lastCalculatedTimestamp) {
            synchronized (this) {
                if (currentTimestamp != lastCalculatedTimestamp) {
                    updateSharedFeatures(currentTimestamp, currentSnapshot, targetBasket);
                    lastCalculatedTimestamp = currentTimestamp;
                }
            }
        }

        FundingMarketFeatures15M f = new FundingMarketFeatures15M();

        // 2. GÁN FEATURE CHUNG
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

        // 3. TÍNH TOÁN COIN SPECIFIC
        f.momentum15M = (kline.priceClose - kline.priceOpen) / kline.priceOpen;
        f.momentum1H = calculateReturn(symbolId, 4, currentTimestamp); // 4 * 15m
        f.momentum4H = calculateReturn(symbolId, 16, currentTimestamp);
        f.momentum24H = calculateReturn(symbolId, 96, currentTimestamp);

        Float rsi = historyManager.getRsi14(symbolId);
        f.rsi1H = (rsi != null) ? rsi : 50.0f;

        f.distFromLow24H = calculateDistFromLow24H(symbolId, kline);
        f.volatilityShock = calculateVolatilityShock(symbolId, kline);

        extractCoinFundingFeatures(f, order.symbol, currentTimestamp);

        return f;
    }

    private void updateSharedFeatures(long currentTime, Map<Short, KlineObjectSimple> marketData, List<Short> basket) {
        short btcId = SimpleSymbolMapper.getInstance().getId("BTCUSDT");

        cachedBtcMom1H = calculateReturn(btcId, 4, currentTime);
        cachedBtcMom4H = calculateReturn(btcId, 16, currentTime);
        cachedBtcMom24H = calculateReturn(btcId, 96, currentTime);

        int upCount = 0, totalValid = 0;
        float upVol = 0, downVol = 0;
        for (KlineObjectSimple k : marketData.values()) {
            if (k.totalUsdt < 50000) continue; // Filter mạnh hơn cho 15m
            totalValid++;
            if (k.priceClose > k.priceOpen) {
                upCount++;
                upVol += k.totalUsdt;
            } else {
                downVol += k.totalUsdt;
            }
        }
        cachedMarketBreadth = (totalValid > 0) ? (float) upCount / totalValid : 0.5f;
        float btcVol = marketData.containsKey(btcId) ? marketData.get(btcId).totalUsdt : 0;
        cachedBtcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0f;

        float sumMom15m = 0, sumMom1h = 0, sumMom24h = 0, sumRsi = 0, sumVolSpike = 0, totalBasketFunding = 0;
        int count = 0, validFundingCount = 0;
        FundingFeeManager fm = FundingFeeManager.getInstance();

        for (Short symId : basket) {
            Float rsi = historyManager.getRsi14(symId);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom15m += calculateReturn(symId, 1, currentTime);
                sumMom1h += calculateReturn(symId, 4, currentTime);
                sumMom24h += calculateReturn(symId, 96, currentTime);

                float currentVol = historyManager.getSumVolume(symId, 1);
                float avgVol = historyManager.getAverageVolume(symId, 20);
                sumVolSpike += (avgVol > 0) ? currentVol / avgVol : 1.0f;
                count++;
            }
            try {
                String symStr = SimpleSymbolMapper.getInstance().getSymbol(symId);
                Float rate = fm.getNearestFundingFee(symStr, currentTime);
                if (rate != null) {
                    totalBasketFunding += rate;
                    validFundingCount++;
                }
            } catch (Exception ignored) {
            }
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

    private void extractCoinFundingFeatures(FundingMarketFeatures15M f, String symbol, long currentTime) {
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

    public float calculateReturn(short symbolId, int candlesBack, long currentTime) {
        Float currentPrice = historyManager.getPriceAt(symbolId, currentTime);
        long pastTime = currentTime - (candlesBack * 15 * 60000L);
        Float pastPrice = historyManager.getPriceAt(symbolId, pastTime);
        if (currentPrice != null && pastPrice != null && pastPrice > 0) return (currentPrice - pastPrice) / pastPrice;
        return 0.0f;
    }

    private float calculateDistFromLow24H(short symbolId, KlineObjectSimple kline) {
        Float low24 = historyManager.getLow24H(symbolId);
        return (low24 != null && low24 > 0) ? (kline.priceClose - low24) / low24 : 0.0f;
    }

    private float calculateVolatilityShock(short symbolId, KlineObjectSimple kline) {
        float avgRange = historyManager.getAverageRange(symbolId, 20); // 20 nến 15m
        float currentRange = kline.maxPrice - kline.minPrice;
        return (avgRange > 0) ? currentRange / avgRange : 1.0f;
    }
}