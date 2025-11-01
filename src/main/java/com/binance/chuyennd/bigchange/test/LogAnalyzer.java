package com.binance.chuyennd.bigchange.test;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects; // Cần thiết cho equals và hashCode

/**
 * Đọc file log, phân tích "Trade" và "Not trade".
 * Thống kê theo Năm, Level, và Loại Trade (Trade/Not trade).
 * (Phiên bản Java 11)
 * Xuất kết quả ra file CSV.
 */
public class LogAnalyzer {

    // Hằng số cho dễ thay đổi
    private static final String INPUT_FILE = "target/tradelog.txt";
    private static final String OUTPUT_FILE = "target/trade_statistics.csv";

    // Đánh dấu mới
    private static final String NOT_TRADE_MARKER = "Not trade : ";
    private static final String TRADE_MARKER = "Trade : ";

    // --- LỚP KEY MỚI (THAY THẾ RECORD) ---
    /**
     * Key cho HashMap, lưu trữ [Năm, Level, Loại Trade]
     * BẮT BUỘC phải implement equals() và hashCode().
     */
    public static final class AggregationKey {
        private final String year;
        private final String level;
        private final String tradeType; // Thay thế cho btcStatus

        public AggregationKey(String year, String level, String tradeType) {
            this.year = year;
            this.level = level;
            this.tradeType = tradeType;
        }

        // Getters
        public String year() { return year; }
        public String level() { return level; }
        public String tradeType() { return tradeType; } // Getter mới

        // BẮT BUỘC: equals() và hashCode() để HashMap hoạt động
        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            AggregationKey that = (AggregationKey) o;
            return Objects.equals(year, that.year) &&
                    Objects.equals(level, that.level) &&
                    Objects.equals(tradeType, that.tradeType); // Cập nhật
        }

        @Override
        public int hashCode() {
            return Objects.hash(year, level, tradeType); // Cập nhật
        }

        @Override
        public String toString() {
            return "AggregationKey[" +
                    "year='" + year + '\'' +
                    ", level='" + level + '\'' +
                    ", tradeType='" + tradeType + '\'' + // Cập nhật
                    ']';
        }
    }
    // --- KẾT THÚC LỚP KEY ---


    public static void main(String[] args) {
        System.out.println("Bat dau phan tich file: " + INPUT_FILE);

        Map<AggregationKey, Long> tradeStats = new HashMap<>();

        try (BufferedReader reader = new BufferedReader(new FileReader(INPUT_FILE))) {
            String line;
            int lineNumber = 0;

            while ((line = reader.readLine()) != null) {
                lineNumber++;

                String dataPart = null;
                String tradeType = null;

                // --- LOGIC PHÂN TÍCH MỚI ---
                // Phải kiểm tra "Not trade : " TRƯỚC "Trade : "
                // vì "Not trade : " cũng chứa chuỗi "Trade : "
                int notTradeIndex = line.indexOf(NOT_TRADE_MARKER);
                if (notTradeIndex != -1) {
                    // Tìm thấy "Not trade : "
                    dataPart = line.substring(notTradeIndex + NOT_TRADE_MARKER.length()).trim();
                    tradeType = "Not trade";
                } else {
                    // Nếu không thấy "Not trade", kiểm tra "Trade"
                    int tradeIndex = line.indexOf(TRADE_MARKER);
                    if (tradeIndex != -1) {
                        // Tìm thấy "Trade : "
                        dataPart = line.substring(tradeIndex + TRADE_MARKER.length()).trim();
                        tradeType = "Trade";
                    } else {
                        // Không tìm thấy cả hai, bỏ qua dòng này
                        continue;
                    }
                }
                // --- KẾT THÚC LOGIC MỚI ---

                try {
                    // 2. Tách chuỗi dữ liệu
                    String[] parts = dataPart.split("\\s+");

                    // 3. Trích xuất thông tin
                    // Format log: [Symbol] [Level] [BtcStatus] [Date] [Time]
                    if (parts.length < 4) {
                        System.err.println("WARN: Dong " + lineNumber + " co format khong dung, bo qua: " + line);
                        continue;
                    }

                    // Chúng ta lấy Level (vị trí 1) và Date (vị trí 3)
                    // Bỏ qua BtcStatus (vị trí 2) theo yêu cầu
                    String level = parts[1];
                    String dateStr = parts[3]; // Format YYYYMMDD

                    // Lấy năm từ dateStr
                    if (dateStr.length() != 8) {
                        System.err.println("WARN: Dong " + lineNumber + " co format ngay thang khong dung: " + dateStr);
                        continue;
                    }
                    String year = dateStr.substring(0, 4);

                    // 4. Cập nhật thống kê
                    // (Sử dụng tradeType đã xác định ở trên)

                    // Tạo key cho năm cụ thể (VD: 2025, FUNDING_FEE_BUY, "Not trade")
                    AggregationKey yearKey = new AggregationKey(year, level, tradeType);
                    tradeStats.put(yearKey, tradeStats.getOrDefault(yearKey, 0L) + 1);

                    // Tạo key cho tổng (VD: TOTAL, FUNDING_FEE_BUY, "Not trade")
                    AggregationKey totalKey = new AggregationKey("TOTAL", level, tradeType);
                    tradeStats.put(totalKey, tradeStats.getOrDefault(totalKey, 0L) + 1);

                } catch (Exception e) {
                    System.err.println("ERROR: Gap loi khi phan tich dong " + lineNumber + ": " + line);
                    e.printStackTrace();
                }
            }

            System.out.println("Phan tich log thanh cong. Tong so luong key thong ke: " + tradeStats.size());

            // 5. Ghi kết quả ra file CSV
            writeCsv(tradeStats);

        } catch (IOException e) {
            System.err.println("ERROR: Khong the doc file: " + INPUT_FILE);
            e.printStackTrace();
        }
    }

    /**
     * Ghi Map thống kê ra file CSV, đã được sắp xếp
     * @param stats Map chứa dữ liệu thống kê
     */
    private static void writeCsv(Map<AggregationKey, Long> stats) {
        // Sắp xếp các key
        // Ưu tiên 1: Năm (TOTAL xuống cuối)
        // Ưu tiên 2: Level
        // Ưu tiên 3: Loại Trade (Not trade, Trade)
        List<AggregationKey> sortedKeys = new ArrayList<>(stats.keySet());

        sortedKeys.sort(Comparator
                .comparing(AggregationKey::year, (y1, y2) -> {
                    if (y1.equals("TOTAL") && y2.equals("TOTAL")) return 0;
                    if (y1.equals("TOTAL")) return 1;
                    if (y2.equals("TOTAL")) return -1;
                    return y1.compareTo(y2);
                })
                .thenComparing(AggregationKey::level)
                .thenComparing(AggregationKey::tradeType) // Cập nhật
        );

        // Bắt đầu ghi file
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(OUTPUT_FILE))) {
            // Ghi header (tiêu đề cột) - ĐÃ CẬP NHẬT
            writer.write("Year,Level,TradeType,TradeCount\n");

            // Ghi từng dòng dữ liệu
            for (AggregationKey key : sortedKeys) {
                Long count = stats.get(key);
                // CẬP NHẬT: key.tradeType() thay cho key.btcStatus()
                writer.write(String.format("%s,%s,%s,%d\n",
                        key.year(),
                        key.level(),
                        key.tradeType(), // Cập nhật
                        count
                ));
            }

            System.out.println("Xuat file CSV thanh cong: " + OUTPUT_FILE);

        } catch (IOException e) {
            System.err.println("ERROR: Khong the ghi file CSV: " + OUTPUT_FILE);
            e.printStackTrace();
        }
    }
}