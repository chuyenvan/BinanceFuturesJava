package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.ai_ml.data.SymbolIdLimits;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

/**
 * [LIVEFIX2 2026-10-11] Tran id: truoc day HistoryManager.MAX_COINS=1000 => symbol id >= 1000 bi BO IM LANG (live)
 * va klineArray[1000] nem AIOOBE (sim). Nay tran chung SymbolIdLimits.CAPACITY=4096; vuot => ERROR + dem.
 */
public class HistoryManagerIdCapTest {

    private static final long T0 = 1_760_000_000_000L - (1_760_000_000_000L % 60_000L);

    @Before
    public void reset() {
        SymbolIdLimits.resetForTest();
    }

    private static KlineObjectSimple k(long t, float lo, float hi) {
        KlineObjectSimple x = new KlineObjectSimple();
        x.startTime = t;
        x.priceOpen = lo; x.minPrice = lo; x.maxPrice = hi; x.priceClose = hi; x.totalUsdt = 10_000f;
        return x;
    }

    @Test
    public void capacityIsShared4096AndAboveLegacy() {
        assertEquals(4096, SymbolIdLimits.CAPACITY);
        assertEquals(SymbolIdLimits.CAPACITY, HistoryManager.MAX_COINS);
        assertTrue(SymbolIdLimits.CAPACITY > SymbolIdLimits.LEGACY_CAPACITY);
        assertTrue(SymbolIdLimits.CAPACITY - 1 <= Short.MAX_VALUE);
    }

    @Test
    public void ids999_1000_1500_storedAndReadable() {
        HistoryManager hm = new HistoryManager();
        for (short id : new short[]{999, 1000, 1500, 4095}) {
            assertTrue("id " + id, hm.acceptKline("S" + id + "USDT", id, k(T0, 1f, 2f)));
            assertTrue(hm.acceptKline("S" + id + "USDT", id, k(T0 + 60_000L, 0.5f, 3f)));
            float[] lh = hm.getLowHigh24H(id);
            assertNotNull("id " + id + " phai co lich su (truoc LIVEFIX2: 1000/1500 bi bo)", lh);
            assertEquals(0.5f, lh[0], 0f);
            assertEquals(3f, lh[1], 0f);
        }
        assertEquals(0, SymbolIdLimits.overCapCount());
    }

    @Test
    public void overCap_isCountedNotSilent_noException() {
        HistoryManager hm = new HistoryManager();
        assertFalse(hm.acceptKline("BIGUSDT", (short) 4096, k(T0, 1f, 2f)));
        assertFalse(hm.acceptKline("BIGUSDT", (short) 5000, k(T0 + 60_000L, 1f, 2f)));
        assertEquals(2, SymbolIdLimits.overCapCount());
        assertNull(hm.getLowHigh24H((short) 4096));
    }

    @Test
    public void sameStartTimeOverwrites_unchangedForLegacyIds() {
        // hanh vi cu giu nguyen: cung startTime => ghi de nen cuoi (id < 1000)
        HistoryManager hm = new HistoryManager();
        hm.acceptKline("AUSDT", (short) 5, k(T0, 1f, 2f));
        hm.acceptKline("AUSDT", (short) 5, k(T0, 7f, 9f));
        float[] lh = hm.getLowHigh24H((short) 5);
        assertEquals(7f, lh[0], 0f);
        assertEquals(9f, lh[1], 0f);
    }

    @Test
    public void requireInRange_simLoaders() {
        assertEquals(999, SymbolIdLimits.requireInRange("t", "x", 999));
        assertEquals(1000, SymbolIdLimits.requireInRange("t", "x", 1000));
        assertEquals(1500, SymbolIdLimits.requireInRange("t", "x", 1500));
        for (int bad : new int[]{-1, 4096, 30000}) {
            try {
                SymbolIdLimits.requireInRange("t", "x", bad);
                fail("phai nem voi id " + bad);
            } catch (IllegalStateException e) {
                assertTrue(e.getMessage().contains("[ID-CAP]"));
            }
        }
    }
}
