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

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.*;

/**
 * BƯỚC 4 (ROADMAP) — Walk-Forward (WFO) cho MODEL gate 15m. Java điều phối, gọi Python CHỈ để train
 * (đưa cả WFO sang Python = rủi ro lệch logic feature/backtest quá cao — giữ Java cho phần đã verify 0.000000).
 *
 * <p><b>Kiến trúc 3 pha tách REPLAY khỏi PREDICT</b> (nút cổ chai là replay ~30-45s/ngày, KHÔNG phải train 3s):
 * <ol>
 *   <li><b>REPLAY 1 LẦN</b>: replay mọi phút toàn range → giữ trong RAM featureStore {@code TreeMap<ts,MarketFeatures>}
 *       + labelStore {@code TreeMap<ts,Float>} (label_oldbasket mọi phút). Xuất CSV mọi-phút cho Python train.
 *       Feature market-level (1 vector 33ch/phút) → ~2.6M phút × 33 float ≈ 350MB, vừa RAM Oracle 23GB.</li>
 *   <li><b>WFO LOOP</b> (expanding, OOS=step=3 tháng, không chồng lấn): mỗi fold k gọi
 *       {@code python train_gate_fold.py --csv <store> --cutoff <t_k> --out model_k.onnx} (train 3s)
 *       → load ONNX qua {@link OnnxInferenceManager} → predict đoạn OOS [t_k, t_k+3m] từ featureStore RAM (vài giây)
 *       → ghi set {@code ai_pred_market_gate_wfo}. Ghép các đoạn OOS = chuỗi walk-forward liên tục,
 *       mỗi đoạn do model CHƯA thấy nó dự báo (không leak).</li>
 *   <li><b>BACKTEST</b> (ngoài): {@code GATE_SET=ai_pred_market_gate_wfo GoldenBacktest} + chấm bằng V4.</li>
 * </ol>
 *
 * <p><b>Chống lệch ngầm</b>: feature extract + predict ĐỀU Java (cùng ComprehensiveMarketFeatureExtractor +
 * OnnxInferenceManager đã verify Java↔Python 0.000000). Python CHỈ train thuần XGBoost→ONNX, không có nhánh
 * logic feature/backtest nào. predRisk4H giữ từ set cũ (isolate biến = predReturn15M).
 *
 * <p>Chạy ORACLE. Args: [start=20210101] [end=20260601] [oosMonths=3] [csvStore] [modelTmpDir] [setName] [pythonScript]
 */
public class WFOGateRunner {

    static final Logger LOG = LoggerFactory.getLogger(WFOGateRunner.class);
    static final long H15 = 15 * 60_000L;
    static final int WARMUP_HOURS = 48;
    static final String DEFAULT_SET = "ai_pred_market_gate_wfo";
    static final String OLD_SET = "ai_pred_market_full_basket_v2"; // nguồn predRisk4H

    // expanding: train luôn bắt đầu từ TRAIN_ANCHOR; OOS đầu tiên bắt đầu khi đã đủ tối thiểu lịch sử
    static final String TRAIN_ANCHOR = "20210101";
    static final String FIRST_OOS = "20230101"; // 2 năm lịch sử tối thiểu trước fold OOS đầu

    public static void main(String[] args) {
        try {
            System.setProperty("ai.onnxruntime.disable_telemetry", "true");
            DataManagerAerospikeFloatSim.setThreadCount(4);
            String start = args.length > 0 ? args[0] : TRAIN_ANCHOR;
            String end = args.length > 1 ? args[1] : "20260601";
            int oosMonths = args.length > 2 ? Integer.parseInt(args[2]) : 3;
            String home = System.getProperty("user.home");
            String csvStore = args.length > 3 ? args[3] : home + "/claudedata/wfo_feature_store.csv";
            String modelTmpDir = args.length > 4 ? args[4] : home + "/claudedata/wfo_models";
            String outFile = args.length > 5 ? args[5] : home + "/claudedata/wfo_gate_pred.csv";
            String pyScript = args.length > 6 ? args[6] : home + "/java/simulator/train_gate_fold.py";
            new WFOGateRunner().run(start, end, oosMonths, csvStore, modelTmpDir, outFile, pyScript);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ WFOGateRunner FAIL", e);
            System.exit(1);
        }
    }

