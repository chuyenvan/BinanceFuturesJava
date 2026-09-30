package com.binance.chuyennd.research.passspeed;

import java.util.TreeMap;

/**
 * [FIX-OOM-OI 2026-09-30] KIỂM ĐÚNG ĐẮN (parity) cho fix {@code inplace}: CẮT cửa sổ 24h (như
 * {@link OiReloadHeapBench} inplace / {@code LiveOiFeatProvider.reloadNowInplace}) KHÔNG đổi kết quả
 * {@code lookup} kiểu merge_asof-backward (tol {@code MERGE_TOL_MS}=2h, 1 mốc ref lấy từ set#1 fallback
 * set#0) so với map chunk-tháng KHÔNG cắt — với mọi mốc {@code t} trong cửa sổ 24h.
 *
 * <p>Thuần bộ nhớ — KHÔNG cần Aerospike/mạng. CHẠY TRÊN KAGGLE/JVM; KHÔNG chạy trên box live.
 * <pre>
 * java -Xmx512m -cp classes com.binance.chuyennd.research.passspeed.OiReloadParityCheck 20 8640
 * </pre>
 */
public class OiReloadParityCheck {

    private static final int NSET = 5;
    private static final long P5M = 5L * 60_000L;
    private static final long H = 3600_000L;
    private static final long MERGE_TOL_MS = 2L * H;

    public static void main(String[] args) {
        int nCoins = args.length > 0 ? Integer.parseInt(args[0]) : 20;
        int pointsPerSet = args.length > 1 ? Integer.parseInt(args[1]) : 8640;
        long now = 1_756_000_000_000L;
        int checks = 0, mism = 0;
        for (int c = 0; c < nCoins; c++) {
            TreeMap<Long, Float>[] full = monthSeries(now, pointsPerSet);
            TreeMap<Long, Float>[] trim = trim24h(full, now);      // như fix inplace
            for (long back = 0; back <= 24L * H; back += 30L * 60_000L) {
                long t = now - back;
                float[] a = lookup(full, t);
                float[] b = lookup(trim, t);
                checks++;
                for (int s = 0; s < NSET; s++) {
                    boolean an = Float.isNaN(a[s]), bn = Float.isNaN(b[s]);
                    if (an != bn || (!an && a[s] != b[s])) { mism++; break; }
                }
            }
        }
        System.out.printf("[PARITY] coins=%d points/set=%d checks=%d mismatches=%d%n",
                nCoins, pointsPerSet, checks, mism);
        System.out.println("[PARITY] VERDICT " + (mism == 0 ? "PASS" : "FAIL"));
        System.exit(mism == 0 ? 0 : 1);
    }

    /** chunk-tháng: {@code pointsPerSet} điểm 5m kết thúc ở {@code end}. */
    private static TreeMap<Long, Float>[] monthSeries(long end, int pointsPerSet) {
        @SuppressWarnings("unchecked")
        TreeMap<Long, Float>[] arr = new TreeMap[NSET];
        for (int s = 0; s < NSET; s++) {
            TreeMap<Long, Float> m = new TreeMap<>();
            for (int i = 0; i < pointsPerSet; i++) m.put(end - (long) (pointsPerSet - 1 - i) * P5M, (float) i);
            arr[s] = m;
        }
        return arr;
    }

    private static TreeMap<Long, Float>[] trim24h(TreeMap<Long, Float>[] a, long now) {
        @SuppressWarnings("unchecked")
        TreeMap<Long, Float>[] out = new TreeMap[NSET];
        long from = now - 24L * H;
        for (int s = 0; s < NSET; s++) out[s] = new TreeMap<>(a[s].tailMap(from, true));
        return out;
    }

    /** Đúng ngữ nghĩa LiveOiFeatProvider.lookup: 1 mốc ref (set#1 fallback set#0) cho cả 5 set. */
    private static float[] lookup(TreeMap<Long, Float>[] a, long t) {
        Long ref = floorKeyTol(a[1], t);
        if (ref == null) ref = floorKeyTol(a[0], t);
        float[] out = new float[NSET];
        for (int s = 0; s < NSET; s++) {
            Float v = ref == null ? null : a[s].get(ref);
            out[s] = v == null ? Float.NaN : v;
        }
        return out;
    }

    private static Long floorKeyTol(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Long k = m.floorKey(t);
        if (k == null || (t - k) > MERGE_TOL_MS) return null;
        return k;
    }
}
