package com.binance.chuyennd.ticker;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.KlineArchiveProto;
import com.binance.chuyennd.proto.KlineProto;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.StorageProto;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;

/**
 * Class này dùng để tiền xử lý (pre-process) dữ liệu ticker 1M với hiệu năng đã được tối ưu.
 * Nó đọc dữ liệu, tính toán trước các chỉ số bằng thuật toán cửa sổ trượt hiệu quả
 * và ghi ra file mới (.pb.snappy.full) để tăng tốc độ backtest.
 */
public class DataPreprocessor {

    public static final Logger LOG = LoggerFactory.getLogger(DataPreprocessor.class);

    // TODO: CHỈNH SỬA LẠI CÁC ĐƯỜNG DẪN NÀY CHO ĐÚNG
    private static final String SOURCE_DIR = "../storage/ticker/ticker1m-protobuf/";
    private static final String DEST_DIR = "../storage/ticker/ticker1m-protobuf-full/";
    private static final int HISTORY_LIMIT = 100; // Giới hạn lịch sử nến (90 phút + buffer)

    public static void main(String[] args) {
        LOG.info("Bắt đầu quá trình tiền xử lý dữ liệu (đã tối ưu)...");

        File sourceDir = new File(SOURCE_DIR);
        if (!sourceDir.exists() || !sourceDir.isDirectory()) {
            LOG.error("Thư mục nguồn không tồn tại: {}", sourceDir.getAbsolutePath());
            return;
        }

        File destDir = new File(DEST_DIR);
        if (!destDir.exists()) {
            destDir.mkdirs();
        }

        File[] filesToProcess = sourceDir.listFiles((dir, name) -> name.endsWith(".pb"));
        if (filesToProcess == null || filesToProcess.length == 0) {
            LOG.warn("Không tìm thấy file .pb.snappy nào trong thư mục nguồn.");
            return;
        }

        Arrays.sort(filesToProcess);
        LOG.info("Tìm thấy {} file để xử lý, bắt đầu từ {}...", filesToProcess.length, filesToProcess[0].getName());

        // Map này sẽ lưu giữ trạng thái xử lý cho mỗi symbol
        Map<String, SymbolProcessingState> processingStates = new HashMap<>();
        int successCount = 0;

        for (File sourceFile : filesToProcess) {
            String destFileName = sourceFile.getName().replace(".pb", ".pb.full");
            File destFile = new File(destDir, destFileName);

            if (destFile.exists()) {
                LOG.info("Bỏ qua, file đã được xử lý: {}", destFileName);
                // Vẫn cập nhật history để đảm bảo tính liên tục cho ngày tiếp theo
                updateHistoryFromFile(processingStates, sourceFile);
                continue;
            }

            try {
                LOG.info("Đang xử lý file: {}", sourceFile.getName());
                KlineArchiveProto.KlineArchive originalArchive = StorageProto.readProtoWithSnappy(sourceFile.getAbsolutePath());
                if (originalArchive == null) {
                    LOG.error("Không thể đọc file: {}", sourceFile.getName());
                    continue;
                }

                TreeMap<Long, Map<String, KlineObjectSimple>> dataByTime = convertProtoArchiveToOldStructure(originalArchive);
                KlineArchiveProto.KlineArchive processedArchive = processAndCalculateIndicators(dataByTime, processingStates);
                StorageProto.writeProtoWithSnappy(destFile.getAbsolutePath(), processedArchive);

                LOG.info("=> Xử lý và ghi thành công file: {}", destFileName);
                successCount++;

            } catch (Exception e) {
                LOG.error("Lỗi khi xử lý file: {}", sourceFile.getName(), e);
            }
        }
        LOG.info("Hoàn tất! Đã xử lý thành công {} file mới.", successCount);
    }

