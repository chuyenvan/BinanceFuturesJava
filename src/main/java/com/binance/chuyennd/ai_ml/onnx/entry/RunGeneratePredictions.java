package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
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
    private static final String MODEL_DIR = "../storage/ai_ml_data/ai_models_reg_v3"; // Sửa lại đường dẫn model nếu cần

    public static void main(String[] args) {
        try {
            System.setProperty("ai.onnxruntime.disable_telemetry", "true");
            System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
            DataManagerAerospikeFloatSim.setThreadCount(4);

            FundingFeeManager.getInstance();
            // Truyền null để chạy từ đầu nếu chạy file này độc lập
            new RunGeneratePredictions().generateAndSave(null);
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    // Thêm tham số lastTimestamp
    public void generateAndSave(Long lastTimestamp) throws Exception {
        OnnxInferenceManager aiBrain = new OnnxInferenceManager(MODEL_DIR);
        ComprehensiveMarketFeatureExtractor featureExtractor = new ComprehensiveMarketFeatureExtractor();

        LOG.info("📥 Loading Market Rates từ Aerospike...");
        TreeMap<Long, MarketDataObject> time2Rate = loadMarketRateData();

        long currentTime;
        if (lastTimestamp != null && lastTimestamp > 0) {
            // Lùi về 00:00:00 của ngày chứa bản ghi cuối cùng để quét cho chắc chắn
            currentTime = Utils.getDate(lastTimestamp);
            LOG.info("🔄 Resuming Market AI Predictions từ ngày: {}", Utils.normalizeDateYYYYMMDDHHmm(currentTime));
        } else {
            currentTime = Utils.sdfFile.parse("20210101").getTime();
            LOG.info("🚀 STARTING MARKET AI PREDICTION GENERATION FROM SCRATCH...");
        }

        long endTime = System.currentTimeMillis();
        int processedDays = 0;

        while (currentTime <= endTime) {
            try {
                // 1. Tạo danh sách các phút trong ngày để kiểm tra Aerospike
                List<Long> timestampsToCheck = new ArrayList<>();
                for (int i = 0; i < 1440; i++) {
                    timestampsToCheck.add(currentTime + i * Utils.TIME_MINUTE);
                }

                // 2. Check xem các phút này ĐÃ TỒN TẠI trong Aerospike chưa
                Set<Long> existingTimestamps = DataManagerAerospikeFloatSim.checkExistingMarketAiPredictions(timestampsToCheck);

                // Nếu cả ngày đều đã có data -> Bỏ qua toàn bộ ngày
                if (existingTimestamps.size() >= 1440) {
                    LOG.info("⏩ Day {} already fully generated ({} records). Skipping...",
                            Utils.normalizeDateYYYYMMDD(currentTime), existingTimestamps.size());
                    currentTime += Utils.TIME_DAY;
                    continue;
                }

                // 3. Đọc nến 1M của ngày hôm nay từ Aerospike (Dùng Custom để chuẩn giờ 00:00:00)
                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, 1440);

                Map<Long, AiPredictionData> batchPredictions = new HashMap<>();

                if (todayData != null && !todayData.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
                        Long timestamp = entry.getKey();

                        if (existingTimestamps.contains(timestamp)) {
                            continue;
                        }

                        Map<String, KlineObjectSimple> marketData = entry.getValue();
                        MarketDataObject rateChange = time2Rate.get(timestamp);

                        List<String> targetBasket = findTop50LosersFromPeak15m(todayData, timestamp);

                        if (targetBasket.size() >= 3) {
                            MarketFeatures features = featureExtractor.extractAllFeatures(
                                    timestamp, marketData, rateChange, targetBasket);

                            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

                            batchPredictions.put(timestamp, new AiPredictionData(
                                    timestamp,
                                    res.return15M, res.return1H, res.return4H, res.return24H,
                                    res.riskDrawdown4H, res.riskDrawdown24H
                            ));
                        }
                    }
                }

                // 4. Lưu vào Aerospike
                if (!batchPredictions.isEmpty()) {
                    DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatch(batchPredictions);
                }

                processedDays++;
                LOG.info("✅ Day {}: Generated and Saved {} NEW records. (Skipped {} existing)",
                        Utils.normalizeDateYYYYMMDD(currentTime), batchPredictions.size(), existingTimestamps.size());

                todayData = null;
                batchPredictions.clear();

            } catch (Exception e) {
                LOG.error("❌ Error processing day " + Utils.normalizeDateYYYYMMDD(currentTime), e);
            }

            currentTime += Utils.TIME_DAY;
        }

        aiBrain.close();
        LOG.info("🎉 DONE ALL MARKET PREDICTIONS!");
    }

    // Đổi hàm này để đọc từ Aerospike thay vì File Snappy
    private TreeMap<Long, MarketDataObject> loadMarketRateData() throws Exception {
        TreeMap<Long, MarketDataObject> data = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        if (data == null) return new TreeMap<>();
        return data;
    }


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
}