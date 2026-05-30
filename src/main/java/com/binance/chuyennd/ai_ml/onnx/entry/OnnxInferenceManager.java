package com.binance.chuyennd.ai_ml.onnx.entry;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures15M;
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

    private final SinglePredictor p1H, p4H, pRisk4H;
    // 🔥 Chỉ cần 1 Scaler dùng chung cho cả 3 model (vì data đầu vào giống hệt nhau)
    private OrtSession sharedScaler;

    public OnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing AI Brain 15M from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        this.opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1);

        this.p1H = new SinglePredictor(modelDir, "futureReturn1H", "Regressor", env, opts);
        this.p4H = new SinglePredictor(modelDir, "futureReturn4H", "Regressor", env, opts);
        this.pRisk4H = new SinglePredictor(modelDir, "maxDrawdownNext4H", "Regressor", env, opts);

        // Load Shared Scaler (Lấy từ Return4H hoặc bất kỳ file Scaler nào vì chúng y hệt nhau)
        try {
            String scalerPath = new File(modelDir, "Scaler_Return4H.onnx").getAbsolutePath();
            if (new File(scalerPath).exists()) {
                this.sharedScaler = env.createSession(scalerPath, opts);
            }
        } catch (Exception e) {
            LOG.warn("⚠️ Không tìm thấy Shared Scaler, sẽ dự đoán bằng Raw Data.");
        }

        LOG.info("✅ All Models loaded successfully! Shared Scaler Active.");
    }

    public PredictionResult predictAll(MarketFeatures15M f) {
        try {
            float[] rawFeatures = extractFeaturesMarket15M(f);
            float[] scaledFeatures = rawFeatures; // Default

            // 🔥 TỐI ƯU 1: CHẠY SCALER ĐÚNG 1 LẦN DUY NHẤT
            if (this.sharedScaler != null) {
                float[][] scaledOutput = runModel(this.sharedScaler, rawFeatures);
                if (scaledOutput != null && scaledOutput.length > 0) {
                    scaledFeatures = scaledOutput[0];
                }
            }

            // 🔥 TỐI ƯU 2: NÉM DATA ĐÃ SCALE VÀO THẲNG MODEL (Bỏ qua khâu scale bên trong)
            float r1 = p1H.predictScaled(scaledFeatures);
            float r4 = p4H.predictScaled(scaledFeatures);
            float risk4 = pRisk4H.predictScaled(scaledFeatures);

            return new PredictionResult(r1, r4, risk4);
        } catch (Exception e) {
            LOG.error("❌ Inference Error", e);
            return new PredictionResult(0, 0, 0);
        }
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

    private float[] extractFeaturesMarket15M(MarketFeatures15M f) {
        float volRegimeNum = 1.0f; // NORMAL
        if ("LOW".equals(f.volatilityRegime)) volRegimeNum = 0.0f;
        else if ("HIGH".equals(f.volatilityRegime)) volRegimeNum = 2.0f;

        return new float[]{
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H,
                f.momentumAcceleration, f.trendStrengthETH, f.trendConsistency,
                f.volatility1H, f.volatility4H, f.volatility24H, f.volatilityTermStructure,
                f.advanceDeclineRatio, f.percentAboveMA20, f.volumeRatioUpDown,
                f.marketBreadthStrength, f.btcDominance, f.rsi14, f.volumeSpike,
                f.distMA20, f.basketMomentum1H, f.basketMomentum4H, f.basketRsi14,
                f.basketVolSpike, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend,
                (float) f.hourOfDay, (float) f.dayOfWeek, (float) f.weekOfMonth,
                (float) f.monthOfYear, volRegimeNum
        };
    }

    private class SinglePredictor {
        private OrtSession model;
        private final OrtEnvironment e;

        public SinglePredictor(String dir, String target, String typePrefix, OrtEnvironment env, OrtSession.SessionOptions opts) {
            this.e = env;
            try {
                String cleanTarget = target.replace("future", "").replace("Next", "");
                String modelFileName = "Model_" + (typePrefix.equals("Regressor") ? "Regressor" : typePrefix) + "_" + cleanTarget + ".onnx";
                String modelPath = new File(dir, modelFileName).getAbsolutePath();

                if (new File(modelPath).exists()) {
                    this.model = env.createSession(modelPath, opts);
                    LOG.info("  -> Loaded Model for {}", target);
                } else {
                    LOG.error("❌ Model missing: {}", modelPath);
                }
            } catch (Exception ex) {
                LOG.error("  -> Failed to load predictor for " + target, ex);
            }
        }

        public float predictScaled(float[] scaledInput) throws OrtException {
            if (model == null) return 0f;
            long[] shape = new long[]{1, scaledInput.length};
            try (OnnxTensor tensor = OnnxTensor.createTensor(e, FloatBuffer.wrap(scaledInput), shape)) {
                String inputName = model.getInputNames().iterator().next();
                try (OrtSession.Result res = model.run(Collections.singletonMap(inputName, tensor))) {
                    float[][] result = (float[][]) res.get(0).getValue();
                    return result[0][0];
                }
            }
        }

        public void close() throws OrtException {
            if (model != null) model.close();
        }
    }

    @Override
    public void close() throws Exception {
        if (p1H != null) p1H.close();
        if (p4H != null) p4H.close();
        if (pRisk4H != null) pRisk4H.close();
        if (sharedScaler != null) sharedScaler.close();
        if (env != null) env.close();
    }

    public static class PredictionResult implements Serializable {
        public float return1H, return4H, riskDrawdown4H;
        public PredictionResult(float r1H, float r4H, float dd4H) {
            this.return1H = r1H;
            this.return4H = r4H;
            this.riskDrawdown4H = dd4H;
        }
    }
}