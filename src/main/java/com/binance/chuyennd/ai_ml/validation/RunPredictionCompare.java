package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.lang.reflect.Field;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

public class RunPredictionCompare {
    private static final Logger LOG = LoggerFactory.getLogger(RunPredictionCompare.class);

    // --- CẤU HÌNH ---
    private static final String START_DATE_STR = "20251227";
    private static final String MODEL_DIR = "../storage/ai_ml_data/ai_models_reg_v3";
    private static final String PROD_DIR = "storage/data/prediction/";
    private static final String TEST_DIR = "storage/predictiontest/";

    private OnnxInferenceManager aiBrain;
    private ComprehensiveMarketFeatureExtractor featureExtractor;
    private TreeMap<Long, MarketRateChange> time2Rate;

    public static void main(String[] args) {
        try {
            System.setProperty("ai.onnxruntime.disable_telemetry", "true");
            new RunPredictionCompare().process();
        } catch (Exception e) {
            LOG.error("Main Process Error", e);
        }
    }

    public void process() throws Exception {
        initSystem();
        long startTime = Utils.sdfFile.parse(START_DATE_STR).getTime();
        long endTime = System.currentTimeMillis();

        // 1. WARM-UP
        LOG.info("🔥 START WARM-UP (Previous Day Data)...");
        long warmUpTimestamp = startTime - Utils.TIME_DAY;
        TreeMap<Long, Map<String, KlineObjectSimple>> warmUpData =
                DataManagerAerospikeFloatSim.readDataFromAerospike1M(warmUpTimestamp);
        if (warmUpData != null) {
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : warmUpData.entrySet()) {
                featureExtractor.updateMarketHistory(entry.getValue());
            }
            LOG.info("✅ Warm-up Finished.");
        }

        // 2. MAIN LOOP
        long currentTime = startTime;
        LOG.info("🚀 STARTING COMPARISON: PREDICT & FEATURES (STRICT MODE)");

        AtomicInteger totalMatched = new AtomicInteger(0);
        AtomicInteger diffPredict = new AtomicInteger(0);
        AtomicInteger diffFeatures = new AtomicInteger(0);

        String loadedDateKey = "";
        TreeMap<Long, Map<String, KlineObjectSimple>> currentDailyData = null;

        while (currentTime <= endTime) {
            String currentDateKey = Utils.normalizeDateYYYYMMDD(currentTime);

            // Load Data theo ngày
            if (!currentDateKey.equals(loadedDateKey)) {
                LOG.info("📥 Processing Day: {}", currentDateKey);
                if (currentDailyData != null) { currentDailyData.clear(); currentDailyData = null; }
                currentDailyData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                loadedDateKey = currentDateKey;
            }

            if (currentDailyData != null && currentDailyData.containsKey(currentTime)) {
                Map<String, KlineObjectSimple> marketSnapshot = currentDailyData.get(currentTime);
                MarketRateChange rateChange = time2Rate.get(currentTime);
                if (rateChange == null) rateChange = new MarketRateChange(0.0, 0.0, 0.0);

                // A. TẠO TEST FEATURES & PREDICT
                MarketFeatures testFeatures = featureExtractor.extractAllFeatures(
                        currentTime, marketSnapshot, rateChange, new ArrayList<>());

                OnnxInferenceManager.PredictionResult testResult = aiBrain.predictAll(testFeatures);

                // B. SO SÁNH VỚI PRODUCTION
                String basePath = PROD_DIR + currentDateKey + "/" + currentTime;
                File prodPredFile = new File(basePath);           // File Predict
                File prodFeatFile = new File(basePath + ".features"); // File Features

                boolean hasProdData = false;

                if (prodPredFile.exists()) {
                    hasProdData = true;
                    try {
                        // 1. So sánh Prediction
                        OnnxInferenceManager.PredictionResult prodResult =
                                (OnnxInferenceManager.PredictionResult) StorageSnappy.readObjectFromFile(prodPredFile.getPath());

                        boolean predMatch = comparePrediction(currentTime, prodResult, testResult);
                        if (!predMatch) diffPredict.incrementAndGet();

                        // 2. So sánh Features (Nếu có file)
                        if (prodFeatFile.exists()) {
                            MarketFeatures prodFeatures =
                                    (MarketFeatures) StorageSnappy.readObjectFromFile(prodFeatFile.getPath());

                            boolean featMatch = compareFeatures(currentTime, prodFeatures, testFeatures);
                            if (!featMatch) diffFeatures.incrementAndGet();

                            if (predMatch && featMatch) totalMatched.incrementAndGet();
                        } else {
                            if (predMatch) totalMatched.incrementAndGet(); // Tạm tính match nếu thiếu file feature
                        }

                    } catch (Exception e) {
                        LOG.error("Error reading prod files at {}", currentTime, e);
                    }
                }

                // Lưu kết quả Test (để debug offline nếu cần)
                if (hasProdData) saveTestResult(currentTime, testResult, testFeatures);
            }
            currentTime += Utils.TIME_MINUTE;
        }

