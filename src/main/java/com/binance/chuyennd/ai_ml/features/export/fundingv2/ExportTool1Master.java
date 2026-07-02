package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

/**
 * Tạo task records trong Aerospike 226 cho từng tháng cần xuất Tool1.
 * Chạy một lần (local hoặc trên 226) trước khi push worker kernels lên Kaggle.
 *
 * <p>Usage:
 * <pre>
 *   java ... ExportTool1Master [startMonth] [endMonth] [reset]
 *   ExportTool1Master 2021-01 2026-06           -- tạo tasks 2021-01..2026-06, skip existing
 *   ExportTool1Master 2021-01 2021-03 reset     -- reset (ghi đè) các tháng đó
 *   ExportTool1Master 2023-06 2023-06            -- tạo 1 task test
 * </pre>
 *
 * @param args [0] startMonth "YYYY-MM" (default "2021-01"),
 *             [1] endMonth "YYYY-MM" inclusive (default "2026-06"),
 *             [2] "reset" để ghi đè kể cả DONE/RUNNING
 */
public class ExportTool1Master {

    private static final Logger LOG = LoggerFactory.getLogger(ExportTool1Master.class);

    /** Set Aerospike chứa task records. Key = "YYYY-MM". Worker scan set này để claim. */
    public static final String TASK_SET = "tool1_export_tasks_v1";

    public static final String STATUS_PENDING = "PENDING";
    public static final String STATUS_RUNNING = "RUNNING";
    public static final String STATUS_DONE    = "DONE";
    public static final String STATUS_FAILED  = "FAILED";

    public static void main(String[] args) throws Exception {
        String startMonth = args.length > 0 ? args[0] : "2021-01";
        String endMonth   = args.length > 1 ? args[1] : "2026-06";
        boolean reset     = args.length > 2 && "reset".equalsIgnoreCase(args[2]);

        List<String> months = generateMonths(startMonth, endMonth);
        LOG.info("Master: {} tasks ({} → {}) reset={}", months.size(), startMonth, endMonth, reset);

        var client = DataManagerAerospikeFloatSim.getClient226();
        WritePolicy wp = new WritePolicy();
        wp.recordExistsAction = RecordExistsAction.UPDATE;

        int created = 0, skipped = 0;
        for (String month : months) {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, TASK_SET, month);
            if (!reset) {
                Record existing = client.get(null, key);
                if (existing != null) {
                    LOG.info("  SKIP {} (status={})", month, existing.getString("status"));
                    skipped++;
                    continue;
                }
            }
            client.put(wp, key,
                    new Bin("status",    STATUS_PENDING),
                    new Bin("month",     month),
                    new Bin("worker_id", ""),
                    new Bin("ts_start",  0L),
                    new Bin("ts_done",   0L),
                    new Bin("error",     "")
            );
            LOG.info("  CREATED {}", month);
            created++;
        }
        LOG.info("Master xong: created={} skipped={} total={}", created, skipped, months.size());
        System.exit(0);
    }

    /**
     * Sinh danh sách tháng "YYYY-MM" từ startMonth đến endMonth (inclusive), thứ tự tăng dần.
     *
     * @param startMonth "YYYY-MM" ví dụ "2021-01"
     * @param endMonth   "YYYY-MM" ví dụ "2026-06"
     * @return list các tháng theo thứ tự
     */
    public static List<String> generateMonths(String startMonth, String endMonth) {
        List<String> result = new ArrayList<>();
        String[] s = startMonth.split("-");
        String[] e = endMonth.split("-");
        int y = Integer.parseInt(s[0]), m = Integer.parseInt(s[1]);
        int ey = Integer.parseInt(e[0]), em = Integer.parseInt(e[1]);
        while (y < ey || (y == ey && m <= em)) {
            result.add(String.format("%04d-%02d", y, m));
            m++;
            if (m > 12) { m = 1; y++; }
        }
        return result;
    }
}
