package com.binance.chuyennd.research;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.After;
import org.junit.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.Assert.*;

/** [NUP3B] BASE_SKIP_SLEEVE_SYMBOLS (PREREG_NUP3B §2, S1x): so nen coi symbol sleeve dang giu la 'dang giu'. */
public class Nup3bBaseSkipTest {

    private static final long T = 28_333_334L * 60_000L;

    private static OrderTargetInfoTest cl(long t0) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 1f, null, 1f, 1, "XUSDT", t0, t0, OrderSide.BUY);
        o.clusterFirstLegTime = t0;
        return o;
    }

    private static SimulatorMarketLevelTicker1MStopLoss sim() {
        SimulatorMarketLevelTicker1MStopLoss s = new SimulatorMarketLevelTicker1MStopLoss();
        s.allOrderDone = new java.util.TreeMap<>();
        s.initSleeveForTest("V1");
        return s;
    }

    @After
    public void reset() {
        Configs.BASE_SKIP_SLEEVE_SYMBOLS = false;
        BudgetManagerSimple.resetInstance();
    }

    @Test
    public void flagOffNeverSkips() {
        Configs.BASE_SKIP_SLEEVE_SYMBOLS = false;
        SimulatorMarketLevelTicker1MStopLoss s = sim();
        s.sleeveBook.symbol2OrderRunning[5] = cl(T);
        assertFalse(s.baseSkipSleeveSym((short) 5, T, MarketLevelChange.PREDICT_SYMBOL_TRADE));
        Set<Short> locked = new HashSet<>();
        s.sleeveBook.activeRunningIds[0] = 5;
        s.sleeveBook.activeRunningCount = 1;
        assertEquals(0, s.slBaseSkipPred + s.slBaseSkipLocked);
        assertTrue(locked.isEmpty());
    }

    @Test
    public void flagOnSkipsSleeveHeldSymbolOncePerSleeveCluster() {
        Configs.BASE_SKIP_SLEEVE_SYMBOLS = true;
        SimulatorMarketLevelTicker1MStopLoss s = sim();
        s.sleeveBook.symbol2OrderRunning[5] = cl(T);
        assertTrue(s.baseSkipSleeveSym((short) 5, T + 60_000L, MarketLevelChange.PREDICT_SYMBOL_TRADE));
        assertTrue(s.baseSkipSleeveSym((short) 5, T + 120_000L, MarketLevelChange.PREDICT_SYMBOL_TRADE));
        assertEquals(2, s.slBaseSkipPred);
        assertEquals(1, s.slBaseSkipDistinct.size());       // cung cum sleeve => 1 cum nen bi bo
        assertFalse(s.baseSkipSleeveSym((short) 6, T, MarketLevelChange.PREDICT_SYMBOL_TRADE));  // sleeve khong giu
    }

    @Test
    public void noSkipWhenBaseAlreadyHoldsOrInSleevePhase() {
        Configs.BASE_SKIP_SLEEVE_SYMBOLS = true;
        SimulatorMarketLevelTicker1MStopLoss s = sim();
        s.sleeveBook.symbol2OrderRunning[5] = cl(T);
        s.symbol2OrderRunning[5] = cl(T);                    // nen dang giu => khong phai 'mo cum moi'
        assertFalse(s.baseSkipSleeveSym((short) 5, T, MarketLevelChange.PREDICT_SYMBOL_TRADE));
        s.symbol2OrderRunning[5] = null;
        s.enterSleeve();                                     // pha sleeve: luat chi ap cho so nen
        assertFalse(s.baseSkipSleeveSym((short) 5, T, MarketLevelChange.PREDICT_SYMBOL_TRADE));
        s.exitSleeve();
        assertTrue(s.baseSkipSleeveSym((short) 5, T, MarketLevelChange.PREDICT_SYMBOL_TRADE));
    }

    @Test
    public void sleeveOffNeverSkips() {
        Configs.BASE_SKIP_SLEEVE_SYMBOLS = true;
        SimulatorMarketLevelTicker1MStopLoss s = new SimulatorMarketLevelTicker1MStopLoss();
        assertNull(s.sleeveBook);
        assertFalse(s.baseSkipSleeveSym((short) 5, T, MarketLevelChange.PREDICT_SYMBOL_TRADE));
    }

    @Test
    public void bigDownLockedSetGetsSleeveHeldSymbols() {
        Configs.BASE_SKIP_SLEEVE_SYMBOLS = true;
        SimulatorMarketLevelTicker1MStopLoss s = sim();
        s.sleeveBook.symbol2OrderRunning[5] = cl(T);
        s.sleeveBook.symbol2OrderRunning[9] = cl(T);
        s.sleeveBook.activeRunningIds[0] = 5;
        s.sleeveBook.activeRunningIds[1] = 9;
        s.sleeveBook.activeRunningCount = 2;
        s.symbol2OrderRunning[9] = cl(T);                    // 9: nen cung giu (overlap cu) => da khoa san
        Set<Short> locked = new HashSet<>();
        locked.add((short) 9);
        s.addSleeveLocked(locked, T);
        assertTrue(locked.contains((short) 5));
        assertTrue(locked.contains((short) 9));
        assertEquals(2, locked.size());
        assertEquals(1, s.slBaseSkipLocked);
    }
}
