package com.binance.chuyennd.ai_ml.data;

import org.junit.Test;

import java.util.*;
import java.util.concurrent.*;

import static org.junit.Assert.*;

/**
 * [MAPAUD 2026-10-11] symbol_mapper: fail-fast id trung khi nap + cap id CAS khong trung giua nhieu "JVM".
 * Tai hien su co 07/2026 (843..850 moi id 2 symbol) bang thuat toan cu, va chung minh thuat toan moi khong tai dien.
 */
public class SymbolMapperIdTest {

    /** Store gia dung chung giua nhieu SimpleSymbolMapper (= nhieu JVM tren cung Aerospike 242). */
    static final class FakeStore implements SymbolMapperStore {
        final Map<String, Short> data = new HashMap<>();
        int gen = 1;
        boolean writable = true;
        int conflictsToInject = 0;
        int putCalls = 0;

        FakeStore withRange(int from, int to) {
            for (int i = from; i <= to; i++) data.put("S" + i + "USDT", (short) i);
            return this;
        }

        @Override public synchronized Map<String, Short> loadForInit() { return new HashMap<>(data); }
        @Override public boolean writable() { return writable; }
        @Override public synchronized Snapshot readForWrite() { return new Snapshot(new HashMap<>(data), gen); }

        @Override
        public synchronized boolean putIfGenerationMatches(String symbol, short id, int expectedGeneration) {
            putCalls++;
            if (conflictsToInject > 0) {          // process khac chen ghi ngay truoc ta
                conflictsToInject--;
                short other = (short) (SymbolIdRules.maxId(data) + 1);
                data.put("OTHER" + other + "USDT", other);
                gen++;
            }
            if (expectedGeneration != gen || data.containsKey(symbol)) return false;
            data.put(symbol, id);
            gen++;
            return true;
        }
    }

    private static final String[] SET1 = {"MUUUSDT", "BNCUSDT", "FWDIUSDT", "MINIMAXUSDT", "SNOWUSDT", "APPUSDT", "GEVUSDT", "PANWUSDT"};
    private static final String[] SET2 = {"XBIUSDT", "SOXSUSDT", "TZAUSDT", "VRTUSDT", "ZHIPUUSDT", "SHAZUSDT", "SOFIUSDT", "SKHYUSDT"};

    /** Thuat toan CU (counter rieng trong RAM + put khong kiem) — 2 JVM cung init o max=842 => 8 id trung. */
    @Test
    public void legacyAlgorithm_reproduces843to850() {
        Map<String, Short> shared = new FakeStore().withRange(1, 842).data;
        short counterA = 842, counterB = 842;   // moi JVM: counter = max luc init
        for (int i = 0; i < 8; i++) {
            shared.put(SET1[i], ++counterA);    // JVM A gap 8 symbol
            shared.put(SET2[i], ++counterB);    // JVM B gap 8 symbol khac
        }
        Map<Short, List<String>> d = SymbolIdRules.duplicateIds(shared);
        assertEquals(8, d.size());
        assertEquals(Arrays.asList("MUUUSDT", "XBIUSDT"), d.get((short) 843));
        assertEquals(Arrays.asList("PANWUSDT", "SKHYUSDT"), d.get((short) 850));
    }

    @Test
    public void newAlgorithm_twoJvmsInterleaved_noCollision() {
        FakeStore st = new FakeStore().withRange(1, 842);
        SimpleSymbolMapper a = new SimpleSymbolMapper(st, "FAIL");
        SimpleSymbolMapper b = new SimpleSymbolMapper(st, "FAIL");
        a.init();
        b.init();                                // ca 2 deu thay max=842
        Set<Short> ids = new HashSet<>();
        for (int i = 0; i < 8; i++) {
            ids.add(a.getId(SET1[i]));
            ids.add(b.getId(SET2[i]));
        }
        assertEquals(16, ids.size());
        assertTrue(SymbolIdRules.duplicateIds(st.data).isEmpty());
        assertEquals(842 + 16, st.data.size());
        assertEquals(858, SymbolIdRules.maxId(st.data));
        for (String s : SET2) assertEquals(st.data.get(s), Short.valueOf(b.getId(s)));
    }

    @Test
    public void symbolAllocatedByOtherJvm_isAdopted_notOverwritten() {
        FakeStore st = new FakeStore().withRange(1, 842);
        SimpleSymbolMapper a = new SimpleSymbolMapper(st, "FAIL");
        SimpleSymbolMapper b = new SimpleSymbolMapper(st, "FAIL");
        a.init();
        b.init();
        short ida = a.getId("NEWUSDT");
        int gen = st.gen;
        short idb = b.getId("NEWUSDT");          // B chua co trong RAM
        assertEquals(ida, idb);
        assertEquals(gen, st.gen);               // B khong ghi gi
        assertEquals("NEWUSDT", b.getSymbol(idb));
    }

    @Test
    public void casConflict_retriesWithNextFreeId() {
        FakeStore st = new FakeStore().withRange(1, 842);
        SimpleSymbolMapper a = new SimpleSymbolMapper(st, "FAIL");
        a.init();
        st.conflictsToInject = 2;                // 2 lan process khac chen 843, 844
        short id = a.getId("NEWUSDT");
        assertEquals(845, id);
        assertEquals(3, st.putCalls);
        assertTrue(SymbolIdRules.duplicateIds(st.data).isEmpty());
    }

