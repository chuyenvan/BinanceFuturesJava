package com.binance.chuyennd.research;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.Test;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayDeque;
import java.util.Collections;

import static com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss.*;
import static org.junit.Assert.*;

/**
 * [NUP3-SLEEVE] docs/prereg/PREREG_NUP3.md — dieu kien mo V0/V1/V2, symbol doc quyen, throttle U_s/U_S_MAX,
 * U tong, nhan book, swap so (sleeve khong ghi vao state so nen), dem leg dau cum nen+sleeve.
 */
public class Nup3SleeveTest {

    private static final long M = 60_000L;
    private static final long T = 28_333_334L * M;   // moc phut chan

    private static OrderTargetInfoTest dummy() {
        return new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 1f, null, 1f, 1, "XUSDT", 0L, 0L, OrderSide.BUY);
    }

    // ---------------------------------------------------------------- dieu kien MO tung arm
    @Test
    public void v0OpensUnconditionally() {
        assertTrue(sleeveArmAllows("V0", 0, 10, false));
        assertTrue(sleeveArmAllows("V0", 99, 10, false));
        assertTrue(sleeveArmAllows("V0", 99, 10, true));
    }

    @Test
    public void v1BlocksWhenTenOrMoreFirstLegsInLastHour() {
        assertTrue(sleeveArmAllows("V1", 9, 10, false));
        assertFalse(sleeveArmAllows("V1", 10, 10, true));
        assertFalse(sleeveArmAllows("V1", 11, 10, false));
    }

    @Test
    public void v2OpensOnlyOnMarketFlag() {
        assertTrue(sleeveArmAllows("V2", 0, 10, true));
        assertTrue(sleeveArmAllows("V2", 99, 10, true));
        assertFalse(sleeveArmAllows("V2", 0, 10, false));
    }

    @Test(expected = IllegalArgumentException.class)
    public void unknownArmThrows() {
        sleeveArmAllows("V3", 0, 10, true);
    }

    @Test
    public void burstWindowIsHalfOpenLast60Minutes() {
        ArrayDeque<Long> dq = new ArrayDeque<>();
        dq.add(T - 61 * M);
        dq.add(T - 60 * M);
        dq.add(T - 30 * M);
        dq.add(T - M);
        dq.add(T);
        dq.add(T);
        // [t-60', t): t-60' TINH, t-61' bi cat, 2 moc tai t KHONG tinh
        assertEquals(3, burstCount(dq, T, 60 * M));
        assertEquals(5, dq.size());
    }

    @Test
    public void burstTenLegsBlocksThenExpires() {
        ArrayDeque<Long> dq = new ArrayDeque<>();
        for (int i = 0; i < 10; i++) dq.add(T - (59 - i) * M);      // T-59' .. T-50'
        assertEquals(10, burstCount(dq, T, 60 * M));
        assertFalse(sleeveArmAllows("V1", burstCount(dq, T, 60 * M), 10, false));
        assertEquals(10, burstCount(dq, T + M, 60 * M));               // T-59' == (T+1') - 60' => van tinh
        int n = burstCount(dq, T + 2 * M, 60 * M);                     // T-59' < T-58' => cat
        assertEquals(9, n);
        assertTrue(sleeveArmAllows("V1", n, 10, false));
    }

    @Test
    public void flagLookupHalfOpenIntervals() {
        long[] s = {T, T + 10 * M};
        long[] e = {T + 3 * M, T + 11 * M};
        assertFalse(flagAt(s, e, T - M));
        assertTrue(flagAt(s, e, T));
        assertTrue(flagAt(s, e, T + 2 * M));
        assertFalse(flagAt(s, e, T + 3 * M));
        assertFalse(flagAt(s, e, T + 9 * M));
        assertTrue(flagAt(s, e, T + 10 * M));
        assertFalse(flagAt(s, e, T + 11 * M));
        assertFalse(flagAt(new long[0], new long[0], T));
    }

    @Test
    public void flagFileLoads() throws Exception {
        File f = File.createTempFile("nup3flag", ".csv");
        f.deleteOnExit();
        Files.write(f.toPath(), ("start_ms,end_ms\n" + T + "," + (T + 3 * M) + "\n" + (T + 10 * M) + "," + (T + 11 * M) + "\n").getBytes());
        long[][] iv = loadFlagIntervals(f);
        assertArrayEquals(new long[]{T, T + 10 * M}, iv[0]);
        assertArrayEquals(new long[]{T + 3 * M, T + 11 * M}, iv[1]);
    }

    @Test(expected = java.io.IOException.class)
    public void flagFileRejectsOverlap() throws Exception {
        File f = File.createTempFile("nup3flag", ".csv");
        f.deleteOnExit();
        Files.write(f.toPath(), ("start_ms,end_ms\n" + T + "," + (T + 3 * M) + "\n" + (T + 2 * M) + "," + (T + 5 * M) + "\n").getBytes());
        loadFlagIntervals(f);
    }

    @Test(expected = java.io.IOException.class)
    public void flagFileRejectsNonMinute() throws Exception {
        File f = File.createTempFile("nup3flag", ".csv");
        f.deleteOnExit();
        Files.write(f.toPath(), ("start_ms,end_ms\n" + (T + 1) + "," + (T + 3 * M) + "\n").getBytes());
        loadFlagIntervals(f);
    }

    // ---------------------------------------------------------------- throttle U_s / U_S_MAX = 0.35
    @Test
    public void throttleUsOverUsMax() {
        float eq = 100_000f;
        float uMax = 0.35f;
        float ladder = Configs.dcaGridTotalWeight();
        if (ladder <= 0f) ladder = 1f;
        float full = eq * Configs.F_BASE / ladder;
        assertEquals(full, TradeUtils.managerBudgetSleeve(0f, eq, uMax), 1e-3f);
        assertEquals(full, TradeUtils.managerBudgetSleeve(null, eq, uMax), 1e-3f);
        assertEquals(full * 0.5f, TradeUtils.managerBudgetSleeve(0.175f * eq, eq, uMax), 1e-2f);
        assertEquals(full * (1f - 0.30f / 0.35f), TradeUtils.managerBudgetSleeve(0.30f * eq, eq, uMax), 1e-2f);
        assertNotNull(TradeUtils.managerBudgetSleeve(0.34f * eq, eq, uMax));
        assertNull(TradeUtils.managerBudgetSleeve(uMax, 1f, uMax));          // U_s == U_S_MAX => chan
        assertNull(TradeUtils.managerBudgetSleeve(0.36f * eq, eq, uMax));
        assertNull(TradeUtils.managerBudgetSleeve(0.50f * eq, eq, uMax));    // nen U_MAX 0.60 KHONG lien quan
        assertNull(TradeUtils.managerBudgetSleeve(0f, 0f, uMax));
        assertNull(TradeUtils.managerBudgetSleeve(0f, null, uMax));
    }

    @Test
    public void equityCommonAddsSleevePnl() {
        assertEquals(100_000f + 1_500f - 200f, equityCommon(100_000f, 36_500f, 35_000f, -200f), 1e-3f);
        assertEquals(100_000f, equityCommon(100_000f, 35_000f, 35_000f, 0f), 0f);
    }

    // ---------------------------------------------------------------- U tong <= 1.0
    @Test
    public void uTotalCheck() {
        assertEquals(0.5f, uTotal(50f, 100f), 1e-6f);
        assertFalse(uTotalFail(1.0f));
        assertTrue(uTotalFail(1.0001f));
        assertTrue(uTotalFail(uTotal(1f, 0f)));            // equity <= 0 => FAIL
        float[] acc = new float[3];
        accPosition(2f, 10f, 12f, 9f, acc);                 // vi the nen
        accPosition(1f, 20f, 18f, 15f, acc);                // vi the sleeve
        assertEquals(42f, acc[0], 1e-6f);
        assertEquals(2f, acc[1], 1e-6f);
        assertEquals(-7f, acc[2], 1e-6f);
        float eq = 35_000f + 100f - 50f + acc[1];
        assertEquals(42f / 35_052f, uTotal(acc[0], eq), 1e-9f);
        assertFalse(uTotalFail(uTotal(acc[0], eq)));
    }

    // ---------------------------------------------------------------- symbol doc quyen phia sleeve
    @Test
    public void symbolExclusiveOnSleeveSide() {
        OrderTargetInfoTest[] base = new OrderTargetInfoTest[10];
        OrderTargetInfoTest[] sl = new OrderTargetInfoTest[10];
        assertTrue(sleeveSymbolFree(base, sl, (short) 3));
        base[3] = dummy();
        assertFalse(sleeveSymbolFree(base, sl, (short) 3));
        base[3] = null;
        sl[3] = dummy();
        assertFalse(sleeveSymbolFree(base, sl, (short) 3));
        assertTrue(sleeveSymbolFree(base, sl, (short) 4));
    }

    // ---------------------------------------------------------------- nhan book
    @Test
    public void bookLabelKeepsColumnCountAndBaseBytes() {
        String header = "sym,side,entry,tp,profit,status,start,time_start_format,end,level,maxmin15m,lastentry,volume,"
                + "quantity,margin,pnl,time_order,funding,dow,up,dow15m,pred15m,risk4h,symbolPred,";
        String row = String.join(",", Collections.nCopies(24, "1")) + ",";
        String lab = labelSleeveLine(row);
        assertTrue(lab.endsWith(",book=sleeve"));
        assertEquals(header.split(",", -1).length, lab.split(",", -1).length);
        assertEquals(row, lab.substring(0, lab.length() - "book=sleeve".length()));
        assertEquals("a,b,book=sleeve", labelSleeveLine("a,b"));
        assertFalse(row.contains("book=sleeve"));
    }

    // ---------------------------------------------------------------- swap so: sleeve khong ghi vao state nen
    @Test
    public void swapKeepsBaseStateIntact() {
        BudgetManagerSimple.resetInstance();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.allOrderDone = new java.util.TreeMap<>();
        BudgetManagerSimple baseBm = BudgetManagerSimple.getInstance();
        baseBm.marginRunning = 123f;
        sim.initSleeveForTest("V0");
        Object baseRunning = sim.symbol2OrderRunning;
        Object baseEntries = sim.symbol2OrdersEntry;
        Object baseIds = sim.activeRunningIds;
        Object baseDone = sim.allOrderDone;
        java.util.Set<String> baseTsx = SimulatorMarketLevelTicker1MStopLoss.tsxDeferred;
        sim.activeRunningCount = 2;
        sim.enterSleeve();
        assertTrue(sim.inSleeve);
        assertNotSame(baseRunning, sim.symbol2OrderRunning);
        assertNotSame(baseEntries, sim.symbol2OrdersEntry);
        assertNotSame(baseIds, sim.activeRunningIds);
        assertNotSame(baseDone, sim.allOrderDone);
        assertNotSame(baseTsx, SimulatorMarketLevelTicker1MStopLoss.tsxDeferred);
        assertNotSame(baseBm, BudgetManagerSimple.getInstance());
        assertEquals(0, sim.activeRunningCount);
        BudgetManagerSimple.getInstance().marginRunning += 50f;
        sim.activeRunningCount = 1;
        sim.symbol2OrderRunning[5] = dummy();
        SimulatorMarketLevelTicker1MStopLoss.tsxDeferred.add("X|1");
        sim.exitSleeve();
        assertFalse(sim.inSleeve);
        assertSame(baseRunning, sim.symbol2OrderRunning);
        assertSame(baseEntries, sim.symbol2OrdersEntry);
        assertSame(baseIds, sim.activeRunningIds);
        assertSame(baseDone, sim.allOrderDone);
        assertSame(baseTsx, SimulatorMarketLevelTicker1MStopLoss.tsxDeferred);
        assertSame(baseBm, BudgetManagerSimple.getInstance());
        assertEquals(2, sim.activeRunningCount);
        assertEquals(123f, baseBm.marginRunning, 0f);
        assertNull(sim.symbol2OrderRunning[5]);
        assertFalse(baseTsx.contains("X|1"));
        assertNotNull(sim.sleeveBook.symbol2OrderRunning[5]);
        assertEquals(1, sim.sleeveBook.activeRunningCount);
        assertEquals(50f, sim.sleeveBook.bm.marginRunning, 0f);
        BudgetManagerSimple.resetInstance();
    }

    @Test(expected = IllegalStateException.class)
    public void doubleEnterThrows() {
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.allOrderDone = new java.util.TreeMap<>();
        sim.initSleeveForTest("V0");
        sim.enterSleeve();
        try {
            sim.enterSleeve();
        } finally {
            sim.exitSleeve();
            BudgetManagerSimple.resetInstance();
        }
    }

    @Test
    public void burstCountsBaseAndSleeveFirstLegsAndOverlap() {
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.allOrderDone = new java.util.TreeMap<>();
        sim.initSleeveForTest("V1");
        sim.sleeveNoteNewCluster((short) 1, T - 10 * M);          // leg dau cum so NEN
        sim.enterSleeve();
        sim.sleeveNoteNewCluster((short) 2, T - 5 * M);           // leg dau cum so SLEEVE
        sim.symbol2OrderRunning[7] = dummy();
        sim.exitSleeve();
        assertEquals(2, burstCount(sim.sleeveFirstLegTimes, T, 60 * M));
        assertEquals(1, sim.slClustersBase);
        assertEquals(1, sim.slClustersSleeve);
        assertEquals(0, sim.slOverlap);
        sim.sleeveNoteNewCluster((short) 7, T);                   // nen mo symbol sleeve dang giu => overlap
        assertEquals(1, sim.slOverlap);
        assertEquals(2, burstCount(sim.sleeveFirstLegTimes, T, 60 * M));   // moc tai t khong tinh
        BudgetManagerSimple.resetInstance();
    }

    @Test
    public void sleeveOffMeansNoBook() {
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        assertNull(sim.sleeveBook);
        sim.sleeveNoteNewCluster((short) 1, T);                   // TAT => khong lam gi
        assertTrue(sim.sleeveFirstLegTimes.isEmpty());
    }
}
