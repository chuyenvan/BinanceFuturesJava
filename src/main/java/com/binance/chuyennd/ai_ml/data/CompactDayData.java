package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import java.util.Arrays;

public class CompactDayData {

    // TASK-142 (lossless): 5 field/phút — GIỮ totalUsdt (trước đây bỏ → CompactDayData LOSSY, làm sai
    // Utils.isTickerAvailable ở phút minPrice==maxPrice có volume). Cấu trúc:
    // [Open0,High0,Low0,Close0,Vol0, Open1,High1,Low1,Close1,Vol1, ...]. Size: 1440 * 5 = 7200 phần tử.
    private static final int F = 5;
    private final float[] data = new float[1440 * F];

    public CompactDayData() {
        // Khởi tạo giá trị mặc định là NaN để biết là chưa có dữ liệu
        Arrays.fill(data, Float.NaN);
    }

    public void set(long dayStart, long time, KlineObjectSimple kline) {
        int index = (int) ((time - dayStart) / 60000L);
        if (index >= 0 && index < 1440) {
            int base = index * F;

            data[base]     = kline.priceOpen;
            data[base + 1] = kline.maxPrice;
            data[base + 2] = kline.minPrice;
            data[base + 3] = kline.priceClose;
            data[base + 4] = kline.totalUsdt;   // GIỮ volume (lossless)
        }
    }

    // TỐI ƯU 2: Truyền Object vào để tái sử dụng (Zero Garbage Collection)
    // Thay vì: KlineObjectSimple k = getData(...)
    // Dùng: compactData.fillData(..., klineReuse);
    public boolean get(long dayStart, int index, KlineObjectSimple output) {
        int base = index * F;

        // Kiểm tra nhanh: Nếu Open là NaN nghĩa là phút này không có dữ liệu
        if (Float.isNaN(data[base])) {
            return false;
        }

        output.startTime =  (dayStart + index * 60000L);
        output.priceOpen = data[base];
        output.maxPrice  = data[base + 1];
        output.minPrice  = data[base + 2];
        output.priceClose= data[base + 3];
        output.totalUsdt = data[base + 4];   // GIỮ volume (lossless) — trước đây = 0 gây sai isTickerAvailable

        return true; // Có dữ liệu
    }

    // Vẫn giữ hàm cũ để tương thích (nhưng không khuyến khích dùng trong vòng lặp lớn)
    public KlineObjectSimple get(long dayStart, int index) {
        KlineObjectSimple k = new KlineObjectSimple();
        if (get(dayStart, index, k)) {
            return k;
        }
        return null;
    }
}