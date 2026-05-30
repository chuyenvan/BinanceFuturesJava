package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.ai_ml.onnx.entry.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
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
            if (binFile.exists()) {
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new FileInputStream(binFile), 1024 * 1024))) {
                    return (T) ois.readObject();
                }
            } else if (gzFile.exists()) {
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(gzFile)), 1024 * 1024))) {
                    return (T) ois.readObject();
                }
            } else {
                LOG.error("❌ KHÔNG TÌM THẤY FILE: Neither {} nor {} exists!", binFile.getPath(), gzFile.getPath());
                return null;
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi trong quá trình đọc file: " + baseFileName, e);
            return null;
        }
    }

    public static TreeMap<Long, MarketDataObject15M> loadMarketData() {
        return loadObject("core_market_data");
    }

    public static TreeMap<Long, AiPredictionData> loadAiPred() {
        return loadObject("core_ai_pred");
    }

    public static TreeMap<Long, long[]> loadFundingPred() {
        return loadObject("core_funding_pred");
    }

    /**
     * Nạp trực tiếp dữ liệu Short 15M vào mảng O(1)
     */
    public static TreeMap<Long, Map<Short, KlineObjectSimple>> loadDailyTickersRaw(long dayTs) {
        String baseName = "ticker_15m_" + Utils.sdfFile.format(new java.util.Date(dayTs));
        // Đọc thẳng Object Map<Short, KlineObjectSimple> đã export
        TreeMap<Long, Map<Short, KlineObjectSimple>> rawData = loadObject(baseName);

        return rawData;
    }
    public static TreeMap<Long, KlineObjectSimple[]> loadDailyTickersShort(long dayTs) {
        String baseName = "ticker_15m_" + Utils.sdfFile.format(new java.util.Date(dayTs));

        // Đọc thẳng Object Map<Short, KlineObjectSimple> đã export
        TreeMap<Long, Map<Short, KlineObjectSimple>> rawData = loadObject(baseName);

        if (rawData == null || rawData.isEmpty()) return null;

        TreeMap<Long, KlineObjectSimple[]> optimizedData = new TreeMap<>();

        for (Map.Entry<Long, Map<Short, KlineObjectSimple>> timeEntry : rawData.entrySet()) {
            // Mảng 5000 phần tử tương ứng với 5000 Symbol ID
            KlineObjectSimple[] klineArray = new KlineObjectSimple[5000];

            for (Map.Entry<Short, KlineObjectSimple> symbolEntry : timeEntry.getValue().entrySet()) {
                klineArray[symbolEntry.getKey()] = symbolEntry.getValue();
            }
            optimizedData.put(timeEntry.getKey(), klineArray);
        }

        rawData.clear();
        return optimizedData;
    }
}