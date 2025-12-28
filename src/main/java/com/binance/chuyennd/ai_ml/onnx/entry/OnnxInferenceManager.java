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

    // Các bộ dự đoán đơn lẻ (Single Predictor)
    private final SinglePredictor p15M, p1H, p4H, p24H, pRisk4H, pRisk24H;

    public OnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing AI Brain V3 (Single XGBoost Mode) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        this.opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1); // Tối ưu CPU

        // Khởi tạo 6 bộ não con cho 6 target
        this.p15M = new SinglePredictor(modelDir, "Return15M");
        this.p1H = new SinglePredictor(modelDir, "Return1H");
        this.p4H = new SinglePredictor(modelDir, "Return4H");
        this.p24H = new SinglePredictor(modelDir, "Return24H");
        this.pRisk4H = new SinglePredictor(modelDir, "maxDrawdown4H");
        this.pRisk24H = new SinglePredictor(modelDir, "maxDrawdown24H");

        LOG.info("✅ All Single XGBoost Models loaded!");
    }

    public PredictionResult predictAll(MarketFeatures f) {
        try {
            // Convert Features sang mảng float[] chuẩn
            float[] rawFeatures = extractFeaturesToArray(f);

            // Dự đoán
            float r15 = p15M.predict(rawFeatures);
            float r1 = p1H.predict(rawFeatures);
            float r4 = p4H.predict(rawFeatures);
            float r24 = p24H.predict(rawFeatures);
            float risk4 = pRisk4H.predict(rawFeatures);
            float risk24 = pRisk24H.predict(rawFeatures);

            return new PredictionResult(r15, r1, r4, r24, risk4, risk24);
        } catch (Exception e) {
            LOG.error("❌ Inference Error", e);
            return new PredictionResult(0, 0, 0, 0, 0, 0);
        }
    }

    /**
     * Class nội bộ xử lý logic Single Model (Scaler -> Model)
     */
    private class SinglePredictor {
        private OrtSession scaler;
        private OrtSession model;
        private final String targetName;

        public SinglePredictor(String dir, String target) {
            this.targetName = target;
            try {
                // 1. Load Scaler
                String scalerPath = dir + "/Scaler_" + target + ".onnx";
                if (fileExists(scalerPath)) {
                    this.scaler = env.createSession(scalerPath, opts);
                } else {
                    LOG.warn("⚠️ Scaler missing for {}: {}", target, scalerPath);
                }

                // 2. Load Model XGBoost duy nhất
                String modelPath = dir + "/Model_Regressor_" + target + ".onnx";
                if (fileExists(modelPath)) {
                    this.model = env.createSession(modelPath, opts);
                    LOG.info("  -> Loaded Model for {}", target);
                } else {
                    LOG.error("❌ Model missing for {}: {}", target, modelPath);
                }

            } catch (Exception e) {
                LOG.error("  -> Failed to load predictor for " + target, e);
            }
        }

        public float predict(float[] rawFeatures) throws OrtException {
            if (model == null) return 0f;

            float[] inputForModel = rawFeatures;

            // 1. Scale dữ liệu (nếu có scaler)
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

        // Helper chạy 1 session ONNX
        private float[][] runModel(OrtSession session, float[] inputData) throws OrtException {
            long[] shape = new long[]{1, inputData.length};
            try (OnnxTensor tensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(inputData), shape)) {
                // Tên node input thường là "float_input", nếu lỗi hãy check lại bằng Netron
                // Với XGBoost convert có thể là "input" hoặc tên khác, nhưng thường library convert chuẩn là "float_input"
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

    // --- CÁC HÀM TIỆN ÍCH ---

    private boolean fileExists(String path) {
        return new File(path).exists();
    }

    private float[] extractFeaturesToArray(MarketFeatures f) {
        // Thứ tự features PHẢI GIỐNG 100% Code Python Training
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
            return String.format("[15M:%.2f%% 1H:%.2f%% 4H:%.2f%% | Risk:%.2f%%]",
                    return15M*100, return1H*100, return4H*100, riskDrawdown4H*100);
        }
    }
}