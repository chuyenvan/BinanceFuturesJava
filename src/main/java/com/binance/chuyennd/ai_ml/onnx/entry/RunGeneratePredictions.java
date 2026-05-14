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

            // Chạy thẳng 1 luồng từ ngày mong muốn (ví dụ 20210101)
            new RunGeneratePredictions().generateAndSave(null);
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void generateAndSave(Long targetStartTs) throws Exception {
        OnnxInferenceManager aiBrain = new OnnxInferenceManager(MODEL_DIR);
        ComprehensiveMarketFeatureExtractor featureExtractor = new ComprehensiveMarketFeatureExtractor();

        LOG.info("📥 Loading FULL Market Rates từ Aerospike...");
        TreeMap<Long, MarketDataObject> time2Rate = loadMarketRateData();

        long startGenerateTime;
        if (targetStartTs != null && targetStartTs > 0) {
            startGenerateTime = Utils.getDate(targetStartTs); // Tròn về 00:00:00 của ngày
        } else {
            startGenerateTime = Utils.sdfFile.parse("20210101").getTime();
        }

        // 🔥 WARMUP CHUẨN 48 TIẾNG (GIỐNG HỆT FILE EXPORT .BIN)
        long warmupStartTime = startGenerateTime - (48 * 3600000L);
        long endTime = System.currentTimeMillis();

        LOG.info("=========================================================");
        LOG.info("🚀 BẮT ĐẦU CHẠY PREDICTION LIÊN TỤC (KHÔNG KIỂM TRA TRÙNG)");
        LOG.info("   - Thời gian Warmup: {}", Utils.normalizeDateYYYYMMDDHHmm(warmupStartTime));
        LOG.info("   - Thời gian bắt đầu ghi: {}", Utils.normalizeDateYYYYMMDDHHmm(startGenerateTime));
        LOG.info("   - Thời gian kết thúc: {}", Utils.normalizeDateYYYYMMDDHHmm(endTime));
        LOG.info("=========================================================");

        // Dọn dẹp sạch sẽ 1 lần duy nhất lúc khởi động
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        long currentReadTs = warmupStartTime;
        Map<Long, AiPredictionData> batchPredictions = new HashMap<>();
        long totalGenerated = 0;

        while (currentReadTs <= endTime) {
            try {
                // Đọc theo chunk 1 ngày (1440 phút) để tối ưu IO Aerospike
                int chunkMinutes = 1440;
                TreeMap<Long, Map<String, KlineObjectSimple>> chunkData =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentReadTs, chunkMinutes);

                if (chunkData != null && !chunkData.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : chunkData.entrySet()) {
                        long timestamp = entry.getKey();
                        Map<String, KlineObjectSimple> marketData = entry.getValue();

                        // 1. LUÔN LUÔN NUÔI HISTORY VÀ RANK (Bất kể đang warmup hay ghi)
                        HistoryManager.getInstance().updateHistory(marketData);
                        CoinRankManager.getInstance().getTopCoin(timestamp);

                        // 2. NẾU ĐANG WARMUP THÌ BỎ QUA PREDICT
                        if (timestamp < startGenerateTime) {
                            continue;
                        }

                        // 3. TRÍCH XUẤT VÀ DỰ ĐOÁN
                        MarketDataObject rateChange = time2Rate.get(timestamp);
                        MarketFeatures features = featureExtractor.extractAllFeatures(timestamp, marketData, rateChange);

                        if (features != null) {
                            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

                            batchPredictions.put(timestamp, new AiPredictionData(
                                    timestamp,
                                    res.return15M, res.return24H
                            ));
                        }

                        // 4. GHI BATCH XUỐNG DB & XÓA RAM (Ghi mỗi 5000 record)
                        if (batchPredictions.size() >= 5000) {
                            DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatch(batchPredictions);
                            totalGenerated += batchPredictions.size();
                            batchPredictions.clear();
                        }
                    }
                }

                LOG.info("⏩ Đã xử lý qua mốc: {} | Tổng ghi đè: {}", Utils.normalizeDateYYYYMMDDHHmm(currentReadTs), totalGenerated);
                currentReadTs += chunkMinutes * Utils.TIME_MINUTE;

            } catch (Exception e) {
                LOG.error("❌ Lỗi khi xử lý đoạn thời gian " + Utils.normalizeDateYYYYMMDDHHmm(currentReadTs), e);
                currentReadTs += 1440 * Utils.TIME_MINUTE; // Bỏ qua chunk lỗi để đi tiếp
            }
        }

        // Ghi nốt phần dư
        if (!batchPredictions.isEmpty()) {
            DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatch(batchPredictions);
            totalGenerated += batchPredictions.size();
            batchPredictions.clear();
        }

        aiBrain.close();
        LOG.info("🎉 HOÀN TẤT! ĐÃ GEN & GHI ĐÈ TỔNG CỘNG {} RECORDS.", totalGenerated);
    }

    private TreeMap<Long, MarketDataObject> loadMarketRateData() throws Exception {
        TreeMap<Long, MarketDataObject> data = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        if (data == null) return new TreeMap<>();
        return data;
    }

    /**
     * Hàm tính toán Predict cho Duy Nhất 1 thời điểm (DÙNG CHO STREAMING LIVE).
     * ⚠️ QUAN TRỌNG: KHÔNG ĐƯỢC CLEAR HISTORY Ở ĐÂY.
     * Môi trường gọi hàm này phải chịu trách nhiệm nạp snapshot liên tục mỗi phút!
     */
    public AiPredictionData predictSingle(long timestamp,
                                          Map<String, KlineObjectSimple> currentMarketSnapshot,
                                          MarketDataObject rateChange,
                                          OnnxInferenceManager aiBrain,
                                          ComprehensiveMarketFeatureExtractor featureExtractor) {
        try {
            if (currentMarketSnapshot == null || currentMarketSnapshot.isEmpty()) return null;

            // ❌ ĐÃ XÓA LỆNH CLEAR HISTORY/RANK Ở ĐÂY ĐỂ TRÁNH LÀM MẤT TRÍ NHỚ CỦA RSI & BASKET

            // 1. Cập nhật dữ liệu mới nhất vào History & Rank
            HistoryManager.getInstance().updateHistory(currentMarketSnapshot);
            CoinRankManager.getInstance().getTopCoin(timestamp);

            // 2. Trích xuất Features
            MarketFeatures features = featureExtractor.extractAllFeatures(timestamp, currentMarketSnapshot, rateChange);

            // 3. Chạy AI Inference
            if (features == null) return null;
            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

            // 4. Đóng gói kết quả
            return new AiPredictionData(
                    timestamp,
                    res.return15M, res.return24H
            );
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi tính predictSingle tại " + Utils.normalizeDateYYYYMMDDHHmm(timestamp), e);
            return null;
        }
    }

    public OnnxInferenceManager getModelManager() throws Exception {
        return new OnnxInferenceManager(MODEL_DIR);
    }
}