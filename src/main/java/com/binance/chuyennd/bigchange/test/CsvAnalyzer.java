package com.binance.chuyennd.bigchange.test;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;

import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.Reader;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class CsvAnalyzer {

    private static class TradeEntry {
        public CSVRecord originalRecord;
        public LocalDateTime startTime;
        public LocalDateTime endTime;
        public String symbol;
        public String level;
        public String sequenceId;

        private static LocalDateTime robustParse(String timeStr) {
            if (timeStr == null || timeStr.isEmpty()) return null;
            timeStr = timeStr.replace("'", "").trim();
            DateTimeFormatter[] formatters = {
                    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
                    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm"),
                    DateTimeFormatter.ofPattern("yyyyMMdd HH:mm"),
                    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS"),
                    DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")
            };
            for (DateTimeFormatter formatter : formatters) {
                try {
                    return LocalDateTime.parse(timeStr, formatter);
                } catch (DateTimeParseException e) {
                    // Continue to next format
                }
            }
            return null;
        }

        public static TradeEntry fromCsvRecord(CSVRecord record) {
            try {
                TradeEntry entry = new TradeEntry();
                entry.originalRecord = record;
                entry.symbol = record.get("sym");
                entry.level = record.get("level");
                entry.startTime = robustParse(record.get("start"));
                entry.endTime = robustParse(record.get("end"));
                if (entry.startTime == null || entry.endTime == null) {
                    return null;
                }
                return entry;
            } catch (Exception e) {
                return null;
            }
        }
    }

    public static void main(String[] args) {
        String inputFile = "target/printDone.csv";
        String outputFile = "target/high_frequency_details.csv";
        int orderThreshold = 100;

        System.out.println("--- BẮT ĐẦU CHƯƠNG TRÌNH PHÂN TÍCH (JAVA 11 COMPATIBLE) ---");
        try {
            // 1. Đọc và xử lý file CSV
            System.out.println("1. Đang đọc và xử lý file '" + inputFile + "'...");
            List<TradeEntry> allEntries = new ArrayList<>();
            Reader in = new FileReader(inputFile);
            CSVFormat csvFormat = CSVFormat.DEFAULT.withHeader().withSkipHeaderRecord(true).withIgnoreEmptyLines(true).withIgnoreSurroundingSpaces(true);
            CSVParser records = new CSVParser(in, csvFormat);

            int initialCount = 0;
            for (CSVRecord record : records) {
                initialCount++;
                TradeEntry entry = TradeEntry.fromCsvRecord(record);
                if (entry != null) {
                    allEntries.add(entry);
                }
            }
            System.out.println("-> Đọc hoàn tất. Xử lý được " + allEntries.size() + "/" + initialCount + " dòng hợp lệ.");

            if (allEntries.isEmpty()) {
                System.out.println("Không có dữ liệu hợp lệ để phân tích. Dừng chương trình.");
                records.close();
                in.close();
                return;
            }

            // 2. Phân tích theo ngày
            System.out.println("\n2. Phân tích số lượng giao dịch theo ngày...");
            Map<LocalDate, Long> tradesPerDay = allEntries.stream()
                    .collect(Collectors.groupingBy(trade -> trade.startTime.toLocalDate(), Collectors.counting()));

            List<LocalDate> highVolumeDays = tradesPerDay.entrySet().stream()
                    .filter(entry -> entry.getValue() > orderThreshold)
                    .map(Map.Entry::getKey)
                    .collect(Collectors.toList());

            System.out.println("-> Tìm thấy " + highVolumeDays.size() + " ngày có số lượng giao dịch vượt quá " + orderThreshold + ".");

            // 3. Phân tích theo giờ
            System.out.println("\n3. Phân tích số lượng giao dịch theo giờ...");
            Map<LocalDateTime, Long> tradesPerHour = allEntries.stream()
                    .collect(Collectors.groupingBy(trade -> LocalDateTime.of(trade.startTime.toLocalDate(), LocalTime.of(trade.startTime.getHour(), 0)), Collectors.counting()));

            List<LocalDateTime> highVolumeHours = tradesPerHour.entrySet().stream()
                    .filter(entry -> entry.getValue() > orderThreshold)
                    .map(Map.Entry::getKey)
                    .collect(Collectors.toList());

            System.out.println("-> Tìm thấy " + highVolumeHours.size() + " giờ có số lượng giao dịch vượt quá " + orderThreshold + ".");

            // 4. Phân tích theo 15 phút
            System.out.println("\n4. Phân tích số lượng giao dịch theo 15 phút...");
            Map<LocalDateTime, Long> tradesPer15Min = allEntries.stream()
                    .collect(Collectors.groupingBy(trade -> {
                        int minute = trade.startTime.getMinute();
                        int quarter = (minute / 15) * 15;
                        return LocalDateTime.of(trade.startTime.toLocalDate(), LocalTime.of(trade.startTime.getHour(), quarter));
                    }, Collectors.counting()));

            List<LocalDateTime> highVolume15MinIntervals = tradesPer15Min.entrySet().stream()
                    .filter(entry -> entry.getValue() > orderThreshold)
                    .map(Map.Entry::getKey)
                    .collect(Collectors.toList());

            System.out.println("-> Tìm thấy " + highVolume15MinIntervals.size() + " khoảng 15 phút có số lượng giao dịch vượt quá " + orderThreshold + ".");


            // 5. Lọc các TradeEntry liên quan đến các khoảng thời gian có khối lượng giao dịch cao
            System.out.println("\n5. Lọc dữ liệu chi tiết...");
            List<TradeEntry> highFrequencyTrades = allEntries.stream()
                    .filter(entry ->
                            highVolumeDays.contains(entry.startTime.toLocalDate()) ||
                                    highVolumeHours.contains(LocalDateTime.of(entry.startTime.toLocalDate(), LocalTime.of(entry.startTime.getHour(), 0))) ||
                                    highVolume15MinIntervals.contains(LocalDateTime.of(entry.startTime.toLocalDate(), LocalTime.of(entry.startTime.getHour(), (entry.startTime.getMinute()/15)*15))))
                    .collect(Collectors.toList());

            System.out.println("-> Tìm thấy " + highFrequencyTrades.size() + " giao dịch trong các khoảng thời gian có khối lượng cao.");

            // 6. Xuất dữ liệu ra file
            System.out.println("\n6. Đang ghi dữ liệu chi tiết ra file '" + outputFile + "'...");
            FileWriter out = new FileWriter(outputFile);
            try (CSVPrinter printer = new CSVPrinter(out, CSVFormat.DEFAULT.withHeader(records.getHeaderMap().keySet().toArray(new String[0])))) {
                for (TradeEntry entry : highFrequencyTrades) {
                    printer.printRecord(entry.originalRecord);
                }
            }
            System.out.println("\n--- THÀNH CÔNG! ---");
            System.out.println("Đã lưu toàn bộ " + highFrequencyTrades.size() + " dòng dữ liệu chi tiết vào file '" + outputFile + "'.");

            records.close();
            in.close();

        } catch (IOException e) {
            System.out.println("\nLỖI: Không thể đọc hoặc ghi file.");
            e.printStackTrace();
        } catch (Exception e) {
            System.out.println("\nLỖI: Đã xảy ra một lỗi không mong muốn.");
            e.printStackTrace();
        }
    }
}