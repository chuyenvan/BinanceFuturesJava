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

    // Các bộ dự đoán
    // P: Profit (Dùng Model V4 Sideway)
    private final SinglePredictor p15M, p1H, p4H, p24H;
    // R: Risk (Dùng Model V3.0 Trend/Full)
    private final SinglePredictor pRisk4H, pRisk24H;

    public OnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing Hybrid AI Brain (V4 Sideway + V3.0 Trend) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        this.opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1); // Tối ưu CPU

        // 1. Load Model Lợi Nhuận (V4 Sideway - Tên file Model_Sideway_...)
        this.p15M = new SinglePredictor(modelDir, "Return15M", "Sideway");
        this.p1H = new SinglePredictor(modelDir, "Return1H", "Sideway");
        this.p4H = new SinglePredictor(modelDir, "Return4H", "Sideway");
        this.p24H = new SinglePredictor(modelDir, "Return24H", "Sideway");

        // 2. Load Model Rủi Ro (V3.0 Trend - Tên file Model_Regressor_...)
        this.pRisk4H = new SinglePredictor(modelDir, "maxDrawdownNext4H", "Regressor"); // Drawdown dùng model cũ
        this.pRisk24H = new SinglePredictor(modelDir, "maxDrawdownNext24H", "Regressor");

        LOG.info("✅ All Hybrid Models loaded successfully!");
    }

    public PredictionResult predictAll(MarketFeatures f) {
        try {
            // 1. Chuẩn bị 2 bộ dữ liệu khác nhau
            float[] featuresV4 = extractFeaturesV4Sideway(f); // Cho Return
            float[] featuresV3 = extractFeaturesV3Full(f);    // Cho Risk

            // 2. Dự đoán
            float r15 = p15M.predict(featuresV4);
            float r1 = p1H.predict(featuresV4);
            float r4 = p4H.predict(featuresV4);
            float r24 = p24H.predict(featuresV4);

            float risk4 = pRisk4H.predict(featuresV3);
            float risk24 = pRisk24H.predict(featuresV3);

            return new PredictionResult(r15, r1, r4, r24, risk4, risk24);
        } catch (Exception e) {
            LOG.error("❌ Inference Error", e);
            return new PredictionResult(0, 0, 0, 0, 0, 0);
        }
    }

    /**
     * TRÍCH XUẤT FEATURES CHO MODEL V4 (SIDEWAY)
     * Logic: Tính toán các chỉ số phái sinh (Bollinger Pos, Compression...) ngay tại đây
     * Danh sách 22 features (Khớp với code Python V4 Final)
     */
    private float[] extractFeaturesV4Sideway(MarketFeatures f) {
        // Tính toán các biến phái sinh (Derived Features)
        float volatility1H = (float) f.volatility1H;
        float volatility24H = (float) f.volatility24H;
        float distMA20 = (float) f.distMA20;

        // Tránh chia cho 0
        float epsilon = 1e-6f;

        // A. Bollinger Position
        float bollinger_pos = distMA20 / (volatility1H + epsilon);

        // B. Volatility Compression
        float vol_compression = volatility24H / (volatility1H + epsilon);
        float vol_term_structure = volatility1H / (volatility24H + epsilon);

        // C. RSI Reversion
        float rsi_reversion = Math.abs((float) f.rsi14 - 50f);

        // D. Basket Divergence
        float basket_divergence = (float) f.momentum15M - (float) f.basketMomentum15M;

        return new float[] {
                // --- Nhóm Mean Reversion ---
                distMA20,                       // 1
                (float) f.percentAboveMA20,     // 2
                (float) f.rsi14,                // 3
                rsi_reversion,                  // 4 (Calculated)
                bollinger_pos,                  // 5 (Calculated)

                // --- Nhóm Volatility ---
                (float) f.volatility15M,        // 6
                volatility1H,                   // 7
                volatility24H,                  // 8
                vol_compression,                // 9 (Calculated)
                vol_term_structure,             // 10 (Calculated)
                (float) f.volatility1M,         // 11

                // --- Nhóm Market Breadth ---
                (float) f.marketBreadthStrength,// 12
                (float) f.advanceDeclineRatio,  // 13
                (float) f.btcDominance,         // 14
                basket_divergence,              // 15 (Calculated)
                (float) f.basketRsi14,          // 16

                // --- Nhóm Momentum ---
                (float) f.momentum15M,          // 17
                (float) f.momentum1H,           // 18
                (float) f.fundingRateRaw,       // 19
                (float) f.fundingRateAvg24H,    // 20

                // --- Time ---
                (float) f.hourOfDay,            // 21
                (float) f.dayOfWeek             // 22
        };
    }

    /**
     * TRÍCH XUẤT FEATURES CHO MODEL V3 (RISK/TREND)
     * Giữ nguyên logic cũ (33 features)
     */
    private float[] extractFeaturesV3Full(MarketFeatures f) {
        return new float[] {
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
        if (p1H != null) p1H.close();
        if (p4H != null) p4H.close();
        if (p24H != null) p24H.close();
        if (pRisk4H != null) pRisk4H.close();
        if (pRisk24H != null) pRisk24H.close();
        if (env != null) env.close();
    }

    public static class PredictionResult implements Serializable {
        public float return15M, return1H, return4H, return24H;
        public float riskDrawdown4H, riskDrawdown24H;
        public PredictionResult(float r15, float r1, float r4, float r24, float risk4, float risk24) {
            this.return15M = r15; this.return1H = r1; this.return4H = r4;
            this.return24H = r24; this.riskDrawdown4H = risk4; this.riskDrawdown24H = risk24;
        }

        @Override
        public String toString() {
            return String.format("[15M:%.2f%% 1H:%.2f%% 4H:%.2f%% | Risk4H:%.2f%%]",
                    return15M*100, return1H*100, return4H*100, riskDrawdown4H*100);
        }
    }
}