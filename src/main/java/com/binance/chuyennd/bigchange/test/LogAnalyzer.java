package com.binance.chuyennd.bigchange.test;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.Collections;

/**
 * Đọc file log, phân tích "Trade" và "Not trade".
 * Thống kê và xuất ra file CSV dạng Pivot (matrix):
 * - Hàng (Row): Level
 * - Cột (Column): [Year]_[TradeType] (ví dụ: 2024_Trade, 2024_Nottrade, TOTAL_Trade)
 * (Phiên bản Java 11)
 */
public class LogAnalyzer {

    // Hằng số cho dễ thay đổi
    private static final String INPUT_FILE = "target/tradelog.txt";
    private static final String OUTPUT_FILE = "target/trade_statistics.csv"; // Đổi tên file output

    // Đánh dấu
    private static final String NOT_TRADE_MARKER = "Not trade : ";
    private static final String TRADE_MARKER = "Trade : ";

    public static void main(String[] args) {
        System.out.println("Bat dau phan tich file: " + INPUT_FILE);

        // Cấu trúc dữ liệu mới:
        // Key ngoài (String): Level (ví dụ: "DCA_LEVEL1", "FUNDING_FEE_BUY")
        // Key trong (String): Composite Key (ví dụ: "2024_Trade", "TOTAL_Nottrade")
        // Value (Long): Số lượng đếm
        Map<String, Map<String, Long>> levelStats = new HashMap<>();

        // Set này dùng để gom tất cả các cột (Year_TradeType) sẽ có trong file CSV
        Set<String> allColumns = new HashSet<>();

        try (BufferedReader reader = new BufferedReader(new FileReader(INPUT_FILE))) {
            String line;
            int lineNumber = 0;

            while ((line = reader.readLine()) != null) {
                lineNumber++;

                String dataPart = null;
                String tradeType = null;

                // 1. Phân tích dòng log (giữ nguyên logic cũ)
                int notTradeIndex = line.indexOf(NOT_TRADE_MARKER);
                if (notTradeIndex != -1) {
                    dataPart = line.substring(notTradeIndex + NOT_TRADE_MARKER.length()).trim();
                    tradeType = "Nottrade"; // Gộp thành 1 từ cho header CSV
                } else {
                    int tradeIndex = line.indexOf(TRADE_MARKER);
                    if (tradeIndex != -1) {
                        dataPart = line.substring(tradeIndex + TRADE_MARKER.length()).trim();
                        tradeType = "Trade";
                    } else {
                        continue;
                    }
                }

                try {
                    // 2. Trích xuất thông tin (giữ nguyên logic cũ)
                    String[] parts = dataPart.split("\\s+");
                    if (parts.length < 4) {
                        System.err.println("WARN: Dong " + lineNumber + " co format khong dung, bo qua: " + line);
                        continue;
                    }
                    String level = parts[1]; // Đây sẽ là HÀNG (ROW)
                    String dateStr = parts[3];
                    if (dateStr.length() != 8) {
                        System.err.println("WARN: Dong " + lineNumber + " co format ngay thang khong dung: " + dateStr);
                        continue;
                    }
                    String year = dateStr.substring(0, 4);

                    // 3. TẠO KEY CỘT MỚI VÀ CẬP NHẬT MAP

                    // Tạo "Composite Key" (khóa tổng hợp) cho CỘT
                    // Ví dụ: "2025" + "_" + "Trade" -> "2025_Trade"
                    String yearColumnKey = year + "_" + tradeType;

                    // Tạo key cho cột TOTAL
                    // Ví dụ: "TOTAL" + "_" + "Trade" -> "TOTAL_Trade"
                    String totalColumnKey = "TOTAL_" + tradeType;

                    // Thêm các key này vào Set để biết tất cả các cột
                    allColumns.add(yearColumnKey);
                    allColumns.add(totalColumnKey);

                    // Cập nhật số đếm cho hàng 'level' này
                    updateStatsMap(levelStats, level, yearColumnKey);
                    updateStatsMap(levelStats, level, totalColumnKey);

                } catch (Exception e) {
                    System.err.println("ERROR: Gap loi khi phan tich dong " + lineNumber + ": " + line);
                    e.printStackTrace();
                }
            }

            System.out.println("Phan tich log thanh cong. Tong so luong cot (Year+Loai) tim thay: " + allColumns.size());

            // 5. Ghi kết quả ra file CSV (logic mới)
            writePivotCsv(levelStats, allColumns);

        } catch (IOException e) {
            System.err.println("ERROR: Khong the doc file: " + INPUT_FILE);
            e.printStackTrace();
        }
    }

