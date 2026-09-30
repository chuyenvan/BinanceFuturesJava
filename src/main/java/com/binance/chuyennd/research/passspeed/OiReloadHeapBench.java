package com.binance.chuyennd.research.passspeed;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * [FIX-OOM-OI 2026-09-30] BENCH ÁP LỰC HEAP (KHÔNG cần Aerospike) cho reload OI của
 * {@code LiveOiFeatProvider}. Mô phỏng ĐÚNG hình dạng dữ liệu production:
 * <ul>
 *   <li>1 chunk-tháng = ~8640 điểm 5m/set (writer MERGE-tích-luỹ cả tháng — KHÔNG phải 288 điểm/24h);</li>
 *   <li>{@code legacy}: dựng map MỚI cho toàn bộ universe trong khi map CŨ vẫn sống (double-buffer) —
 *       đỉnh ≈ 2× steady;</li>
 *   <li>{@code inplace}: nạp từng lô 64 coin vào map đang sống + CẮT 24h (288 điểm/set) — đỉnh ≈ steady + 1 lô.</li>
 * </ul>
 * PASS = hoàn tất NHIỀU chu kỳ reload, KHÔNG OOM, đỉnh heap dùng &lt; {@code -Xmx} và &lt; ngưỡng
 * {@code BENCH_BUDGET_MB}.
 *
 * <p>CHẠY (không chạy trên box live): xem docs/audit/FIX_OOM_OI_LIVE.md §verify.
 * <pre>
 * java -Xmx512m -cp target/binance-java-sdk-1.2.4.jar \
 *   com.binance.chuyennd.research.passspeed.OiReloadHeapBench legacy  653 3
 * java -Xmx512m -cp target/binance-java-sdk-1.2.4.jar \
 *   com.binance.chuyennd.research.passspeed.OiReloadHeapBench inplace 653 3
 * </pre>
 */
public class OiReloadHeapBench {

    private static final int NSET = 5;
    private static final long T0 = 1_756_000_000_000L;
    private static final long P5M = 5L * 60_000L;

    private static long peakUsed = 0L;

    public static void main(String[] args) {
        String mode = args.length > 0 ? args[0] : "inplace";
        int nCoins = args.length > 1 ? Integer.parseInt(args[1]) : 653;
        int cycles = args.length > 2 ? Integer.parseInt(args[2]) : 3;
        int pointsPerSet = args.length > 3 ? Integer.parseInt(args[3]) : 8640;   // ~1 tháng 5m
        int chunk = args.length > 4 ? Integer.parseInt(args[4]) : 64;

        System.out.printf("[BENCH] mode=%s nCoins=%d cycles=%d points/set=%d chunk=%d maxHeap=%dMB%n",
                mode, nCoins, cycles, pointsPerSet, chunk, Runtime.getRuntime().maxMemory() / (1 << 20));

        List<String> universe = new ArrayList<>();
        for (int i = 0; i < nCoins; i++) universe.add("C" + i + "USDT");

        boolean inplace = "inplace".equalsIgnoreCase(mode);
        long budgetMb = Long.parseLong(System.getenv().getOrDefault("BENCH_BUDGET_MB", "0"));
        Map<String, TreeMap<Long, Float>[]> live = new ConcurrentHashMap<>();
        Throwable err = null;
        try {
            for (int c = 0; c < cycles; c++) {
                if (inplace) reloadInplace(live, universe, chunk);
                else live = reloadLegacy(live, universe);
                sample();
            }
        } catch (Throwable t) {
            err = t;
        }

        long mb = peakUsed / (1 << 20);
        System.out.printf("[BENCH] coins=%d cycles=%d peakUsed=%dMB err=%s%n",
                live.size(), cycles, mb, err == null ? "none" : err.getClass().getSimpleName() + ": " + err.getMessage());

        // PASS = hoàn tất mọi chu kỳ KHÔNG OOM (+ đỉnh dưới ngân sách nếu có đặt BENCH_BUDGET_MB).
        boolean pass = err == null && (budgetMb <= 0 || mb <= budgetMb);
        System.out.println("[BENCH] VERDICT " + (pass ? "PASS" : "FAIL"));
        System.exit(pass ? 0 : 1);
    }

    // ------------------------------------------------------------------
    // LEGACY: double-buffer (như LiveOiFeatProvider legacy) — đỉnh 2× steady
    // ------------------------------------------------------------------
    private static Map<String, TreeMap<Long, Float>[]> reloadLegacy(
            Map<String, TreeMap<Long, Float>[]> cur, List<String> universe) {
        Map<String, TreeMap<Long, Float>[]> loaded = new HashMap<>();   // dựng MỚI toàn bộ
        for (String c : universe) loaded.put(c, monthSeries());          // chunk-tháng đầy (8640 điểm/set)
        sample();                                                        // đỉnh: cur (cũ) + loaded (mới) cùng sống
        return new ConcurrentHashMap<>(loaded);                          // swap (bản cũ thành rác)
    }

    // ------------------------------------------------------------------
    // INPLACE: nạp từng lô + cắt 24h vào CHÍNH map đang sống
    // ------------------------------------------------------------------
    private static void reloadInplace(Map<String, TreeMap<Long, Float>[]> live, List<String> universe, int chunk) {
        long now = System.currentTimeMillis();
        long keepFrom = now - 24L * 3600_000L;
        for (int s0 = 0; s0 < universe.size(); s0 += chunk) {
            int s1 = Math.min(s0 + chunk, universe.size());
            for (int i = s0; i < s1; i++) {
                TreeMap<Long, Float>[] arr = monthSeries();
                for (int s = 0; s < NSET; s++) {
                    if (arr[s].firstKey() < keepFrom) arr[s] = new TreeMap<>(arr[s].tailMap(keepFrom, true));
                }
                live.put(universe.get(i), arr);                          // thay tại chỗ, KHÔNG copy toàn map
            }
            sample();
        }
    }

    /** 1 chunk-tháng: 5 set × {@code 8640} điểm 5m, mốc thời gian kết thúc ở hiện tại. */
    private static TreeMap<Long, Float>[] monthSeries() {
        int n = 8640;
        long end = System.currentTimeMillis();
        @SuppressWarnings("unchecked")
        TreeMap<Long, Float>[] arr = new TreeMap[NSET];
        for (int s = 0; s < NSET; s++) {
            TreeMap<Long, Float> m = new TreeMap<>();
            for (int i = 0; i < n; i++) m.put(end - (long) (n - 1 - i) * P5M, (float) i);
            arr[s] = m;
        }
        return arr;
    }

    private static void sample() {
        Runtime r = Runtime.getRuntime();
        long used = r.totalMemory() - r.freeMemory();
        if (used > peakUsed) peakUsed = used;
    }
}
