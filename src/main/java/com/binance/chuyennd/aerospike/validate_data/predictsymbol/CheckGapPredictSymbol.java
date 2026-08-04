package com.binance.chuyennd.aerospike.validate_data.predictsymbol;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class CheckGapPredictSymbol {
    public static final Logger LOG = LoggerFactory.getLogger(CheckGapPredictSymbol.class);

    public static void main(String[] args) {
        String setName = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDING_PRED;
        AerospikeClient client = DataManagerAerospikeFloatSim.getClientOracle();
        String startDateStr = "20210101";

        scanMissingData(client, setName, startDateStr);
    }

    public static void scanMissingData(AerospikeClient client, String setName, String startDateStr) {
        try {
            SimpleDateFormat dayFmt = new SimpleDateFormat("yyyyMMdd");
            SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");

            long startTime = dayFmt.parse(startDateStr).getTime() + 7 * Utils.TIME_HOUR;
            long endTime = System.currentTimeMillis();
            long step = 60000L;

            BatchPolicy batchPolicy = new BatchPolicy();
            batchPolicy.maxConcurrentThreads = 4;

            int batchSize = 5000;
            List<Long> timeBuffer = new ArrayList<>();
            List<Key> keyBuffer = new ArrayList<>();

            long totalMissing = 0;
            long totalChecked = 0;

            LOG.info("🚀 [PREDICT SYMBOL] BẮT ĐẦU QUÉT SET [{}] TỪ {} ĐẾN NAY...", setName, startDateStr);

            for (long t = startTime; t <= endTime; t += step) {
                timeBuffer.add(t);
                String keyStr = keyFmt.format(new Date(t));
                keyBuffer.add(new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyStr));

                if (keyBuffer.size() == batchSize || t + step > endTime) {
                    Key[] keysArray = keyBuffer.toArray(new Key[0]);
                    boolean[] existsArray = client.exists(batchPolicy, keysArray);

                    for (int i = 0; i < existsArray.length; i++) {
                        if (!existsArray[i]) {
                            totalMissing++;
                            if (totalMissing <= 100) {
                                LOG.warn("❌ [PREDICT SYM] THIẾU TẠI PHÚT: {}", keyFmt.format(new Date(timeBuffer.get(i))));
                            } else if (totalMissing == 101) {
                                LOG.warn("⚠️ ... (Phát hiện quá nhiều lổ hổng, đã ẩn bớt log) ...");
                            }
                        }
                    }

                    totalChecked += keyBuffer.size();
                    if (totalChecked % 500000 == 0) {
                        LOG.info("🔄 [PREDICT SYM] Tiến độ: {} phút...", totalChecked);
                    }

                    timeBuffer.clear();
                    keyBuffer.clear();
                }
            }

            LOG.info("==========================================================");
            LOG.info("✅ HOÀN TẤT QUÉT PREDICT SYMBOL: [{}]", setName);
            LOG.info("📊 Tổng kiểm tra : {}", totalChecked);
            LOG.info("🚨 THIẾU        : {} ({}%)", totalMissing, String.format("%.4f", (float) totalMissing / totalChecked * 100));
            LOG.info("==========================================================");
        } catch (Exception e) {
            LOG.error("Lỗi khi quét Aerospike", e);
        }
    }
}