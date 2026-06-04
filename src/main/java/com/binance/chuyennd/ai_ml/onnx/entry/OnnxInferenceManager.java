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
    private final SinglePredictor p15M;
    // R: Risk (Dùng Model V3.0 Trend/Full)
    private final SinglePredictor pRisk4H;

    public OnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing V4 Experimental AI Brain from: {}", modelDir);
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


        LOG.info("✅ All V4 Models loaded successfully!");
    }

    public PredictionResult predictAll(MarketFeatures f) {
        try {
            // 1. Chuẩn bị 2 bộ dữ liệu khác nhau
//            float[] featuresV4 = extractFeaturesV4Sideway(f); // Cho Return
            float[] featuresV3 = extractFeaturesV3Full(f);    // Cho Risk

            // 2. Dự đoán
            float r15 = p15M.predict(featuresV3);
            float risk4 = pRisk4H.predict(featuresV3);

            return new PredictionResult(r15, risk4);
        } catch (Exception e) {
            LOG.error("❌ Inference Error", e);
            return new PredictionResult(0, 0);
        }
    }

    /**
     * TRÍCH XUẤT FEATURES CHO MODEL V4 (SIDEWAY)
     * Logic: Tính toán các chỉ số phái sinh (Bollinger Pos, Compression...) ngay tại đây
     * Danh sách 22 features (Khớp với code Python V4 Final)
     */
    private float[] extractFeaturesV4Sideway(MarketFeatures f) {
        float epsilon = 1e-6f;

        // 1. Chuẩn bị các biến cơ sở (Cast sang float 1 lần cho gọn)
        float vol1H = (float) f.volatility1H;
        float vol24H = (float) f.volatility24H;
        float mom15M = (float) f.momentum15M;
        float mom1H = (float) f.momentum1H;
        float rsi14 = (float) f.rsi14;
        float momAccel = (float) f.momentumAcceleration;
        float fundRaw = (float) f.fundingRateRaw;
        float fundAvg = (float) f.fundingRateAvg24H;

        // 2. TÍNH TOÁN CÁC BIẾN PHÁI SINH (CALCULATED FEATURES)
        // Logic khớp với hàm preprocess_data trong Python

        // [CORE] Volatility Term Structure
        float volTermStructure = vol1H / (vol24H + epsilon);

        // [CORE] Interactions: mom15M_vol1H
        float mom15M_vol1H = mom15M * vol1H;

        // [CORE] Interactions: rsi_accel = (rsi14 - 50) * momentumAcceleration
        float rsi_accel = (rsi14 - 50f) * momAccel;

        // [V4 NEW] trend_efficiency = abs(momentum1H) / (volatility1H + 1e-6)
        float trend_efficiency = Math.abs(mom1H) / (vol1H + epsilon);

        // [V4 NEW] funding_shock = fundingRateRaw - fundingRateAvg24H
        float funding_shock = fundRaw - fundAvg;

        // [V4 NEW] panic_index = volatility1H * (100 - rsi14)
        float panic_index = vol1H * (100f - rsi14);

        // 3. XÂY DỰNG MẢNG FEATURE (Thứ tự phải khớp tuyệt đối với danh sách feature_columns)
        return new float[]{
                // --- Nhóm Tín Hiệu Nhanh ---
                mom15M,                             // 1. momentum15M
                mom1H,                              // 2. momentum1H
                (float) f.momentum4H,               // 3. momentum4H
                (float) f.momentum24H,              // 4. momentum24H
                momAccel,                           // 5. momentumAcceleration
                rsi_accel,                          // 6. rsi_accel (Calculated)
                mom15M_vol1H,                       // 7. mom15M_vol1H (Calculated)

                // --- Nhóm Môi Trường ---
                (float) f.volatility15M,            // 8. volatility15M
                vol1H,                              // 9. volatility1H
                vol24H,                             // 10. volatility24H
                (float) f.volatility1M,             // 11. volatility1M
                volTermStructure,                   // 12. volatilityTermStructure (Calculated)

                // --- Nhóm Trend & Sentiment ---
                (float) f.trendConsistency,         // 13. trendConsistency
                (float) f.advanceDeclineRatio,      // 14. advanceDeclineRatio
                (float) f.percentAboveMA20,         // 15. percentAboveMA20
                (float) f.marketBreadthStrength,    // 16. marketBreadthStrength
                (float) f.btcDominance,             // 17. btcDominance
                (float) f.volumeSpike,              // 18. volumeSpike

                // --- Nhóm Funding ---
                fundRaw,                            // 19. fundingRateRaw
                fundAvg,                            // 20. fundingRateAvg24H
                funding_shock,                      // 21. funding_shock (Calculated)

                // --- Nhóm Time ---
                (float) f.hourOfDay,                // 22. hourOfDay
                (float) f.dayOfWeek,                // 23. dayOfWeek
                (float) f.monthOfYear,              // 24. monthOfYear

                // --- Nhóm Basket ---
                (float) f.basketMomentum15M,        // 25. basketMomentum15M
                (float) f.basketMomentum1H,         // 26. basketMomentum1H
                (float) f.basketRsi14,              // 27. basketRsi14
                (float) f.basketVolSpike,           // 28. basketVolSpike

                // --- V4 Special ---
                trend_efficiency,                   // 29. trend_efficiency (Calculated)
                panic_index                         // 30. panic_index (Calculated)
        };
    }

    /**
     * TRÍCH XUẤT FEATURES CHO MODEL V3 (RISK/TREND)
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