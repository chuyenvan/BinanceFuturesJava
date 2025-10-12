/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.ticker;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.KlineArchiveProto;
import com.binance.chuyennd.proto.KlineProto;
import com.binance.chuyennd.utils.StorageProto;
import com.binance.chuyennd.utils.StorageSnappy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

/**
 * Class này dùng để so sánh tốc độ đọc dữ liệu giữa 2 định dạng:
 * 1. Định dạng cũ: Java Serializable + Snappy Compression.
 * 2. Định dạng mới: Protocol Buffers (Protobuf) + Snappy + Chuyển đổi cấu trúc.
 */
public class BenchmarkReadSpeed {

    public static final Logger LOG = LoggerFactory.getLogger(BenchmarkReadSpeed.class);

    // TODO: CHỈNH SỬA LẠI CÁC ĐƯỜNG DẪN NÀY CHO ĐÚNG VỚI CẤU TRÚC PROJECT CỦA BẠN
    private static final String SNAPPY_DIR = "../storage/ticker/ticker1m-snappy/";
    private static final String PROTOBUF_SNAPPY_DIR = "../storage/ticker/ticker1m-protobuf/";

    // --- Cấu hình Benchmark ---
    private static final int NUMBER_OF_FILES_TO_TEST = 10; // Số lượng file để test
    private static final int WARMUP_RUNS = 3;             // Số lần chạy "nháp" để JVM tối ưu (JIT Compilation)
    private static final int BENCHMARK_RUNS = 5;          // Số lần chạy thật để lấy kết quả trung bình

    public static void main(String[] args) throws IOException {
        LOG.info("Chuẩn bị benchmark tốc độ đọc file...");

        // Lấy danh sách file từ thư mục Snappy cũ
        List<File> snappyFiles = getFilesFromDir(SNAPPY_DIR, NUMBER_OF_FILES_TO_TEST);
        if (snappyFiles.isEmpty()) {
            LOG.error("Không tìm thấy file nào trong thư mục Snappy nguồn: {}", new File(SNAPPY_DIR).getAbsolutePath());
            return;
        }

        // Tìm các file Protobuf tương ứng
        List<File> protoFiles = snappyFiles.stream()
                .map(snappyFile -> new File(PROTOBUF_SNAPPY_DIR, snappyFile.getName() + ".pb"))
                .filter(File::exists)
                .collect(Collectors.toList());

        if (snappyFiles.size() != protoFiles.size()) {
            LOG.error("Số lượng file không khớp! Tìm thấy {} file Snappy nhưng chỉ có {} file Protobuf tương ứng.",
                    snappyFiles.size(), protoFiles.size());
            return;
        }

        LOG.info("Sẽ test trên {} cặp file.", snappyFiles.size());

        // --- Giai đoạn Warm-up ---
        LOG.info("Bắt đầu giai đoạn Warm-up ({} lần) để ổn định JVM...", WARMUP_RUNS);
        for (int i = 0; i < WARMUP_RUNS; i++) {
            runSnappyReadTest(snappyFiles, false);
            runProtobufReadTest(protoFiles, false);
        }

        // --- Giai đoạn Benchmark ---
        LOG.info("Bắt đầu benchmark ({} lần chạy thật để lấy trung bình)...", BENCHMARK_RUNS);

        long totalSnappyTime = 0;
        for (int i = 0; i < BENCHMARK_RUNS; i++) {
            totalSnappyTime += runSnappyReadTest(snappyFiles, true);
        }
        long averageSnappyTime = totalSnappyTime / BENCHMARK_RUNS;

        long totalProtoTime = 0;
        for (int i = 0; i < BENCHMARK_RUNS; i++) {
            totalProtoTime += runProtobufReadTest(protoFiles, true);
        }
        long averageProtoTime = totalProtoTime / BENCHMARK_RUNS;

        // --- In kết quả ---
        LOG.info("\n====================== KẾT QUẢ BENCHMARK ======================");
        LOG.info("Định dạng cũ (Snappy + Serializable): {} ms (trung bình)", averageSnappyTime);
        LOG.info("Định dạng mới (Protobuf + Snappy + Convert): {} ms (trung bình)", averageProtoTime);
        LOG.info("---------------------------------------------------------------");
        if (averageProtoTime > 0) {
            double factor = (double) averageSnappyTime / averageProtoTime;
            LOG.info("=> Protobuf nhanh hơn khoảng {} lần.", String.format("%.2f", factor));
        }
        LOG.info("===============================================================");
    }