    /**
     * Hàm hỗ trợ để cập nhật nested map (Map lồng nhau).
     * @param statsMap Map tổng
     * @param rowKey Key của hàng (VD: "DCA_LEVEL1")
     * @param columnKey Key của cột (VD: "2025_Trade")
     */
    private static void updateStatsMap(Map<String, Map<String, Long>> statsMap, String rowKey, String columnKey) {
        // Lấy hoặc tạo mới Map con cho 'rowKey'
        Map<String, Long> columnStats = statsMap.computeIfAbsent(rowKey, k -> new HashMap<>());

        // Cập nhật (hoặc_tạo mới) số đếm cho 'columnKey'
        columnStats.put(columnKey, columnStats.getOrDefault(columnKey, 0L) + 1);
    }


    /**
     * Ghi Map thống kê ra file CSV dạng Pivot (matrix).
     * @param levelStats Map chứa dữ liệu thống kê (Key: Level)
     * @param allColumns Set chứa tất cả các header cột (VD: "2025_Trade", "TOTAL_Nottrade")
     */
    private static void writePivotCsv(Map<String, Map<String, Long>> levelStats, Set<String> allColumns) {

        // --- Chuẩn bị Header (Cột) ---
        List<String> sortedColumns = new ArrayList<>(allColumns);

        // Sắp xếp các cột: 2024_Nottrade, 2024_Trade, 2025_Nottrade, ..., TOTAL_Nottrade, TOTAL_Trade
        Collections.sort(sortedColumns, new Comparator<String>() {
            @Override
            public int compare(String c1, String c2) {
                String[] parts1 = c1.split("_");
                String[] parts2 = c2.split("_");

                String year1 = parts1[0];
                String type1 = parts1[1];
                String year2 = parts2[0];
                String type2 = parts2[1];

                // So sánh Năm (đẩy TOTAL xuống cuối)
                int yearCompare;
                if (year1.equals("TOTAL") && year2.equals("TOTAL")) yearCompare = 0;
                else if (year1.equals("TOTAL")) yearCompare = 1;
                else if (year2.equals("TOTAL")) yearCompare = -1;
                else yearCompare = year1.compareTo(year2);

                if (yearCompare != 0) {
                    return yearCompare;
                }

                // Nếu cùng Năm (hoặc cùng TOTAL), so sánh Loại (Nottrade, Trade)
                return type1.compareTo(type2);
            }
        });

        // --- Chuẩn bị Hàng (Levels) ---
        List<String> sortedLevels = new ArrayList<>(levelStats.keySet());
        Collections.sort(sortedLevels); // Sắp xếp Level theo A-Z

        // Bắt đầu ghi file
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(OUTPUT_FILE))) {

            // 1. Ghi dòng Header (Tiêu đề cột)
            writer.write("Level"); // Cột đầu tiên luôn là "Level"
            for (String columnHeader : sortedColumns) {
                writer.write("," + columnHeader);
            }
            writer.write("\n"); // Xuống dòng

            // 2. Ghi từng dòng dữ liệu (mỗi dòng 1 Level)
            for (String level : sortedLevels) {
                writer.write(level); // Ghi tên Level ở cột đầu tiên

                // Lấy Map con chứa dữ liệu của Level này
                Map<String, Long> columnStats = levelStats.get(level);

                // Lặp qua TẤT CẢ các cột đã sắp xếp
                for (String columnHeader : sortedColumns) {
                    // Lấy giá trị đếm của cột này, nếu không có thì dùng số 0
                    Long count = columnStats.getOrDefault(columnHeader, 0L);
                    writer.write("," + count);
                }
                writer.write("\n"); // Xuống dòng, chuẩn bị cho Level tiếp theo
            }

            System.out.println("Xuat file CSV Pivot thanh cong: " + OUTPUT_FILE);

        } catch (IOException e) {
            System.err.println("ERROR: Khong the ghi file CSV: " + OUTPUT_FILE);
            e.printStackTrace();
        }
    }
}