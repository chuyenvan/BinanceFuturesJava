package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss.*;
import static org.junit.Assert.*;

/**
 * [NUP4] docs/prereg/PREREG_NUP4.md §3 — trung symbol tren MOT tai khoan one-way.
 * Kiem: luat trung symbol, gop cum (qty/entry/1 stop), tach PnL theo chu so huu, DCA sau gop,
 * U/equity GOP (kill-switch A40), va mode NONE giu nguyen hanh vi cu.
 */
public class Nup4MergeTest {

    private static final long M = 60_000L;
    private static final long T0 = 28_300_000L * M;

    private static OrderTargetInfoTest leg(String sym, long t, float entry, float qty) {
        return new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, qty, 1, sym, t, t, OrderSide.BUY);
    }

    private static KlineObjectSimple ticker(float close) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.priceClose = close;
        k.priceOpen = close;
        k.minPrice = close;
        k.maxPrice = close;
        k.startTime = T0;
        return k;
    }

    // ------------------------------------------------ 1. luat trung symbol
    @Test
    public void sleeveNeverOpensSymbolHeldByBase() {
        // inSleeve=true => luon NONE bat ke mode / ben kia giu hay khong
        for (String m : new String[]{"M1", "M2", "M3"}) {
            assertEquals("NONE", mergeDecision(m, true, true, false));
            assertEquals("NONE", mergeDecision(m, true, false, true));
        }
    }

    @Test
    public void baseOnSleeveHeldSymbolRoutesPerMode() {
        assertEquals("MERGE_BASE", mergeDecision("M1", false, false, true));
        assertEquals("MERGE_SLEEVE", mergeDecision("M2", false, false, true));
        assertEquals("SPLIT", mergeDecision("M3", false, false, true));
        assertEquals("NONE", mergeDecision("NONE", false, false, true));
    }

    @Test
    public void baseAlreadyHeldOrNothingOnOtherSideIsNoMerge() {
        assertEquals("NONE", mergeDecision("M1", false, true, true));    // nen da giu => lenh thuong
        assertEquals("NONE", mergeDecision("M1", false, false, false));  // khong ai giu
        assertEquals("NONE", mergeDecision("xx", false, false, true));   // mode la
    }

    // ------------------------------------------------ 2. gop cum: qty, entry, 1 stop
    @Test
    public void mergeCombinesQuantityAndWeightedEntry() {
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        OrderTargetInfoTest slv = leg("ABCUSDT", T0 - 30 * M, 100f, 2f);   // sleeve: 2 @ 100
        OrderTargetInfoTest bas = leg("ABCUSDT", T0, 90f, 1f);             // nen: 1 @ 90
        List<OrderTargetInfoTest> legs = new ArrayList<>();
        legs.add(slv);
        legs.add(bas);
        OrderTargetInfoTest merged = sim.mergeOrder(legs, ticker(95f), slv);
        assertEquals(3f, merged.quantity, 1e-6f);
        assertEquals((2f * 100f + 1f * 90f) / 3f, merged.priceEntry, 1e-6f);
        assertEquals(T0 - 30 * M, merged.clusterFirstLegTime);            // dong ho tu leg dau (sleeve)
        assertEquals(100f, merged.firstEntryPrice, 1e-6f);                // hard-SL giu gia entry dau
        assertEquals(2, merged.legCount);
    }

    @Test
    public void mergedPositionHasExactlyOneStopLevel() {
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        OrderTargetInfoTest slv = leg("ABCUSDT", T0 - 30 * M, 100f, 2f);
        slv.priceSL = 80f;                                                // sleeve da arm stop
        List<OrderTargetInfoTest> legs = new ArrayList<>();
        legs.add(slv);
        legs.add(leg("ABCUSDT", T0, 90f, 1f));
        OrderTargetInfoTest merged = sim.mergeOrder(legs, ticker(95f), slv);
        // [NUP4] quy uoc da dang ky: gop => stop RESET, arm lai theo luat cua so quan ly (1 stop duy nhat)
        assertTrue(singleStopAfterMerge(merged));
        assertNull(merged.priceSL);
    }

    // ------------------------------------------------ 3. tach PnL theo qty/chu so huu
    @Test
    public void pnlSplitsByQuantityAndEntryPerOwner() {
        Configs.RATE_FEE = 0.001f;
        Configs.APPLY_SLIPPAGE = false;
        OrderTargetInfoTest slv = leg("ABCUSDT", T0 - 30 * M, 100f, 2f);
        OrderTargetInfoTest bas = leg("ABCUSDT", T0, 90f, 1f);
        OrderTargetInfoTest slv2 = leg("ABCUSDT", T0 + M, 95f, 1f);        // DCA sau gop (chu so huu rieng)
        float exit = 110f;
        for (OrderTargetInfoTest o : new OrderTargetInfoTest[]{slv, bas, slv2}) o.priceTP = exit;
        Map<String, String> owner = new HashMap<>();
        owner.put("ABCUSDT|" + slv.timeStart, "S");
        owner.put("ABCUSDT|" + bas.timeStart, "B");
        owner.put("ABCUSDT|" + slv2.timeStart, "B");                       // DCA sau gop do NEN tao => B
        List<OrderTargetInfoTest> legs = new ArrayList<>();
        legs.add(slv);
        legs.add(bas);
        legs.add(slv2);
        Map<String, Double> p = pnlByOwner(legs, owner);
        double total = 0.0;
        for (OrderTargetInfoTest o : legs) total += o.calTp();
        assertEquals(total, p.get("B") + p.get("S"), 1e-3);
        // sleeve: 2*(110-100) - 0.001*2*100 = 19,8
        assertEquals(19.8, p.get("S"), 1e-2);
        // base: 1*(110-90) - 0.001*1*90 + 1*(110-95) - 0.001*1*95 = 20-0,09+15-0,095 = 34,815
        assertEquals(34.815, p.get("B"), 1e-2);
    }

    @Test
    public void ownerMissingFallsBackToBase() {
        Configs.RATE_FEE = 0.0f;
        Configs.APPLY_SLIPPAGE = false;
        OrderTargetInfoTest o = leg("ZZZUSDT", T0, 10f, 1f);
        o.priceTP = 11f;
        List<OrderTargetInfoTest> legs = new ArrayList<>();
        legs.add(o);
        Map<String, Double> p = pnlByOwner(legs, new HashMap<>());
        assertEquals(1.0, p.get("B"), 1e-6);
        assertEquals(0.0, p.get("S"), 1e-6);
    }

    // ------------------------------------------------ 4. kill-switch / U tren equity GOP
    @Test
    public void combinedEquityAndUIncludeBothBooks() {
        float eqBase = 100f;
        float sleeveProfit = -20f;                    // sleeve lo => equity gop giam
        float eq = equityCommon(eqBase, 0f, 0f, sleeveProfit);
        assertEquals(80f, eq, 1e-6f);
        float u = uTotal(60f + 30f, eq);               // notional nen + sleeve / equity GOP
        assertEquals(1.125f, u, 1e-6f);
        assertTrue(uTotalFail(u));                     // A40/U: vuot 1,0 => FAIL ky thuat
        assertFalse(uTotalFail(uTotal(50f + 20f, eq)));
    }

    @Test
    public void sleeveLossReducesCombinedEquityUsedByKillSwitch() {
        float eqUp = equityCommon(100f, 0f, 0f, 10f);
        float eqDown = equityCommon(100f, 0f, 0f, -10f);
        assertTrue(eqUp > eqDown);
        assertEquals(90f, eqDown, 1e-6f);
    }
}
