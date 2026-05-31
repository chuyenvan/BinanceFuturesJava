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
    private static final String TASK_SET_NAME = "funding_tasks_monthly_v1";

    /**
     * KHỞI TẠO DANH SÁCH VIỆC (Chỉ chạy 1 lần ở máy Admin hoặc Server đầu tiên)
     * Chia thời gian thành các gói (Chunk) theo THÁNG.
     */
    public static void initTasks(long startTime, long endTime) {
        LOG.info("🛠 Initializing Task Queue in Aerospike (MONTHLY)...");
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient242();

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
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient242();
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