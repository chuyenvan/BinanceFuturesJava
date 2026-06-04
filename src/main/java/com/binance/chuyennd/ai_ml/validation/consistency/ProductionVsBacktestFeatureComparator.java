package com.binance.chuyennd.ai_ml.validation.consistency;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.lang.reflect.Field;
import java.util.*;

public class ProductionVsBacktestFeatureComparator {
    private static final Logger LOG = LoggerFactory.getLogger(ProductionVsBacktestFeatureComparator.class);
    private static final String PROD_PREDICT_DIR = "storage/data/prediction/";

    // 🔥 ĐƯỜNG DẪN TỚI FOLDER CHỨA MODEL ONNX (Giữ nguyên của bác)
    private static final String MODEL_DIR = "C:\\Users\\pc\\Desktop\\data\\ai_models_reg_v3";

    // --- CÁC BIẾN LƯU TRỮ THỐNG KÊ TRUNG BÌNH ---
    private Map<String, Double> featureDiffSum = new TreeMap<>();
    private Map<String, Integer> featureDiffCount = new TreeMap<>();
    private Map<String, Double> predictDiffSum = new TreeMap<>();
    private Map<String, Integer> predictDiffCount = new TreeMap<>();

    public static void main(String[] args) {
        new ProductionVsBacktestFeatureComparator().runCompare();
    }

    public void runCompare() {
        LOG.info("🚀 KHỞI ĐỘNG CÔNG CỤ SOI FEATURES & PREDICTIONS TRÊN TOÀN BỘ DỮ LIỆU...");

        List<File> featureFiles = collectFeatureFiles(PROD_PREDICT_DIR);
        if (featureFiles.isEmpty()) {
            LOG.error("❌ Không tìm thấy file dữ liệu nào!");
            return;
        }

        // 🔥 Quét toàn bộ dữ liệu thay vì 10 mẫu
        int limit = featureFiles.size();
        LOG.info("📊 TỔNG SỐ MẪU CẦN ĐỐI SOÁT: {}", limit);

        // 🧠 KHỞI TẠO BỘ NÃO AI ĐỂ CHẠY ON-THE-FLY
        OnnxInferenceManager aiBrain = null;
        try {
            aiBrain = new OnnxInferenceManager(MODEL_DIR);
            LOG.info("✅ Load AI Model thành công để test!");
        } catch (Exception e) {
            LOG.error("❌ Không thể load AI Model, kiểm tra lại MODEL_DIR: {}", MODEL_DIR, e);
        }

        for (int i = 0; i < limit; i++) {
            File prodFile = featureFiles.get(i);
            try {
                long rawTime = Long.parseLong(prodFile.getName().replace(".features", ""));
                long targetTime = (rawTime / 60000L) * 60000L;

                LOG.info("\n========================================================");
                LOG.info("🔍 MẪU {}/{} TẠI: {}", i+1, limit, Utils.normalizeDateYYYYMMDDHHmm(targetTime));

                MarketFeatures prodFeatures = (MarketFeatures) StorageSnappy.readObjectFromFile(prodFile.getPath());
                if (prodFeatures == null) continue;

                long startTimeWarmup = targetTime - (1500 * 60000L);
                TreeMap<Long, Map<String, KlineObjectSimple>> warmupData =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startTimeWarmup, 1505);

                if (warmupData.isEmpty()) continue;

                Map<String, KlineObjectSimple> targetMarketData = warmupData.remove(targetTime);
                if (targetMarketData == null) continue;
                warmupData.tailMap(targetTime).clear();

                ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();
                extractor.initDataFromTickerMap(warmupData);
                MarketDataObject targetMarketRate = calculateMarketData(targetTime, warmupData, targetMarketData);

                // 1. TRÍCH XUẤT FEATURES BẰNG CODE BACKTEST
                MarketFeatures btFeatures = extractor.extractAllFeatures(targetTime, targetMarketData, targetMarketRate);

                // 2. ĐỐI SOÁT FEATURES VÀ LƯU THỐNG KÊ
                compareFeatureFields(prodFeatures, btFeatures);

                // 3. ĐỐI SOÁT PREDICTIONS BẰNG AI MODEL (3 CHIỀU)
                if (aiBrain != null) {
                    // Đọc file predict gốc của Production (Xóa đuôi .features đi)
                    String predictFilePath = prodFile.getPath().replace(".features", "");
                    OnnxInferenceManager.PredictionResult prodSavedPred =
                            (OnnxInferenceManager.PredictionResult) StorageSnappy.readObjectFromFile(predictFilePath);

                    // Prod_Fly (Tính lại trên Prod_Features) và BT_Fly (Tính trên BT_Features)
                    // 🔥 Thay đổi hàm thành predictAll theo code của bác
                    OnnxInferenceManager.PredictionResult prodFlyPred = aiBrain.predictAll(prodFeatures);
                    OnnxInferenceManager.PredictionResult btFlyPred = aiBrain.predictAll(btFeatures);

                    if (prodSavedPred != null) {
                        comparePredictions3Way(prodSavedPred, prodFlyPred, btFlyPred);
                    } else {
                        LOG.warn("⚠️ Không tìm thấy file Prediction của PROD tại: {}", predictFilePath);
                        // Fallback: So sánh 2 chiều thông thường nếu ko có file
                        comparePredictions3Way(prodFlyPred, prodFlyPred, btFlyPred);
                    }
                }

            } catch (Exception e) {
                LOG.error("Lỗi: ", e);
            }
        }

