package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.GenerationPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Worker xuất Tool1 feature theo từng tháng. Chạy trên Kaggle (hoặc 226, read-only).
 *
 * <p>Luồng hoạt động:
 * <ol>
 *   <li>Load toàn bộ MarketData + SymbolMapper từ Aerospike 226 <b>một lần</b>.</li>
 *   <li>Scan {@link ExportTool1Master#TASK_SET}, claim task PENDING (hoặc RUNNING stale) bằng generation lock.</li>
 *   <li>Chạy {@link ExportFeaturesForPythonTool#startGeneration} cho tháng đó.</li>
 *   <li>Ghi output vào {@code features_export_python_v3/<month>/} trong CWD.</li>
 *   <li>Mark DONE trong Aerospike, claim task tiếp theo.</li>
 *   <li>Thoát (System.exit 0) khi không còn task PENDING.</li>
 * </ol>
 *
 * <p>Usage: {@code java ... ExportTool1Worker [workerId]}
 *
 * //@param args[0] workerId (default = KAGGLE_KERNEL_RUN_TYPE + "-" + PID)
 */
public class ExportTool1Worker {

    private static final Logger LOG = LoggerFactory.getLogger(ExportTool1Worker.class);

    /** Task RUNNING quá ngưỡng này coi worker đã chết → cho worker khác cướp. */
    private static final long STALE_RUNNING_MS = 30 * 60_000L; // 30 phút

    private static String workerId;

    public static void main(String[] args) throws Exception {
        workerId = args.length > 0 ? args[0]
                : (System.getenv().getOrDefault("KAGGLE_KERNEL_RUN_TYPE", "local")
                   + "-" + ProcessHandle.current().pid());
        LOG.info("👷 Worker khởi động: workerId={} set={}", workerId, ExportTool1Master.TASK_SET);

        // Load market data + symbol mapper một lần, tái dùng cho tất cả tháng trong session.
        LOG.info("📥 Nạp MarketData + SymbolMapper (một lần cho toàn session)...");
        TreeMap<Long, MarketDataObject> marketData =
                DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);
        LOG.info("✅ Nạp xong: {} mốc market data, {} symbols", marketData.size(), symbolMap.size());

        int processed = 0;
        while (true) {
            String month = claimNextTask();
            if (month == null) {
                LOG.info("☕ Không còn task PENDING. Worker thoát. Đã xuất {} tháng.", processed);
                break;
            }

            LOG.info("🔨 [task #{}] Bắt đầu xuất tháng: {}", processed + 1, month);
            long t0 = System.currentTimeMillis();
            Key taskKey = new Key(Configs.AEROSPIKE_NAMESPACE, ExportTool1Master.TASK_SET, month);

            try {
                long[] range = monthToRange(month);
                // Export vào temp dir riêng, sau đó rename thành ff_YYYYMM.t1c.gz ở root dir.
                // Tránh để nhiều tháng ghi trùng file trong cùng session.
                String rootDir = "features_export_python_v3/";
                String tmpDir  = rootDir + ".tmp_" + month + "/";
                new File(tmpDir).mkdirs();

                new ExportFeaturesForPythonTool().startGeneration(
                        tmpDir, range[0], range[1], marketData, symbolMap);

                // [2026-08-07 TASK-251] Tool1 đổi sang định dạng T1C1 (.t1c.gz) — xem Tool1ColSink.
                // Tìm file .t1c.gz được tạo trong tmp dir và đổi tên thành ff_YYYYMM.t1c.gz
                String monthCompact = month.replace("-", ""); // "2021-01" -> "202101"
                String destPath = rootDir + "ff_" + monthCompact + ".t1c.gz";
                File[] generated = new File(tmpDir).listFiles(f -> f.getName().endsWith(".t1c.gz"));
                if (generated == null || generated.length == 0) {
                    throw new IllegalStateException("Không tìm thấy .t1c.gz trong tmpDir=" + tmpDir);
                }
                Files.move(generated[0].toPath(), Paths.get(destPath), StandardCopyOption.REPLACE_EXISTING);
                new File(tmpDir).delete(); // xóa tmp dir (nếu rỗng)
                LOG.info("📦 Output: {} ({} bytes)", destPath, new File(destPath).length());

                long elapsedMs = System.currentTimeMillis() - t0;
                long fileSize = new File(destPath).length();
                markDone(taskKey, month, elapsedMs, fileSize, workerId);
                processed++;
                LOG.info("✅ Tháng {} xong trong {}s | size={} bytes", month, elapsedMs / 1000, fileSize);

            } catch (Exception e) {
                LOG.error("❌ Lỗi xuất tháng {}: {}", month, e.getMessage(), e);
                markFailed(taskKey, e.getMessage());
            }
        }

        System.exit(0);
    }

    /**
     * Scan TASK_SET tìm task PENDING hoặc RUNNING-stale, claim bằng generation-based optimistic lock.
     *
     * @return month "YYYY-MM" nếu claim thành công; null nếu không còn task nào.
     */
    private static String claimNextTask() {
        String[] found = {null};
        try {
            DataManagerAerospikeFloatSim.getClientOracle().scanAll(
                    null, Configs.AEROSPIKE_NAMESPACE, ExportTool1Master.TASK_SET,
                    (key, record) -> {
                        if (found[0] != null) return; // đã claim được 1, bỏ qua phần còn lại

                        String status  = record.getString("status");
                        long   tsStart = record.getLong("ts_start");
                        boolean stale  = ExportTool1Master.STATUS_RUNNING.equals(status)
                                && (System.currentTimeMillis() - tsStart) > STALE_RUNNING_MS;

                        if (!ExportTool1Master.STATUS_PENDING.equals(status) && !stale) return;

                        WritePolicy wp = new WritePolicy();
                        wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
                        wp.generation = record.generation;
                        try {
                            DataManagerAerospikeFloatSim.getClientOracle().put(wp, key,
                                    new Bin("status",    ExportTool1Master.STATUS_RUNNING),
                                    new Bin("worker_id", workerId),
                                    new Bin("ts_start",  System.currentTimeMillis())
                            );
                            found[0] = record.getString("month");
                        } catch (com.aerospike.client.AerospikeException ae) {
                            // Race condition: worker khác vừa claim — bỏ qua, scan tiếp
                        }
                    },
                    "status", "month", "ts_start");
        } catch (Exception e) {
            LOG.warn("Lỗi scan tasks: {}", e.getMessage(), e);
        }
        return found[0];
    }

    /**
     * Mark task DONE, ghi kernel_slug (workerId) vào record để B5 tải lại output theo slug.
     *
     * @param key       Aerospike task key
     * @param month     tháng "YYYY-MM"
     * @param elapsedMs thời gian xử lý
     * @param fileSize  kích thước file ff_YYYYMM.bin.gz
     * @param slug      kernel slug (workerId) — dùng để B5 liệt kê slug → tải output
     */
    private static void markDone(Key key, String month, long elapsedMs, long fileSize, String slug) {
        try {
            DataManagerAerospikeFloatSim.getClientOracle().put(new WritePolicy(), key,
                    new Bin("status",      ExportTool1Master.STATUS_DONE),
                    new Bin("ts_done",     System.currentTimeMillis()),
                    new Bin("elapsed_ms",  elapsedMs),
                    new Bin("file_size",   fileSize),
                    new Bin("kernel_slug", slug)
            );
        } catch (Exception e) {
            LOG.warn("Không mark DONE cho {}: {}", month, e.getMessage());
        }
    }

    private static void markFailed(Key key, String errorMsg) {
        try {
            String msg = errorMsg != null
                    ? errorMsg.substring(0, Math.min(errorMsg.length(), 500))
                    : "";
            DataManagerAerospikeFloatSim.getClientOracle().put(new WritePolicy(), key,
                    new Bin("status",  ExportTool1Master.STATUS_FAILED),
                    new Bin("error",   msg),
                    new Bin("ts_done", System.currentTimeMillis())
            );
        } catch (Exception e) {
            LOG.warn("Không mark FAILED: {}", e.getMessage());
        }
    }

    /**
     * Chuyển "YYYY-MM" thành [startEpochMs, endEpochMs) theo quy ước Tool1 (07:00 GMT+7).
     * start = ngày 1 tháng M 07:00; end = ngày 1 tháng M+1 07:00 (loại trừ).
     */
    private static long[] monthToRange(String month) throws Exception {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        sdf.setTimeZone(java.util.TimeZone.getTimeZone("Asia/Ho_Chi_Minh"));
        String[] p = month.split("-");
        int y = Integer.parseInt(p[0]), m = Integer.parseInt(p[1]);
        int ny = m == 12 ? y + 1 : y;
        int nm = m == 12 ? 1 : m + 1;
        long start = sdf.parse(String.format("%04d-%02d-01 07:00", y,  m )).getTime();
        long end   = sdf.parse(String.format("%04d-%02d-01 07:00", ny, nm)).getTime();
        return new long[]{start, end};
    }
}
