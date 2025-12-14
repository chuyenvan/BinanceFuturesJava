package com.binance.chuyennd.ai_ml.v4;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.FloatBuffer;
import java.util.*;

public class OnnxInferenceManagerV4 implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(OnnxInferenceManagerV4.class);
    private final OrtEnvironment env;
    private final Map<String, OrtSession> sessions = new HashMap<>();

    private static final List<String> LABELS = Arrays.asList(
            "Return15M", "Return1H", "Return4H", "Return24H", "maxDrawdown4H"
    );

    public OnnxInferenceManagerV4(String modelDir) throws Exception {
        this.env = OrtEnvironment.getEnvironment();
        try { System.setProperty("ai.onnxruntime.disable_telemetry", "true"); } catch (Exception ignored){}

        LOG.info("🚀 [V4] Loading Ensemble Models (CPU RESTRICTED MODE)...");
        for (String label : LABELS) {
            String path = modelDir + "/Model_Regressor_" + label + ".onnx";
            if (!new File(path).exists()) throw new RuntimeException("Missing V4 Model: " + path);

            OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
            opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.BASIC_OPT);

            // --- FIX CPU USAGE ---
            // Ép ONNX chỉ chạy 1 luồng xử lý cho mỗi model.
            // Vì bạn chạy vòng lặp tuần tự (Sequential) trong RunGeneratePredictions,
            // 1 luồng là đủ nhanh và không ăn hết CPU của hệ thống.
            opts.setIntraOpNumThreads(1);
            opts.setInterOpNumThreads(1);
            // ---------------------

            sessions.put(label, env.createSession(path, opts));
        }
    }

    public PredictionResultV4 predict(MarketFeaturesV4 features) {
        if (features.onnxInputData == null) return new PredictionResultV4(0,0,0,0,0,0);

        // Các lệnh này sẽ chạy tuần tự trên 1 luồng đã định nghĩa ở trên
        float p15m = runModel("Return15M", features.onnxInputData);
        float p1h  = runModel("Return1H", features.onnxInputData);
        float p4h  = runModel("Return4H", features.onnxInputData);
        float p24h = runModel("Return24H", features.onnxInputData);
        float pMaxDD = runModel("maxDrawdown4H", features.onnxInputData);

        return new PredictionResultV4(features.timestamp, p15m, p1h, p4h, p24h, pMaxDD);
    }

    private float runModel(String label, float[] inputData) {
        try {
            OrtSession session = sessions.get(label);
            long[] shape = new long[]{1, inputData.length};
            try (OnnxTensor tensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(inputData), shape)) {
                String inputName = session.getInputNames().iterator().next();
                try (OrtSession.Result res = session.run(Collections.singletonMap(inputName, tensor))) {
                    float[][] out = (float[][]) ((OnnxTensor) res.get(0)).getValue();
                    return out[0][0];
                }
            }
        } catch (Exception e) {
            return 0.0f;
        }
    }

    @Override
    public void close() throws Exception {
        for(OrtSession s : sessions.values()) s.close();
        env.close();
    }

    public static class PredictionResultV4 {
        public long timestamp;
        public float p15M, p1H, p4H, p24H, maxDD4H;
        public PredictionResultV4(long t, float r15, float r1, float r4, float r24, float dd) {
            this.timestamp = t;
            this.p15M = r15; this.p1H = r1; this.p4H = r4; this.p24H = r24; this.maxDD4H = dd;
        }
    }
}