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

    // Cập nhật History thông qua Manager
    public void updateMarketHistory(Map<String, KlineObjectSimple> currentMarketData) {
        historyManager.updateHistory(currentMarketData);
        activeSymbols.addAll(currentMarketData.keySet());
    }

    // 🔥 METHOD: Tìm Basket dựa trên History (Logic drop 15m)
    public List<String> findPotentialLosers(long currentTimestamp) {
        List<Map.Entry<String, Double>> drops = new ArrayList<>();
        long startTime = currentTimestamp - (15 * 60 * 1000L); // 15 phút trước

        for (String symbol : activeSymbols) {
            List<KlineObjectSimple> history = historyManager.getHistory(symbol);
            if (history == null || history.isEmpty()) continue;

//            KlineObjectSimple currentKline = history.get(history.size() - 1);
//
//            // 1. Lọc Volume rác (< 50k USDT)
//            if (currentKline.totalUsdt < 5000) continue;
//
//            // 2. Tìm đỉnh giá trong 15 phút gần nhất
//            double maxPrice15m = -1.0;
//
//            // Duyệt ngược từ cuối lên
//            for (int i = history.size() - 1; i >= 0; i--) {
//                KlineObjectSimple k = history.get(i);
//                if (k.startTime < startTime) break;
//                if (k.maxPrice > maxPrice15m) {
//                    maxPrice15m = k.maxPrice;
//                }
//            }
//
//            // 3. Tính độ sụt giảm
//            if (maxPrice15m > 0) {
//                double currentPrice = currentKline.priceClose;
//                double dropFromPeak = (currentPrice - maxPrice15m) / maxPrice15m;
//
//                // Giảm > 0.1% là lấy (Logic Relaxed)
//                if (dropFromPeak < -0.001) {
//                    drops.add(new AbstractMap.SimpleEntry<>(symbol, dropFromPeak));
//                }
//            }

                    drops.add(new AbstractMap.SimpleEntry<>(symbol, 0d));
        }

        // Sort giảm dần theo mức giảm (giảm nhiều nhất lên đầu)
        drops.sort(Map.Entry.comparingByValue());

        // Lấy Top 60
        return drops.stream()
                .limit(60)
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }

    public MarketFeatures extractAllFeatures(long timestamp,
                                             Map<String, KlineObjectSimple> currentMarketData,
                                             MarketDataObject marketData) {

        // 1. Cập nhật dữ liệu mới nhất
        updateMarketHistory(currentMarketData);
        List<String> targetBasket = findPotentialLosers(timestamp);


        MarketFeatures features = new MarketFeatures();
        features.timestamp = timestamp;
        features.dateKey = Utils.normalizeDateYYYYMMDD(timestamp);

        String anchorSymbol = "BTCUSDT";
        extractMomentumFeatures(features, anchorSymbol, marketData);
        extractVolatilityFeatures(features, anchorSymbol);
        extractTechnicalIndicators(features, anchorSymbol);
        extractBreadthFeatures(features, currentMarketData);

        extractBasketFundingFeatures(features, targetBasket, timestamp);
        extractBasketTechnicalFeatures(features, targetBasket);

        extractTimeFeatures(features, timestamp);
        validateAndCleanFeatures(features);

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
        features.trendConsistency = (features.momentum5M * features.momentum1H > 0) ? 1.0 : -1.0;
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
        Double rsi = historyManager.getRsi14(symbol);
        features.rsi14 = (rsi != null) ? rsi : 50.0;

        double currentVol = historyManager.getSumVolume(symbol, 1);
        double avgVol = historyManager.getAverageVolume(symbol, 20); // 20 nến gần nhất
        features.volumeSpike = (avgVol > 0) ? currentVol / avgVol : 1.0;

        Double ma20 = historyManager.getMa(symbol, 20);
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h != null && !h.isEmpty() && ma20 != null && ma20 > 0) {
            double close = h.get(h.size() - 1).priceClose;
            features.distMA20 = (close - ma20) / ma20;
        } else {
            features.distMA20 = 0.0;
        }
    }

    private void extractBreadthFeatures(MarketFeatures features, Map<String, KlineObjectSimple> marketData) {
        int upCount = 0, downCount = 0;
        double upVol = 0, downVol = 0;
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

            Double ma20 = historyManager.getMa(symbol, 20);
            if (ma20 != null && k.priceClose > ma20) aboveMA20Count++;
        }
        features.advanceDeclineRatio = (downCount > 0) ? (double) upCount / downCount : 10.0;
        features.volumeRatioUpDown = (downVol > 0) ? upVol / downVol : 10.0;
        features.marketBreadthStrength = (totalValid > 0) ? (double) upCount / totalValid : 0.5;
        features.percentAboveMA20 = (totalValid > 0) ? (double) aboveMA20Count / totalValid : 0.5;
        double btcVol = marketData.containsKey("BTCUSDT") ? marketData.get("BTCUSDT").totalUsdt : 0;
        features.btcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0;
    }

    private void extractBasketTechnicalFeatures(MarketFeatures features, List<String> basket) {
        if (basket == null || basket.isEmpty()) {
            features.basketRsi14 = features.rsi14;
            features.basketMomentum15M = features.momentum15M;
            features.basketMomentum1H = features.momentum1H;
            features.basketVolSpike = features.volumeSpike;
            return;
        }
        double sumRsi = 0, sumMom15m = 0, sumMom1h = 0, sumVolSpike = 0;
        int count = 0;
        for (String symbol : basket) {
            Double rsi = historyManager.getRsi14(symbol);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);

                double currentVol = historyManager.getSumVolume(symbol, 1);
                double avgVol = historyManager.getAverageVolume(symbol, 20);
                double volSpike = (avgVol > 0) ? currentVol / avgVol : 1.0;
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

    private double calculateVolatility(String symbol, int periods) {
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h == null || h.size() < 5) return 0.0;

        int start = Math.max(0, h.size() - periods);
        double sum = 0, sumSq = 0;
        int count = 0;
        for (int i = start; i < h.size() - 1; i++) {
            double r = (h.get(i + 1).priceClose - h.get(i).priceClose) / h.get(i).priceClose;
            sum += r;
            sumSq += r * r;
            count++;
        }
        return (count < 2) ? 0.0 : Math.sqrt(Math.max(0, (sumSq - (sum * sum) / count) / (count - 1)));
    }

    private void extractBasketFundingFeatures(MarketFeatures features, List<String> basket, long currentTime) {
        try {
            if (basket == null || basket.isEmpty()) basket = Collections.singletonList("BTCUSDT");
            double totalCurrentFunding = 0;
            double totalAvg24H = 0;
            int validCount = 0;
            for (String symbol : basket) {
                Double currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, currentTime);
                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;
                    double sum24h = 0;
                    int count24h = 0;
                    for (int i = 0; i <= 24; i += 4) {
                        long pastTime = currentTime - (i * 3600 * 1000L);
                        Double past = FundingFeeManager.getInstance().getNearestFundingFee(symbol, pastTime);
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
                features.fundingRateRaw = 0.0;
                features.fundingRateAvg24H = 0.0;
            }
            features.fundingRateTrend = features.fundingRateRaw - features.fundingRateAvg24H;
        } catch (Exception e) {
            features.fundingRateRaw = 0.0;
            features.fundingRateAvg24H = 0.0;
            features.fundingRateTrend = 0.0;
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
        if (Double.isNaN(f.momentum1M)) f.momentum1M = 0.0;
        if (Double.isNaN(f.rsi14)) f.rsi14 = 50.0;
        if (Double.isInfinite(f.advanceDeclineRatio)) f.advanceDeclineRatio = 10.0;
        if (Double.isNaN(f.fundingRateRaw)) f.fundingRateRaw = 0.0;
    }
}