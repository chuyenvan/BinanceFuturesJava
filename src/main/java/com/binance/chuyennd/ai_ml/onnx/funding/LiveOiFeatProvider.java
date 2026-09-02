package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;

import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * LIVE — đọc 5 OI feature (#41..#45) ĐÃ TÍNH SẴN trên Oracle ({@code ComputeOiFeat2Live242}) từ
 * Aerospike-242 ({@link OiFeatLiveSets}), lookup merge_asof BACKWARD 2h. ZERO compute trên bot.
 *
 * <p>Cache per-coin trong 1 tick; gọi {@link #clear()} đầu mỗi tick để đọc lại data Oracle vừa push.
 * FIX OOM 2026-08-29: getMetricMap242 trả TOÀN BỘ lịch sử (~30k điểm/coin) -> 780 coin × 5 set ≈ 23M
 * entry ≈ 1.9GB đỉnh/tick -> OOM. lookup() chỉ cần floorKey(t) trong MERGE_TOL_MS=2h nên CẮT map về
 * 24h ngay sau khi đọc (bản full chỉ transient rồi GC). Kết quả lookup y hệt.
 */
public class LiveOiFeatProvider {

    // FIX OOM 2026-08-29: chỉ giữ 24h lịch sử OI trong RAM (>> MERGE_TOL_MS 2h, và >> OI-GUARD-2 gate 2h).
    private static final long CACHE_WINDOW_MS = 24L * 60L * 60_000L;

    private final Map<String, TreeMap<Long, Float>[]> cache = new HashMap<>();

    @SuppressWarnings("unchecked")
    private TreeMap<Long, Float>[] load(String coin) {
        TreeMap<Long, Float>[] c = cache.get(coin);
        if (c != null) return c;
        long cutoff = System.currentTimeMillis() - CACHE_WINDOW_MS;
        TreeMap<Long, Float>[] arr = new TreeMap[]{
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.BIN, coin), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.OI_Z, OiFeatLiveSets.BIN, coin), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.LS_GLOBAL, OiFeatLiveSets.BIN, coin), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.LS_TOPTRADER, OiFeatLiveSets.BIN, coin), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.TAKER_BUY, OiFeatLiveSets.BIN, coin), cutoff),
        };
        cache.put(coin, arr);
        return arr;
    }

    /**
     * FIX OOM 2026-08-29: cắt TreeMap về [cutoff, now] — bản full-history (~30k điểm) chỉ transient rồi GC.
     * lookup() chỉ chấp nhận OI trong MERGE_TOL_MS=2h quanh t (floorKeyTol) nên 24h cho kết quả y hệt.
     */
    private static TreeMap<Long, Float> recentTail(TreeMap<Long, Float> m, long cutoff) {
        if (m == null || m.isEmpty()) return m;
        return new TreeMap<>(m.tailMap(cutoff, true));
    }

    /**
     * [oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuy] tại t (merge_asof backward 2h). Cả 5 set
     * cùng tập ts → dùng 1 mốc ref (oiZ, fallback delta) rồi đọc cả 5 tại mốc đó → nhất quán.
     * NaN từng phần / cả 5 neu khong co OI ≤ t trong tol.
     */
    public float[] lookup(String coin, long t) {
        TreeMap<Long, Float>[] a = load(coin);
        Long ref = floorKeyTol(a[1], t);
        if (ref == null) ref = floorKeyTol(a[0], t);
        if (ref == null) return nan5();
        return new float[]{val(a[0], ref), val(a[1], ref), val(a[2], ref), val(a[3], ref), val(a[4], ref)};
    }

    public void clear() {
        cache.clear();
    }

    /**
     * [OI-GUARD-2] Tuoi pipeline oi_feat: ts moi nhat (lastKey OI_Z) cua coin tham chieu (BTC/ETH) tren 242.
     * BTC/ETH luon co oi_feat khi compute khoe -> lastKey ~ lan compute thanh cong gan nhat.
     * Tra 0 neu ca hai deu chua co (cold-start truoc lan compute dau) -> caller KHONG gate luc do.
     */
    public long pipelineFreshTs() {
        long best = 0L;
        for (String c : new String[]{"BTCUSDT", "ETHUSDT"}) {
            TreeMap<Long, Float> z = DataManagerAerospikeFloatSim.getMetricMap242(
                    OiFeatLiveSets.OI_Z, OiFeatLiveSets.BIN, c);
            if (z != null && !z.isEmpty()) best = Math.max(best, z.lastKey());
        }
        return best;
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
