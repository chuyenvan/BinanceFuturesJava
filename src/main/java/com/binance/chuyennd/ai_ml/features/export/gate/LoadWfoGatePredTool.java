package com.binance.chuyennd.ai_ml.features.export.gate;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * TASK-121 — Nạp {@code wfo_gate_pred.csv} (leak-free gate/market predictions sinh bởi {@link WFOGateRunner}
 * per-fold trên Oracle) vào Aerospike set {@code ai_pred_market_gate_wfo} (GĐ2 mắt xích 1).
 *
 * <p><b>SCHEMA (mirror ĐÚNG reader hiện hành — KHÔNG đoán format).</b> Xác định bằng cách đọc code reader
 * mà {@code WfoDataset.export} dùng khi env {@code WFO_SET_PRED=ai_pred_market_gate_wfo}:
 * {@link DataManagerAerospikeFloatSim#getAllMarketAiPredictionsFromAerospikeSet(String)} — scanAll bin
 * {@code "data"} → Snappy.uncompress → gson→{@link AiPredictionData} → key = {@code data.timestamp}.
 * <ul>
 *   <li><b>Client/box:</b> {@code getClientOracle()} (trên Oracle = Aerospike local theo config box).</li>
 *   <li><b>Namespace:</b> {@code Configs.AEROSPIKE_NAMESPACE} (config.properties = {@code ticker}).</li>
 *   <li><b>Set:</b> {@code ai_pred_market_gate_wfo} (override qua arg[1] hoặc env {@code WFO_SET_PRED}).</li>
 *   <li><b>Key (per-tick / per-phút, KHÔNG chunk-tháng):</b> {@code yyyyMMdd-HHmm} format từ epoch-ms
 *       (formatter pin GMT+7 trong writer). Mỗi phút = 1 record.</li>
 *   <li><b>Bin:</b> đúng 1 bin tên {@code "data"} = {@code Snappy.compress(gson.toJson(AiPredictionData) UTF-8)}.</li>
 *   <li><b>WritePolicy:</b> {@code recordExistsAction=UPDATE, sendKey=true} → put đè cùng key ⇒ <b>idempotent</b>
 *       (chạy lại KHÔNG nhân đôi; cùng timestamp → cùng key → ghi đè).</li>
 * </ul>
 * Vì lý do trên tool <b>tái dùng</b> {@link DataManagerAerospikeFloatSim#saveMarketAiPredictionsBatchToSet(String, Map)}
 * làm writer (nguồn sự thật duy nhất về key/bin/encoding/policy) thay vì tự dựng lại → 0 rủi ro lệch format.
 *
 * <p><b>CSV input</b> (do {@link WFOGateRunner} sinh): header cố định
 * {@code timestamp,predReturn15M,predRisk4H}; mỗi dòng {@code <epochMs:long>,<float>,<float>}.
 * {@code timestamp} = epoch-ms → gán thẳng {@code AiPredictionData.timestamp} (reader lấy làm key).
 *
 * <p><b>Cách chạy (Oracle, master — KHÔNG phải CCD):</b>
 * <pre>
 *   # validate 1 chunk trước rồi so đọc-lại, sau đó full:
 *   java -cp binance-java-sdk.jar \
 *     com.binance.chuyennd.ai_ml.features.export.gate.LoadWfoGatePredTool \
 *     ~/claudedata/wfo_gate_pred.csv [ai_pred_market_gate_wfo]
 * </pre>
 * arg[0] = đường dẫn CSV (bắt buộc); arg[1] = set (tuỳ chọn, mặc định env {@code WFO_SET_PRED} hoặc
 * {@code ai_pred_market_gate_wfo}). Exception bất kỳ → exit 1. Log SLF4J mỗi mốc 100k dòng.
 */
public class LoadWfoGatePredTool {

    static final Logger LOG = LoggerFactory.getLogger(LoadWfoGatePredTool.class);

    static final String DEFAULT_SET = "ai_pred_market_gate_wfo";
    static final String EXPECTED_HEADER = "timestamp,predReturn15M,predRisk4H";
    /** Aerospike batch cap = 5000; chừa biên → 4900 key/batch (bound RAM khi CSV ~1.7M dòng). */
    static final int CHUNK = 4900;
    static final int PREFLIGHT_ROWS = 5; // validate N dòng đầu trước khi nạp thật
    static final int LOG_EVERY = 100_000;

    /** Sink 1 batch (≤ {@link #CHUNK} key) → cho phép test không cần Aerospike. */
    interface BatchSink {
        void write(String setName, Map<Long, AiPredictionData> batch);
    }

    /** Sink production: ghi thẳng Aerospike theo config box, đúng format reader. */
    static final BatchSink AEROSPIKE_SINK = DataManagerAerospikeFloatSim::saveMarketAiPredictionsBatchToSet;

    public static void main(String[] args) {
        try {
            if (args.length < 1 || args[0].isEmpty()) {
                LOG.error("⛔ Thiếu arg[0] = đường dẫn wfo_gate_pred.csv");
                System.exit(1);
                return;
            }
            File csv = new File(args[0]);
            String setName = args.length > 1 && !args[1].isEmpty()
                    ? args[1]
                    : envOr("WFO_SET_PRED", DEFAULT_SET);

            LOG.info("🚀 TASK-121 nạp gate pred: csv={} → set={} (clientOracle, chunk={})",
                    csv.getAbsolutePath(), setName, CHUNK);
            long total = load(csv, setName, CHUNK, AEROSPIKE_SINK);
            LOG.info("🎯 DONE: nạp {} record → set {} (idempotent: chạy lại ghi đè cùng key)", total, setName);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ LoadWfoGatePredTool FAIL", e);
            System.exit(1);
        }
    }

    /**
     * Đọc CSV streaming, validate header + {@link #PREFLIGHT_ROWS} dòng đầu, gom {@code chunkSize} key/batch
     * rồi flush qua {@code sink}. Trả tổng số record đã nạp. Ném exception nếu header/dòng sai → main → exit 1.
     */
    static long load(File csv, String setName, int chunkSize, BatchSink sink) throws Exception {
        if (!csv.isFile()) throw new IllegalArgumentException("CSV không tồn tại: " + csv.getAbsolutePath());
        long total = 0;
        int preflight = 0;
        // TreeMap không cần — dùng LinkedHashMap giữ thứ tự đọc; key = timestamp (dedup trong-batch tự nhiên).
        Map<Long, AiPredictionData> batch = new LinkedHashMap<>(chunkSize * 2);
        try (BufferedReader br = new BufferedReader(new FileReader(csv))) {
            String header = br.readLine();
            validateHeader(header);
            String line;
            long lineNo = 1; // đã đọc header
            while ((line = br.readLine()) != null) {
                lineNo++;
                if (line.trim().isEmpty()) continue;
                AiPredictionData d;
                try {
                    d = parseLine(line);
                } catch (Exception e) {
                    throw new IllegalStateException("Dòng " + lineNo + " sai format: [" + line + "] — " + e.getMessage());
                }
                if (preflight < PREFLIGHT_ROWS) {
                    preflight++;
                    LOG.info("   preflight[{}] ts={} p15={} r4={}", preflight, d.timestamp, d.predReturn15M, d.predRisk4H);
                }
                batch.put(d.timestamp, d);
                total++;
                if (batch.size() >= chunkSize) {
                    sink.write(setName, batch);
                    batch.clear();
                }
                if (total % LOG_EVERY == 0) LOG.info("... nạp {} record (đang ở dòng {})", total, lineNo);
            }
        }
        if (!batch.isEmpty()) sink.write(setName, batch); // flush chunk cuối
        return total;
    }

    /** Header phải KHỚP tuyệt đối (chống nạp nhầm file khác schema). */
    static void validateHeader(String header) {
        if (header == null) throw new IllegalStateException("CSV rỗng (không có header)");
        String h = header.trim();
        // BOM UTF-8 nếu có
        if (h.startsWith("﻿")) h = h.substring(1);
        if (!h.equals(EXPECTED_HEADER)) {
            throw new IllegalStateException("Header sai: mong '" + EXPECTED_HEADER + "' nhưng nhận '" + h + "'");
        }
    }

    /** Parse 1 dòng {@code epochMs,predReturn15M,predRisk4H} → {@link AiPredictionData}. Ném nếu sai. */
    static AiPredictionData parseLine(String line) {
        String[] p = line.split(",");
        if (p.length != 3) throw new IllegalArgumentException("cần 3 cột, có " + p.length);
        long ts = Long.parseLong(p[0].trim());
        if (ts <= 0) throw new IllegalArgumentException("timestamp phải > 0: " + ts);
        float p15 = Float.parseFloat(p[1].trim());
        float r4 = Float.parseFloat(p[2].trim());
        return new AiPredictionData(ts, p15, r4);
    }

    private static String envOr(String k, String def) {
        String v = System.getenv(k);
        return (v == null || v.isEmpty()) ? def : v;
    }
}