    // feature store trong RAM (replay 1 lần)
    private final TreeMap<Long, MarketFeatures> featureStore = new TreeMap<>();
    private final TreeMap<Long, Float> labelStore = new TreeMap<>();
    private TreeMap<Long, AiPredictionData> oldPred;

    void run(String start, String end, int oosMonths, String csvStore, String modelTmpDir,
             String outFile, String pyScript) throws Exception {
        long fairStart = Utils.sdfFile.parse(start).getTime();
        long evalEnd = Utils.sdfFile.parse(end).getTime();
        new File(modelTmpDir).mkdirs();

        LOG.info("🚀 WFO GATE | {} -> {} | OOS={}m | csv={} | out={}", start, end, oosMonths, csvStore, outFile);

        // ===== PHA 1: REPLAY 1 LẦN -> featureStore + labelStore + CSV =====
        replayAndBuildStore(fairStart, evalEnd, csvStore);
        if (featureStore.isEmpty()) { LOG.error("⛔ featureStore rỗng — dừng."); return; }
        LOG.info("✅ PHA 1 xong: featureStore={} phút | label={} | range {} .. {}",
                featureStore.size(), labelStore.size(),
                Utils.normalizeDateYYYYMMDD(featureStore.firstKey()), Utils.normalizeDateYYYYMMDD(featureStore.lastKey()));

        oldPred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospikeSet(OLD_SET);
        LOG.info("   predRisk4H từ set cũ: {} mốc", oldPred.size());

        // ===== PHA 2: WFO LOOP expanding =====
        long firstOos = Utils.sdfFile.parse(FIRST_OOS).getTime();
        List<long[]> folds = buildExpandingFolds(firstOos, evalEnd, oosMonths);
        LOG.info("📐 {} fold expanding (OOS={}m): ", folds.size(), oosMonths);
        for (int i = 0; i < folds.size(); i++) {
            LOG.info("   fold {}: train[{} -> {}] OOS[{} -> {}]", i,
                    TRAIN_ANCHOR, Utils.normalizeDateYYYYMMDD(folds.get(i)[0]),
                    Utils.normalizeDateYYYYMMDD(folds.get(i)[0]), Utils.normalizeDateYYYYMMDD(folds.get(i)[1]));
        }

        long totalWritten = 0;
        // GHI FILE thay Aerospike: ghi 226 qua mạng = 65 rec/s (nghẽn 99% thời gian, đo bằng smoke3).
        // File local = tức thì. File gate WFO interface cho backtest đọc qua GATE_FILE. 1 writer cho cả chuỗi OOS.
        try (BufferedWriter gw = new BufferedWriter(new FileWriter(outFile))) {
            gw.write("timestamp,predReturn15M,predRisk4H"); gw.newLine();
            for (int i = 0; i < folds.size(); i++) {
                long cutoff = folds.get(i)[0];   // train < cutoff ; OOS = [cutoff, oosEnd)
                long oosEnd = folds.get(i)[1];
                String cutoffStr = Utils.normalizeDateYYYYMMDD(cutoff).replace("-", "");
                String modelDir = modelTmpDir + "/fold_" + i;
                new File(modelDir).mkdirs();

                // (a) gọi Python train tới cutoff
                LOG.info("🔧 fold {} — train Python (cutoff={})...", i, cutoffStr);
                int rc = runPythonTrain(pyScript, csvStore, cutoffStr, modelDir);
                if (rc != 0) { LOG.error("⛔ fold {} train rc={} — DỪNG (không bỏ qua, tránh chuỗi WFO thủng).", i, rc); return; }

                // (b) predict đoạn OOS từ featureStore RAM (nhanh ~0s) → ghi file (tức thì)
                long written = predictOOSToFile(modelDir, cutoff, oosEnd, gw);
                totalWritten += written;
                LOG.info("✅ fold {} xong: ghi {} pred OOS [{} -> {})", i, written,
                        Utils.normalizeDateYYYYMMDD(cutoff), Utils.normalizeDateYYYYMMDD(oosEnd));
            }
        }

        LOG.info("🎯 WFO DONE: {} fold, tổng {} pred OOS -> file {}", folds.size(), totalWritten, outFile);
        LOG.info("   Bước tiếp: GATE_FILE={} java ... GoldenBacktest FAST  (chấm bằng HPOFitnessCalculatorV4)", outFile);
    }

