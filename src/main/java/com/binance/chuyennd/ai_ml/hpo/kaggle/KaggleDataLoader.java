package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;

public class KaggleDataLoader {
    private static final Logger LOG = LoggerFactory.getLogger(KaggleDataLoader.class);
    private static final String IMPORT_DIR = "kaggle_data_hpo/";

    @SuppressWarnings("unchecked")
    private static <T> T loadObject(String baseFileName) {
        File binFile = new File(IMPORT_DIR + baseFileName + ".bin");
        File gzFile = new File(IMPORT_DIR + baseFileName + ".bin.gz");

        try {
            // 1. ƯU TIÊN 1: Tìm file .bin đã được giải nén (Kaggle Auto-unzip)
            if (binFile.exists()) {
                // LOG.debug("📂 Loading uncompressed file: {}", binFile.getPath());
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new FileInputStream(binFile), 1024 * 1024))) {
                    return (T) ois.readObject();
                }
            }
            // 2. ƯU TIÊN 2: Tìm file .bin.gz gốc (Chạy Local hoặc Kaggle giữ nguyên file)
            else if (gzFile.exists()) {
                // LOG.debug("🗜️ Loading compressed file: {}", gzFile.getPath());
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(gzFile)), 1024 * 1024))) {
                    return (T) ois.readObject();
                }
            }
            // 3. Không tìm thấy cả 2
            else {
                LOG.error("❌ KHÔNG TÌM THẤY FILE: Neither {} nor {} exists!", binFile.getPath(), gzFile.getPath());
                return null;
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi trong quá trình đọc file: " + baseFileName, e);
            return null;
        }
    }

    public static TreeMap<Long, MarketDataObject> loadMarketData() {
        // Chỉ truyền tên file gốc, Loader sẽ tự lo đuôi .bin hoặc .bin.gz
        return loadObject("core_market_data");
    }

    public static TreeMap<Long, AiPredictionData> loadAiPred() {
        return loadObject("core_ai_pred");
    }

    public static TreeMap<Long, long[]> loadFundingPred() {
        return loadObject("core_funding_pred");
    }

    /**
     * Hàm tải dữ liệu Ticker từ File (String) và Convert nóng sang Short trong RAM.
     * Giải pháp này giúp không phải Export lại cục data Kaggle khổng lồ.
     */
    public static TreeMap<Long, KlineObjectSimple[]> loadDailyTickersShort(long dayTs) {
        String baseName = "ticker_" + Utils.sdfFile.format(new java.util.Date(dayTs));
        TreeMap<Long, Map<String, KlineObjectSimple>> rawData = loadObject(baseName);

        if (rawData == null || rawData.isEmpty()) return null;

        TreeMap<Long, KlineObjectSimple[]> optimizedData = new TreeMap<>();

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : rawData.entrySet()) {
            // Khởi tạo mảng 5000 phần tử (tốn cực ít RAM vì chỉ chứa reference)
            KlineObjectSimple[] klineArray = new KlineObjectSimple[1000];

            for (Map.Entry<String, KlineObjectSimple> symbolEntry : timeEntry.getValue().entrySet()) {
                String fullSymbol = symbolEntry.getKey().endsWith("USDT") ? symbolEntry.getKey() : symbolEntry.getKey() + "USDT";
                short symbolId = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getId(fullSymbol);

                // Nạp thẳng vào Index của mảng
                klineArray[symbolId] = symbolEntry.getValue();
            }
            optimizedData.put(timeEntry.getKey(), klineArray);
        }
        rawData.clear();
        return optimizedData;
    }
}