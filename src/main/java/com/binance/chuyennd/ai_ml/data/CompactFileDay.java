package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-142 (rework) — NÉN 1 NGÀY ticker-file (đường TICKER_SOURCE=file) dạng LOSSLESS, gọn RAM.
 *
 * <p><b>Vì sao KHÔNG dùng {@link CompactDayData}:</b> CompactDayData LOSSY — bỏ {@code totalUsdt}
 * (dựng lại = 0) nên {@link com.binance.chuyennd.utils.Utils#isTickerAvailable} ({@code minPrice!=maxPrice
 * || totalUsdt!=0}) ĐỔI quyết định vào lệnh ở phút {@code minPrice==maxPrice} nhưng có volume → lệch kết quả.
 *
 * <p><b>Vì sao KHÔNG cache exact-object:</b> giữ nguyên {@code TreeMap<Long,KlineObjectSimple[1000]>} tốn
 * ~16-24GB/window (2024 nhiều coin) → OOM trên Oracle 23GB. Bản nén này giữ per-coin {@code float[P*5]}
 * (open/high/low/close/<b>totalUsdt</b>) → ~5-6GB/window (clear trước OOS giữ đỉnh ~1 window).
 *
 * <p><b>Lossless ra sao:</b> lưu {@link #times} = ĐÚNG map key mỗi phút (KHÔNG giả định alignment). Khi
 * dựng lại đặt {@code kline.startTime = times[p]} = đúng key gốc. Đây là BẤT BIẾN mà sim vốn dựa vào:
 * vòng ngoài dùng {@code entry.getKey()} để tra {@code predictionMap.get(time)}, còn {@code createOrderBUY}
 * dùng {@code predictionMap.get(ticker.startTime)} — hai chỗ CHỈ khớp khi {@code ticker.startTime == key}.
 * Giữ đủ 5 field sim đọc + startTime = key ⇒ object VALUE dựng lại Y HỆT map gốc (đường đọc thẳng).
 */
final class CompactFileDay {

    /** Số field lưu mỗi phút: priceOpen, maxPrice, minPrice, priceClose, totalUsdt. */
    private static final int F = 5;
    /** Sentinel "phút này coin vắng dữ liệu" — priceOpen thực luôn > 0 nên NaN an toàn (như CompactDayData). */
    private static final float ABSENT = Float.NaN;

    /** Map key (mốc thời gian) mỗi phút, tăng dần, length = P. */
    private final long[] times;
    /** symbolId -> float[P*F]; slot [p*F] = NaN nghĩa là coin vắng ở phút p. */
    private final Map<Short, float[]> coin2ohlcv;
    /** Độ dài mảng KlineObjectSimple[] mỗi phút (khớp loader = 1000) để dựng lại đúng shape. */
    private final int arrLen;

    private CompactFileDay(long[] times, Map<Short, float[]> coin2ohlcv, int arrLen) {
        this.times = times;
        this.coin2ohlcv = coin2ohlcv;
        this.arrLen = arrLen;
    }

    /**
     * Nén map ngày (đã giải nén từ file) thành dạng compact. KHÔNG mutate {@code day}.
     * Yêu cầu {@code day} non-null, non-empty (caller đảm bảo — miss KHÔNG cache).
     */
    static CompactFileDay compress(TreeMap<Long, KlineObjectSimple[]> day) {
        int p = day.size();
        long[] times = new long[p];
        Map<Short, float[]> coin2 = new HashMap<>();
        int arrLen = 1000; // mặc định khớp KaggleDataLoader; ghi đè theo mảng thực tế bên dưới
        int idx = 0;
        for (Map.Entry<Long, KlineObjectSimple[]> e : day.entrySet()) {
            times[idx] = e.getKey();
            KlineObjectSimple[] arr = e.getValue();
            if (arr != null) {
                if (arr.length > arrLen) arrLen = arr.length;
                for (short id = 0; id < arr.length; id++) {
                    KlineObjectSimple k = arr[id];
                    if (k == null) continue;
                    float[] f = coin2.get(id);
                    if (f == null) {
                        f = new float[p * F];
                        java.util.Arrays.fill(f, ABSENT);
                        coin2.put(id, f);
                    }
                    int base = idx * F;
                    f[base]     = k.priceOpen;
                    f[base + 1] = k.maxPrice;
                    f[base + 2] = k.minPrice;
                    f[base + 3] = k.priceClose;
                    f[base + 4] = k.totalUsdt;   // 🔑 field CompactDayData làm mất — bản này GIỮ
                }
            }
            idx++;
        }
        return new CompactFileDay(times, coin2, arrLen);
    }

    /**
     * Dựng lại {@code TreeMap<Long, KlineObjectSimple[arrLen]>} Y HỆT map gốc (giá trị 5 field + startTime=key).
     * Mỗi lần gọi tạo object MỚI (sim chỉ ĐỌC ticker nên không cần chia sẻ; tránh mọi rủi ro mutate chéo).
     */
    TreeMap<Long, KlineObjectSimple[]> reconstruct() {
        int p = times.length;
        KlineObjectSimple[][] minuteArrs = new KlineObjectSimple[p][];
        for (int i = 0; i < p; i++) minuteArrs[i] = new KlineObjectSimple[arrLen];

        for (Map.Entry<Short, float[]> ce : coin2ohlcv.entrySet()) {
            short id = ce.getKey();
            float[] f = ce.getValue();
            for (int i = 0; i < p; i++) {
                int base = i * F;
                float open = f[base];
                if (Float.isNaN(open)) continue;   // coin vắng phút này
                KlineObjectSimple k = new KlineObjectSimple();
                k.startTime  = times[i];           // = ĐÚNG key gốc (bất biến sim dựa vào)
                k.priceOpen  = open;
                k.maxPrice   = f[base + 1];
                k.minPrice   = f[base + 2];
                k.priceClose = f[base + 3];
                k.totalUsdt  = f[base + 4];
                minuteArrs[i][id] = k;
            }
        }

        TreeMap<Long, KlineObjectSimple[]> out = new TreeMap<>();
        for (int i = 0; i < p; i++) out.put(times[i], minuteArrs[i]);
        return out;
    }

    /** Số phút (map entry) đang giữ — chỉ để log/giám sát. */
    int minutes() {
        return times.length;
    }
}
