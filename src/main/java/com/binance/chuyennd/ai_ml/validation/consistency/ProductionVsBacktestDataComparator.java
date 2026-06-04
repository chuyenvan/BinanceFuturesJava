package com.binance.chuyennd.ai_ml.validation.consistency;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
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

public class ProductionVsBacktestDataComparator {
    private static final Logger LOG = LoggerFactory.getLogger(ProductionVsBacktestDataComparator.class);

    private static final String PROD_PREDICT_DIR = "storage/data/prediction/";

    // 🔥 NGƯỠNG LỆCH PHẦN TRĂM (0.03 = 3%)
    private static final double TOLERANCE_THRESHOLD = 0.03;

    // Class phụ để lưu trữ các mẫu bị lệch và sắp xếp
    static class MismatchRecord implements Comparable<MismatchRecord> {
        long time;
        double maxDeviation;
        String logDetail;

        public MismatchRecord(long time, double maxDeviation, String logDetail) {
            this.time = time;
            this.maxDeviation = maxDeviation;
            this.logDetail = logDetail;
        }

        @Override
        public int compareTo(MismatchRecord o) {
            // Sắp xếp giảm dần (Lệch to nhất lên đầu)
            return Double.compare(o.maxDeviation, this.maxDeviation);
        }
    }

    public static void main(String[] args) {
        new ProductionVsBacktestDataComparator().runCompare();
    }

    public void runCompare() {
        LOG.info("🚀 Đang khởi động tiến trình đối soát (Ngưỡng Lệch >= {}%)...", TOLERANCE_THRESHOLD * 100);

        List<File> predictFiles = collectPredictionFiles(PROD_PREDICT_DIR);
        if (predictFiles.isEmpty()) return;

        int matchCount = 0;
        int mismatchCount = 0;

        List<MismatchRecord> mismatchList = new ArrayList<>();

        for (File file : predictFiles) {
            try {
                long timestamp = Long.parseLong(file.getName());

                OnnxInferenceManager.PredictionResult prodData =
                        (OnnxInferenceManager.PredictionResult) StorageSnappy.readObjectFromFile(file.getPath());
                if (prodData == null) continue;

                AiPredictionData backtestData = DataManagerAerospikeFloatSim.getAiPredictionMarketAtTime(timestamp);
                if (backtestData == null) continue;

                // Tính % lệch của 2 biến nòng cốt (đã bỏ 24H)
                double dev15M = getDeviation(prodData.return15M, backtestData.predReturn15M);
                double devRisk4H = getDeviation(prodData.riskDrawdown4H, backtestData.predRisk4H);

                // Độ lệch lớn nhất đại diện cho mẫu này
                double maxDev = Math.max(dev15M, devRisk4H);

                if (maxDev <= TOLERANCE_THRESHOLD) {
                    matchCount++;
                } else {
                    mismatchCount++;
                    String detail = String.format("PROD [15M:%8.5f, Risk4H:%8.5f] vs BT [15M:%8.5f, Risk4H:%8.5f] | Max Lệch: %.2f%%",
                            prodData.return15M, prodData.riskDrawdown4H,
                            backtestData.predReturn15M, backtestData.predRisk4H,
                            maxDev * 100);
                    mismatchList.add(new MismatchRecord(timestamp, maxDev, detail));
                }
            } catch (Exception e) {}
        }

        Collections.sort(mismatchList);

        LOG.info("\n==========================================");
        LOG.info("=== 🚨 TOP 10 TRƯỜNG HỢP LỆCH NẶNG NHẤT VÀ PHÂN TÍCH FEATURE ===");


        int limit = Math.min(10, mismatchList.size());
        for (int i = 0; i < limit; i++) {
            MismatchRecord record = mismatchList.get(i);
            LOG.info("\n🔴 Top {}: Time: {} | {}", i + 1, Utils.normalizeDateYYYYMMDDHHmm(record.time), record.logDetail);

            // --- TRÍCH XUẤT VÀ ĐỐI CHIẾU FEATURE CỦA RIÊNG MẪU NÀY ---
            analyzeFeatureMismatch(record.time);
        }

        LOG.info("\n==========================================");
        LOG.info("=== BÁO CÁO ĐỐI SOÁT PREDICTION ===");
        LOG.info("✅ Khớp (Lệch <= {}%)           : {}", TOLERANCE_THRESHOLD * 100, matchCount);
        LOG.info("❌ Bị lệch pha (Lệch > {}%)     : {}", TOLERANCE_THRESHOLD * 100, mismatchCount);
        LOG.info("==========================================");
    }

