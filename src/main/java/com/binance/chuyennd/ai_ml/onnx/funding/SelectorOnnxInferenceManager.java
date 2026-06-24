package com.binance.chuyennd.ai_ml.onnx.funding;

import ai.onnxruntime.*;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.FloatBuffer;
import java.util.*;

/**
 * TASK-109 bước 2 — Selector inference Java (Mức B: wire realtime vào engine).
 *
 * Load 4 model ONNX selector (4h/12h/24h/72h, convert từ .ubj ở bước 1) qua onnxruntime, predict P(win)
 * = P(coin chạm +6% trong horizon H) cho 45 feature (40 Tool1 f0..f39 + 5 OI). ĐỒNG BỘ Python:
 *   - 45 feature ĐÚNG thứ tự FEAT = convertFeaturesToArray (40) + [oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy].
 *   - ONNX classifier output: [label(N), probabilities(N,2)] → lấy float[][] cột [1] = P(win) (KHỚP bước 1 verify).
 *   - KHÔNG scale (train không scale). missing/NaN: onnxruntime xử lý như XGBoost (split default).
 *
 * Tái dùng pattern FundingOnnxInferenceManager (tìm output float[][]), nhưng 4 model + 45 feat + cột P(win).
 */
public class SelectorOnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(SelectorOnnxInferenceManager.class);

    public static final String[] HORIZONS = {"4h", "12h", "24h", "72h"};
    public static final int NUM_FEATURES = 45;
    public static final String[] OI_NAMES = {"oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"};

    private final OrtEnvironment env;
    private final OrtSession[] sessions = new OrtSession[HORIZONS.length];
    private final String[] inputName = new String[HORIZONS.length];

    /** @param modelDir thư mục chứa model_4h.onnx ... model_72h.onnx (bước 1) */
    public SelectorOnnxInferenceManager(String modelDir) throws OrtException {
        this(modelDir, Math.min(4, Runtime.getRuntime().availableProcessors()));
    }

    public SelectorOnnxInferenceManager(String modelDir, int intraOpThreads) throws OrtException {
        this.env = OrtEnvironment.getEnvironment();
        for (int h = 0; h < HORIZONS.length; h++) {
            String path = modelDir + "/model_" + HORIZONS[h] + ".onnx";
            OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
            opts.addConfigEntry("session.disable_cpu_mem_arena", "1");
            opts.setIntraOpNumThreads(intraOpThreads);
            opts.setInterOpNumThreads(1);
            sessions[h] = env.createSession(path, opts);
            inputName[h] = sessions[h].getInputInfo().keySet().iterator().next();
            LOG.info("🧠 Selector {} loaded: {} (input='{}')", HORIZONS[h], path, inputName[h]);
        }
    }

    /**
     * 45 feature ĐÚNG thứ tự train/generate Python: 40 Tool1 (convertFeaturesToArray) + 5 OI.
     * oi5 theo thứ tự OI_NAMES; nếu thiếu OI tại (symbol,ts) truyền NaN (XGBoost/ONNX xử lý missing).
     */
    public static float[] extractFeatures45(FundingMarketFeatures f, float[] oi5) {
        if (oi5 == null || oi5.length != 5) throw new IllegalArgumentException("oi5 phải có 5 phần tử (OI_NAMES)");
        float[] x = new float[NUM_FEATURES];
        // 40 Tool1 — KHỚP HỆT ExportFeaturesForPythonTool.convertFeaturesToArray (nguồn sinh ff_*.bin)
        float[] t1 = {
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength,
                f.rateDown15MAvg, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock,
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike,
                f.coinFundingRate, f.basketFundingAvg, f.fundingRateAvg24H, f.fundingRateTrend,
                f.fundingPercentileCoin, f.fundingZCoin, f.fundingPersistence, f.fundingSum24h, f.fundingAbs,
                f.volumeZCoin, f.volumeTrend,
                f.distFromHigh24H, f.rangePosition24H, f.atrSqueeze, f.relStrengthBtc24H,
                f.fundingRankCS, f.volumeZRankCS, f.momentumRankCS,
                f.ret15m, f.rvol15m, f.volumeZ5m, f.closePosRange15m, f.wickRatio15m
        };
        System.arraycopy(t1, 0, x, 0, 40);
        System.arraycopy(oi5, 0, x, 40, 5);
        return x;
    }

    /** Predict P(win) cho 1 horizon, batch các điểm. Trả float[batchSize] = P(win). */
    public float[] predictWin(int horizonIdx, List<float[]> batch) {
        int n = batch.size();
        if (n == 0) return new float[0];
        FloatBuffer buf = FloatBuffer.allocate(n * NUM_FEATURES);
        for (float[] f : batch) buf.put(f);
        buf.flip();
        long[] shape = {n, NUM_FEATURES};
        float[] win = new float[n];
        try (OnnxTensor in = OnnxTensor.createTensor(env, buf, shape);
             OrtSession.Result res = sessions[horizonIdx].run(Collections.singletonMap(inputName[horizonIdx], in))) {
            float[][] prob = findProb2D(res);   // (N,2): cột [1] = P(win)
            if (prob == null) throw new RuntimeException("Selector " + HORIZONS[horizonIdx] + ": không tìm thấy output (N,2)");
            for (int i = 0; i < n; i++) win[i] = prob[i][1];
        } catch (Exception e) {
            LOG.error("❌ Selector {} inference lỗi: {}", HORIZONS[horizonIdx], e.getMessage());
            Arrays.fill(win, Float.NaN);
        }
        return win;
    }

    /** Predict cả 4 horizon cho 1 batch. Trả float[batchSize][4] theo thứ tự HORIZONS. */
    public float[][] predictAll4(List<float[]> batch) {
        int n = batch.size();
        float[][] out = new float[n][HORIZONS.length];
        for (int h = 0; h < HORIZONS.length; h++) {
            float[] w = predictWin(h, batch);
            for (int i = 0; i < n; i++) out[i][h] = w[i];
        }
        return out;
    }

    /** Tìm output float[][] (N,2) trong kết quả — classifier ONNX trả [label, probabilities]. */
    private static float[][] findProb2D(OrtSession.Result res) throws OrtException {
        for (Map.Entry<String, OnnxValue> e : res) {
            Object v = e.getValue().getValue();
            if (v instanceof float[][]) {
                float[][] a = (float[][]) v;
                if (a.length > 0 && a[0].length == 2) return a;
            }
        }
        // fallback: index 1 (label ở 0, prob ở 1)
        if (res.size() > 1) {
            Object v1 = res.get(1).getValue();
            if (v1 instanceof float[][]) return (float[][]) v1;
        }
        return null;
    }

    @Override
    public void close() throws Exception {
        for (OrtSession s : sessions) if (s != null) s.close();
        if (env != null) env.close();
    }
}
