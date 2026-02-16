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

public class EntryDcaOnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(EntryDcaOnnxInferenceManager.class);
    private final OrtEnvironment env;
    private OrtSession session;

    private String inputNodeName = "X";

    // 🔥 SỬA TẠI ĐÂY: Tăng từ 21 lên 22
    private static final int NUM_FEATURES = 22;

    public EntryDcaOnnxInferenceManager(String modelPath) throws OrtException {
        LOG.info("🧠 Initializing Funding AI (BATCH MODE) from: {}", modelPath);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();

        opts.addConfigEntry("session.disable_cpu_mem_arena", "1");
        opts.setIntraOpNumThreads(Math.min(4, Runtime.getRuntime().availableProcessors()));
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

        // Cấp phát bộ nhớ dựa trên NUM_FEATURES mới (22)
        FloatBuffer buffer = FloatBuffer.allocate(batchSize * NUM_FEATURES);

        for (float[] f : batchFeatures) {
            // Kiểm tra an toàn: Nếu mảng f không đủ 22 phần tử thì báo lỗi hoặc skip
            if (f.length != NUM_FEATURES) {
                LOG.error("❌ Feature size mismatch! Expected {}, Got {}", NUM_FEATURES, f.length);
                continue;
            }
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

            // Tìm output đúng định dạng
            if (result.size() > 0) {
                // Ưu tiên lấy output index 1 (thường là probabilities trong scikit-learn/xgboost wrapper)
                // Nếu model native xgboost thì có thể là index 0
                int targetIndex = (result.size() > 1) ? 1 : 0;

                Object val = result.get(targetIndex).getValue();
                if (val instanceof float[][]) {
                    output = (float[][]) val;
                } else {
                    // Fallback: Duyệt tìm mảng float[][]
                    for (Map.Entry<String, OnnxValue> entry : result) {
                        Object v = entry.getValue().getValue();
                        if (v instanceof float[][]) {
                            output = (float[][]) v;
                            break;
                        }
                    }
                }
            }

            if (output != null) {
                Collections.addAll(results, output);
            } else {
                throw new RuntimeException("❌ Không tìm thấy output float[][] trong kết quả ONNX!");
            }

        } catch (Exception e) {
            LOG.error("❌ Batch inference error: {}", e.getMessage());
            for (int i = 0; i < batchSize; i++) {
                results.add(new float[]{0, 0, 0, 0, 0});
            }
        }
        return results;
    }

    public float[] extractFeaturesToArray(FundingMarketFeatures f) {
        return new float[]{
                // 1. Context (5)
                (float) f.btcMomentum1H,
                (float) f.btcMomentum4H,
                (float) f.btcMomentum24H,
                (float) f.btcDominance,
                (float) f.marketBreadthStrength,

                // 2. Coin Specific (8)
                (float) f.momentum1M,   // Feature mới
                (float) f.momentum15M,
                (float) f.momentum1H,
                (float) f.momentum4H,
                (float) f.momentum24H,
                (float) f.rsi1H,
                (float) f.distFromLow24H,
                (float) f.volatilityShock,

                // 3. Basket (5)
                (float) f.basketMomentum15M,
                (float) f.basketMomentum1H,
                (float) f.basketMomentum24H,
                (float) f.basketRsi14,
                (float) f.basketVolSpike,

                // 4. Funding (4)
                (float) f.coinFundingRate,
                (float) f.fundingRateRaw,
                (float) f.fundingRateAvg24H,
                (float) f.fundingRateTrend
        };
    }

    @Override
    public void close() throws Exception {
        if (session != null) session.close();
        if (env != null) env.close();
    }
}