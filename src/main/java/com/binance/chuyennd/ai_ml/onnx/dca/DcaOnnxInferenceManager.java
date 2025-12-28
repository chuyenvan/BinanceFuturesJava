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

    // 2 Sessions riêng biệt cho 2 Model
    private final OrtSession sessionRisk;   // Dự báo Sập (Drop)
    private final OrtSession sessionReward; // Dự báo Hồi (Rise)

    private static final String INPUT_NODE = "float_input";

    public DcaOnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing DCA AI Brain (Dual Models) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();

        // Tối ưu hóa Inference
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(2); // Dùng 2 luồng CPU

        // 1. Load Model Risk (Sập)
        String riskPath = modelDir + "/Model_DCA_Risk.onnx";
        LOG.info("Loading Risk Model: {}", riskPath);
        this.sessionRisk = env.createSession(riskPath, opts);

        // 2. Load Model Reward (Hồi)
        String rewardPath = modelDir + "/Model_DCA_Reward.onnx";
        LOG.info("Loading Reward Model: {}", rewardPath);
        this.sessionReward = env.createSession(rewardPath, opts);

        LOG.info("✅ DCA Dual Models loaded successfully!");
    }

    public DcaPredictionResult predict(DcaMarketFeatures f) {
        try {
            // Trích xuất features thô (Không cần Scaler nữa vì Model mới đã bỏ Scaler)
            float[] rawFeatures = extractFeaturesToArray(f);

            // Chạy 2 model song song hoặc tuần tự
            float predictedDD = runInference(sessionRisk, rawFeatures);   // Dự báo Sập
            float predictedRise = runInference(sessionReward, rawFeatures); // Dự báo Hồi

            return new DcaPredictionResult(predictedDD, predictedRise);

        } catch (Exception e) {
            LOG.error("❌ DCA Inference Error: {}", e.getMessage());
            // Trả về kết quả "An toàn nhất" khi lỗi:
            // Risk cực cao (-100%) để không vào lệnh
            // Reward cực thấp (0%)
            return new DcaPredictionResult(-1.0f, 0.0f);
        }
    }

    private float runInference(OrtSession modelSession, float[] features) throws OrtException {
        // Tạo Tensor đầu vào [1, num_features]
        long[] shape = new long[]{1, features.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(features), shape);
        Map<String, OnnxTensor> inputs = Collections.singletonMap(INPUT_NODE, inputTensor);

        // Chạy Inference
        try (OrtSession.Result result = modelSession.run(inputs)) {
            // XGBoost Regressor trả về float[1][1]
            float[][] output = (float[][]) result.get(0).getValue();
            return output[0][0];
        }
    }

    // 🔥 CẬP NHẬT: 24 FEATURES (Khớp với Code Python Grandmaster mới nhất)
    // Lưu ý: distFromHigh7D đã bị bỏ
    private float[] extractFeaturesToArray(DcaMarketFeatures f) {
        return new float[] {
                // --- 1. Market Position ---
                (float) f.distFromHigh24H,

                // --- 2. Relative Strength ---
                (float) f.instantAlpha,
                (float) f.recoveryElasticity,

                // --- 3. Market Context ---
                (float) f.crashVelocity,
                (float) f.globalRateDownAvg,

                // --- 4. Macro BTC ---
                (float) f.btcMomentum1H,
                (float) f.btcMomentum24H,

                // --- 5. Coin Specific Technicals ---
                (float) f.rsi1H,
                (float) f.volumeAnomaly,
                (float) f.distFromLow24H,
                (float) f.maxRateChange60M,
                (float) f.volatilityShock,

                // --- 6. Basket Features ---
                (float) f.basketMomentum15M,
                (float) f.basketMomentum1H,
                (float) f.basketMomentum24H,
                (float) f.basketRsi14,
                (float) f.basketVolSpike,

                // --- 7. Funding ---
                (float) f.fundingRateRaw,
                (float) f.fundingRateAvg24H,
                (float) f.fundingRateTrend,

                // --- 8. Time ---
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
        if (env != null) env.close();
    }
}