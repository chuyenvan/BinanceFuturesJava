package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class ComprehensiveMarketFeatureExtractor15M {
    private static final Logger LOG = LoggerFactory.getLogger(ComprehensiveMarketFeatureExtractor15M.class);
    private final HistoryManager15M historyManager = HistoryManager15M.getInstance();

    public MarketFeatures15M extractAllFeatures(long timestamp,
                                                Map<Short, KlineObjectSimple> currentMarketData,
                                                MarketDataObject15M marketData,
                                                List<Short> targetBasket) {

        MarketFeatures15M features = new MarketFeatures15M();
        features.timestamp = timestamp;
        features.dateKey = Utils.normalizeDateYYYYMMDD(timestamp);

        short anchorSymbolId = SimpleSymbolMapper.getInstance().getId("BTCUSDT");

        extractMomentumFeatures(features, anchorSymbolId, marketData, timestamp);
        extractVolatilityFeatures(features, anchorSymbolId, timestamp);
        extractTechnicalIndicators(features, anchorSymbolId, timestamp);
        extractBreadthFeatures(features, currentMarketData, targetBasket, timestamp);
        extractBasketTechnicalFeatures(features, targetBasket, timestamp);
        extractBasketFundingFeatures(features, targetBasket, timestamp);
        extractTimeFeatures(features, timestamp);

        return features;
    }

    private void extractMomentumFeatures(MarketFeatures15M features, short symbolId, MarketDataObject15M rate, long currentTime) {
        if (rate != null) features.momentum15M = rate.rateDownAvg;
        features.momentum1H = calculateReturn(symbolId, 4, currentTime);   // 4 * 15m = 1H
        features.momentum4H = calculateReturn(symbolId, 16, currentTime);  // 16 * 15m = 4H
        features.momentum24H = calculateReturn(symbolId, 96, currentTime); // 96 * 15m = 24H
        features.momentumAcceleration = features.momentum1H - features.momentum15M;

        short ethId = SimpleSymbolMapper.getInstance().getId("ETHUSDT");
        features.trendStrengthETH = calculateReturn(ethId, 16, currentTime);
        features.trendConsistency = (features.momentum1H * features.momentum4H > 0) ? 1.0f : -1.0f;
    }

    private void extractVolatilityFeatures(MarketFeatures15M features, short symbolId, long currentTime) {
        features.volatility1H = calculateVolatility(symbolId, 4, currentTime);
        features.volatility4H = calculateVolatility(symbolId, 16, currentTime);
        features.volatility24H = calculateVolatility(symbolId, 96, currentTime);

        if (features.volatility24H != 0)
            features.volatilityTermStructure = features.volatility4H / features.volatility24H;

        if (features.volatility4H > 0.02) features.volatilityRegime = "HIGH";
        else if (features.volatility4H < 0.005) features.volatilityRegime = "LOW";
        else features.volatilityRegime = "NORMAL";
    }

    private void extractTechnicalIndicators(MarketFeatures15M features, short symbolId, long currentTime) {
        // Tận dụng HistoryManager O(1). Vì đã updateHistory() trước khi gọi hàm này, head đang ở đúng currentTime.
        Float rsi = historyManager.getRsi14(symbolId);
        features.rsi14 = (rsi != null) ? rsi : 50.0f;

        float currentVol = historyManager.getSumVolume(symbolId, 1);
        float avgVol = historyManager.getAverageVolume(symbolId, 20);
        features.volumeSpike = (avgVol > 0) ? currentVol / avgVol : 1.0f;

        Float ma20 = historyManager.getMa(symbolId, 20);
        Float currentPrice = historyManager.getPriceAt(symbolId, currentTime);

        if (currentPrice != null && ma20 != null && ma20 > 0) {
            features.distMA20 = (currentPrice - ma20) / ma20;
        } else {
            features.distMA20 = 0.0f;
        }
    }

    private void extractBreadthFeatures(MarketFeatures15M features, Map<Short, KlineObjectSimple> marketData, List<Short> targetBasket, long currentTime) {
        int upCount = 0, downCount = 0; float upVol = 0, downVol = 0; int totalValid = 0, aboveMA20Count = 0;

        for (Short symId : targetBasket) {
            KlineObjectSimple k = marketData.get(symId);
            if (k == null) continue;
            totalValid++;

            if (k.priceClose > k.priceOpen) {
                upCount++; upVol += k.totalUsdt;
            } else if (k.priceClose < k.priceOpen) {
                downCount++; downVol += k.totalUsdt;
            }

            Float ma20 = historyManager.getMa(symId, 20);
            if (ma20 != null && k.priceClose > ma20) aboveMA20Count++;
        }

        features.advanceDeclineRatio = (downCount > 0) ? (float) upCount / downCount : 10.0f;
        features.volumeRatioUpDown = (downVol > 0) ? upVol / downVol : 10.0f;
        features.marketBreadthStrength = (totalValid > 0) ? (float) upCount / totalValid : 0.5f;
        features.percentAboveMA20 = (totalValid > 0) ? (float) aboveMA20Count / totalValid : 0.5f;

        short btcId = SimpleSymbolMapper.getInstance().getId("BTCUSDT");
        float btcVol = marketData.containsKey(btcId) ? marketData.get(btcId).totalUsdt : 0;
        features.btcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0f;
    }

    private void extractBasketTechnicalFeatures(MarketFeatures15M features, List<Short> basket, long currentTime) {
        if (basket == null || basket.isEmpty()) {
            features.basketRsi14 = features.rsi14;
            features.basketMomentum1H = features.momentum1H;
            features.basketMomentum4H = features.momentum4H;
            features.basketVolSpike = features.volumeSpike;
            return;
        }

        float sumRsi = 0, sumMom1h = 0, sumMom4h = 0, sumVolSpike = 0; int count = 0;
        for (Short symId : basket) {
            Float rsi = historyManager.getRsi14(symId);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom1h += calculateReturn(symId, 4, currentTime);
                sumMom4h += calculateReturn(symId, 16, currentTime);

                float currentVol = historyManager.getSumVolume(symId, 1);
                float avgVol = historyManager.getAverageVolume(symId, 20);
                sumVolSpike += (avgVol > 0) ? currentVol / avgVol : 1.0f;
                count++;
            }
        }

        if (count > 0) {
            features.basketRsi14 = sumRsi / count;
            features.basketMomentum1H = sumMom1h / count;
            features.basketMomentum4H = sumMom4h / count;
            features.basketVolSpike = sumVolSpike / count;
        } else {
            features.basketRsi14 = features.rsi14;
            features.basketMomentum1H = features.momentum1H;
            features.basketMomentum4H = features.momentum4H;
            features.basketVolSpike = features.volumeSpike;
        }
    }

    // =========================================================
    // HÀM TOÁN HỌC HỖ TRỢ TRUY XUẤT LỊCH SỬ CHUẨN XÁC
    // =========================================================

    private float calculateReturn(short symbolId, int candlesBack, long currentTime) {
        Float currentPrice = historyManager.getPriceAt(symbolId, currentTime);
        long pastTime = currentTime - (candlesBack * 15 * 60000L);
        Float pastPrice = historyManager.getPriceAt(symbolId, pastTime);

        if (currentPrice != null && pastPrice != null && pastPrice > 0) {
            return (currentPrice - pastPrice) / pastPrice;
        }
        return 0.0f;
    }

    private float calculateVolatility(short symbolId, int periods, long currentTime) {
        List<Float> closes = new ArrayList<>();
        // Lấy giá từ hiện tại lùi về quá khứ
        for (int i = 0; i <= periods; i++) {
            Float p = historyManager.getPriceAt(symbolId, currentTime - (i * 15 * 60000L));
            if (p != null) closes.add(p);
        }

        if (closes.size() < 2) return 0.0f;

        float sum = 0, sumSq = 0; int count = 0;
        // closes[0] là nến mới nhất, closes[1] là nến cũ hơn
        // Return = (Mới - Cũ) / Cũ
        for (int i = 0; i < closes.size() - 1; i++) {
            float r = (closes.get(i) - closes.get(i + 1)) / closes.get(i + 1);
            sum += r;
            sumSq += r * r;
            count++;
        }
        return (count < 2) ? 0.0f : (float) Math.sqrt(Math.max(0, (sumSq - (sum * sum) / count) / (count - 1)));
    }

    private void extractBasketFundingFeatures(MarketFeatures15M features, List<Short> basket, long currentTime) {
        try {
            if (basket == null || basket.isEmpty()) {
                basket = Collections.singletonList(SimpleSymbolMapper.getInstance().getId("BTCUSDT"));
            }

            float totalCurrentFunding = 0; float totalAvg24H = 0; int validCount = 0;

            for (Short symId : basket) {
                // Map ngược lại ra String để dùng cho FundingFeeManager cũ
                String symbolStr = SimpleSymbolMapper.getInstance().getSymbol(symId);
                if (symbolStr == null || symbolStr.startsWith("UNKNOWN")) continue;

                Float currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbolStr, currentTime);
                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;

                    float sum24h = 0; int count24h = 0;
                    // Lấy Funding 24H qua (Binance nhả Funding mỗi 8 tiếng, nhưng để an toàn ta chọc mẫu cách 4 tiếng)
                    for (int i = 0; i <= 24; i += 4) {
                        long pastTime = currentTime - (i * 3600 * 1000L);
                        Float past = FundingFeeManager.getInstance().getNearestFundingFee(symbolStr, pastTime);
                        if (past != null) {
                            sum24h += past;
                            count24h++;
                        }
                    }

                    if (count24h > 0) {
                        totalAvg24H += (sum24h / count24h);
                    } else {
                        totalAvg24H += currentFunding;
                    }
                    validCount++;
                }
            }

            if (validCount > 0) {
                features.fundingRateRaw = totalCurrentFunding / validCount;
                features.fundingRateAvg24H = totalAvg24H / validCount;
            } else {
                features.fundingRateRaw = 0.0f; features.fundingRateAvg24H = 0.0f;
            }

            features.fundingRateTrend = features.fundingRateRaw - features.fundingRateAvg24H;

        } catch (Exception e) {
            LOG.error("Lỗi khi extract Funding Features", e);
            features.fundingRateRaw = 0.0f; features.fundingRateAvg24H = 0.0f; features.fundingRateTrend = 0.0f;
        }
    }

    private void extractTimeFeatures(MarketFeatures15M features, long timestamp) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(timestamp);

        features.hourOfDay = c.get(Calendar.HOUR_OF_DAY);
        features.dayOfWeek = c.get(Calendar.DAY_OF_WEEK);
        features.weekOfMonth = c.get(Calendar.WEEK_OF_MONTH);
        features.monthOfYear = c.get(Calendar.MONTH) + 1;
    }
}