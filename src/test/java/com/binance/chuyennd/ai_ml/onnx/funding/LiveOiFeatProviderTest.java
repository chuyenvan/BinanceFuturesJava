package com.binance.chuyennd.ai_ml.onnx.funding;

import org.junit.Test;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * [FIX-OOM-OI 2026-09-30] Unit test KHÔNG cần Aerospike/mạng:
 * (1) knob {@code OI_LIVE_REFRESH_MODE} — mọi giá trị khác "inplace" phải là legacy (default parity);
 * (2) PARITY logic: cắt cửa sổ 24h (giống fix inplace) KHÔNG đổi kết quả {@link LiveOiFeatProvider#lookup}
 *     với mọi mốc t trong cửa sổ 24h (merge_asof backward 2h);
 * (3) bound {@code knownCoins}: grace-tick + trần cứng.
 *
 * <p>Bench áp lực heap (JVM {@code -Xmx}) nằm ở
 * {@code research/passspeed/OiReloadHeapBench} — KHÔNG chạy trên box live.
 */
public class LiveOiFeatProviderTest {

    private static final long MIN = 60_000L;
    private static final long H = 60L * MIN;

    // ------------------------------------------------------------------
    // (1) knob parity-default
    // ------------------------------------------------------------------
    @Test
    public void refreshMode_defaultIsLegacy() {
        assertEquals("legacy", LiveOiFeatProvider.refreshMode());
        assertFalse(LiveOiFeatProvider.isInplaceMode(LiveOiFeatProvider.refreshMode()));
    }

    @Test
    public void isInplaceMode_onlyInplace() {
        assertTrue(LiveOiFeatProvider.isInplaceMode("inplace"));
        assertTrue(LiveOiFeatProvider.isInplaceMode(" INPLACE "));
        assertTrue(LiveOiFeatProvider.isInplaceMode("InPlace"));
        assertFalse(LiveOiFeatProvider.isInplaceMode("legacy"));
        assertFalse(LiveOiFeatProvider.isInplaceMode(null));
        assertFalse(LiveOiFeatProvider.isInplaceMode(""));
        assertFalse(LiveOiFeatProvider.isInplaceMode("double"));
    }

    // ------------------------------------------------------------------
    // (2) parity: cắt 24h vô hại cho lookup trong cửa sổ
    // ------------------------------------------------------------------

    /** Map 5m cho `days` ngày, 5 set giá trị khác nhau, đủ để tạo map cỡ "chunk-tháng" như production. */
    private static TreeMap<Long, Float>[] series5(long endTs, int days) {
        int n = days * 24 * 12;                       // 5m
        @SuppressWarnings("unchecked")
        TreeMap<Long, Float>[] arr = new TreeMap[5];
        for (int s = 0; s < 5; s++) arr[s] = new TreeMap<>();
        for (int i = 0; i < n; i++) {
            long t = endTs - (long) (n - 1 - i) * 5L * MIN;
            for (int s = 0; s < 5; s++) arr[s].put(t, (float) (s * 100 + i));
        }
        return arr;
    }

    private static TreeMap<Long, Float>[] trim24h(TreeMap<Long, Float>[] a, long now) {
        @SuppressWarnings("unchecked")
        TreeMap<Long, Float>[] out = new TreeMap[5];
        long from = now - 24L * H;
        for (int s = 0; s < 5; s++) out[s] = new TreeMap<>(a[s].tailMap(from, true));
        return out;
    }

    private static boolean same5(float[] a, float[] b) {
        for (int i = 0; i < 5; i++) {
            boolean an = Float.isNaN(a[i]), bn = Float.isNaN(b[i]);
            if (an || bn) { if (an != bn) return false; }
            else if (a[i] != b[i]) return false;
        }
        return true;
    }

    @Test
    public void trim24h_preservesLookupWithinWindow() {
        long now = 1_756_000_000_000L;
        TreeMap<Long, Float>[] full = series5(now, 30);      // ~chunk-tháng (8640 điểm/set)
        TreeMap<Long, Float>[] trimmed = trim24h(full, now); // như fix inplace

        Map<String, TreeMap<Long, Float>[]> mFull = new HashMap<>();
        Map<String, TreeMap<Long, Float>[]> mTrim = new HashMap<>();
        mFull.put("BTCUSDT", full);
        mTrim.put("BTCUSDT", trimmed);

        LiveOiFeatProvider p = new LiveOiFeatProvider();
        for (long back = 0; back <= 24L * H; back += 30L * MIN) {
            long t = now - back;
            p.testSeed(mFull, now);
            float[] a = p.lookup("BTCUSDT", t);
            p.testSeed(mTrim, now);
            float[] b = p.lookup("BTCUSDT", t);
            assertTrue("parity tai t-now=" + back + "ms: " + Arrays.toString(a) + " vs " + Arrays.toString(b),
                    same5(a, b));
        }
    }

    @Test
    public void lookup_isOneRefForAllFiveSets() {
        long now = 1_756_000_000_000L;
        TreeMap<Long, Float>[] full = series5(now, 30);
        Map<String, TreeMap<Long, Float>[]> m = new HashMap<>();
        m.put("ETHUSDT", full);

        LiveOiFeatProvider p = new LiveOiFeatProvider();
        p.testSeed(m, now);
        long t = now - 7L * MIN;
        float[] v = p.lookup("ETHUSDT", t);
        long ref = full[1].floorKey(t);
        for (int s = 0; s < 5; s++) {
            assertEquals(full[s].get(ref), v[s], 0f);
        }
    }

    @Test
    public void lookup_nanWhenOutsideTolerance() {
        long now = 1_756_000_000_000L;
        TreeMap<Long, Float>[] full = series5(now, 30);
        Map<String, TreeMap<Long, Float>[]> m = new HashMap<>();
        m.put("BTCUSDT", full);
        LiveOiFeatProvider p = new LiveOiFeatProvider();
        p.testSeed(m, now);
        // t cách điểm gần nhất > MERGE_TOL_MS 2h → NaN cả 5 (giống legacy).
        float[] v = p.lookup("BTCUSDT", now + 3L * H);
        for (float x : v) assertTrue(Float.isNaN(x));
    }

    // ------------------------------------------------------------------
    // (3) bound knownCoins
    // ------------------------------------------------------------------
    @Test
    public void coinsToEvict_graceAndCap() {
        Set<String> known = new HashSet<>(Arrays.asList("A", "B", "C", "D"));
        Map<String, Long> lastSeen = new HashMap<>();
        lastSeen.put("A", 100L);   // vua thay
        lastSeen.put("B", 50L);    // vang 50 tick
        lastSeen.put("C", 10L);    // vang 90 tick
        lastSeen.put("D", 100L);

        // grace 60: B (vang 50 <= 60) giu; C (vang 90 > 60) bo.
        assertEquals(new HashSet<>(Arrays.asList("C")),
                LiveOiFeatProvider.coinsToEvict(known, lastSeen, 100L, 60, 0));
        // grace 40: B va C deu bo.
        assertEquals(new HashSet<>(Arrays.asList("B", "C")),
                LiveOiFeatProvider.coinsToEvict(known, lastSeen, 100L, 40, 0));
        // tran 2 coin: bo them coin cu nhat (C da bo, con A/B/D -> bo B).
        assertEquals(new HashSet<>(Arrays.asList("B", "C")),
                LiveOiFeatProvider.coinsToEvict(known, lastSeen, 100L, 60, 2));
        // khong vuot tran + khong vang: khong bo gi.
        Map<String, Long> allFresh = new HashMap<>();
        for (String c : known) allFresh.put(c, 100L);
        assertTrue(LiveOiFeatProvider.coinsToEvict(known, allFresh, 100L, 60, 10).isEmpty());
    }

    @Test
    public void maxCoins_defaultBounded() {
        assertTrue(LiveOiFeatProvider.maxCoins() > 0);
        assertTrue(LiveOiFeatProvider.maxCoins() <= 5000);
    }
}
