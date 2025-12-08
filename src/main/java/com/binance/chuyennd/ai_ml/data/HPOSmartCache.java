package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class HPOSmartCache {

    private static final Logger LOG = LoggerFactory.getLogger(HPOSmartCache.class);

    // Key: StartTime ngày (Long)
    // Value: Map<SymbolId, CompactDayData> -> Lưu dạng mảng trong RAM
    private static final ConcurrentHashMap<Long, Map<Short, CompactDayData>> RAM_STORE = new ConcurrentHashMap<>();

    // Vẫn giữ Snappy cache cho disk IO nếu cần, nhưng RAM Store là quan trọng nhất
    // Ở đây tôi tối ưu thẳng vào việc lưu trữ sau khi giải nén

    public static void getData(long startTime) {
        if (RAM_STORE.containsKey(startTime)) return; // Đã có trong RAM

        // 1. Đọc từ nguồn (Disk/Aerospike) -> Ra TreeMap cũ
        TreeMap<Long, Map<String, KlineObjectSimple>> rawData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);

        if (rawData == null || rawData.isEmpty()) return;

        // 2. CONVERT TỪ TREEMAP SANG COMPACT ARRAYS (Tối ưu RAM)
        Map<Short, CompactDayData> compactMap = new HashMap<>();

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : rawData.entrySet()) {
            long time = entry.getKey();
            Map<String, KlineObjectSimple> symbolMap = entry.getValue();

            for (Map.Entry<String, KlineObjectSimple> tickerEntry : symbolMap.entrySet()) {
                String symbol = tickerEntry.getKey();
                short symbolId = SimpleSymbolMapper.getId(symbol);
                KlineObjectSimple kline = tickerEntry.getValue();

                // Lấy hoặc tạo mới CompactData cho symbol này
                CompactDayData compactData = compactMap.computeIfAbsent(symbolId,
                        k -> new CompactDayData(k, 1440)); // Mặc định 1440 phút/ngày

                compactData.add(time, kline);
            }
        }

        // 3. Lưu vào RAM Store
        RAM_STORE.put(startTime, compactMap);

        // Help GC
        rawData.clear();
        rawData = null;
    }

    /**
     * API Lấy dữ liệu siêu tốc cho BacktestEngine
     */
    public static KlineObjectSimple getKline(short symbolId, long time) {
        // 1. Xác định ngày (Key cấp 1)

        long dayStart = Utils.getStartTimeOfDay(time);

        Map<Short, CompactDayData> dayMap = RAM_STORE.get(dayStart);
        if (dayMap == null) return null;

        // 2. Lấy cục data mảng của Symbol
        CompactDayData compactData = dayMap.get(symbolId);
        if (compactData == null) return null;

        // 3. Tìm index trong mảng (Binary Search)
        int index = compactData.findIndex(time);

        // 4. Trả về Object (Hoặc null nếu không tìm thấy)
        return compactData.getKline(index);
    }

    // Clear cache
    public static void clear() {
        RAM_STORE.clear();
    }
}