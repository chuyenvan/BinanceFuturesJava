package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.HashSet;
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
 * ⇒ ~3250 round-trip lớn qua WAN/lượt ⇒ ~250s/lượt. Nay: BatchRead 1 lần + chỉ chunk-tháng gần (24h) +
 * cache qua tick.
 *
 * <p>[B6-SPEED-V3 2026-09-29] Trước đây {@link #beginTick} reload ĐỒNG BỘ khi {@code pipelineFreshTs}
 * tăng (~30s/giờ) ⇒ chặn tick. Nay <b>double-buffer</b>: {@code volatile Snapshot} (data + freshTs) đọc
 * qua tham chiếu nguyên tử; thread nền tải buffer MỚI rồi swap nguyên tử — tick KHÔNG chặn. Độ trễ tối
 * đa so bản cũ = thời gian reload nền (~30s, 1 lần/giờ); OI merge_asof 2h + cadence OI 60' ⇒ vô hại.
 * Cold-start (lần đầu) VẪN load đồng bộ 1 lần (y hệt bản cũ).
 *
 * <p>Nguồn LOCAL Oracle (226): writer {@code ComputeOiFeat2Live242.writeFeatures} chỉ ghi
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
        if (universe != null) knownCoins.addAll(universe);
        if (current.freshTs == 0L && !knownCoins.isEmpty()) {
            synchronized (reloadLock) {
                if (current.freshTs == 0L) reloadNow(true);
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
            Snapshot cur = current;
            long fresh = pipelineFreshTs();
            boolean stale = fresh > cur.freshTs;
            boolean hasMissing = false;
            for (String c : knownCoins) if (!cur.data.containsKey(c)) { hasMissing = true; break; }
            if (!stale && !hasMissing) return;
            synchronized (reloadLock) {
                cur = current;
                fresh = pipelineFreshTs();
                stale = fresh > cur.freshTs;
                reloadLocked(stale);
            }
        } catch (Throwable t) {
            LOG.error("[OI-LIVE] reload nền lỗi: {}", t.toString());
        }
    }

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
            TreeMap<Long, Float>[] prev = current.data.putIfAbsent(coin, a);
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
