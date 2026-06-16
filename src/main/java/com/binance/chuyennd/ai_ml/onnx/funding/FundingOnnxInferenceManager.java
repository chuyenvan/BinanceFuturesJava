
package com.binance.chuyennd.ai_ml.onnx.funding;

import ai.onnxruntime.*;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

public class FundingOnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(FundingOnnxInferenceManager.class);
    private final OrtEnvironment env;
    private OrtSession session;

    private String inputNodeName = "X";
    private static final int NUM_FEATURES = 21;

    public FundingOnnxInferenceManager(String modelPath) throws OrtException {
        // Default GIỮ NGUYÊN min(4, cores) để output bất biến với bản cũ.
        this(modelPath, Math.min(4, Runtime.getRuntime().availableProcessors()));
    }

    public FundingOnnxInferenceManager(String modelPath, int intraOpThreads) throws OrtException {
        LOG.info("🧠 Initializing Funding AI (BATCH MODE) from: {} | intraOpThreads={}", modelPath, intraOpThreads);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();

        opts.addConfigEntry("session.disable_cpu_mem_arena", "1");
        opts.setIntraOpNumThreads(intraOpThreads);
        opts.setInterOpNumThreads(1);

        this.session = env.createSession(modelPath, opts);

        // Auto detect input name
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
            // 🔥 SỬA LỖI TẠI ĐÂY: Tìm đúng Output là float[][] (Probabilities)
            // Model Classifier thường trả về: [0]: Label (long[]), [1]: Probs (float[][])
            float[][] output = null;

            // Cách 1: Duyệt qua các output để tìm mảng float 2 chiều
            for (Map.Entry<String, OnnxValue> entry : result) {
                Object val = entry.getValue().getValue();
                if (val instanceof float[][]) {
                    output = (float[][]) val;
                    break;
                }
            }

            // Cách 2: Nếu loop trên không tìm thấy (hiếm), thử lấy Index 1 cứng
            if (output == null) {
                if (result.size() > 1) {
                    Object val1 = result.get(1).getValue();
                    if (val1 instanceof float[][]) output = (float[][]) val1;
                }
                // Fallback cuối cùng: thử index 0 nếu model chỉ có 1 output
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
            // Crash safe: Điền kết quả rỗng
            for (int i = 0; i < batchSize; i++) {
                results.add(new float[]{0, 0, 0, 0, 0});
            }
        }
        return results;
    }

    public float[] extractFeaturesToArray(FundingMarketFeatures f) {
        return new float[]{
                (float) f.btcMomentum1H, (float) f.btcMomentum4H, (float) f.btcMomentum24H,
                (float) f.btcDominance, (float) f.marketBreadthStrength,
                (float) f.rateDown15MAvg, (float) f.momentum1H, (float) f.momentum4H, (float) f.momentum24H,
                (float) f.rsi1H, (float) f.distFromLow24H, (float) f.volatilityShock,
                (float) f.basketMomentum15M, (float) f.basketMomentum1H, (float) f.basketMomentum24H,
                (float) f.basketRsi14, (float) f.basketVolSpike,
                (float) f.coinFundingRate, (float) f.basketFundingAvg, (float) f.fundingRateAvg24H, (float) f.fundingRateTrend
        };
    }

    @Override
    public void close() throws Exception {
        if (session != null) session.close();
        if (env != null) env.close();
    }
}