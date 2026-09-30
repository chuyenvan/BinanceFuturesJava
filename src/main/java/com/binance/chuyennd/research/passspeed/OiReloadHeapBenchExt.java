package com.binance.chuyennd.research.passspeed;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * [FIX-OOM-OI 2026-09-30] TÁCH "peak-used-dưới-churn" (gồm rác chưa GC, phụ thuộc kích thước heap)
 * khỏi "RETAINED steady" (sau System.gc) cho reload OI — nCoins=653, chunk-tháng 8640 điểm/set.
 *
 * <p>3 mode (thuần bộ nhớ, KHÔNG cần Aerospike):
 * <ul>
 *   <li>{@code legacy}      — double-buffer: dựng MỚI toàn universe khi map CŨ còn sống (như bug).</li>
 *   <li>{@code inplace}     — như fix {@code reloadNowInplace}: dựng chunk-tháng RỒI cắt 24h ngay (tạm full-month/coin).</li>
 *   <li>{@code inplace_slice} — biến thể "cắt ngay khi decode": chỉ dựng 288 điểm/coin (không tạm full-month).</li>
 * </ul>
 * In mỗi chu kỳ (để thấy KHÔNG tăng đơn điệu), rồi in peak + retained-sau-GC + tổng entry.
 * CHẠY TRÊN KAGGLE/JVM; KHÔNG chạy trên box live.
 */
public class OiReloadHeapBenchExt {

    private static final int NSET = 5;
    private static final long P5M = 5L * 60_000L;
    private static final long H = 3600_000L;

    public static void main(String[] args) {
        String mode = args.length > 0 ? args[0] : "inplace";
        int nCoins = args.length > 1 ? Integer.parseInt(args[1]) : 653;
        int cycles = args.length > 2 ? Integer.parseInt(args[2]) : 3;
        int pointsPerSet = args.length > 3 ? Integer.parseInt(args[3]) : 8640;
        int chunk = args.length > 4 ? Integer.parseInt(args[4]) : 64;
        long budgetMb = Long.parseLong(System.getenv().getOrDefault("BENCH_BUDGET_MB", "0"));

        System.out.printf("[EXT] mode=%s nCoins=%d cycles=%d points/set=%d chunk=%d maxHeap=%dMB%n",
                mode, nCoins, cycles, pointsPerSet, chunk, Runtime.getRuntime().maxMemory() / (1 << 20));
        List<String> universe = new ArrayList<>();
        for (int i = 0; i < nCoins; i++) universe.add("C" + i + "USDT");

        Map<String, TreeMap<Long, Float>[]> live = new ConcurrentHashMap<>();
        long peak = 0; Throwable err = null;
        try {
            for (int c = 0; c < cycles; c++) {
                long now = System.currentTimeMillis();
                if ("legacy".equalsIgnoreCase(mode)) {
                    Map<String, TreeMap<Long, Float>[]> loaded = new java.util.HashMap<>();
                    for (String s : universe) loaded.put(s, monthSeries(now, pointsPerSet));
                    live = new ConcurrentHashMap<>(loaded);
                } else if ("inplace_slice".equalsIgnoreCase(mode)) {
                    for (int s0 = 0; s0 < universe.size(); s0 += chunk) {
                        for (int i = s0; i < Math.min(s0 + chunk, universe.size()); i++)
                            live.put(universe.get(i), windowSeries(now, pointsPerSet));
                    }
                } else {
                    for (int s0 = 0; s0 < universe.size(); s0 += chunk) {
                        for (int i = s0; i < Math.min(s0 + chunk, universe.size()); i++) {
                            TreeMap<Long, Float>[] a = monthSeries(now, pointsPerSet);   // tạm full-month/coin
                            long keep = now - 24L * H;
                            for (int s = 0; s < NSET; s++)
                                if (!a[s].isEmpty() && a[s].firstKey() < keep)
                                    a[s] = new TreeMap<>(a[s].tailMap(keep, true));
                            live.put(universe.get(i), a);
                        }
                    }
                }
                long u = usedMb();
                peak = Math.max(peak, u);
                System.out.printf("[EXT] cycle=%d usedNow=%dMB%n", c, u);
            }
        } catch (Throwable t) {
            err = t;
        }
        long retained = settle();
        long entries = 0;
        for (TreeMap<Long, Float>[] a : live.values()) for (TreeMap<Long, Float> m : a) entries += m.size();

        System.out.printf("[EXT] coins=%d entries=%d peakUsed=%dMB retained(afterGC)=%dMB err=%s%n",
                live.size(), entries, peak, retained, err == null ? "none" : err.getClass().getSimpleName());
        boolean pass = err == null && (budgetMb <= 0 || retained <= budgetMb);
        System.out.println("[EXT] VERDICT " + (pass ? "PASS" : "FAIL"));
        System.exit(pass ? 0 : 1);
    }

    private static long usedMb() {
        Runtime r = Runtime.getRuntime();
        return (r.totalMemory() - r.freeMemory()) / (1 << 20);
    }

    private static long settle() {
        long prev = -1;
        for (int i = 0; i < 4; i++) {
            System.gc();
            try { Thread.sleep(300); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            long u = usedMb();
            if (u == prev) return u;
            prev = u;
        }
        return prev;
    }

    /** chunk-tháng: {@code n} điểm 5m kết thúc ở {@code end}. */
    private static TreeMap<Long, Float>[] monthSeries(long end, int n) {
        @SuppressWarnings("unchecked")
        TreeMap<Long, Float>[] arr = new TreeMap[NSET];
        for (int s = 0; s < NSET; s++) {
            TreeMap<Long, Float> m = new TreeMap<>();
            for (int i = 0; i < n; i++) m.put(end - (long) (n - 1 - i) * P5M, (float) i);
            arr[s] = m;
        }
        return arr;
    }

    /** biến thể cắt-ngay-khi-decode: chỉ 24h (288 điểm/5m). */
    private static TreeMap<Long, Float>[] windowSeries(long end, int pointsPerSet) {
        return monthSeries(end, Math.min(pointsPerSet, (int) (24L * H / P5M)));
    }
}
