package com.binance.chuyennd.ai_ml.data;

import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

/** [A1 R4i ADV] KHONG commit vao nhanh implementer. Mapper refresh: id trung giua id CUC BO va id store. */
public class A1R4iAdvMapperTest {

    static final class RoStore implements SymbolMapperStore {
        final Map<String, Short> data = new HashMap<>();
        boolean writable;
        @Override public Map<String, Short> loadForInit() { return new HashMap<>(data); }
        @Override public boolean writable() { return writable; }
        @Override public Snapshot readForWrite() { return new Snapshot(new HashMap<>(data), 1); }
        @Override public boolean putIfGenerationMatches(String s, short id, int g) { return false; }
    }

    /** Process chi doc (hoac process ghi sau loi store) cap id CUC BO 6 cho AAA; store (collectData) cap 6 cho BBB, 7 cho AAA. */
    @Test
    public void refreshMustNotGiveTwoSymbolsSameId() {
        RoStore st = new RoStore();
        for (int i = 1; i <= 5; i++) st.data.put("S" + i + "USDT", (short) i);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "FAIL");
        m.init();
        short a = m.getId("AAAUSDT");          // id cuc bo
        assertEquals(6, a);
        st.data.put("BBBUSDT", (short) 6);     // process khac cap 6 cho BBB truoc
        st.data.put("AAAUSDT", (short) 7);
        m.refreshFromStore();
        short b = m.getId("BBBUSDT");
        assertNotEquals("2 symbol KHAC nhau cung id trong 1 JVM => HistoryManager tron du lieu", a, b);
    }

    /** Trung id xuat hien SAU init (policy FAIL): init se nem, refresh thi nhan im lang (chi log). */
    @Test
    public void refreshDuplicateAfterInitIsNotRejectedLikeInit() {
        RoStore st = new RoStore();
        for (int i = 1; i <= 5; i++) st.data.put("S" + i + "USDT", (short) i);
        SimpleSymbolMapper m = new SimpleSymbolMapper(st, "FAIL");
        m.init();
        st.data.put("DUPUSDT", (short) 3);     // store bi ghi trung id 3 sau init
        m.refreshFromStore();
        assertNotEquals("DUP nhan id cua S3 => tron du lieu", m.getId("S3USDT"), m.getId("DUPUSDT"));
    }
}
