package com.binance.chuyennd.ai_ml.features.export.gate;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
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
 * <p>Chạy ORACLE. Args: [start=20210101] [end=20260601] [oosMonths=3] [csvStore] [modelTmpDir] [setName] [pythonScript] [minTrainMonths=3]
 */
public class WFOGateRunner {

    static final Logger LOG = LoggerFactory.getLogger(WFOGateRunner.class);
    static final String DEFAULT_SET = "ai_pred_market_gate_wfo";
    static final String OLD_SET = "ai_pred_market_full_basket_v2"; // nguồn predRisk4H

    // expanding: train luôn bắt đầu từ TRAIN_ANCHOR; OOS đầu tiên bắt đầu khi đã đủ tối thiểu lịch sử
    static final String TRAIN_ANCHOR = "20210101";
    // TASK-156: mặc định giảm 24 -> 3 tháng (khớp bước OOS) để fold OOS đầu phủ được 2021-2022 (gốc rễ
    // WFO FAIL 8/17 cửa sổ ZERO_TRADES do gate pred cũ chỉ phủ 2023+ — KHÔNG do thiếu feature data, feature
    // store (wfo_feature_store.csv) đã có sẵn từ TRAIN_ANCHOR 2021-01-01, đo được trước khi sửa).
    static final int DEFAULT_MIN_TRAIN_MONTHS = 3;

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
            int minTrainMonths = args.length > 7 ? Integer.parseInt(args[7]) : DEFAULT_MIN_TRAIN_MONTHS;
            new WFOGateRunner().run(start, end, oosMonths, csvStore, modelTmpDir, outFile, pyScript, minTrainMonths);
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
             String outFile, String pyScript, int minTrainMonths) throws Exception {
        long fairStart = Utils.sdfFile.parse(start).getTime();
        long evalEnd = Utils.sdfFile.parse(end).getTime();
        new File(modelTmpDir).mkdirs();

        LOG.info("🚀 WFO GATE | {} -> {} | OOS={}m | csv={} | out={}", start, end, oosMonths, csvStore, outFile);

        // ===== PHA 1: REPLAY 1 LẦN -> featureStore + labelStore + CSV =====
        // Logic replay/label nằm ở ExportGateDataset (nguồn sự thật DUY NHẤT) — tránh 2 bản logic label lệch nhau.
        // ExportGateDataset còn chạy được ĐỘC LẬP (không train) để xuất dataset đẩy Kaggle.
        long emitted = ExportGateDataset.replayToCsv(fairStart, evalEnd, csvStore, (ts, f, label) -> {
            featureStore.put(ts, f);
            labelStore.put(ts, label);
        });
        if (featureStore.isEmpty()) { LOG.error("⛔ featureStore rỗng — dừng."); return; }
        if (emitted != featureStore.size()) {
            LOG.error("⛔ LỆCH: CSV emit {} dòng nhưng featureStore {} phút — dừng.", emitted, featureStore.size());
            return;
        }
        LOG.info("✅ PHA 1 xong: featureStore={} phút | label={} | range {} .. {}",
                featureStore.size(), labelStore.size(),
                Utils.normalizeDateYYYYMMDD(featureStore.firstKey()), Utils.normalizeDateYYYYMMDD(featureStore.lastKey()));

        oldPred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospikeSet(OLD_SET);
        LOG.info("   predRisk4H từ set cũ: {} mốc", oldPred.size());

        // ===== PHA 2: WFO LOOP expanding =====
        Calendar firstOosCal = Calendar.getInstance();
        firstOosCal.setTimeInMillis(fairStart);
        firstOosCal.add(Calendar.MONTH, minTrainMonths);
        long firstOos = firstOosCal.getTimeInMillis();
        LOG.info("   minTrainMonths={} -> fold OOS đầu bắt đầu {}", minTrainMonths, Utils.normalizeDateYYYYMMDD(firstOos));
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

    private static String fmt(float v) {
        if (Float.isNaN(v) || Float.isInfinite(v)) return "0.000000";
        return String.format(Locale.US, "%.8f", v);
    }
}
