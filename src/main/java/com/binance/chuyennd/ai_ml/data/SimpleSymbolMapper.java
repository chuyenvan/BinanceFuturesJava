package com.binance.chuyennd.ai_ml.data;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class SimpleSymbolMapper {
    // Map lưu trữ: Symbol (String) <-> ID (Short)
    private static final Map<String, Short> strToId = new ConcurrentHashMap<>();
    private static final Map<Short, String> idToStr = new ConcurrentHashMap<>();

    // Bộ đếm ID, bắt đầu từ 1 (để dành 0 cho null/error nếu cần)
    private static short counter = 0;

    /**
     * Lấy ID của Symbol.
     * Nếu Symbol mới chưa có trong Map -> Tự động cấp ID mới tăng dần.
     * Synchronized để đảm bảo an toàn tuyệt đối khi chạy đa luồng load data.
     */
    public static synchronized short getId(String symbol) {
        if (strToId.containsKey(symbol)) {
            return strToId.get(symbol);
        }

        short newId = ++counter;
        strToId.put(symbol, newId);
        idToStr.put(newId, symbol);

        return newId;
    }

    /**
     * Lấy lại String Symbol từ ID (dùng khi in log hoặc debug)
     */
    public static String getSymbol(short id) {
        return idToStr.getOrDefault(id, "UNKNOWN-" + id);
    }
}