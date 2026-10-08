package com.binance.chuyennd.research;

import com.binance.chuyennd.ai_ml.onnx.entry.NselGate;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.After;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * NSEL J-A (docs/prereg/PREREG_NSEL.md §3) phia simulator: CORE_ADD toi da 1/cum va CHI khi leg0 tang THEM,
 * chan CORE_ADD khong tinh bac grid, OFF => phep dem cu (byte-identical), nen "sap" cua penalty dung bien -1%,
 * selectCands K tuong minh, enum CORE_ADD them CUOI (khong doi ordinal cu).
 */
public class NselCoreAddTest {

    private final boolean coreAdd0 = Configs.NSEL_CORE_ADD;
    private final boolean dcaSig0 = Configs.DCA_SIGNAL_GATE;

    @After
    public void restore() {
        Configs.NSEL_CORE_ADD = coreAdd0;
        Configs.DCA_SIGNAL_GATE = dcaSig0;
    }

    /** symbol=null co chu dich: ctor chi goi SimpleSymbolMapper khi symbol != null (tranh Aerospike). */
    private static OrderTargetInfoTest leg(long t, int tier) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 100f, null, 1f,
                Configs.LEVERAGE_ORDER, null, t, t, OrderSide.BUY);
        o.nselTier = tier;
        return o;
    }

    private static List<OrderTargetInfoTest> legs(int... tiers) {
        List<OrderTargetInfoTest> l = new ArrayList<>();
        long t = 1_600_000_000_000L;
        for (int s : tiers) l.add(leg(t += 60_000L, s));
        return l;
    }

    private static final int C = NselGate.TIER_CORE, A = NselGate.TIER_ADD, X = NselGate.TIER_CORE_ADD;

    /** OFF (ca DCA_SIGNAL_GATE va NSEL_CORE_ADD tat) => gridLegCount == size() ke ca khi co chan danh dau CORE_ADD. */
    @Test
    public void offGridCountIsSize() {
        Configs.NSEL_CORE_ADD = false;
        Configs.DCA_SIGNAL_GATE = false;
        assertEquals(0, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(null));
        assertEquals(1, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(A)));
        assertEquals(3, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(A, X, C)));
    }

    /** ON: chan CORE_ADD KHONG an mat bac grid (bac DCA ke khong dich). */
    @Test
    public void coreAddLegNotInGrid() {
        Configs.NSEL_CORE_ADD = true;
        assertEquals(1, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(A, X)));
        assertEquals(2, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(A, X, C)));
        assertEquals(2, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(C, C)));
    }

    /** CORE_ADD chi khi leg0 tang THEM; toi da NSEL_CORE_ADD_MAX_PER_CLUSTER (1) moi cum. */
    @Test
    public void coreAddEligibilityMaxOneAndLeg0Add() {
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(legs(A), 1));
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(legs(A, C), 1));   // leg DCA grid (tier 0) khong tinh
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(legs(A, X), 1));  // da co 1 CORE_ADD
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(legs(C), 1));     // leg0 LOI
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(legs(C, A), 1));  // leg0 LOI (A khong phai leg0)
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(new ArrayList<>(), 1));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(null, 1));
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(legs(A, X), 2));
        assertEquals(A, SimulatorMarketLevelTicker1MStopLoss.clusterLeg0Tier(legs(A, X)));
        assertEquals(1, SimulatorMarketLevelTicker1MStopLoss.countCoreAdd(legs(A, X, C)));
        assertEquals(-1, SimulatorMarketLevelTicker1MStopLoss.clusterLeg0Tier(null));
    }

    /** Mac dinh moi chan cu = tang LOI (0) => khong cum nao co leg0 THEM khi NSEL OFF => khong CORE_ADD. */
    @Test
    public void defaultTierIsCore() {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 100f, null, 1f,
                Configs.LEVERAGE_ORDER, null, 1L, 1L, OrderSide.BUY);
        assertEquals(NselGate.TIER_CORE, o.nselTier);
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.coreAddClusterEligible(java.util.Collections.singletonList(o), 1));
    }

    /**
     * Penalty: nen quyet dinh "sap" ⇔ float32 (close-open)/open <= -0.01f (y het efd85d6d); bien -1% = sap.
     * Ham khong nhan loai chan => ap MOI loai chan (PREDICT/BIG_DOWN/DCA/CORE_ADD) tai call-site createOrder.
     */
    @Test
    public void crashBarBoundary() {
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.isCrashBar(99f, 100f));       // dung -1%
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.isCrashBar(99.01f, 100f));   // -0.99%
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.isCrashBar(50f, 100f));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.isCrashBar(101f, 100f));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.isCrashBar(100f, 100f));
        // cung bieu thuc voi F1 (NselGate.f1Pass nhan (c-o)/o): -1% chinh xac la sap
        float br = (99f - 100f) / 100f;
        assertTrue(br <= -0.01f);
    }

    /** selectCands(K) lay DUNG min(K, len) phan tu dau, giu thu tu (K = max(K_LOI, K_THEM) khi NSEL bat). */
    @Test
    public void selectCandsExplicitK() {
        long[] pred = new long[40];
        for (int i = 0; i < pred.length; i++) pred[i] = ((long) (i + 1) << 32) | (Float.floatToIntBits(0.01f * i) & 0xFFFFFFFFL);
        List<Long> got = SimulatorMarketLevelTicker1MStopLoss.selectCands(pred, 32);
        assertEquals(32, got.size());
        for (int i = 0; i < got.size(); i++) assertEquals(pred[i], (long) got.get(i));
        assertEquals(5, SimulatorMarketLevelTicker1MStopLoss.selectCands(new long[]{1, 2, 3, 4, 5}, 32).size());
        assertEquals(0, SimulatorMarketLevelTicker1MStopLoss.selectCands(new long[0], 32).size());
    }

    /** CORE_ADD them CUOI enum: ordinal hang cu khong doi; printDone ghi "CORE_ADD". */
    @Test
    public void coreAddEnumAppendedLast() {
        MarketLevelChange[] v = MarketLevelChange.values();
        assertEquals(MarketLevelChange.CORE_ADD, v[v.length - 1]);
        assertEquals(MarketLevelChange.FORCED_SELLER, v[v.length - 2]);
        assertEquals("CORE_ADD", MarketLevelChange.CORE_ADD.toString());
    }
}
