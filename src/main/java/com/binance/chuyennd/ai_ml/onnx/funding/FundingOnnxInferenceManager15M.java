package com.binance.chuyennd.ai_ml.onnx.funding;

import ai.onnxruntime.*;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures15M;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public class FundingOnnxInferenceManager15M implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(FundingOnnxInferenceManager15M.class);
    private final OrtEnvironment env;
    private OrtSession session;

    private String inputNodeName = "X";
    // 21 Features tương ứng với chuẩn 15M mới
    private static final int NUM_FEATURES = 21;

    public FundingOnnxInferenceManager15M(String modelPath) throws OrtException {
        LOG.info("🧠 Initializing Funding AI 15M (BATCH MODE) from: {}", modelPath);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();

        opts.addConfigEntry("session.disable_cpu_mem_arena", "1");
        opts.setIntraOpNumThreads(Math.min(4, Runtime.getRuntime().availableProcessors()));
        opts.setInterOpNumThreads(1);

        this.session = env.createSession(modelPath, opts);

        // Tự động nhận diện Input Node của ONNX
        try {
            Map<String, NodeInfo> inputInfo = this.session.getInputInfo();
            if (!inputInfo.isEmpty()) {
                this.inputNodeName = inputInfo.keySet().iterator().next();
                LOG.info("✅ Detected ONNX Input Name: '{}'", this.inputNodeName);
            }
        } catch (Exception e) {
            LOG.warn("⚠️ Could not detect input name, using default '{}'", this.inputNodeName);
        }
    }

    public List<float[]> predictBatch(List<float[]> batchFeatures) {
        int batchSize = batchFeatures.size();
        if (batchSize == 0) return new ArrayList<>();

        FloatBuffer buffer = FloatBuffer.allocate(batchSize * NUM_FEATURES);
        for (float[] f : batchFeatures) {
            buffer.put(f);
        }
        buffer.flip();

        List<float[]> results = new ArrayList<>(batchSize);
        long[] shape = new long[]{batchSize, NUM_FEATURES};

        try (
                OnnxTensor inputTensor = OnnxTensor.createTensor(env, buffer, shape);
                OrtSession.Result result = session.run(Collections.singletonMap(inputNodeName, inputTensor))
        ) {
            float[][] output = null;

            for (Map.Entry<String, OnnxValue> entry : result) {
                Object val = entry.getValue().getValue();
                if (val instanceof float[][]) {
                    output = (float[][]) val;
                    break;
                }
            }

            if (output == null) {
                if (result.size() > 1) {
                    Object val1 = result.get(1).getValue();
                    if (val1 instanceof float[][]) output = (float[][]) val1;
                }
                if (output == null) {
                    Object val0 = result.get(0).getValue();
                    if (val0 instanceof float[][]) output = (float[][]) val0;
                }
            }

            if (output != null) {
                Collections.addAll(results, output);
            } else {
                throw new RuntimeException("❌ Không tìm thấy output float[][] trong kết quả ONNX!");
            }

        } catch (Exception e) {
            LOG.error("❌ Batch inference error: {}", e.getMessage());
            // Crash safe: Điền kết quả rỗng (giả sử output 5 labels)
            for (int i = 0; i < batchSize; i++) {
                results.add(new float[]{0, 0, 0, 0, 0});
            }
        }
        return results;
    }

    // Nhận trực tiếp FundingMarketFeatures15M
    public float[] extractFeaturesToArray(FundingMarketFeatures15M f) {
        return new float[]{
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength,
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock,
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike,
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend
        };
    }

    @Override
    public void close() throws Exception {
        if (session != null) session.close();
        if (env != null) env.close();
    }
}