        LOG.info("=== FINAL REPORT ===");
        LOG.info("✅ Perfect Matches: {}", totalMatched.get());
        LOG.info("❌ Diff Prediction: {}", diffPredict.get());
        LOG.info("❌ Diff Features  : {}", diffFeatures.get());
    }

    // --- LOGIC SO SÁNH FEATURES (REFLECTION) ---
    private boolean compareFeatures(long time, MarketFeatures prod, MarketFeatures test) {
        boolean isMatch = true;
        StringBuilder diffLog = new StringBuilder();
        double delta = 0.0001; // Chấp nhận sai số nhỏ

        try {
            // Duyệt qua tất cả các field của MarketFeatures
            for (Field field : MarketFeatures.class.getFields()) {
                Object valProd = field.get(prod);
                Object valTest = field.get(test);

                // Bỏ qua các field không quan trọng hoặc null
                if (valProd == null || valTest == null) continue;

                if (field.getType() == double.class || field.getType() == Double.class) {
                    double d1 = ((Number) valProd).doubleValue();
                    double d2 = ((Number) valTest).doubleValue();
                    if (Math.abs(d1 - d2) > delta) {
                        isMatch = false;
                        diffLog.append(String.format("\n   - %s: Prod=%.4f vs Test=%.4f", field.getName(), d1, d2));
                    }
                } else if (field.getType() == int.class || field.getType() == Integer.class) {
                    int i1 = ((Number) valProd).intValue();
                    int i2 = ((Number) valTest).intValue();
                    if (i1 != i2) {
                        isMatch = false;
                        diffLog.append(String.format("\n   - %s: Prod=%d vs Test=%d", field.getName(), i1, i2));
                    }
                }
                // Có thể thêm check String/List nếu cần
            }
        } catch (IllegalAccessException e) {
            e.printStackTrace();
            return false;
        }

        if (!isMatch) {
            LOG.info("❌ FEATURES DIFF at {}: {}", time, diffLog.toString());
        }
        return isMatch;
    }

    private boolean comparePrediction(long timestamp, OnnxInferenceManager.PredictionResult prod, OnnxInferenceManager.PredictionResult test) {
        double delta = 0.0001;
        boolean match = Math.abs(prod.return1H - test.return1H) < delta
                && Math.abs(prod.riskDrawdown4H - test.riskDrawdown4H) < delta;

        if (!match) {
            LOG.info("❌ PREDICT DIFF at {}: Prod[1H:{}%] vs Test[1H:{}%]",
                    timestamp, Utils.formatPercent(prod.return1H), Utils.formatPercent(test.return1H));
        }
        return match;
    }

    private void saveTestResult(long timestamp, OnnxInferenceManager.PredictionResult res, MarketFeatures feat) {
        try {
            String dateStr = Utils.normalizeDateYYYYMMDD(timestamp);
            String folder = TEST_DIR + dateStr + "/";
            new File(folder).mkdirs();
            StorageSnappy.writeObject2File(folder + timestamp, res);
            StorageSnappy.writeObject2File(folder + timestamp + ".features", feat);
        } catch (Exception e) { e.printStackTrace(); }
    }

    private void initSystem() throws Exception {
        FundingFeeManager.getInstance();
        this.aiBrain = new OnnxInferenceManager(MODEL_DIR);
        this.featureExtractor = new ComprehensiveMarketFeatureExtractor();
        if (new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) {
            this.time2Rate = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
        } else {
            this.time2Rate = new TreeMap<>();
        }
    }
}