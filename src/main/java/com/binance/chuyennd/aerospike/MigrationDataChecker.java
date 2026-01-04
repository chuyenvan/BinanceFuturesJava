package com.binance.chuyennd.aerospike;

import com.aerospike.client.*;
import com.aerospike.client.Record;
import com.aerospike.client.policy.ClientPolicy;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.util.Map;

public class MigrationDataChecker {
    private static final Logger LOG = LoggerFactory.getLogger(MigrationDataChecker.class);

    private static final String TARGET_HOST = "103.157.218.242";
    private static final int PORT = 3222;
    private static final String NAMESPACE = Configs.AEROSPIKE_NAMESPACE;
    private static final String SET_NAME = "kline_1m_opt";

    public static void main(String[] args) {
        // Kiểm tra một mốc thời gian cụ thể (Thay đổi theo dữ liệu bạn có)
        String testKey = "20210101-0700";
        checkData(testKey);
    }

    public static void checkData(String keyString) {
        ClientPolicy cp = new ClientPolicy();
        cp.timeout = 10000;

        try (AerospikeClient client = new AerospikeClient(cp, TARGET_HOST, PORT)) {
            LOG.info("🔍 Đang kết nối server .242 để kiểm tra Key: {}", keyString);

            // 1. Thử đọc bằng User Key String
            Key userKey = new Key(NAMESPACE, SET_NAME, keyString);
            Record record = client.get(null, userKey);

            if (record != null) {
                LOG.info("✅ TÌM THẤY dữ liệu bằng User Key String!");
                processRecord(record);
            } else {
                LOG.warn("❌ KHÔNG tìm thấy dữ liệu bằng String Key.");
                LOG.info("--------------------------------------------------");
                LOG.info("🔄 Đang quét (Scan) 1 bản ghi bất kỳ để xem cấu trúc thực tế...");

                ScanPolicy sp = new ScanPolicy();
                sp.maxRecords = 1; // Chỉ lấy 1 bản ghi duy nhất để kiểm tra

                client.scanAll(sp, NAMESPACE, SET_NAME, (key, rec) -> {
                    LOG.info("📌 THÔNG TIN BẢN GHI TRONG DATABASE:");
                    LOG.info("   - UserKey (Giá trị gốc): {}", key.userKey);

                    if (key.userKey == null) {
                        LOG.error("   ❗ CẢNH BÁO: UserKey bị NULL. Đây là lý do bạn không đọc được dữ liệu bằng String!");
                        LOG.info("   - Digest (Mã băm): {}", bytesToHex(key.digest));
                    } else {
                        LOG.info("   - Kiểu dữ liệu UserKey: {}", key.userKey.getClass().getSimpleName());
                    }

                    LOG.info("   - Danh sách Bins hiện có: {}", rec.bins.keySet());
                });
            }

        } catch (Exception e) {
            LOG.error("❌ Lỗi thực thi: {}", e.getMessage());
        }
    }

    private static void processRecord(Record record) {
        try {
            // Java 11: Lấy Object rồi kiểm tra kiểu trước khi ép sang byte[]
            Object dataObj = record.getValue("data");
            if (dataObj instanceof byte[]) {
                byte[] compressedData = (byte[]) dataObj;
                byte[] decompressed = Snappy.uncompress(compressedData);
                MinuteDataFinal protoData = MinuteDataFinal.parseFrom(decompressed);

                LOG.info("🚀 Giải mã thành công! Nến chứa {} mã coin.", protoData.getTickersCount());
                protoData.getTickersMap().entrySet().stream().limit(2).forEach(entry -> {
                    LOG.info("   ⭐ {} | Close: {}", entry.getKey(), entry.getValue().getPriceClose());
                });
            } else {
                LOG.error("⚠️ Bin 'data' không phải kiểu byte[]. Kiểu thực tế: {}",
                        dataObj != null ? dataObj.getClass().getName() : "null");
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi giải mã Snappy/Protobuf: {}", e.getMessage());
        }
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) sb.append(String.format("%02x", b));
        return sb.toString();
    }
}