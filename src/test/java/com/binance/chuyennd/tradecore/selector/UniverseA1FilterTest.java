package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.After;
import org.junit.Test;

import java.net.URISyntaxException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.TreeMap;

import static org.junit.Assert.*;

/** Fixture exchangeInfo: kiem dinh nghia TradFi/INDEX va co TAT/BAT cua UNIVERSE_A1. */
public class UniverseA1FilterTest {

    private static Path fixture() throws URISyntaxException {
        return Paths.get(UniverseA1FilterTest.class.getResource("/universe_a1_exchange_info.json").toURI());
    }

    @After
    public void tearDown() {
        UniverseA1Filter.resetForTest();
    }

    @Test
    public void flagOff_khongLocGi() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", false);
        assertFalse(UniverseA1Filter.isActive());
        assertFalse(UniverseA1Filter.isExcluded("AAPLUSDT"));
        Map<String, KlineObjectSimple> m = new LinkedHashMap<>();
        m.put("AAPLUSDT", new KlineObjectSimple());
        assertSame(m, UniverseA1Filter.filter(m));
    }

    @Test
    public void flagOn_locDungDinhNghia() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        assertTrue(UniverseA1Filter.isActive());
        // TradFi: contractType TRADIFI_PERPETUAL, underlyingType ngoai {COIN,INDEX,PREMARKET}
        assertTrue(UniverseA1Filter.isExcluded("AAPLUSDT"));
        assertTrue(UniverseA1Filter.isExcluded("GLDUSDT"));
        // INDEX: underlyingType=INDEX hoac co trong danh sach INDEX tuong minh
        assertTrue(UniverseA1Filter.isExcluded("SPXUSDT"));
        assertTrue(UniverseA1Filter.isExcluded("DEFIUSDT"));
        // PREMARKET (PREDICTUSDT) la crypto; thieu underlyingType => KHONG coi la TF
        assertFalse(UniverseA1Filter.isExcluded("PREDICTUSDT"));
        assertFalse(UniverseA1Filter.isExcluded("WEIRDUSDT"));
        assertFalse(UniverseA1Filter.isExcluded("BTCUSDT"));
        // ten ngan duoc chuan hoa ve USDT
        assertTrue(UniverseA1Filter.isExcluded("AAPL"));
        Map<String, Integer> st = UniverseA1Filter.stats();
        assertEquals(2, st.get("tradfi").intValue());   // AAPL + GLD
        assertEquals(2, st.get("index").intValue());    // SPX + DEFI
        assertEquals(4, st.get("excluded").intValue());
    }

    @Test
    public void filterSnapshot_giuNguyenMapGoc() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        Map<String, String> m = new LinkedHashMap<>();
        m.put("BTCUSDT", "btc");
        m.put("AAPLUSDT", "aapl");
        m.put("SPXUSDT", "spx");
        Map<String, String> out = UniverseA1Filter.filter(m);
        assertEquals(1, out.size());
        assertTrue(out.containsKey("BTCUSDT"));
        assertEquals(3, m.size());
    }

    @Test
    public void filterMinutes_locTungPhut() throws Exception {
        UniverseA1Filter.installForTest(fixture(), "DEFIUSDT", true);
        TreeMap<Long, Map<String, KlineObjectSimple>> in = new TreeMap<>();
        Map<String, KlineObjectSimple> a = new LinkedHashMap<>();
        a.put("BTCUSDT", new KlineObjectSimple());
        a.put("AAPLUSDT", new KlineObjectSimple());
        in.put(1L, a);
        Map<String, KlineObjectSimple> b = new LinkedHashMap<>();
        b.put("SPXUSDT", new KlineObjectSimple());
        in.put(2L, b);
        TreeMap<Long, Map<String, KlineObjectSimple>> out = UniverseA1Filter.filterMinutes(in);
        assertEquals(2, out.size());
        assertEquals(1, out.get(1L).size());
        assertTrue(out.get(1L).containsKey("BTCUSDT"));
        assertTrue(out.get(2L).isEmpty());
    }
}
