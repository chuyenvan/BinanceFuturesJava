package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.text.ParseException;
import java.util.Map;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;  // 🔥 THÊM IMPORT
import java.util.zip.GZIPOutputStream; // 🔥 THÊM IMPORT

public class DataManager {

    private static final Logger LOG = LoggerFactory.getLogger(DataManager.class);

    // TRÊN VPS: Để "storage_data/"
    // TRÊN KAGGLE: Đổi thành "/kaggle/input/ten-dataset-cua-ban/storage_data/" (ĐỌC TRỰC TIẾP TỪ ĐÂY)
    public static String DATA_DIR = "storage_data/";

    public static boolean isDumpingMode = false;

    static {
        File dir = new File(DATA_DIR);
        if (!dir.exists() && !DATA_DIR.startsWith("/kaggle")) {
            dir.mkdirs();
        }
    }

    // 1. Quản lý Market Data (Đổi đuôi thành .dat.gz)
    public static TreeMap<Long, MarketDataObject> getMarketData() {
        String filePath = DATA_DIR + "market_data.dat.gz";
        TreeMap<Long, MarketDataObject> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file Market Data. Đang tải từ Aerospike...");
            data = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
            if (isDumpingMode && data != null && !data.isEmpty()) writeObjectToFile(filePath, data);
        } else {
            LOG.info("✅ Đã load Market Data từ file offline.");
        }
        return data;
    }

    // 2. Quản lý AI Prediction Data
    public static TreeMap<Long, AiPredictionData> getAiPredictionData() {
        String filePath = DATA_DIR + "ai_prediction_data.dat.gz";
        TreeMap<Long, AiPredictionData> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file AI Prediction. Đang tải từ Aerospike...");
            data = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
            if (isDumpingMode && data != null && !data.isEmpty()) writeObjectToFile(filePath, data);
        } else {
            LOG.info("✅ Đã load AI Prediction từ file offline.");
        }
        return data;
    }

    // 3. Quản lý Funding Prediction Data
    public static TreeMap<Long, long[]> getFundingPredictionData(Long startTime, int numberMinutes) {
        String filePath = DATA_DIR + "funding_prediction_" + startTime + ".dat.gz";
        TreeMap<Long, long[]> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file Funding Prediction. Đang tải từ Aerospike...");
            data = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);
            if (isDumpingMode && data != null && !data.isEmpty()) writeObjectToFile(filePath, data);
        } else {
            LOG.info("✅ Đã load Funding Prediction từ file offline.");
        }
        return data;
    }

    // 4. Quản lý Tickers 1M
    public static TreeMap<Long, Map<String, KlineObjectSimple>> getTickers1M(Long startTime) {
        String filePath = DATA_DIR + "tickers_1m_" + startTime + ".dat.gz";
        TreeMap<Long, Map<String, KlineObjectSimple>> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file Tickers cho time: {}. Đang tải từ Aerospike...", startTime);
            data = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
            if (isDumpingMode && data != null && !data.isEmpty()) {
                writeObjectToFile(filePath, data);
            }
        }
        return data;
    }

    // ================= Hàm tiện ích Đọc/Ghi File Nhị phân NÉN GZIP =================
    private static <T> T readObjectFromFile(String filePath) {
        File file = new File(filePath);
        if (!file.exists()) return null;
        // 🔥 BỌC THÊM GZIPInputStream
        try (ObjectInputStream ois = new ObjectInputStream(new GZIPInputStream(new BufferedInputStream(new FileInputStream(file))))) {
            return (T) ois.readObject();
        } catch (Exception e) {
            LOG.error("Lỗi khi đọc file (có thể file bị hỏng): " + filePath, e);
            return null;
        }
    }

    private static void writeObjectToFile(String filePath, Object obj) {
        if (DATA_DIR.startsWith("/kaggle/input")) return;

        // 🔥 BỌC THÊM GZIPOutputStream
        try (ObjectOutputStream oos = new ObjectOutputStream(new GZIPOutputStream(new BufferedOutputStream(new FileOutputStream(filePath))))) {
            oos.writeObject(obj);
            LOG.info("Đã lưu và nén file offline thành công: " + filePath);
        } catch (Exception e) {
            LOG.error("Lỗi khi ghi file: " + filePath, e);
        }
    }

    public static void dumpAllDataForKaggle(Long startTimeStr, int totalDays) {
        LOG.info("🔥 BẮT ĐẦU DUMP VÀ NÉN DATA RA FILE...");
        isDumpingMode = true;

        getMarketData();
        getAiPredictionData();
        getFundingPredictionData(startTimeStr, totalDays * 24 * 60);

        long current = startTimeStr;
        for (int i = 0; i < totalDays; i++) {
            getTickers1M(current);
            current += 86400000L;
        }

        isDumpingMode = false;
        LOG.info("✅ HOÀN TẤT DUMP DATA!");
    }

    public static void main(String[] args) throws ParseException {
        Long startTime = Utils.sdfFile.parse("20250101").getTime() + 7 * Utils.TIME_HOUR;
        int numberDays = System.currentTimeMillis() - startTime > 0 ? (int) ((System.currentTimeMillis() - startTime) / Utils.TIME_DAY) : 0;
        dumpAllDataForKaggle(startTime, numberDays);
    }
}