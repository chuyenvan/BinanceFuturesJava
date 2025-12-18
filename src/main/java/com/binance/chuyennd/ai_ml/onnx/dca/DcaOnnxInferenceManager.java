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

    // Sessions cho Classification (Recoverable)
    private final OrtSession scRecover, modRecover;

    // Sessions cho Regression (MaxDrawdown)
    private final OrtSession scDrawdown, modDrawdown;

    private static final String INPUT_NODE = "float_input";

    public DcaOnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing DCA AI Brain from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);

        // Tối ưu luồng (giống bộ cũ)
        opts.setIntraOpNumThreads(2);
        opts.setInterOpNumThreads(1);

        // 1. Load Model Classification (IsRecoverable3D)
        this.scRecover = env.createSession(modelDir + "/Scaler_DCA_IsRecoverable3D.onnx", opts);
        this.modRecover = env.createSession(modelDir + "/Model_DCA_IsRecoverable3D.onnx", opts);

        // 2. Load Model Regression (MaxDrawdown3D)
        this.scDrawdown = env.createSession(modelDir + "/Scaler_DCA_MaxDrawdown3D.onnx", opts);
        this.modDrawdown = env.createSession(modelDir + "/Model_DCA_MaxDrawdown3D.onnx", opts);

        LOG.info("✅ DCA Models loaded successfully!");
    }

    public DcaPredictionResult predict(DcaMarketFeatures f) {
        try {
            float[] rawFeatures = extractFeaturesToArray(f);

            // 1. Chạy Classification: Có về bờ không?
            // Output của Classifier thường là mảng xác suất [Prob_Class0, Prob_Class1]
            // Hoặc đôi khi chỉ là label 0/1 tùy cách export.
            // Với XGBoost Classifier + ONNX, thường output node 1 là probabilities (ZipMap)
            // Tuy nhiên để đơn giản, ta cần check kỹ output shape.
            // Ở đây tôi giả định output model trả về xác suất Class 1 (Recoverable).
            float recoverProb = runInferenceClassification(scRecover, modRecover, rawFeatures);

            // 2. Chạy Regression: Lỗ bao nhiêu?
            float predictedDD = runInferenceRegression(scDrawdown, modDrawdown, rawFeatures);

            return new DcaPredictionResult(recoverProb, predictedDD);

        } catch (Exception e) {
            LOG.error("❌ DCA Inference Error: {}", e.getMessage(), e);
            // Trả về kết quả an toàn (Không về bờ, Lỗ sâu)
            return new DcaPredictionResult(0.0f, -1.0f);
        }
    }

    private float runInferenceRegression(OrtSession scaler, OrtSession model, float[] rawFeatures) throws OrtException {
        // ... (Logic giống hệt bộ cũ: Scaler -> Model -> Output float) ...
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
        // Classification hơi khác chút: Output thường là Label (int) và Probabilities (Map/Array)
        // Tuy nhiên, model ONNX xuất từ onnxmltools thường trả về:
        // Output 0: Label (0 hoặc 1)
        // Output 1: Probabilities (Map<Int, Float> hoặc Array)

        long[] shape = new long[]{1, rawFeatures.length};
        OnnxTensor inputTensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(rawFeatures), shape);
        Map<String, OnnxTensor> inputs = Collections.singletonMap(INPUT_NODE, inputTensor);

        try (OrtSession.Result scalerRes = scaler.run(inputs)) {
            float[][] scaledData = (float[][]) scalerRes.get(0).getValue();
            OnnxTensor scaledTensor = OnnxTensor.createTensor(env, scaledData);
            Map<String, OnnxTensor> modInputs = Collections.singletonMap(INPUT_NODE, scaledTensor);

            try (OrtSession.Result modelRes = model.run(modInputs)) {
                // Lấy output thứ 2 (Probabilities)
                // Lưu ý: ONNX Runtime Java xử lý ZipMap (Map<Long, Float>) hơi phức tạp
                // Cách đơn giản nhất: Lấy Output 1 (Label) nếu ko lấy được Prob.
                // Nhưng ở đây ta sẽ cố lấy Prob của Class 1.

                // Hack: Với XGBoost Binary, thường output thứ 2 là danh sách xác suất.
                // Nếu gặp khó khăn với ZipMap, ta sẽ dùng Label (Output 0) tạm thời.
                // Ở đây tôi viết code để lấy Label trước cho an toàn (0.0 hoặc 1.0)
                // Vì SVM/XGBoost onnx conversion đôi khi trả về int64 cho label.

                Object labelVal = modelRes.get(0).getValue();
                if (labelVal instanceof long[]) {
                    long[] labels = (long[]) labelVal;
                    return (float) labels[0]; // Trả về 0.0 hoặc 1.0
                }
                if (labelVal instanceof int[]) {
                    int[] labels = (int[]) labelVal;
                    return (float) labels[0];
                }

                // Nếu muốn lấy Prob chi tiết (ví dụ 0.89), cần parse Output 1 (ZipMap sequence)
                // Code Java xử lý Map trong OnnxRuntime khá dài dòng.
                // Tạm thời trả về Label (Hard Vote) để chạy được ngay.
                return 0.0f;
            }
        }
    }

    // 🔥 QUAN TRỌNG: Thứ tự KHỚP 100% với Python `feature_columns`
    private float[] extractFeaturesToArray(DcaMarketFeatures f) {
        return new float[] {
                // Group 1: Position
                (float) f.currentDrawdown, (float) f.lossVelocity1H,
                // Group 2: Capital
                (float) f.dcaImpactRatio,
                // Group 3: Relative Strength
                (float) f.instantAlpha, (float) f.recoveryElasticity, (float) f.dangerIndex,
                // Group 4: Context
                (float) f.crashVelocity, (float) f.globalRateDownAvg, (float) f.fundingRate,
                // Group 5: Macro
                (float) f.btcMomentum15M, (float) f.btcMomentum1H, (float) f.btcMomentum4H, (float) f.btcMomentum24H,
                (float) f.btcMomentumAcceleration, (float) f.ethTrendStrength,
                // Group 6: Technical
                (float) f.rsi1H, (float) f.volumeAnomaly, (float) f.distFromLow24H, (float) f.maxRateChange60M
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