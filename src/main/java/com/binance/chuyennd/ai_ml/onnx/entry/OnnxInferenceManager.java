package com.binance.chuyennd.ai_ml.onnx.entry;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.Serializable;
import java.nio.FloatBuffer;
import java.util.*;

public class OnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(OnnxInferenceManager.class);
    private final OrtEnvironment env;
    private final OrtSession.SessionOptions opts;

    // Các bộ dự đoán — CẢ HAI hiện chạy feature set V3 Full (33 feat); xem predictAll().
    // (Model V4 Sideway/30-feat từng được cân nhắc nhưng KHÔNG dùng — đã gỡ extractFeaturesV4Sideway.)
    // P: Return15M
    private final SinglePredictor p15M;
    // R: Risk (maxDrawdownNext4H)
    private final SinglePredictor pRisk4H;

    public OnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing AI Brain (V3 Full features) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        this.opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1); // Tối ưu CPU

        // Lưu ý: Python script lưu tên file là "Model_Regressor_..." cho tất cả các target
        // Ví dụ: Model_Regressor_return15M.onnx
        // Nên ta truyền typePrefix là "Regressor" cho tất cả.

        // 1. Load Model Lợi Nhuận (đã BỎ model 24H — predReturn24H không còn dùng)
        this.p15M = new SinglePredictor(modelDir, "futureReturn15M", "Regressor");
        // 2. Load Model Rủi Ro
        this.pRisk4H = new SinglePredictor(modelDir, "maxDrawdownNext4H", "Regressor");


        LOG.info("✅ All Models loaded successfully!");
    }

    public PredictionResult predictAll(MarketFeatures f) {
        try {
            // CẢ return15M lẫn risk4H dùng chung feature set V3 Full (33 feat) — khớp model live đang chạy.
            float[] featuresV3 = extractFeaturesV3Full(f);

            float r15 = p15M.predict(featuresV3);
            float risk4 = pRisk4H.predict(featuresV3);

            return new PredictionResult(r15, risk4);
        } catch (Exception e) {
            LOG.error("❌ Inference Error", e);
            return new PredictionResult(0, 0);
        }
    }

    /**
     * TRÍCH XUẤT FEATURES CHO MODEL V3 (RISK/TREND/RETURN)
     * Giữ nguyên logic cũ (33 features)
     */
    private float[] extractFeaturesV3Full(MarketFeatures f) {
        return new float[]{
                (float) f.momentum1M, (float) f.momentum5M, (float) f.momentum15M, (float) f.momentum1H,
                (float) f.momentum4H, (float) f.momentum24H, (float) f.momentumAcceleration,
                (float) f.trendStrengthETH, (float) f.trendConsistency,
                (float) f.volatility1M, (float) f.volatility15M, (float) f.volatility1H,
                (float) f.volatility24H, (float) f.volatilityTermStructure,
                (float) f.advanceDeclineRatio, (float) f.percentAboveMA20, (float) f.volumeRatioUpDown,
                (float) f.marketBreadthStrength, (float) f.btcDominance,
                (float) f.rsi14, (float) f.volumeSpike, (float) f.distMA20,
                (float) f.fundingRateRaw, (float) f.fundingRateAvg24H, (float) f.fundingRateTrend,
                (float) f.hourOfDay, (float) f.dayOfWeek, (float) f.weekOfMonth, (float) f.monthOfYear,
                (float) f.basketMomentum15M, (float) f.basketMomentum1H, (float) f.basketRsi14, (float) f.basketVolSpike
        };
    }

    /**
     * Class nội bộ xử lý logic Single Model (Scaler -> Model)
     */
    private class SinglePredictor {
        private OrtSession scaler;
        private OrtSession model;
        private final String targetName;

        public SinglePredictor(String dir, String target, String typePrefix) {
            this.targetName = target;
            try {
                // Tên file Scaler: Scaler_Sideway_Return15M.onnx hoặc Scaler_Return15M.onnx (tuỳ prefix)
                String prefix = typePrefix.equals("Regressor") ? "" : typePrefix + "_";
                // Logic clean name: Nếu là Regressor (V3) thì để trống prefix (vì file cũ là Scaler_Return...)
                // Nếu là Sideway (V4) thì file là Scaler_Sideway_Return...

                // Tuy nhiên, theo code python V4: f"Scaler_Sideway_{clean_name}.onnx"
                // Theo code python V3: f"Scaler_{clean_name}.onnx"

                String cleanTarget = target.replace("future", "").replace("Next", "");
                String scalerFileName = "Scaler_" + (typePrefix.equals("Regressor") ? "" : typePrefix + "_") + cleanTarget + ".onnx";
                String modelFileName = "Model_" + (typePrefix.equals("Regressor") ? "Regressor" : typePrefix) + "_" + cleanTarget + ".onnx";

                // 1. Load Scaler
                String scalerPath = dir + "/" + scalerFileName;
                if (fileExists(scalerPath)) {
                    this.scaler = env.createSession(scalerPath, opts);
                } else {
                    LOG.warn("⚠️ Scaler missing: {}", scalerPath);
                }

                // 2. Load Model
                String modelPath = dir + "/" + modelFileName;
                if (fileExists(modelPath)) {
                    this.model = env.createSession(modelPath, opts);
                    LOG.info("  -> Loaded {} Model for {}", typePrefix, target);
                } else {
                    LOG.error("❌ Model missing: {}", modelPath);
                }

            } catch (Exception e) {
                LOG.error("  -> Failed to load predictor for " + target, e);
            }
        }

        public float predict(float[] rawFeatures) throws OrtException {
            if (model == null) return 0f;

            float[] inputForModel = rawFeatures;

            // 1. Scale dữ liệu
            if (scaler != null) {
                float[][] scaledOutput = runModel(scaler, rawFeatures);
                if (scaledOutput != null && scaledOutput.length > 0) {
                    inputForModel = scaledOutput[0];
                }
            }

            // 2. Chạy model chính
            float[][] result = runModel(model, inputForModel);
            if (result != null && result.length > 0) {
                return result[0][0];
            }
            return 0f;
        }

        private float[][] runModel(OrtSession session, float[] inputData) throws OrtException {
            long[] shape = new long[]{1, inputData.length};
            try (OnnxTensor tensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(inputData), shape)) {
                String inputName = session.getInputNames().iterator().next();
                try (OrtSession.Result res = session.run(Collections.singletonMap(inputName, tensor))) {
                    return (float[][]) res.get(0).getValue();
                }
            }
        }

        public void close() throws OrtException {
            if (scaler != null) scaler.close();
            if (model != null) model.close();
        }
    }

    private boolean fileExists(String path) {
        return new File(path).exists();
    }

    @Override
    public void close() throws Exception {
        if (p15M != null) p15M.close();
        if (pRisk4H != null) pRisk4H.close();
        if (env != null) env.close();
    }

    public static class PredictionResult implements Serializable {
        public float return15M;
        public float riskDrawdown4H;

        public PredictionResult(float return15M, float riskDrawdown4H) {
            this.return15M = return15M;
            this.riskDrawdown4H = riskDrawdown4H;
        }

        @Override
        public String toString() {
            return String.format("[15M:%.2f%% | Risk4H:%.2f%%]",
                    return15M * 100, riskDrawdown4H * 100);
        }
    }
}