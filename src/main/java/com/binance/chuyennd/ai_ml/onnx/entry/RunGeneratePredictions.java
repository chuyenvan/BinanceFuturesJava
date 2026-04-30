package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class RunGeneratePredictions {
    private static final Logger LOG = LoggerFactory.getLogger(RunGeneratePredictions.class);
    private static final String MODEL_DIR = "../storage/ai_ml_data/ai_models_reg_v3"; // Sửa lại đường dẫn model nếu cần

    public static void main(String[] args) {
        try {
            System.setProperty("ai.onnxruntime.disable_telemetry", "true");
            System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
            DataManagerAerospikeFloatSim.setThreadCount(4);

            // Truyền null để chạy từ đầu nếu chạy file này độc lập
            new RunGeneratePredictions().generateAndSave(null);
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    // Thêm tham số lastTimestamp
    public void generateAndSave(Long lastTimestamp) throws Exception {
        OnnxInferenceManager aiBrain = new OnnxInferenceManager(MODEL_DIR);

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
                List<Long> timestampsToCheck = new ArrayList<>();
                for (int i = 0; i < 1440; i++) {
                    timestampsToCheck.add(currentTime + i * Utils.TIME_MINUTE);
                }
//
                Set<Long> existingTimestamps = DataManagerAerospikeFloatSim.checkExistingMarketAiPredictions(timestampsToCheck);
//                Set<Long> existingTimestamps = new HashSet<>();
                // Nếu cả ngày đều đã có data -> Bỏ qua toàn bộ ngày
                if (existingTimestamps.size() >= 1440) {
                    LOG.info("⏩ Day {} đã full ({} records). Skipping...",
                            Utils.normalizeDateYYYYMMDD(currentTime), existingTimestamps.size());
                    currentTime += Utils.TIME_DAY;
                    continue; // Bỏ qua
                }

                // =====================================================================
                // 🔥 BẮT BUỘC: KHỞI TẠO LẠI VÀ WARM-UP TRƯỚC KHI TÍNH NGÀY MỚI
                // =====================================================================
                ComprehensiveMarketFeatureExtractor featureExtractor = new ComprehensiveMarketFeatureExtractor();

                long warmupStartTime = currentTime - (1500 * Utils.TIME_MINUTE);
                LOG.info("📥 Đang kéo 1500 phút quá khứ từ Aerospike để Warm-Up Extractor...");
                TreeMap<Long, Map<String, KlineObjectSimple>> warmupData =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(warmupStartTime, 1500);

                if (warmupData != null && !warmupData.isEmpty()) {
                    featureExtractor.initDataFromTickerMap(warmupData);
                    LOG.info("✅ Warm-up thành công!");
                }
                // =====================================================================

                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, 1440);

                Map<Long, AiPredictionData> batchPredictions = new HashMap<>();

                if (!todayData.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
                        Long timestamp = entry.getKey();

                        if (existingTimestamps.contains(timestamp)) {
                            continue;
                        }

                        Map<String, KlineObjectSimple> marketData = entry.getValue();
                        MarketDataObject rateChange = time2Rate.get(timestamp);

                        // Tính Features
                        MarketFeatures features = featureExtractor.extractAllFeatures(
                                timestamp, marketData, rateChange);
                        OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

                        batchPredictions.put(timestamp, new AiPredictionData(
                                timestamp,
                                res.return15M,  res.return24H,
                                res.riskDrawdown4H
                        ));
                    }
                }

                if (!batchPredictions.isEmpty()) {
                    DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatch(batchPredictions);
                }

                processedDays++;
                LOG.info("✅ Day {}: Đã lưu {} records mới. (Bỏ qua {} records cũ)",
                        Utils.normalizeDateYYYYMMDD(currentTime), batchPredictions.size(), existingTimestamps.size());

                todayData = null;
                warmupData = null; // Clear RAM
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
    // Thêm vào class RunGeneratePredictions.java

    /**
     * Hàm tính toán Predict cho Duy Nhất 1 thời điểm.
     * Lưu ý: Extractor truyền vào phải được Warm-up/Update history trước khi gọi hàm này.
     */
    public AiPredictionData predictSingle(long timestamp,
                                          Map<String, KlineObjectSimple> currentMarketSnapshot,
                                          MarketDataObject rateChange,
                                          OnnxInferenceManager aiBrain,
                                          ComprehensiveMarketFeatureExtractor featureExtractor) {
        try {
            if (currentMarketSnapshot == null || currentMarketSnapshot.isEmpty()) return null;
            // B. Warm-up 1500 phút nến để tính toán lại
            LOG.info("   ⏳ Đang Warm-up 1500 nến từ Aerospike...");
            HistoryManager.getInstance().getAllHistory().clear();
            CoinRankManager.getInstance().resetCache();

            // 1. Trích xuất Features (Dựa trên history đã được update trong featureExtractor)
            MarketFeatures features = featureExtractor.extractAllFeatures(timestamp, currentMarketSnapshot, rateChange);

            // 2. Chạy AI Inference
            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

            // 3. Đóng gói kết quả
            return new AiPredictionData(
                    timestamp,
                    res.return15M, res.return24H, res.riskDrawdown4H
            );
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi tính predictSingle tại " + Utils.normalizeDateYYYYMMDDHHmm(timestamp), e);
            return null;
        }
    }

    // Hàm bổ trợ để load Model tập trung
    public OnnxInferenceManager getModelManager() throws Exception {
        return new OnnxInferenceManager(MODEL_DIR);
    }

}