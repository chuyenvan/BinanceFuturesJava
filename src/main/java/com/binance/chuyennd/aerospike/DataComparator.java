package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.util.Map;
import java.util.TreeMap;

public class DataComparator {

    public static void main(String[] args) {
        // 1. Chọn một thời điểm trong quá khứ để check (Ví dụ: hôm qua)
        long currentTime = System.currentTimeMillis();
        long startTime = currentTime - (24L * 60 * 60 * 1000); // 1 ngày trước

        System.out.println("Dang doc du lieu tu 2 nguon de so sanh...");
        System.out.println("Time check: " + startTime);

        // 2. Đọc dữ liệu từ 2 nguồn
        // Nguồn CHUẨN (Cũ - Double)
        long t1 = System.currentTimeMillis();
        TreeMap<Long, Map<String, KlineObjectSimple>> oldData = DataManagerAerospike.readDataFromAerospike1M(startTime);
        System.out.println("Old Data loaded: " + oldData.size() + " phut (Time: " + (System.currentTimeMillis() - t1) + "ms)");

        // Nguồn TEST (Mới/Sim - Float)
        long t2 = System.currentTimeMillis();
        TreeMap<Long, Map<String, KlineObjectSimple>> newData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
        System.out.println("New Data loaded: " + newData.size() + " phut (Time: " + (System.currentTimeMillis() - t2) + "ms)");

        // 3. Bắt đầu so sánh
        compareDatasets(oldData, newData);
    }

    private static void compareDatasets(
            TreeMap<Long, Map<String, KlineObjectSimple>> oldData,
            TreeMap<Long, Map<String, KlineObjectSimple>> newData) {

        System.out.println("\n==========================================");
        System.out.println("          KET QUA SO SANH CHI TIET        ");
        System.out.println("==========================================");

        int totalKeysChecked = 0;
        int totalErrors = 0;
        int missingSymbols = 0;
        double maxPercentDiff = 0.0;
        String worstCaseSymbol = "";

        // Duyệt qua từng phút của dữ liệu CŨ
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : oldData.entrySet()) {
            long timestamp = entry.getKey();
            Map<String, KlineObjectSimple> oldTickers = entry.getValue();

            // Check xem bên MỚI có phút này không
            if (!newData.containsKey(timestamp)) {
//                System.err.println("LOI NGHIEM TRONG: Ben MOI mat toan bo du lieu phut: " + timestamp);
                continue;
            }

            Map<String, KlineObjectSimple> newTickers = newData.get(timestamp);

            // Duyệt qua từng Coin trong phút đó
            for (Map.Entry<String, KlineObjectSimple> tickerEntry : oldTickers.entrySet()) {
                String symbol = tickerEntry.getKey();
                KlineObjectSimple oldKline = tickerEntry.getValue();

                totalKeysChecked++;

                // Check xem bên MỚI có Symbol này không
                // (Lưu ý: Logic cắt đuôi USDT có thể gây lỗi ở đây nếu không map đúng)
                if (!newTickers.containsKey(symbol)) {
                    missingSymbols++;
                    if (missingSymbols < 5) {
                        System.err.println("MISSING SYMBOL: Ben moi khong tim thay " + symbol + " tai thoi diem " + timestamp);
                    }
                    continue;
                }

                KlineObjectSimple newKline = newTickers.get(symbol);

                // SO SÁNH GIÁ TRỊ (Cho phép sai số nhỏ do Float)
                double diffPercent = compareKline(oldKline, newKline, symbol, timestamp);

                if (diffPercent > 0.1) { // Nếu lệch quá 0.1% thì coi là LỖI
                    totalErrors++;
                    if (diffPercent > maxPercentDiff) {
                        maxPercentDiff = diffPercent;
                        worstCaseSymbol = symbol + " (Time: " + timestamp + ")";
                    }

                    // In ra 5 lỗi đầu tiên để debug
                    if (totalErrors < 5) {
                        System.out.println("--- SAI LECH DU LIEU ---");
                        System.out.printf("Symbol: %s | Time: %d\n", symbol, timestamp);
                        System.out.printf("Open OLD: %.8f | NEW: %.8f | Diff: %.4f%%\n", oldKline.priceOpen, newKline.priceOpen, diffPercent);
                        System.out.printf("Vol  OLD: %.8f | NEW: %.8f\n", oldKline.totalUsdt, newKline.totalUsdt);
                    }
                }
            }
        }

        System.out.println("\n---------------- TONG KET ----------------");
        System.out.println("Tong so nén (Kline) da check: " + totalKeysChecked);
        System.out.println("So luong Symbol bi mat (Missing): " + missingSymbols);
        System.out.println("So luong sai lech gia tri (>0.1%): " + totalErrors);

        if (totalErrors > 0) {
            System.out.printf("Sai lech lon nhat (Max Diff): %.4f%% tai %s\n", maxPercentDiff, worstCaseSymbol);
        } else {
            System.out.println("=> DU LIEU KHOP NHAU (Sai so trong pham vi cho phep cua Float)");
        }
    }

    /**
     * So sánh 2 object Kline và trả về % sai lệch lớn nhất giữa các trường
     */
    private static double compareKline(KlineObjectSimple oldK, KlineObjectSimple newK, String symbol, long time) {
        double maxDiff = 0.0;

        maxDiff = Math.max(maxDiff, calculateDiff(oldK.priceOpen, newK.priceOpen));
        maxDiff = Math.max(maxDiff, calculateDiff(oldK.priceClose, newK.priceClose));
        maxDiff = Math.max(maxDiff, calculateDiff(oldK.maxPrice, newK.maxPrice));
        maxDiff = Math.max(maxDiff, calculateDiff(oldK.minPrice, newK.minPrice));

        // Volume thường lệch nhiều hơn giá một chút, có thể check riêng
        // maxDiff = Math.max(maxDiff, calculateDiff(oldK.totalUsdt, newK.totalUsdt));

        return maxDiff;
    }

    private static double calculateDiff(Double v1, Double v2) {
        if (v1 == null || v2 == null) return 100.0; // Lỗi null
        if (v1 == 0 && v2 == 0) return 0.0;
        if (v1 == 0 || v2 == 0) return 100.0; // Một thằng 0, một thằng có giá trị -> Lệch 100%

        double diff = Math.abs(v1 - v2);
        return (diff / v1) * 100.0; // Trả về % sai lệch
    }
}