package com.binance.chuyennd.websocket;

import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [KFIX 2026-10-10] Lõi CHỐT NẾN 1m cho {@code ticker.kline_1m_opt} — thuần logic, test được (không static, không mạng).
 * Audit: docs/audit/KLINE_242_DIVERGENCE.md (15,7% ô lệch từ 2026-04-25: nến M chụp REST giây 2–6 rồi "chốt vĩnh viễn").
 *
 * <p>Ba nguồn ghi nến ĐÃ ĐÓNG M (minute = openTime ms):
 * <ol>
 *   <li><b>WS final</b> ({@code <sym>@kline_1m}, {@code k.x == true}) — nến cuối của sàn, tới &lt; 1 s sau khi đóng:
 *       {@link #onWsFinal} gom, {@link #flushWsFinals} ghi (trước khi live đọc ở giây 6).</li>
 *   <li><b>REST sớm</b> ({@link #earlyRest}, limit=2) — chỉ cho symbol THIẾU WS final (mọi symbol ở mode rest_settle).
 *       Có thể CHƯA settle ⇒ luôn được pass settle kiểm lại.</li>
 *   <li><b>REST settle</b> ({@link #settle}, limit ≥ 3) — nến đã đóng ≥ {@code settleMinAgeMs}: so với bản trong store,
 *       khác ⇒ GHI ĐÈ ({@code rewritten_diff}); thiếu ⇒ ghi ({@code filled_missing}). Với limit=3 mỗi nến được kiểm ở 2 pass
 *       liên tiếp (M ở pass M+1 và M+2) ⇒ symbol lỗi một lần tự lành ở pass sau.</li>
 * </ol>
 * Nến phút ĐANG MỞ (nặn từ ticker/price) chỉ được ghi qua {@link #writeOpenMinute}: bị CHẶN khi phút đó đã chốt
 * ({@code minute <= finalizedThrough}) ⇒ hết race ranh phút ghi đè nến đã chốt. Mọi ghi đi qua MỘT khoá.
 */
public final class KlineIngestCore {
    private static final Logger LOG = LoggerFactory.getLogger(KlineIngestCore.class);
    static final long MIN = 60_000L;

    /** Đọc/ghi một phút (key yyyyMMdd-HHmm) — prod: DataManagerAerospikeFloatSim (merge theo symbol). */
    public interface MinuteStore {
        Map<String, KlineObjectOptimized> read(long minute);

        void write(long minute, Map<String, KlineObjectOptimized> candles);
    }

    /** REST {@code fapi/v1/klines?interval=1m&limit=N} (nến mới nhất) cho symbol đầy đủ (BTCUSDT). Lỗi ⇒ ném exception. */
    public interface RestFetcher {
        List<Bar> fetch(String symbol, int limit) throws Exception;
    }

    /** Một nến 1m (openTime ms) đã parse sang proto float32. */
    public static final class Bar {
        public final long openTime;
        public final KlineObjectOptimized k;

        public Bar(long openTime, KlineObjectOptimized k) {
            this.openTime = openTime;
            this.k = k;
        }
    }

    /** Kết quả REST sớm: nến M đã ghi + nến phút đang mở (để seed bộ nặn như V8.1) + symbol lỗi. */
    public static final class EarlyResult {
        public final Map<String, KlineObjectOptimized> closed = new HashMap<>();
        public final Map<String, KlineObjectOptimized> open = new HashMap<>();
        public final List<String> failed = new ArrayList<>();
    }

    /** Kết quả một pass settle. */
    public static final class SettleResult {
        public int fetched, failed, rewrittenDiff, filledMissing, same, immature;
        public final List<String> failedSymbols = new ArrayList<>();
        public final Map<Long, Integer> diffByMinute = new TreeMap<>();
    }

    private final MinuteStore store;
    private final RestFetcher rest;
    private final ExecutorService pool;
    private final int retries;
    private final long retryBackoffMs;
    private final long settleMinAgeMs;
    private final long fetchTimeoutMs;

    private final Object writeLock = new Object();
    private volatile long finalizedThrough = Long.MIN_VALUE;
    /** WS final chưa ghi: minute -> shortSym -> nến. */
    private final ConcurrentHashMap<Long, ConcurrentHashMap<String, KlineObjectOptimized>> wsPending = new ConcurrentHashMap<>();
    /** Symbol (ngắn) đã có WS final theo phút (để biết ai THIẾU). */
    private final ConcurrentHashMap<Long, Set<String>> wsSeen = new ConcurrentHashMap<>();
    /** Phút đã flush WS (final tới muộn hơn ⇒ ghi ngay ở flushLate, đếm ws_late). */
    private final Set<Long> wsFlushed = ConcurrentHashMap.newKeySet();

    // ---- counters (cộng dồn từ khi start; snapshot định kỳ ở statsLine) ----
    final AtomicLong cWsFinal = new AtomicLong(), cWsLate = new AtomicLong();
    final AtomicLong cEarlyFetched = new AtomicLong(), cEarlyFailed = new AtomicLong();
    final AtomicLong cSettleFetched = new AtomicLong(), cSettleFailed = new AtomicLong();
    final AtomicLong cRewrittenDiff = new AtomicLong(), cFilledMissing = new AtomicLong(), cSame = new AtomicLong();
    final AtomicLong cOpenBlocked = new AtomicLong();
    private long[] lastSnap = new long[10];

    public KlineIngestCore(MinuteStore store, RestFetcher rest, ExecutorService pool, int retries,
                           long retryBackoffMs, long settleMinAgeMs, long fetchTimeoutMs) {
        this.store = store;
        this.rest = rest;
        this.pool = pool;
        this.retries = Math.max(1, retries);
        this.retryBackoffMs = Math.max(0, retryBackoffMs);
        this.settleMinAgeMs = Math.max(0, settleMinAgeMs);
        this.fetchTimeoutMs = fetchTimeoutMs;
    }

    public static String shortSym(String fullSym) {
        return fullSym.endsWith("USDT") ? fullSym.substring(0, fullSym.length() - 4) : fullSym;
    }

    /** So khớp bit float32 cả 5 trường (O/H/L/C/totalUsdt). */
    public static boolean sameBits(KlineObjectOptimized a, KlineObjectOptimized b) {
        if (a == null || b == null) return a == b;
        return Float.floatToIntBits(a.getPriceOpen()) == Float.floatToIntBits(b.getPriceOpen())
                && Float.floatToIntBits(a.getMaxPrice()) == Float.floatToIntBits(b.getMaxPrice())
                && Float.floatToIntBits(a.getMinPrice()) == Float.floatToIntBits(b.getMinPrice())
                && Float.floatToIntBits(a.getPriceClose()) == Float.floatToIntBits(b.getPriceClose())
                && Float.floatToIntBits(a.getTotalUsdt()) == Float.floatToIntBits(b.getTotalUsdt());
    }

    public long finalizedThrough() {
        return finalizedThrough;
    }

    /** Ghi nến ĐÃ ĐÓNG của phút {@code minute} (merge theo symbol trong store) và đánh dấu phút đã chốt. */
    void writeClosed(long minute, Map<String, KlineObjectOptimized> candles) {
        if (candles == null || candles.isEmpty()) return;
        synchronized (writeLock) {
            if (minute > finalizedThrough) finalizedThrough = minute;
            store.write(minute, new HashMap<>(candles));
        }
    }

    /**
     * Ghi nến phút ĐANG MỞ (nặn realtime). Trả false (không ghi) nếu phút đó đã chốt — chặn ghi đè nến đóng
     * bởi vòng ticker/price lỡ nhịp qua ranh phút.
     */
    public boolean writeOpenMinute(long minute, Map<String, KlineObjectOptimized> candles) {
        synchronized (writeLock) {
            if (minute <= finalizedThrough) {
                cOpenBlocked.incrementAndGet();
                return false;
            }
            store.write(minute, new HashMap<>(candles));
            return true;
        }
    }

    // ------------------------------- WS final -------------------------------

    /** Sự kiện WS {@code x=true} của nến {@code openTime}. Thread-safe (gọi từ luồng okhttp). */
    public void onWsFinal(String fullSym, long openTime, KlineObjectOptimized k) {
        String s = shortSym(fullSym);
        wsPending.computeIfAbsent(openTime, m -> new ConcurrentHashMap<>()).put(s, k);
        wsSeen.computeIfAbsent(openTime, m -> ConcurrentHashMap.newKeySet()).add(s);
        cWsFinal.incrementAndGet();
    }

    /** Ghi mọi WS final đang chờ của phút {@code minute} (lần đầu cho phút này). Trả số nến ghi. */
    public int flushWsFinals(long minute) {
        wsFlushed.add(minute);
        ConcurrentHashMap<String, KlineObjectOptimized> m = wsPending.remove(minute);
        if (m == null || m.isEmpty()) return 0;
        writeClosed(minute, m);
        return m.size();
    }

    /** WS final tới SAU khi phút đã flush ⇒ ghi ngay (đè cả bản REST sớm chưa settle). Trả số nến ghi. */
    public int flushLateFinals() {
        int n = 0;
        for (Long minute : new ArrayList<>(wsPending.keySet())) {
            if (!wsFlushed.contains(minute)) continue;
            ConcurrentHashMap<String, KlineObjectOptimized> m = wsPending.remove(minute);
            if (m == null || m.isEmpty()) continue;
            writeClosed(minute, m);
            cWsLate.addAndGet(m.size());
            n += m.size();
        }
        return n;
    }

    /** Symbol (đầy đủ) trong {@code fullSyms} CHƯA có WS final cho phút {@code minute}. */
    public List<String> missingFinals(long minute, Collection<String> fullSyms) {
        Set<String> seen = wsSeen.get(minute);
        List<String> out = new ArrayList<>();
        for (String s : fullSyms) {
            if (seen == null || !seen.contains(shortSym(s))) out.add(s);
        }
        return out;
    }

    /** Dọn state WS cũ hơn {@code keepFromMinute}. */
    public void gc(long keepFromMinute) {
        wsSeen.keySet().removeIf(m -> m < keepFromMinute);
        wsFlushed.removeIf(m -> m < keepFromMinute);
        for (Long m : new ArrayList<>(wsPending.keySet())) {
            if (m < keepFromMinute) {
                ConcurrentHashMap<String, KlineObjectOptimized> left = wsPending.remove(m);
                if (left != null && !left.isEmpty()) {
                    LOG.warn("[KLINE-INGEST] bo {} WS final cua phut {} chua ghi (qua cu)", left.size(), m);
                }
            }
        }
    }

    // ------------------------------- REST -------------------------------

    /** Gọi REST có retry; null nếu hết lượt (đã log WARN lần cuối). */
    List<Bar> fetchWithRetry(String sym, int limit) {
        Exception last = null;
        for (int i = 0; i < retries; i++) {
            try {
                List<Bar> b = rest.fetch(sym, limit);
                if (b != null) return b;
                last = new IllegalStateException("empty response");
            } catch (Exception e) {
                last = e;
            }
            if (i + 1 < retries && retryBackoffMs > 0) {
                try {
                    Thread.sleep(retryBackoffMs);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        }
        LOG.warn("[KLINE-INGEST] fetch {} limit={} loi sau {} lan: {}", sym, limit, retries, last == null ? "?" : last.toString());
        return null;
    }

    /** Song song trên pool; symbol lỗi/timeout ⇒ value null. */
    Map<String, List<Bar>> fetchAll(Collection<String> syms, int limit) {
        Map<String, Future<List<Bar>>> fs = new HashMap<>();
        for (String s : syms) fs.put(s, pool.submit(() -> fetchWithRetry(s, limit)));
        Map<String, List<Bar>> out = new HashMap<>();
        long deadline = System.currentTimeMillis() + fetchTimeoutMs;
        for (Map.Entry<String, Future<List<Bar>>> e : fs.entrySet()) {
            List<Bar> r = null;
            try {
                long left = Math.max(1, deadline - System.currentTimeMillis());
                r = e.getValue().get(left, TimeUnit.MILLISECONDS);
            } catch (Exception ex) {
                e.getValue().cancel(true);
                LOG.warn("[KLINE-INGEST] fetch {} timeout/loi: {}", e.getKey(), ex.toString());
            }
            out.put(e.getKey(), r);
        }
        return out;
    }

    /**
     * REST sớm cho phút vừa đóng {@code minute}: ghi nến M (có thể chưa settle — pass settle sẽ kiểm lại) và trả nến
     * phút đang mở (M+1) để seed bộ nặn. WS final tới sau sẽ đè (flushLateFinals).
     */
    public EarlyResult earlyRest(long minute, Collection<String> fullSyms) {
        EarlyResult r = new EarlyResult();
        if (fullSyms.isEmpty()) return r;
        Map<String, List<Bar>> got = fetchAll(fullSyms, 2);
        for (Map.Entry<String, List<Bar>> e : got.entrySet()) {
            String s = shortSym(e.getKey());
            if (e.getValue() == null) {
                r.failed.add(e.getKey());
                continue;
            }
            boolean hit = false;
            for (Bar b : e.getValue()) {
                if (b.openTime == minute) {
                    r.closed.put(s, b.k);
                    hit = true;
                } else if (b.openTime == minute + MIN) {
                    r.open.put(s, b.k);
                }
            }
            if (!hit) r.failed.add(e.getKey());   // phần tử trả thiếu nến M
        }
        // WS final đã tới trong lúc fetch thì KHÔNG đè bằng REST sớm (WS final là bản cuối của sàn).
        Set<String> seen = wsSeen.get(minute);
        if (seen != null) r.closed.keySet().removeAll(seen);
        writeClosed(minute, r.closed);
        cEarlyFetched.addAndGet(got.size() - r.failed.size());
        cEarlyFailed.addAndGet(r.failed.size());
        if (!r.failed.isEmpty()) {
            LOG.warn("[KLINE-INGEST] REST som phut {}: {} symbol loi/thieu nen (vd {}) — pass settle se ghi lai",
                    minute, r.failed.size(), r.failed.subList(0, Math.min(5, r.failed.size())));
        }
        return r;
    }

    /**
     * Pass settle: REST limit={@code limit} cho mọi symbol; với mỗi nến ĐÃ ĐÓNG đủ lâu
     * ({@code openTime + 1' <= nowMs - settleMinAgeMs}) so với store, khác ⇒ ghi đè, thiếu ⇒ ghi.
     * Nến chưa đủ tuổi / phút đang mở: KHÔNG ghi (đếm immature).
     */
    public SettleResult settle(long nowMs, Collection<String> fullSyms, int limit) {
        SettleResult res = new SettleResult();
        if (fullSyms.isEmpty()) return res;
        Map<String, List<Bar>> got = fetchAll(fullSyms, Math.max(2, limit));
        Map<Long, Map<String, KlineObjectOptimized>> byMinute = new TreeMap<>();
        for (Map.Entry<String, List<Bar>> e : got.entrySet()) {
            if (e.getValue() == null) {
                res.failed++;
                res.failedSymbols.add(e.getKey());
                continue;
            }
            res.fetched++;
            for (Bar b : e.getValue()) {
                if (b.openTime + MIN > nowMs - settleMinAgeMs) {
                    res.immature++;
                    continue;
                }
                byMinute.computeIfAbsent(b.openTime, m -> new HashMap<>()).put(shortSym(e.getKey()), b.k);
            }
        }
        for (Map.Entry<Long, Map<String, KlineObjectOptimized>> e : byMinute.entrySet()) {
            long minute = e.getKey();
            Map<String, KlineObjectOptimized> existing = store.read(minute);
            Map<String, KlineObjectOptimized> diff = new HashMap<>();
            int nd = 0;
            for (Map.Entry<String, KlineObjectOptimized> k : e.getValue().entrySet()) {
                KlineObjectOptimized old = existing == null ? null : existing.get(k.getKey());
                if (old == null) {
                    diff.put(k.getKey(), k.getValue());
                    res.filledMissing++;
                } else if (!sameBits(old, k.getValue())) {
                    diff.put(k.getKey(), k.getValue());
                    res.rewrittenDiff++;
                    nd++;
                } else {
                    res.same++;
                }
            }
            if (!diff.isEmpty()) writeClosed(minute, diff);
            res.diffByMinute.put(minute, nd);
        }
        cSettleFetched.addAndGet(res.fetched);
        cSettleFailed.addAndGet(res.failed);
        cRewrittenDiff.addAndGet(res.rewrittenDiff);
        cFilledMissing.addAndGet(res.filledMissing);
        cSame.addAndGet(res.same);
        if (res.failed > 0) {
            LOG.warn("[KLINE-INGEST] settle: {} symbol fetch loi (vd {}) — pass phut sau (limit={}) se kiem lai",
                    res.failed, res.failedSymbols.subList(0, Math.min(5, res.failedSymbols.size())), limit);
        }
        return res;
    }

    /** Dòng thống kê định kỳ: cộng dồn + delta kể từ lần gọi trước. */
    public synchronized String statsLine() {
        long[] cur = {cWsFinal.get(), cWsLate.get(), cEarlyFetched.get(), cEarlyFailed.get(), cSettleFetched.get(),
                cSettleFailed.get(), cRewrittenDiff.get(), cFilledMissing.get(), cSame.get(), cOpenBlocked.get()};
        String[] names = {"ws_final", "ws_late", "early_fetched", "early_failed", "fetched", "failed",
                "rewritten_diff", "filled_missing", "same", "open_write_blocked"};
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < cur.length; i++) {
            sb.append(names[i]).append('=').append(cur[i]).append("(+").append(cur[i] - lastSnap[i]).append(") ");
        }
        lastSnap = cur;
        return sb.toString().trim();
    }
}
