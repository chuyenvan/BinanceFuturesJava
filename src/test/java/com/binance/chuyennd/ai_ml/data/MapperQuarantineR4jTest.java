package com.binance.chuyennd.ai_ml.data;

import org.junit.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/** [V12 R4j A1 MAJ-1] KHONG BAO GIO 2 symbol 1 id: symbol bi tu choi id => cach ly (id rieng, khong giao dich) + KHAN. */
public class MapperQuarantineR4jTest {

    static final class RoStore implements SymbolMapperStore {
        final Map<String, Short> data = new HashMap<>();
        boolean writable;
        @Override public Map<String, Short> loadForInit() { return new HashMap<>(data); }
        @Override public boolean writable() { return writable; }
        @Override public Snapshot readForWrite() { return new Snapshot(new HashMap<>(data), 1); }
        @Override public boolean putIfGenerationMatches(String s, short id, int g) { return false; }
    }

    @Test
    public void refreshConflict_quarantinesNewcomer_ownerUnaffected() {
        RoStore st = new RoStore();
        for (int i = 1; i <= 5; i++) st.data.put("S" + i + "USDT", (short) i);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "FAIL");
        List<String> alerts = new ArrayList<>();
        m.alertSink = alerts::add;
        m.init();
        short a = m.getId("AAAUSDT");
        st.data.put("BBBUSDT", (short) a);
        st.data.put("AAAUSDT", (short) 7);
        m.refreshFromStore();
        short b = m.getId("BBBUSDT");
        assertNotEquals(a, b);
        assertTrue(m.isQuarantined("BBBUSDT"));
        assertFalse(m.isQuarantined("AAAUSDT"));
        assertEquals("chu id giu nguyen", "AAAUSDT", m.getSymbol(a));
        assertEquals("BBBUSDT", m.getSymbol(b));
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0), alerts.get(0).contains("KHAN") && alerts.get(0).contains("BBBUSDT"));
        Map<String, Integer> snap = new HashMap<>();
        snap.put("AAAUSDT", 1);
        snap.put("BBBUSDT", 2);
        Map<String, Integer> out = m.dropQuarantined(snap);
        assertTrue(out.containsKey("AAAUSDT"));
        assertFalse("khong giao dich / khong nap history", out.containsKey("BBBUSDT"));
        m.refreshFromStore();
        assertEquals("khong canh bao lap", 1, alerts.size());
    }

    @Test
    public void initWarnDuplicate_nonOwnerQuarantined() {
        RoStore st = new RoStore();
        st.data.put("BTCUSDT", (short) 1);
        st.data.put("XUSDT", (short) 1);
        st.data.put("ETHUSDT", (short) 2);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "WARN");
        List<String> alerts = new ArrayList<>();
        m.alertSink = alerts::add;
        m.init();
        assertEquals(1, m.getId("BTCUSDT"));
        assertNotEquals(1, m.getId("XUSDT"));
        assertTrue(m.isQuarantined("XUSDT"));
        assertEquals("BTCUSDT", m.getSymbol((short) 1));
        assertEquals(1, alerts.size());
    }

    @Test
    public void quarantineIdsNeverCollide() {
        RoStore st = new RoStore();
        for (int i = 1; i <= 3; i++) st.data.put("S" + i + "USDT", (short) i);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "FAIL");
        m.alertSink = s -> { };
        m.init();
        st.data.put("D1USDT", (short) 1);
        st.data.put("D2USDT", (short) 2);
        st.data.put("D3USDT", (short) 3);
        m.refreshFromStore();
        java.util.Set<Short> ids = new java.util.HashSet<>();
        for (String s : new String[]{"S1USDT", "S2USDT", "S3USDT", "D1USDT", "D2USDT", "D3USDT"}) ids.add(m.getId(s));
        assertEquals(6, ids.size());
        assertEquals(3, m.quarantinedSymbols().size());
    }
}
