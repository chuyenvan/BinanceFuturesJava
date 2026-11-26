package com.binance.chuyennd.ai_ml.data;

import org.junit.Test;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.*;

/** [A1 R4j ADV] KHONG commit. Cach ly id trung: id rieng 4095 xuong co dung id store (hien tai / tuong lai) khong. */
public class A1R4jAdvMapperTest {

    static final class Store implements SymbolMapperStore {
        final Map<String, Short> data = new HashMap<>();
        @Override public Map<String, Short> loadForInit() { return new HashMap<>(data); }
        @Override public boolean writable() { return false; }
        @Override public Snapshot readForWrite() { return new Snapshot(new HashMap<>(data), 1); }
        @Override public boolean putIfGenerationMatches(String s, short id, int g) { return false; }
    }

    static void assertNoSharedId(SimpleSymbolMapper m) {
        Set<Short> seen = new HashSet<>();
        for (Map.Entry<String, Short> e : m.getAllMappings().entrySet()) {
            assertTrue("id " + e.getValue() + " dung chung (" + e.getKey() + ")", seen.add(e.getValue()));
        }
    }

    /** Store tuong lai cap dung id cach ly 4095 cho symbol Z => Z khong duoc chung id voi symbol dang cach ly. */
    @Test
    public void futureStoreIdEqualToQuarantineId() {
        Store st = new Store();
        for (int i = 1; i <= 5; i++) st.data.put("S" + i + "USDT", (short) i);
        st.data.put("ZZDUPUSDT", (short) 3);   // trung id 3 => cach ly luc init (policy WARN)
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "WARN");
        m.alertSink = s -> { };
        m.init();
        assertTrue(m.isQuarantined("ZZDUPUSDT"));
        short q = m.getId("ZZDUPUSDT");
        st.data.put("FUTUSDT", q);
        m.refreshFromStore();
        assertNotEquals(q, m.getId("FUTUSDT"));
        assertNoSharedId(m);
    }

    /** Store DA co id 4095 luc init + 1 id trung => cach ly khong duoc lay 4095. */
    @Test
    public void storeAlreadyHas4095() {
        Store st = new Store();
        for (int i = 1; i <= 5; i++) st.data.put("S" + i + "USDT", (short) i);
        st.data.put("HIGHUSDT", (short) 4095);
        st.data.put("ZZDUPUSDT", (short) 2);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "WARN");
        m.alertSink = s -> { };
        m.init();
        assertEquals(4095, m.getId("HIGHUSDT"));
        assertNoSharedId(m);
        assertEquals("S2USDT", m.getSymbol((short) 2));
    }

    /** XUSDT/BTCUSDT id 1 (242): BTC giu id 1 + KHONG cach ly; XUSDT cach ly. */
    @Test
    public void btcKeepsIdOne() {
        Store st = new Store();
        st.data.put("BTCUSDT", (short) 1);
        st.data.put("XUSDT", (short) 1);
        st.data.put("ETHUSDT", (short) 2);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "WARN");
        m.alertSink = s -> { };
        m.init();
        assertFalse(m.isQuarantined("BTCUSDT"));
        assertEquals(1, m.getId("BTCUSDT"));
        assertTrue(m.isQuarantined("XUSDT"));
        assertEquals("BTCUSDT", m.getSymbol((short) 1));
        assertNoSharedId(m);
    }
}
