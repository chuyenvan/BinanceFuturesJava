package com.binance.chuyennd.websocket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiPredicate;

/**
 * [INGEST-QF/QF2] Thay pass settle REST MỌI symbol mỗi phút (≈752 weight/phút, 10-30 rewritten_diff=0 cả ngày) bằng:
 * <ol>
 *   <li><b>suspects</b>: (symbol, phút) có ô KHÔNG phải WS final (REST sớm chưa settle, thiếu, khởi động) ⇒ kiểm lại bằng REST
 *       limit đủ phủ phút cũ nhất (weight 1, MỘT call phủ mọi phút của symbol); ô nào WS final tới muộn ⇒ gỡ trước khi gọi
 *       ({@link #dropCovered});</li>
 *   <li><b>sample</b>: {@code sampleN} symbol/phút xoay vòng — đối soát ô WS.</li>
 * </ol>
 * Thuần logic (không mạng), test được. Prereg: docs/prereg/PREREG_INGEST_QUICKFIX.md (+ADD1, ADD-1b).
 */
public final class SettlePlanner {
    private static final Logger LOG = LoggerFactory.getLogger(SettlePlanner.class);
    static final long MIN = 60_000L;
    static final int MIN_LIMIT = 3, MAX_LIMIT = 99;

    /** symbol đầy đủ -> các phút (openTime) chưa được kiểm. */
    private final ConcurrentHashMap<String, TreeSet<Long>> pending = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Integer> failStreak = new ConcurrentHashMap<>();
    private final int sampleN;
    private final int maxFailPasses;
    private int cursor = 0;
    private long droppedCells = 0;

    public SettlePlanner(int sampleN, int maxFailPasses) {
        this.sampleN = Math.max(0, sampleN);
        this.maxFailPasses = Math.max(1, maxFailPasses);
    }

    public static final class Plan {
        public final List<String> suspects = new ArrayList<>();
        public final List<String> sample = new ArrayList<>();
        public int suspectLimit = MIN_LIMIT;
    }

    public synchronized void markSuspect(String fullSym, long minute) {
        pending.computeIfAbsent(fullSym, k -> new TreeSet<>()).add(minute);
    }

    public synchronized void markSuspects(Collection<String> fullSyms, long minute) {
        for (String s : fullSyms) markSuspect(s, minute);
    }

    public int suspectCount() {
        return pending.size();
    }

    /** [QF3] Bản sao các phút còn chờ của một symbol (rỗng nếu không còn). */
    public synchronized List<Long> pendingOf(String fullSym) {
        TreeSet<Long> t = pending.get(fullSym);
        return t == null ? new ArrayList<>() : new ArrayList<>(t);
    }

    /** Số symbol còn ô phút {@code minute} chưa kiểm. */
    public synchronized int pendingAt(long minute) {
        int n = 0;
        for (TreeSet<Long> t : pending.values()) if (t.contains(minute)) n++;
        return n;
    }

    /** Tổng ô bị bỏ kiểm (REST lỗi quá {@code maxFailPasses} pass) từ khi start — Q2 coi là TRƯỢT. */
    public synchronized long droppedCells() {
        return droppedCells;
    }

    /** Gỡ ô đã có WS final (tới muộn sau khi bị đánh dấu). Trả số ô gỡ. */
    public synchronized int dropCovered(BiPredicate<String, Long> hasWsFinal) {
        int n = 0;
        for (Iterator<Map.Entry<String, TreeSet<Long>>> it = pending.entrySet().iterator(); it.hasNext(); ) {
            Map.Entry<String, TreeSet<Long>> e = it.next();
            for (Iterator<Long> mi = e.getValue().iterator(); mi.hasNext(); ) {
                if (hasWsFinal.test(e.getKey(), mi.next())) {
                    mi.remove();
                    n++;
                }
            }
            if (e.getValue().isEmpty()) {
                it.remove();
                failStreak.remove(e.getKey());
            }
        }
        return n;
    }

    /** Limit REST cần để phủ phút {@code oldestMin} khi phút đang mở là {@code curMin}. */
    static int limitFor(long curMin, long oldestMin) {
        long span = (curMin - oldestMin) / MIN + 2;   // + nến đang mở + 1 đệm
        return (int) Math.max(MIN_LIMIT, Math.min(MAX_LIMIT, span));
    }

