package com.binance.chuyennd.aerospike.validate_data.predictmarket;


import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import java.util.Map;

public class DebugMinute {
    public static void main(String[] args) throws Exception {
        // Trỏ vào đúng phút đang báo lỗi
        long time = Utils.sdfFileHour.parse("20210302 08:01").getTime();

        // Kéo 2 phút ra xem
        java.util.TreeMap<Long, Map<String, KlineObjectSimple>> data =
                DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(time, 2);

        for (Long t : data.keySet()) {
            System.out.println("\n====== PHÚT: " + Utils.normalizeDateYYYYMMDDHHmm(t) + " ======");
            Map<String, KlineObjectSimple> tickers = data.get(t);
            System.out.println("Tổng số Symbol: " + tickers.size());

            int count = 0;
            for (String sym : tickers.keySet()) {
                KlineObjectSimple k = tickers.get(sym);
                System.out.println(String.format("👉 %-10s | Open: %-8s | Close: %-8s | High: %-8s | Low: %-8s | Vol USDT: %s",
                        sym, k.priceOpen, k.priceClose, k.maxPrice, k.minPrice, k.totalUsdt));

                // Kiểm tra luôn hàm isTickerAvailable
                boolean isAvailable = Utils.isTickerAvailable(k);
                if (!isAvailable) {
                    System.out.println("   ❌ isTickerAvailable = FALSE (Bị loại khỏi AI)");
                }

                count++;
                if (count >= 5) break; // In 5 đồng đại diện thôi cho đỡ rác console
            }
        }
        DataManagerAerospikeFloatSim.closeConnection();
        System.exit(0);
    }
}