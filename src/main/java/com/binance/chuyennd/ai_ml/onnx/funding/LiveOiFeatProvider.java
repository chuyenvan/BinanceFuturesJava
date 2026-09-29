package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * LIVE — đọc 5 OI feature (#41..#45) ĐÃ TÍNH SẴN trên Oracle ({@code ComputeOiFeat2Live242}) từ
 * Aerospike-242 ({@link OiFeatLiveSets}), lookup merge_asof BACKWARD 2h. ZERO compute trên bot.
 *
 * <p>[B4-SPEED 2026-09-29] Trước đây: {@link #clear()} ĐẦU MỖI TICK ⇒ mỗi tick {@link #lookup}
 * gọi {@code load()} TUẦN TỰ 5×{@code getMetricMap242} (FULL history ~30k điểm ~81 chunk-tháng/coin)
 * ⇒ ~3250 round-trip lớn qua WAN/lượt ⇒ ~250s/lượt. Nay:
 * <ul>
 *   <li><b>BatchRead 1 lần cho mọi coin</b> ({@code getMetricMap242RecentBatch}) — ~650 coin × 5 set
 *       chỉ vài round-trip (thay vì ~3250).</li>
 *   <li><b>Chỉ đọc chunk-tháng gần</b> (24h) — lookup chỉ cần floorKey trong 2h ⇒ BIT-IDENTICAL.</li>
 *   <li><b>Cache giữ qua tick</b> (không clear mỗi tick) — dữ liệu chỉ đổi khi {@code pipelineFreshTs}
 *       tăng (cadence ~60'). Refresh nền + guard đồng bộ trong {@link #beginTick(Collection)}.</li>
 * </ul>
 *
 * <p>Nguồn LOCAL Oracle (226): đã kiểm tra writer {@code ComputeOiFeat2Live242.writeFeatures} — chỉ ghi
 * {@code writeMetricMap242} (242), KHÔNG mirror về 226 ⇒ feature oi_feat_* CHỈ có trên 242 ⇒ không áp
 * "ưu tiên 226" (raw OI có trên 226 nhưng feature đã-tính thì không; live KHÔNG tự tính).
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

    /** Cache per-coin QUA TICK. Chỉ reload khi pipelineFreshTs tăng. */
    private final Map<String, TreeMap<Long, Float>[]> cache = new ConcurrentHashMap<>();
    /** Các coin đã từng load (để refresh nền biết cần đọc lại coin nào). */
    private final Set<String> knownCoins = ConcurrentHashMap.newKeySet();

    /** pipelineFreshTs tại lần reload gần nhất. 0 = chưa load. */
    private volatile long loadedFreshTs = 0L;

    /** Khoá tuần tự reload (refresh nền + guard tick KHÔNG chạy đè). */
    private final Object reloadLock = new Object();

    private final ScheduledExecutorService bg = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "LiveOiFeatRefresh");
        t.setDaemon(true);
        return t;
    });
    private volatile boolean bgStarted = false;

    /**
     * Gọi ĐẦU MỖI TICK (trước mọi {@link #lookup}), truyền universe cần predict. Đảm bảo cache đầy đủ +
     * đúng mới nhất: nạp symbol còn thiếu (batch) + reload NGAY (đồng bộ) nếu pipelineFreshTs tăng.
     */
    public void beginTick(Collection<String> universe) {
        startBgIfNeeded();
        if (universe != null) knownCoins.addAll(universe);
        refreshIfStale();
    }

    /** Khởi động thread refresh nền 1 lần duy nhất (prefetch giữa các tick). */
    private void startBgIfNeeded() {
        if (bgStarted) return;
        synchronized (this) {
            if (bgStarted) return;
            bg.scheduleWithFixedDelay(this::refreshIfStale, 10, 10, TimeUnit.SECONDS);
            bgStarted = true;
        }
    }

    /** Reload (batch, chỉ chunk-tháng gần) khi pipelineFreshTs tăng HOẶC còn coin thiếu cache. */
    private void refreshIfStale() {
        long fresh = pipelineFreshTs();
        java.util.Set<String> missing = new java.util.HashSet<>();
        for (String c : knownCoins) if (!cache.containsKey(c)) missing.add(c);
        if (missing.isEmpty() && fresh <= loadedFreshTs) return;
        synchronized (reloadLock) {
            fresh = pipelineFreshTs();
            boolean stale = fresh > loadedFreshTs;
            java.util.Set<String> toLoad = stale ? new java.util.HashSet<>(knownCoins) : new java.util.HashSet<>();
            for (String c : knownCoins) if (!cache.containsKey(c)) toLoad.add(c);
            if (toLoad.isEmpty()) return;
            long since = System.currentTimeMillis() - CACHE_WINDOW_MS - READ_MARGIN_MS;
            Map<String, TreeMap<Long, Float>[]> loaded =
                    DataManagerAerospikeFloatSim.getMetricMap242RecentBatch(toLoad, OI_SETS, OiFeatLiveSets.BIN, since);
            cache.putAll(loaded);
            loadedFreshTs = fresh;
            LOG.info("[OI-LIVE] load {} coin (since={}) tai freshTs={} (stale={})", loaded.size(), since, fresh, stale);
        }
    }

    /**
     * [oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuy] tại t (merge_asof backward 2h). Cả 5 set
     * cùng tập ts → dùng 1 mốc ref (oiZ, fallback delta) rồi đọc cả 5 tại mốc đó → nhất quán.
     * NaN từng phần / cả 5 neu khong co OI ≤ t trong tol.
     */
    public float[] lookup(String coin, long t) {
        TreeMap<Long, Float>[] a = cache.get(coin);
        if (a == null) {
            // cold-start ngoài beginTick (ít khi): nạp 1 coin batch.
            long since = System.currentTimeMillis() - CACHE_WINDOW_MS - READ_MARGIN_MS;
            a = DataManagerAerospikeFloatSim.getMetricMap242RecentBatch(
                    java.util.Collections.singletonList(coin), OI_SETS, OiFeatLiveSets.BIN, since).get(coin);
            if (a == null) a = emptyArr();
            TreeMap<Long, Float>[] prev = cache.putIfAbsent(coin, a);
            if (prev != null) a = prev;
            knownCoins.add(coin);
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
     * [B4-SPEED] Đọc CHỈ chunk-tháng gần (24h) — lastKey y hệt full-history (điểm mới nhất nằm tháng hiện tại).
     * Tra 0 neu ca hai deu chua co (cold-start) -> caller KHONG gate luc do.
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
