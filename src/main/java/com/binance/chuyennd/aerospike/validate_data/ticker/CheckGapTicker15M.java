package com.binance.chuyennd.aerospike.validate_data.ticker;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class CheckGapTicker15M {
    public static final Logger LOG = LoggerFactory.getLogger(CheckGapTicker15M.class);

    public static void main(String[] args) {
        // Test nhanh từ đầu năm 2021
        List<Long> gaps = getMissingTimestamps("20210101-0700");
        LOG.info("Test thấy {} block Ticker 15m bị thiếu.", gaps.size());
    }

    /**
     * Hàm lấy danh sách các block 15 phút bị thiếu (Timestamp Long)
     */
    public static List<Long> getMissingTimestamps(String startDateStr) {
        List<Long> missingList = new ArrayList<>();

        // 🔥 1. Đổi tên Set sang nến 15m
        String setName = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER_15M;

        AerospikeClient client = DataManagerAerospikeFloatSim.getClient226();

        try {
            SimpleDateFormat inputFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");

            long rawStartTime = inputFmt.parse(startDateStr).getTime();
            // 🔥 3. Căn chỉnh ép về mốc chẵn 15 phút (00, 15, 30, 45)
            long startTime = rawStartTime - (rawStartTime % (15 * 60000L));

            long endTime = System.currentTimeMillis();
            // 🔥 4. Bước nhảy 15 phút
            long step = 15 * 60000L;

            BatchPolicy batchPolicy = new BatchPolicy();
            batchPolicy.maxConcurrentThreads = 4;

            int batchSize = 5000;
            List<Long> timeBuffer = new ArrayList<>();
            List<Key> keyBuffer = new ArrayList<>();

            LOG.info("🚀 [TICKER GAP 15M] Đang quét lổ hổng từ {}...", startDateStr);

            for (long t = startTime; t <= endTime; t += step) {
                timeBuffer.add(t);
                String keyStr = keyFmt.format(new Date(t));
                keyBuffer.add(new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyStr));

                if (keyBuffer.size() == batchSize || t + step > endTime) {
                    Key[] keysArray = keyBuffer.toArray(new Key[0]);
                    // Check tồn tại cực nhanh (chỉ check Metadata, không kéo Data về RAM)
                    boolean[] existsArray = client.exists(batchPolicy, keysArray);

                    for (int i = 0; i < existsArray.length; i++) {
                        if (!existsArray[i]) {
                            missingList.add(timeBuffer.get(i));
                        }
                    }

                    timeBuffer.clear();
                    keyBuffer.clear();
                }
            }

            LOG.info("✅ Quét xong! Phát hiện {} lổ hổng Ticker 15M.", missingList.size());

        } catch (Exception e) {
            LOG.error("Lỗi khi quét Aerospike Ticker 15M", e);
        }
        return missingList;
    }
}