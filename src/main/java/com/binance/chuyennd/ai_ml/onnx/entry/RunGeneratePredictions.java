package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor15M;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures15M;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class RunGeneratePredictions {
    private static final Logger LOG = LoggerFactory.getLogger(RunGeneratePredictions.class);

    public static void main(String[] args) {
        try {
            System.setProperty("ai.onnxruntime.disable_telemetry", "true");
            System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
            DataManagerAerospikeFloatSim.setThreadCount(4);

            new RunGeneratePredictions().generateAndSave(null);
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void generateAndSave(Long targetStartTs) throws Exception {
        OnnxInferenceManager aiBrain = new OnnxInferenceManager(Configs.MODEL_MARKET_PREDICT_DIR);
        ComprehensiveMarketFeatureExtractor15M featureExtractor = new ComprehensiveMarketFeatureExtractor15M();

        long startGenerateTime;
        if (targetStartTs != null && targetStartTs > 0) {
            startGenerateTime = Utils.getDate(targetStartTs);
        } else {
            startGenerateTime = Utils.sdfFile.parse("20210101").getTime();
        }

        long warmupStartTime = startGenerateTime - (48 * 3600000L);
        long endTime = System.currentTimeMillis();

        LOG.info("=========================================================");
        LOG.info("🚀 BẮT ĐẦU CHẠY PREDICTION LIÊN TỤC (HỆ 15 PHÚT)");
        LOG.info("   - Thời gian Warmup: {}", Utils.normalizeDateYYYYMMDDHHmm(warmupStartTime));
        LOG.info("   - Thời gian ghi: {}", Utils.normalizeDateYYYYMMDDHHmm(startGenerateTime));
        LOG.info("=========================================================");

        HistoryManager15M.getInstance().resetCache();

        long currentReadTs = warmupStartTime;
        Map<Long, AiPredictionData> batchPredictions = new HashMap<>();
        long totalGenerated = 0;

        int chunkBlocks15m = 96; // 1 Ngày

        while (currentReadTs <= endTime) {
            try {
                // Đọc 96 blocks = 1 ngày (Data Kline)
                TreeMap<Long, Map<Short, KlineObjectSimple>> chunkData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentReadTs, chunkBlocks15m);

                if (chunkData != null && !chunkData.isEmpty()) {

                    // 🔥 CÚ HACK TỐI ƯU CỦA BÁC: Lấy tất cả RateChange 1 lần duy nhất bằng hàm Batch
                    // Bác chú ý: Cần đảm bảo trong DataManagerAerospikeFloatSim có hàm lấy Batch trả về Map
                    Map<Long, MarketDataObject15M> rateChangeMap =
                            DataManagerAerospikeFloatSim.getMarketData15MBatch(chunkData.keySet());

                    for (Map.Entry<Long, Map<Short, KlineObjectSimple>> entry : chunkData.entrySet()) {
                        long timestamp = entry.getKey();
                        Map<Short, KlineObjectSimple> marketData = entry.getValue();

                        // 1. LUÔN NUÔI HISTORY
                        HistoryManager15M.getInstance().updateHistory(marketData);

                        if (timestamp < startGenerateTime) {
                            continue;
                        }

                        // 2. TRÍCH XUẤT DATA 15M TỪ RAM (Thay vì ping Aerospike)
                        MarketDataObject15M rateChange = null;
                        if (rateChangeMap != null) {
                            rateChange = rateChangeMap.get(timestamp);
                        }

                        List<Short> basket = HistoryManager15M.getInstance().findPotentialLosersShort(timestamp);

                        MarketFeatures15M features = featureExtractor.extractAllFeatures(timestamp, marketData, rateChange, basket);

                        if (features != null) {
                            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

                            batchPredictions.put(timestamp, new AiPredictionData(
                                    timestamp,
                                    res.return1H, res.return4H, res.riskDrawdown4H
                            ));
                        }

                        if (batchPredictions.size() >= 1000) {
                            DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatch(batchPredictions);
                            totalGenerated += batchPredictions.size();
                            batchPredictions.clear();
                        }
                    }
                }

                LOG.info("⏩ Đã xử lý qua mốc: {} | Tổng ghi đè: {}", Utils.normalizeDateYYYYMMDDHHmm(currentReadTs),
                        totalGenerated);
                currentReadTs += chunkBlocks15m * 15 * Utils.TIME_MINUTE;

            } catch (Exception e) {
                LOG.error("❌ Lỗi khi xử lý đoạn thời gian " + Utils.normalizeDateYYYYMMDDHHmm(currentReadTs), e);
                currentReadTs += chunkBlocks15m * 15 * Utils.TIME_MINUTE;
            }
        }

        if (!batchPredictions.isEmpty()) {
            DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatch(batchPredictions);
            totalGenerated += batchPredictions.size();
        }

        aiBrain.close();
        LOG.info("🎉 HOÀN TẤT! ĐÃ GEN TỔNG CỘNG {} RECORDS (HỆ 15M).", totalGenerated);
    }

    public AiPredictionData predictSingle(long timestamp,
                                          Map<Short, KlineObjectSimple> currentMarketSnapshot,
                                          MarketDataObject15M rateChange,
                                          OnnxInferenceManager aiBrain,
                                          ComprehensiveMarketFeatureExtractor15M featureExtractor) {
        try {
            if (currentMarketSnapshot == null || currentMarketSnapshot.isEmpty()) return null;

            HistoryManager15M.getInstance().updateHistory(currentMarketSnapshot);
            List<Short> basket = HistoryManager15M.getInstance().findPotentialLosersShort(timestamp);

            MarketFeatures15M features = featureExtractor.extractAllFeatures(timestamp, currentMarketSnapshot, rateChange, basket);
            if (features == null) return null;

            OnnxInferenceManager.PredictionResult res = aiBrain.predictAll(features);

            return new AiPredictionData(
                    timestamp,
                    res.return1H, res.return4H, res.riskDrawdown4H
            );
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi tính predictSingle tại " + Utils.normalizeDateYYYYMMDDHHmm(timestamp), e);
            return null;
        }
    }
}