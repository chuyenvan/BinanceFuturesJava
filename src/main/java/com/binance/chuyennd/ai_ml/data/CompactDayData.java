package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import java.util.Arrays;

/**
 * Lưu trữ dữ liệu 1 ngày của 1 Symbol dưới dạng mảng nguyên thủy.
 * Không dùng List, không dùng KlineObjectSimple để tiết kiệm RAM.
 */
public class CompactDayData {
    public final short symbolId;
    public int size = 0;

    // Dữ liệu dạng cột (Columnar)
    public long[] times;
    public float[] opens;
    public float[] highs;
    public float[] lows;
    public float[] closes;
    public float[] volumes;

    public CompactDayData(short symbolId, int capacity) {
        this.symbolId = symbolId;
        this.times = new long[capacity];
        this.opens = new float[capacity];
        this.highs = new float[capacity];
        this.lows = new float[capacity];
        this.closes = new float[capacity];
        this.volumes = new float[capacity];
    }

    public void add(long time, KlineObjectSimple kline) {
        if (size >= times.length) {
            // Tự động mở rộng mảng nếu thiếu (ít khi xảy ra nếu init đúng 1440)
            resize(size * 2);
        }
        times[size] = time;
        opens[size] = kline.priceOpen.floatValue();
        highs[size] = kline.maxPrice.floatValue();
        lows[size] = kline.minPrice.floatValue();
        closes[size] = kline.priceClose.floatValue();
        volumes[size] = kline.totalUsdt.floatValue();
        size++;
    }

    // Tìm vị trí của thời gian (Binary Search vì time luôn tăng dần) -> Cực nhanh
    public int findIndex(long time) {
        int idx = Arrays.binarySearch(times, 0, size, time);
        // Nếu không tìm thấy chính xác, binarySearch trả về -(insertion point) - 1
        // Ta muốn lấy nến ngay trước đó (floor)
        if (idx < 0) {
            idx = -idx - 2;
        }
        if (idx < 0) return -1;
        return idx;
    }

    // Lấy object ra (chỉ tạo khi cần dùng - Flyweight)
    public KlineObjectSimple getKline(int index) {
        if (index < 0 || index >= size) return null;

        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = (double) times[index];
        k.priceOpen = (double) opens[index];
        k.maxPrice = (double) highs[index];
        k.minPrice = (double) lows[index];
        k.priceClose = (double) closes[index];
        k.totalUsdt = (double) volumes[index];
        return k;
    }

    private void resize(int newCapacity) {
        times = Arrays.copyOf(times, newCapacity);
        opens = Arrays.copyOf(opens, newCapacity);
        highs = Arrays.copyOf(highs, newCapacity);
        lows = Arrays.copyOf(lows, newCapacity);
        closes = Arrays.copyOf(closes, newCapacity);
        volumes = Arrays.copyOf(volumes, newCapacity);
    }
}