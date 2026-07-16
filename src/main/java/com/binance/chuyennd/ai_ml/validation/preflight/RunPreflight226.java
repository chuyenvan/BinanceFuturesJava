package com.binance.chuyennd.ai_ml.validation.preflight;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Info;
import com.aerospike.client.cluster.Node;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A1PredCoverageValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A4FoldCountValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.A5SurvivorshipValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.D1FundingTzValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.D3IntrabarLookaheadValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.checks.F2ConfigVersionValidator;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Runner chẩn đoán: chạy SUBSET validator NHẸ trên cluster 226 (read-only) để lấy SỐ THẬT,
 * KHÔNG scan nặng (không đụng kline_1m_opt 2.8M). Trước tiên in danh sách set + record-count
 * (info "sets") để biết CHÍNH XÁC nguồn nào đang ở 226 ns={@code ticker} — tránh kết luận nhầm
 * khi set thực ra nằm ở box/ns khác.
 *
 * <p>Chạy: {@code java -cp target/classes;<shaded.jar> ...RunPreflight226 [reportPath]}
 * từ thư mục repo (cần config.properties ở CWD để {@code Configs} nạp host 226).</p>
 */
public final class RunPreflight226 {

    private static final Logger LOG = LoggerFactory.getLogger(RunPreflight226.class);

    private RunPreflight226() {
    }

    /**
     * @param args [0]=reportPath (mặc định docs/reports/preflight_226_light.md)
     */
    public static void main(String[] args) {
        String reportPath = args.length > 0 ? args[0] : "docs/reports/preflight_226_light.md";
        try {
            AerospikeClient client = DataManagerAerospikeFloatSim.getClient226();
            Node[] nodes = client.getNodes();
            LOG.info("Kết nối 226: {} node, ns mặc định = {}", nodes.length, Configs.AEROSPIKE_NAMESPACE);
            if (nodes.length > 0) {
                String sets = Info.request(nodes[0], "sets");
                LOG.info("=== SETS trên 226 (set:objects) ===");
                for (String s : sets.split(";")) {
                    if (s.contains("objects=")) {
                        String ns = extract(s, "ns=");
                        String set = extract(s, "set=");
                        String objects = extract(s, "objects=");
                        LOG.info("  ns={} set={} objects={}", ns, set, objects);
                    }
                }
            }

            PreflightContext ctx = new PreflightContext.Builder()
                    .client(client)
                    .expected(new ExpectedRanges())
                    .build();

            PreflightGate gate = new PreflightGate()
                    .register(new A1PredCoverageValidator())
                    .register(new A4FoldCountValidator())
                    .register(new A5SurvivorshipValidator())
                    .register(new D1FundingTzValidator())
                    .register(new D3IntrabarLookaheadValidator())
                    .register(new F2ConfigVersionValidator());

            LOG.info("=== CHẠY {} validator nhẹ trên 226 (read-only) ===", gate.validatorCount());
            ValidationReport report = gate.run(ctx, Tier.ALL);
            report.writeTo(reportPath);
            LOG.info("VERDICT tổng (subset nhẹ): {} | BLOCK-fail={} WARN={}",
                    report.isPass() ? "PASS" : "FAIL", report.blockingFailures(), report.warnings());
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("RunPreflight226 FAIL", e);
            System.exit(1);
        }
    }

    /**
     * @param s   chuỗi info Aerospike (key=val:key=val)
     * @param key khoá cần lấy (kèm '=')
     * @return giá trị sau key tới ':' kế tiếp, hoặc "?" nếu không có
     */
    private static String extract(String s, String key) {
        int i = s.indexOf(key);
        if (i < 0) {
            return "?";
        }
        int start = i + key.length();
        int end = s.indexOf(':', start);
        return end < 0 ? s.substring(start) : s.substring(start, end);
    }
}
