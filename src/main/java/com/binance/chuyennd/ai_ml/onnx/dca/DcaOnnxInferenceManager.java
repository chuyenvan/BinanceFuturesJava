package com.binance.chuyennd.ai_ml.onnx.dca;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.ai_ml.features.export.dca.DcaMarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.FloatBuffer;
import java.util.*;

public class DcaOnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(DcaOnnxInferenceManager.class);
    private final OrtEnvironment env;

    // Định nghĩa cấu trúc lưu Session kèm Trọng số (Weight)
    private static class ModelSession {
        OrtSession session;
        float weight;
        String name;

        public ModelSession(OrtSession session, float weight, String name) {
            this.session = session;
            this.weight = weight;
            this.name = name;
        }
    }

    // Danh sách Ensemble cho từng loại
    private final List<ModelSession> modelsRisk = new ArrayList<>();
    private final List<ModelSession> modelsReward = new ArrayList<>();
    private final List<ModelSession> modelsPump = new ArrayList<>();
    private final List<ModelSession> modelsDump = new ArrayList<>();

    private static final String INPUT_NODE = "float_input";

    public DcaOnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing DCA AI (Optimized Edition) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1);

        // --- CẤU HÌNH TRỌNG SỐ DỰA TRÊN TRAINING LOG ---

        // 1. RISK: LightGBM (RMSE 0.0444) tốt hơn XGB (0.0445) một chút
        loadModel(modelDir, "LGBM_Risk.onnx", 1.5f, modelsRisk, opts);  // Trọng số cao hơn
        loadModel(modelDir, "XGB_Risk.onnx", 1.0f, modelsRisk, opts);

        // 2. REWARD: LightGBM (0.2057) tốt hơn XGB (0.2065)
        loadModel(modelDir, "LGBM_Reward.onnx", 1.5f, modelsReward, opts);
        loadModel(modelDir, "XGB_Reward.onnx", 1.0f, modelsReward, opts);

        // 3. PUMP: XGBoost (AUC 0.861) tốt hơn LightGBM (0.858)
        loadModel(modelDir, "XGB_Pump.onnx", 1.5f, modelsPump, opts);   // Ưu tiên XGB bắt Pump
        loadModel(modelDir, "LGBM_Pump.onnx", 1.0f, modelsPump, opts);

        // 4. DUMP: Cả 2 đều cực tốt (AUC > 0.975). Dùng cả 2 để chắc chắn.
        loadModel(modelDir, "XGB_Dump.onnx", 1.0f, modelsDump, opts);
        loadModel(modelDir, "LGBM_Dump.onnx", 1.0f, modelsDump, opts);

        // LƯU Ý: Đã loại bỏ hoàn toàn CatBoost để tiết kiệm ~10GB RAM

        LOG.info("✅ AI Loaded. Performance Optimized.");
    }

    private void loadModel(String dir, String fileName, float weight, List<ModelSession> targetList, OrtSession.SessionOptions opts) {
        try {
            String path = dir + "/" + fileName;
            java.io.File f = new java.io.File(path);
            if (f.exists()) {
                targetList.add(new ModelSession(env.createSession(path, opts), weight, fileName));
                LOG.info("  + Loaded: {} (Weight: {})", fileName, weight);
            } else {
                LOG.warn("  - Missing: {} (Skipping, auto-rebalance weights)", fileName);
            }
        } catch (Exception e) {
            LOG.error("  x Error loading {}: {}", fileName, e.getMessage());
        }
    }

    public DcaPredictionResult predict(DcaMarketFeatures f) {
        try {
            float[] rawFeatures = extractFeaturesToArray(f);

            // Tính trung bình có trọng số (Weighted Ensemble)
            float risk = runWeightedRegression(modelsRisk, rawFeatures, -1.0f);
            float reward = runWeightedRegression(modelsReward, rawFeatures, 0.0f);
            float pump = runWeightedClassification(modelsPump, rawFeatures);
            float dump = runWeightedClassification(modelsDump, rawFeatures);

            return new DcaPredictionResult(risk, reward, pump, dump);

        } catch (Exception e) {
            LOG.error("❌ Inference Error: {}", e.getMessage());
            return new DcaPredictionResult(-1f, 0f, 0f, 1f);
        }
    }

    // Hàm tính Regression (Risk/Reward) theo trọng số
    private float runWeightedRegression(List<ModelSession> models, float[] features, float defaultValue) {
        if (models.isEmpty()) return defaultValue;

        float totalValue = 0;
        float totalWeight = 0;

        for (ModelSession ms : models) {
            try (OrtSession.Result result = runSession(ms.session, features)) {
                float[][] output = (float[][]) result.get(0).getValue();
                float val = output[0][0];

                totalValue += val * ms.weight;
                totalWeight += ms.weight;
            } catch (Exception e) {
                LOG.error("Error running {}: {}", ms.name, e.getMessage());
            }
        }
        return totalWeight > 0 ? totalValue / totalWeight : defaultValue;
    }

    // Hàm tính Classification (Pump/Dump) theo trọng số
    private float runWeightedClassification(List<ModelSession> models, float[] features) {
        if (models.isEmpty()) return 0.0f;

        float totalProb = 0;
        float totalWeight = 0;

        for (ModelSession ms : models) {
            try (OrtSession.Result result = runSession(ms.session, features)) {
                // Lấy xác suất lớp 1 (Positive)
                // XGBoost/LGBM ONNX thường trả về output[1] là một list map hoặc tensor array
                // Code check này xử lý trường hợp output là Tensor float[][]
                Object val = result.get(1).getValue();
                float prob = 0.0f;

                if (val instanceof float[][]) {
                    prob = ((float[][]) val)[0][1]; // Index 1 = Lớp "Có" (Pump/Dump)
                }

                totalProb += prob * ms.weight;
                totalWeight += ms.weight;
            } catch (Exception e) {
                LOG.error("Error running {}: {}", ms.name, e.getMessage());
            }
        }
        return totalWeight > 0 ? totalProb / totalWeight : 0.0f;
    }

    private OrtSession.Result runSession(OrtSession session, float[] features) throws OrtException {
        long[] shape = new long[]{1, features.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(features), shape);
        return session.run(Collections.singletonMap(INPUT_NODE, inputTensor));
    }

    private float[] extractFeaturesToArray(DcaMarketFeatures f) {
        // Copy lại hàm extract feature 41 cột của bạn vào đây
        return new float[] {
                (float)f.distFromHigh24H, (float)f.distMA20, (float)f.instantAlpha, (float)f.recoveryElasticity,
                (float)f.crashVelocity, (float)f.globalRateDownAvg, (float)f.advanceDeclineRatio, (float)f.btcDominance, (float)f.marketBreadthStrength,
                (float)f.btcMomentum15M, (float)f.btcMomentum1H, (float)f.btcMomentum4H, (float)f.btcMomentum24H, (float)f.btcMomentumAcceleration,
                (float)f.ethMomentum15M, (float)f.ethMomentum4H,
                (float)f.momentum15M, (float)f.momentum1H, (float)f.momentum4H, (float)f.momentum24H,
                (float)f.rsi1H, (float)f.rsiChange, (float)f.volumeAnomaly, (float)f.volumeRatio15M_24H,
                (float)f.distFromLow24H, (float)f.maxRateChange60M, (float)f.volatilityShock, (float)f.volatilityTermStructure,
                (float)f.basketMomentum15M, (float)f.basketMomentum1H, (float)f.basketMomentum24H, (float)f.basketRsi14, (float)f.basketVolSpike,
                (float)f.coinFundingRate, (float)f.fundingRateRaw, (float)f.fundingRateAvg24H, (float)f.fundingRateTrend,
                (float)f.hourOfDay, (float)f.dayOfWeek, (float)f.weekOfMonth, (float)f.monthOfYear
        };
    }

    @Override
    public void close() throws Exception {
        for (ModelSession ms : modelsRisk) ms.session.close();
        for (ModelSession ms : modelsReward) ms.session.close();
        for (ModelSession ms : modelsPump) ms.session.close();
        for (ModelSession ms : modelsDump) ms.session.close();
        if (env != null) env.close();
    }
}