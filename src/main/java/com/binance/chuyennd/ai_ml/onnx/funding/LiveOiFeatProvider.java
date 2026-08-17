package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;

import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * LIVE — đọc 5 OI feature (#41..#45) ĐÃ TÍNH SẴN trên Oracle ({@code ComputeOiFeat2Live242}) từ
 * Aerospike-242 ({@link OiFeatLiveSets}), lookup merge_asof BACKWARD 2h. ZERO compute, ZERO series
 * full-history trên bot → không OOM (khác {@code SelectorOiProvider} nạp full).
 *
 * <p>Cache per-coin trong 1 tick (5 map nhỏ rolling); gọi {@link #clear()} đầu mỗi tick để đọc lại
 * data Oracle vừa push (tránh stale).
 */
public class LiveOiFeatProvider {

    private final Map<String, TreeMap<Long, Float>[]> cache = new HashMap<>();

    @SuppressWarnings("unchecked")
    private TreeMap<Long, Float>[] load(String coin) {
        TreeMap<Long, Float>[] c = cache.get(coin);
        if (c != null) return c;
        TreeMap<Long, Float>[] arr = new TreeMap[]{
                DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.BIN, coin),
                DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.OI_Z, OiFeatLiveSets.BIN, coin),
                DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.LS_GLOBAL, OiFeatLiveSets.BIN, coin),
                DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.LS_TOPTRADER, OiFeatLiveSets.BIN, coin),
                DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.TAKER_BUY, OiFeatLiveSets.BIN, coin),
        };
        cache.put(coin, arr);
        return arr;
    }

    /**
     * [oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuy] tại t (merge_asof backward 2h). Cả 5 set
     * cùng tập ts → dùng 1 mốc ref (oiZ, fallback delta) rồi đọc cả 5 tại mốc đó → nhất quán.
     * NaN từng phần / cả 5 nếu không có OI ≤ t trong tol.
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
