package com.binance.chuyennd.ai_ml.deepseek;

//import com.binance.chuyennd.research.FundingFeeManager;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.trading.FundingFeeManagerProduction;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class ComprehensiveMarketFeatureExtractor {
    private static final Logger LOG = LoggerFactory.getLogger(ComprehensiveMarketFeatureExtractor.class);

    private final Map<String, Deque<KlineObjectSimple>> symbolHistoryMap;
    private final int maxHistorySize = 1500;

    public ComprehensiveMarketFeatureExtractor() {
        this.symbolHistoryMap = new ConcurrentHashMap<>();
//        try {
//            FundingFeeManager.getInstance();
//        } catch (Exception e) {
//            LOG.error("Funding init failed", e);
//        }
    }

    // --- NEW METHOD: Khởi tạo dữ liệu từ ListenAllTicker ---
    public void initDataFromTickerMap(ConcurrentHashMap<String, TreeMap<Long, KlineObjectSimple>> allTickers) {
        LOG.info("AI Feature Extractor: Syncing history from ListenAllTicker (TreeMap source)...");
        int count = 0;

        for (Map.Entry<String, TreeMap<Long, KlineObjectSimple>> entry : allTickers.entrySet()) {
            String symbol = entry.getKey();
            TreeMap<Long, KlineObjectSimple> timeMap = entry.getValue();

            if (timeMap == null || timeMap.isEmpty()) continue;

            Deque<KlineObjectSimple> history = new ArrayDeque<>();

            // TreeMap.values() trả về Collection đã sắp xếp theo Key (Time) tăng dần -> Đảm bảo đúng thứ tự
            Collection<KlineObjectSimple> sortedKlines = timeMap.values();

            // Tính toán số lượng cần bỏ qua để chỉ lấy maxHistorySize phần tử cuối cùng
            int totalSize = sortedKlines.size();
            int skipCount = Math.max(0, totalSize - maxHistorySize);

            int currentIndex = 0;
            for (KlineObjectSimple kline : sortedKlines) {
                if (currentIndex >= skipCount) {
                    history.addLast(kline);
                }
                currentIndex++;
            }

            symbolHistoryMap.put(symbol, history);
            count++;
        }
        LOG.info("AI Feature Extractor: Synced history for {} symbols.", count);
    }

    public MarketFeatures extractAllFeatures(long timestamp,
                                             Map<String, KlineObjectSimple> currentMarketData,
                                             MarketRateChange marketRateChange,
                                             List<String> targetBasket) {

        MarketFeatures features = new MarketFeatures();
        features.timestamp = timestamp;
        features.dateKey = getDateString(timestamp);

        updateMarketHistory(currentMarketData);

        String anchorSymbol = "BTCUSDT";

        // 1. BTC Features (Vĩ mô)
        extractMomentumFeatures(features, anchorSymbol, marketRateChange);
        extractVolatilityFeatures(features, anchorSymbol);
        extractTechnicalIndicators(features, anchorSymbol);

        // 2. Market Wide Features
        extractBreadthFeatures(features, currentMarketData);

        // 3. 🔥 BASKET Features (Vi mô - Quan trọng cho bắt đáy)
        extractBasketFundingFeatures(features, targetBasket, timestamp);
        extractBasketTechnicalFeatures(features, targetBasket); // <--- MỚI

        // 4. Time & Validate
        extractTimeFeatures(features, timestamp);
        validateAndCleanFeatures(features);

        return features;
    }

    public MarketFeatures extractAllFeaturesProduction(long timestamp,
                                                       Map<String, KlineObjectSimple> currentMarketData,
                                                       MarketRateChange marketRateChange,
                                                       List<String> targetBasket) {

        MarketFeatures features = new MarketFeatures();
        features.timestamp = timestamp;
        features.dateKey = getDateString(timestamp);

        updateMarketHistory(currentMarketData);

        String anchorSymbol = "BTCUSDT";

        // 1. BTC Features (Vĩ mô)
        extractMomentumFeatures(features, anchorSymbol, marketRateChange);
        extractVolatilityFeatures(features, anchorSymbol);
        extractTechnicalIndicators(features, anchorSymbol);

        // 2. Market Wide Features
        extractBreadthFeatures(features, currentMarketData);

        // 3. 🔥 BASKET Features (Vi mô - Quan trọng cho bắt đáy)
        extractBasketFundingFeaturesProduction(features, targetBasket, timestamp);
        extractBasketTechnicalFeatures(features, targetBasket); // <--- MỚI

        // 4. Time & Validate
        extractTimeFeatures(features, timestamp);
        validateAndCleanFeatures(features);

        return features;
    }

    private void extractBasketFundingFeatures(MarketFeatures features, List<String> basket, long currentTime) {
        try {
            if (basket == null || basket.isEmpty()) {
                // Fallback về BTC nếu không có basket
                basket = Collections.singletonList("BTCUSDT");
            }

            double totalCurrentFunding = 0;
            double totalAvg24H = 0;
            int validCount = 0;

            // Duyệt qua từng coin trong rổ để lấy Funding
            for (String symbol : basket) {
                Double currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, currentTime);

                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;

                    // Tính TB 24h cho coin này
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
                // Lấy trung bình cộng của cả rổ
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

    // 🔥 HÀM MỚI: Tính Funding Fee trung bình của cả Basket
    private void extractBasketFundingFeaturesProduction(MarketFeatures features, List<String> basket, long currentTime) {
        try {
            if (basket == null || basket.isEmpty()) {
                // Fallback về BTC nếu không có basket
                basket = Collections.singletonList("BTCUSDT");
            }

            double totalCurrentFunding = 0;
            double totalAvg24H = 0;
            int validCount = 0;

            // Duyệt qua từng coin trong rổ để lấy Funding
            for (String symbol : basket) {
                Double currentFunding = FundingFeeManagerProduction.getInstance().getNearestFundingFee(symbol, currentTime);

                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;

                    // Tính TB 24h cho coin này
                    double sum24h = 0;
                    int count24h = 0;
                    for (int i = 0; i <= 24; i += 4) {
                        long pastTime = currentTime - (i * 3600 * 1000L);
                        Double past = FundingFeeManagerProduction.getInstance().getNearestFundingFee(symbol, pastTime);
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
                // Lấy trung bình cộng của cả rổ
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

//    private void extractBasketFundingFeatures(MarketFeatures features, List<String> basket, long currentTime) {
//        try {
//            if (basket == null || basket.isEmpty()) {
//                // Fallback về BTC nếu không có basket
//                basket = Collections.singletonList("BTCUSDT");
//            }
//
//            double totalCurrentFunding = 0;
//            double totalAvg24H = 0;
//            int validCount = 0;
//
//            // Duyệt qua từng coin trong rổ để lấy Funding
//            for (String symbol : basket) {
//                Double currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, currentTime);
//
//                if (currentFunding != null) {
//                    totalCurrentFunding += currentFunding;
//
//                    // Tính TB 24h cho coin này
//                    double sum24h = 0;
//                    int count24h = 0;
//                    for (int i = 0; i <= 24; i += 4) {
//                        long pastTime = currentTime - (i * 3600 * 1000L);
//                        Double past = FundingFeeManager.getInstance().getNearestFundingFee(symbol, pastTime);
//                        if (past != null) {
//                            sum24h += past;
//                            count24h++;
//                        }
//                    }
//                    if (count24h > 0) totalAvg24H += (sum24h / count24h);
//                    else totalAvg24H += currentFunding;
//
//                    validCount++;
//                }
//            }
//
//            if (validCount > 0) {
//                // Lấy trung bình cộng của cả rổ
//                features.fundingRateRaw = totalCurrentFunding / validCount;
//                features.fundingRateAvg24H = totalAvg24H / validCount;
//            } else {
//                features.fundingRateRaw = 0.0;
//                features.fundingRateAvg24H = 0.0;
//            }
//
//            features.fundingRateTrend = features.fundingRateRaw - features.fundingRateAvg24H;
//
//        } catch (Exception e) {
//            features.fundingRateRaw = 0.0;
//            features.fundingRateAvg24H = 0.0;
//            features.fundingRateTrend = 0.0;
//        }
//    }

    // 🔥 HÀM MỚI: Tính RSI/Momentum trung bình của Basket
    private void extractBasketTechnicalFeatures(MarketFeatures features, List<String> basket) {
        if (basket == null || basket.isEmpty()) {
            // Fallback: Lấy giống BTC nếu không có basket
            features.basketRsi14 = features.rsi14;
            features.basketMomentum15M = features.momentum15M;
            features.basketMomentum1H = features.momentum1H;
            features.basketVolSpike = features.volumeSpike;
            return;
        }

        double sumRsi = 0, sumMom15m = 0, sumMom1h = 0, sumVolSpike = 0;
        int count = 0;

        for (String symbol : basket) {
            Deque<KlineObjectSimple> history = symbolHistoryMap.get(symbol);
            if (history != null && history.size() >= 25) {
                List<KlineObjectSimple> list = new ArrayList<>(history);
                KlineObjectSimple current = list.get(list.size() - 1);

                // RSI
                sumRsi += calculateRSI(list, 14);

                // Momentum
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);

                // Vol Spike
                double avgVol = 0;
                int n = 0;
                for (int i = list.size() - 2; i >= Math.max(0, list.size() - 22); i--) {
                    avgVol += list.get(i).totalUsdt;
                    n++;
                }
                if (n > 0 && avgVol > 0) sumVolSpike += current.totalUsdt / (avgVol / n);
                else sumVolSpike += 1.0;

                count++;
            }
        }

        if (count > 0) {
            features.basketRsi14 = sumRsi / count;
            features.basketMomentum15M = sumMom15m / count;
            features.basketMomentum1H = sumMom1h / count;
            features.basketVolSpike = sumVolSpike / count;
        } else {
            // 🔥 FALLBACK: Lấy của BTC nếu Basket rỗng/thiếu data
            features.basketRsi14 = features.rsi14;
            features.basketMomentum15M = features.momentum15M;
            features.basketMomentum1H = features.momentum1H;
            features.basketVolSpike = features.volumeSpike;
        }
    }

    private void updateMarketHistory(Map<String, KlineObjectSimple> currentMarketData) {
        for (Map.Entry<String, KlineObjectSimple> entry : currentMarketData.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();
            if (kline != null) {
                Deque<KlineObjectSimple> history = symbolHistoryMap.computeIfAbsent(symbol, k -> new ArrayDeque<>());
                history.addLast(kline);
                if (history.size() > maxHistorySize) history.removeFirst();
            }
        }
    }

    private void extractMomentumFeatures(MarketFeatures features, String symbol, MarketRateChange rate) {
        // Copy code cũ...
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
        features.volatility1M = calculateVolatility(symbol, 2);
        features.volatility15M = calculateVolatility(symbol, 15);
        features.volatility1H = calculateVolatility(symbol, 60);
        features.volatility24H = calculateVolatility(symbol, 1440);

        if (features.volatility24H != 0) {
            features.volatilityTermStructure = features.volatility1H / features.volatility24H;
        }

        // 🔥 ĐÃ XÓA: var95_1H và expectedShortfall1H
        // Vì nó chỉ là volatility1H * hằng số -> Không có giá trị cho AI

        if (features.volatility1H > 0.01) features.volatilityRegime = "HIGH";
        else if (features.volatility1H < 0.002) features.volatilityRegime = "LOW";
        else features.volatilityRegime = "NORMAL";
    }

    private void extractBreadthFeatures(MarketFeatures features, Map<String, KlineObjectSimple> marketData) {
        // Copy code cũ...
        int upCount = 0, downCount = 0;
        double upVol = 0, downVol = 0;
        int totalValid = 0, aboveMA20Count = 0;
        for (Map.Entry<String, KlineObjectSimple> entry : marketData.entrySet()) {
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
            if (isAboveMA(entry.getKey(), 20, k.priceClose)) aboveMA20Count++;
        }
        features.advanceDeclineRatio = (downCount > 0) ? (double) upCount / downCount : 10.0;
        features.volumeRatioUpDown = (downVol > 0) ? upVol / downVol : 10.0;
        features.marketBreadthStrength = (totalValid > 0) ? (double) upCount / totalValid : 0.5;
        features.percentAboveMA20 = (totalValid > 0) ? (double) aboveMA20Count / totalValid : 0.5;
        double btcVol = marketData.containsKey("BTCUSDT") ? marketData.get("BTCUSDT").totalUsdt : 0;
        features.btcDominance = (upVol + downVol > 0) ? btcVol / (upVol + downVol) : 0.0;
    }

    private void extractTechnicalIndicators(MarketFeatures features, String symbol) {
        // Copy code cũ...
        Deque<KlineObjectSimple> history = symbolHistoryMap.get(symbol);
        if (history == null || history.size() < 25) {
            features.rsi14 = 50.0;
            features.volumeSpike = 1.0;
            features.distMA20 = 0.0;
            return;
        }
        List<KlineObjectSimple> list = new ArrayList<>(history);
        KlineObjectSimple current = list.get(list.size() - 1);
        features.rsi14 = calculateRSI(list, 14);
        double avgVol = 0;
        int count = 0;
        for (int i = list.size() - 2; i >= Math.max(0, list.size() - 22); i--) {
            avgVol += list.get(i).totalUsdt;
            count++;
        }
        features.volumeSpike = (count > 0 && avgVol > 0) ? current.totalUsdt / (avgVol / count) : 1.0;
        double ma20 = 0;
        count = 0;
        for (int i = list.size() - 1; i >= Math.max(0, list.size() - 20); i--) {
            ma20 += list.get(i).priceClose;
            count++;
        }
        features.distMA20 = (count > 0 && ma20 > 0) ? (current.priceClose - ma20 / count) / (ma20 / count) : 0.0;
    }

    private double calculateRSI(List<KlineObjectSimple> data, int period) {
        if (data.size() <= period) return 50.0;
        double sumGain = 0, sumLoss = 0;
        for (int i = data.size() - period; i < data.size(); i++) {
            double change = data.get(i).priceClose - data.get(i - 1).priceClose;
            if (change > 0) sumGain += change;
            else sumLoss -= change;
        }
        if (sumLoss == 0) return 100.0;
        return 100.0 - (100.0 / (1.0 + (sumGain / sumLoss)));
    }

    private double calculateReturn(String symbol, int periods) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.size() <= periods) return 0.0;
        List<KlineObjectSimple> l = new ArrayList<>(h);
        double cur = l.get(l.size() - 1).priceClose;
        double past = l.get(Math.max(0, l.size() - 1 - periods)).priceClose;
        return (past > 0) ? (cur - past) / past : 0.0;
    }

    private double calculateVolatility(String symbol, int periods) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.size() < 5) return 0.0;
        List<KlineObjectSimple> l = new ArrayList<>(h);
        int start = Math.max(0, l.size() - periods);
        double sum = 0, sumSq = 0;
        int count = 0;
        for (int i = start; i < l.size() - 1; i++) {
            double r = (l.get(i + 1).priceClose - l.get(i).priceClose) / l.get(i).priceClose;
            sum += r;
            sumSq += r * r;
            count++;
        }
        return (count < 2) ? 0.0 : Math.sqrt(Math.max(0, (sumSq - (sum * sum) / count) / (count - 1)));
    }

    private boolean isAboveMA(String symbol, int period, double price) {
        Deque<KlineObjectSimple> h = symbolHistoryMap.get(symbol);
        if (h == null || h.size() < period) return false;
        double sum = 0;
        int count = 0;
        Iterator<KlineObjectSimple> it = h.descendingIterator();
        while (it.hasNext() && count < period) {
            sum += it.next().priceClose;
            count++;
        }
        return price > (sum / count);
    }

//    private void extractFundingFeatures(MarketFeatures features, String symbol, long currentTime) {
//        try {
//            Double currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, currentTime);
//            features.fundingRateRaw = (currentFunding != null) ? currentFunding : 0.0;
//            double sumFunding = 0;
//            int count = 0;
//            for (int i = 0; i <= 24; i += 4) {
//                long pastTime = currentTime - (i * 3600 * 1000L);
//                Double pastFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, pastTime);
//                if (pastFunding != null) {
//                    sumFunding += pastFunding;
//                    count++;
//                }
//            }
//            features.fundingRateAvg24H = (count > 0) ? sumFunding / count : features.fundingRateRaw;
//            features.fundingRateTrend = features.fundingRateRaw - features.fundingRateAvg24H;
//        } catch (Exception e) {
//            features.fundingRateRaw = 0.0;
//            features.fundingRateAvg24H = 0.0;
//            features.fundingRateTrend = 0.0;
//        }
//    }

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

    private String getDateString(long timestamp) {
        try {
            return Utils.normalizeDateYYYYMMDD(timestamp);
        } catch (Exception e) {
            return String.valueOf(timestamp);
        }
    }
}