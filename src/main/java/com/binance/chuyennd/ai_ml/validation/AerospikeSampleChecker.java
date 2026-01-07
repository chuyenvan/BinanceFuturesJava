package com.binance.chuyennd.ai_ml.validation;

import com.aerospike.client.AerospikeClient;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class AerospikeSampleChecker {
    private static final Logger LOG = LoggerFactory.getLogger(AerospikeSampleChecker.class);

    public static void main(String[] args) {
        try {
            // 1. Khởi tạo client cho 2 cụm
            AerospikeClient sourceClient = new AerospikeClient("103.157.218.226", 3222);
            AerospikeClient targetClient = new AerospikeClient("103.157.218.242", 3222);

            // 2. Chọn ngày kiểm tra (Ví dụ ngày hôm qua)
            long startTime = Utils.sdfFile.parse("20230106").getTime() + 7 * Utils.TIME_HOUR;

            // 3. Đọc dữ liệu (Sử dụng hàm Custom để lấy chính xác mốc thời gian)
            TreeMap<Long, Map<String, KlineObjectSimple>> sourceData = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startTime, 1440);
            TreeMap<Long, Map<String, KlineObjectSimple>> targetData = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(startTime, 1440);

            // 4. Lấy ngẫu nhiên 10 mốc thời gian có đủ dữ liệu
            List<Long> allTimestamps = new ArrayList<>(sourceData.keySet());
            Collections.shuffle(allTimestamps);
            List<Long> samples = allTimestamps.subList(0, Math.min(10, allTimestamps.size()));
            samples.sort(Long::compare);

            String[] symbols = {"BTCUSDT", "ETHUSDT"};

            System.out.println("======================================================================================================");
            System.out.println("CHECK DỮ LIỆU ĐỂ SO SÁNH VỚI BINANCE (RANDOM 10 MINUTES)");
            System.out.println("======================================================================================================");

            for (long ts : samples) {
                System.out.println("\n🕒 Thời gian: " + Utils.normalizeDateYYYYMMDDHHmm(ts));

                for (String sym : symbols) {
                    KlineObjectSimple sK = sourceData.get(ts).get(sym);
                    KlineObjectSimple tK = targetData.get(ts).get(sym);

                    if (sK != null) {
                        printKlineInfo("SOURCE (" + sym + ")", sK);
                    }
                    if (tK != null) {
                        printKlineInfo("TARGET (" + sym + ")", tK);
                    }
                }
                System.out.println("------------------------------------------------------------------------------------------------------");
            }

            sourceClient.close();
            targetClient.close();
        } catch (Exception e) {
            LOG.error("❌ Lỗi: {}", e.getMessage());
        }
    }

    private static void printKlineInfo(String label, KlineObjectSimple k) {
        // In theo định dạng dễ nhìn để đối soát Web: O - H - L - C - Vol
        System.out.printf("%-18s | %-18s | Open: %.2f | High: %.2f | Low: %.2f | Close: %.2f | Vol: %,.0f USDT\n",
                label,k.startTime, k.priceOpen, k.maxPrice, k.minPrice, k.priceClose, k.totalUsdt);
    }
}