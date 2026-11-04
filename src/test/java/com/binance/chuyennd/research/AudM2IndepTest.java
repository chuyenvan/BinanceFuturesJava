package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.After;
import org.junit.BeforeClass;
import org.junit.Test;

import java.util.*;

import static org.junit.Assert.*;

/**
 * AUDIT DOC LAP (11-04) cho sua M2 ADD-3 — khac test implementer: so sleeve giu HAI symbol; gop o symbol THU NHAT
 * (swap-remove trong mang active co the lam mat/lap id khac); dong symbol con lai truoc; nen muon vao lai symbol da gop
 * phai bi chan (khong mo vi the thu hai); cuoi cung moi so sach: active rong, margin 0, du 3 leg, m2BaseHeld rong.
 */
public class AudM2IndepTest {
    static final long M = 60_000L, T0 = 1_790_100_000_000L;
    static final short A = 11, B = 23;

    @BeforeClass
    public static void noAerospike() {
        TestMapperStub.seed("AUDAUSDT", "AUDBUSDT");
    }

    @After
    public void reset() {
        Configs.MERGE_MODE = "NONE";
        BudgetManagerSimple.resetInstance();
    }

    static OrderTargetInfoTest leg(String sym, long t, float e, float q) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, e, null, q, 1, sym, t, t, OrderSide.BUY);
        o.firstEntryPrice = e;
        o.clusterFirstLegTime = t;
        return o;
    }

    static KlineObjectSimple tk(float c, long t) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.priceClose = c; k.priceOpen = c; k.minPrice = c; k.maxPrice = c; k.startTime = t;
        return k;
    }

    static void put(SimulatorMarketLevelTicker1MStopLoss s, short id, OrderTargetInfoTest o) {
        List<OrderTargetInfoTest> L = new ArrayList<>();
        L.add(o);
        s.sleeveBook.symbol2OrdersEntry[id] = L;
        s.sleeveBook.symbol2OrderRunning[id] = o;
        s.sleeveBook.activeRunningIds[s.sleeveBook.activeRunningCount++] = id;
        s.sleeveBook.bm.marginRunning += o.calMargin();
        s.legOwner.put(o.symbol + "|" + o.timeStart, "S");
    }

    static Set<Short> active(SimulatorMarketLevelTicker1MStopLoss s) {
        Set<Short> r = new HashSet<>();
        for (int i = 0; i < s.sleeveBook.activeRunningCount; i++) assertTrue("id lap", r.add(s.sleeveBook.activeRunningIds[i]));
        return r;
    }

    static void closeInSleeve(SimulatorMarketLevelTicker1MStopLoss s, short id, float px, long t) {
        s.enterSleeve();
        try {
            OrderTargetInfoTest r = s.symbol2OrderRunning[id];
            assertNotNull("vi the phai thay duoc trong so sleeve", r);
            r.priceTP = px; r.lastPrice = px; r.timeUpdate = t; r.status = OrderTargetStatus.TAKE_PROFIT_DONE;
            s.closeOrder(id, r);
        } finally {
            s.exitSleeve();
        }
    }

    @Test
    public void twoSymbolsMergeFirstCloseOtherThenMerged() {
        Configs.APPLY_FUNDING_FEE = false;
        Configs.MERGE_MODE = "M2";
        SimulatorMarketLevelTicker1MStopLoss s = new SimulatorMarketLevelTicker1MStopLoss();
        s.allOrderDone = new TreeMap<>();
        s.initSleeveForTest("V1");
        put(s, A, leg("AUDAUSDT", T0 - 90 * M, 50f, 4f));
        put(s, B, leg("AUDBUSDT", T0 - 80 * M, 20f, 5f));
        assertEquals(new HashSet<>(Arrays.asList(A, B)), active(s));

        OrderTargetInfoTest bas = leg("AUDAUSDT", T0, 40f, 2f);
        s.legOwner.put(bas.symbol + "|" + bas.timeStart, "B");
        assertEquals("MERGE_SLEEVE", SimulatorMarketLevelTicker1MStopLoss.mergeDecision("M2", false, false, true));
        assertTrue(s.mergeSleeveCluster(A, bas, tk(40f, T0), "MERGE_SLEEVE"));
        assertEquals("ca 2 symbol van active, khong lap", new HashSet<>(Arrays.asList(A, B)), active(s));
        float mA = s.sleeveBook.symbol2OrderRunning[A].calMargin(), mB = s.sleeveBook.symbol2OrderRunning[B].calMargin();
        assertEquals(mA + mB, s.sleeveBook.bm.marginRunning, 1e-3f);
        assertEquals(6f, s.sleeveBook.symbol2OrderRunning[A].quantity, 1e-6f);

        // nen muon vao lai A (da gop, so nen coi la 'dang giu') => khong gop/mo them
        assertEquals("NONE", SimulatorMarketLevelTicker1MStopLoss.mergeDecision("M2", false, s.m2BaseHeld.contains(A), true));

        closeInSleeve(s, B, 22f, T0 + 10 * M);
        assertEquals(Collections.singleton(A), active(s));
        assertTrue("A van bi nen khoa", s.m2BaseHeld.contains(A));

        closeInSleeve(s, A, 45f, T0 + 20 * M);
        assertEquals(0, s.sleeveBook.activeRunningCount);
        assertTrue(s.m2BaseHeld.isEmpty());
        assertEquals(0f, s.sleeveBook.bm.marginRunning, 1e-3f);
        assertEquals("3 leg (2 sleeve + 1 nen da gop)", 3, s.sleeveBook.allOrderDone.size());
        int nB = 0;
        for (OrderTargetInfoTest o : s.sleeveBook.allOrderDone.values())
            if ("B".equals(s.legOwner.get(o.symbol + "|" + o.timeStart))) nB++;
        assertEquals("leg nen da gop van mang owner B", 1, nB);
    }
}
