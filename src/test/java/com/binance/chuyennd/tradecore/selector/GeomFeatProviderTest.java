package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import org.junit.Test;

import java.util.*;

import static org.junit.Assert.*;

/** Unit test {@link GeomFeatProvider}: gop bar gio (quy uoc s1_geom_store.month), warm-up, chot gio, nguon loi. */
public class GeomFeatProviderTest {

    private static final long H = GeomFeatProvider.H, MIN = GeomFeatProvider.MIN;
    private static final long T0 = 1_759_000_000_000L / H * H;   // moc gio bat ky

    private static KlineObjectOptimized k(float hi, float lo, float cl) {
        return KlineObjectOptimized.newBuilder().setPriceOpen(cl).setMaxPrice(hi).setMinPrice(lo).setPriceClose(cl)
                .setTotalUsdt(1f).build();
    }

    private static Map<String, KlineObjectOptimized> m(Object... kv) {
        Map<String, KlineObjectOptimized> r = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) r.put((String) kv[i], (KlineObjectOptimized) kv[i + 1]);
        return r;
    }

    @Test
    public void aggregateHourConvention() {
        List<Map<String, KlineObjectOptimized>> mins = new ArrayList<>();
        mins.add(m("BTCUSDT", k(10f, 9f, 9.5f), "ETH", k(5f, 4f, 4.5f), "USDCUSDT", k(1f, 1f, 1f), "XUSDT", k(3f, 2f, 0f)));
        mins.add(null);                                                    // phut thieu ban ghi
        mins.add(m("BTCUSDT", k(12f, 0f, 11f), "ETHUSDT", k(6f, 3f, 0f)));  // low 0 -> NaN; close 0 -> NaN
        mins.add(m("DEADUSDT", KlineObjectOptimized.newBuilder().setMaxPrice(2f).setMinPrice(2f).setPriceClose(2f).build()));
        Map<String, double[]> b = GeomFeatProvider.aggregateHour(mins);
        assertArrayEquals(new double[]{12, 9, 11, 2}, b.get("BTCUSDT"), 0d);
        assertArrayEquals(new double[]{6, 3, 4.5, 2}, b.get("ETHUSDT"), 0d);   // close = phut HUU HAN cuoi; ten +USDT
        assertFalse(b.containsKey("USDCUSDT"));                             // STABLE
        assertFalse(b.containsKey("XUSDT"));                                // khong co close huu han -> khong co bar
        assertFalse(b.containsKey("DEADUSDT"));                             // qv gio = 0 -> bo (thay lineage F_TAIL)
        assertEquals(2, b.size());
    }

    /** Nguon gia: gia phut = f(sym, phut), co the doi theo "phien ban" de kiem doc lai gio chua chot. */
    private static final class Fake implements GeomFeatProvider.MinuteSource {
        int calls = 0;
        boolean fail = false;
        float bump = 0f;

        @Override
        public Map<Long, Map<String, KlineObjectOptimized>> read(long[] mins) {
            calls++;
            if (fail) return null;
            Map<Long, Map<String, KlineObjectOptimized>> out = new HashMap<>();
            for (long t : mins) {
                long i = t / MIN;
                Map<String, KlineObjectOptimized> r = new HashMap<>();
                for (int s = 0; s < 25; s++) {
                    float base = 10f + s + (float) Math.sin((i + s * 7) * 0.01) + bump;
                    r.put("S" + s + "USDT", k(base + 0.3f + (i % 5) * 0.01f, base - 0.2f, base));
                }
                out.put(t, r);
            }
            return out;
        }
    }

    /** Tinh tay bar gio truc tiep tu Fake roi so voi provider.features (khop TUYET DOI). */
    private static Map<String, double[]> direct(Fake f, long last) {
        int n = GeomFeatProvider.HIST_HOURS;
        Map<String, double[][]> arr = new HashMap<>();
        for (int k = 0; k < n; k++) {
            long t = last - (long) (n - 1 - k) * H;
            long[] mins = new long[60];
            for (int q = 0; q < 60; q++) mins[q] = t - 60 * MIN + q * MIN;
            Map<Long, Map<String, KlineObjectOptimized>> got = f.read(mins);
            List<Map<String, KlineObjectOptimized>> asc = new ArrayList<>();
            for (long q : mins) asc.add(got.get(q));
            for (Map.Entry<String, double[]> e : GeomFeatProvider.aggregateHour(asc).entrySet()) {
                double[][] a = arr.computeIfAbsent(e.getKey(), s -> new double[3][n]);
                for (int z = 0; z < 3; z++) a[z][k] = e.getValue()[z];
            }
        }
        return GeomFeatureLive.computeTick(arr, n - 1);
    }

    @Test
    public void warmupThenIncrementalMatchesDirect() {
        Fake f = new Fake();
        GeomFeatProvider p = new GeomFeatProvider(f);
        long last = T0;
        assertNull(p.features(last));                                    // chua nap -> null (BO tick)
        assertTrue(p.refresh(last, last + 10 * MIN));
        assertEquals(GeomFeatProvider.HIST_HOURS, f.calls);              // warm-up: 1 batch / gio
        assertTrue(p.ready(last));
        Map<String, double[]> got = p.features(last), exp = direct(new Fake(), last);
        assertEquals(exp.keySet(), got.keySet());
        for (String s : exp.keySet()) assertArrayEquals(exp.get(s), got.get(s), 0d);
        f.calls = 0;
        long next = last + H;
        assertTrue(p.refresh(next, next + 10 * MIN));
        assertEquals(1, f.calls);                                        // gio moi: dung 1 batch
        exp = direct(new Fake(), next);
        got = p.features(next);
        for (String s : exp.keySet()) assertArrayEquals(exp.get(s), got.get(s), 0d);
        assertEquals(GeomFeatProvider.HIST_HOURS, p.hoursHeld());       // cat cua so
    }

    /** Gio cuoi chua chot (now < ts_h + COMMIT_LAG) -> tick sau doc lai; da chot -> khong doc lai. */
    @Test
    public void lastHourReReadUntilCommitted() {
        Fake f = new Fake();
        GeomFeatProvider p = new GeomFeatProvider(f);
        long last = T0;
        assertTrue(p.refresh(last, last + 30_000L));
        double c1 = p.features(last).get("S0USDT")[3];
        f.bump = 1f;                                                     // phut cuoi "chot" lai gia khac
        f.calls = 0;
        assertTrue(p.refresh(last, last + GeomFeatProvider.COMMIT_LAG_MS));
        assertEquals(1, f.calls);
        double c2 = p.features(last).get("S0USDT")[3];
        assertNotEquals(c1, c2, 0d);
        f.calls = 0;
        assertTrue(p.refresh(last, last + 10 * MIN));
        assertEquals(0, f.calls);                                        // da chot
    }

    /** Nguon loi -> refresh false, features null (KHONG tra NaN toan cot). */
    @Test
    public void sourceErrorNotReady() {
        Fake f = new Fake();
        f.fail = true;
        GeomFeatProvider p = new GeomFeatProvider(f);
        assertFalse(p.refresh(T0, T0 + 10 * MIN));
        assertNull(p.features(T0));
        assertFalse(p.ready(T0));
    }

    /** Key phut GMT+7 nhu S1RankerLive.minuteKey / short_v3_r1_fade.key_of. */
    @Test
    public void minuteKeyGmt7() {
        assertEquals("19700101-0700", GeomFeatProvider.minuteKey(0L));
        assertEquals("20251231-0659", GeomFeatProvider.minuteKey(1767139140000L));   // 2025-12-30 23:59 UTC
    }
}
