package com.binance.chuyennd.research.passspeed;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.funding.LiveOiFeatProvider;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * [B4-SPEED] BENCH read-only cho 1 lượt predict OI: KHÔNG đặt lệnh, KHÔNG ghi Redis/Aerospike/242.
 * Đo p50/p95 "cũ" (full-history getMetricMap242 per-coin) vs "mới" (BatchRead recent + cache qua tick)
 * và chứng minh PARITY (5 giá trị lookup BIT-IDENTICAL).
 *
 * <p>Chạy với config.properties trỏ 242 read-only (giống shadow_c3): AEROSPIKE_HOST=103.157.218.242,
 * AEROSPIKE_NAMESPACE=ticker, AEROSPIKE_READ_CLUSTER=242.
 *
 * <p>Mode: {@code old | new | parity} (mặc định parity). Arg 2 = subset (0 = toàn bộ universe).
 */
public class PassSpeedBench {

    private static final Logger LOG = LoggerFactory.getLogger(PassSpeedBench.class);

    private static final String[] OI_SETS = {
            OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.OI_Z, OiFeatLiveSets.LS_GLOBAL,
            OiFeatLiveSets.LS_TOPTRADER, OiFeatLiveSets.TAKER_BUY
    };
    private static final long CACHE_WINDOW_MS = 24L * 60L * 60_000L;
    private static final long READ_MARGIN_MS = 1L * 60L * 60_000L;

    public static void main(String[] args) {
        String mode = args.length >= 1 ? args[0] : "parity";
        int subset = args.length >= 2 ? Integer.parseInt(args[1]) : 0;

        // 1. ticker read (đo như luồng live)
        long t0 = System.nanoTime();
        Map<String, List<KlineObjectSimple>> tickers = DataManagerAerospikeFloatSim.readDataForSymbols(
                System.currentTimeMillis() - 1000L * Utils.TIME_MINUTE, 1000);
        long tickerMs = (System.nanoTime() - t0) / 1_000_000L;
        LOG.info("[BENCH] ticker read (1000') = {}ms, {} symbol", tickerMs, tickers.size());

        List<String> universe = new ArrayList<>(tickers.keySet());
        if (subset > 0 && subset < universe.size()) universe = universe.subList(0, subset);
        long t = System.currentTimeMillis();
        long cutoff = t - CACHE_WINDOW_MS;

        Map<String, float[]> oldLookup = new HashMap<>();
        Map<String, float[]> newLookup = new HashMap<>();

        // ---- OLD: full-history per-coin (mô phỏng load() cũ) ----
        if ("old".equals(mode) || "parity".equals(mode)) {
            long[] perCoinMs = new long[universe.size()];
            int i = 0;
            long o0 = System.nanoTime();
            for (String sym : universe) {
                long c0 = System.nanoTime();
                @SuppressWarnings("unchecked")
                TreeMap<Long, Float>[] arr = new TreeMap[]{
                        recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[0], OiFeatLiveSets.BIN, sym), cutoff),
                        recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[1], OiFeatLiveSets.BIN, sym), cutoff),
                        recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[2], OiFeatLiveSets.BIN, sym), cutoff),
                        recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[3], OiFeatLiveSets.BIN, sym), cutoff),
                        recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[4], OiFeatLiveSets.BIN, sym), cutoff),
                };
                oldLookup.put(sym, lookupFrom(arr, t));
                perCoinMs[i++] = (System.nanoTime() - c0) / 1_000_000L;
            }
            long oldTotal = (System.nanoTime() - o0) / 1_000_000L;
            reportPerCoin("OLD (full-history, per-coin)", perCoinMs, oldTotal);
        }

        // ---- NEW: BatchRead recent + cache ----
        if ("new".equals(mode) || "parity".equals(mode)) {
            LiveOiFeatProvider provider = new LiveOiFeatProvider();
            long n0 = System.nanoTime();
            provider.beginTick(universe);   // batch nạp mọi coin (chỉ chunk-tháng gần)
            long newLoadMs = (System.nanoTime() - n0) / 1_000_000L;
            long n1 = System.nanoTime();
            for (String sym : universe) {
                newLookup.put(sym, provider.lookup(sym, t));
            }
            long newLookupMs = (System.nanoTime() - n1) / 1_000_000L;
            LOG.info("[BENCH] NEW load(batch)={}ms lookupAll={}ms cho {} coin", newLoadMs, newLookupMs, universe.size());
            // tick 2 (cache hit): beginTick KHÔNG reload => chỉ đo phí freshTs check
            long n2 = System.nanoTime();
            provider.beginTick(universe);
            long cacheHitMs = (System.nanoTime() - n2) / 1_000_000L;
            LOG.info("[BENCH] NEW tick-2 (cache hit, beginTick) = {}ms", cacheHitMs);
        }

        // ---- PARITY ----
        if ("parity".equals(mode)) {
            int same = 0, diff = 0;
            float maxDiff = 0f;
            List<String> diffSyms = new ArrayList<>();
            for (String sym : universe) {
                float[] a = oldLookup.get(sym);
                float[] b = newLookup.get(sym);
                if (a == null || b == null) { diff++; diffSyms.add(sym + "(null)"); continue; }
                boolean eq = true;
                for (int k = 0; k < 5; k++) {
                    float av = a[k], bv = b[k];
                    boolean aNan = Float.isNaN(av), bNan = Float.isNaN(bv);
                    if (aNan || bNan) { if (aNan != bNan) { eq = false; maxDiff = Float.MAX_VALUE; } }
                    else if (av != bv) { eq = false; maxDiff = Math.max(maxDiff, Math.abs(av - bv)); }
                }
                if (eq) same++; else { diff++; diffSyms.add(sym); }
            }
            LOG.info("[PARITY] {} coin: {} BIT-IDENTICAL, {} khac, maxDiff={} | lech: {}",
                    universe.size(), same, diff, maxDiff, diffSyms.isEmpty() ? "-" : diffSyms.subList(0, Math.min(10, diffSyms.size())));
            LOG.info("[PARITY] VERDICT: {}", (diff == 0) ? "PASS (bit-identical)" : "FAIL");
        }

        LOG.info("[BENCH] xong. KHONG ghi gi len 242 (read-only).");
        System.exit(0);
    }

    private static TreeMap<Long, Float> recentTail(TreeMap<Long, Float> m, long cutoff) {
        if (m == null || m.isEmpty()) return m;
        return new TreeMap<>(m.tailMap(cutoff, true));
    }

    private static float[] lookupFrom(TreeMap<Long, Float>[] a, long t) {
        Long ref = floorKeyTol(a[1], t);
        if (ref == null) ref = floorKeyTol(a[0], t);
        if (ref == null) return new float[]{Float.NaN, Float.NaN, Float.NaN, Float.NaN, Float.NaN};
        return new float[]{val(a[0], ref), val(a[1], ref), val(a[2], ref), val(a[3], ref), val(a[4], ref)};
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

    private static void reportPerCoin(String label, long[] perCoinMs, long totalMs) {
        long[] sorted = Arrays.copyOf(perCoinMs, perCoinMs.length);
        Arrays.sort(sorted);
        long p50 = sorted[sorted.length / 2];
        long p95 = sorted[Math.min(sorted.length - 1, (int) (sorted.length * 0.95))];
        LOG.info("[BENCH] {} n={} p50={}ms p95={}ms max={}ms total={}ms",
                label, sorted.length, p50, p95, sorted[sorted.length - 1], totalMs);
    }
}
