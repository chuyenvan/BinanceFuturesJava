package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * LIVE — đọc 5 OI feature (#41..#45) ĐÃ TÍNH SẴN trên Oracle ({@code ComputeOiFeat2Live242}) từ
 * Aerospike-242 ({@link OiFeatLiveSets}), lookup merge_asof BACKWARD 2h. ZERO compute trên bot.
 *
 * <p>[B4-SPEED 2026-09-29] Trước đây: {@link #clear()} ĐẦU MỖI TICK ⇒ mỗi tick {@link #lookup}
 * gọi {@code load()} TUẦN TỰ 5×{@code getMetricMap242} (FULL history ~30k điểm ~81 chunk-tháng/coin)
 * ⇒ ~3250 round-trip lớn qua WAN/lượt ⇒ ~250s/lượt. Nay: BatchRead 1 lần + chỉ chunk-tháng gần (24h) +
 * cache qua tick.
 *
 * <p>[B6-SPEED-V3 2026-09-29] Trước đây {@link #beginTick} reload ĐỒNG BỘ khi {@code pipelineFreshTs}
 * tăng (~30s/giờ) ⇒ chặn tick. Nay <b>double-buffer</b>: {@code volatile Snapshot} (data + freshTs) đọc
 * qua tham chiếu nguyên tử; thread nền tải buffer MỚI rồi swap nguyên tử — tick KHÔNG chặn. Độ trễ tối
 * đa so bản cũ = thời gian reload nền (~30s, 1 lần/giờ); OI merge_asof 2h + cadence OI 60' ⇒ vô hại.
 * Cold-start (lần đầu) VẪN load đồng bộ 1 lần (y hệt bản cũ).
 *
 * <p>[FIX-OOM-OI 2026-09-30] <b>R4 1' shadow OOM (45×/2h)</b> — nguyên nhân gốc:
 * <ol>
 *   <li><b>Reader KHÔNG cắt cửa sổ 24h</b>: hằng {@code CACHE_WINDOW_MS} chỉ giới hạn <i>số chunk-THÁNG</i>
 *       đọc, KHÔNG cắt phần tử. Chunk-tháng {@code SYMBOL_yyyyMM} được writer MERGE-tích-luỹ
 *       ({@code writeMonthChunk}) nên chứa ~CẢ THÁNG (~8640 điểm 5m/set), không phải 288 điểm/24h
 *       ⇒ RAM OI ≈ 653 coin × 5 set × ~8640 ≈ <b>28M entry ≈ 2,2–2,5 GB</b> (gấp ~30× ý định 24h).</li>
 *   <li><b>Double-buffer dựng map MỚI cho TOÀN BỘ knownCoins trong khi map CŨ vẫn sống</b>
 *       (⇒ đỉnh ≈ 2× steady ≈ <b>4,4–5 GB</b>) vượt {@code -Xmx4g} ⇒ {@code OutOfMemoryError}.</li>
 *   <li><b>Retry-storm</b>: OOM bị bắt trong thread nền ⇒ swap không commit ⇒ {@code freshTs} đứng yên ⇒
 *       {@code stale=true} mãi ⇒ thử lại mỗi 10s, mỗi lần lại cấp phát ~2 GB ⇒ GC thrash kéo dài 2h,
 *       {@code [GATE]} chỉ chạy ~44/145 phút (~30%).</li>
 * </ol>
 * Fix (mode MỚI {@code OI_LIVE_REFRESH_MODE=inplace}; default {@code legacy} = byte-identical bản cũ):
 * (1) nạp TĂNG DẦN từng lô 64 coin vào CHÍNH map đang sống (không copy toàn map);
 * (2) CẮT mỗi TreeMap về [now-24h, ∞) ngay khi decode ⇒ steady ≈ 940k entry ≈ ~85 MB;
 * (3) {@code knownCoins} có bound (grace-tick + trần 1500 coin);
 * (4) backoff sau lỗi ⇒ không retry-storm.
 * Nguồn LOCAL Oracle (226): writer {@code ComputeOiFeat2Live242.writeFeatures} chỉ ghi
 * {@code writeMetricMap242} (242), KHÔNG mirror về 226 ⇒ feature oi_feat_* CHỈ có trên 242 ⇒ không áp
 * "ưu tiên 226".
 */
public class LiveOiFeatProvider {

    private static final Logger LOG = LoggerFactory.getLogger(LiveOiFeatProvider.class);

    private static final long CACHE_WINDOW_MS = 24L * 60L * 60_000L;
    /** Biên an toàn thêm 1h khi đọc chunk-tháng để không bao giờ thiếu đầu cửa sổ 24h. */
    private static final long READ_MARGIN_MS = 1L * 60L * 60_000L;

    private static final String[] OI_SETS = {
            OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.OI_Z, OiFeatLiveSets.LS_GLOBAL,
            OiFeatLiveSets.LS_TOPTRADER, OiFeatLiveSets.TAKER_BUY
    };

    // ---------------------------------------------------------------------
    // [FIX-OOM-OI] Knob. Base = HÀNH VI HIỆN TẠI (legacy) để parity tuyệt đối.
    // ---------------------------------------------------------------------
    /** {@code legacy} (default) = double-buffer như cũ; {@code inplace} = nạp tăng dần + cắt 24h + bound. */
    private static final String REFRESH_MODE = envOr("OI_LIVE_REFRESH_MODE", "legacy");
    private static final boolean INPLACE = isInplaceMode(REFRESH_MODE);
    /** inplace: số coin/lô khi nạp (giới hạn đỉnh tạm thời). */
    private static final int SYM_CHUNK = envInt("OI_LIVE_SYM_CHUNK", 64);
    /** inplace: trần cứng số coin giữ trong RAM. */
    private static final int MAX_COINS = envInt("OI_LIVE_MAX_COINS", 1500);
    /** inplace: số tick vắng mặt (không có trong universe) trước khi bỏ coin. */
    private static final int EVICT_GRACE_TICKS = envInt("OI_LIVE_EVICT_GRACE_TICKS", 120);
    /** inplace: backoff sau 1 lần reload lỗi (ms) — chặn retry-storm khi OOM. */
    private static final long FAIL_BACKOFF_MS = envLong("OI_LIVE_FAIL_BACKOFF_MS", 60_000L);

    private static String envOr(String k, String d) {
        String v = System.getenv(k);
        return (v == null || v.trim().isEmpty()) ? d : v.trim();
    }

    private static int envInt(String k, int d) {
        try {
            return Integer.parseInt(envOr(k, String.valueOf(d)));
        } catch (NumberFormatException e) {
            return d;
        }
    }

    private static long envLong(String k, long d) {
        try {
            return Long.parseLong(envOr(k, String.valueOf(d)));
        } catch (NumberFormatException e) {
            return d;
        }
    }

    /** Thuần hàm: {@code inplace} (case/space-insensitive). Default & mọi giá trị khác = legacy. */
    static boolean isInplaceMode(String mode) {
        return mode != null && "inplace".equalsIgnoreCase(mode.trim());
    }

    /** Chế độ đang chạy (test/audit). */
    static String refreshMode() {
        return REFRESH_MODE;
    }

    /** Snapshot bất biến: data OI + freshTs tại lần nạp. Swap nguyên tử qua {@code volatile}. */
    private static final class Snapshot {
        final Map<String, TreeMap<Long, Float>[]> data;
        final long freshTs;

        Snapshot(Map<String, TreeMap<Long, Float>[]> data, long freshTs) {
            this.data = data;
            this.freshTs = freshTs;
        }
    }

    /** Buffer hiện hành (đọc qua tham chiếu nguyên tử — lookup không chặn). */
    private volatile Snapshot current = new Snapshot(new ConcurrentHashMap<>(), 0L);

    /** Các coin đã từng thấy (để thread nền biết cần đọc lại coin nào). */
    private final Set<String> knownCoins = ConcurrentHashMap.newKeySet();

    /** [FIX-OOM-OI] Chỉ dùng ở mode inplace: tick gần nhất coin xuất hiện trong universe. */
    private final Map<String, Long> lastSeenTick = new ConcurrentHashMap<>();
    private final AtomicLong tickSeq = new AtomicLong();

    /** [FIX-OOM-OI] Chỉ dùng ở mode inplace: mốc thời gian sớm nhất được phép thử lại reload. */
    private volatile long nextAttemptAfterMs = 0L;

    /** Khoá tuần tự reload (thread nền + cold-start KHÔNG chạy đè). */
    private final Object reloadLock = new Object();

    private final ScheduledExecutorService bg = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "LiveOiFeatRefresh");
        t.setDaemon(true);
        return t;
    });
    private volatile boolean bgStarted = false;

    /**
     * Gọi ĐẦU MỖI TICK (trước mọi {@link #lookup}), truyền universe cần predict. Đăng ký universe +
     * khởi động nền. Cold-start (chưa từng load) thì load đồng bộ 1 lần; về sau KHÔNG chặn tick (reload
     * nền double-buffer).
     */
    public void beginTick(Collection<String> universe) {
        startBgIfNeeded();
        if (universe != null) {
            knownCoins.addAll(universe);
            if (INPLACE) {
                long seq = tickSeq.incrementAndGet();
                for (String c : universe) lastSeenTick.put(c, seq);
            }
        }
        if (current.freshTs == 0L && !knownCoins.isEmpty()) {
            synchronized (reloadLock) {
                if (current.freshTs == 0L) {
                    if (INPLACE) reloadNowInplace();
                    else reloadNow(true);
                }
            }
        }
    }

    /** Khởi động thread refresh nền 1 lần duy nhất (prefetch giữa các tick). */
    private void startBgIfNeeded() {
        if (bgStarted) return;
        synchronized (this) {
            if (bgStarted) return;
            bg.scheduleWithFixedDelay(this::reloadInBackground, 10, 10, TimeUnit.SECONDS);
            bgStarted = true;
        }
    }

    /** Thread nền: nếu pipelineFreshTs tăng (data mới) HOẶC còn coin thiếu ⇒ tải buffer MỚI + swap. */
    private void reloadInBackground() {
        try {
            if (INPLACE && System.currentTimeMillis() < nextAttemptAfterMs) return;
            Snapshot cur = current;
            long fresh = pipelineFreshTs();
            boolean stale = fresh > cur.freshTs;
            boolean hasMissing = false;
            for (String c : knownCoins) if (!cur.data.containsKey(c)) { hasMissing = true; break; }
            if (!stale && !hasMissing) return;
            synchronized (reloadLock) {
                if (INPLACE) {
                    reloadLockedInplace();
                } else {
                    cur = current;
                    fresh = pipelineFreshTs();
                    stale = fresh > cur.freshTs;
                    reloadLocked(stale);
                }
            }
        } catch (Throwable t) {
            if (INPLACE) nextAttemptAfterMs = System.currentTimeMillis() + FAIL_BACKOFF_MS;
            LOG.error("[OI-LIVE] reload nền lỗi: {}", t.toString());
        }
    }

    // =====================================================================
    // LEGACY (default) — double-buffer y hệt bản B6, KHÔNG đụng vào.
    // =====================================================================

    /** Load đồng bộ (chỉ gọi trong reloadLock). Khi stale: nạp lại TOÀN BỘ knownCoins; nếu không: nạp coin thiếu. */
    private void reloadLocked(boolean stale) {
        Snapshot cur = current;
        Set<String> toLoad;
        long fresh = pipelineFreshTs();
        if (stale) {
            toLoad = new HashSet<>(knownCoins);
        } else {
            toLoad = new HashSet<>();
            for (String c : knownCoins) if (!cur.data.containsKey(c)) toLoad.add(c);
            if (toLoad.isEmpty()) return;
        }
        long since = System.currentTimeMillis() - CACHE_WINDOW_MS - READ_MARGIN_MS;
        Map<String, TreeMap<Long, Float>[]> loaded =
                DataManagerAerospikeFloatSim.getMetricMap242RecentBatch(toLoad, OI_SETS, OiFeatLiveSets.BIN, since);
        long newFresh = stale ? fresh : cur.freshTs;
        Map<String, TreeMap<Long, Float>[]> newData = new ConcurrentHashMap<>(stale ? loaded : cur.data);
        if (!stale) newData.putAll(loaded);
        current = new Snapshot(newData, newFresh);
        LOG.info("[OI-LIVE] swap buffer {} coin (since={}) tai freshTs={} (stale={})", newData.size(), since, newFresh, stale);
    }

    /** Cold-start đồng bộ (chỉ gọi trong reloadLock): nạp toàn bộ knownCoins + swap. */
    private void reloadNow(boolean stale) {
        Set<String> toLoad = new HashSet<>(knownCoins);
        if (toLoad.isEmpty()) return;
        long since = System.currentTimeMillis() - CACHE_WINDOW_MS - READ_MARGIN_MS;
        long fresh = pipelineFreshTs();
        Map<String, TreeMap<Long, Float>[]> loaded =
                DataManagerAerospikeFloatSim.getMetricMap242RecentBatch(toLoad, OI_SETS, OiFeatLiveSets.BIN, since);
        current = new Snapshot(new ConcurrentHashMap<>(loaded), fresh);
        LOG.info("[OI-LIVE] cold-load {} coin (since={}) tai freshTs={}", loaded.size(), since, fresh);
    }

    // =====================================================================
    // INPLACE (opt-in) — nạp tăng dần, cắt 24h, bound RAM.
    // =====================================================================

    /** [FIX-OOM-OI] Cold-start inplace: nạp toàn bộ knownCoins theo lô vào 1 map mới. */
    private void reloadNowInplace() {
        Set<String> toLoad = new HashSet<>(knownCoins);
        if (toLoad.isEmpty()) return;
        long now = System.currentTimeMillis();
        long since = now - CACHE_WINDOW_MS - READ_MARGIN_MS;
        long keepFrom = now - CACHE_WINDOW_MS;
        long fresh = pipelineFreshTs();
        Map<String, TreeMap<Long, Float>[]> data = new ConcurrentHashMap<>();
        DataManagerAerospikeFloatSim.getMetricMap242RecentBatchInto(
                toLoad, OI_SETS, OiFeatLiveSets.BIN, since, keepFrom, SYM_CHUNK, data::put);
        current = new Snapshot(data, fresh);
        LOG.info("[OI-LIVE] inplace cold-load {} coin (since={}, keep={}) tai freshTs={}", data.size(), since, keepFrom, fresh);
    }

    /**
     * [FIX-OOM-OI] Reload inplace: nạp từng lô coin vào CHÍNH map đang sống ({@code current.data}) —
     * KHÔNG bao giờ dựng bản sao toàn map ⇒ đỉnh ≈ steady + 1 lô. Data cũ của coin được thay tại thời
     * điểm {@code put} (ConcurrentHashMap atomic).
     */
    private void reloadLockedInplace() {
        Map<String, TreeMap<Long, Float>[]> target = current.data;
        long fresh = pipelineFreshTs();
        boolean stale = fresh > current.freshTs;
        Set<String> toLoad = new LinkedHashSet<>();
        for (String c : knownCoins) if (stale || !target.containsKey(c)) toLoad.add(c);
        if (toLoad.isEmpty()) return;
        long now = System.currentTimeMillis();
        long since = now - CACHE_WINDOW_MS - READ_MARGIN_MS;
        long keepFrom = now - CACHE_WINDOW_MS;
        int[] pushed = {0};
        DataManagerAerospikeFloatSim.getMetricMap242RecentBatchInto(
                toLoad, OI_SETS, OiFeatLiveSets.BIN, since, keepFrom, SYM_CHUNK,
                (sym, arr) -> { target.put(sym, arr); pushed[0]++; });
        if (stale) current = new Snapshot(target, fresh);
        int evicted = pruneInplace(target);
        LOG.info("[OI-LIVE] inplace refresh {} coin (since={}, keep={}) tai freshTs={} (stale={}) size={} evicted={}",
                pushed[0], since, keepFrom, fresh, stale, target.size(), evicted);
    }

    /** Bỏ coin khỏi knownCoins/lastSeenTick/data theo {@link #coinsToEvict}. Trả số coin bỏ. */
    private int pruneInplace(Map<String, TreeMap<Long, Float>[]> data) {
        Set<String> drop = coinsToEvict(knownCoins, lastSeenTick, tickSeq.get(), EVICT_GRACE_TICKS, MAX_COINS);
        for (String c : drop) {
            knownCoins.remove(c);
            lastSeenTick.remove(c);
            data.remove(c);
        }
        return drop.size();
    }

    /**
     * [FIX-OOM-OI] Thuần hàm: coin cần bỏ = (a) vắng &gt; {@code graceTicks} tick, (b) phần dư khi vượt
     * {@code maxCoins} (bỏ coin lâu không thấy nhất trước). Bound RAM theo lịch sử universe.
     */
    static Set<String> coinsToEvict(Set<String> known, Map<String, Long> lastSeen,
                                    long nowSeq, int graceTicks, int maxCoins) {
        Set<String> drop = new HashSet<>();
        if (known == null || known.isEmpty()) return drop;
        for (String c : known) {
            Long seen = lastSeen == null ? null : lastSeen.get(c);
            if (seen != null && (nowSeq - seen) > graceTicks) drop.add(c);
        }
        int remain = known.size() - drop.size();
        if (maxCoins > 0 && remain > maxCoins) {
            List<String> alive = new ArrayList<>();
            for (String c : known) if (!drop.contains(c)) alive.add(c);
            alive.sort(Comparator.comparingLong(c -> lastSeen == null ? 0L : lastSeen.getOrDefault(c, 0L)));
            int extra = remain - maxCoins;
            for (int i = 0; i < extra && i < alive.size(); i++) drop.add(alive.get(i));
        }
        return drop;
    }

    /**
     * [oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuy] tại t (merge_asof backward 2h). Cả 5 set
     * cùng tập ts → dùng 1 mốc ref (oiZ, fallback delta) rồi đọc cả 5 tại mốc đó → nhất quán.
     */
    public float[] lookup(String coin, long t) {
        TreeMap<Long, Float>[] a = current.data.get(coin);
        if (a == null) {
            // cold-start ngoài beginTick (ít khi): nạp 1 coin batch.
            long since = System.currentTimeMillis() - CACHE_WINDOW_MS - READ_MARGIN_MS;
            a = DataManagerAerospikeFloatSim.getMetricMap242RecentBatch(
                    java.util.Collections.singletonList(coin), OI_SETS, OiFeatLiveSets.BIN, since).get(coin);
            if (a == null) a = emptyArr();
            // [FIX-OOM-OI] ở legacy giữ nguyên; ở inplace chỉ cache khi chưa chạm trần (bound RAM).
            if (!INPLACE || current.data.size() < MAX_COINS) {
                TreeMap<Long, Float>[] prev = current.data.putIfAbsent(coin, a);
                if (prev != null) a = prev;
                knownCoins.add(coin);
            }
        }
        Long ref = floorKeyTol(a[1], t);
        if (ref == null) ref = floorKeyTol(a[0], t);
        if (ref == null) return nan5();
        return new float[]{val(a[0], ref), val(a[1], ref), val(a[2], ref), val(a[3], ref), val(a[4], ref)};
    }

    /**
     * [B4-SPEED] Giữ API (caller cũ gọi {@code clear()} đầu mỗi tick) nhưng thành NO-OP: cache giữ qua
     * tick, refresh do {@link #beginTick(Collection)} / thread nền. Không xoá cache.
     */
    public void clear() {
        // NO-OP by design — xem javadoc class.
    }

    /**
     * [OI-GUARD-2] Tuoi pipeline oi_feat: ts moi nhat (lastKey OI_Z) cua coin tham chieu (BTC/ETH) tren 242.
     * [B4-SPEED] Đọc CHỈ chunk-tháng gần (24h) — lastKey y hệt full-history. ĐỌC THẬT từ 242 (KHÔNG qua cache)
     * để guard OI_STALE_HALT vẫn chính xác. Tra 0 neu ca hai deu chua co (cold-start).
     */
    public long pipelineFreshTs() {
        long now = System.currentTimeMillis();
        long since = now - CACHE_WINDOW_MS - READ_MARGIN_MS;
        long best = 0L;
        for (String c : new String[]{"BTCUSDT", "ETHUSDT"}) {
            TreeMap<Long, Float> z = DataManagerAerospikeFloatSim.getMetricMap242Recent(
                    OiFeatLiveSets.OI_Z, OiFeatLiveSets.BIN, c, since);
            if (z != null && !z.isEmpty()) best = Math.max(best, z.lastKey());
        }
        return best;
    }

    // ---------------------------------------------------------------------
    // [TEST-ONLY] seam cho unit test (không cần Aerospike).
    // ---------------------------------------------------------------------

    /** [TEST-ONLY] Nạp dữ liệu tổng hợp để kiểm parity lookup. */
    void testSeed(Map<String, TreeMap<Long, Float>[]> data, long freshTs) {
        this.current = new Snapshot(data, freshTs);
    }

    /** [TEST-ONLY] Trần coin hiệu dụng (audit/bench). */
    static int maxCoins() {
        return MAX_COINS;
    }

    @SuppressWarnings("unchecked")
    private static TreeMap<Long, Float>[] emptyArr() {
        return new TreeMap[]{new TreeMap<>(), new TreeMap<>(), new TreeMap<>(), new TreeMap<>(), new TreeMap<>()};
    }

    private static Long floorKeyTol(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Long k = m.floorKey(t);
        if (k == null || (t - k) > OiFeatLiveSets.MERGE_TOL_MS) return null;
        return k;
    }

    private static float val(TreeMap<Long, Float> m, long ts) {
        if (m == null) return Float.NaN;
        Float v = m.get(ts);
        return v == null ? Float.NaN : v;
    }

    private static float[] nan5() {
        return new float[]{Float.NaN, Float.NaN, Float.NaN, Float.NaN, Float.NaN};
    }
}
