package com.binance.chuyennd.ai_ml.features.export.entry;


import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public class ComprehensiveMarketFeatureExtractor {
    private static final Logger LOG = LoggerFactory.getLogger(ComprehensiveMarketFeatureExtractor.class);

    // 🔥 DÙNG HISTORY MANAGER THAY VÌ MAP RIÊNG
    private final HistoryManager historyManager = new HistoryManager();

    // Theo dõi danh sách symbol đang có history để iterate (Vì HistoryManager có thể ẩn Map)
    private final Set<String> activeSymbols = ConcurrentHashMap.newKeySet();

    public ComprehensiveMarketFeatureExtractor() {
    }

    public void initDataFromTickerMap(TreeMap<Long, Map<String, KlineObjectSimple>> time2Ticker) {
        LOG.info("AI Feature Extractor: Syncing history from {} size: {}",
                Utils.normalizeDateYYYYMMDDHHmm(time2Ticker.firstKey()), time2Ticker.size());

        for (Map<String, KlineObjectSimple> tickerMap : time2Ticker.values()) {
            updateMarketHistory(tickerMap);
        }

        LOG.info("AI Feature Extractor: Completed syncing {} history from {}.",
                time2Ticker.size(), Utils.normalizeDateYYYYMMDDHHmm(time2Ticker.firstKey()));
    }

    // =========================================================================
    // 🔥 TRÙM CUỐI: CHẶN ĐỨNG SAI SỐ MILI-GIÂY KHI NẠP NẾN VÀO LỊCH SỬ
    // =========================================================================
    public void updateMarketHistory(Map<String, KlineObjectSimple> currentMarketData) {
        Map<String, KlineObjectSimple> cleanedMarketData = new HashMap<>();

        for (Map.Entry<String, KlineObjectSimple> entry : currentMarketData.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple originalKline = entry.getValue();

            // Bỏ qua nến hỏng
            if (originalKline == null || originalKline.startTime == null) continue;

            // Chặt bỏ phần mili-giây thừa mứa để Key luôn là chẵn phút (VD: 1776603120000)
            long cleanStartTime = (originalKline.startTime.longValue() / 60000L) * 60000L;

            // Cập nhật trực tiếp lại startTime của nến
            originalKline.startTime = cleanStartTime;

            cleanedMarketData.put(symbol, originalKline);
        }

        historyManager.updateHistory(cleanedMarketData);
        activeSymbols.addAll(cleanedMarketData.keySet());
    }

    public MarketFeatures extractAllFeatures(long timestamp,
                                             Map<String, KlineObjectSimple> currentMarketData,
                                             MarketDataObject marketData) {

        // 🔥 ÉP LÀM TRÒN VỀ ĐẦU PHÚT CHẴN ĐỂ ĐỒNG BỘ VỚI HISTORY MANAGER
        timestamp = (timestamp / 60000L) * 60000L;

        // 1. Cập nhật dữ liệu mới nhất (Đã được chặt mili-giây ở hàm trên)
        updateMarketHistory(currentMarketData);
        List<String> targetBasket = new ArrayList<>(currentMarketData.keySet());

        MarketFeatures features = new MarketFeatures();
        features.timestamp = timestamp;
        features.dateKey = Utils.normalizeDateYYYYMMDD(timestamp);

        String anchorSymbol = "BTCUSDT";
        extractMomentumFeatures(features, anchorSymbol, marketData);
        extractVolatilityFeatures(features, anchorSymbol);
        extractTechnicalIndicators(features, anchorSymbol);
        extractBreadthFeatures(features, currentMarketData);
        extractBasketTechnicalFeatures(features, targetBasket);
        extractBasketFundingFeatures(features, targetBasket, timestamp);
        extractTimeFeatures(features, timestamp);

        return features;
    }


    // --- CÁC HÀM EXTRACT SỬ DỤNG HISTORY MANAGER ---

    private void extractMomentumFeatures(MarketFeatures features, String symbol, MarketDataObject rate) {
        if (rate != null) {
            features.momentum1M = rate.rateDownAvg;
            features.momentum15M = rate.rateDown15MAvg;
        }
        features.momentum5M = calculateReturn(symbol, 5);
        features.momentum1H = calculateReturn(symbol, 60);
        features.momentum4H = calculateReturn(symbol, 240);
        features.momentum24H = calculateReturn(symbol, 1440);
        features.momentumAcceleration = features.momentum5M - features.momentum15M;
        features.trendStrengthETH = calculateReturn("ETHUSDT", 60);
        features.trendConsistency = (features.momentum5M * features.momentum1H > 0) ? 1.0f : -1.0f;
    }

    private void extractVolatilityFeatures(MarketFeatures features, String symbol) {
        features.volatility1M = calculateVolatility(symbol, 3);
        features.volatility15M = calculateVolatility(symbol, 15);
        features.volatility1H = calculateVolatility(symbol, 60);
        features.volatility24H = calculateVolatility(symbol, 1440);

        if (features.volatility24H != 0)
            features.volatilityTermStructure = features.volatility1H / features.volatility24H;

        if (features.volatility1H > 0.01) features.volatilityRegime = "HIGH";
        else if (features.volatility1H < 0.002) features.volatilityRegime = "LOW";
        else features.volatilityRegime = "NORMAL";
    }

    private void extractTechnicalIndicators(MarketFeatures features, String symbol) {
        // Sử dụng hàm có sẵn trong HistoryManager nếu có, hoặc tính thủ công từ history list
        Float rsi = historyManager.getRsi14(symbol);
        features.rsi14 = (rsi != null) ? rsi : 50.0f;

        float currentVol = historyManager.getSumVolume(symbol, 1);
        float avgVol = historyManager.getAverageVolume(symbol, 20); // 20 nến gần nhất
        features.volumeSpike = (avgVol > 0) ? currentVol / avgVol : 1.0f;

        Float ma20 = historyManager.getMa(symbol, 20);
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h != null && !h.isEmpty() && ma20 != null && ma20 > 0) {
            float close = h.get(h.size() - 1).priceClose;
            features.distMA20 = (close - ma20) / ma20;
        } else {
            features.distMA20 = 0.0f;
        }
    }

    private void extractBreadthFeatures(MarketFeatures features, Map<String, KlineObjectSimple> marketData) {
        int upCount = 0, downCount = 0;
        float upVol = 0, downVol = 0;
        int totalValid = 0, aboveMA20Count = 0;
        for (Map.Entry<String, KlineObjectSimple> entry : marketData.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple k = entry.getValue();
            if (k.totalUsdt < 5000) continue;
            totalValid++;
            if (k.priceClose > k.priceOpen) {
                upCount++;
                upVol += k.totalUsdt;
            } else if (k.priceClose < k.priceOpen) {
                downCount++;
                downVol += k.totalUsdt;
            }

            Float ma20 = historyManager.getMa(symbol, 20);
            if (ma20 != null && k.priceClose > ma20) aboveMA20Count++;
        }
        features.advanceDeclineRatio = (downCount > 0) ? (float) upCount / downCount : 10.0f;
        features.volumeRatioUpDown = (downVol > 0) ? upVol / downVol : 10.0f;
        features.marketBreadthStrength = (totalValid > 0) ? (float) upCount / totalValid : 0.5f;
        features.percentAboveMA20 = (totalValid > 0) ? (float) aboveMA20Count / totalValid : 0.5f;
        float btcVol = marketData.containsKey("BTCUSDT") ? marketData.get("BTCUSDT").totalUsdt : 0;
        features.btcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0f;
    }

    private void extractBasketTechnicalFeatures(MarketFeatures features, List<String> basket) {
        if (basket == null || basket.isEmpty()) {
            features.basketRsi14 = features.rsi14;
            features.basketMomentum15M = features.momentum15M;
            features.basketMomentum1H = features.momentum1H;
            features.basketVolSpike = features.volumeSpike;
            return;
        }
        float sumRsi = 0, sumMom15m = 0, sumMom1h = 0, sumVolSpike = 0;
        int count = 0;
        for (String symbol : basket) {
            Float rsi = historyManager.getRsi14(symbol);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);

                float currentVol = historyManager.getSumVolume(symbol, 1);
                float avgVol = historyManager.getAverageVolume(symbol, 20);
                float volSpike = (avgVol > 0) ? currentVol / avgVol : 1.0f;
                sumVolSpike += volSpike;

                count++;
            }
        }
        if (count > 0) {
            features.basketRsi14 = sumRsi / count;
            features.basketMomentum15M = sumMom15m / count;
            features.basketMomentum1H = sumMom1h / count;
            features.basketVolSpike = sumVolSpike / count;
        } else {
            features.basketRsi14 = features.rsi14;
            features.basketMomentum15M = features.momentum15M;
            features.basketMomentum1H = features.momentum1H;
            features.basketVolSpike = features.volumeSpike;
        }
    }

    // --- HELPER METHODS SỬ DỤNG HISTORY LIST TỪ MANAGER ---

    private float calculateReturn(String symbol, int minutes) {
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h == null || h.isEmpty()) return 0.0f;

        KlineObjectSimple current = h.get(h.size() - 1);
        long pastTime = current.startTime.longValue() - (minutes * 60000L);

        Float pastPrice = historyManager.getPriceAt(symbol, pastTime);
        if (pastPrice != null && pastPrice > 0) {
            return (current.priceClose - pastPrice) / pastPrice;
        }
        return 0.0f;
    }

    private float calculateVolatility(String symbol, int periods) {
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h == null || h.size() < 5) return 0.0f;

        int start = Math.max(0, h.size() - periods);
        float sum = 0, sumSq = 0;
        int count = 0;
        for (int i = start; i < h.size() - 1; i++) {
            float r = (h.get(i + 1).priceClose - h.get(i).priceClose) / h.get(i).priceClose;
            sum += r;
            sumSq += r * r;
            count++;
        }
        return (count < 2) ? 0.0f : (float) Math.sqrt(Math.max(0, (sumSq - (sum * sum) / count) / (count - 1)));
    }

    private void extractBasketFundingFeatures(MarketFeatures features, List<String> basket, long currentTime) {
        try {
            if (basket == null || basket.isEmpty()) basket = Collections.singletonList("BTCUSDT");
            float totalCurrentFunding = 0;
            float totalAvg24H = 0;
            int validCount = 0;
            for (String symbol : basket) {
                Float currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, currentTime);
                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;
                    float sum24h = 0;
                    int count24h = 0;
                    for (int i = 0; i <= 24; i += 4) {
                        long pastTime = currentTime - (i * 3600 * 1000L);
                        Float past = FundingFeeManager.getInstance().getNearestFundingFee(symbol, pastTime);
                        if (past != null) {
                            sum24h += past;
                            count24h++;
                        }
                    }
                    if (count24h > 0) totalAvg24H += (sum24h / count24h);
                    else totalAvg24H += currentFunding;
                    validCount++;
                }
            }
            if (validCount > 0) {
                features.fundingRateRaw = totalCurrentFunding / validCount;
                features.fundingRateAvg24H = totalAvg24H / validCount;
            } else {
                features.fundingRateRaw = 0.0f;
                features.fundingRateAvg24H = 0.0f;
            }
            features.fundingRateTrend = features.fundingRateRaw - features.fundingRateAvg24H;
        } catch (Exception e) {
            features.fundingRateRaw = 0.0f;
            features.fundingRateAvg24H = 0.0f;
            features.fundingRateTrend = 0.0f;
        }
    }


    private void extractTimeFeatures(MarketFeatures features, long timestamp) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(timestamp);
        features.hourOfDay = c.get(Calendar.HOUR_OF_DAY);
        features.dayOfWeek = c.get(Calendar.DAY_OF_WEEK);
        features.weekOfMonth = c.get(Calendar.WEEK_OF_MONTH);
        features.monthOfYear = c.get(Calendar.MONTH) + 1;
    }

    private void validateAndCleanFeatures(MarketFeatures f) {
        if (Float.isNaN(f.momentum1M)) f.momentum1M = 0.0f;
        if (Float.isNaN(f.rsi14)) f.rsi14 = 50.0f;
        if (Float.isInfinite(f.advanceDeclineRatio)) f.advanceDeclineRatio = 10.0f;
        if (Float.isNaN(f.fundingRateRaw)) f.fundingRateRaw = 0.0f;
    }
}