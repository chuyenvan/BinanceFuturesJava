package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.Date;
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

    public static TreeMap<Long, Map<String, KlineObjectSimple>> loadDailyTickers(long dayTs) {
        String baseName = "ticker_" + Utils.sdfFile.format(new Date(dayTs));
        return loadObject(baseName);
    }
}