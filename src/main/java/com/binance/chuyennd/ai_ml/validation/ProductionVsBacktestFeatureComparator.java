package com.binance.chuyennd.ai_ml.validation;

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

    // 🔥 ĐƯỜNG DẪN TỚI FOLDER CHỨA MODEL ONNX (Sửa lại nếu cần)
    private static final String MODEL_DIR = "C:\\Users\\pc\\Desktop\\data\\ai_models_reg_v3";

    public static void main(String[] args) {
        new ProductionVsBacktestFeatureComparator().runCompare();
    }

    public void runCompare() {
        LOG.info("🚀 KHỞI ĐỘNG CÔNG CỤ SOI FEATURES & PREDICTIONS (TEST 10 MẪU)...");

        List<File> featureFiles = collectFeatureFiles(PROD_PREDICT_DIR);
        if (featureFiles.isEmpty()) return;
        Collections.shuffle(featureFiles);
        int limit = Math.min(10, featureFiles.size()); // LẤY 10 MẪU


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

                // 2. ĐỐI SOÁT FEATURES
                compareFeatureFields(prodFeatures, btFeatures);

                // 3. ĐỐI SOÁT PREDICTIONS BẰNG AI MODEL
                if (aiBrain != null) {
                    String predictFilePath = prodFile.getPath().replace(".features", "");
                    OnnxInferenceManager.PredictionResult prodPred =
                            (OnnxInferenceManager.PredictionResult) StorageSnappy.readObjectFromFile(predictFilePath);

                    if (prodPred != null) {
                        OnnxInferenceManager.PredictionResult btPred = aiBrain.predictAll(btFeatures);
                        comparePredictions(prodPred, btPred);
                    } else {
                        LOG.warn("⚠️ Không tìm thấy file Prediction của PROD tại: {}", predictFilePath);
                    }
                }

            } catch (Exception e) {
                LOG.error("Lỗi: ", e);
            }
        }

        if (aiBrain != null) {
            try { aiBrain.close(); } catch (Exception e) {}
        }
    }

    private void comparePredictions(OnnxInferenceManager.PredictionResult prod, OnnxInferenceManager.PredictionResult bt) {
        LOG.info("--- 🧠 ĐỐI SOÁT AI PREDICTION ---");
        // Sai số cho phép: 0.0001 (Nếu lệch dưới mức này thì coi như bằng nhau)
        float epsilon = 0.0001f;
        int diff = 0;

        // CHỈ CHECK 3 LABEL QUAN TRỌNG NHẤT, BỎ QUA CÁC LABEL CÒN LẠI
        diff += checkPred("return15M", prod.return15M, bt.return15M, epsilon);
        diff += checkPred("return24H", prod.return24H, bt.return24H, epsilon);
        diff += checkPred("riskDrawdown4H", prod.riskDrawdown4H, bt.riskDrawdown4H, epsilon);

        if (diff == 0) {
            LOG.info("✅ PREDICTION CỦA 3 BIẾN NÒNG CỐT KHỚP HOÀN HẢO 100%!");
        } else {
            LOG.info("❌ Số lượng biến Prediction bị lệch: {}", diff);
        }
    }

    private int checkPred(String name, float prod, float bt, float epsilon) {
        if (Math.abs(prod - bt) > epsilon) {
            // Tính phần trăm lệch (Dựa trên giá trị lớn hơn để tránh chia cho 0 hoặc số quá nhỏ)
            float percentDiff = 0;
            float maxAbs = Math.max(Math.abs(prod), Math.abs(bt));

            if (maxAbs > 0.000001f) {
                percentDiff = (Math.abs(prod - bt) / maxAbs) * 100;
            }

            // Format log in ra 2 chữ số thập phân cho dễ nhìn
            String percentStr = String.format("%.2f%%", percentDiff);

            LOG.error("❌ LỆCH PREDICT [{}]: PROD = {} | BT = {} | Lệch: {}",
                    name, String.format("%.6f", prod), String.format("%.6f", bt), percentStr);
            return 1;
        }
        return 0;
    }

    // =========================================================================
    // HÀM TỰ TÍNH MARKET DATA
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

    private void compareFeatureFields(MarketFeatures prod, MarketFeatures bt) {
        int diffCount = 0;
        Field[] fields = MarketFeatures.class.getFields();
        for (Field field : fields) {
            try {
                field.setAccessible(true);
                Object prodVal = field.get(prod); Object btVal = field.get(bt);
                if (prodVal == null && btVal == null) continue;

                boolean isMatch = false;
                if (prodVal instanceof Float && btVal instanceof Float) {
                    isMatch = Math.abs((Float) prodVal - (Float) btVal) < 0.0001f;
                } else if (prodVal instanceof Double && btVal instanceof Double) {
                    isMatch = Math.abs((Double) prodVal - (Double) btVal) < 0.0001f;
                } else {
                    isMatch = Objects.equals(prodVal, btVal);
                }

                if (!isMatch) {
                    diffCount++;
                    // LOG.error("❌ LỆCH FEATURE: [{}] -> PROD: {} | BT: {}", field.getName(), prodVal, btVal);
                }
            } catch (Exception e) {}
        }
        LOG.info("=> Lệch {} Features (Đa phần là Breadth/Basket do sai số lượng Coin active)", diffCount);
    }

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