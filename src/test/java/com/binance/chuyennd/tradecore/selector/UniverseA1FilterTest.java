package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.After;
import org.junit.Test;

import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.TreeMap;

import static org.junit.Assert.*;

/**
 * Fixture = raw /fapi/v1/exchangeInfo (co contractType/underlyingType/onboardDate/serverTime).
 * Kiem: dinh nghia TradFi/INDEX, point-in-time (MDT), fail-closed symbol moi, fail-fast (moi lan goi),
 * assert >=200 TF, reload theo mtime, co TAT khong doi hanh vi.
 */
public class UniverseA1FilterTest {

    private static final long MDT_ONBOARD = 1792574400000L;   // 2026-10-21T09:20Z

    private static Path fixture() throws URISyntaxException {
        return Paths.get(UniverseA1FilterTest.class.getResource("/universe_a1_exchange_info.json").toURI());
    }

    @After
    public void tearDown() {
        UniverseA1Filter.resetForTest();
    }

    // ------------------------------------------------------------------ co TAT / dinh nghia

    @Test
    public void flagOff_khongLocGi() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", false);
        assertFalse(UniverseA1Filter.isActive());
        assertFalse(UniverseA1Filter.isExcluded("AAPLUSDT", MDT_ONBOARD));
        Map<String, KlineObjectSimple> m = new LinkedHashMap<>();
        m.put("AAPLUSDT", new KlineObjectSimple());
        assertSame(m, UniverseA1Filter.filter(m, MDT_ONBOARD));
        assertSame(m, UniverseA1Filter.filter(m));
    }

    @Test
    public void flagOn_locDungDinhNghia() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        assertTrue(UniverseA1Filter.isActive());
        long t = 1793000000000L;   // 2026-10-26 > moi onboardDate
        // TradFi: contractType TRADIFI_PERPETUAL, underlyingType ngoai {COIN,INDEX,PREMARKET}
        assertTrue(UniverseA1Filter.isExcluded("AAPLUSDT", t));
        assertTrue(UniverseA1Filter.isExcluded("MDTUSDT", t));
        // INDEX: underlyingType=INDEX (ALL/BTCDOM/DEFI)
        assertTrue(UniverseA1Filter.isExcluded("ALLUSDT", t));
        assertTrue(UniverseA1Filter.isExcluded("BTCDOMUSDT", t));
        assertTrue(UniverseA1Filter.isExcluded("DEFIUSDT", t));
        // P2: SPXUSDT la COIN (SPX6900), KHONG phai INDEX; PREMARKET la crypto; thieu underlyingType => khong TF
        assertFalse(UniverseA1Filter.isExcluded("SPXUSDT", t));
        assertFalse(UniverseA1Filter.isExcluded("PREDICTUSDT", t));
        assertFalse(UniverseA1Filter.isExcluded("NOFIELDUSDT", t));
        assertFalse(UniverseA1Filter.isExcluded("BTCUSDT", t));
        // ten ngan duoc chuan hoa ve USDT
        assertTrue(UniverseA1Filter.isExcluded("AAPL", t));
        Map<String, Integer> st = UniverseA1Filter.stats();
        assertEquals(2, st.get("tradfi").intValue());   // AAPL + MDT
        assertEquals(3, st.get("index").intValue());    // ALL + BTCDOM + DEFI
        assertEquals(5, st.get("excluded").intValue());
        assertEquals(1793072475507L, UniverseA1Filter.snapshotTs());
    }

    // ------------------------------------------------------------------ point-in-time

    @Test
    public void pointInTime_mdtTruocSauOnboard() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        long before = MDT_ONBOARD - 1;
        assertFalse("MDT la crypto truoc onboard", UniverseA1Filter.isExcluded("MDTUSDT", before));
        assertTrue("MDT la TF tu onboard", UniverseA1Filter.isExcluded("MDTUSDT", MDT_ONBOARD));
        assertTrue(UniverseA1Filter.isExcluded("MDTUSDT", MDT_ONBOARD + 60_000));
        // AAPL onboard 2026-04-06
        assertFalse(UniverseA1Filter.isExcluded("AAPLUSDT", 1775483400000L - 1));
        assertTrue(UniverseA1Filter.isExcluded("AAPLUSDT", 1775483400000L));
        // INDEX cung point-in-time (ALL onboard 2025-08-06)
        assertFalse(UniverseA1Filter.isExcluded("ALLUSDT", 1754472600000L - 1));
        assertTrue(UniverseA1Filter.isExcluded("ALLUSDT", 1754472600000L));
    }

    @Test
    public void symbolMoiSauSnapshot_failClosed() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        long snap = UniverseA1Filter.snapshotTs();
        assertFalse("truoc snapshot: khong biet => giu", UniverseA1Filter.isExcluded("NEWUSDT", snap - 1));
        assertTrue("sau snapshot: khong phan loai duoc => loai", UniverseA1Filter.isExcluded("NEWUSDT", snap + 1));
    }

    // ------------------------------------------------------------------ filter map / phut

    @Test
    public void filterSnapshot_giuNguyenMapGoc() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        long t = 1793000000000L;
        Map<String, String> m = new LinkedHashMap<>();
        m.put("BTCUSDT", "btc");
        m.put("AAPLUSDT", "aapl");
        m.put("ALLUSDT", "all");
        Map<String, String> out = UniverseA1Filter.filter(m, t);
        assertEquals(1, out.size());
        assertTrue(out.containsKey("BTCUSDT"));
        assertEquals(3, m.size());
        // khong dinh symbol bi loai => tra NGUYEN object (khong copy)
        Map<String, String> safe = new LinkedHashMap<>();
        safe.put("BTCUSDT", "btc");
        assertSame(safe, UniverseA1Filter.filter(safe, t));
    }

    @Test
    public void filterMinutes_locTungPhut_pointInTime() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        TreeMap<Long, Map<String, KlineObjectSimple>> in = new TreeMap<>();
        in.put(1L, snap("BTCUSDT", "AAPLUSDT", "MDTUSDT"));
        in.put(MDT_ONBOARD - 60_000, snap("BTCUSDT", "AAPLUSDT", "MDTUSDT"));
        in.put(MDT_ONBOARD, snap("BTCUSDT", "AAPLUSDT", "MDTUSDT"));
        TreeMap<Long, Map<String, KlineObjectSimple>> out = UniverseA1Filter.filterMinutes(in);
        assertEquals(3, out.size());
        assertEquals(3, out.get(1L).size());                       // 1970: ca 3 deu la crypto
        assertEquals(2, out.get(MDT_ONBOARD - 60_000).size());     // AAPL da onboard, MDT chua
        assertFalse(out.get(MDT_ONBOARD - 60_000).containsKey("AAPLUSDT"));
        assertEquals(1, out.get(MDT_ONBOARD).size());              // MDT bi loai tu day
        assertTrue(out.get(MDT_ONBOARD).containsKey("BTCUSDT"));
    }

    /** Parity: duong replay (filterMinutes) va duong live (filter tung phut) cho CUNG tap moi phut. */
    @Test
    public void parityReplayVa2Live_cungTap() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        TreeMap<Long, Map<String, KlineObjectSimple>> day = new TreeMap<>();
        long t0 = 1792800000000L;   // 2026-10-23
        for (int i = 0; i < 1440; i++) {
            day.put(t0 + i * 60_000L, snap("BTCUSDT", "AAPLUSDT", "MDTUSDT", "ALLUSDT", "SPXUSDT"));
        }
        TreeMap<Long, Map<String, KlineObjectSimple>> replay = UniverseA1Filter.filterMinutes(day);
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : day.entrySet()) {
            Map<String, KlineObjectSimple> live = UniverseA1Filter.filter(e.getValue(), e.getKey());
            assertEquals("tap tai " + e.getKey(), live.keySet(), replay.get(e.getKey()).keySet());
            assertFalse(replay.get(e.getKey()).containsKey("AAPLUSDT"));
            assertFalse(replay.get(e.getKey()).containsKey("MDTUSDT"));
            assertFalse(replay.get(e.getKey()).containsKey("ALLUSDT"));
            assertTrue(replay.get(e.getKey()).containsKey("SPXUSDT"));
            assertTrue(replay.get(e.getKey()).containsKey("BTCUSDT"));
        }
    }

    // ------------------------------------------------------------------ fail-fast

    @Test
    public void thieuFile_nemMoiLanGoi() throws Exception {
        Path missing = Paths.get("/tmp/khong-ton-tai-universe-a1-" + System.nanoTime() + ".json");
        UniverseA1Filter.setConfigForTest(true, missing, "DEFIUSDT", true);
        assertThrows("lan 1", UniverseA1Filter::initEager);
        assertThrows("lan 2", UniverseA1Filter::initEager);
        assertThrows("lan 3 (qua isExcluded)", () -> UniverseA1Filter.isExcluded("BTCUSDT", 1L));
    }

    @Test
    public void jsonHong_nemMoiLanGoi() throws Exception {
        Path bad = Files.createTempFile("a1bad", ".json");
        Files.write(bad, "{not-json".getBytes(StandardCharsets.UTF_8));
        try {
            UniverseA1Filter.setConfigForTest(true, bad, "DEFIUSDT", true);
            assertThrows("lan 1", UniverseA1Filter::initEager);
            assertThrows("lan 2", UniverseA1Filter::initEager);
        } finally {
            Files.deleteIfExists(bad);
        }
    }

    @Test
    public void itHon200Tf_biTuChoi() throws Exception {
        Path small = genExchange(199, false);
        try {
            UniverseA1Filter.setConfigForTest(true, small, "DEFIUSDT", true);
            assertThrows("199 TF < 200", UniverseA1Filter::initEager);
        } finally {
            Files.deleteIfExists(small);
        }
    }

    @Test
    public void du200Tf_hopLe() throws Exception {
        Path ok = genExchange(200, false);
        try {
            UniverseA1Filter.setConfigForTest(true, ok, "DEFIUSDT", true);
            UniverseA1Filter.initEager();
            assertTrue(UniverseA1Filter.isActive());
            assertEquals(200, UniverseA1Filter.stats().get("tradfi").intValue());
            assertTrue(UniverseA1Filter.isExcluded("SYM000USDT", 2000000000000L));
        } finally {
            Files.deleteIfExists(ok);
        }
    }

    @Test
    public void reloadTheoMtime() throws Exception {
        Path f = genExchange(200, false);
        try {
            long t = 1750000000000L;   // 2025-06, TRUOC serverTime snapshot => symbol la khong biet, khong fail-closed
            UniverseA1Filter.installForTest(f, "DEFIUSDT", true, false);
            assertFalse(UniverseA1Filter.isExcluded("NEWTFUSDT", t));
            // them 1 TF moi + doi mtime
            Files.write(f, genExchangeJson(200, true).getBytes(StandardCharsets.UTF_8));
            UniverseA1Filter.resetStatForTest();
            assertTrue("reload theo mtime", UniverseA1Filter.isExcluded("NEWTFUSDT", t));
        } finally {
            Files.deleteIfExists(f);
        }
    }

    /**
     * Snapshot THAT (v12 fixture 10-27) neu co tren may: assert >=200 TF va cac ca thuc te
     * (MDT point-in-time, SPXUSDT la COIN/SPX6900, INDEX ALL/BTCDOM/DEFI).
     */
    @Test
    public void realSnapshotNeuCo() throws Exception {
        Path gz = Paths.get("/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz");
        org.junit.Assume.assumeTrue("khong co fixture that", Files.isRegularFile(gz));
        Path plain = Files.createTempFile("exinfo-real", ".json");
        try (java.util.zip.GZIPInputStream in = new java.util.zip.GZIPInputStream(Files.newInputStream(gz))) {
            Files.copy(in, plain, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        }
        try {
            UniverseA1Filter.installForTest(plain, "ALLUSDT,BTCDOMUSDT,DEFIUSDT", true, true);
            Map<String, Integer> st = UniverseA1Filter.stats();
            assertTrue("TF that >= 200", st.get("tradfi") >= 200);
            assertEquals(3, st.get("index").intValue());
            long t = 1793000000000L;
            assertTrue(UniverseA1Filter.isExcluded("AAPLUSDT", t));
            assertTrue(UniverseA1Filter.isExcluded("MDTUSDT", t));
            assertFalse(UniverseA1Filter.isExcluded("MDTUSDT", 1792574400000L - 1));
            assertFalse("SPXUSDT = COIN SPX6900", UniverseA1Filter.isExcluded("SPXUSDT", t));
            assertTrue(UniverseA1Filter.isExcluded("ALLUSDT", t));
            assertTrue(UniverseA1Filter.isExcluded("BTCDOMUSDT", t));
            assertTrue(UniverseA1Filter.isExcluded("DEFIUSDT", t));
        } finally {
            Files.deleteIfExists(plain);
        }
    }

    // ------------------------------------------------------------------ helpers

    private static Map<String, KlineObjectSimple> snap(String... syms) {
        Map<String, KlineObjectSimple> m = new LinkedHashMap<>();
        for (String s : syms) m.put(s, new KlineObjectSimple());
        return m;
    }

    private interface Run {
        void run();
    }

    private static void assertThrows(String msg, Run r) {
        try {
            r.run();
            fail("khong nem: " + msg);
        } catch (IllegalStateException expected) {
            // ok
        }
    }

    private static String genExchangeJson(int nTf, boolean extra) {
        StringBuilder sb = new StringBuilder("{\"serverTime\":1793072475507,\"symbols\":[");
        sb.append("{\"symbol\":\"BTCUSDT\",\"contractType\":\"PERPETUAL\",\"underlyingType\":\"COIN\",\"onboardDate\":1567965300000}");
        for (int i = 0; i < nTf; i++) {
            sb.append(",{\"symbol\":\"SYM").append(String.format("%03d", i))
                    .append("USDT\",\"contractType\":\"TRADIFI_PERPETUAL\",\"underlyingType\":\"EQUITY\",\"onboardDate\":1700000000000}");
        }
        if (extra) {
            sb.append(",{\"symbol\":\"NEWTFUSDT\",\"contractType\":\"TRADIFI_PERPETUAL\",\"underlyingType\":\"EQUITY\",\"onboardDate\":1700000000000}");
        }
        sb.append("]}");
        return sb.toString();
    }

    private static Path genExchange(int nTf, boolean extra) throws Exception {
        Path f = Files.createTempFile("a1gen", ".json");
        Files.write(f, genExchangeJson(nTf, extra).getBytes(StandardCharsets.UTF_8));
        return f;
    }
}