    /** PHA 1: replay mọi phút, lưu feature + label vào RAM, đồng thời xuất CSV mọi-phút cho Python train. */
    private void replayAndBuildStore(long fairStart, long evalEnd, String csvStore) throws Exception {
        long warmupStart = fairStart - WARMUP_HOURS * Utils.TIME_HOUR;
        TreeMap<Long, MarketDataObject> time2Rate = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();
        double featChecksum = 0;
        long nRows = 0;

        try (BufferedWriter w = new BufferedWriter(new FileWriter(csvStore))) {
            // header: toCSVHeader ĐÃ gồm "timestamp,...,futureReturn15M,maxDrawdownNext4H".
            // Cắt 2 cột label cũ, thay bằng label_oldbasket. (toCSVRow khớp header này — cùng class, đồng bộ.)
            String base = new MarketFeatures().toCSVHeader();
            int cut = base.indexOf(",futureReturn15M");
            if (cut > 0) base = base.substring(0, cut);
            w.write(base + ",label_oldbasket");
            w.newLine();

            long day = Utils.getDate(warmupStart);
            long lastDay = Utils.getDate(evalEnd);
            int dayCount = 0;
            while (day <= lastDay) {
                try {
                    TreeMap<Long, Map<String, KlineObjectSimple>> today =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                    TreeMap<Long, Map<String, KlineObjectSimple>> tomorrow =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day + Utils.TIME_DAY);
                    TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>();
                    if (today != null) lookup.putAll(today);
                    if (tomorrow != null) lookup.putAll(tomorrow);
                    if (today == null) { day += Utils.TIME_DAY; continue; }

                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                        long ts = e.getKey();
                        Map<String, KlineObjectSimple> snap = e.getValue();
                        HistoryManager.getInstance().updateHistory(snap);
                        CoinRankManager.getInstance().getTopCoin(ts);
                        if (ts < fairStart || ts > evalEnd) continue;

                        // MỌI PHÚT (không de-overlap — WFO cần predict mọi phút để backtest đủ độ phủ)
                        MarketFeatures f = extractor.extractAllFeatures(ts, snap, time2Rate.get(ts));
                        if (f == null) continue;

                        List<String> basketOld = HistoryManager.getInstance().findPotentialLosers(ts);
                        float labOld = basketMaxGain(lookup, ts, basketOld);

                        featureStore.put(ts, f);
                        labelStore.put(ts, labOld);
                        featChecksum += f.momentum15M + f.volatility15M + f.basketVolSpike;

                        // CSV: toCSVRow ĐÃ bắt đầu bằng timestamp + kết thúc bằng 2 cột label cũ → cắt 2 cột cuối,
                        // thêm label_oldbasket. KHỚP header (base + label_oldbasket). KHÔNG thêm ts thừa.
                        String row = f.toCSVRow();
                        int idx = nthLastComma(row, 2);
                        if (idx > 0) row = row.substring(0, idx);
                        w.write(row + "," + fmt(labOld));
                        w.newLine();
                        nRows++;
                    }
                } catch (Exception ex) {
                    LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(day), ex.getMessage());
                }
                day += Utils.TIME_DAY;
                if (++dayCount % 30 == 0) LOG.info("... replay {} ngày | rows={} | day={}",
                        dayCount, nRows, Utils.normalizeDateYYYYMMDD(day));
            }
        }
        LOG.info("   featChecksum={} (so 2 lần chạy để check determinism)", String.format("%.6f", featChecksum));
    }

    /** Sinh fold expanding: mỗi fold OOS = [cutoff, cutoff+oosMonths), bước trượt = oosMonths (không chồng lấn). */
    private List<long[]> buildExpandingFolds(long firstOos, long evalEnd, int oosMonths) {
        List<long[]> folds = new ArrayList<>();
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(firstOos);
        while (true) {
            long cutoff = c.getTimeInMillis();
            if (cutoff >= evalEnd) break;
            c.add(Calendar.MONTH, oosMonths);
            long oosEnd = Math.min(c.getTimeInMillis(), evalEnd);
            folds.add(new long[]{cutoff, oosEnd});
            if (oosEnd >= evalEnd) break;
        }
        return folds;
    }

    /** Gọi Python train_gate_fold.py (train < cutoff -> ONNX trong modelDir). Trả exit code. */
    private int runPythonTrain(String pyScript, String csv, String cutoffStr, String modelDir) throws Exception {
        // dùng venv python; train_gate_fold.py nhận env DATA/CUTOFF/OUT_DIR (giống train_gate15m_v2_final.py)
        String home = System.getProperty("user.home");
        String py = home + "/envs/xgb-env/bin/python";
        ProcessBuilder pb = new ProcessBuilder(py, pyScript);
        pb.environment().put("DATA", csv);
        pb.environment().put("CUTOFF", cutoffStr);
        pb.environment().put("OUT_DIR", modelDir);
        pb.redirectErrorStream(true);
        Process p = pb.start();
        try (Scanner sc = new Scanner(p.getInputStream())) {
            while (sc.hasNextLine()) {
                String line = sc.nextLine();
                if (line.contains("OOS IC") || line.contains("Export") || line.contains("Error") || line.contains("Traceback"))
                    LOG.info("   [py] {}", line);
            }
        }
        return p.waitFor();
    }

    /** Predict đoạn OOS [cutoff, oosEnd) từ featureStore RAM (KHÔNG replay lại), ghi vào file CSV gate.
     *  predict ~0s (đo smoke3); ghi file local tức thì (thay ghi Aerospike 226 qua mạng = 65 rec/s nghẽn 99%). */
    private long predictOOSToFile(String modelDir, long cutoff, long oosEnd, BufferedWriter gw) throws Exception {
        long n = 0;
        try (OnnxInferenceManager brain = new OnnxInferenceManager(modelDir)) {
            for (Map.Entry<Long, MarketFeatures> e : featureStore.subMap(cutoff, true, oosEnd, false).entrySet()) {
                long ts = e.getKey();
                float pred15 = brain.predictAll(e.getValue()).return15M;
                AiPredictionData old = oldPred.get(ts);
                float risk4 = old != null ? old.predRisk4H : 0f;
                gw.write(ts + "," + fmt(pred15) + "," + fmt(risk4));
                gw.newLine();
                n++;
            }
        }
        return n;
    }

    // ===== helper copy từ ExportGate15mV2 (giữ đồng bộ logic label) =====
    private float basketMaxGain(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts, List<String> basket) {
        if (basket == null || basket.isEmpty()) return 0f;
        NavigableMap<Long, Map<String, KlineObjectSimple>> future = data.subMap(ts, false, ts + H15, true);
        if (future.isEmpty()) return 0f;
        Map<String, KlineObjectSimple> atT = data.get(ts);
        if (atT == null) return 0f;
        float sum = 0; int cnt = 0;
        for (String sym : basket) {
            KlineObjectSimple k0 = atT.get(sym);
            if (k0 == null || k0.priceClose <= 0) continue;
            float entry = (float) k0.priceClose;
            float maxGain = 0;
            for (Map<String, KlineObjectSimple> snap : future.values()) {
                KlineObjectSimple k = snap.get(sym);
                if (k != null && k.maxPrice > 0) {
                    float g = (float) ((k.maxPrice - entry) / entry);
                    if (g > maxGain) maxGain = g;
                }
            }
            sum += maxGain; cnt++;
        }
        return cnt > 0 ? sum / cnt : 0f;
    }

    private static int nthLastComma(String s, int n) {
        int count = 0;
        for (int i = s.length() - 1; i >= 0; i--) if (s.charAt(i) == ',') { if (++count == n) return i; }
        return -1;
    }
    private static String fmt(float v) {
        if (Float.isNaN(v) || Float.isInfinite(v)) return "0.000000";
        return String.format(Locale.US, "%.8f", v);
    }
}