    private static long runSnappyReadTest(List<File> files, boolean logTime) {
        long startTime = System.nanoTime();
        int objectCount = 0;
        for (File file : files) {
            Object data = StorageSnappy.readObjectFromFile(file.getAbsolutePath());
            if (data != null) {
                objectCount++;
            }
        }
        long endTime = System.nanoTime();
        long durationMs = TimeUnit.NANOSECONDS.toMillis(endTime - startTime);
        if (logTime) {
            LOG.info("[Snappy]   Đọc {}/{} files mất: {} ms", objectCount, files.size(), durationMs);
        }
        return durationMs;
    }

    private static long runProtobufReadTest(List<File> files, boolean logTime) throws IOException {
        long startTime = System.nanoTime();
        int objectCount = 0;
        for (File file : files) {
            KlineArchiveProto.KlineArchive archive = StorageProto.readProtoWithSnappy(file.getAbsolutePath());
            if (archive != null) {
                // THÊM BƯỚC CHUYỂN ĐỔI VÀO BÀI TEST
                TreeMap<Long, Map<String, KlineObjectSimple>> convertedData = convertProtoArchiveToOldStructure(archive);
                if (convertedData != null) {
                    objectCount++;
                }
            }
        }
        long endTime = System.nanoTime();
        long durationMs = TimeUnit.NANOSECONDS.toMillis(endTime - startTime);
        if (logTime) {
            LOG.info("[Protobuf] Đọc + Convert {}/{} files mất: {} ms", objectCount, files.size(), durationMs);
        }
        return durationMs;
    }

    private static List<File> getFilesFromDir(String dirPath, int limit) {
        File dir = new File(dirPath);
        if (!dir.exists() || !dir.isDirectory()) {
            return new ArrayList<>();
        }
        // Lọc ra các file, không lấy thư mục
        File[] files = dir.listFiles(File::isFile);
        if (files == null) {
            return new ArrayList<>();
        }
        // Sắp xếp theo tên để đảm bảo thứ tự nhất quán
        Arrays.sort(files);

        List<File> result = new ArrayList<>();
        for (int i = 0; i < Math.min(files.length, limit); i++) {
            result.add(files[i]);
        }
        return result;
    }

    private static TreeMap<Long, Map<String, KlineObjectSimple>> convertProtoArchiveToOldStructure(KlineArchiveProto.KlineArchive archive) {
        TreeMap<Long, Map<String, KlineObjectSimple>> time2SymbolAndKline = new TreeMap<>();
        if (archive == null) {
            return null;
        }

        Map<String, KlineArchiveProto.SymbolKlines> symbolKlinesMap = archive.getSymbolKlinesMap();

        for (Map.Entry<String, KlineArchiveProto.SymbolKlines> symbolEntry : symbolKlinesMap.entrySet()) {
            String symbol = symbolEntry.getKey();
            Map<Long, KlineProto.KlineObjectSimpleProto> timeToKlineProtoMap = symbolEntry.getValue().getTimeToKlineMap();

            for (Map.Entry<Long, KlineProto.KlineObjectSimpleProto> timeEntry : timeToKlineProtoMap.entrySet()) {
                Long time = timeEntry.getKey();
                KlineObjectSimple simpleKline = convertKlineProtoToSimple(timeEntry.getValue());
                time2SymbolAndKline.computeIfAbsent(time, k -> new HashMap<>()).put(symbol, simpleKline);
            }
        }
        return time2SymbolAndKline;
    }

    private static KlineObjectSimple convertKlineProtoToSimple(KlineProto.KlineObjectSimpleProto protoKline) {
        KlineObjectSimple simpleKline = new KlineObjectSimple();
        simpleKline.startTime = (double) protoKline.getStartTime();
        simpleKline.priceOpen = (double) protoKline.getPriceOpen();
        simpleKline.maxPrice = (double) protoKline.getMaxPrice();
        simpleKline.minPrice = (double) protoKline.getMinPrice();
        simpleKline.priceClose = (double) protoKline.getPriceClose();
        simpleKline.totalUsdt = (double) protoKline.getTotalUsdt();
        return simpleKline;
    }
}
