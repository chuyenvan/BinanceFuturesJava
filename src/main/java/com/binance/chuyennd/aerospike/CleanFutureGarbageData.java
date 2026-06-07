package com.binance.chuyennd.aerospike;

import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.concurrent.atomic.AtomicInteger;

public class CleanFutureGarbageData {
    private static final Logger LOG = LoggerFactory.getLogger(CleanFutureGarbageData.class);

    public static void main(String[] args) {
        LOG.info("🧹 BẮT ĐẦU QUÉT VÀ DỌN DẸP DỮ LIỆU TƯƠNG LAI (GHOST DATA)...");

        // Thời gian thực tế hiện tại
        long currentRealTime = System.currentTimeMillis();
        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        AtomicInteger totalDeleted = new AtomicInteger(0);

        // 3 Set cần kiểm tra
        String[] setsToClean = {
                DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MARKET_DATA,
                DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_AI_PRED_MARKET,
                DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDING_PRED
        };

        ScanPolicy scanPolicy = new ScanPolicy();
        scanPolicy.concurrentNodes = true;
        // Tối ưu: Chỉ kéo Key về RAM, không kéo data để chạy siêu nhanh
        scanPolicy.includeBinData = false;

        for (String setName : setsToClean) {
            LOG.info("🔍 Đang kiểm tra Set: {}", setName);

            try {
                DataManagerAerospikeFloatSim.getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, setName, (key, record) -> {
                    if (key.userKey != null) {
                        try {
                            String keyStr = key.userKey.toString();
                            long recordTime = fmt.parse(keyStr).getTime();

                            // NẾU THỜI GIAN CỦA KEY LỚN HƠN THỜI GIAN THỰC TẾ -> XÓA!
                            if (recordTime > currentRealTime) {
                                DataManagerAerospikeFloatSim.getClient226().delete(null, key);
                                int count = totalDeleted.incrementAndGet();
                                LOG.info("🗑️ Đã xóa bản ghi ảo tương lai: {} (Tổng: {})", keyStr, count);
                            }
                        } catch (Exception e) {
                            // Bỏ qua nếu key không đúng định dạng
                        }
                    }
                });
            } catch (Exception e) {
                LOG.error("Lỗi khi quét Set " + setName, e);
            }
        }

        DataManagerAerospikeFloatSim.closeConnection();
        LOG.info("✅ HOÀN TẤT DỌN DẸP! Đã xóa tổng cộng {} bản ghi tương lai.", totalDeleted.get());
        LOG.info("🚀 Bây giờ bạn có thể bật lại Simulator, nó sẽ tự động chạy bù dữ liệu đúng chuẩn!");
    }
}