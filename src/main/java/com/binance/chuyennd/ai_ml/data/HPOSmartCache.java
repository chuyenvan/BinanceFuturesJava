package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class HPOSmartCache {

    private static final Logger LOG = LoggerFactory.getLogger(HPOSmartCache.class);

    // KHO CHỨA DỮ LIỆU NÉN (Dùng RAM ít nhất có thể)
    private static final ConcurrentHashMap<Long, Map<Short, CompactDayData>> RAM_STORE = new ConcurrentHashMap<>();

    /**
     * Hàm này được Simulator gọi.
     * Nhiệm vụ:
     * 1. Nếu chưa có data trong RAM: Load từ Disk -> Nén vào RAM Store -> Trả về Map.
     * 2. Nếu đã có data trong RAM: Bung nén từ RAM Store -> Trả về Map.
     */
    public static TreeMap<Long, Map<String, KlineObjectSimple>> getData(long dayStart) {

        // 1. Kiểm tra xem đã có trong Cache chưa
        Map<Short, CompactDayData> compressedMap = RAM_STORE.get(dayStart);

        if (compressedMap == null) {
            // --- TRƯỜNG HỢP CHƯA CÓ (LẦN ĐẦU LOAD) ---
            // Load Raw từ Aerospike/Disk
            TreeMap<Long, Map<String, KlineObjectSimple>> rawData = DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);

            if (rawData != null && !rawData.isEmpty()) {
                // Nén và lưu vào RAM Store ngay lập tức
                compressAndStore(dayStart, rawData);
            }
            return rawData; // Trả về luôn để dùng
        } else {
            // --- TRƯỜNG HỢP ĐÃ CÓ (RECONSTRUCT) ---
            // Bung nén từ CompactDayData ra TreeMap cho Simulator dùng
            return reconstructTreeMap(dayStart, compressedMap);
        }
    }

    // Hàm nén dữ liệu từ Raw Map vào Compact Store
    private static void compressAndStore(long dayStart, TreeMap<Long, Map<String, KlineObjectSimple>> rawData) {
        Map<Short, CompactDayData> compactMap = new HashMap<>();

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : rawData.entrySet()) {
            long time = entry.getKey();
            Map<String, KlineObjectSimple> symbolMap = entry.getValue();

            for (Map.Entry<String, KlineObjectSimple> ticker : symbolMap.entrySet()) {
                short symbolId = SimpleSymbolMapper.getId(ticker.getKey());
                KlineObjectSimple kline = ticker.getValue();

                CompactDayData compactData = compactMap.computeIfAbsent(symbolId, k -> new CompactDayData());
                compactData.set(dayStart, time, kline);
            }
        }
        RAM_STORE.put(dayStart, compactMap);
    }

    // Hàm tái tạo TreeMap từ dữ liệu nén (Chỉ tốn RAM tạm thời)
    private static TreeMap<Long, Map<String, KlineObjectSimple>> reconstructTreeMap(long dayStart, Map<Short, CompactDayData> compressedMap) {
        TreeMap<Long, Map<String, KlineObjectSimple>> result = new TreeMap<>();

        // Duyệt qua tất cả các Symbol trong ngày hôm đó
        for (Map.Entry<Short, CompactDayData> entry : compressedMap.entrySet()) {
            short symbolId = entry.getKey();
            CompactDayData compactData = entry.getValue();

            // Lấy lại tên Symbol từ ID (Bạn cần đảm bảo Mapper có hàm này)
            String symbol = SimpleSymbolMapper.getSymbol(symbolId);
            if (symbol == null) continue;

            // Duyệt 1440 phút trong ngày
            for (int i = 0; i < 1440; i++) {
                KlineObjectSimple kline = compactData.get(dayStart, i);
                if (kline != null) {
                    long time = kline.startTime.longValue();

                    // Put vào Result Map
                    result.computeIfAbsent(time, k -> new HashMap<>()).put(symbol, kline);
                }
            }
        }
        return result;
    }

    // Hàm getKline lẻ (cho BacktestEngineAI dùng nếu cần)
    public static KlineObjectSimple getKline(short symbolId, long time) {
        long dayStart = Utils.getStartOfDayGMT7(time);
        Map<Short, CompactDayData> dayMap = RAM_STORE.get(dayStart);
        if (dayMap == null) return null;
        CompactDayData data = dayMap.get(symbolId);
        if (data == null) return null;

        // Tính index
        int index = (int) ((time - dayStart) / 60000L);
        if (index < 0 || index >= 1440) return null;

        return data.get(dayStart, index);
    }
}