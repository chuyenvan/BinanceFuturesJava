package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import java.util.Arrays;

public class CompactDayData {

    // TỐI ƯU 1: Gộp 4 mảng thành 1 mảng duy nhất để tăng tốc độ truy cập CPU Cache
    // Cấu trúc: [Open0, High0, Low0, Close0, Open1, High1, Low1, Close1, ...]
    // Size: 1440 * 4 = 5760 phần tử
    private final float[] data = new float[5760];

    public CompactDayData() {
        // Khởi tạo giá trị mặc định là NaN để biết là chưa có dữ liệu
        Arrays.fill(data, Float.NaN);
    }

    public void set(long dayStart, long time, KlineObjectSimple kline) {
        int index = (int) ((time - dayStart) / 60000L);
        if (index >= 0 && index < 1440) {
            int base = index << 2; // Tương đương index * 4 nhưng nhanh hơn (Bit shift)

            data[base]     = kline.priceOpen.floatValue();
            data[base + 1] = kline.maxPrice.floatValue();
            data[base + 2] = kline.minPrice.floatValue();
            data[base + 3] = kline.priceClose.floatValue();
        }
    }

    // TỐI ƯU 2: Truyền Object vào để tái sử dụng (Zero Garbage Collection)
    // Thay vì: KlineObjectSimple k = getData(...)
    // Dùng: compactData.fillData(..., klineReuse);
    public boolean get(long dayStart, int index, KlineObjectSimple output) {
        int base = index << 2; // index * 4

        // Kiểm tra nhanh: Nếu Open là NaN nghĩa là phút này không có dữ liệu
        if (Float.isNaN(data[base])) {
            return false;
        }

        output.startTime =  (dayStart + index * 60000L);
        output.priceOpen = (float) data[base];
        output.maxPrice  = (float) data[base + 1];
        output.minPrice  = (float) data[base + 2];
        output.priceClose= (float) data[base + 3];
        output.totalUsdt = 0.0f;

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