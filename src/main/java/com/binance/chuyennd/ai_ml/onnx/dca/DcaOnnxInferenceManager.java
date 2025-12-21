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

    // Sessions cho Classification (Recoverable / Risk Warning)
    private final OrtSession scRecover, modRecover;

    // Sessions cho Regression (MaxDrawdown / MaxDropFromNow)
    private final OrtSession scDrawdown, modDrawdown;

    private static final String INPUT_NODE = "float_input";

    public DcaOnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing DCA AI Brain (Advanced Risk - 16 Features) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);

        // Tối ưu luồng
        opts.setIntraOpNumThreads(2);
        opts.setInterOpNumThreads(1);

        // 1. Load Model Classification (Có thể là IsRecoverable hoặc RiskAlert tùy file bạn train)
        this.scRecover = env.createSession(modelDir + "/Scaler_DCA_IsRecoverable3D.onnx", opts);
        this.modRecover = env.createSession(modelDir + "/Model_DCA_IsRecoverable3D.onnx", opts);

        // 2. Load Model Regression (MaxDropFromNow)
        // Lưu ý: Nếu bạn train file mới tên là Model_DCA_MaxDrop.onnx thì sửa lại tên file ở đây nhé
        // Ở đây tôi giữ tên cũ hoặc bạn đổi tên file model cho khớp
        this.scDrawdown = env.createSession(modelDir + "/Scaler_DCA_MaxDrawdown3D.onnx", opts);
        this.modDrawdown = env.createSession(modelDir + "/Model_DCA_MaxDrawdown3D.onnx", opts);

        LOG.info("✅ DCA Models loaded successfully!");
    }

    public DcaPredictionResult predict(DcaMarketFeatures f) {
        try {
            float[] rawFeatures = extractFeaturesToArray(f);

            // 1. Chạy Classification
            float recoverProb = runInferenceClassification(scRecover, modRecover, rawFeatures);

            // 2. Chạy Regression
            float predictedDD = runInferenceRegression(scDrawdown, modDrawdown, rawFeatures);

            return new DcaPredictionResult(recoverProb, predictedDD);

        } catch (Exception e) {
            LOG.error("❌ DCA Inference Error: {}", e.getMessage(), e);
            // Trả về kết quả an toàn (Rủi ro cao nhất)
            return new DcaPredictionResult(0.0f, -1.0f);
        }
    }

    private float runInferenceRegression(OrtSession scaler, OrtSession model, float[] rawFeatures) throws OrtException {
        long[] shape = new long[]{1, rawFeatures.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(rawFeatures), shape);
        Map<String, OnnxTensor> inputs = Collections.singletonMap(INPUT_NODE, inputTensor);

        try (OrtSession.Result scalerRes = scaler.run(inputs)) {
            float[][] scaledData = (float[][]) scalerRes.get(0).getValue();
            OnnxTensor scaledTensor = OnnxTensor.createTensor(env, scaledData);
            Map<String, OnnxTensor> modInputs = Collections.singletonMap(INPUT_NODE, scaledTensor);

            try (OrtSession.Result modelRes = model.run(modInputs)) {
                float[][] output = (float[][]) modelRes.get(0).getValue();
                return output[0][0]; // Giá trị dự báo (float)
            }
        }
    }

    private float runInferenceClassification(OrtSession scaler, OrtSession model, float[] rawFeatures) throws OrtException {
        long[] shape = new long[]{1, rawFeatures.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(rawFeatures), shape);
        Map<String, OnnxTensor> inputs = Collections.singletonMap(INPUT_NODE, inputTensor);

        try (OrtSession.Result scalerRes = scaler.run(inputs)) {
            float[][] scaledData = (float[][]) scalerRes.get(0).getValue();
            OnnxTensor scaledTensor = OnnxTensor.createTensor(env, scaledData);
            Map<String, OnnxTensor> modInputs = Collections.singletonMap(INPUT_NODE, scaledTensor);

            try (OrtSession.Result modelRes = model.run(modInputs)) {
                Object labelVal = modelRes.get(0).getValue();
                if (labelVal instanceof long[]) return (float) ((long[]) labelVal)[0];
                if (labelVal instanceof int[]) return (float) ((int[]) labelVal)[0];
                return 0.0f;
            }
        }
    }

    // 🔥 CẬP NHẬT: 16 FEATURES (Bỏ dcaImpactRatio, Bớt BTC, Thêm Spike/Shock)
    // Thứ tự này phải khớp 100% với Python train
    private float[] extractFeaturesToArray(DcaMarketFeatures f) {
        return new float[] {
                // Group 1: Position Context (2) - ĐÃ BỎ dcaImpactRatio
                (float) f.currentDrawdown,
                (float) f.lossVelocity1H,

                // Group 2: Relative Strength (3)
                (float) f.instantAlpha,
                (float) f.recoveryElasticity,
                (float) f.dangerIndex,

                // Group 3: Market Context (3)
                (float) f.crashVelocity,
                (float) f.globalRateDownAvg,


                // Group 4: Macro BTC (2) - ĐÃ RÚT GỌN
                (float) f.btcMomentum1H,
                (float) f.btcMomentum24H,

                // Group 5: Coin Specific Technicals (6) - ĐÃ BỔ SUNG
                (float) f.rsi1H,
                (float) f.volumeAnomaly,     // Giữ lại hoặc thay bằng logic khác nếu cần
                (float) f.distFromLow24H,
                (float) f.maxRateChange60M,
                (float) f.volumeSpike,       // Feature Mới
                (float) f.volatilityShock    // Feature Mới
        };
    }

    @Override
    public void close() throws Exception {
        if (scRecover != null) scRecover.close();
        if (modRecover != null) modRecover.close();
        if (scDrawdown != null) scDrawdown.close();
        if (modDrawdown != null) modDrawdown.close();
        if (env != null) env.close();
    }
}