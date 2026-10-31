package com.binance.chuyennd.research;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;

import java.lang.reflect.Field;
import java.util.Map;

/**
 * [NUP4-FIX] Test KHONG duoc cham Aerospike: nap san symbol vao SimpleSymbolMapper (RAM) bang reflection, danh dau
 * da init => getId() tra tu RAM, khong goi loadSymbolMapper/saveSymbolMapping (su co ghi 242 ngay 10-31).
 */
public final class TestMapperStub {
    private TestMapperStub() {
    }

    @SuppressWarnings("unchecked")
    public static synchronized void seed(String... symbols) {
        try {
            SimpleSymbolMapper m = SimpleSymbolMapper.getInstance();
            Field fi = SimpleSymbolMapper.class.getDeclaredField("isInitialized");
            Field fs = SimpleSymbolMapper.class.getDeclaredField("strToId");
            Field fr = SimpleSymbolMapper.class.getDeclaredField("idToStr");
            fi.setAccessible(true);
            fs.setAccessible(true);
            fr.setAccessible(true);
            fi.setBoolean(m, true);
            Map<String, Short> s2i = (Map<String, Short>) fs.get(m);
            Map<Short, String> i2s = (Map<Short, String>) fr.get(m);
            short next = 4000;
            for (Short v : s2i.values()) if (v >= next) next = (short) (v + 1);
            for (String sym : symbols) {
                if (!s2i.containsKey(sym)) {
                    s2i.put(sym, next);
                    i2s.put(next, sym);
                    next++;
                }
            }
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("TestMapperStub: khong seed duoc mapper", e);
        }
    }
}