    /**
     * Lớp nội bộ để quản lý trạng thái xử lý của mỗi symbol.
     */
    private static class SymbolProcessingState {
        // Sử dụng Deque để thêm/xóa 2 đầu hiệu quả
        Deque<KlineObjectSimple> history = new ArrayDeque<>(HISTORY_LIMIT);
        double maxChange90m = 0.0;
    }


    private static KlineArchiveProto.KlineArchive processAndCalculateIndicators(
            TreeMap<Long, Map<String, KlineObjectSimple>> dataByTime,
            Map<String, SymbolProcessingState> processingStates) {

        // Map này chứa các builder cho file hiện tại, giúp tối ưu việc build
        Map<String, KlineArchiveProto.SymbolKlines.Builder> fileScopedSymbolBuilders = new HashMap<>();

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : dataByTime.entrySet()) {
            for (Map.Entry<String, KlineObjectSimple> symbolEntry : timeEntry.getValue().entrySet()) {
                String symbol = symbolEntry.getKey();
                KlineObjectSimple currentKline = symbolEntry.getValue();

                SymbolProcessingState state = processingStates.computeIfAbsent(symbol, k -> new SymbolProcessingState());

                // --- TÍNH TOÁN TỊNH TIẾN ---
                KlineObjectSimple oldestKline = null;
                double oldestKlineRate = 0.0;
                // Nếu cửa sổ đã đủ 90, lấy ra cây nến cũ nhất để xử lý
                if (state.history.size() >= 90) {
                    oldestKline = state.history.removeFirst();
                    oldestKlineRate = Utils.rateOf2Double(oldestKline.maxPrice, oldestKline.minPrice);
                }

                state.history.addLast(currentKline);


                // Giới hạn tổng thể lịch sử để không tràn bộ nhớ
                while (state.history.size() > HISTORY_LIMIT) {
                    state.history.removeFirst();
                }

                // Cập nhật maxChange90m một cách thông minh
                double currentKlineRate = Utils.rateOf2Double(currentKline.maxPrice, currentKline.minPrice);
                if (oldestKline != null && oldestKlineRate >= state.maxChange90m) {
                    // Nếu nến bị loại bỏ chính là max, phải quét lại
                    state.maxChange90m = calculateFullMaxChange(state.history);
                } else {
                    // Ngược lại, chỉ cần so sánh với nến mới
                    state.maxChange90m = Math.max(state.maxChange90m, currentKlineRate);
                }

                // --- TÍNH TOÁN CÁC CHỈ SỐ CÒN LẠI ---
                Indicators indicators = calculateRemainingIndicators(state.history, symbol);
                indicators.maxChange90M = (float) state.maxChange90m;

                KlineProto.KlineObjectSimpleProto processedKline = buildProcessedKline(currentKline, indicators);

                // --- TỐI ƯU VIỆC BUILD PROTOBUF ---
                KlineArchiveProto.SymbolKlines.Builder symbolBuilder = fileScopedSymbolBuilders
                        .computeIfAbsent(symbol, k -> KlineArchiveProto.SymbolKlines.newBuilder().setSymbol(k));
                symbolBuilder.putTimeToKline(currentKline.startTime.longValue(), processedKline);
            }
        }

