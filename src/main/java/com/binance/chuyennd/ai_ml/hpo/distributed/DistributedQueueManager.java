package com.binance.chuyennd.ai_ml.hpo.distributed;

import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.cdt.ListOperation;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class DistributedQueueManager {
    private static final Logger LOG = LoggerFactory.getLogger(DistributedQueueManager.class);
    private static final String SET_QUEUE = "hpo_queue";
    private static final String SET_TASKS = "hpo_tasks";
    private static final String QUEUE_KEY = "funding_fee_tasks"; // Tên hàng đợi

    private static final WritePolicy writePolicy = new WritePolicy();
    static {
        writePolicy.sendKey = true;
    }

    // ================== DÀNH CHO MASTER ==================

    /** Master: Đẩy 1 bộ Gen vào hàng đợi và tạo Record trạng thái */
    public static void pushTask(String genomeKey, String paramsStr) {
        try {
            // 1. Tạo Record Task với trạng thái PENDING
            Key taskKey = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TASKS, genomeKey);
            DataManagerAerospikeFloatSim.getClient242().put(writePolicy, taskKey,
                    new Bin("params", paramsStr),
                    new Bin("status", "PENDING"),
                    new Bin("score", 0.0)
            );

            // 2. Đẩy genomeKey vào cuối Hàng đợi (Queue)
            Key queueKey = new Key(Configs.AEROSPIKE_NAMESPACE, SET_QUEUE, QUEUE_KEY);
            DataManagerAerospikeFloatSim.getClient242().operate(writePolicy, queueKey,
                    ListOperation.append("task_list", com.aerospike.client.Value.get(genomeKey))
            );
        } catch (Exception e) {
            LOG.error("❌ Error pushing task: ", e);
        }
    }

    /** Master: Chờ Worker xử lý xong và lấy điểm */
    public static Float waitForResult(String genomeKey) {
        Key taskKey = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TASKS, genomeKey);
        int timeoutSeconds = 300; // Đợi tối đa 5 phút cho 1 task

        while (timeoutSeconds > 0) {
            try {
                Record record = DataManagerAerospikeFloatSim.getClient242().get(null, taskKey);
                if (record != null && "DONE".equals(record.getString("status"))) {
                    return record.getFloat("score");
                }
                Thread.sleep(1000); // Ngủ 1 giây rồi check lại
                timeoutSeconds--;
            } catch (Exception e) {
                // Ignore
            }
        }
        LOG.warn("⚠️ Task Timeout: {}", genomeKey);
        return -10000.0f; // Phạt nặng nếu Worker chết giữa chừng gây timeout
    }

    // ================== DÀNH CHO WORKERS ==================

    /** Worker: Rút 1 Task khỏi đỉnh Hàng đợi (Atomic) */
    public static String popTask() {
        try {
            Key queueKey = new Key(Configs.AEROSPIKE_NAMESPACE, SET_QUEUE, QUEUE_KEY);
            // Rút phần tử index 0 (Pop). Thao tác này là độc quyền (Atomic), không sợ luồng khác cướp mất.
            Record record = DataManagerAerospikeFloatSim.getClient242().operate(writePolicy, queueKey,
                    ListOperation.pop("task_list", 0)
            );

            if (record != null) {
                return record.getString("task_list"); // Trả về genomeKey
            }
        } catch (Exception e) {
            // Hàng đợi rỗng hoặc lỗi
        }
        return null;
    }

    /** Worker: Lấy tham số của Task để chạy */
    public static String getTaskParams(String genomeKey) {
        try {
            Key taskKey = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TASKS, genomeKey);
            Record record = DataManagerAerospikeFloatSim.getClient242().get(null, taskKey);
            if (record != null) {
                return record.getString("params");
            }
        } catch (Exception e) {}
        return null;
    }

    /** Worker: Nộp điểm số và đóng Task */
    public static void submitResult(String genomeKey, float score) {
        try {
            Key taskKey = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TASKS, genomeKey);
            DataManagerAerospikeFloatSim.getClient242().put(writePolicy, taskKey,
                    new Bin("status", "DONE"),
                    new Bin("score", score)
            );
        } catch (Exception e) {
            LOG.error("❌ Error submitting result: ", e);
        }
    }
}