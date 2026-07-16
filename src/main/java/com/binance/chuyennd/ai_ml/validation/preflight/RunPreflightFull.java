package com.binance.chuyennd.ai_ml.validation.preflight;

import com.aerospike.client.AerospikeClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;

/**
 * Entrypoint FULL validate — chạy đủ 21 validator (tầng ALL) rồi đóng {@link ValidationStamp}.
 * Thiết kế để chạy TẠI NƠI DATA Ở (Oracle bin+Aerospike ns=test, hoặc Kaggle bản sao) — theo luật
 * CORE "validate-theo-nơi-chạy". KHÔNG chạy ở máy dev (thiếu dữ liệu).
 *
 * <p>Cấu hình qua ENV (không hardcode host):</p>
 * <ul>
 *   <li>{@code PREFLIGHT_AS_HOST} / {@code PREFLIGHT_AS_PORT} — Aerospike (mặc định 127.0.0.1:3222 = Oracle local)</li>
 *   <li>{@code WFO_DATA_DIR} — thư mục bin dataset (market/pred/funding + manifest)</li>
 *   <li>{@code WFO_FUNDING_PRED_DIR} — thư mục predict_wf_*.bin (selector)</li>
 *   <li>{@code PREFLIGHT_ENV} — nhãn môi trường ghi vào stamp (oracle/kaggle/226; mặc định "oracle")</li>
 *   <li>{@code PREFLIGHT_FINGERPRINT} — md5 dataset (từ manifest); dùng khoá stamp</li>
 *   <li>{@code PREFLIGHT_STAMP} — nơi ghi stamp (mặc định {@code <WFO_DATA_DIR>/validation_stamp.properties})</li>
 * </ul>
 *
 * <p>Namespace scan lấy từ {@code Configs.AEROSPIKE_NAMESPACE} (config.properties tại box đó — Oracle = test).</p>
 */
public final class RunPreflightFull {

    private static final Logger LOG = LoggerFactory.getLogger(RunPreflightFull.class);

    private RunPreflightFull() {
    }

    /**
     * @param args [0]=reportPath (mặc định docs/reports/preflight_full_&lt;env&gt;.md)
     */
    public static void main(String[] args) {
        String host = envOr("PREFLIGHT_AS_HOST", "127.0.0.1");
        int port = Integer.parseInt(envOr("PREFLIGHT_AS_PORT", "3222"));
        String wfoDataDir = System.getenv("WFO_DATA_DIR");
        String fundingPredDir = System.getenv("WFO_FUNDING_PRED_DIR");
        String envTag = envOr("PREFLIGHT_ENV", "oracle");
        String fingerprint = envOr("PREFLIGHT_FINGERPRINT", "unknown");
        String stampPath = envOr("PREFLIGHT_STAMP",
                (wfoDataDir != null ? wfoDataDir : ".") + "/validation_stamp.properties");
        String reportPath = args.length > 0 ? args[0] : "docs/reports/preflight_full_" + envTag + ".md";

        AerospikeClient client = null;
        try {
            LOG.info("PREFLIGHT FULL @ env={} | Aerospike {}:{} | WFO_DATA_DIR={} | predDir={} | fingerprint={}",
                    envTag, host, port, wfoDataDir, fundingPredDir, fingerprint);
            client = new AerospikeClient(host, port);

            Map<String, String> sysEnv = System.getenv();
            PreflightContext ctx = new PreflightContext.Builder()
                    .client(client)
                    .wfoDataDir(wfoDataDir)
                    .fundingPredDir(fundingPredDir)
                    .env(sysEnv)
                    .expected(new ExpectedRanges())
                    .build();

            PreflightGate gate = PreflightValidators.buildDefault();
            LOG.info("Chạy {} validator (tầng ALL)...", gate.validatorCount());
            boolean pass = gate.runFullAndStamp(ctx, fingerprint, envTag, stampPath, reportPath);
            LOG.info("PREFLIGHT FULL verdict: {} | report={} | stamp={}",
                    pass ? "PASS (đã đóng stamp)" : "FAIL (KHÔNG đóng stamp)", reportPath, stampPath);
            System.exit(pass ? 0 : 3);
        } catch (Throwable e) {
            LOG.error("RunPreflightFull FAIL", e);
            System.exit(1);
        } finally {
            if (client != null) {
                client.close();
            }
        }
    }

    private static String envOr(String key, String dflt) {
        String v = System.getenv(key);
        return v == null || v.trim().isEmpty() ? dflt : v;
    }
}
