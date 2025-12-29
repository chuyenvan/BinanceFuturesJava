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
import java.util.Map;

public class DcaOnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(DcaOnnxInferenceManager.class);
    private final OrtEnvironment env;

    // 4 Sessions cho 4 Models (Ultimate Ensemble)
    private final OrtSession sessionRisk;   // Regression: Max Drop
    private final OrtSession sessionReward; // Regression: Max Rise
    private final OrtSession sessionPump;   // Classification: Pump > 20%
    private final OrtSession sessionDump;   // Classification: Dump > 30%

    private static final String INPUT_NODE = "float_input";

    public DcaOnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing DCA AI Brain (Quad-Core Models) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();

        // Tối ưu hóa Inference
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1); // Mỗi model dùng 1 thread để chạy song song hiệu quả hơn

        // 1. Load Model Risk
        this.sessionRisk = loadSession(modelDir, "Model_Risk.onnx", opts);

        // 2. Load Model Reward
        this.sessionReward = loadSession(modelDir, "Model_Reward.onnx", opts);

        // 3. Load Model Pump
        this.sessionPump = loadSession(modelDir, "Model_Pump.onnx", opts);

        // 4. Load Model Dump
        this.sessionDump = loadSession(modelDir, "Model_Dump.onnx", opts);

        LOG.info("✅ DCA Quad-Core Models loaded successfully!");
    }

    private OrtSession loadSession(String dir, String fileName, OrtSession.SessionOptions opts) {
        try {
            String path = dir + "/" + fileName;
            LOG.info("Loading Model: {}", path);
            return env.createSession(path, opts);
        } catch (Exception e) {
            LOG.warn("⚠️ Warning: Could not load model {}. Feature will be disabled.", fileName);
            return null;
        }
    }

    public DcaPredictionResult predict(DcaMarketFeatures f) {
        try {
            // Trích xuất features thô (41 features - Khớp với Python)
            float[] rawFeatures = extractFeaturesToArray(f);

            // Chạy Inference
            float predictedDD = runRegression(sessionRisk, rawFeatures, -1.0f);
            float predictedRise = runRegression(sessionReward, rawFeatures, 0.0f);
            float probPump = runClassification(sessionPump, rawFeatures);
            float probDump = runClassification(sessionDump, rawFeatures);

            return new DcaPredictionResult(predictedDD, predictedRise, probPump, probDump);

        } catch (Exception e) {
            LOG.error("❌ DCA Inference Error: {}", e.getMessage());
            return new DcaPredictionResult(-1.0f, 0.0f, 0.0f, 1.0f); // Default: Rất nguy hiểm
        }
    }

    private float runRegression(OrtSession session, float[] features, float defaultValue) {
        if (session == null) return defaultValue;
        try (OrtSession.Result result = runSession(session, features)) {
            float[][] output = (float[][]) result.get(0).getValue();
            return output[0][0];
        } catch (Exception e) {
            return defaultValue;
        }
    }

    private float runClassification(OrtSession session, float[] features) {
        if (session == null) return 0.0f;
        try (OrtSession.Result result = runSession(session, features)) {
            // XGBoost Classifier thường trả về [1][1] là xác suất lớp 1 (nếu binary:logistic)
            // Hoặc [1][2] (lớp 0, lớp 1) nếu multi:softprob.
            // Với code Python binary:logistic output là xác suất lớp 1.
            float[][] output = (float[][]) result.get(1).getValue(); // Index 1 thường là probabilities map
            // Tuy nhiên với ONNX export từ XGBoost, output 0 là label, output 1 là probability map
            // Để an toàn và đơn giản với float_input tensor, ta check output shape.

            // Cách xử lý an toàn cho Binary Classification ONNX:
            // Output thường là float array xác suất.
            Object val = result.get(1).getValue();
            if (val instanceof float[][]) {
                // Check shape
                return ((float[][]) val)[0][1]; // Lấy xác suất của class 1 (Positive)
            }
            return 0.0f;
        } catch (Exception e) {
            // Fallback nếu cấu trúc ONNX khác biệt (ví dụ chỉ trả về label)
            return 0.0f;
        }
    }

    private OrtSession.Result runSession(OrtSession session, float[] features) throws OrtException {
        long[] shape = new long[]{1, features.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(features), shape);
        Map<String, OnnxTensor> inputs = Collections.singletonMap(INPUT_NODE, inputTensor);
        return session.run(inputs);
    }

    // 🔥 CẬP NHẬT: 41 FEATURES (Khớp 100% với Header Python mới nhất)
    private float[] extractFeaturesToArray(DcaMarketFeatures f) {
        return new float[] {
                // 1. Market Position (2)
                (float) f.distFromHigh24H,
                (float) f.distMA20,

                // 2. Rel Strength (2)
                (float) f.instantAlpha,
                (float) f.recoveryElasticity,

                // 3. Market Context (5)
                (float) f.crashVelocity,
                (float) f.globalRateDownAvg,
                (float) f.advanceDeclineRatio,
                (float) f.btcDominance,
                (float) f.marketBreadthStrength,

                // 4. Macro BTC (5)
                (float) f.btcMomentum15M,
                (float) f.btcMomentum1H,
                (float) f.btcMomentum4H,
                (float) f.btcMomentum24H,
                (float) f.btcMomentumAcceleration,

                // 5. Macro ETH (2)
                (float) f.ethMomentum15M,
                (float) f.ethMomentum4H,

                // 6. Coin Momentum (4)
                (float) f.momentum15M,
                (float) f.momentum1H,
                (float) f.momentum4H,
                (float) f.momentum24H,

                // 7. Technicals (8)
                (float) f.rsi1H,
                (float) f.rsiChange,
                (float) f.volumeAnomaly,
                (float) f.volumeRatio15M_24H,
                (float) f.distFromLow24H,
                (float) f.maxRateChange60M,
                (float) f.volatilityShock,
                (float) f.volatilityTermStructure,

                // 8. Basket (5)
                (float) f.basketMomentum15M,
                (float) f.basketMomentum1H,
                (float) f.basketMomentum24H,
                (float) f.basketRsi14,
                (float) f.basketVolSpike,

                // 9. Funding (4)
                (float) f.coinFundingRate,
                (float) f.fundingRateRaw,
                (float) f.fundingRateAvg24H,
                (float) f.fundingRateTrend,

                // 10. Time (4)
                (float) f.hourOfDay,
                (float) f.dayOfWeek,
                (float) f.weekOfMonth,
                (float) f.monthOfYear
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