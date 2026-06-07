package com.binance.chuyennd.ai_ml.onnx.funding;

import com.aerospike.client.*;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class AerospikeTaskCoordinator {
    private static final Logger LOG = LoggerFactory.getLogger(AerospikeTaskCoordinator.class);

    // 🔥 Đổi tên Set để tạo Queue mới hoàn toàn, không dính với Queue tuần cũ
    private static final String TASK_SET_NAME = "funding_tasks_monthly_v2";

    /**
     * RE-QUEUE 1 task bị lỗi hoặc dừng giữa chừng.
     *
     * @param monthStartStr đầu tháng của task gốc, vd "20260301" (đúng key TASK_yyyyMMdd lúc init).
     * @param resumeFromStr null = chạy lại CẢ THÁNG;
     *                      hoặc vd "20260315" = chạy tiếp từ giữa chừng (đọc log
     *                      "✅ Đã xử lý xong: yyyyMMdd" cuối cùng của worker chết để biết mốc).
     *                      Ghi đè record là idempotent nên resume chỉ để tiết kiệm thời gian,
     *                      chạy lại cả tháng cũng KHÔNG sai dữ liệu.
     */
    public static void requeueTask(String monthStartStr, String resumeFromStr) {
        // PHẢI cùng cluster với claimNextTask (226) — không thì worker không bao giờ thấy task
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient226();
        try {
            long monthStart = Utils.sdfFile.parse(monthStartStr).getTime();
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(monthStart);
            cal.add(Calendar.MONTH, 1);
            long chunkEnd = cal.getTimeInMillis();

            long chunkStart = monthStart;
            if (resumeFromStr != null) {
                long resume = Utils.sdfFile.parse(resumeFromStr).getTime();
                if (resume > monthStart && resume < chunkEnd) {
                    chunkStart = resume;
                } else {
                    LOG.warn("⚠️ resumeFrom {} nằm ngoài tháng {} -> chạy lại cả tháng.", resumeFromStr, monthStartStr);
                }
            }

            // Giữ NGUYÊN key gốc TASK_<đầu tháng> kể cả khi resume — tránh sinh task trùng/lệch key;
            // worker đọc start/end từ bin nên resume vẫn đúng.
            String keyString = "TASK_" + monthStartStr;
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, TASK_SET_NAME, keyString);
            client.put(null, key, new Bin("start", chunkStart), new Bin("end", chunkEnd));

            LOG.info("✅ Re-queued {}: {} -> {}", keyString,
                    Utils.normalizeDateYYYYMMDDHHmm(chunkStart), Utils.normalizeDateYYYYMMDDHHmm(chunkEnd));
        } catch (ParseException e) {
            LOG.error("❌ Sai định dạng ngày (yyyyMMdd): {} / {}", monthStartStr, resumeFromStr);
        }
    }
    /**
     * KHỞI TẠO DANH SÁCH VIỆC (Chỉ chạy 1 lần ở máy Admin hoặc Server đầu tiên)
     * Chia thời gian thành các gói (Chunk) theo THÁNG.
     */
    public static void initTasks(long startTime, long endTime) {
        LOG.info("🛠 Initializing Task Queue in Aerospike (MONTHLY)...");
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient226();

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);

        int count = 0;

        while (cal.getTimeInMillis() < endTime) {
            long chunkStart = cal.getTimeInMillis();

            // 🔥 Thêm 1 tháng bằng Calendar để chuẩn xác số ngày (28, 30, 31)
            cal.add(Calendar.MONTH, 1);
            long chunkEnd = Math.min(cal.getTimeInMillis(), endTime);

            // Key ví dụ: TASK_20210101
            String keyString = "TASK_" + Utils.normalizeDateYYYYMMDD(chunkStart);
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, TASK_SET_NAME, keyString);

            // Ghi metadata (Start, End) vào Aerospike
            // Dùng Put (Create/Update)
            client.put(null, key,
                    new Bin("start", chunkStart),
                    new Bin("end", chunkEnd)
            );

            count++;
        }
        LOG.info("✅ Created {} tasks (Months) in Set '{}'", count, TASK_SET_NAME);
    }

    /**
     * WORKER GỌI HÀM NÀY ĐỂ NHẬN VIỆC
     * Cơ chế: Scan tìm task -> Atomic Delete -> Nếu xóa được thì nhận.
     */
    public static TaskRange claimNextTask() {
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient226();
        ScanPolicy policy = new ScanPolicy();
        policy.maxRecords = 50; // Scan lấy mẫu 50 task đầu tiên

        final List<TaskRange> candidates = new ArrayList<>();

        try {
            client.scanAll(policy, Configs.AEROSPIKE_NAMESPACE, TASK_SET_NAME, (key, record) -> {
                long start = record.getLong("start");
                long end = record.getLong("end");
                candidates.add(new TaskRange(key, start, end));
            }, "start", "end");
        } catch (AerospikeException e) {
            // Ignore scan errors
        }

        if (candidates.isEmpty()) return null; // Hết việc

        // Shuffle để các server đỡ tranh nhau cùng 1 task đầu tiên
        Collections.shuffle(candidates);

        // Thử Atomic Delete để giành quyền xử lý
        for (TaskRange task : candidates) {
            try {
                // Xóa record. Return true nếu record tồn tại và xóa thành công.
                boolean existed = client.delete(null, task.key);
                if (existed) {
                    LOG.info("🎯 Claimed Task: {} -> {}",
                            Utils.normalizeDateYYYYMMDD(task.start),
                            Utils.normalizeDateYYYYMMDD(task.end));
                    return task;
                }
            } catch (Exception e) {
                // Bị tranh mất, thử cái khác
            }
        }

        return null;
    }

    public static class TaskRange {
        public Key key;
        public long start;
        public long end;

        public TaskRange(Key key, long start, long end) {
            this.key = key;
            this.start = start;
            this.end = end;
        }
    }

    /**
     * CHỈ KHỞI TẠO LẠI CÁC TASK CỤ THỂ (Dùng khi một số task bị lỗi)
     * @param specificDates Danh sách chuỗi ngày định dạng YYYYMMDD (ví dụ: "20210101", "20210201")
     */
    public static void reInitSpecificTasks(List<String> specificDates) {
        LOG.info("🛠 Re-initializing {} specific tasks in Aerospike (MONTHLY)...", specificDates.size());
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient242();

        for (String dateStr : specificDates) {
            try {
                // Chuyển từ YYYYMMDD sang timestamp
                long chunkStart = Utils.sdfFile.parse(dateStr).getTime();

                // Tính chunkEnd bằng cách cộng 1 tháng
                Calendar cal = Calendar.getInstance();
                cal.setTimeInMillis(chunkStart);
                cal.add(Calendar.MONTH, 1);
                long chunkEnd = cal.getTimeInMillis();

                String keyString = "TASK_" + dateStr;
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, TASK_SET_NAME, keyString);

                // Ghi đè vào Aerospike
                client.put(null, key,
                        new Bin("start", chunkStart),
                        new Bin("end", chunkEnd)
                );
                LOG.info("✅ Re-queued Task: {}", keyString);

            } catch (ParseException e) {
                LOG.error("❌ Invalid date format: {}", dateStr);
            }
        }
    }

    public static void main(String[] args) throws ParseException {
        String startStr = "20210101";
        long globalStart = Utils.sdfFile.parse(startStr).getTime();
        long globalEnd = System.currentTimeMillis();
        AerospikeTaskCoordinator.initTasks(globalStart, globalEnd);


//        AerospikeTaskCoordinator.requeueTask("20241201", null);



//        // Danh sách các task bạn lọc được từ log là bị lỗi hoặc chạy quá lâu (Phải trúng mốc đầu tháng nếu khởi tạo theo tháng)
//        List<String> claimedTasks = Arrays.asList(
//                "20210101", "20210201"
//        );
//
//        if (!claimedTasks.isEmpty()) {
//            AerospikeTaskCoordinator.reInitSpecificTasks(claimedTasks);
//        } else {
//            LOG.info("No tasks to re-initialize.");
//        }
    }
}