package com.binance.chuyennd.ai_ml.onnx;


import com.binance.chuyennd.aerospike.DataManagerAerospike;
import com.binance.chuyennd.ai_ml.deepseek.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.deepseek.MarketFeatures;
import com.binance.chuyennd.ai_ml.deepseek.OnnxInferenceManager;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class RunGeneratePredictions {
    private static final Logger LOG = LoggerFactory.getLogger(RunGeneratePredictions.class);

    // File lưu kết quả dự báo (để Backtest dùng lại)


    // Thư mục chứa Model ONNX
    private static final String MODEL_DIR = "../storage/ai_ml_data/ai_models_reg";

    public static void main(String[] args) {
        try {
            FundingFeeManager.getInstance(); // Init Funding
            new RunGeneratePredictions().generateAndSave();
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void generateAndSave() throws Exception {
        // 1. Khởi tạo AI Brain & Feature Extractor
        OnnxInferenceManager aiBrain = new OnnxInferenceManager(MODEL_DIR);
        ComprehensiveMarketFeatureExtractor featureExtractor = new ComprehensiveMarketFeatureExtractor();

        // 2. Load Market Rate Data
        LOG.info("Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        // 3. Map chứa kết quả (Sẽ lưu xuống file)
        // Dùng TreeMap để đảm bảo thứ tự thời gian
        TreeMap<Long, AiPredictionData> predictionMap = new TreeMap<>();

        // 4. Cấu hình thời gian chạy (Từ 2021 đến nay)
        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("🚀 STARTING PREDICTION GENERATION...");

        int processedDays = 0;

        // --- VÒNG LẶP CHÍNH ---
        while (currentTime <= endTime) {
            try {
                // Load data hôm nay và ngày mai (để làm lookup)
                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospike.readDataFromAerospike1M(currentTime);
                TreeMap<Long, Map<String, KlineObjectSimple>> tomorrowData =
                        DataManagerAerospike.readDataFromAerospike1M(currentTime + Utils.TIME_DAY);

                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (todayData != null) lookupData.putAll(todayData);
                if (tomorrowData != null) lookupData.putAll(tomorrowData);

                if (todayData != null && !todayData.isEmpty()) {
                    // DUYỆT TỪNG PHÚT TRONG NGÀY
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
                        Long timestamp = entry.getKey();
                        Map<String, KlineObjectSimple> marketData = entry.getValue();
                        MarketRateChange rateChange = time2Rate.get(timestamp);

                        // 1. Xác định Rổ Coin (Basket) tại thời điểm đó
                        // Dùng logic Top Losers giống hệt lúc train
                        List<String> targetBasket = findTop50LosersFromPeak15m(lookupData, timestamp);

                        // Chỉ dự đoán nếu có rổ coin hợp lệ (> 3 coin)
                        // Nếu không có basket, coi như thị trường sideway, không cần dự báo
                        if (targetBasket.size() >= 3) {

                            // 2. Trích xuất Features
                            MarketFeatures features = featureExtractor.extractAllFeatures(
                                    timestamp, marketData, rateChange, targetBasket);

                            // 3. Gọi AI Dự báo
                            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

                            // 4. Lưu kết quả
                            AiPredictionData data = new AiPredictionData(
                                    timestamp,
                                    res.return15M, res.return1H, res.return4H, res.return24H,
                                    res.riskDrawdown4H, res.riskDrawdown24H
                            );
                            predictionMap.put(timestamp, data);
                        }
                    }
                }

                processedDays++;
                if (processedDays % 10 == 0) {
                    LOG.info("✅ Processed {} days. Total Predictions: {}", processedDays, predictionMap.size());
                    // Lưu tạm để backup (Optional)
                }

            } catch (Exception e) {
                LOG.warn("Error day {}: {}", Utils.normalizeDateYYYYMMDD(currentTime), e.getMessage());
            }

            currentTime += Utils.TIME_DAY;
        }

        // 5. Lưu file cuối cùng
        LOG.info("💾 Saving {} predictions to file: {}", predictionMap.size(), Configs.FILE_AI_PREDICTIONS);
        StorageSnappy.writeObject2File(Configs.FILE_AI_PREDICTIONS, predictionMap);

        aiBrain.close();
        LOG.info("🎉 DONE!");
    }

    // --- LOGIC TÌM BASKET (Copy y hệt từ RunFullDataCollection để nhất quán) ---
    private List<String> findTop50LosersFromPeak15m(TreeMap<Long, Map<String, KlineObjectSimple>> dailyData, Long currentTimestamp) {
        Long startTime = currentTimestamp - (15 * 60 * 1000L);
        Map<Long, Map<String, KlineObjectSimple>> recentData = dailyData.subMap(startTime, true, currentTimestamp, true);
        if (recentData.isEmpty()) return new ArrayList<>();

        Map<String, KlineObjectSimple> currentPrices = dailyData.get(currentTimestamp);
        Map<String, Double> maxPrices15m = new HashMap<>();

        for (Map<String, KlineObjectSimple> minuteData : recentData.values()) {
            for (Map.Entry<String, KlineObjectSimple> entry : minuteData.entrySet()) {
                String symbol = entry.getKey();
                double high = entry.getValue().maxPrice;
                if (!maxPrices15m.containsKey(symbol) || high > maxPrices15m.get(symbol)) {
                    maxPrices15m.put(symbol, high);
                }
            }
        }

        List<Map.Entry<String, Double>> drops = new ArrayList<>();
        for (String symbol : currentPrices.keySet()) {
            KlineObjectSimple currentKline = currentPrices.get(symbol);
            if (currentKline.totalUsdt < 5000) continue;

            if (maxPrices15m.containsKey(symbol)) {
                double peakPrice = maxPrices15m.get(symbol);
                double currentPrice = currentKline.priceClose;
                if (peakPrice > 0) {
                    double dropFromPeak = (currentPrice - peakPrice) / peakPrice;
                    // Logic Relaxed: Giảm > 0.1% là lấy
                    if (dropFromPeak < -0.001) {
                        drops.add(new AbstractMap.SimpleEntry<>(symbol, dropFromPeak));
                    }
                }
            }
        }
        drops.sort(Map.Entry.comparingByValue());
        List<String> result = new ArrayList<>();
        int limit = Math.min(drops.size(), 60);
        for (int i = 0; i < limit; i++) result.add(drops.get(i).getKey());
        return result;
    }

    private TreeMap<Long, MarketRateChange> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) return new TreeMap<>();
        return (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
    }
}