package com.binance.chuyennd.aerospike.validate_data.predictmarket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor15M;
import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.ai_ml.onnx.entry.RunGeneratePredictions;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

public class ValidateMarketPredictConsistency {
    public static final Logger LOG = LoggerFactory.getLogger(ValidateMarketPredictConsistency.class);

    public static void main(String[] args) {
        new ValidateMarketPredictConsistency().runRandomValidation();
    }

    public void runRandomValidation() {
        LOG.info("🚀 KHỞI ĐỘNG ĐỐI SOÁT DỰ BÁO 15M: AEROSPIKE (CŨ) vs TÍNH TOÁN LẠI (MỚI)...");

        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            long startTime = fmt.parse("20210101-0700").getTime();
            long endTime = System.currentTimeMillis() - 60 * Utils.TIME_MINUTE; // Bỏ qua 1h gần nhất
            long thirtyDaysAgo = endTime - (30L * 24 * 60 * 60 * 1000);

            // 1. SINH 20 MỐC THỜI GIAN NGẪU NHIÊN CHUẨN 15 PHÚT
            Set<Long> randomTimestamps = new HashSet<>();
            long block15m = 15 * 60000L;

            while (randomTimestamps.size() < 10) {
                long rawTime = ThreadLocalRandom.current().nextLong(thirtyDaysAgo, endTime);
                // 🔥 Ép mốc thời gian về chẵn 15 phút (00, 15, 30, 45)
                randomTimestamps.add((rawTime / block15m) * block15m);
            }
            while (randomTimestamps.size() < 20) {
                long rawTime = ThreadLocalRandom.current().nextLong(startTime, thirtyDaysAgo);
                randomTimestamps.add((rawTime / block15m) * block15m);
            }

            List<Long> testTimestamps = new ArrayList<>(randomTimestamps);
            Collections.sort(testTimestamps);

            RunGeneratePredictions generator = new RunGeneratePredictions();
            OnnxInferenceManager aiBrain = new OnnxInferenceManager(Configs.MODEL_MARKET_PREDICT_DIR);
            ComprehensiveMarketFeatureExtractor15M featureExtractor = new ComprehensiveMarketFeatureExtractor15M();

            int totalChecked = 0;
            int totalErrors = 0;

            // 2. BẮT ĐẦU ĐỐI SOÁT TỪNG MẪU
            for (int i = 0; i < testTimestamps.size(); i++) {
                long targetTime = testTimestamps.get(i);
                LOG.info("\n========================================================");
                LOG.info("🔍 MẪU {}/20 TẠI: {}", (i + 1), Utils.normalizeDateYYYYMMDDHHmm(targetTime));

                // A. Lấy dữ liệu cũ từ Aerospike
                AiPredictionData oldPred = DataManagerAerospikeFloatSim.getMarketAiPredictionAtTime(targetTime);
                if (oldPred == null) {
                    LOG.warn("   ⚠️ Aerospike không có dữ liệu cũ tại phút này. Bỏ qua!");
                    continue;
                }

                // B. Warm-up 100 nến 15M (Tương đương 25 giờ) để tính toán lại
                LOG.info("   ⏳ Đang Warm-up 100 block 15m từ Aerospike...");
                HistoryManager15M.getInstance().resetCache();

                long warmupStart = targetTime - 100 * block15m;
                TreeMap<Long, Map<Short, KlineObjectSimple>> warmupData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(warmupStart, 101);

                if (warmupData == null || !warmupData.containsKey(targetTime)) {
                    LOG.error("   ❌ Thiếu dữ liệu nến để tính toán lại. Bỏ qua!");
                    continue;
                }

                // Nạp lịch sử (trừ cây nến target để truyền vào hàm predictSingle)
                for (Map.Entry<Long, Map<Short, KlineObjectSimple>> entry : warmupData.entrySet()) {
                    if (entry.getKey() < targetTime) {
                        HistoryManager15M.getInstance().updateHistory(entry.getValue());
                    }
                }

                // C. Tính toán lại kết quả mới (On-the-fly)
                Map<Short, KlineObjectSimple> snapshot = warmupData.get(targetTime);
                MarketDataObject15M rateChange = DataManagerAerospikeFloatSim.getMarketData15MAtTime(targetTime);

                AiPredictionData newPred = generator.predictSingle(
                        targetTime, snapshot, rateChange, aiBrain, featureExtractor
                );

                if (newPred == null) {
                    LOG.error("   ❌ Không thể tính toán lại dự báo mới!");
                    continue;
                }

                // D. So sánh các chỉ số nòng cốt
                totalChecked++;
                int diffs = comparePredictions(oldPred, newPred);
                if (diffs > 0) totalErrors++;
            }
            aiBrain.close();
            LOG.info("\n========================================================");
            LOG.info("🎉 TỔNG KẾT ĐỐI SOÁT PREDICT 15M:");
            LOG.info("📊 Mẫu đã check   : {}", totalChecked);
            LOG.info("🚨 Mẫu bị sai lệch : {} (Sai số > 0.5%)", totalErrors);
            LOG.info("========================================================");

        } catch (Exception e) {
            LOG.error("Lỗi đối soát dự báo", e);
        }
    }

    /**
     * So sánh các field float trong AiPredictionData. Sai số > 0.5% tính là lỗi.
     */
    private int comparePredictions(AiPredictionData oldP, AiPredictionData newP) {
        int errorCount = 0;
        // 🔥 Đã đổi tên 3 biến sang hệ quy chiếu 15M (1H, 4H, Risk4H)
        String[] fieldsToCheck = {"predReturn1H", "predReturn4H", "predRisk4H"};

        for (String fieldName : fieldsToCheck) {
            try {
                Field field = AiPredictionData.class.getField(fieldName);
                float valOld = field.getFloat(oldP);
                float valNew = field.getFloat(newP);

                float maxAbs = Math.max(Math.abs(valOld), Math.abs(valNew));
                float diffPercent = (maxAbs == 0) ? 0 : (Math.abs(valOld - valNew) / maxAbs) * 100f;

                if (diffPercent > 0.5f) {
                    errorCount++;
                    LOG.error("   ❌ [LỆCH {}] Cũ: {} | Mới: {} | Lệch: {}%",
                            fieldName, valOld, valNew, String.format("%.2f", diffPercent));
                }
            } catch (Exception e) {
                LOG.error("Lỗi truy cập field: " + fieldName, e);
            }
        }

        if (errorCount == 0) {
            LOG.info("   ✅ HOÀN HẢO! Kết quả tính lại khớp hoàn toàn với dữ liệu cũ.");
        }
        return errorCount;
    }
}