        if (aiBrain != null) {
            try { aiBrain.close(); } catch (Exception e) {}
        }

        // 🔥 IN BẢNG THỐNG KÊ TRUNG BÌNH KHI KẾT THÚC
        printStatisticsSummary(limit);
    }

    private void comparePredictions3Way(OnnxInferenceManager.PredictionResult prodSaved,
                                        OnnxInferenceManager.PredictionResult prodFly,
                                        OnnxInferenceManager.PredictionResult bt) {
        LOG.info("--- 🧠 ĐỐI SOÁT AI PREDICTION (3 CHIỀU) ---");
        float epsilon = 0.0001f;

        // BƯỚC 1: Check tính nhất quán của Model (Prod Saved vs Prod Fly)
        int diffModel = 0;
        diffModel += checkPred("return15M (Fly)", prodSaved.return15M, prodFly.return15M, epsilon, false);
        diffModel += checkPred("risk4H (Fly)", prodSaved.riskDrawdown4H, prodFly.riskDrawdown4H, epsilon, false);

        if (diffModel > 0) {
            LOG.error("🚨 CẢNH BÁO ĐỎ: ONNX Model tính toán không nhất quán! (Cùng 1 Features nhưng lúc Realtime ra kết quả khác lúc Test)");
        }

        // BƯỚC 2: Check độ lệch môi trường (Prod Saved vs Backtest Fly)
        int diffEnv = 0;
        diffEnv += checkPred("return15M", prodSaved.return15M, bt.return15M, epsilon, true);
        diffEnv += checkPred("riskDrawdown4H", prodSaved.riskDrawdown4H, bt.riskDrawdown4H, epsilon, true);

        if (diffEnv == 0) {
            LOG.info("✅ PREDICTION CỦA PROD VÀ BACKTEST KHỚP HOÀN HẢO 100%!");
        } else {
            LOG.info("❌ Số lượng biến Prediction bị lệch: {}", diffEnv);
        }
    }

    private int checkPred(String name, float prod, float bt, float epsilon, boolean isRecordStats) {
        float percentDiff = 0f;
        float maxAbs = Math.max(Math.abs(prod), Math.abs(bt));

        if (maxAbs > 0.000001f) {
            percentDiff = (Math.abs(prod - bt) / maxAbs) * 100f;
        }

        // Chỉ cộng dồn thống kê cho trường hợp đối chiếu Prod vs BT (Môi trường thực)
        if (isRecordStats) {
            predictDiffSum.put(name, predictDiffSum.getOrDefault(name, 0.0) + percentDiff);
            predictDiffCount.put(name, predictDiffCount.getOrDefault(name, 0) + 1);
        }

        if (Math.abs(prod - bt) > epsilon) {
            String percentStr = String.format("%.2f%%", percentDiff);
            LOG.error("❌ LỆCH PREDICT [{}]: PROD = {} | BT = {} | Lệch: {}",
                    String.format("%-20s", name), String.format("%10.6f", prod), String.format("%10.6f", bt), percentStr);
            return 1;
        }
        return 0;
    }

    private void compareFeatureFields(MarketFeatures prod, MarketFeatures bt) {
        int diffCount = 0;
        Field[] fields = MarketFeatures.class.getFields();
        for (Field field : fields) {
            try {
                field.setAccessible(true);
                Object prodVal = field.get(prod);
                Object btVal = field.get(bt);
                if (prodVal == null && btVal == null) continue;

                boolean isMatch = false;
                float diffPercent = 0f;

                if (prodVal instanceof Number && btVal instanceof Number) {
                    float p = ((Number) prodVal).floatValue();
                    float b = ((Number) btVal).floatValue();
                    if (Math.abs(p - b) < 0.0001f) {
                        isMatch = true;
                    }
                    float maxAbs = Math.max(Math.abs(p), Math.abs(b));
                    if (maxAbs > 0.000001f) {
                        diffPercent = (Math.abs(p - b) / maxAbs) * 100f;
                    }
                } else {
                    isMatch = Objects.equals(prodVal, btVal);
                }

                // Ghi nhận thống kê cho tất cả các biến Number (Dù lệch 0% vẫn ghi nhận)
                if (prodVal instanceof Number && btVal instanceof Number) {
                    String fieldName = field.getName();
                    featureDiffSum.put(fieldName, featureDiffSum.getOrDefault(fieldName, 0.0) + diffPercent);
                    featureDiffCount.put(fieldName, featureDiffCount.getOrDefault(fieldName, 0) + 1);
                }

                if (!isMatch) {
                    diffCount++;
                    if (prodVal instanceof Number && btVal instanceof Number) {
                        float p = ((Number) prodVal).floatValue();
                        float b = ((Number) btVal).floatValue();
                        LOG.warn("   ⚠️ [FEATURE] {}: PROD = {} | BT = {} | Lệch: {}%",
                                String.format("%-25s", field.getName()),
                                String.format("%10.6f", p),
                                String.format("%10.6f", b),
                                String.format("%5.2f", diffPercent));
                    } else {
                        LOG.warn("   ⚠️ [FEATURE] {}: PROD = {} | BT = {}", field.getName(), prodVal, btVal);
                    }
                }
            } catch (Exception e) {}
        }
        LOG.info("=> Tổng lệch {} Features", diffCount);
    }

    private void printStatisticsSummary(int totalSamples) {
        LOG.info("\n========================================================");
        LOG.info("📊 TỔNG KẾT LỆCH TRUNG BÌNH TRÊN {} MẪU DỮ LIỆU", totalSamples);
        LOG.info("========================================================");

        LOG.info("--- 1. LỆCH TRUNG BÌNH CỦA MARKET FEATURES ---");
        for (Map.Entry<String, Double> entry : featureDiffSum.entrySet()) {
            String name = entry.getKey();
            int count = featureDiffCount.getOrDefault(name, 1);
            double avgDiff = entry.getValue() / count;

            if (avgDiff > 0.01) { // Lọc bỏ nhiễu li ti
                LOG.info("   🔸 {}: {}%", String.format("%-25s", name), String.format("%6.3f", avgDiff));
            }
        }

        LOG.info("\n--- 2. LỆCH TRUNG BÌNH CỦA AI PREDICTIONS ---");
        for (Map.Entry<String, Double> entry : predictDiffSum.entrySet()) {
            String name = entry.getKey();
            int count = predictDiffCount.getOrDefault(name, 1);
            double avgDiff = entry.getValue() / count;
            LOG.info("   🎯 {}: {}%", String.format("%-25s", name), String.format("%6.3f", avgDiff));
        }
        LOG.info("========================================================\n");
    }

    // =========================================================================
    // HÀM TỰ TÍNH MARKET DATA (GIỮ NGUYÊN HOÀN TOÀN CỦA BÁC)
    // =========================================================================
    private MarketDataObject calculateMarketData(long targetTime,
                                                 TreeMap<Long, Map<String, KlineObjectSimple>> warmupData,
                                                 Map<String, KlineObjectSimple> targetMarketData) {
        Map<String, Float> symbol2MaxPrice = new HashMap<>();
        Map<String, Float> symbol2MinPrice = new HashMap<>();
        int lookback = 15;

        for (String symbol : targetMarketData.keySet()) {
            float maxP = -1f; float minP = Float.MAX_VALUE;
            for (int i = 0; i < lookback; i++) {
                long pastTime = targetTime - (i * 60000L);
                Map<String, KlineObjectSimple> snapshot = (pastTime == targetTime) ? targetMarketData : warmupData.get(pastTime);
                if (snapshot != null) {
                    KlineObjectSimple k = snapshot.get(symbol);
                    if (k != null) {
                        if (k.maxPrice > maxP) maxP = k.maxPrice;
                        if (k.minPrice < minP) minP = k.minPrice;
                    }
                }
            }
            if (maxP != -1f) symbol2MaxPrice.put(symbol, maxP);
            if (minP != Float.MAX_VALUE) symbol2MinPrice.put(symbol, minP);
        }

        try {
            return MarketBigChangeDetector.calMarketData(targetMarketData, symbol2MaxPrice, symbol2MinPrice);
        } catch (Exception e) {
            return new MarketDataObject(0f, 0f, 0f);
        }
    }

    // =========================================================================
    // HÀM TÌM KIẾM FILE (GIỮ NGUYÊN HOÀN TOÀN CỦA BÁC)
    // =========================================================================
    private List<File> collectFeatureFiles(String path) {
        List<File> allFiles = new ArrayList<>(); File root = new File(path);
        if (!root.exists() || !root.isDirectory()) return allFiles;
        File[] dateDirs = root.listFiles(File::isDirectory);
        if (dateDirs != null) {
            for (File dateDir : dateDirs) {
                File[] files = dateDir.listFiles((dir, name) -> name.endsWith(".features"));
                if (files != null) allFiles.addAll(Arrays.asList(files));
            }
        }
        return allFiles;
    }
}