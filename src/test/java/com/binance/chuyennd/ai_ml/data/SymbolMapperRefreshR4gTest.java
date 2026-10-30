package com.binance.chuyennd.ai_ml.data;

import org.junit.Test;

import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 R4g] Lam moi mapper TAI CHO (thay restart 12h): id do process KHAC cap sau init duoc nap (getSymbol truot tu doc lai,
 * <= 1 lan/phut; refreshFromStore dinh ky); id da co trong JVM KHONG BAO GIO doi.
 */
public class SymbolMapperRefreshR4gTest {

    static final class CountingStore implements SymbolMapperStore {
        final SymbolMapperIdTest.FakeStore d;
        final AtomicInteger loads = new AtomicInteger();

        CountingStore(SymbolMapperIdTest.FakeStore d) {
            this.d = d;
        }

        @Override public Map<String, Short> loadForInit() { loads.incrementAndGet(); return d.loadForInit(); }
        @Override public boolean writable() { return d.writable(); }
        @Override public Snapshot readForWrite() { return d.readForWrite(); }
        @Override public boolean putIfGenerationMatches(String s, short id, int g) { return d.putIfGenerationMatches(s, id, g); }
    }

    @Test
    public void idAllocatedByOtherProcess_resolvedOnMiss_rateLimited() {
        SymbolMapperIdTest.FakeStore st = new SymbolMapperIdTest.FakeStore().withRange(1, 10);
        CountingStore cs = new CountingStore(st);
        SimpleSymbolMapper trade = new SimpleSymbolMapper(cs, "FAIL");
        AtomicLong t = new AtomicLong(1_000_000L);
        trade.refreshClock = t::get;
        trade.init();
        SimpleSymbolMapper ingest = new SimpleSymbolMapper(st, "FAIL");   // process khac (collectData)
        ingest.init();
        short id = ingest.getId("NEWUSDT");
        assertEquals(11, id);
        int l0 = cs.loads.get();
        assertEquals("truot => doc lai store", "NEWUSDT", trade.getSymbol(id));
        assertEquals(l0 + 1, cs.loads.get());
        short id2 = ingest.getId("NEW2USDT");
        assertEquals("UNKNOWN-12", trade.getSymbol(id2));   // < 60 s: KHONG doc lai (chong goi day)
        assertEquals("UNKNOWN-12", trade.getSymbol(id2));
        assertEquals(l0 + 1, cs.loads.get());
        t.addAndGet(SimpleSymbolMapper.MISS_REFRESH_MIN_MS);
        assertEquals("NEW2USDT", trade.getSymbol(id2));
        assertEquals(l0 + 2, cs.loads.get());
        assertEquals(12, trade.getId("NEW2USDT"));   // getId dung id store, khong cap moi
    }

    @Test
    public void refreshNeverChangesExistingIds() {
        SymbolMapperIdTest.FakeStore st = new SymbolMapperIdTest.FakeStore().withRange(1, 5);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "FAIL");
        m.init();
        st.data.put("S3USDT", (short) 99);    // store bi sua (vd tool repair) sau khi JVM init
        st.data.put("ADDUSDT", (short) 6);
        assertEquals(1, m.refreshFromStore());
        assertEquals("id trong JVM giu nguyen", 3, m.getId("S3USDT"));
        assertEquals("S3USDT", m.getSymbol((short) 3));
        assertEquals("ADDUSDT", m.getSymbol((short) 6));
        assertEquals(0, m.refreshFromStore());
    }

    @Test
    public void storeErrorKeepsMap() {
        SymbolMapperIdTest.FakeStore st = new SymbolMapperIdTest.FakeStore().withRange(1, 3);
        boolean[] fail = {false};
        SymbolMapperStore bad = new SymbolMapperStore() {
            @Override public Map<String, Short> loadForInit() {
                if (fail[0]) throw new IllegalStateException("aerospike down");
                return st.loadForInit();
            }
            @Override public boolean writable() { return false; }
            @Override public Snapshot readForWrite() { return st.readForWrite(); }
            @Override public boolean putIfGenerationMatches(String s, short id, int g) { return false; }
        };
        SimpleSymbolMapper m = new SimpleSymbolMapper(bad, "FAIL");
        m.init();
        fail[0] = true;
        assertEquals(0, m.refreshFromStore());
        assertEquals("S2USDT", m.getSymbol((short) 2));
    }
}
