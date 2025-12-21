package com.binance.chuyennd.ai_ml.onnx.entry;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.Serializable;
import java.nio.FloatBuffer;
import java.util.*;

public class OnnxInferenceManager implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(OnnxInferenceManager.class);
    private final OrtEnvironment env;
    private final OrtSession.SessionOptions opts;

    // Các bộ dự đoán Ensemble (Thay vì session lẻ)
    private final EnsemblePredictor p15M, p1H, p4H, p24H, pRisk4H, pRisk24H;

    public OnnxInferenceManager(String modelDir) throws OrtException {
        LOG.info("🧠 Initializing AI Brain V4 (Ensemble Mode) from: {}", modelDir);
        this.env = OrtEnvironment.getEnvironment();
        this.opts = new OrtSession.SessionOptions();
        opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        opts.setIntraOpNumThreads(1); // Tối ưu cho chạy nhiều model nhỏ

        // Khởi tạo 6 bộ não con cho 6 target
        this.p15M = new EnsemblePredictor(modelDir, "Return15M");
        this.p1H = new EnsemblePredictor(modelDir, "Return1H");
        this.p4H = new EnsemblePredictor(modelDir, "Return4H");
        this.p24H = new EnsemblePredictor(modelDir, "Return24H");
        this.pRisk4H = new EnsemblePredictor(modelDir, "maxDrawdown4H");
        this.pRisk24H = new EnsemblePredictor(modelDir, "maxDrawdown24H");

        LOG.info("✅ All Ensemble Models loaded!");
    }

    public PredictionResult predictAll(MarketFeatures f) {
        try {
            // Convert Features sang mảng float[] chuẩn
            float[] rawFeatures = extractFeaturesToArray(f);

            // Dự đoán song song hoặc tuần tự
            float r15 = p15M.predict(rawFeatures);
            float r1 = p1H.predict(rawFeatures);
            float r4 = p4H.predict(rawFeatures);
            float r24 = p24H.predict(rawFeatures);
            float risk4 = pRisk4H.predict(rawFeatures);
            float risk24 = pRisk24H.predict(rawFeatures);

            return new PredictionResult(r15, r1, r4, r24, risk4, risk24);
        } catch (Exception e) {
            LOG.error("❌ Inference Error", e);
            return new PredictionResult(0, 0, 0, 0, 0, 0);
        }
    }

    /**
     * Class nội bộ xử lý logic Ensemble (Voting)
     */
    private class EnsemblePredictor {
        private OrtSession scaler;
        private OrtSession modelXGB;
        private OrtSession modelLGBM;
        private OrtSession modelCat;

        // Trọng số chuẩn hóa (nếu thiếu model nào thì chia lại trọng số)
        private double wXGB = 0, wLGBM = 0, wCat = 0;
        private final String targetName;

        public EnsemblePredictor(String dir, String target) {
            this.targetName = target;
            try {
                // 1. Load Weights từ file txt
                double[] rawWeights = loadWeights(dir + "/Weights_" + target + ".txt");

                // 2. Load Scaler (Bắt buộc phải có)
                this.scaler = env.createSession(dir + "/Scaler_" + target + ".onnx", opts);

                // 3. Load Models & Gán Weight (Thứ tự Python: [XGB, LGBM, Cat])
                // Load XGB
                if (fileExists(dir + "/Model_Regressor_" + target + "_XGB.onnx")) {
                    this.modelXGB = env.createSession(dir + "/Model_Regressor_" + target + "_XGB.onnx", opts);
                    this.wXGB = (rawWeights.length > 0) ? rawWeights[0] : 0;
                }

                // Load LGBM
                if (fileExists(dir + "/Model_Regressor_" + target + "_LGBM.onnx")) {
                    this.modelLGBM = env.createSession(dir + "/Model_Regressor_" + target + "_LGBM.onnx", opts);
                    this.wLGBM = (rawWeights.length > 1) ? rawWeights[1] : 0;
                }

                // Load CatBoost (Hiện tại bạn đang thiếu file này, code sẽ tự handle)
                if (fileExists(dir + "/Model_Regressor_" + target + "_Cat.onnx")) {
                    this.modelCat = env.createSession(dir + "/Model_Regressor_" + target + "_Cat.onnx", opts);
                    this.wCat = (rawWeights.length > 2) ? rawWeights[2] : 0;
                }

                // 4. Normalize Weights (Phòng trường hợp thiếu file CatBoost hoặc file Weights bị lệch)
                normalizeWeights();

                LOG.info("  -> Target {}: Loaded Weights [XGB:{:.2f}, LGBM:{:.2f}, Cat:{:.2f}]",
                        target, wXGB, wLGBM, wCat);

            } catch (Exception e) {
                LOG.error("  -> Failed to load ensemble for " + target, e);
            }
        }

        private void normalizeWeights() {
            double sum = 0;
            if (modelXGB != null) sum += wXGB; else wXGB = 0;
            if (modelLGBM != null) sum += wLGBM; else wLGBM = 0;
            if (modelCat != null) sum += wCat; else wCat = 0;

            if (sum > 0) {
                wXGB /= sum; wLGBM /= sum; wCat /= sum;
            } else {
                // Fallback nếu lỗi hết: dùng XGB làm chính
                if (modelXGB != null) wXGB = 1.0;
            }
        }

        public float predict(float[] rawFeatures) throws OrtException {
            if (scaler == null) return 0f;

            // 1. Scale dữ liệu
            float[][] scaledFeatures = runModel(scaler, rawFeatures); // Scaler trả về array đã scale
            float[] inputForModel = scaledFeatures[0];

            // 2. Chạy từng model con
            float finalPred = 0;
            if (modelXGB != null && wXGB > 0) {
                finalPred += runModel(modelXGB, inputForModel)[0][0] * wXGB;
            }
            if (modelLGBM != null && wLGBM > 0) {
                finalPred += runModel(modelLGBM, inputForModel)[0][0] * wLGBM;
            }
            if (modelCat != null && wCat > 0) {
                finalPred += runModel(modelCat, inputForModel)[0][0] * wCat;
            }

            return finalPred;
        }

        // Helper chạy 1 session ONNX
        private float[][] runModel(OrtSession session, float[] inputData) throws OrtException {
            long[] shape = new long[]{1, inputData.length};
            OnnxTensor tensor = OnnxTensor.createTensor(env, FloatBuffer.wrap(inputData), shape);
            // Tên node input thường là "float_input", nếu lỗi hãy check lại bằng Netron
            try (OrtSession.Result res = session.run(Collections.singletonMap("float_input", tensor))) {
                return (float[][]) res.get(0).getValue();
            }
        }
    }

    // --- CÁC HÀM TIỆN ÍCH ---

    private double[] loadWeights(String path) {
        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            String line = br.readLine();
            if (line == null) return new double[0];
            // Format: "[0.3, 0.5, 0.2]" -> Remove [] -> Split
            line = line.replace("[", "").replace("]", "").trim();
            if (line.isEmpty()) return new double[0];

            String[] parts = line.split(",");
            double[] res = new double[parts.length];
            for (int i = 0; i < parts.length; i++) res[i] = Double.parseDouble(parts[i].trim());
            return res;
        } catch (Exception e) {
            LOG.warn("Could not read weights from {}, assuming equal weights or single model.", path);
            return new double[0];
        }
    }

    private boolean fileExists(String path) {
        return new java.io.File(path).exists();
    }

    private float[] extractFeaturesToArray(MarketFeatures f) {
        // Thứ tự features PHẢI GIỐNG 100% Code Python
        return new float[] {
                (float) f.momentum1M, (float) f.momentum5M, (float) f.momentum15M, (float) f.momentum1H,
                (float) f.momentum4H, (float) f.momentum24H, (float) f.momentumAcceleration,
                (float) f.trendStrengthETH, (float) f.trendConsistency,
                (float) f.volatility1M, (float) f.volatility15M, (float) f.volatility1H,
                (float) f.volatility24H, (float) f.volatilityTermStructure,
                (float) f.advanceDeclineRatio, (float) f.percentAboveMA20, (float) f.volumeRatioUpDown,
                (float) f.marketBreadthStrength, (float) f.btcDominance,
                (float) f.rsi14, (float) f.volumeSpike, (float) f.distMA20,
                (float) f.fundingRateRaw, (float) f.fundingRateAvg24H, (float) f.fundingRateTrend,
                (float) f.hourOfDay, (float) f.dayOfWeek, (float) f.weekOfMonth, (float) f.monthOfYear,
                (float) f.basketMomentum15M, (float) f.basketMomentum1H, (float) f.basketRsi14, (float) f.basketVolSpike
        };
    }

    @Override
    public void close() throws Exception {
        // Close all sessions inside predictors
        closePredictor(p15M); closePredictor(p1H); closePredictor(p4H);
        closePredictor(p24H); closePredictor(pRisk4H); closePredictor(pRisk24H);
        if (env != null) env.close();
    }

    private void closePredictor(EnsemblePredictor p) throws OrtException {
        if (p == null) return;
        if (p.scaler != null) p.scaler.close();
        if (p.modelXGB != null) p.modelXGB.close();
        if (p.modelLGBM != null) p.modelLGBM.close();
        if (p.modelCat != null) p.modelCat.close();
    }

    public static class PredictionResult implements Serializable {
        public float return15M, return1H, return4H, return24H;
        public float riskDrawdown4H, riskDrawdown24H;
        public PredictionResult(float r15, float r1, float r4, float r24, float risk4, float risk24) {
            this.return15M = r15; this.return1H = r1; this.return4H = r4;
            this.return24H = r24; this.riskDrawdown4H = risk4; this.riskDrawdown24H = risk24;
        }
    }
}