package com.binance.chuyennd.ai_ml.features.export.gate;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * TASK-043 — Generate gate 15m v2 prediction → set Aerospike MỚI {@code ai_pred_market_gate_v2}.
 *
 * <p><b>ĐỒNG BỘ TUYỆT ĐỐI</b> (tránh sai lệch ngầm — yêu cầu cốt lõi của Uni):
 * <ul>
 *   <li>Khung đọc/replay GIỐNG HỆT {@link ExportGate15mV2} đã sinh CSV train: cùng
 *       {@code readDataFromAerospike1M} (theo ngày), cùng warmup 48h, cùng nuôi history mỗi phút,
 *       cùng {@code CoinRankManager.getTopCoin}. → snapshot tại t khi generate = snapshot khi train.</li>
 *   <li>Feature: {@link OnnxInferenceManager#predictAll} tự gọi {@code extractFeaturesV3Full} (33 feat,
 *       đúng thứ tự model XGBoost đã train theo list V3FULL). 1 nguồn sự thật cho thứ tự feature.</li>
 *   <li>Model: XGBoost→ONNX ở MODEL_DIR mới, KHÔNG scaler (raw feature). predRisk4H GIỮ NGUYÊN từ set
 *       cũ (isolate đúng biến đổi = predReturn15M).</li>
 * </ul>
 *
 * <p><b>VERIFY trước khi ghi</b>: in predReturn15M tại 3 ts tham chiếu để so ONNX Python
 * (ts=1748736000000→0.006784, 1748736900000→0.007545, 1748737800000→0.006802). Lệch &gt; 1e-4 ⇒ DỪNG.
 *
 * <p>Generate tại MỌI mốc {@code ts % 15min == 0} (khớp cách backtest tra theo phút). Chạy ORACLE.
 * Args: [mode=VERIFY|FULL] [startYYYYMMDD] [endYYYYMMDD] [modelDir] [setName]
 */
public class GenerateGate15mV2Predictions {

    static final Logger LOG = LoggerFactory.getLogger(GenerateGate15mV2Predictions.class);
    static final long H15 = 15 * 60_000L;
    static final int WARMUP_HOURS = 48;
    static final String DEFAULT_SET = "ai_pred_market_gate_v2";
    static final String OLD_SET = "ai_pred_market_full_basket_v2"; // nguồn predRisk4H giữ nguyên

    // 3 mốc tham chiếu OOS + giá trị ONNX Python (verify đồng bộ Java↔Python)
    static final long[] REF_TS = {1748736000000L, 1748736900000L, 1748737800000L};
    static final double[] REF_VAL = {0.006784, 0.007545, 0.006802};
    static final double REF_TOL = 1e-3;

    public static void main(String[] args) {
        try {
            System.setProperty("ai.onnxruntime.disable_telemetry", "true");
            DataManagerAerospikeFloatSim.setThreadCount(4);
            String mode = args.length > 0 ? args[0] : "VERIFY";
            String startStr = args.length > 1 ? args[1] : "20250601";
            String endStr = args.length > 2 ? args[2] : "20260601";
            String modelDir = args.length > 3 ? args[3]
                    : (System.getProperty("user.home") + "/claudedata/gate_model_v2");
            String setName = args.length > 4 ? args[4] : DEFAULT_SET;
            new GenerateGate15mV2Predictions().run(mode, startStr, endStr, modelDir, setName);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ GenerateGate15mV2 FAIL", e);
            System.exit(1);
        }
    }

