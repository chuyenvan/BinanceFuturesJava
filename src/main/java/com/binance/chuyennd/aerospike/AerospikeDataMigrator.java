package com.binance.chuyennd.aerospike;

import com.aerospike.client.*;
import com.aerospike.client.policy.ClientPolicy;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.atomic.AtomicInteger;

public class AerospikeDataMigrator {
    private static final Logger LOG = LoggerFactory.getLogger(AerospikeDataMigrator.class);

    private static final String SOURCE_HOST = "103.157.218.226";
    private static final String TARGET_HOST = "103.157.218.242";
    private static final String NAMESPACE = Configs.AEROSPIKE_NAMESPACE;
    private static final String SET_NAME = "kline_1m_opt";

    public static void main(String[] args) {
        migrate();
    }

    public static void migrate() {
        try (AerospikeClient source = new AerospikeClient(SOURCE_HOST, 3222);
             AerospikeClient target = new AerospikeClient(TARGET_HOST, 3222)) {

            LOG.info("🚀 Bắt đầu chuyển nến 1m từ .226 sang .242...");

            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true; // Quét song song tất cả các node

            WritePolicy writePolicy = new WritePolicy();
            writePolicy.expiration = 0; // Lưu vĩnh viễn
            writePolicy.sendKey = true; // Bắt buộc lưu UserKey để giữ định dạng yyyyMMdd-HHmm

            AtomicInteger total = new AtomicInteger(0);

            source.scanAll(scanPolicy, NAMESPACE, SET_NAME, (key, record) -> {
                // Vì bạn dùng yyyyMMdd-HHmm, lấy giá trị String từ userKey
                Object userKey = (key.userKey != null) ? key.userKey.getObject() : key.digest;

                Key targetKey = new Key(NAMESPACE, SET_NAME, Value.get(userKey));

                // Copy Bin "data" (chứa Protobuf + Snappy)
                target.put(writePolicy, targetKey, new Bin("data", record.getValue("data")));

                int count = total.incrementAndGet();
                if (count % 500 == 0) LOG.info("🔄 Đã copy {} nến...", count);
            });

            LOG.info("🏁 Hoàn tất! Đã migrate thành công {} bản ghi.", total.get());

        } catch (Exception e) {
            LOG.error("❌ Lỗi Migration: {}", e.getMessage());
        }
    }
}