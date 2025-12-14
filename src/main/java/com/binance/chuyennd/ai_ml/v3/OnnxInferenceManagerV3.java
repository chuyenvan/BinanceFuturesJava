package com.binance.chuyennd.ai_ml.v3;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.FloatBuffer;
import java.util.*;

public class OnnxInferenceManagerV3 implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(OnnxInferenceManagerV3.class);
    private final OrtEnvironment env;
    private final Map<String, OrtSession> sessions = new HashMap<>();

    // Model V3 có 4 labels này
    private static final List<String> LABELS = Arrays.asList(
            "Return15M", "Return1H", "Return4H", "maxDrawdown4H"
    );

    public OnnxInferenceManagerV3(String modelDir) throws Exception {
        this.env = OrtEnvironment.getEnvironment();
        try { System.setProperty("ai.onnxruntime.disable_telemetry", "true"); } catch (Exception e){}

        LOG.info("🚀 [V3] Loading Models from: {}", modelDir);
        for (String label : LABELS) {
            String path = modelDir + "/Model_Regressor_" + label + ".onnx";
            if (!new File(path).exists()) throw new RuntimeException("Missing V3 Model: " + path);

            OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
            opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.BASIC_OPT);
            sessions.put(label, env.createSession(path, opts));
        }
    }

    public PredictionResultV3 predict(MarketFeaturesV3 features) {
        // Lấy input vector từ FeatureEngineerV3 đã tính toán
        if (features.onnxInputData == null || features.onnxInputData.length == 0) {
            return new PredictionResultV3(0,0,0,0); // Không đủ dữ liệu
        }

        float p15m = runModel("Return15M", features.onnxInputData);
        float p1h  = runModel("Return1H", features.onnxInputData);
        float p4h  = runModel("Return4H", features.onnxInputData);
        float pMaxDD = runModel("maxDrawdown4H", features.onnxInputData);

        return new PredictionResultV3(p15m, p1h, p4h, pMaxDD);
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
            LOG.error("Inference Error [{}]: {}", label, e.getMessage());
            return 0.0f;
        }
    }

    @Override
    public void close() throws Exception {
        for(OrtSession s : sessions.values()) s.close();
        env.close();
    }

    public static class PredictionResultV3 {
        public float return15M, return1H, return4H, maxDrawdown4H;
        public PredictionResultV3(float r15, float r1, float r4, float maxDD) {
            this.return15M = r15; this.return1H = r1; this.return4H = r4; this.maxDrawdown4H = maxDD;
        }
    }
}