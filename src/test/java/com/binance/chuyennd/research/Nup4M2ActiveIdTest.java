package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.After;
import org.junit.BeforeClass;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import static org.junit.Assert.*;

/**
 * [NUP4 ADDENDUM-3] Tai hien bug M2: sau gop, vi the trong so SLEEVE phai nam trong mang active (=> vong exit cua sleeve
 * thay va dong duoc), dong xong thi symbol duoc giai phong (m2BaseHeld), margin tra ve 0, printDone (allOrderDone) du 2 leg.
 * Truoc ban sua: mang active rong sau gop => vong exit khong dong gi => cac assert sau "exit" deu FAIL.
 */
public class Nup4M2ActiveIdTest {
    static final long M = 60_000L, T0 = 1_790_000_000_000L;
    static final short SID = 5;

    @BeforeClass
    public static void noAerospike() {
        TestMapperStub.seed("M2XUSDT");
    }

    @After
    public void reset() {
        Configs.MERGE_MODE = "NONE";
        BudgetManagerSimple.resetInstance();
    }

    static OrderTargetInfoTest leg(long t, float e, float q) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, e, null, q, 1, "M2XUSDT", t, t, OrderSide.BUY);
        o.firstEntryPrice = e;
        o.clusterFirstLegTime = t;
        return o;
    }

    static KlineObjectSimple tk(float c, long t) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.priceClose = c; k.priceOpen = c; k.minPrice = c; k.maxPrice = c; k.startTime = t;
        return k;
    }

    /** sim co so SLEEVE dang giu SID (1 leg sleeve 2 @ 100), mode cho truoc. */
    static SimulatorMarketLevelTicker1MStopLoss simWithSleevePosition(String mode, OrderTargetInfoTest slv) {
        Configs.APPLY_FUNDING_FEE = false;
        Configs.MERGE_MODE = mode;
        SimulatorMarketLevelTicker1MStopLoss s = new SimulatorMarketLevelTicker1MStopLoss();
        s.allOrderDone = new java.util.TreeMap<>();
        s.initSleeveForTest("V1");
        List<OrderTargetInfoTest> L = new ArrayList<>();
        L.add(slv);
        s.sleeveBook.symbol2OrdersEntry[SID] = L;
        s.sleeveBook.symbol2OrderRunning[SID] = slv;
        s.sleeveBook.activeRunningIds[0] = SID;
        s.sleeveBook.activeRunningCount = 1;
        s.sleeveBook.bm.marginRunning = slv.calMargin();
        s.legOwner.put(slv.symbol + "|" + slv.timeStart, "S");
        return s;
    }

    /** chay dung vong exit cua sleeve (duyet mang active) va dong moi vi the tai gia px. */
    static int sleeveExitAll(SimulatorMarketLevelTicker1MStopLoss s, float px, long t) {
        s.enterSleeve();
        int n = 0;
        try {
            for (short id : Arrays.copyOf(s.activeRunningIds, s.activeRunningCount)) {
                OrderTargetInfoTest r = s.symbol2OrderRunning[id];
                r.priceTP = px;
                r.lastPrice = px;
                r.timeUpdate = t;
                r.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                s.closeOrder(id, r);
                n++;
            }
        } finally {
            s.exitSleeve();
        }
        return n;
    }

    @Test
    public void m2MergedPositionIsActiveExitsAndReleases() {
        OrderTargetInfoTest slv = leg(T0 - 60 * M, 100f, 2f);
        SimulatorMarketLevelTicker1MStopLoss s = simWithSleevePosition("M2", slv);
        OrderTargetInfoTest bas = leg(T0, 90f, 1f);
        s.legOwner.put(bas.symbol + "|" + bas.timeStart, "B");
        assertTrue("M2 => leg vao so sleeve", s.mergeSleeveCluster(SID, bas, tk(90f, T0), "MERGE_SLEEVE"));
        // vi the gop: 1 vi the (3 @ 96,67) trong so SLEEVE, VA co trong mang active (bug cu: count = 0)
        assertEquals(1, s.sleeveBook.activeRunningCount);
        assertEquals(SID, s.sleeveBook.activeRunningIds[0]);
        assertEquals(3f, s.sleeveBook.symbol2OrderRunning[SID].quantity, 1e-6f);
        assertTrue(s.m2BaseHeld.contains(SID));
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.singleStopAfterMerge(s.symbol2OrderRunning,
                s.sleeveBook.symbol2OrderRunning, SID));
        // vong exit cua sleeve phai thay va dong duoc
        assertEquals(1, sleeveExitAll(s, 110f, T0 + 30 * M));
        assertNull(s.sleeveBook.symbol2OrderRunning[SID]);
        assertNull(s.sleeveBook.symbol2OrdersEntry[SID]);
        assertEquals(0, s.sleeveBook.activeRunningCount);
        assertFalse("symbol phai duoc giai phong cho so nen", s.m2BaseHeld.contains(SID));
        assertEquals("margin phai tra ve", 0f, s.sleeveBook.bm.marginRunning, 1e-3f);
        assertEquals("printDone du 2 leg", 2, s.sleeveBook.allOrderDone.size());
    }

    @Test
    public void m2DoesNotDuplicateActiveId() {
        short[] ids = new short[4];
        int n = SimulatorMarketLevelTicker1MStopLoss.addSleeveActiveId(ids, 0, (short) 7);
        n = SimulatorMarketLevelTicker1MStopLoss.addSleeveActiveId(ids, n, (short) 7);
        assertEquals(1, n);
        n = SimulatorMarketLevelTicker1MStopLoss.addSleeveActiveId(ids, n, (short) 9);
        assertEquals(2, n);
        assertEquals(9, ids[1]);
    }

    /** M1 (ra soat cung loai): sleeve nha vi the hoan toan; caller (duong thuong) se addActiveRunningId o so NEN. */
    @Test
    public void m1ReleasesSleeveBookCompletely() {
        OrderTargetInfoTest slv = leg(T0 - 60 * M, 100f, 2f);
        SimulatorMarketLevelTicker1MStopLoss s = simWithSleevePosition("M1", slv);
        OrderTargetInfoTest bas = leg(T0, 90f, 1f);
        assertFalse("M1 => caller di tiep duong thuong", s.mergeSleeveCluster(SID, bas, tk(90f, T0), "MERGE_BASE"));
        assertEquals(0, s.sleeveBook.activeRunningCount);
        assertNull(s.sleeveBook.symbol2OrderRunning[SID]);
        assertEquals(0f, s.sleeveBook.bm.marginRunning, 1e-3f);
        assertSame(slv, s.symbol2OrderRunning[SID]);
        assertEquals(1, s.symbol2OrdersEntry[SID].size());
        assertFalse(s.m2BaseHeld.contains(SID));
        assertEquals(sleeveExitAll(s, 110f, T0 + 30 * M), 0);     // khong con gi o so sleeve
    }
}