    // =========================================================================
    // HÀM TỰ ĐỘNG CÀO FEATURE VÀ ĐỐI CHIẾU
    // =========================================================================
    private void analyzeFeatureMismatch(long targetTime) {
        try {
            // 1. Đọc PROD Features
            String featurePath = PROD_PREDICT_DIR + Utils.normalizeDateYYYYMMDD(targetTime) + "/" + targetTime + ".features";
            MarketFeatures prodFeatures = (MarketFeatures) StorageSnappy.readObjectFromFile(featurePath);

            if (prodFeatures == null) {
                LOG.warn("   ⚠️ Không tìm thấy file PROD .features tại {}", featurePath);
                return;
            }

            // 2. Cào dữ liệu BT và Warmup
            long startTimeWarmup = targetTime - (1500 * 60000L);
            TreeMap<Long, Map<String, KlineObjectSimple>> warmupData =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startTimeWarmup, 1505);

            if (warmupData == null || warmupData.isEmpty()) {
                LOG.warn("   ⚠️ Aerospike trả về rỗng. Không thể tái tạo BT.");
                return;
            }

            Map<String, KlineObjectSimple> targetMarketData = warmupData.remove(targetTime);
            if (targetMarketData == null) return;
            warmupData.tailMap(targetTime).clear();

            ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();
            extractor.initDataFromTickerMap(warmupData);

            MarketDataObject targetMarketRate = DataManagerAerospikeFloatSim.getMarketDataAtTime(targetTime);
            if (targetMarketRate == null) {
                targetMarketRate = calculateMarketData(targetTime, warmupData, targetMarketData);
            }

            // 3. Tái tạo BT Features
            MarketFeatures btFeatures = extractor.extractAllFeatures(targetTime, targetMarketData, targetMarketRate);

            // 4. SO SÁNH FIELD BY FIELD
            int diffCount = 0;
            Field[] fields = MarketFeatures.class.getFields();
            for (Field field : fields) {
                try {
                    field.setAccessible(true);
                    Object prodVal = field.get(prodFeatures);
                    Object btVal = field.get(btFeatures);
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
                        LOG.error("   ↳ ❌ Feature Lệch: [{}] -> PROD: {} | BT: {}", field.getName(), prodVal, btVal);
                    }
                } catch (Exception e) {}
            }

            if (diffCount == 0) {
                LOG.info("   ✅ Tất cả Features đều khớp hoàn hảo! (Lệch Prediction có thể do quá trình AI Model bị lượng tử hóa Float/Double)");
            } else {
                LOG.info("   => Kết luận: Có {} Features đầu vào bị lệch khiến AI ra quyết định sai khác.", diffCount);
            }

        } catch (Exception e) {
            LOG.error("   ⚠️ Lỗi phân tích Feature: ", e);
        }
    }

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

    private double getDeviation(double prodValue, double btValue) {
        if (prodValue == 0 && btValue == 0) return 0.0;
        double maxAbs = Math.max(Math.abs(prodValue), Math.abs(btValue));
        if (maxAbs < 0.000001) return 0.0;
        return Math.abs(prodValue - btValue) / maxAbs;
    }

    private List<File> collectPredictionFiles(String path) {
        List<File> allFiles = new ArrayList<>(); File root = new File(path);
        if (!root.exists() || !root.isDirectory()) return allFiles;
        File[] dateDirs = root.listFiles(File::isDirectory);
        if (dateDirs != null) {
            for (File dateDir : dateDirs) {
                File[] files = dateDir.listFiles((dir, name) -> !name.endsWith(".features"));
                if (files != null) allFiles.addAll(Arrays.asList(files));
            }
        }
        return allFiles;
    }
}