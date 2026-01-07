package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.trading.FundingFeeManagerProduction;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public class ComprehensiveMarketFeatureExtractor {
    private static final Logger LOG = LoggerFactory.getLogger(ComprehensiveMarketFeatureExtractor.class);

    private final Map<String, Deque<KlineObjectSimple>> symbolHistoryMap;
    private final int maxHistorySize = 1500;

    public ComprehensiveMarketFeatureExtractor() {
        this.symbolHistoryMap = new ConcurrentHashMap<>();
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

    // 🔥 METHOD MỚI: Tự động tìm Basket dựa trên History (Thay thế findPotentialLosersRelaxed bên ngoài)
    public List<String> findPotentialLosers(long currentTimestamp) {
        List<Map.Entry<String, Double>> drops = new ArrayList<>();
        long startTime = currentTimestamp - (15 * 60 * 1000L); // 15 phút trước

        for (Map.Entry<String, Deque<KlineObjectSimple>> entry : symbolHistoryMap.entrySet()) {
            String symbol = entry.getKey();
            Deque<KlineObjectSimple> history = entry.getValue();
            if (history.isEmpty()) continue;

            KlineObjectSimple currentKline = history.getLast();

            // 1. Lọc Volume rác (< 50k USDT)
            if (currentKline.totalUsdt < 50000) continue;

            // 2. Tìm đỉnh giá trong 15 phút gần nhất từ History
            double maxPrice15m = -1.0;

            // Duyệt ngược từ cuối lên để tối ưu tốc độ
            Iterator<KlineObjectSimple> it = history.descendingIterator();
            while (it.hasNext()) {
                KlineObjectSimple k = it.next();
                if (k.startTime < startTime) break; // Đã quá 15p thì dừng
                if (k.maxPrice > maxPrice15m) {
                    maxPrice15m = k.maxPrice;
                }
            }

            // 3. Tính độ sụt giảm
            if (maxPrice15m > 0) {
                double currentPrice = currentKline.priceClose;
                double dropFromPeak = (currentPrice - maxPrice15m) / maxPrice15m;

                // Giảm > 0.1% là lấy (Logic Relaxed)
                if (dropFromPeak < -0.001) {
                    drops.add(new AbstractMap.SimpleEntry<>(symbol, dropFromPeak));
                }
            }
        }

        // Sort giảm dần theo mức giảm (giảm nhiều nhất lên đầu)
        drops.sort(Map.Entry.comparingByValue());

        // Lấy Top 60
        return drops.stream()
                .limit(60)
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }

    // Cập nhật History - Public để Manager có thể gọi trước khi tìm Basket
    public void updateMarketHistory(Map<String, KlineObjectSimple> currentMarketData) {
        for (Map.Entry<String, KlineObjectSimple> entry : currentMarketData.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();
            if (kline != null) {
                Deque<KlineObjectSimple> history = symbolHistoryMap.computeIfAbsent(symbol, k -> new ArrayDeque<>());

                // Chống duplicate: Nếu kline cuối cùng cùng timestamp thì update thay vì add mới
                if (!history.isEmpty() && history.getLast().startTime.equals(kline.startTime)) {
                    history.removeLast();
                }

                history.addLast(kline);
                if (history.size() > maxHistorySize) history.removeFirst();
            }
        }
    }

    public MarketFeatures extractAllFeatures(long timestamp,
                                             Map<String, KlineObjectSimple> currentMarketData,
                                             MarketRateChange marketRateChange,
                                             List<String> targetBasket) { // targetBasket có thể null

        // 1. Cập nhật dữ liệu mới nhất vào History trước
        updateMarketHistory(currentMarketData);

        // 2. Nếu không truyền Basket -> Tự động tính toán từ History
        if (targetBasket == null || targetBasket.isEmpty()) {
            targetBasket = findPotentialLosers(timestamp);
        }

        MarketFeatures features = new MarketFeatures();
        features.timestamp = timestamp;
        features.dateKey = Utils.normalizeDateYYYYMMDD(timestamp);

        String anchorSymbol = "BTCUSDT";

        extractMomentumFeatures(features, anchorSymbol, marketRateChange);
        extractVolatilityFeatures(features, anchorSymbol);
        extractTechnicalIndicators(features, anchorSymbol);
        extractBreadthFeatures(features, currentMarketData);

        // Sử dụng targetBasket đã có (hoặc vừa tìm được)
        extractBasketFundingFeatures(features, targetBasket, timestamp);
        extractBasketTechnicalFeatures(features, targetBasket);

        extractTimeFeatures(features, timestamp);
        validateAndCleanFeatures(features);

        return features;
    }

    // ... (Giữ nguyên các hàm extractFeatures private khác bên dưới: Production, Momentum, Technical, Breadth...)

    // Giữ nguyên logic extractBasketFundingFeatures, extractBasketTechnicalFeatures, v.v.
    // ...
    // ...
    // (Phần code cũ không thay đổi, chỉ paste lại phần method private nếu cần thiết,
    // nhưng quan trọng nhất là 3 method public ở trên)

    // --- COPY LẠI CÁC PRIVATE METHODS CŨ ---
    public MarketFeatures extractAllFeaturesProduction(long timestamp,
                                                       Map<String, KlineObjectSimple> currentMarketData,
                                                       MarketRateChange marketRateChange,
                                                       List<String> targetBasket) {
        // Production logic tương tự
        updateMarketHistory(currentMarketData);
        if (targetBasket == null || targetBasket.isEmpty()) {
            targetBasket = findPotentialLosers(timestamp);
        }

        MarketFeatures features = new MarketFeatures();
        features.timestamp = timestamp;
        features.dateKey = Utils.normalizeDateYYYYMMDD(timestamp); // Fix try-catch inside

        String anchorSymbol = "BTCUSDT";
        extractMomentumFeatures(features, anchorSymbol, marketRateChange);
        extractVolatilityFeatures(features, anchorSymbol);
        extractTechnicalIndicators(features, anchorSymbol);
        extractBreadthFeatures(features, currentMarketData);
        extractBasketFundingFeaturesProduction(features, targetBasket, timestamp);
        extractBasketTechnicalFeatures(features, targetBasket);
        extractTimeFeatures(features, timestamp);
        validateAndCleanFeatures(features);
        return features;
    }

    // ... (Các hàm private cũ giữ nguyên) ...
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

    private void extractBasketFundingFeaturesProduction(MarketFeatures features, List<String> basket, long currentTime) {
        try {
            if (basket == null || basket.isEmpty()) basket = Collections.singletonList("BTCUSDT");
            double totalCurrentFunding = 0;
            double totalAvg24H = 0;
            int validCount = 0;
            for (String symbol : basket) {
                Double currentFunding = FundingFeeManagerProduction.getInstance().getNearestFundingFee(symbol, currentTime);
                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;
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
            Deque<KlineObjectSimple> history = symbolHistoryMap.get(symbol);
            if (history != null && history.size() >= 25) {
                List<KlineObjectSimple> list = new ArrayList<>(history);
                KlineObjectSimple current = list.get(list.size() - 1);
                sumRsi += calculateRSI(list, 14);
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);
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
            features.basketRsi14 = features.rsi14;
            features.basketMomentum15M = features.momentum15M;
            features.basketMomentum1H = features.momentum1H;
            features.basketVolSpike = features.volumeSpike;
        }
    }

    // Copy Private helpers: calculateRSI, calculateReturn, calculateVolatility, etc.
    private void extractMomentumFeatures(MarketFeatures features, String symbol, MarketRateChange rate) {
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

    private void extractBreadthFeatures(MarketFeatures features, Map<String, KlineObjectSimple> marketData) {
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