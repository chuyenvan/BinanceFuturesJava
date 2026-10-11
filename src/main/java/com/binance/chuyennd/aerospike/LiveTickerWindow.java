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
 * <p>[KFIX-B 2026-10-10] <b>Đọc lại</b> {@code rereadMinutes} (mặc định 3, env {@code KLINE_LIVE_REREAD_MIN}, 0 = tắt =
 * hành vi cũ) phút ĐÃ nạp gần nhất mỗi tick; nến khác ⇒ GHI ĐÈ cache. Lý do: nến M đọc ở giây 6 có thể là bản chưa chốt
 * (audit KLINE_242_DIVERGENCE / KLINE_FIX_242_EVIDENCE: 12,5% phút live đọc trước khi ingest chốt; REST sớm chưa settle) và
 * trước đây được giữ vĩnh viễn trong cache. Đồng thời đo "độ đúng nến lúc quyết định" qua {@link LiveKlineAudit}
 * (log {@code [LIVE-KLINE]} mỗi 10'). Chi phí: +≤3 phút đọc/tick (~21 KB/phút).
 *
 * <p>Full reload khi: khởi động (cache rỗng), clock nhảy (lùi/vượt quá cửa sổ), đổi kích thước cửa sổ.
 * Thread-safe (đọc đồng bộ) — mỗi tick xây list KẾT QUẢ mới, không trả object cache để ghi.
 */
public final class LiveTickerWindow {

    private static final Logger LOG = LoggerFactory.getLogger(LiveTickerWindow.class);
    static final int REREAD_DEFAULT = 3;
    static final long STATS_EVERY_MIN = 10;

    /** Nguồn phút (prod: {@link DataManagerAerospikeFloatSim#readDataFromAerospikeCustom}) — tiêm được cho test. */
    interface MinuteReader {
        TreeMap<Long, Map<String, KlineObjectSimple>> read(long fromMinute, int count);
    }

    /** symbol -> (phút căn chỉnh ms -> nến 1m). TreeMap cho thứ tự tăng dần + cắt headMap O(1). */
    private final Map<String, TreeMap<Long, KlineObjectSimple>> bySymbol = new HashMap<>();
    /** Phút cuối đã nạp (inclusive, căn phút). Long.MIN_VALUE = cold. */
    private long loadedThroughMinute = Long.MIN_VALUE;
    private int windowMinutes = 0;
    private final MinuteReader reader;
    private final int rereadMinutes;
    private final LiveKlineAudit audit = new LiveKlineAudit();
    private long lastStatsMinute = Long.MIN_VALUE;

    public LiveTickerWindow() {
        this(DataManagerAerospikeFloatSim::readDataFromAerospikeCustom, rereadFromEnv());
    }

    LiveTickerWindow(MinuteReader reader, int rereadMinutes) {
        this.reader = reader;
        this.rereadMinutes = Math.max(0, rereadMinutes);
    }

    static int rereadFromEnv() {
        String v = com.binance.chuyennd.tradecore.Cfg.getOr("KLINE_LIVE_REREAD_MIN", String.valueOf(REREAD_DEFAULT));
        try {
            return Math.max(0, Integer.parseInt(v.trim()));
        } catch (NumberFormatException e) {
            LOG.error("[LIVE-KLINE] KLINE_LIVE_REREAD_MIN='{}' khong hop le -> {}", v, REREAD_DEFAULT);
            return REREAD_DEFAULT;
        }
    }

    /** Thước độ đúng nến lúc quyết định (đánh dấu top-K / PASS từ DetectEntrySignal2TradeNormal). */
    public LiveKlineAudit audit() {
        return audit;
    }

    public int rereadMinutes() {
        return rereadMinutes;
    }

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
            audit.dropBefore(Long.MAX_VALUE);
            loadedThroughMinute = startMinute - Utils.TIME_MINUTE;
            LOG.info("[TICKER-CACHE] full reload window={} phut [{}..{}] (now={})", minutesToRead,
                    Utils.normalizeDateYYYYMMDDHHmm(startMinute), Utils.normalizeDateYYYYMMDDHHmm(endMinute),
                    Utils.normalizeDateYYYYMMDDHHmm(now));
        }
        windowMinutes = minutesToRead;
        long prevLoaded = loadedThroughMinute;

        // [KFIX-B] đọc lại các phút ĐÃ nạp gần nhất (trước khi nạp phút mới) — sửa nến đọc lúc chưa chốt.
        if (rereadMinutes > 0 && !full) {
            long rFrom = Math.max(startMinute, prevLoaded - (long) (rereadMinutes - 1) * Utils.TIME_MINUTE);
            long rTo = Math.min(prevLoaded, endMinute);
            if (rTo >= rFrom) {
                int cnt = (int) ((rTo - rFrom) / Utils.TIME_MINUTE) + 1;
                audit.countOverwrite(mergeReread(reader.read(rFrom, cnt)));
            }
        }

        boolean freshEnd = false;
        if (loadedThroughMinute < endMinute) {
            long fromMinute = loadedThroughMinute + Utils.TIME_MINUTE;
            int count = (int) ((endMinute - fromMinute) / Utils.TIME_MINUTE) + 1;
            long t0 = System.currentTimeMillis();
            TreeMap<Long, Map<String, KlineObjectSimple>> fresh = reader.read(fromMinute, count);
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : fresh.entrySet()) {
                long m = e.getKey();
                for (Map.Entry<String, KlineObjectSimple> k : e.getValue().entrySet()) {
                    bySymbol.computeIfAbsent(k.getKey(), s -> new TreeMap<>()).put(m, k.getValue());
                }
            }
            Map<String, KlineObjectSimple> endMap = fresh.get(endMinute);
            if (endMap != null && !endMap.isEmpty()) {
                audit.onDecisionRead(endMinute, endMap);        // ảnh chụp nến dùng để quyết định phút này
                freshEnd = true;
            }
            loadedThroughMinute = endMinute;
            long ms = System.currentTimeMillis() - t0;
            if (count > 1 || full) {
                LOG.info("[TICKER-CACHE] +{} phut moi ({}..{}) trong {} ms, {} symbol trong bo nho",
                        count, Utils.normalizeDateYYYYMMDDHHmm(fromMinute),
                        Utils.normalizeDateYYYYMMDDHHmm(endMinute), ms, bySymbol.size());
            }
        }

        // [KFIX-B] phút quyết định sẽ KHÔNG còn được đọc lại ở tick sau ⇒ chốt thước (so ảnh chụp vs bản mới nhất).
        long nextFrom = loadedThroughMinute - (long) (Math.max(1, rereadMinutes) - 1) * Utils.TIME_MINUTE;
        finalizeBefore(rereadMinutes > 0 ? nextFrom : Long.MAX_VALUE, freshEnd ? endMinute : Long.MIN_VALUE);
        if (endMinute != lastStatsMinute && (endMinute / Utils.TIME_MINUTE) % STATS_EVERY_MIN == 0) {
            lastStatsMinute = endMinute;
            LOG.info("[LIVE-KLINE] reread={}' {}", rereadMinutes, audit.statsLine());
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

    /** Ghi đè cache bằng bản đọc lại nếu khác (hoặc cache chưa có). Trả số ô (symbol, phút) bị ghi đè. */
    private int mergeReread(TreeMap<Long, Map<String, KlineObjectSimple>> again) {
        int n = 0;
        if (again == null) return 0;
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : again.entrySet()) {
            long m = e.getKey();
            for (Map.Entry<String, KlineObjectSimple> k : e.getValue().entrySet()) {
                TreeMap<Long, KlineObjectSimple> t = bySymbol.computeIfAbsent(k.getKey(), s -> new TreeMap<>());
                if (!LiveKlineAudit.same(t.get(m), k.getValue())) {
                    t.put(m, k.getValue());
                    n++;
                }
            }
        }
        return n;
    }

    private void finalizeBefore(long threshold, long exclude) {
        for (long m : audit.trackedMinutes()) {
            if (m >= threshold || m == exclude) continue;
            Map<String, KlineObjectSimple> latest = new HashMap<>();
            for (Map.Entry<String, TreeMap<Long, KlineObjectSimple>> e : bySymbol.entrySet()) {
                KlineObjectSimple k = e.getValue().get(m);
                if (k != null) latest.put(e.getKey(), k);
            }
            audit.finalizeMinute(m, latest);
        }
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
