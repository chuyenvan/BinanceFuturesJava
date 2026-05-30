package com.binance.chuyennd.aerospike.validate_data.predictsymbol;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class CheckGapPredictSymbol15M {
    public static final Logger LOG = LoggerFactory.getLogger(CheckGapPredictSymbol15M.class);

    public static void main(String[] args) {
        // 🔥 ĐỔI SANG SET NAME 15M (Bác hãy kiểm tra chính xác constant này trong DataManagerAerospikeFloatSim)
        String setName = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDING_PRED_15M;
        AerospikeClient client = DataManagerAerospikeFloatSim.getClient226();
        String startDateStr = "20210101";

        scanMissingData15M(client, setName, startDateStr);
    }

    public static void scanMissingData15M(AerospikeClient client, String setName, String startDateStr) {
        try {
            SimpleDateFormat dayFmt = new SimpleDateFormat("yyyyMMdd");
            SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");

            long startTime = dayFmt.parse(startDateStr).getTime() + 7 * Utils.TIME_HOUR;

            // 🔥 QUAN TRỌNG: Ép mốc bắt đầu về đúng điểm 15 phút đầu tiên (Floor Time)
            long step = 15 * 60000L; // 15 phút
            startTime = startTime - (startTime % step);

            long endTime = System.currentTimeMillis();

            BatchPolicy batchPolicy = new BatchPolicy();
            batchPolicy.maxConcurrentThreads = 4;

            int batchSize = 5000;
            List<Long> timeBuffer = new ArrayList<>();
            List<Key> keyBuffer = new ArrayList<>();

            long totalMissing = 0;
            long totalChecked = 0;

            LOG.info("🚀 [15M CHECK] BẮT ĐẦU QUÉT SET [{}] TỪ {} ĐẾN NAY...", setName, keyFmt.format(new Date(startTime)));

            for (long t = startTime; t <= endTime; t += step) {
                timeBuffer.add(t);
                String keyStr = keyFmt.format(new Date(t));
                keyBuffer.add(new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyStr));

                // Gửi batch kiểm tra khi đủ size hoặc đến cuối dữ liệu
                if (keyBuffer.size() == batchSize || t + step > endTime) {
                    Key[] keysArray = keyBuffer.toArray(new Key[0]);
                    boolean[] existsArray = client.exists(batchPolicy, keysArray);

                    for (int i = 0; i < existsArray.length; i++) {
                        if (!existsArray[i]) {
                            totalMissing++;
                            if (totalMissing <= 100) {
                                LOG.warn("❌ [15M GAP] THIẾU TẠI: {}", keyFmt.format(new Date(timeBuffer.get(i))));
                            } else if (totalMissing == 101) {
                                LOG.warn("⚠️ ... (Phát hiện quá nhiều lổ hổng, đã ẩn bớt log) ...");
                            }
                        }
                    }

                    totalChecked += keyBuffer.size();
                    if (totalChecked % 50000 == 0) {
                        LOG.info("🔄 [15M CHECK] Tiến độ: {} block 15 phút...", totalChecked);
                    }

                    timeBuffer.clear();
                    keyBuffer.clear();
                }
            }

            LOG.info("==========================================================");
            LOG.info("✅ HOÀN TẤT QUÉT GAP 15M: [{}]", setName);
            LOG.info("📊 Tổng block kiểm tra : {}", totalChecked);
            LOG.info("🚨 BLOCK BỊ THIẾU     : {} ({}%)", totalMissing,
                    totalChecked > 0 ? String.format("%.4f", (float) totalMissing / totalChecked * 100) : "0");
            LOG.info("==========================================================");
        } catch (Exception e) {
            LOG.error("Lỗi khi quét Aerospike gap 15M", e);
        }
    }
}