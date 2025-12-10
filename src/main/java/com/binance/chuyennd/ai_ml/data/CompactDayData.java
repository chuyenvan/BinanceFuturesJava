package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

/**
 * Lưu trữ dữ liệu 1 ngày dạng cột (Columnar).
 * - Bỏ mảng Time (Dùng index để tính).
 * - Bỏ mảng Volume (Tiết kiệm RAM).
 * - Size cố định 1440.
 */
public class CompactDayData {
    // 4 mảng giá (4 * 4 bytes = 16 bytes/nến)
    public float[] opens = new float[1440];
    public float[] highs = new float[1440];
    public float[] lows = new float[1440];
    public float[] closes = new float[1440];

    // Hàm lưu dữ liệu vào mảng
    public void set(long dayStart, long time, KlineObjectSimple kline) {
        // Tính index dựa trên phút trong ngày (0 -> 1439)
        int index = (int) ((time - dayStart) / 60000L);
        if (index >= 0 && index < 1440) {
            opens[index] = kline.priceOpen.floatValue();
            highs[index] = kline.maxPrice.floatValue();
            lows[index] = kline.minPrice.floatValue();
            closes[index] = kline.priceClose.floatValue();
        }
    }

    // Hàm lấy dữ liệu ra (Tái tạo Object)
    public KlineObjectSimple get(long dayStart, int index) {
        // Nếu close == 0 tức là phút đó không có dữ liệu
        if (closes[index] == 0.0f) return null;

        KlineObjectSimple k = new KlineObjectSimple();
        // Tái tạo lại Time từ index
        k.startTime = (double) (dayStart + index * 60000L);
        k.priceOpen = (double) opens[index];
        k.maxPrice = (double) highs[index];
        k.minPrice = (double) lows[index];
        k.priceClose = (double) closes[index];
        k.totalUsdt = 0.0; // Volume đã bỏ để tiết kiệm RAM
        return k;
    }
}