    @Test
    public void readOnlyProcess_localIdNotPersisted() {
        FakeStore st = new FakeStore().withRange(1, 842);
        st.writable = false;                     // shadow / kaggle (Live242WriteGuard chan)
        SimpleSymbolMapper a = new SimpleSymbolMapper(st, "FAIL");
        short id = a.getId("NEWUSDT");
        assertEquals(843, id);
        assertEquals(842, st.data.size());
        assertEquals(0, st.putCalls);
        assertEquals(Short.valueOf((short) 843), a.getLocalOnlyMappings().get("NEWUSDT"));
        assertEquals(id, a.getId("NEWUSDT"));    // on dinh trong JVM
        assertEquals(844, a.getId("NEW2USDT"));  // duy nhat trong JVM
    }

    @Test
    public void init_failFastOnDuplicateIds() {
        FakeStore st = new FakeStore().withRange(1, 842);
        st.data.put("MUUUSDT", (short) 843);
        st.data.put("XBIUSDT", (short) 843);
        SimpleSymbolMapper a = new SimpleSymbolMapper(st, "FAIL");
        try {
            a.init();
            fail("phai nem khi co id trung");
        } catch (IllegalStateException e) {
            assertTrue(e.getMessage(), e.getMessage().contains("843=[MUUUSDT, XBIUSDT]"));
        }
    }

    @Test
    public void init_warnPolicy_deterministicReverse() {
        FakeStore st = new FakeStore().withRange(1, 842);
        st.data.put("XBIUSDT", (short) 843);
        st.data.put("MUUUSDT", (short) 843);
        SimpleSymbolMapper a = new SimpleSymbolMapper(st, "WARN");
        a.init();
        assertEquals("MUUUSDT", a.getSymbol((short) 843));
        assertEquals(844, a.getId("NEWUSDT"));
    }

    @Test
    public void manyThreadsManyJvms_overlappingSymbols_uniqueAndConsistent() throws Exception {
        FakeStore st = new FakeStore().withRange(1, 842);
        List<SimpleSymbolMapper> jvms = new ArrayList<>();
        for (int j = 0; j < 4; j++) {
            SimpleSymbolMapper m = new SimpleSymbolMapper(st, "FAIL");
            m.init();
            jvms.add(m);
        }
        ExecutorService ex = Executors.newFixedThreadPool(16);
        List<Future<Map<String, Short>>> fs = new ArrayList<>();
        for (int t = 0; t < 32; t++) {
            final SimpleSymbolMapper m = jvms.get(t % 4);
            final int seed = t;
            fs.add(ex.submit(() -> {
                Map<String, Short> got = new HashMap<>();
                Random r = new Random(seed);
                for (int k = 0; k < 200; k++) {
                    String s = "N" + r.nextInt(60) + "USDT";   // 60 symbol moi, trung lap giua luong/JVM
                    got.put(s, m.getId(s));
                }
                return got;
            }));
        }
        Map<String, Short> all = new HashMap<>();
        for (Future<Map<String, Short>> f : fs) {
            for (Map.Entry<String, Short> e : f.get(60, TimeUnit.SECONDS).entrySet()) {
                Short prev = all.putIfAbsent(e.getKey(), e.getValue());
                if (prev != null) assertEquals("1 symbol = 1 id tren moi JVM: " + e.getKey(), prev, e.getValue());
            }
        }
        ex.shutdown();
        assertTrue(SymbolIdRules.duplicateIds(st.data).isEmpty());
        assertEquals(new HashSet<>(all.values()).size(), all.size());
        for (Map.Entry<String, Short> e : all.entrySet()) assertEquals(st.data.get(e.getKey()), e.getValue());
    }

    @Test
    public void planRepair_movesEverySymbolOfDuplicateIdsToFreshIds() {
        Map<String, Short> m = new FakeStore().withRange(1, 842).data;
        for (int i = 0; i < 8; i++) {
            m.put(SET1[i], (short) (843 + i));
            m.put(SET2[i], (short) (843 + i));
        }
        for (int i = 851; i <= 933; i++) m.put("L" + i + "USDT", (short) i);
        Map<String, Short> plan = SymbolIdRules.planRepair(m);
        assertEquals(16, plan.size());
        assertEquals(Short.valueOf((short) 934), plan.get("MUUUSDT"));   // id 843: MUU < XBI
        assertEquals(Short.valueOf((short) 935), plan.get("XBIUSDT"));
        assertEquals(Short.valueOf((short) 949), plan.get("SKHYUSDT"));
        Map<String, Short> fixed = new HashMap<>(m);
        fixed.putAll(plan);
        SymbolIdRules.assertUniqueIds(fixed, "test");
        for (short id = 843; id <= 850; id++) assertFalse(fixed.containsValue(id));   // id nhiem ban bo han
        assertEquals(m.size(), fixed.size());
        assertTrue(SymbolIdRules.planRepair(fixed).isEmpty());
    }
}
