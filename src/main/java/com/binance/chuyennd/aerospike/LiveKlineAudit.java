package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [KFIX-B 2026-10-10] Thước "độ đúng nến lúc quyết định" cho live/shadow (owner yêu cầu ≥ 99%).
 *
 * <p>Với mỗi phút quyết định M (phút đóng mới nhất mà tick đọc lần đầu), giữ ảnh chụp nến từng symbol lúc quyết định.
 * {@link LiveTickerWindow} đọc lại M ở các tick sau (cửa sổ đọc lại N phút); khi M rời cửa sổ đọc lại, {@link #finalizeMinute}
 * so ảnh chụp với bản đọc lại cuối cùng: khác (5 trường float32) ⇒ (symbol, M) "decided_on_unsettled".
 * Đếm riêng cho symbol vào top-K selector ({@link #markTopK}) và symbol PASS gate ({@link #markPass}) của tick đó.
 * Thuần logic, không I/O, thread-safe (synchronized) — tick live đơn luồng nên không tranh chấp.
 */
public final class LiveKlineAudit {

    private final Map<Long, Map<String, KlineObjectSimple>> decided = new TreeMap<>();
    private final Map<Long, Set<String>> topK = new HashMap<>();
    private final Map<Long, Set<String>> pass = new HashMap<>();
    private long currentDecisionMinute = Long.MIN_VALUE;

    // cộng dồn: [0]=all,[1]=topk,[2]=pass ; total / unsettled ; + phút đã chốt, ô nến đọc lại bị ghi đè
    final AtomicLong[] total = {new AtomicLong(), new AtomicLong(), new AtomicLong()};
    final AtomicLong[] unsettled = {new AtomicLong(), new AtomicLong(), new AtomicLong()};
    final AtomicLong minutes = new AtomicLong();
    final AtomicLong rereadOverwritten = new AtomicLong();
    /** Dùng chung (S1RankerLive là singleton riêng): số close 1h S1 bị sửa khi đọc lại. */
    static final AtomicLong S1_CLOSE_REWRITTEN = new AtomicLong();
    private long[] snap = new long[9];

    /** So khớp 5 trường giá/khối lượng (bit float32). */
    public static boolean same(KlineObjectSimple a, KlineObjectSimple b) {
        if (a == null || b == null) return a == b;
        return Float.floatToIntBits(a.priceOpen) == Float.floatToIntBits(b.priceOpen)
                && Float.floatToIntBits(a.maxPrice) == Float.floatToIntBits(b.maxPrice)
                && Float.floatToIntBits(a.minPrice) == Float.floatToIntBits(b.minPrice)
                && Float.floatToIntBits(a.priceClose) == Float.floatToIntBits(b.priceClose)
                && Float.floatToIntBits(a.totalUsdt) == Float.floatToIntBits(b.totalUsdt);
    }

    /** Tick đọc lần đầu phút M (nến dùng để quyết định). Giữ tham chiếu (cache thay object khi ghi đè, không sửa tại chỗ). */
    public synchronized void onDecisionRead(long minute, Map<String, KlineObjectSimple> candles) {
        decided.put(minute, new HashMap<>(candles));
        currentDecisionMinute = minute;
    }

    public synchronized long currentDecisionMinute() {
        return currentDecisionMinute;
    }

    /** Symbol nằm trong top-K selector của tick quyết định phút hiện tại. */
    public synchronized void markTopK(String symbol) {
        if (currentDecisionMinute != Long.MIN_VALUE) topK.computeIfAbsent(currentDecisionMinute, m -> new HashSet<>()).add(symbol);
    }

    /** Symbol PASS gate (không bị gate REJECT) ở tick quyết định phút hiện tại. */
    public synchronized void markPass(String symbol) {
        if (currentDecisionMinute != Long.MIN_VALUE) pass.computeIfAbsent(currentDecisionMinute, m -> new HashSet<>()).add(symbol);
    }

    void countOverwrite(int n) {
        rereadOverwritten.addAndGet(n);
    }

    public static void countS1Rewrite(int n) {
        S1_CLOSE_REWRITTEN.addAndGet(n);
    }

    /** Các phút quyết định đang chờ chốt (tăng dần). */
    public synchronized java.util.List<Long> trackedMinutes() {
        return new java.util.ArrayList<>(decided.keySet());
    }

    /** Có ảnh chụp quyết định cho phút này chưa chốt? */
    public synchronized boolean tracking(long minute) {
        return decided.containsKey(minute);
    }

    /**
     * Phút M rời cửa sổ đọc lại: so ảnh chụp lúc quyết định với bản mới nhất {@code latest} (symbol thiếu trong latest
     * ⇒ không đánh giá được, bỏ qua). Trả số (symbol, M) lệch.
     */
    public synchronized int finalizeMinute(long minute, Map<String, KlineObjectSimple> latest) {
        Map<String, KlineObjectSimple> d = decided.remove(minute);
        Set<String> tk = topK.remove(minute);
        Set<String> ps = pass.remove(minute);
        if (d == null) return 0;
        minutes.incrementAndGet();
        int bad = 0;
        for (Map.Entry<String, KlineObjectSimple> e : d.entrySet()) {
            KlineObjectSimple now = latest == null ? null : latest.get(e.getKey());
            if (now == null) continue;
            boolean diff = !same(e.getValue(), now);
            boolean inTop = tk != null && tk.contains(e.getKey());
            boolean inPass = ps != null && ps.contains(e.getKey());
            total[0].incrementAndGet();
            if (inTop) total[1].incrementAndGet();
            if (inPass) total[2].incrementAndGet();
            if (diff) {
                bad++;
                unsettled[0].incrementAndGet();
                if (inTop) unsettled[1].incrementAndGet();
                if (inPass) unsettled[2].incrementAndGet();
            }
        }
        return bad;
    }

    /** Bỏ ảnh chụp các phút cũ hơn {@code keepFrom} chưa chốt (vd full reload) — không tính vào thước. */
    public synchronized void dropBefore(long keepFrom) {
        decided.keySet().removeIf(m -> m < keepFrom);
        topK.keySet().removeIf(m -> m < keepFrom);
        pass.keySet().removeIf(m -> m < keepFrom);
    }

    static String pct(long bad, long tot) {
        return tot == 0 ? "n/a" : String.format("%.3f%%", 100.0 * (tot - bad) / tot);
    }

    /** Một dòng log: cộng dồn (cum) + cửa sổ kể từ lần gọi trước (win). correct = 1 − unsettled/total. */
    public synchronized String statsLine() {
        long[] cur = {total[0].get(), unsettled[0].get(), total[1].get(), unsettled[1].get(), total[2].get(),
                unsettled[2].get(), minutes.get(), rereadOverwritten.get(), S1_CLOSE_REWRITTEN.get()};
        long[] w = new long[cur.length];
        for (int i = 0; i < cur.length; i++) w[i] = cur[i] - snap[i];
        snap = cur;
        return String.format("win{minutes=%d decided_on_unsettled=%d/%d correct=%s | topK %d/%d correct=%s | pass %d/%d correct=%s"
                        + " | reread_overwritten=%d s1_close_rewritten=%d} cum{decided_on_unsettled=%d/%d correct=%s | topK %d/%d correct=%s"
                        + " | pass %d/%d correct=%s | minutes=%d}",
                w[6], w[1], w[0], pct(w[1], w[0]), w[3], w[2], pct(w[3], w[2]), w[5], w[4], pct(w[5], w[4]), w[7], w[8],
                cur[1], cur[0], pct(cur[1], cur[0]), cur[3], cur[2], pct(cur[3], cur[2]), cur[5], cur[4], pct(cur[5], cur[4]),
                cur[6]);
    }
}
