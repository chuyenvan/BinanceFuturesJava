package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * [B6-PASS-SPEED-V3] Cửa sổ nến 1m TRƯỢT cho đường live — bỏ đọc lại 1000' MỖI tick.
 *
 * <p>Trước đây {@code DetectEntrySignal2TradeNormal.checkMarketLevelChange2Trade} gọi
 * {@code readDataForSymbols(now-1000', 1000)} MỖI tick = đọc + giải nén + parse 1000 phút × ~736 symbol
 * ≈ 7MB (~1.8–2.4s). Nay: cache per-symbol các nến 1m đã parse, mỗi tick CHỈ đọc các phút MỚI
 * (BatchRead, retry sẵn trong {@link DataManagerAerospikeFloatSim#readDataFromAerospikeCustom}) rồi
 * append; drop phút cũ hơn cửa sổ (trượt).
 *
 * <p><b>Parity:</b> nội dung nến (open/high/low/close/volume) đọc từ CÙNG record Aerospike ⇒
 * BIT-IDENTICAL full-read. Khác biệt duy nhất là {@code startTime} (cache căn phút, full-read giữ offset
 * sub-phút của {@code now}) — vô hại vì mọi consumer của {@code time}/startTime đều chuẩn hoá về phút
 * hoặc thô hơn ({@code getTopCoin} chia nguyên, OI floorKey merge_asof 2h, S1 căn giờ,
 * {@code normalizeDateYYYYMMDDHHmm} cắt giây). Xem PREREG_PASS_SPEED_V3 §2.1.
 *
 * <p>Full reload khi: khởi động (cache rỗng), clock nhảy (lùi/vượt quá cửa sổ), đổi kích thước cửa sổ.
 * Thread-safe (đọc đồng bộ) — mỗi tick xây list KẾT QUẢ mới, không trả object cache để ghi.
 */
public final class LiveTickerWindow {

    private static final Logger LOG = LoggerFactory.getLogger(LiveTickerWindow.class);

    /** symbol -> (phút căn chỉnh ms -> nến 1m). TreeMap cho thứ tự tăng dần + cắt headMap O(1). */
    private final Map<String, TreeMap<Long, KlineObjectSimple>> bySymbol = new HashMap<>();
    /** Phút cuối đã nạp (inclusive, căn phút). Long.MIN_VALUE = cold. */
    private long loadedThroughMinute = Long.MIN_VALUE;
    private int windowMinutes = 0;

    /**
     * Đọc cửa sổ {@code minutesToRead} phút kết thúc tại phút hoàn chỉnh cuối cùng (≤ now-1').
     *
     * @param now           thời điểm hiện tại (ms); cửa sổ = [floor(now)-minutesToRead·1', floor(now)-1'].
     * @param minutesToRead kích thước cửa sổ (phút).
     * @return symbol -> danh sách nến 1m tăng dần theo thời gian (cùng quy ước append-USDT như
     *         {@link DataManagerAerospikeFloatSim#readDataForSymbols}).
     */
    public synchronized Map<String, List<KlineObjectSimple>> read(long now, int minutesToRead) {
        long[] w = windowBounds(now, minutesToRead);
        long startMinute = w[0];
        long endMinute = w[1];

        boolean full = windowMinutes != minutesToRead
                || loadedThroughMinute == Long.MIN_VALUE
                || loadedThroughMinute < startMinute   // nhảy tới (gap): dữ liệu đã nạp nằm ngoài cửa sổ
                || loadedThroughMinute > endMinute;    // clock lùi
        if (full) {
            bySymbol.clear();
            loadedThroughMinute = startMinute - Utils.TIME_MINUTE;
            LOG.info("[TICKER-CACHE] full reload window={} phut [{}..{}] (now={})", minutesToRead,
                    Utils.normalizeDateYYYYMMDDHHmm(startMinute), Utils.normalizeDateYYYYMMDDHHmm(endMinute),
                    Utils.normalizeDateYYYYMMDDHHmm(now));
        }
        windowMinutes = minutesToRead;

        if (loadedThroughMinute < endMinute) {
            long fromMinute = loadedThroughMinute + Utils.TIME_MINUTE;
            int count = (int) ((endMinute - fromMinute) / Utils.TIME_MINUTE) + 1;
            long t0 = System.currentTimeMillis();
            TreeMap<Long, Map<String, KlineObjectSimple>> fresh =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(fromMinute, count);
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : fresh.entrySet()) {
                long m = e.getKey();
                for (Map.Entry<String, KlineObjectSimple> k : e.getValue().entrySet()) {
                    bySymbol.computeIfAbsent(k.getKey(), s -> new TreeMap<>()).put(m, k.getValue());
                }
            }
            loadedThroughMinute = endMinute;
            long ms = System.currentTimeMillis() - t0;
            if (count > 1 || full) {
                LOG.info("[TICKER-CACHE] +{} phut moi ({}..{}) trong {} ms, {} symbol trong bo nho",
                        count, Utils.normalizeDateYYYYMMDDHHmm(fromMinute),
                        Utils.normalizeDateYYYYMMDDHHmm(endMinute), ms, bySymbol.size());
            }
        }

        // Trượt cửa sổ: bỏ nến cũ hơn startMinute.
        for (TreeMap<Long, KlineObjectSimple> m : bySymbol.values()) {
            if (m.isEmpty()) continue;
            m.headMap(startMinute, false).clear();
        }

        Map<String, List<KlineObjectSimple>> out = new HashMap<>(bySymbol.size());
        for (Map.Entry<String, TreeMap<Long, KlineObjectSimple>> e : bySymbol.entrySet()) {
            if (!e.getValue().isEmpty()) {
                out.put(e.getKey(), new ArrayList<>(e.getValue().values()));
            }
        }
        return out;
    }

    /** Số symbol đang giữ trong cache (diagnostic). */
    public synchronized int cachedSymbols() {
        return bySymbol.size();
    }

    /** [B6-SPEED] Cửa sổ phút căn chỉnh [startMinute..endMinute] cho {@code minutesToRead} phút kết thúc
     *  tại phút hoàn chỉnh cuối (≤ now-1'). THUẦN TÍNH TOÁN — test được không cần Aerospike. */
    static long[] windowBounds(long now, int minutesToRead) {
        long floor = now - (now % Utils.TIME_MINUTE);
        long endMinute = floor - Utils.TIME_MINUTE;
        long startMinute = endMinute - (long) (minutesToRead - 1) * Utils.TIME_MINUTE;
        return new long[]{startMinute, endMinute};
    }
}
