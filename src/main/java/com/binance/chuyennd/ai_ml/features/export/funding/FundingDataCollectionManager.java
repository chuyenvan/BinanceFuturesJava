package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;
import org.jetbrains.annotations.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.*;

public class FundingDataCollectionManager {
    private static final Logger LOG = LoggerFactory.getLogger(FundingDataCollectionManager.class);
    private final String outputDir;
    private final String outputFile; // 1 file DUY NHẤT (append) để tiện đẩy Kaggle
    private final List<String> buffer = new ArrayList<>();
    private int collectedCount = 0;
    private final FundingFeatureExtractorV2 featureExtractor = new FundingFeatureExtractorV2();


    // Counter cho 2 loại label
    private final int[] label6Counts = new int[5];
    private final int[] label40Counts = new int[5];

    public FundingDataCollectionManager(String outputDir) {
        this.outputDir = outputDir;
        this.outputFile = outputDir + "/data_funding_all.csv";
        new File(outputDir).mkdirs();
        writeHeader();
        // Tạo MỚI file data (truncate). headerless (python đọc names=COLUMNS); cột tham chiếu ở header_funding.csv.
        try (BufferedWriter w = new BufferedWriter(new FileWriter(outputFile, false))) {
            // chỉ để truncate/tạo file rỗng
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void writeHeader() {
        String header =
                // Trục thời gian (để split theo thời gian, KHÔNG phải feature)
                "timestamp,symbol," +
                // Context
                "btcMomentum1H,btcMomentum4H,btcMomentum24H,btcDominance,marketBreadthStrength," +
                        // Coin
                        "momentum1M,momentum15M,momentum1H,momentum4H,momentum24H,rsi1H,distFromLow24H,volatilityShock," +
                        // Basket
                        "basketMomentum15M,basketMomentum1H,basketMomentum24H,basketRsi14,basketVolSpike," +
                        // Funding
                        "coinFundingRate,fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                        // LABELS (2 columns)
                        "label6,label40";

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputDir + "/header_funding.csv"))) {
            writer.write(header);
            writer.newLine();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void updateHistory(Map<String, KlineObjectSimple> snapshot) {
        featureExtractor.updateMarketHistory(snapshot);
    }

    public float getReturn(String symbol, int minutes) {
        return featureExtractor.calculateReturn(symbol, minutes);
    }

    public void processSample(long currentTimestamp, OrderTargetInfoTest order,
                              Map<String, KlineObjectSimple> currentSnapshot,
                              TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData,
                              MarketDataObject marketData) {
        try {
            final List<String> basket = HistoryManager.getInstance().findPotentialLosers(currentTimestamp);

            FundingMarketFeatures features = featureExtractor.extractFeatures(
                    currentTimestamp, order, currentSnapshot, marketData, basket);

            if (features != null) {
                features.timestamp = currentTimestamp;
                features.symbol = order.symbol;
                String csvLine = calculateLabelsAndFormat(features, order, futureLookupData);
                if (csvLine != null) {
                    buffer.add(csvLine);
                    collectedCount++;
                }
            }
        } catch (Exception e) {
            LOG.error("Error processing funding sample", e);
        }
    }

    private String calculateLabelsAndFormat(FundingMarketFeatures f, OrderTargetInfoTest order,
                                            TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {
        float entryPrice = order.lastPrice;
        if (entryPrice <= 0) return null;

        // 1. Tính toán Label 6 (Target 6%)
        float targetPrice6 = entryPrice * 1.06f;
        f.label6 = calculateLabelType(order.symbol, targetPrice6, order.timeStart, futureLookupData);
        if (f.label6 >= 0 && f.label6 <= 4) label6Counts[f.label6]++;

        // 2. Tính toán Label 40 (Target 40%)
        float targetPrice40 = entryPrice * 1.40f;
        f.label40 = calculateLabelType(order.symbol, targetPrice40, order.timeStart, futureLookupData);
        if (f.label40 >= 0 && f.label40 <= 4) label40Counts[f.label40]++;

        // 3. Format CSV
        StringBuilder sb = getStringBuilder(f);

        return sb.toString();
    }

    @NotNull
    private static StringBuilder getStringBuilder(FundingMarketFeatures f) {
        StringBuilder sb = new StringBuilder();

        // Trục thời gian + symbol (KHÔNG phải feature train)
        sb.append(f.timestamp).append(",");
        sb.append(f.symbol == null ? "NULL" : f.symbol).append(",");

        // Context
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength));

        // Coin
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.momentum1M, f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock));

        // Basket
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike));

        // Funding
        sb.append(String.format("%.8f,%.8f,%.8f,%.8f,",
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend));

        // Labels
        sb.append(String.format("%d,%d", f.label6, f.label40));
        return sb;
    }

    // Hàm chung để tính loại Label (0-4) dựa trên Target Price
    private int calculateLabelType(String symbol, float targetPrice, long startTime,
                                   TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {
        if (checkProfit(symbol, targetPrice, startTime, 15 * Utils.TIME_MINUTE, futureLookupData)) {
            return 4;
        } else if (checkProfit(symbol, targetPrice, startTime, 4 * Utils.TIME_HOUR, futureLookupData)) {
            return 3;
        } else if (checkProfit(symbol, targetPrice, startTime, 24 * Utils.TIME_HOUR, futureLookupData)) {
            return 2;
        } else if (checkProfit(symbol, targetPrice, startTime, 72 * Utils.TIME_HOUR, futureLookupData)) {
            return 1;
        } else {
            return 0;
        }
    }

    private boolean checkProfit(String symbol, float targetPrice, long startTime, long duration,
                                TreeMap<Long, Map<String, KlineObjectSimple>> futureData) {
        long endTime = startTime + duration;
        Map<Long, Map<String, KlineObjectSimple>> periodData = futureData.subMap(startTime, false, endTime, true);

        for (Map<String, KlineObjectSimple> snapshot : periodData.values()) {
            KlineObjectSimple k = snapshot.get(symbol);
            if (k != null && k.maxPrice >= targetPrice) {
                return true;
            }
        }
        return false;
    }

    public void exportData() {
        if (buffer.isEmpty()) return;
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputFile, true))) {
            for (String line : buffer) {
                writer.write(line);
                writer.newLine();
            }
            buffer.clear();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public int getCollectedCount() {
        return collectedCount;
    }

    public String getLabelReport() {
        return String.format("L6:[%d,%d,%d,%d,F:%d] | L40:[%d,%d,%d,%d,F:%d]",
                label6Counts[4], label6Counts[3], label6Counts[2], label6Counts[1], label6Counts[0],
                label40Counts[4], label40Counts[3], label40Counts[2], label40Counts[1], label40Counts[0]);
    }

    public static class FundingFeatureExtractorV2 {
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
            // FIX: dùng ring O(1) thay getHistory() (đã disable trả rỗng → trước đây LUÔN ra 0).
            return historyManager.getReturn(symbol, minutes);
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
}