    void run(String mode, String startStr, String endStr, String modelDir, String setName) throws Exception {
        boolean verifyOnly = mode.equalsIgnoreCase("VERIFY");
        long fairStart = Utils.sdfFile.parse(startStr).getTime();
        long evalEnd = Utils.sdfFile.parse(endStr).getTime();
        long warmupStart = fairStart - WARMUP_HOURS * Utils.TIME_HOUR;
        LOG.info("🧠 GENERATE gate15m v2 | mode={} | {} -> {} | model={} | set={}",
                mode, startStr, endStr, modelDir, setName);

        LOG.info("📥 Nạp market rate data...");
        TreeMap<Long, MarketDataObject> time2Rate = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        LOG.info("   market rate: {} mốc", time2Rate.size());

        // predRisk4H giữ nguyên từ set cũ — nạp full 1 lần (chỉ để tra cứu theo ts)
        LOG.info("📥 Nạp predRisk4H từ set cũ {} (giữ nguyên)...", OLD_SET);
        TreeMap<Long, AiPredictionData> oldPred =
                DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospikeSet(OLD_SET);
        LOG.info("   set cũ: {} mốc (lấy predRisk4H)", oldPred.size());

        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();

        Map<Long, Float> refFound = new HashMap<>();
        long nPred = 0, nSaved = 0;
        float firstPred = Float.NaN;
        boolean allSame = true;
        Map<Long, AiPredictionData> batch = new HashMap<>();

        try (OnnxInferenceManager brain = new OnnxInferenceManager(modelDir)) {
            long day = Utils.getDate(warmupStart);
            long lastDay = Utils.getDate(evalEnd);
            int dayCount = 0;
            while (day <= lastDay) {
                try {
                    TreeMap<Long, Map<String, KlineObjectSimple>> today =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                    if (today == null) { day += Utils.TIME_DAY; continue; }

                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                        long ts = e.getKey();
                        Map<String, KlineObjectSimple> snap = e.getValue();

                        // nuôi history mỗi phút (GIỐNG HỆT export — đồng bộ snapshot)
                        HistoryManager.getInstance().updateHistory(snap);
                        CoinRankManager.getInstance().getTopCoin(ts);
                        if (ts < fairStart || ts > evalEnd) continue;

                        // GENERATE MỌI PHÚT (giống gate cũ): backtest tra predictionMap.get(time) exact-match
                        // theo phút → nếu chỉ có mốc 15m thì 14/15 phút trả null = bỏ qua entry = lệch độ phủ.

                        MarketFeatures f = extractor.extractAllFeatures(ts, snap, time2Rate.get(ts));
                        if (f == null) continue;

                        float pred15 = brain.predictAll(f).return15M;
                        nPred++;

                        // sanity: output suy biến (hằng số) = feature mismatch âm thầm
                        if (Float.isNaN(firstPred)) firstPred = pred15;
                        else if (Math.abs(pred15 - firstPred) > 1e-9) allSame = false;

                        // bắt mốc tham chiếu để verify Java↔Python
                        for (long rt : REF_TS) if (ts == rt) refFound.put(ts, pred15);

                        if (!verifyOnly) {
                            // giữ nguyên predRisk4H từ set cũ; nếu thiếu set cũ -> 0 (không chặn)
                            AiPredictionData old = oldPred.get(ts);
                            float risk4 = old != null ? old.predRisk4H : 0f;
                            batch.put(ts, new AiPredictionData(ts, pred15, risk4));
                            if (batch.size() >= 5000) {
                                DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatchToSet(setName, batch);
                                nSaved += batch.size();
                                batch.clear();
                            }
                        }
                    }
                } catch (Exception ex) {
                    LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(day), ex.getMessage());
                }
                day += Utils.TIME_DAY;
                if (++dayCount % 20 == 0) LOG.info("... {} ngày | pred={} saved={} | day={}",
                        dayCount, nPred, nSaved, Utils.normalizeDateYYYYMMDD(day));
            }
            if (!verifyOnly && !batch.isEmpty()) {
                DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatchToSet(setName, batch);
                nSaved += batch.size();
            }
        }

        // ===== VERIFY đồng bộ =====
        if (allSame && nPred > 10) {
            LOG.error("⛔ Output HẰNG SỐ ({} mốc cùng giá trị {}) — predictAll nuốt lỗi / feature mismatch. DỪNG.",
                    nPred, firstPred);
            throw new IllegalStateException("Model output constant — feature mismatch nghi ngờ");
        }
        LOG.info("🔎 VERIFY 3 mốc tham chiếu (Java vs ONNX Python):");
        boolean refOk = true;
        for (int i = 0; i < REF_TS.length; i++) {
            Float jv = refFound.get(REF_TS[i]);
            if (jv == null) {
                LOG.warn("   ts={} : Java KHÔNG có mốc này (ngoài range generate?)", REF_TS[i]);
                continue;
            }
            double diff = Math.abs(jv - REF_VAL[i]);
            String verdict = diff <= REF_TOL ? "✅ KHỚP" : "❌ LỆCH";
            LOG.info("   ts={} Java={} Python={} diff={} {}",
                    REF_TS[i], String.format("%.6f", jv), REF_VAL[i], String.format("%.6f", diff), verdict);
            if (diff > REF_TOL) refOk = false;
        }
        if (!refOk) {
            LOG.error("⛔ LỆCH Java↔Python > {} — feature/thứ tự/model KHÔNG đồng bộ. KHÔNG tin set vừa ghi.", REF_TOL);
            throw new IllegalStateException("Java-Python mismatch — dừng để tránh lệch ngầm");
        }
        LOG.info("✅ {} | pred={} | saved={} -> set {}", verifyOnly ? "VERIFY xong (không ghi)" : "GENERATE xong",
                nPred, nSaved, setName);
    }
}