        // Build Archive cuối cùng từ các builder đã có
        KlineArchiveProto.KlineArchive.Builder archiveBuilder = KlineArchiveProto.KlineArchive.newBuilder();
        for (KlineArchiveProto.SymbolKlines.Builder builder : fileScopedSymbolBuilders.values()) {
            archiveBuilder.putSymbolKlines(builder.getSymbol(), builder.build());
        }
        return archiveBuilder.build();
    }

    /**
     * Tính các chỉ số không thể tính tịnh tiến hoặc cần cửa sổ nhỏ hơn.
     */
    private static Indicators calculateRemainingIndicators(Deque<KlineObjectSimple> history, String symbol) {
        Indicators indicators = new Indicators();
        List<KlineObjectSimple> historyList = new ArrayList<>(history); // Chuyển sang List để dễ truy cập

        // Tính các chỉ số 15M
        int startIndex15M = Math.max(0, historyList.size() - 15);
        if (startIndex15M < historyList.size()) {
            float periodHigh = 0;
            float periodMin = Float.MAX_VALUE;
            float volume15M = 0;
            for (int i = startIndex15M; i < historyList.size(); i++) {
                KlineObjectSimple k = historyList.get(i);
                periodHigh = Math.max(periodHigh, k.maxPrice.floatValue());
                periodMin = Math.min(periodMin, k.minPrice.floatValue());
                volume15M += k.totalUsdt;
            }
            indicators.maxPrice15M = periodHigh;
            indicators.volume90M = volume15M;
            if (periodHigh > 0) {
                indicators.movementRange15M = (periodHigh - periodMin) / periodHigh;
            }
        }
        return indicators;
    }

    /**
     * Quét lại toàn bộ cửa sổ để tìm maxChange, chỉ được gọi khi cần thiết.
     */
    private static double calculateFullMaxChange(Deque<KlineObjectSimple> history) {
        double maxRate = 0.0;
        for (KlineObjectSimple kline : history) {
            maxRate = Math.max(maxRate, Utils.rateOf2Double(kline.maxPrice, kline.minPrice));
        }
        return maxRate;
    }

    private static KlineProto.KlineObjectSimpleProto buildProcessedKline(KlineObjectSimple currentKline, Indicators indicators) {
        return KlineProto.KlineObjectSimpleProto.newBuilder()
                .setStartTime(currentKline.startTime.longValue())
                .setPriceOpen(currentKline.priceOpen.floatValue())
                .setMaxPrice(currentKline.maxPrice.floatValue())
                .setMinPrice(currentKline.minPrice.floatValue())
                .setPriceClose(currentKline.priceClose.floatValue())
                .setTotalUsdt(currentKline.totalUsdt.floatValue())
                .build();
    }

    private static class Indicators {
        float movementRange15M = 0.0f;
        float maxPrice15M = 0.0f;
        float volume90M = 0.0f;
        float maxChange90M = 0.0f;

    }

    private static void updateHistoryFromFile(Map<String, SymbolProcessingState> processingStates, File sourceFile) {
        KlineArchiveProto.KlineArchive archive = StorageProto.readProtoWithSnappy(sourceFile.getAbsolutePath());
        if (archive == null) return;

        TreeMap<Long, Map<String, KlineObjectSimple>> dataByTime = convertProtoArchiveToOldStructure(archive);
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : dataByTime.entrySet()) {
            for (Map.Entry<String, KlineObjectSimple> symbolEntry : timeEntry.getValue().entrySet()) {
                String symbol = symbolEntry.getKey();
                KlineObjectSimple kline = symbolEntry.getValue();

                SymbolProcessingState state = processingStates.computeIfAbsent(symbol, k -> new SymbolProcessingState());

                // Chỉ cần cập nhật history, không cần tính toán lại volume/maxChange ở đây
                state.history.addLast(kline);
                while (state.history.size() > HISTORY_LIMIT) {
                    state.history.removeFirst();
                }
            }
        }
    }

    private static TreeMap<Long, Map<String, KlineObjectSimple>> convertProtoArchiveToOldStructure(KlineArchiveProto.KlineArchive archive) {
        TreeMap<Long, Map<String, KlineObjectSimple>> time2SymbolAndKline = new TreeMap<>();
        if (archive == null) return time2SymbolAndKline;

        for (Map.Entry<String, KlineArchiveProto.SymbolKlines> symbolEntry : archive.getSymbolKlinesMap().entrySet()) {
            String symbol = symbolEntry.getKey();
            for (Map.Entry<Long, KlineProto.KlineObjectSimpleProto> timeEntry : symbolEntry.getValue().getTimeToKlineMap().entrySet()) {
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

