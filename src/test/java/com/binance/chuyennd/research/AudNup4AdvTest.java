package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.BeforeClass;
import org.junit.Test;

import java.util.*;

import static com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss.*;
import static org.junit.Assert.*;

/** AUDIT NUP4 (doc lap voi claw): test doi khang + test cho ban sua NUP4-FIX (PREREG_NUP4 ADDENDUM-2). */
public class AudNup4AdvTest {
    static final long M = 60_000L, H = 3_600_000L, D = 86_400_000L, T0 = 1_790_000_000_000L;

    @BeforeClass
    public static void noAerospike() {
        TestMapperStub.seed("AAAUSDT", "BBBUSDT", "CCCUSDT", "DDDUSDT");
    }

    static OrderTargetInfoTest leg(String s, long t, float e, float q) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, e, null, q, 1, s, t, t, OrderSide.BUY);
        o.firstEntryPrice = e;
        return o;
    }

    static KlineObjectSimple tk(float c) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.priceClose = c; k.priceOpen = c; k.minPrice = c; k.maxPrice = c; k.startTime = T0;
        return k;
    }

    /** A1 (truoc: FAIL logic — leg nen thua huong dong ho/neo cua sleeve). Nay: dong ho + neo = leg NEN, ke ca sau DCA. */
    @Test public void m1BaseLegKeepsOwnClockAndHardSlAnchor() {
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        OrderTargetInfoTest slv = leg("AAAUSDT", T0 - 10 * D, 100f, 1f);
        OrderTargetInfoTest bas = leg("AAAUSDT", T0, 60f, 1f);
        sim.m1AnchorTime.put(bas.symbolId, bas.timeStart);
        sim.m1AnchorEntry.put(bas.symbolId, 60f);
        List<OrderTargetInfoTest> L = new ArrayList<>(Arrays.asList(slv, bas));
        OrderTargetInfoTest m = sim.mergeOrder(L, tk(60f), slv);
        assertEquals(T0, clockOf(m));
        assertEquals(60f, m.firstEntryPrice, 1e-6f);
        assertEquals("funding van quet tu leg dau", T0 - 10 * D, m.clusterFirstLegTime);
        L.add(leg("AAAUSDT", T0 + 5 * H, 50f, 1f));            // DCA nen sau gop
        OrderTargetInfoTest m2 = sim.mergeOrder(L, tk(50f), m);
        assertEquals(T0, clockOf(m2));
        assertEquals(60f, m2.firstEntryPrice, 1e-6f);
    }

    /** A1-control: khong co anchor (B0 / M2 / cum binh thuong) => hanh vi cu y nguyen. */
    @Test public void noAnchorKeepsLegacyClock() {
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        OrderTargetInfoTest a = leg("BBBUSDT", T0 - 2 * D, 10f, 1f);
        OrderTargetInfoTest b = leg("BBBUSDT", T0, 9f, 1f);
        OrderTargetInfoTest m = sim.mergeOrder(new ArrayList<>(Arrays.asList(a, b)), tk(9f), a);
        assertEquals(0L, m.stopClockTime);
        assertEquals(T0 - 2 * D, clockOf(m));
        assertEquals(10f, m.firstEntryPrice, 1e-6f);
    }

    /** A2: kiem "1 stop" PHAI fail duoc khi ca 2 so cung giu 1 symbol (2 vi the / 2 stop). */
    @Test public void singleStopDetectsDoubleHolding() {
        OrderTargetInfoTest[] base = new OrderTargetInfoTest[8], slv = new OrderTargetInfoTest[8];
        base[3] = leg("CCCUSDT", T0, 1f, 1f);
        assertTrue(singleStopAfterMerge(base, slv, (short) 3));
        slv[3] = leg("CCCUSDT", T0 - D, 1f, 1f);
        assertFalse(singleStopAfterMerge(base, slv, (short) 3));
        assertEquals(1, countOverlap(base, new short[]{3, 5}, 2, slv));
        base[3] = null;
        assertTrue(singleStopAfterMerge(base, slv, (short) 3));
        assertEquals(0, countOverlap(base, new short[]{3}, 1, slv));
    }

    /** A3: funding cum tron chu so huu chia theo qty, tong bao toan; cum 1 chu so huu => null (hanh vi cu). */
    @Test public void fundingSplitsByQuantityPerOwner() {
        OrderTargetInfoTest s1 = leg("DDDUSDT", T0 - D, 100f, 1f);
        OrderTargetInfoTest b1 = leg("DDDUSDT", T0, 80f, 2f);
        OrderTargetInfoTest b2 = leg("DDDUSDT", T0 + H, 70f, 1f);
        Map<String, String> own = new HashMap<>();
        own.put("DDDUSDT|" + s1.timeStart, "S");
        own.put("DDDUSDT|" + b1.timeStart, "B");
        own.put("DDDUSDT|" + b2.timeStart, "B");
        float[] f = splitFundingByOwner(Arrays.asList(s1, b1, b2), own, -40f);
        assertNotNull(f);
        assertEquals(-10f, f[0], 1e-5f);   // S: 1/4
        assertEquals(-30f, f[1], 1e-5f);   // B: 3/4 vao leg B dau
        assertEquals(0f, f[2], 0f);
        assertEquals(-40f, f[0] + f[1] + f[2], 1e-5f);
        own.put("DDDUSDT|" + s1.timeStart, "B");
        assertNull(splitFundingByOwner(Arrays.asList(s1, b1, b2), own, -40f));
    }

    /** Kill-switch A40: active khi DD >= 40 % tu dinh, dem so lan kich; thr=0 => khong bao gio active. */
    @Test public void killSwitchA40TriggersAndCounts() {
        KillSwitchA40 k = new KillSwitchA40(0.40f);
        assertFalse(k.update(100f));
        assertFalse(k.update(61f));        // -39 %
        assertTrue(k.update(60f));         // -40 % => kich lan 1
        assertTrue(k.update(50f));         // van active, khong dem lai
        assertFalse(k.update(70f));        // -30 % => tat
        assertTrue(k.update(55f));         // kich lan 2
        assertEquals(2L, k.triggers);
        KillSwitchA40 off = new KillSwitchA40(0f);
        assertFalse(off.update(100f));
        assertFalse(off.update(1f));
        assertEquals(0L, off.triggers);
    }

    /** M3 da bo khoi NUP4: mergeDecision khong con nhanh SPLIT. */
    @Test public void m3IsRemoved() {
        assertEquals("NONE", mergeDecision("M3", false, false, true));
        assertEquals("MERGE_BASE", mergeDecision("M1", false, false, true));
        assertEquals("MERGE_SLEEVE", mergeDecision("M2", false, false, true));
    }
}
