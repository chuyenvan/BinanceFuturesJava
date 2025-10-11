package com.binance.chuyennd.ticker;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.KlineArchiveProto;
import com.binance.chuyennd.proto.KlineProto;
import com.binance.chuyennd.utils.StorageProto;
import com.binance.chuyennd.utils.StorageSnappy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.TreeMap;

public class DataConverter {
    public static final Logger LOG = LoggerFactory.getLogger(DataConverter.class);

    // TODO: CHỈNH SỬA LẠI ĐƯỜNG DẪN CHO ĐÚNG VỚI CẤU TRÚC CỦA BẠN
    // Thư mục chứa các file snappy cũ
    private static final String SOURCE_DIRECTORY = "../storage/ticker/ticker1m-snappy/";
    // Thư mục để lưu các file protobuf mới
    private static final String DESTINATION_DIRECTORY = "../storage/ticker/ticker1m-protobuf/";

    public static void main(String[] args) {
        LOG.info("Bắt đầu quá trình chuyển đổi dữ liệu từ Snappy sang Protobuf...");

        File sourceDir = new File(SOURCE_DIRECTORY);
        File destDir = new File(DESTINATION_DIRECTORY);

        if (!sourceDir.exists() || !sourceDir.isDirectory()) {
            LOG.error("Thư mục nguồn không tồn tại: {}", sourceDir.getAbsolutePath());
            return;
        }

        if (!destDir.exists()) {
            destDir.mkdirs();
            LOG.info("Đã tạo thư mục đích: {}", destDir.getAbsolutePath());
        }

        File[] filesToConvert = sourceDir.listFiles();
        if (filesToConvert == null || filesToConvert.length == 0) {
            LOG.warn("Không có file nào trong thư mục nguồn để chuyển đổi.");
            return;
        }

        int successCount = 0;
        int skippedCount = 0;
        for (File oldFile : filesToConvert) {
            if (oldFile.isFile()) {
                try {
                    // TẠO ĐƯỜNG DẪN FILE ĐÍCH
                    String newFileName = oldFile.getName() + ".pb";
                    Path newFilePath = Paths.get(DESTINATION_DIRECTORY, newFileName);

                    // KIỂM TRA XEM FILE ĐÍCH ĐÃ TỒN TẠI CHƯA
                    if (Files.exists(newFilePath)) {
                        skippedCount++;
                        continue; // Bỏ qua và chuyển sang file tiếp theo
                    }

                    // Đọc file snappy cũ
                    Object data = StorageSnappy.readObjectFromFile(oldFile.getAbsolutePath());
                    if (data instanceof TreeMap) {
                        @SuppressWarnings("unchecked")
                        TreeMap<Long, Map<String, KlineObjectSimple>> oldDataStructure = (TreeMap<Long, Map<String, KlineObjectSimple>>) data;

                        // Chuyển đổi sang cấu trúc Protobuf
                        KlineArchiveProto.KlineArchive protoArchive = convertToProto(oldDataStructure);

                        // Ghi ra file protobuf mới
//                        try (FileOutputStream fos = new FileOutputStream(newFilePath.toFile())) {
//                            protoArchive.writeTo(fos);
//                        }
                        StorageProto.writeProtoWithSnappy(newFilePath.toFile().getAbsolutePath(), protoArchive);
                        LOG.info("=> Chuyển đổi thành công file {} -> {}", oldFile.getName(), newFileName);
                        successCount++;
                    }
                } catch (Exception e) {
                    LOG.error("Lỗi khi chuyển đổi file: {}", oldFile.getName(), e);
                }
            }
        }
        LOG.info("Hoàn tất! Đã chuyển đổi: {} file. Bỏ qua: {} file đã tồn tại.", successCount, skippedCount);
    }

    /**
     * Hàm này chuyển đổi cấu trúc dữ liệu TreeMap cũ sang cấu trúc Protobuf Archive mới.
     */
    private static KlineArchiveProto.KlineArchive convertToProto(TreeMap<Long, Map<String, KlineObjectSimple>> oldData) {
        // Cần đảo ngược cấu trúc map để nhóm theo symbol trước
        Map<String, TreeMap<Long, KlineObjectSimple>> dataBySymbol = new TreeMap<>();
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : oldData.entrySet()) {
            Long time = entry.getKey();
            Map<String, KlineObjectSimple> symbolMap = entry.getValue();
            for (Map.Entry<String, KlineObjectSimple> symbolEntry : symbolMap.entrySet()) {
                String symbol = symbolEntry.getKey();
                KlineObjectSimple kline = symbolEntry.getValue();
                dataBySymbol.computeIfAbsent(symbol, k -> new TreeMap<>()).put(time, kline);
            }
        }

        KlineArchiveProto.KlineArchive.Builder archiveBuilder = KlineArchiveProto.KlineArchive.newBuilder();

        for (Map.Entry<String, TreeMap<Long, KlineObjectSimple>> symbolEntry : dataBySymbol.entrySet()) {
            String symbol = symbolEntry.getKey();
            TreeMap<Long, KlineObjectSimple> klines = symbolEntry.getValue();

            KlineArchiveProto.SymbolKlines.Builder symbolKlinesBuilder = KlineArchiveProto.SymbolKlines.newBuilder();
            symbolKlinesBuilder.setSymbol(symbol);

            for(Map.Entry<Long, KlineObjectSimple> klineEntry : klines.entrySet()){
                KlineProto.KlineObjectSimpleProto protoKline = convertKline(klineEntry.getValue());
                symbolKlinesBuilder.putTimeToKline(klineEntry.getKey(), protoKline);
            }
            archiveBuilder.putSymbolKlines(symbol, symbolKlinesBuilder.build());
        }

        return archiveBuilder.build();
    }

    /**
     * Hàm tiện ích để chuyển đổi một object KlineObjectSimple sang KlineObjectSimpleProto.
     */
    private static KlineProto.KlineObjectSimpleProto convertKline(KlineObjectSimple oldKline) {
        KlineProto.KlineObjectSimpleProto.Builder builder = KlineProto.KlineObjectSimpleProto.newBuilder();

        if (oldKline.startTime != null) builder.setStartTime(oldKline.startTime.longValue());
        if (oldKline.priceOpen != null) builder.setPriceOpen(oldKline.priceOpen.floatValue());
        if (oldKline.maxPrice != null) builder.setMaxPrice(oldKline.maxPrice.floatValue());
        if (oldKline.minPrice != null) builder.setMinPrice(oldKline.minPrice.floatValue());
        if (oldKline.priceClose != null) builder.setPriceClose(oldKline.priceClose.floatValue());
        if (oldKline.totalUsdt != null) builder.setTotalUsdt(oldKline.totalUsdt.floatValue());

        return builder.build();
    }
}