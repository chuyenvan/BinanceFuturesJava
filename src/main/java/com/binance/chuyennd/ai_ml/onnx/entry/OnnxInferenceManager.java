package com.binance.chuyennd.ai_ml.onnx.entry;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.Serializable;
import java.nio.FloatBuffer;
import java.util.Collections;
import java.util.Map;

public class OnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(OnnxInferenceManager.class);
    private final OrtEnvironment env;

    // Sessions
    private final OrtSession sc15M, sc1H, sc4H, sc24H, scRisk4H, scRisk24H;
    private final OrtSession mod15M, mod1H, mod4H, mod24H, modRisk4H, modRisk24H;
    private static final String INPUT_NODE = "float_input";

    public OnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing AI Brain from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);

        // --- THÊM ĐOẠN NÀY ---
        // Giới hạn số luồng tính toán song song bên trong một operator (phép tính ma trận)
        opts.setIntraOpNumThreads(2);

        // Giới hạn số luồng chạy song song giữa các operator (thường để 1 hoặc 2)
        opts.setInterOpNumThreads(1);
        // ---------------------

        // Load Models & Scalers
        this.sc15M = env.createSession(modelDir + "/Scaler_Return15M.onnx", opts);
        this.mod15M = env.createSession(modelDir + "/Model_Regressor_Return15M.onnx", opts);
        this.sc1H = env.createSession(modelDir + "/Scaler_Return1H.onnx", opts);
        this.mod1H = env.createSession(modelDir + "/Model_Regressor_Return1H.onnx", opts);
        this.sc4H = env.createSession(modelDir + "/Scaler_Return4H.onnx", opts);
        this.mod4H = env.createSession(modelDir + "/Model_Regressor_Return4H.onnx", opts);
        this.sc24H = env.createSession(modelDir + "/Scaler_Return24H.onnx", opts);
        this.mod24H = env.createSession(modelDir + "/Model_Regressor_Return24H.onnx", opts);
        this.scRisk4H = env.createSession(modelDir + "/Scaler_maxDrawdown4H.onnx", opts);
        this.modRisk4H = env.createSession(modelDir + "/Model_Regressor_maxDrawdown4H.onnx", opts);
        this.scRisk24H = env.createSession(modelDir + "/Scaler_maxDrawdown24H.onnx", opts);
        this.modRisk24H = env.createSession(modelDir + "/Model_Regressor_maxDrawdown24H.onnx", opts);

        LOG.info("✅ All 12 ONNX files loaded successfully!");
    }

    public PredictionResult predictAll(MarketFeatures f) {
        try {
            float[] rawFeatures = extractFeaturesToArray(f);

            float p15m = runInference(sc15M, mod15M, rawFeatures);
            float p1h = runInference(sc1H, mod1H, rawFeatures);
            float p4h = runInference(sc4H, mod4H, rawFeatures);
            float p24h = runInference(sc24H, mod24H, rawFeatures);
            float r4h = runInference(scRisk4H, modRisk4H, rawFeatures);
            float r24h = runInference(scRisk24H, modRisk24H, rawFeatures);

            return new PredictionResult(p15m, p1h, p4h, p24h, r4h, r24h);
        } catch (Exception e) {
            LOG.error("❌ Inference Error: {}", e.getMessage());
            return new PredictionResult(0, 0, 0, 0, 0, 0);
        }
    }

    private float runInference(OrtSession scaler, OrtSession model, float[] rawFeatures) throws OrtException {
        long[] shape = new long[]{1, rawFeatures.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(rawFeatures), shape);
        Map<String, OnnxTensor> inputs = Collections.singletonMap(INPUT_NODE, inputTensor);

        try (OrtSession.Result scalerRes = scaler.run(inputs)) {
            float[][] scaledData = (float[][]) scalerRes.get(0).getValue();
            OnnxTensor scaledTensor = OnnxTensor.createTensor(env, scaledData);
            Map<String, OnnxTensor> modInputs = Collections.singletonMap(INPUT_NODE, scaledTensor);
            try (OrtSession.Result modelRes = model.run(modInputs)) {
                float[][] output = (float[][]) modelRes.get(0).getValue();
                return output[0][0];
            }
        }
    }

    // 🔥 QUAN TRỌNG: Thứ tự này PHẢI KHỚP 100% với Code Python Train
    // Code Python Train: numeric_features (đã loại bỏ String, var95, shortfall)
    private float[] extractFeaturesToArray(MarketFeatures f) {
        return new float[] {
                // 1. Momentum (10)
                (float) f.momentum1M, (float) f.momentum5M, (float) f.momentum15M, (float) f.momentum1H,
                (float) f.momentum4H, (float) f.momentum24H, (float) f.momentumAcceleration,
                // trendStrengthBTC đã bỏ
                (float) f.trendStrengthETH, (float) f.trendConsistency,

                // 2. Volatility (5) - Đã bỏ var95, shortfall
                (float) f.volatility1M, (float) f.volatility15M, (float) f.volatility1H,
                (float) f.volatility24H, (float) f.volatilityTermStructure,

                // 3. Breadth (5)
                (float) f.advanceDeclineRatio, (float) f.percentAboveMA20, (float) f.volumeRatioUpDown,
                (float) f.marketBreadthStrength, (float) f.btcDominance,

                // 4. Indicators (3)
                (float) f.rsi14, (float) f.volumeSpike, (float) f.distMA20,

                // 5. Funding (3)
                (float) f.fundingRateRaw, (float) f.fundingRateAvg24H, (float) f.fundingRateTrend,

                // 6. Time (4)
                (float) f.hourOfDay, (float) f.dayOfWeek, (float) f.weekOfMonth, (float) f.monthOfYear,

                // 7. Basket (4) - Python tự động append vào cuối
                (float) f.basketMomentum15M, (float) f.basketMomentum1H, (float) f.basketRsi14, (float) f.basketVolSpike
        };
    }

    @Override
    public void close() throws Exception {
        if (sc15M != null) sc15M.close(); if (mod15M != null) mod15M.close();
        if (sc1H != null) sc1H.close(); if (mod1H != null) mod1H.close();
        if (sc4H != null) sc4H.close(); if (mod4H != null) mod4H.close();
        if (sc24H != null) sc24H.close(); if (mod24H != null) mod24H.close();
        if (scRisk4H != null) scRisk4H.close(); if (modRisk4H != null) modRisk4H.close();
        if (scRisk24H != null) scRisk24H.close(); if (modRisk24H != null) modRisk24H.close();
        if (env != null) env.close();
    }

    public static class PredictionResult implements Serializable {
        public float return15M, return1H, return4H, return24H;
        public float riskDrawdown4H, riskDrawdown24H;
        public PredictionResult(float r15, float r1, float r4, float r24, float risk4, float risk24) {
            this.return15M = r15; this.return1H = r1; this.return4H = r4; this.return24H = r24;
            this.riskDrawdown4H = risk4; this.riskDrawdown24H = risk24;
        }
        @Override
        public String toString() {
            return String.format("AI[15M:%.2f%% 1H:%.2f%% | Risk4H:%.2f%%]", return15M*100, return1H*100, riskDrawdown4H*100);
        }
    }
}