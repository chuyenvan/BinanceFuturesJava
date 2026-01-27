package com.binance.chuyennd.ai_ml.onnx.dca;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.ai_ml.features.export.dca.DcaMarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class DcaOnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(DcaOnnxInferenceManager.class);
    private final OrtEnvironment env;

    private OrtSession sessionRisk;
    private OrtSession sessionReward;
    private OrtSession sessionPump;
    private OrtSession sessionDump;

    private static final String INPUT_NODE = "float_input";
    private static final int NUM_FEATURES = 41; // Số lượng feature cố định

    public DcaOnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing DCA AI (BATCH MODE) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions opts = new OrtSession.SessionOptions();

        // Tối ưu cho Batch lớn
        opts.addConfigEntry("session.disable_cpu_mem_arena", "1");
        opts.setIntraOpNumThreads(Math.min(4, Runtime.getRuntime().availableProcessors())); // Cho phép đa luồng nội bộ khi tính batch
        opts.setInterOpNumThreads(1);

        this.sessionRisk = loadSession(modelDir, "Model_Risk.onnx", opts);
        this.sessionReward = loadSession(modelDir, "Model_Reward.onnx", opts);
        this.sessionPump = loadSession(modelDir, "Model_Pump.onnx", opts);
        this.sessionDump = loadSession(modelDir, "Model_Dump.onnx", opts);
    }

    private OrtSession loadSession(String dir, String fileName, OrtSession.SessionOptions opts) {
        try {
            String path = dir + "/" + fileName;
            java.io.File f = new java.io.File(path);
            if (f.exists()) return env.createSession(path, opts);
        } catch (Exception e) {}
        return null;
    }

    // --- 🔥 HÀM MỚI: PREDICT BATCH 🔥 ---
    // Input: List các mảng feature (mỗi mảng 41 phần tử)
    // Output: List kết quả tương ứng
    public List<DcaPredictionResult> predictBatch(List<float[]> batchFeatures) {
        int batchSize = batchFeatures.size();
        if (batchSize == 0) return new ArrayList<>();

        // 1. Flatten dữ liệu: Chuyển List<float[]> thành 1 mảng float khổng lồ 1 chiều
        // Kích thước = batchSize * 41
        FloatBuffer buffer = FloatBuffer.allocate(batchSize * NUM_FEATURES);
        for (float[] f : batchFeatures) {
            buffer.put(f);
        }
        buffer.flip();

        List<DcaPredictionResult> results = new ArrayList<>(batchSize);

        // Khởi tạo giá trị mặc định
        float[] riskArr = new float[batchSize];
        float[] rewardArr = new float[batchSize];
        float[] pumpArr = new float[batchSize];
        float[] dumpArr = new float[batchSize];

        try {
            // Chạy Batch cho từng Model (Chỉ tạo Tensor 4 lần thay vì 4 * batchSize lần)
            runBatchRegression(sessionRisk, buffer, batchSize, riskArr, -0.1f);
            buffer.rewind(); // Tua lại buffer để dùng cho model sau

            runBatchRegression(sessionReward, buffer, batchSize, rewardArr, 0.05f);
            buffer.rewind();

            runBatchRegression(sessionPump, buffer, batchSize, pumpArr, 0.0f);
            buffer.rewind();

            runBatchRegression(sessionDump, buffer, batchSize, dumpArr, 0.0f);

        } catch (Exception e) {
            LOG.error("Batch inference error: {}", e.getMessage());
        }

        // Gom kết quả lại
        for (int i = 0; i < batchSize; i++) {
            results.add(new DcaPredictionResult(riskArr[i], rewardArr[i], pumpArr[i], dumpArr[i]));
        }
        return results;
    }

    private void runBatchRegression(OrtSession session, FloatBuffer buffer, int batchSize, float[] outputArr, float defaultVal) {
        if (session == null) {
            Arrays.fill(outputArr, defaultVal);
            return;
        }

        long[] shape = new long[]{batchSize, NUM_FEATURES};

        try (
                OnnxTensor inputTensor = OnnxTensor.createTensor(env, buffer, shape);
                OrtSession.Result result = session.run(Collections.singletonMap(INPUT_NODE, inputTensor))
        ) {
            // Output của Batch là mảng 2 chiều [batchSize][1]
            float[][] output = (float[][]) result.get(0).getValue();

            for (int i = 0; i < batchSize; i++) {
                outputArr[i] = output[i][0];
            }
        } catch (Exception e) {
            Arrays.fill(outputArr, defaultVal);
        }
    }

    // Helper trích xuất feature (public để bên ngoài gọi trước khi gom batch)
    public float[] extractFeaturesToArray(DcaMarketFeatures f) {
        return new float[] {
                (float)f.distFromHigh24H, (float)f.distMA20, (float)f.instantAlpha, (float)f.recoveryElasticity,
                (float)f.crashVelocity, (float)f.globalRateDownAvg, (float)f.advanceDeclineRatio, (float)f.btcDominance, (float)f.marketBreadthStrength,
                (float)f.btcMomentum15M, (float)f.btcMomentum1H, (float)f.btcMomentum4H, (float)f.btcMomentum24H, (float)f.btcMomentumAcceleration,
                (float)f.ethMomentum15M, (float)f.ethMomentum4H,
                (float)f.momentum15M, (float)f.momentum1H, (float)f.momentum4H, (float)f.momentum24H,
                (float)f.rsi1H, (float)f.rsiChange, (float)f.volumeAnomaly, (float)f.volumeRatio15M_24H,
                (float)f.distFromLow24H, (float)f.maxRateChange60M, (float)f.volatilityShock, (float)f.volatilityTermStructure,
                (float)f.basketMomentum15M, (float)f.basketMomentum1H, (float)f.basketMomentum24H, (float)f.basketRsi14, (float)f.basketVolSpike,
                (float)f.coinFundingRate, (float)f.fundingRateRaw, (float)f.fundingRateAvg24H, (float)f.fundingRateTrend,
                (float)f.hourOfDay, (float)f.dayOfWeek, (float)f.weekOfMonth, (float)f.monthOfYear
        };
    }

    @Override
    public void close() throws Exception {
        if (sessionRisk != null) sessionRisk.close();
        if (sessionReward != null) sessionReward.close();
        if (sessionPump != null) sessionPump.close();
        if (sessionDump != null) sessionDump.close();
        if (env != null) env.close();
    }
}