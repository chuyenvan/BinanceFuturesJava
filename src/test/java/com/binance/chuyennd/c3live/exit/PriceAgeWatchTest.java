package com.binance.chuyennd.c3live.exit;

import org.junit.Test;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** [W3A muc 5 D-03] tuoi gia nhip exit: CHI dem + log, khong doi quyet dinh exit. */
public class PriceAgeWatchTest {

    @Test
    public void demGiaCu_thieuTs_maxAge() {
        AtomicLong now = new AtomicLong(1_000_000L);
        Map<String, Long> ts = new HashMap<>();
        ts.put("AUSDT", 1_000_000L - 2_000L);    // 2 s
        ts.put("BUSDT", 1_000_000L - 18_300L);   // 18,3 s (max lich su audit)
        PriceAgeWatch w = new PriceAgeWatch(15_000L, ts::get, now::get);
        assertEquals(1, w.observe(Arrays.asList("AUSDT", "BUSDT", "CUSDT")));
        assertEquals(1L, w.staleTicks());
        assertEquals(1L, w.staleObs());
        assertEquals(1L, w.missingObs());
        assertEquals(18_300L, w.maxAgeMs());
        ts.put("BUSDT", 1_000_000L);
        now.addAndGet(10_000L);
        assertEquals(0, w.observe(Arrays.asList("AUSDT", "BUSDT")));
        assertEquals(1L, w.staleTicks());
        assertEquals(0, w.observe(java.util.Collections.emptyList()));
    }

    @Test
    public void docLoi_tinhThieu_khongNem() {
        PriceAgeWatch w = new PriceAgeWatch(15_000L, s -> { throw new IllegalStateException("aerospike"); }, () -> 0L);
        assertEquals(0, w.observe(Arrays.asList("AUSDT")));
        assertEquals(1L, w.missingObs());
    }

    /** [W3B muc 3b] ban batch: 1 lan doc / nhip cho MOI symbol; ket qua dem nhu ban tung symbol. */
    @Test
    public void batch_motLanDocMoiNhip_ketQuaNhuCu() {
        AtomicLong now = new AtomicLong(1_000_000L);
        Map<String, Long> ts = new HashMap<>();
        ts.put("AUSDT", 1_000_000L - 2_000L);
        ts.put("BUSDT", 1_000_000L - 18_300L);
        java.util.concurrent.atomic.AtomicInteger calls = new java.util.concurrent.atomic.AtomicInteger();
        java.util.List<java.util.Collection<String>> seen = new java.util.ArrayList<>();
        PriceAgeWatch b = PriceAgeWatch.batch(15_000L, syms -> {
            calls.incrementAndGet();
            seen.add(new java.util.ArrayList<>(syms));
            Map<String, Long> m = new HashMap<>();
            for (String s : syms) if (ts.containsKey(s)) m.put(s, ts.get(s));
            return m;
        }, now::get);
        PriceAgeWatch o = new PriceAgeWatch(15_000L, ts::get, now::get);
        java.util.List<String> syms = Arrays.asList("AUSDT", "BUSDT", "CUSDT");
        assertEquals(o.observe(syms), b.observe(syms));
        assertEquals(1, calls.get());
        assertEquals(syms, seen.get(0));
        assertEquals(o.staleObs(), b.staleObs());
        assertEquals(o.missingObs(), b.missingObs());
        assertEquals(o.maxAgeMs(), b.maxAgeMs());
        for (int i = 0; i < 50; i++) b.observe(syms);
        assertEquals("1 lenh doc / nhip (khong N get)", 51, calls.get());
    }

    /** [W3B muc 3b] batch nem loi => ca nhip tinh thieu, khong nem, khong log moi nhip (dong WARN 1/phut). */
    @Test
    public void batch_loi_tinhThieu_khongNem() {
        AtomicLong now = new AtomicLong(0L);
        PriceAgeWatch b = PriceAgeWatch.batch(15_000L, s -> { throw new IllegalStateException("aerospike"); }, now::get);
        for (int i = 0; i < 10; i++) {
            assertEquals(0, b.observe(Arrays.asList("AUSDT", "BUSDT")));
            now.addAndGet(1_000L);
        }
        assertEquals(20L, b.missingObs());
        assertEquals(0L, b.staleTicks());
    }

    @Test
    public void env() {
        assertTrue(PriceAgeWatch.enabled(null));
        assertFalse(PriceAgeWatch.enabled("false"));
        assertEquals(15_000L, PriceAgeWatch.staleFrom(null));
        assertEquals(20_000L, PriceAgeWatch.staleFrom("20000"));
        assertEquals(15_000L, PriceAgeWatch.staleFrom("-1"));
    }

    /** exitTick: trailing.step(px) chay TRUOC va KHONG doc ket qua PriceAgeWatch (khong doi quyet dinh). */
    @Test
    public void nguon_chiQuanSatSauStep() throws Exception {
        String s = new String(Files.readAllBytes(new File(
                "src/main/java/com/binance/chuyennd/c3live/runtime/C3LiveRuntime.java").toPath()), StandardCharsets.UTF_8);
        int step = s.indexOf("trailing.step(px);");
        int obs = s.indexOf("priceAge.observe(syms);");
        assertTrue(step > 0 && obs > step);
        assertEquals(1, s.split("priceAge\\.observe\\(", -1).length - 1);
        assertFalse(s.contains("= priceAge.observe("));
    }
}
