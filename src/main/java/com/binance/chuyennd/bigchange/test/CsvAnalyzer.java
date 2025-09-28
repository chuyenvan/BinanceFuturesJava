package com.binance.chuyennd.bigchange.test;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.csv.CSVRecord;

import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.Reader;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class CsvAnalyzer {

    // Lớp nội tại để lưu trữ dữ liệu mỗi dòng
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
                    DateTimeFormatter.ofPattern("yyyyMMdd HH:mm")
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
        String outputFile = "target/long_duration_trades_details.csv";
        long durationThresholdDays = 30;

        System.out.println("--- BẮT ĐẦU CHƯƠNG TRÌNH PHÂN TÍCH (JAVA 11 COMPATIBLE) ---");
        try {
            // 1. Đọc và xử lý file CSV
            System.out.println("1. Đang đọc và xử lý file '" + inputFile + "'...");
            List<TradeEntry> allEntries = new ArrayList<>();
            Reader in = new FileReader(inputFile);
            // Sử dụng cú pháp cũ hơn của CSVFormat để tương thích Java 11
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

            // 2. Sắp xếp và xác định chuỗi lệnh
            System.out.println("\n2. Đang xác định các chuỗi lệnh DCA...");
            allEntries.sort(Comparator.comparing((TradeEntry e) -> e.symbol).thenComparing(e -> e.startTime));

            Map<String, Integer> sequenceCounter = new HashMap<>();
            for (TradeEntry entry : allEntries) {
                boolean isDca = entry.level != null && entry.level.contains("DCA");
                if (!isDca) {
                    int nextId = sequenceCounter.getOrDefault(entry.symbol, 0) + 1;
                    sequenceCounter.put(entry.symbol, nextId);
                }
                entry.sequenceId = entry.symbol + "_" + sequenceCounter.getOrDefault(entry.symbol, 1);
            }
            long totalSequences = allEntries.stream().map(e -> e.sequenceId).distinct().count();
            System.out.println("-> Đã xác định được " + totalSequences + " chuỗi lệnh.");

            // 3. Tính toán và lọc các chuỗi lệnh dài ngày
            System.out.println("\n3. Đang lọc các chuỗi lệnh có thời gian > " + durationThresholdDays + " ngày...");
            Map<String, List<TradeEntry>> sequencesById = allEntries.stream().collect(Collectors.groupingBy(e -> e.sequenceId));
            List<String> longSequenceIds = new ArrayList<>();

            for (Map.Entry<String, List<TradeEntry>> seqEntry : sequencesById.entrySet()) {
                List<TradeEntry> sequence = seqEntry.getValue();
                LocalDateTime startTime = sequence.stream().min(Comparator.comparing(e -> e.startTime)).get().startTime;
                LocalDateTime endTime = sequence.stream().max(Comparator.comparing(e -> e.endTime)).get().endTime;
                long durationDays = ChronoUnit.DAYS.between(startTime, endTime);

                if (durationDays > durationThresholdDays) {
                    longSequenceIds.add(seqEntry.getKey());
                }
            }

            if (longSequenceIds.isEmpty()) {
                System.out.println("\n==> KẾT QUẢ: Không tìm thấy chuỗi lệnh nào thỏa mãn điều kiện (> " + durationThresholdDays + " ngày).");
                records.close();
                in.close();
                return;
            }
            System.out.println("-> Tìm thấy " + longSequenceIds.size() + " chuỗi lệnh dài hơn " + durationThresholdDays + " ngày.");

            // 4. Xuất dữ liệu ra file
            System.out.println("\n4. Đang ghi dữ liệu chi tiết ra file '" + outputFile + "'...");
            List<TradeEntry> longTradeDetails = new ArrayList<>();
            for(TradeEntry entry : allEntries){
                if(longSequenceIds.contains(entry.sequenceId)){
                    longTradeDetails.add(entry);
                }
            }

            FileWriter out = new FileWriter(outputFile);
            try (CSVPrinter printer = new CSVPrinter(out, CSVFormat.DEFAULT.withHeader(records.getHeaderMap().keySet().toArray(new String[0])))) {
                for (TradeEntry entry : longTradeDetails) {
                    printer.printRecord(entry.originalRecord);
                }
            }
            System.out.println("\n--- THÀNH CÔNG! ---");
            System.out.println("Đã lưu toàn bộ " + longTradeDetails.size() + " dòng dữ liệu chi tiết vào file '" + outputFile + "'.");

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