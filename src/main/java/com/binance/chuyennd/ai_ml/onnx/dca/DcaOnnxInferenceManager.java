package com.binance.chuyennd.ai_ml.onnx.dca;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.ai_ml.features.export.dca.DcaMarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.FloatBuffer;
import java.util.Collections;

public class DcaOnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(DcaOnnxInferenceManager.class);
    private final OrtEnvironment env;

    // Các Session đơn lẻ (XGBoost Ultimate Only)
    private OrtSession sessionRisk;
    private OrtSession sessionReward;
    private OrtSession sessionPump;
    private OrtSession sessionDump;

    private static final String INPUT_NODE = "float_input";

    public DcaOnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing DCA AI (XGBoost Ultimate) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();

        // Tối ưu hoá mức cao nhất cho Inference
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1); // Single thread mỗi session để tiết kiệm CPU cho việc khác

        // --- LOAD 4 MODEL XGBOOST CHÍNH ---
        // Tên file phải khớp với code Python output
        this.sessionRisk = loadSession(modelDir, "Model_Risk.onnx", opts);
        this.sessionReward = loadSession(modelDir, "Model_Reward.onnx", opts);
        this.sessionPump = loadSession(modelDir, "Model_Pump.onnx", opts);
        this.sessionDump = loadSession(modelDir, "Model_Dump.onnx", opts);

        if (sessionRisk == null || sessionReward == null || sessionPump == null || sessionDump == null) {
            LOG.warn("⚠️ Warning: Some AI models failed to load. Predictions may be incomplete.");
        } else {
            LOG.info("✅ All 4 XGBoost Models Loaded Successfully.");
        }
    }

    private OrtSession loadSession(String dir, String fileName, OrtSession.SessionOptions opts) {
        try {
            String path = dir + "/" + fileName;
            java.io.File f = new java.io.File(path);
            if (f.exists()) {
                LOG.info("  + Loaded: {}", fileName);
                return env.createSession(path, opts);
            } else {
                LOG.error("  ❌ Missing Model File: {}", path);
                return null;
            }
        } catch (Exception e) {
            LOG.error("  ❌ Error loading {}: {}", fileName, e.getMessage());
            return null;
        }
    }

    public DcaPredictionResult predict(DcaMarketFeatures f) {
        try {
            float[] rawFeatures = extractFeaturesToArray(f);

            // Chạy Inference đơn lẻ
            float risk = runRegression(sessionRisk, rawFeatures, -0.1f); // Default risk -10%
            float reward = runRegression(sessionReward, rawFeatures, 0.05f); // Default reward 5%
            float pump = runClassification(sessionPump, rawFeatures);
            float dump = runClassification(sessionDump, rawFeatures);

            return new DcaPredictionResult(risk, reward, pump, dump);

        } catch (Exception e) {
            // e.printStackTrace(); // Uncomment để debug nếu cần
            // Trả về giá trị an toàn nếu lỗi: Không Pump, Không Dump, Risk nhẹ
            return new DcaPredictionResult(0f, 0f, 0f, 0f);
        }
    }

    // Hàm chạy cho Risk/Reward (Output là giá trị thực)
    private float runRegression(OrtSession session, float[] features, float defaultValue) {
        if (session == null) return defaultValue;
        try (OrtSession.Result result = runSession(session, features)) {
            float[][] output = (float[][]) result.get(0).getValue();
            return output[0][0];
        } catch (Exception e) {
            return defaultValue;
        }
    }

    // Hàm chạy cho Pump/Dump (Output là xác suất lớp 1)
    private float runClassification(OrtSession session, float[] features) {
        if (session == null) return 0.0f;
        try (OrtSession.Result result = runSession(session, features)) {
            // XGBoost Classifier ONNX output:
            // Node 0: Label dự đoán (0 hoặc 1) -> Không dùng
            // Node 1: Probabilities (List Map hoặc Tensor) -> Dùng cái này

            Object val = result.get(1).getValue();

            if (val instanceof float[][]) {
                // Trường hợp output là Tensor [1, 2] (Class 0, Class 1)
                return ((float[][]) val)[0][1];
            } else {
                // Trường hợp thư viện cũ trả về dạng khác, mặc định 0
                return 0.0f;
            }
        } catch (Exception e) {
            return 0.0f;
        }
    }

    private OrtSession.Result runSession(OrtSession session, float[] features) throws OrtException {
        // Tạo Tensor đầu vào [1, n_features]
        long[] shape = new long[]{1, features.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(features), shape);
        return session.run(Collections.singletonMap(INPUT_NODE, inputTensor));
    }

    // Map 41 Features từ Object sang mảng float (Thứ tự phải khớp tuyệt đối với Python training)
    private float[] extractFeaturesToArray(DcaMarketFeatures f) {
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
        if (sessionRisk != null) sessionRisk.close();
        if (sessionReward != null) sessionReward.close();
        if (sessionPump != null) sessionPump.close();
        if (sessionDump != null) sessionDump.close();
        if (env != null) env.close();
    }
}