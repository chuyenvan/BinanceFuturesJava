package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

/** [V11] S1FeatDump (dong CSV, cong), FundingFeeManager (lich refresh gio), q_t9, sim tie sort. */
public class V11SmallTest {

    @Test
    public void s1DumpRowAndSwitch() {
        float[] f = {0.1f, -0.25f, 0.5f, 1f / 3f, 0f, Float.NaN, 2e-7f, 3f, 4f};
        String r = S1FeatDump.row(1792155600000L, "BTCUSDT", f, -0.123456789f, 1792152000000L, 1792152000000L,
                1792155605000L, "prefetch");
        assertEquals("1792155600000,BTCUSDT,0.1,-0.25,0.5,0.33333334,0.0,NaN,2.0E-7,3.0,4.0,-0.12345679,"
                + "1792152000000,1792152000000,1792155605000,prefetch", r);
        assertEquals(S1FeatDump.HEADER.split(",").length, r.split(",", -1).length);
        assertTrue(S1FeatDump.row(1L, "X", f, 0f, null, 0L, 0L, "none").contains(",0.0,,0,0,none"));
        assertEquals(1, S1FeatDump.resolveEvery(null, "100000"));
        assertEquals(0, S1FeatDump.resolveEvery(null, "0"));
        assertEquals(0, S1FeatDump.resolveEvery("0", "100000"));
        assertEquals(5, S1FeatDump.resolveEvery(" 5 ", "0"));
        assertEquals(1, S1FeatDump.resolveEvery("abc", "1"));
        assertTrue(S1FeatDump.due(1792155600000L, 1));
        assertFalse(S1FeatDump.due(1792155660000L, 2) && S1FeatDump.due(1792155720000L, 2));
        assertFalse(S1FeatDump.due(1792155600000L, 0));
    }

    @Test
    public void fundingHourlySchedule() throws Exception {
        Class<?> c = Class.forName("com.binance.chuyennd.research.FundingFeeManager");
        java.lang.reflect.Method due = c.getDeclaredMethod("hourlyDue", long.class);
        java.lang.reflect.Method d50 = c.getDeclaredMethod("delayToSecond50", long.class);
        due.setAccessible(true);
        d50.setAccessible(true);
        long h = 1792155600000L;   // dau gio
        assertTrue((Boolean) due.invoke(null, h + 50_000L));
        assertTrue((Boolean) due.invoke(null, h + 2 * 60_000L + 50_000L));
        assertFalse((Boolean) due.invoke(null, h + 3 * 60_000L + 50_000L));
        assertFalse((Boolean) due.invoke(null, h + 59 * 60_000L + 50_000L));
        assertEquals(50_000L, (long) (Long) d50.invoke(null, h));
        assertEquals(60_000L, (long) (Long) d50.invoke(null, h + 50_000L));
        assertEquals(1_000L, (long) (Long) d50.invoke(null, h + 49_000L));
        assertEquals(59_000L, (long) (Long) d50.invoke(null, h + 51_000L));
    }

    @Test
    public void qt9Format() throws Exception {
        Class<?> c = Class.forName("com.binance.chuyennd.ai_ml.onnx.entry.LiveGateRollingRatio");
        java.lang.reflect.Method m = c.getDeclaredMethod("fmtQ9", double.class);
        m.setAccessible(true);
        assertEquals("0.00722812345", m.invoke(null, 0.00722812345));
        String f9 = (String) m.invoke(null, (double) 0.007228f);   // gia tri float32 that, 9 chu so co nghia
        assertFalse(f9.contains("e") || f9.contains("E"));
        assertEquals((double) 0.007228f, Double.parseDouble(f9), 1e-12);
        String six = String.format("%.6f", 0.00722812345);
        assertEquals("0.007228", six);
    }

    @Test
    public void simTieSortByScoreThenName() throws Exception {
        Class<?> c = Class.forName("com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss");
        java.lang.reflect.Method rk = c.getDeclaredMethod("symbolNameRank", Map.class);
        java.lang.reflect.Method so = c.getDeclaredMethod("sortByFloatThenName", long[].class, int[].class);
        rk.setAccessible(true);
        so.setAccessible(true);
        Map<String, Short> all = new HashMap<>();
        all.put("ZECUSDT", (short) 1);
        all.put("ADAUSDT", (short) 2);
        all.put("BTCUSDT", (short) 3);
        all.put("ETHUSDT", (short) 4);
        int[] nr = (int[]) rk.invoke(null, all);
        long[] a = {enc(1, 0.5f), enc(4, 0.5f), enc(3, 0.2f), enc(2, 0.5f), enc(9, 0.5f)};
        so.invoke(null, a, nr);
        assertEquals(3, (short) (a[0] >> 32));
        assertEquals(2, (short) (a[1] >> 32));   // ADA
        assertEquals(4, (short) (a[2] >> 32));   // ETH
        assertEquals(1, (short) (a[3] >> 32));   // ZEC
        assertEquals(9, (short) (a[4] >> 32));   // id khong co ten -> cuoi nhom trung
        assertEquals(0.2f, Float.intBitsToFloat((int) a[0]), 0f);
    }

    private static long enc(int id, float v) {
        return ((long) id << 32) | (Float.floatToIntBits(v) & 0xFFFFFFFFL);
    }
}
