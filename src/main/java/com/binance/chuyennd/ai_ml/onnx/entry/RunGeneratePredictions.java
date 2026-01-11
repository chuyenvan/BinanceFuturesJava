package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
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

public class RunGeneratePredictions {
    private static final Logger LOG = LoggerFactory.getLogger(RunGeneratePredictions.class);
    private static final String MODEL_DIR = "../storage/ai_ml_data/ai_models_reg_v4";

    public static void main(String[] args) {
        try {
            System.setProperty("ai.onnxruntime.disable_telemetry", "true");
            FundingFeeManager.getInstance();
            new RunGeneratePredictions().generateAndSave();
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void generateAndSave() throws Exception {
        OnnxInferenceManager aiBrain = new OnnxInferenceManager(MODEL_DIR);
        ComprehensiveMarketFeatureExtractor featureExtractor = new ComprehensiveMarketFeatureExtractor();

        LOG.info("Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        TreeMap<Long, AiPredictionData> predictionMap = new TreeMap<>();

        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("🚀 STARTING PREDICTION GENERATION (YEARLY SAVE MODE)...");

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(currentTime);
        int currentYearProcessing = cal.get(Calendar.YEAR);

        int processedDays = 0;

        while (currentTime <= endTime) {
            try {
                cal.setTimeInMillis(currentTime);
                int yearOfToday = cal.get(Calendar.YEAR);

                // --- 🆕 ĐOẠN CODE MỚI THÊM: CHECK FILE EXISTING ---
                // Kiểm tra nếu file của năm nay đã có trên ổ cứng thì bỏ qua cả năm luôn
                String expectedFileName = Configs.FILE_AI_ENTRY_PREDICTIONS + "_" + yearOfToday;
                if (new File(expectedFileName).exists()) {
                    LOG.info("⏩ File data năm {} đã tồn tại ({}). Skip qua năm tiếp theo...", yearOfToday, expectedFileName);

                    // Nhảy thời gian sang ngày 1 tháng 1 năm sau
                    cal.set(Calendar.YEAR, yearOfToday + 1);
                    cal.set(Calendar.DAY_OF_YEAR, 1);
                    cal.set(Calendar.HOUR_OF_DAY, 0);
                    cal.set(Calendar.MINUTE, 0);
                    cal.set(Calendar.SECOND, 0);
                    cal.set(Calendar.MILLISECOND, 0);

                    currentTime = cal.getTimeInMillis();

                    // Cập nhật biến theo dõi năm để logic phía dưới không bị loạn khi bắt đầu năm mới
                    currentYearProcessing = yearOfToday + 1;
                    continue;
                }
                // --------------------------------------------------

                // 1. Kiểm tra chuyển giao năm (Năm cũ qua năm mới)
                if (yearOfToday > currentYearProcessing) {
                    saveAndClear(currentYearProcessing, predictionMap);
                    currentYearProcessing = yearOfToday;
                }

                // 2. Load Data
                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);

                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = todayData;

                if (todayData != null && !todayData.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
                        Long timestamp = entry.getKey();
                        Map<String, KlineObjectSimple> marketData = entry.getValue();
                        MarketRateChange rateChange = time2Rate.get(timestamp);

                        List<String> targetBasket = findTop50LosersFromPeak15m(lookupData, timestamp);

                        if (targetBasket.size() >= 3) {
                            MarketFeatures features = featureExtractor.extractAllFeatures(
                                    timestamp, marketData, rateChange, targetBasket);

                            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

                            predictionMap.put(timestamp, new AiPredictionData(
                                    timestamp,
                                    res.return15M, res.return1H, res.return4H, res.return24H,
                                    res.riskDrawdown4H, res.riskDrawdown24H
                            ));
                        }
                    }
                }

                todayData = null; // Help GC
                lookupData = null;

                processedDays++;
                if (processedDays % 20 == 0) {
                    LOG.info("... Day {}: Processed. Current Year Map Size: {}",
                            Utils.normalizeDateYYYYMMDD(currentTime), predictionMap.size());
                }

            } catch (Exception e) {
                LOG.error("Error day " + currentTime, e);
            }

            currentTime += Utils.TIME_DAY;
        }

        // Lưu nốt phần còn lại (năm cuối cùng chưa hết hoặc năm hiện tại)
        if (!predictionMap.isEmpty()) {
            saveAndClear(currentYearProcessing, predictionMap);
        }

        aiBrain.close();
        LOG.info("🎉 DONE ALL!");
    }

    private void saveAndClear(int year, TreeMap<Long, AiPredictionData> map) {
        if (map.isEmpty()) return;

        String fileName = Configs.FILE_AI_ENTRY_PREDICTIONS + "_" + year;
        LOG.info("💾 >>> END OF YEAR {}. Saving {} records to: {}", year, map.size(), fileName);

        StorageSnappy.writeObject2File(fileName, map);
        map.clear();
        System.gc();
        LOG.info("🧹 RAM Cleared. Ready for Year {}", year + 1);
    }

    // ... (Giữ nguyên các hàm findTop50Losers và loadMarketRateData như cũ)
    private List<String> findTop50LosersFromPeak15m(TreeMap<Long, Map<String, KlineObjectSimple>> dailyData, Long currentTimestamp) {
        Long startTime = currentTimestamp - (15 * 60 * 1000L);
        NavigableMap<Long, Map<String, KlineObjectSimple>> recentData = dailyData.subMap(startTime, true, currentTimestamp, true);
        if (recentData.isEmpty()) return new ArrayList<>();

        Map<String, KlineObjectSimple> currentPrices = dailyData.get(currentTimestamp);
        Map<String, Double> maxPrices15m = new HashMap<>();

        for (Map<String, KlineObjectSimple> minuteData : recentData.values()) {
            for (Map.Entry<String, KlineObjectSimple> entry : minuteData.entrySet()) {
                String symbol = entry.getKey();
                double high = entry.getValue().maxPrice;
                maxPrices15m.merge(symbol, high, Math::max);
            }
        }

        List<Map.Entry<String, Double>> drops = new ArrayList<>();
        for (Map.Entry<String, KlineObjectSimple> entry : currentPrices.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();
            if (kline.totalUsdt < 5000) continue;

            Double peakPrice = maxPrices15m.get(symbol);
            if (peakPrice != null && peakPrice > 0) {
                double drop = (kline.priceClose - peakPrice) / peakPrice;
                if (drop < -0.001) {
                    drops.add(new AbstractMap.SimpleEntry<>(symbol, drop));
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