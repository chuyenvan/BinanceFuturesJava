package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.slf4j.helpers.MessageFormatter;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/**
 * [SHADOW2 2026-10-05] (b) key OFF => dong [GATE] y het chuoi cu; key ON => them n_skipfull/u.
 * (c) liveBookFull: profile C3 bat => von lay tu so giay ShadowBookC3 (mock U gia + so that), tat => BudgetManager.
 */
public class LiveBookUTest {

    private float uMax0;

    @Before
    public void setUp() {
        uMax0 = Configs.U_MAX;
        Configs.U_MAX = 0.60f;
    }

    @After
    public void tearDown() {
        Configs.U_MAX = uMax0;
        ShadowBookC3.resetForTest();
        stateFile().delete();
    }

    private static java.io.File stateFile() {
        return new java.io.File(System.getProperty("user.dir"), "open_positions.csv");
    }

    /** Mau CU chep NGUYEN VAN (khong dung hang so cua LiveBookU) — chong troi parser. */
    private static final String OLD = "[GATE] scale={} topk={} base={} thr=[{}..{}] n_cand={} n_rej={} n_pass={}";

    @Test
    public void keyOffLineIdenticalToLegacy() {
        String exp = "[GATE] scale=1.5500 topk=16 base=0.00800 thr=[0.01720..0.02400] n_cand=16 n_rej=15 n_pass=1";
        String got = LiveBookU.gateLine(false, "1.5500", 16, "0.00800", "0.01720", "0.02400", 16, 15, 7, 0.65f);
        assertEquals(exp, got);
        assertEquals(MessageFormatter.arrayFormat(OLD,
                new Object[]{"1.5500", 16, "0.00800", "0.01720", "0.02400", 16, 15, 1}).getMessage(), got);
        String got2 = LiveBookU.gateLine(false, "1.5500", 16, "0.00800", "-", "-", 3, 3, 0, Float.NaN);
        assertEquals("[GATE] scale=1.5500 topk=16 base=0.00800 thr=[-..-] n_cand=3 n_rej=3 n_pass=0", got2);
        assertFalse(got.contains("n_skipfull") || got.contains(" u="));
    }

    @Test
    public void keyOnAppendsSkipFullAndU() {
        String base = "[GATE] scale=1.5500 topk=24 base=0.00800 thr=[0.01720..0.02400] n_cand=24 n_rej=20 n_pass=4";
        assertEquals(base + " n_skipfull=7 u=0.6500",
                LiveBookU.gateLine(true, "1.5500", 24, "0.00800", "0.01720", "0.02400", 24, 20, 7, 0.65f));
        assertEquals(base + " n_skipfull=0 u=-",
                LiveBookU.gateLine(true, "1.5500", 24, "0.00800", "0.01720", "0.02400", 24, 20, 0, Float.NaN));
        assertEquals("0.5999", LiveBookU.fmtU(0.59994f));
    }

    /** (c) mock U gia: C3 bat => lay von so giay (U=0.70 => day); C3 tat => BudgetManager, KHONG goi so giay. */
    @Test
    public void c3OnUsesShadowBookSource() {
        AtomicInteger calls = new AtomicInteger();
        Float[] on = LiveBookU.marginEquity(true, 100f, 1000f, () -> {
            calls.incrementAndGet();
            return new Float[]{700f, 1000f};
        });
        assertEquals(1, calls.get());
        assertEquals(0.70f, LiveBookU.u(on[0], on[1]), 1e-6f);
        assertNull(TradeUtils.managerBudget(null, on[0], on[1], MarketLevelChange.PREDICT_SYMBOL_TRADE));
        Float[] off = LiveBookU.marginEquity(false, 100f, 1000f, () -> {
            calls.incrementAndGet();
            return new Float[]{700f, 1000f};
        });
        assertEquals(1, calls.get());
        assertEquals(100f, off[0], 0f);
        assertEquals(1000f, off[1], 0f);
        assertNotNull(TradeUtils.managerBudget(null, off[0], off[1], MarketLevelChange.PREDICT_SYMBOL_TRADE));
        Float[] nul = LiveBookU.marginEquity(false, null, null, () -> null);
        assertNull(nul[0]);
        assertTrue(Float.isNaN(LiveBookU.u(nul[0], nul[1])));
        assertTrue(Float.isNaN(LiveBookU.u(10f, 0f)));
    }

    /** (c) so giay THAT: fromBook = {marginRunning, equityNow(gia vi the mo)}; so rong => khong lay gia. */
    @Test
    public void fromBookReadsShadowBook() {
        ShadowBookC3.resetForTest();
        stateFile().delete();
        Configs.properties.putIfAbsent("CAPITAL_START", "35000");
        ShadowBookC3 b = ShadowBookC3.getInstance();
        AtomicInteger fetch = new AtomicInteger();
        Float[] empty = LiveBookU.fromBook(b, s -> {
            fetch.incrementAndGet();
            return new HashMap<>();
        });
        assertEquals(0, fetch.get());
        assertEquals(0f, empty[0], 0f);
        b.openPos("AAAUSDT", 0L, 100f, 2f, 1, 0.10f);
        Map<String, Float> px = new HashMap<>();
        px.put("AAAUSDT", 110f);
        Float[] me = LiveBookU.fromBook(b, s -> {
            fetch.incrementAndGet();
            assertTrue(s.contains("AAAUSDT"));
            return px;
        });
        assertEquals(1, fetch.get());
        assertEquals(b.marginRunning(), me[0], 0f);
        assertEquals(b.equityNow(px), me[1], 0f);
        assertEquals(20f, me[1] - empty[1], 1e-3f);
        assertTrue(me[0] > 0f);
    }
}
