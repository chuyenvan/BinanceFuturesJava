package com.binance.chuyennd.aerospike;

import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

public class MigrateFundingJsonToBinary {
    private static final Logger LOG = LoggerFactory.getLogger(MigrateFundingJsonToBinary.class);

    // 🔥 TÊN SET CŨ (JSON) VÀ SET MỚI (BINARY)
    private static final String OLD_SET_NAME = "funding_pred_1m_v3"; // Thay bằng đúng tên set cũ của bạn
    private static final String NEW_SET_NAME = "funding_pred_1m_v4"; // Set mới siêu tốc

    public static void main(String[] args) {
        LOG.info("🚀 STARTING MIGRATION: {} -> {}", OLD_SET_NAME, NEW_SET_NAME);
        long startTime = System.currentTimeMillis();

        AtomicInteger countSuccess = new AtomicInteger(0);
        AtomicInteger countError = new AtomicInteger(0);

        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true;

            WritePolicy writePolicy = new WritePolicy();
            writePolicy.sendKey = true; // Bắt buộc giữ key gốc

            // Quét đa luồng toàn bộ Set Cũ
            DataManagerAerospikeFloatSim.getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, OLD_SET_NAME, (key, record) -> {
                try {
                    if (key.userKey == null) return;
                    String keyStr = key.userKey.toString();

                    // 1. ĐỌC DỮ LIỆU CŨ (JSON NÉN)
                    byte[] oldCompressed = (byte[]) record.getValue("data");
                    if (oldCompressed == null) return;

                    byte[] oldRawBytes = Snappy.uncompress(oldCompressed);
                    String json = new String(oldRawBytes, "UTF-8");
                    Map<Short, float[]> dataMap = Utils.gson.fromJson(json, new com.google.gson.reflect.TypeToken<Map<Short, float[]>>() {}.getType());

                    if (dataMap != null && !dataMap.isEmpty()) {

                        // 2. MÃ HÓA SANG DỮ LIỆU MỚI (BINARY NÉN)
                        byte[] newRawBytes = DataManagerAerospikeFloatSim.encodeFundingMapToBinary(dataMap);
                        byte[] newCompressed = Snappy.compress(newRawBytes);

                        // 3. GHI VÀO SET MỚI
                        Key newKey = new Key(Configs.AEROSPIKE_NAMESPACE, NEW_SET_NAME, keyStr);
                        DataManagerAerospikeFloatSim.getClient226().put(writePolicy, newKey, new Bin("data", newCompressed));

                        // Đếm tiến độ
                        int currentCount = countSuccess.incrementAndGet();
                        if (currentCount % 20000 == 0) {
                            LOG.info("⚡ Đã chuyển đổi thành công {} records...", currentCount);
                        }
                    }
                } catch (Exception e) {
                    countError.incrementAndGet();
                    // LOG.error("Lỗi tại key {}: {}", key.userKey, e.getMessage());
                }
            }, "data");

            long duration = (System.currentTimeMillis() - startTime) / 1000;
            LOG.info("=========================================");
            LOG.info("🎉 MIGRATION HOÀN TẤT SAU {} GIÂY!", duration);
            LOG.info("✅ Số record thành công: {}", countSuccess.get());
            LOG.info("❌ Số record bị lỗi: {}", countError.get());
            LOG.info("=========================================");

        } catch (Exception e) {
            LOG.error("Migration failed", e);
        } finally {
            // Tắt hoàn toàn client để kết thúc tiến trình
            DataManagerAerospikeFloatSim.closeConnection();
            System.exit(0);
        }
    }
}