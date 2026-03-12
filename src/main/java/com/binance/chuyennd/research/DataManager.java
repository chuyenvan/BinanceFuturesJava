package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class DataManager {
    private static final Logger LOG = LoggerFactory.getLogger(DataManager.class);
    public static String DATA_DIR = "storage_data/";
    public static boolean isDumpingMode = false;

    // Bộ nhớ đệm Static - Duy nhất cho toàn bộ chương trình
    private static volatile TreeMap<Long, MarketDataObject> cachedMarketData = null;
    private static volatile TreeMap<Long, AiPredictionData> cachedAiPredictionData = null;
    private static volatile TreeMap<Long, long[]> cachedFundingPred = null;
//    private static final ConcurrentHashMap<Long, TreeMap<Long, Map<String, KlineObjectSimple>>>
//            cachedTickers1M = new ConcurrentHashMap<>();

    private static final Object lockMarket = new Object();
    private static final Object lockAi = new Object();
    private static final Object lockFunding = new Object();

    public static TreeMap<Long, MarketDataObject> getMarketData() {
        if (cachedMarketData == null) {
            synchronized (lockMarket) {
                if (cachedMarketData == null) {
                    LOG.info("📥 [RAM] Đang nạp Market Data độc quyền từ Aerospike...");
                    cachedMarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
                }
            }
        }
        return cachedMarketData;
    }

    public static TreeMap<Long, AiPredictionData> getAiPredictionData() {
        if (cachedAiPredictionData == null) {
            synchronized (lockAi) {
                if (cachedAiPredictionData == null) {
                    LOG.info("📥 [RAM] Đang nạp AI Predictions độc quyền từ Aerospike...");
                    cachedAiPredictionData = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
                }
            }
        }
        return cachedAiPredictionData;
    }

    // Hàm trả về Funding Pred (Dùng trong HPO và Simulator)
    public static TreeMap<Long, long[]> getFundingPredictionData(Long startTime, int numberMinutes) {
        if (cachedFundingPred == null) {
            synchronized (lockFunding) {
                if (cachedFundingPred == null) {
                    LOG.info("📥 [RAM] Đang nạp Funding Predictions độc quyền cho dải thời gian này...");
                    cachedFundingPred = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);
                }
            }
        }
        return cachedFundingPred;
    }

    public static TreeMap<Long, Map<String, KlineObjectSimple>> getTickers1M(Long startTime) {
//        if (!cachedTickers1M.containsKey(startTime)) {
//            synchronized (cachedTickers1M) {
//                if (!cachedTickers1M.containsKey(startTime)) {
//                    LOG.info("📥 [RAM] Đang nạp nến 1M ngày {}...", Utils.normalizeDateYYYYMMDD(startTime));
        TreeMap<Long, Map<String, KlineObjectSimple>> data = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
        return data;
//                    if (data != null) cachedTickers1M.put(startTime, data);
//                }
//            }
//        }
//        return cachedTickers1M.get(startTime);
    }

    // --- HÀM TIỆN ÍCH ĐỂ ĐỌC/GHI FILE ---
    private static <T> T readObjectFromFile(String filePath) {
        File file = new File(filePath);
        if (!file.exists()) return null;
        try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new FileInputStream(file)))) {
            return (T) ois.readObject();
        } catch (Exception e) {
            return null;
        }
    }

    private static void writeObjectToFile(String filePath, Object obj) {
        if (DATA_DIR.startsWith("/kaggle/input")) return;
        try (ObjectOutputStream oos = new ObjectOutputStream(new BufferedOutputStream(new FileOutputStream(filePath)))) {
            oos.writeObject(obj);
            LOG.info("💾 Đã dump dữ liệu ra file: {}", filePath);
        } catch (Exception e) {
            LOG.error("❌ Lỗi ghi file: {}", filePath);
        }
    }
}