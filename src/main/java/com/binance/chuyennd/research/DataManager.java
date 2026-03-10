package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.text.ParseException;
import java.util.Map;
import java.util.TreeMap;

public class DataManager {

    private static final Logger LOG = LoggerFactory.getLogger(DataManager.class);

    // Lấy đường dẫn linh hoạt: Nếu có cấu hình từ bên ngoài thì dùng, không thì mặc định là storage_data/
    public static String DATA_DIR = System.getProperty("data.dir", "storage_data/");

    public static boolean isDumpingMode = false;

    static {
        // Đảm bảo DATA_DIR luôn có dấu '/' ở cuối
        if (!DATA_DIR.endsWith("/")) {
            DATA_DIR += "/";
        }
        File dir = new File(DATA_DIR);
        if (!dir.exists() && !DATA_DIR.startsWith("/kaggle")) {
            dir.mkdirs();
        }
    }

    // TÌM ĐÚNG FILE .dat NHƯ TRÊN KAGGLE CỦA BẠN
    public static TreeMap<Long, MarketDataObject> getMarketData() {
        String filePath = DATA_DIR + "market_data.dat";
        TreeMap<Long, MarketDataObject> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file: {}. Đang tải từ Aerospike...", filePath);
            data = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
            if (isDumpingMode && data != null && !data.isEmpty()) writeObjectToFile(filePath, data);
        } else {
            LOG.info("✅ Đã load Market Data từ file offline.");
        }
        return data;
    }

    public static TreeMap<Long, AiPredictionData> getAiPredictionData() {
        String filePath = DATA_DIR + "ai_prediction_data.dat";
        TreeMap<Long, AiPredictionData> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file: {}. Đang tải từ Aerospike...", filePath);
            data = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
            if (isDumpingMode && data != null && !data.isEmpty()) writeObjectToFile(filePath, data);
        } else {
            LOG.info("✅ Đã load AI Prediction từ file offline.");
        }
        return data;
    }

    public static TreeMap<Long, long[]> getFundingPredictionData(Long startTime, int numberMinutes) {
        String filePath = DATA_DIR + "funding_prediction_" + startTime + ".dat";
        TreeMap<Long, long[]> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file: {}. Đang tải từ Aerospike...", filePath);
            data = DataManagerAerospikeFloatSim.getFundingPredictionsPrimitiveByRange(startTime, numberMinutes);
            if (isDumpingMode && data != null && !data.isEmpty()) writeObjectToFile(filePath, data);
        } else {
            LOG.info("✅ Đã load Funding Prediction từ file offline.");
        }
        return data;
    }

    public static TreeMap<Long, Map<String, KlineObjectSimple>> getTickers1M(Long startTime) {
        String filePath = DATA_DIR + "tickers_1m_" + startTime + ".dat";
        TreeMap<Long, Map<String, KlineObjectSimple>> data = readObjectFromFile(filePath);

        if (data == null || data.isEmpty()) {
            LOG.info("Không tìm thấy file: {}. Đang tải từ Aerospike...", filePath);
            data = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
            if (isDumpingMode && data != null && !data.isEmpty()) {
                writeObjectToFile(filePath, data);
            }
        }
        return data;
    }

    // ĐỌC FILE DẠNG CƠ BẢN (KHÔNG GZIP)
    private static <T> T readObjectFromFile(String filePath) {
        File file = new File(filePath);
        if (!file.exists()) return null;
        try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new FileInputStream(file)))) {
            return (T) ois.readObject();
        } catch (Exception e) {
            LOG.error("Lỗi khi đọc file: " + filePath, e);
            return null;
        }
    }

    private static void writeObjectToFile(String filePath, Object obj) {
        if (DATA_DIR.startsWith("/kaggle/input")) return;
        try (ObjectOutputStream oos = new ObjectOutputStream(new BufferedOutputStream(new FileOutputStream(filePath)))) {
            oos.writeObject(obj);
            LOG.info("Đã lưu file offline thành công: " + filePath);
        } catch (Exception e) {
            LOG.error("Lỗi khi ghi file: " + filePath, e);
        }
    }
}