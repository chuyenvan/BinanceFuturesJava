package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleSymbolMapper {

    private static final Logger LOG = LoggerFactory.getLogger(SimpleSymbolMapper.class);

    // Map lưu trữ: Symbol (String) <-> ID (Short)
    private final Map<String, Short> strToId = new ConcurrentHashMap<>();
    private final Map<Short, String> idToStr = new ConcurrentHashMap<>();

    // Bộ đếm ID
    private short counter = 0;

    // Cờ đánh dấu đã load dữ liệu hay chưa
    private boolean isInitialized = false;

    // --- SINGLETON PATTERN ---

    // Private Constructor để ngăn tạo instance từ bên ngoài
    private SimpleSymbolMapper() {
        // Có thể gọi init() ngay tại đây nếu muốn tự động load khi gọi getInstance()
        // init();
    }

    public Map<Float, String> extractSymbol(TreeMap<Float, Short> rate2Max) {
        Map<Float, String> rate2Symbol = new TreeMap<>();
        for (Map.Entry<Float, Short> entry : rate2Max.entrySet()) {
            String symbol = getSymbol(entry.getValue());
            rate2Symbol.put(entry.getKey(), symbol);
        }
        return rate2Symbol;
    }

    public TreeMap<Float, Short> convertSymbolList(TreeMap<Float, String> rateMax2Symbols) {
        TreeMap<Float, Short> rate2Id = new TreeMap<>();
        for (Map.Entry<Float, String> entry : rateMax2Symbols.entrySet()) {
            short id = getId(entry.getValue());
            rate2Id.put(entry.getKey(), id);
        }
        return rate2Id;
    }

    // Static Inner Class - Holder chứa Instance duy nhất
    // JVM đảm bảo class này chỉ được load và khởi tạo 1 lần duy nhất khi được gọi đến -> Thread-Safe
    private static class Holder {
        private static final SimpleSymbolMapper INSTANCE = new SimpleSymbolMapper();
    }

    // Public method để lấy Instance duy nhất
    public static SimpleSymbolMapper getInstance() {
        return Holder.INSTANCE;
    }

    // -------------------------

    /**
     * Hàm khởi tạo: Load dữ liệu từ Aerospike vào RAM.
     * Cần gọi hàm này 1 lần lúc start app.
     */
    public synchronized void init() {
        if (isInitialized) return;

        LOG.info("🔄 Initializing SimpleSymbolMapper (Singleton) from Aerospike...");
        Map<String, Short> dbMap = DataManagerAerospikeFloatSim.loadSymbolMapper();

        if (dbMap != null && !dbMap.isEmpty()) {
            strToId.putAll(dbMap);

            // Rebuild map ngược (ID -> String) và tìm max counter
            short maxId = 0;
            for (Map.Entry<String, Short> entry : dbMap.entrySet()) {
                idToStr.put(entry.getValue(), entry.getKey());
                if (entry.getValue() > maxId) {
                    maxId = entry.getValue();
                }
            }
            // Cập nhật counter để ID tiếp theo không bị trùng
            counter = maxId;
        }

        isInitialized = true;
        LOG.info("✅ SimpleSymbolMapper initialized. Total: {}, Next ID: {}", strToId.size(), counter + 1);
    }

    /**
     * Lấy ID của Symbol.
     * - Nếu đã có trong RAM -> Trả về ngay.
     * - Nếu chưa có -> Tạo ID mới -> Lưu RAM -> Lưu Aerospike -> Trả về.
     */
    public short getId(String symbol) {
        // Tự động init nếu chưa init (Lazy Load an toàn)
        if (!isInitialized) {
            init();
        }

        if (strToId.containsKey(symbol)) {
            return strToId.get(symbol);
        }

        // Cấp ID mới
        short newId = ++counter;

        // 1. Lưu vào RAM
        strToId.put(symbol, newId);
        idToStr.put(newId, symbol);

        // 2. Lưu vào Aerospike
        DataManagerAerospikeFloatSim.saveSymbolMapping(symbol, newId);

        return newId;
    }

    public String getSymbol(short id) {
        if (!isInitialized) init();
        return idToStr.getOrDefault(id, "UNKNOWN-" + id);
    }

    public Map<String, Short> getAllMappings() {
        if (!isInitialized) init();
        return strToId;
    }

    public static void main(String[] args) {
        // 1. Khởi tạo (tùy chọn, vì getId tự gọi nếu cần)
        SimpleSymbolMapper.getInstance().init();

// 2. Lấy ID
        short id = SimpleSymbolMapper.getInstance().getId("ETHUSDT");
        String symbol = SimpleSymbolMapper.getInstance().getSymbol(id);
        LOG.info("ID of {}: {}", id, symbol);
        id = SimpleSymbolMapper.getInstance().getId("CYBERUSDT");
        symbol = SimpleSymbolMapper.getInstance().getSymbol(id);
        LOG.info("ID of {}: {}", id, symbol);
        id = SimpleSymbolMapper.getInstance().getId("BTCUSDT");
// 3. Lấy Symbol ngược lại
        symbol = SimpleSymbolMapper.getInstance().getSymbol(id);
        LOG.info("ID of {}: {}", id, symbol);
    }
}