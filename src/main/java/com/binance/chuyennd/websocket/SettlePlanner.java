package com.binance.chuyennd.websocket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * [INGEST-QF 2026-10-30] Thay pass settle REST MỌI symbol mỗi phút (≈752 weight/phút, 10-30 rewritten_diff=0 cả ngày) bằng:
 * <ol>
 *   <li><b>suspects</b>: symbol có ô nến KHÔNG đến từ WS final (REST sớm lúc +4 s có thể chưa settle, REST lỗi, thiếu khi
 *       khởi động) ⇒ kiểm lại bằng REST với limit đủ phủ ô cũ nhất (3..99, weight 1), tới khi fetch OK thì gỡ;</li>
 *   <li><b>sample</b>: {@code sampleN} symbol/phút xoay vòng theo thứ tự tên (phủ ~752 symbol mỗi ~30′) — đối soát ô WS.</li>
 * </ol>
 * Thuần logic (không mạng), test được. Prereg: docs/prereg/PREREG_INGEST_QUICKFIX.md.
 */
public final class SettlePlanner {
    private static final Logger LOG = LoggerFactory.getLogger(SettlePlanner.class);
    static final long MIN = 60_000L;
    static final int MIN_LIMIT = 3, MAX_LIMIT = 99;

    /** symbol đầy đủ -> phút (openTime) cũ nhất chưa được REST kiểm. */
    private final ConcurrentHashMap<String, Long> oldest = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Integer> failStreak = new ConcurrentHashMap<>();
    private final int sampleN;
    private final int maxFailPasses;
    private int cursor = 0;

    public SettlePlanner(int sampleN, int maxFailPasses) {
        this.sampleN = Math.max(0, sampleN);
        this.maxFailPasses = Math.max(1, maxFailPasses);
    }

    public static final class Plan {
        public final List<String> suspects = new ArrayList<>();
        public final List<String> sample = new ArrayList<>();
        public int suspectLimit = MIN_LIMIT;
    }

    public void markSuspect(String fullSym, long minute) {
        oldest.merge(fullSym, minute, Math::min);
    }

    public void markSuspects(Collection<String> fullSyms, long minute) {
        for (String s : fullSyms) markSuspect(s, minute);
    }

    public int suspectCount() {
        return oldest.size();
    }

    /** Limit REST cần để phủ phút {@code oldestMin} khi phút đang mở là {@code curMin}. */
    static int limitFor(long curMin, long oldestMin) {
        long span = (curMin - oldestMin) / MIN + 2;   // + nến đang mở + 1 đệm
        return (int) Math.max(MIN_LIMIT, Math.min(MAX_LIMIT, span));
    }

    /** Kế hoạch cho pass ở phút đang mở {@code curMin}; {@code universe} = symbol đang subscribe. */
    public synchronized Plan plan(long curMin, List<String> universe) {
        Plan p = new Plan();
        Set<String> uni = new HashSet<>(universe);
        long minOld = Long.MAX_VALUE;
        for (Map.Entry<String, Long> e : oldest.entrySet()) {
            if (!uni.contains(e.getKey())) {           // symbol bi go khoi universe => thoi kiem
                oldest.remove(e.getKey());
                failStreak.remove(e.getKey());
                continue;
            }
            if (e.getValue() >= curMin) continue;      // phut chua dong
            p.suspects.add(e.getKey());
            minOld = Math.min(minOld, e.getValue());
        }
        java.util.Collections.sort(p.suspects);
        if (!p.suspects.isEmpty()) p.suspectLimit = limitFor(curMin, minOld);
        List<String> sorted = new ArrayList<>(universe);
        java.util.Collections.sort(sorted);
        Set<String> sus = new HashSet<>(p.suspects);
        int n = sorted.size();
        for (int i = 0; i < n && p.sample.size() < sampleN; i++) {
            String s = sorted.get((cursor + i) % n);
            if (!sus.contains(s)) p.sample.add(s);
        }
        if (n > 0) cursor = (cursor + Math.min(sampleN, n)) % n;
        return p;
    }

    /**
     * Ghi nhận kết quả pass suspects: symbol fetch OK với limit {@code limit} ở phút {@code curMin} ⇒ mọi ô từ
     * {@code curMin-(limit-1)} đã kiểm ⇒ gỡ (ô cũ hơn vượt tầm 99′ thì bỏ, log). Lỗi ⇒ giữ, quá {@code maxFailPasses} pass ⇒ gỡ + WARN.
     */
    public synchronized void onSuspectsSettled(Collection<String> requested, Collection<String> failed, long curMin, int limit) {
        Set<String> bad = new HashSet<>(failed);
        long covered = curMin - (long) (limit - 1) * MIN;
        for (String s : requested) {
            if (bad.contains(s)) {
                int k = failStreak.merge(s, 1, Integer::sum);
                if (k >= maxFailPasses) {
                    oldest.remove(s);
                    failStreak.remove(s);
                    LOG.warn("[KLINE-INGEST] bo kiem lai {} sau {} pass REST loi lien tiep (symbol loi/delist?)", s, k);
                }
                continue;
            }
            Long o = oldest.get(s);
            if (o != null && o < covered) {
                LOG.warn("[KLINE-INGEST] {} co o chua kiem tu {} ngoai tam limit={} — chi kiem duoc tu {}", s, o, limit, covered);
            }
            oldest.remove(s);
            failStreak.remove(s);
        }
    }
}
