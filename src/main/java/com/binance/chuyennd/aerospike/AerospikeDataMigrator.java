package com.binance.chuyennd.aerospike;

import com.aerospike.client.*;
import com.aerospike.client.Record;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.Date;

public class AerospikeDataMigrator {
    private static final Logger LOG = LoggerFactory.getLogger(AerospikeDataMigrator.class);

    public static void main(String[] args) {
        // Cấu hình mốc thời gian muốn migrate (Ví dụ từ 01/01/2021)
        long startTime = 1609459200000L; // 2021-01-01 00:00:00 UTC
        migrateByTimeRange(startTime);
    }

    public static void migrateByTimeRange(long startTs) {
        AerospikeClient source = new AerospikeClient("103.157.218.226", 3222);
        AerospikeClient target = new AerospikeClient("103.157.218.242", 3222);

        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true; // 🔥 Bắt buộc để server mới lưu được tên String
        wp.expiration = 0;

        long currentTime = System.currentTimeMillis();
        long movingTs = startTs;

        LOG.info("🚀 Bắt đầu Force Migrate theo mốc thời gian...");

        int count = 0;
        while (movingTs <= currentTime) {
            String keyStr = fmt.format(new Date(movingTs));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, "kline_1m_opt", keyStr);

            // Đọc từ nguồn
            Record record = source.get(null, key);
            if (record != null) {
                // Chuyển bins sang mảng
                Bin[] bins = record.bins.entrySet().stream()
                        .map(e -> new Bin(e.getKey(), e.getValue()))
                        .toArray(Bin[]::new);

                // Ghi sang đích
                target.put(wp, key, bins);
                count++;
                if (count % 1000 == 0) LOG.info("🔄 Đã chuyển: {} (Time: {})", count, keyStr);
            }

            movingTs += 60000L; // Nhảy 1 phút
        }

        LOG.info("🏁 Hoàn tất! Đã chuyển {} bản ghi chuẩn Key String.", count);
        source.close();
        target.close();
    }
}