    /** Limit cho một tập symbol (theo phút cũ nhất của chính tập đó). */
    public synchronized int limitFor(Collection<String> syms, long curMin) {
        long minOld = Long.MAX_VALUE;
        for (String s : syms) {
            TreeSet<Long> t = pending.get(s);
            if (t != null && !t.isEmpty()) minOld = Math.min(minOld, t.first());
        }
        return minOld == Long.MAX_VALUE ? MIN_LIMIT : limitFor(curMin, minOld);
    }

    /** Kế hoạch cho pass ở phút đang mở {@code curMin} (mọi phút đã đóng coi là đủ tuổi). */
    public synchronized Plan plan(long curMin, List<String> universe) {
        return plan(curMin, universe, curMin - MIN);
    }

    /**
     * [QF2] Kế hoạch: chỉ symbol có ô ĐỦ TUỔI settle ({@code openTime <= matureThrough}, tức nến đã đóng ≥ settleMinAge) —
     * ô chưa đủ tuổi REST chưa chắc final, KlineIngestCore.settle cũng không ghi ⇒ không gọi phí, không gỡ.
     */
    public synchronized Plan plan(long curMin, List<String> universe, long matureThrough) {
        Plan p = new Plan();
        Set<String> uni = new HashSet<>(universe);
        for (Iterator<Map.Entry<String, TreeSet<Long>>> it = pending.entrySet().iterator(); it.hasNext(); ) {
            Map.Entry<String, TreeSet<Long>> e = it.next();
            if (!uni.contains(e.getKey())) {           // symbol bi go khoi universe => thoi kiem
                it.remove();
                failStreak.remove(e.getKey());
                continue;
            }
            if (e.getValue().first() >= curMin || e.getValue().first() > matureThrough) continue;   // chua dong / chua du tuoi
            p.suspects.add(e.getKey());
        }
        // o cu nhat truoc (khong symbol nao bi bo doi: o nao cung gia dan), cung phut thi theo ten
        p.suspects.sort(java.util.Comparator.<String>comparingLong(s -> pending.get(s).first()).thenComparing(s -> s));
        p.suspectLimit = limitFor(p.suspects, curMin);
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
     * Ghi nhận kết quả pass suspects: symbol fetch OK với limit {@code limit} ở phút {@code curMin} ⇒ mọi ô phút &lt; curMin
     * đã kiểm (ô ngoài tầm 99′ thì bỏ + WARN). Lỗi ⇒ giữ; quá {@code maxFailPasses} pass liên tiếp ⇒ bỏ + WARN + đếm droppedCells.
     */
    public synchronized void onSuspectsSettled(Collection<String> requested, Collection<String> failed, long curMin, int limit) {
        onSuspectsSettled(requested, failed, curMin, limit, curMin - MIN);
    }

    /** [QF2] Chỉ gỡ ô đủ tuổi ({@code <= matureThrough}); ô chưa đủ tuổi giữ lại cho pass sau. */
    public synchronized void onSuspectsSettled(Collection<String> requested, Collection<String> failed, long curMin, int limit,
                                               long matureThrough) {
        Set<String> bad = new HashSet<>(failed);
        long covered = curMin - (long) (limit - 1) * MIN;
        for (String s : requested) {
            TreeSet<Long> t = pending.get(s);
            if (t == null) continue;
            if (bad.contains(s)) {
                int k = failStreak.merge(s, 1, Integer::sum);
                if (k >= maxFailPasses) {
                    droppedCells += t.size();
                    pending.remove(s);
                    failStreak.remove(s);
                    LOG.warn("[KLINE-INGEST] bo kiem lai {} ({} o) sau {} pass REST loi lien tiep (symbol loi/delist?)", s, t.size(), k);
                }
                continue;
            }
            if (!t.isEmpty() && t.first() < covered) {
                LOG.warn("[KLINE-INGEST] {} co o chua kiem tu {} ngoai tam limit={} — chi kiem duoc tu {}", s, t.first(), limit, covered);
            }
            t.headSet(Math.min(curMin - MIN, matureThrough), true).clear();   // phut da dong + du tuoi da kiem (hoac ngoai tam)
            if (t.isEmpty()) pending.remove(s);
            failStreak.remove(s);
        }
    }

    /** Lấy tối đa {@code room} phần tử, bắt đầu xoay vòng theo {@code rot} (không symbol nào bị bỏ đói mãi). */
    public static List<String> take(List<String> syms, int room, long rot) {
        if (room >= syms.size()) return new ArrayList<>(syms);
        List<String> out = new ArrayList<>(Math.max(0, room));
        int n = syms.size();
        int start = (int) Math.floorMod(rot, (long) n);
        for (int i = 0; i < room; i++) out.add(syms.get((start + i) % n));
        return out;
    }
}
