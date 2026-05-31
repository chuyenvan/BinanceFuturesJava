package com.binance.chuyennd.aerospike.validate_data.ticker;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class CheckGapTicker {
    public static final Logger LOG = LoggerFactory.getLogger(CheckGapTicker.class);

    public static void main(String[] args) {
        // Test nhanh
        List<Long> gaps = getMissingTimestamps("20210101-0700");
        LOG.info("Test thấy {} phút bị thiếu.", gaps.size());
    }

    /**
     * Hàm lấy danh sách các phút bị thiếu (Timestamp Long)
     */
    public static List<Long> getMissingTimestamps(String startDateStr) {
        List<Long> missingList = new ArrayList<>();
        String setName = "kline_1m_opt";
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient242();

        try {
            // Định dạng mới hỗ trợ cả giờ phút (VD: 20210101-0700)
            SimpleDateFormat inputFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");

            long startTime = inputFmt.parse(startDateStr).getTime();
            long endTime = System.currentTimeMillis();
            long step = 60000L;

            BatchPolicy batchPolicy = new BatchPolicy();
            batchPolicy.maxConcurrentThreads = 4;

            int batchSize = 5000;
            List<Long> timeBuffer = new ArrayList<>();
            List<Key> keyBuffer = new ArrayList<>();

            LOG.info("🚀 [TICKER GAP] Đang quét lổ hổng từ {}...", startDateStr);

            for (long t = startTime; t <= endTime; t += step) {
                timeBuffer.add(t);
                String keyStr = keyFmt.format(new Date(t));
                keyBuffer.add(new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyStr));

                if (keyBuffer.size() == batchSize || t + step > endTime) {
                    Key[] keysArray = keyBuffer.toArray(new Key[0]);
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

            LOG.info("✅ Quét xong! Phát hiện {} lổ hổng Ticker.", missingList.size());

        } catch (Exception e) {
            LOG.error("Lỗi khi quét Aerospike Ticker", e);
        }
        return missingList;
    }
}