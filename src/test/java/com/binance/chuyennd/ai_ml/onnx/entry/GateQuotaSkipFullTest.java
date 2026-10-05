package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * GATE_QUOTA_SKIPFULL (docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md): key GATE_QUOTA_SKIP_WHEN_FULL.
 * ON + so day => r KHONG nap buffer, KHONG pass; OFF => y het ban 3 tham so; ON + so khong day => y het OFF.
 */
public class GateQuotaSkipFullTest {

    private static final long MIN = 60_000L;
    private static final long HOUR = 3600_000L;
    private static final long DAY = 86_400_000L;
    private static final float SP = 0.1f;
    private boolean saved;

    @Before
    public void setUp() {
        saved = Configs.GATE_QUOTA_SKIP_WHEN_FULL;
        LiveGateRollingRatio.resetForTest();
        GateRollingRatio.configureForTest(0.9f, 90);
    }

    @After
    public void tearDown() {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = saved;
        LiveGateRollingRatio.resetForTest();
    }

    private static AiPredictionData pred(long ts, float p15) {
        return new AiPredictionData(ts, p15, 0f);
    }

    @Test
    public void keyDefaultIsOff() {
        assertFalse("GATE_QUOTA_SKIP_WHEN_FULL mac dinh phai false", saved);
    }

    /** ON + so day: REJECT, buffer KHONG tang, pass KHONG tang, seen van dem; so khong day => PASS nhu thuong. */
    @Test
    public void onBookFullSkipsBufferAndPass() {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = true;
        AIRejectFilter f = new AIRejectFilter();
        AIRejectFilter.FilterResult r = f.entryGate(pred(0L, 0.5f), SP, true, true);
        assertEquals(AIRejectFilter.FilterDecision.REJECT, r.decision);
        assertEquals(0, GateRollingRatio.bufferSizeForTest());
        assertEquals(0L, GateRollingRatio.passForTest());
        assertEquals(1L, GateRollingRatio.seenForTest());
        assertEquals(1L, GateRollingRatio.skipFullForTest());
        AIRejectFilter.FilterResult r2 = f.entryGate(pred(MIN, 0.5f), SP, true, false);
        assertEquals(AIRejectFilter.FilterDecision.PASS, r2.decision);
        assertEquals(1, GateRollingRatio.bufferSizeForTest());
        assertEquals(1L, GateRollingRatio.passForTest());
        assertEquals(2L, GateRollingRatio.seenForTest());
    }

    /** OFF + bookFull=true: y het ban 3 tham so (quyet dinh, ly do, buffer, pass). */
    @Test
    public void offBookFullIdenticalToLegacy() {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = false;
        AIRejectFilter f = new AIRejectFilter();
        AIRejectFilter.FilterResult a = f.entryGate(pred(0L, 0.5f), SP, true, true);
        int bufA = GateRollingRatio.bufferSizeForTest();
        long passA = GateRollingRatio.passForTest();
        GateRollingRatio.configureForTest(0.9f, 90);
        AIRejectFilter.FilterResult b = f.entryGate(pred(0L, 0.5f), SP, true);
        assertEquals(b.decision, a.decision);
        assertEquals(b.reason, a.reason);
        assertEquals(GateRollingRatio.bufferSizeForTest(), bufA);
        assertEquals(GateRollingRatio.passForTest(), passA);
        assertEquals(1, bufA);
    }

    /** ON khong anh huong leg khong phai PREDICT (BIG_DOWN / DCA: predictSymbolTrade=false) du so day. */
    @Test
    public void onDoesNotTouchNonPredictLegs() {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = true;
        AIRejectFilter f = new AIRejectFilter();
        AIRejectFilter.FilterResult a = f.entryGate(pred(0L, 0.5f), SP, false, true);
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = false;
        AIRejectFilter.FilterResult b = f.entryGate(pred(0L, 0.5f), SP, false);
        assertEquals(b.decision, a.decision);
        assertEquals(b.reason, a.reason);
        assertEquals(0L, GateRollingRatio.skipFullForTest());
        assertEquals(0, GateRollingRatio.bufferSizeForTest());
    }

    private static String[] runSeq(boolean keyOn) {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = keyOn;
        GateRollingRatio.configureForTest(0.9f, 90);
        AIRejectFilter f = new AIRejectFilter();
        String[] out = new String[960];
        for (int i = 0; i < 960; i++) {
            float p15 = ((i * 37) % 100) / 1000f;
            out[i] = f.entryGate(pred(i * 15L * MIN, p15), SP, true, false).decision.name();
        }
        return out;
    }

    /** ON + so KHONG day = OFF tren chuoi 10 ngay (qua warm-up): cung quyet dinh tung ung vien. */
    @Test
    public void onNotFullEqualsOff() {
        String[] on = runSeq(true);
        int bufOn = GateRollingRatio.bufferSizeForTest();
        String[] off = runSeq(false);
        assertEquals(GateRollingRatio.bufferSizeForTest(), bufOn);
        for (int i = 0; i < on.length; i++) assertEquals("i=" + i, off[i], on[i]);
    }

    private static float qAfter(boolean keyOn, boolean withHuge) {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = keyOn;
        GateRollingRatio.configureForTest(0.9f, 90);
        AIRejectFilter f = new AIRejectFilter();
        for (int i = 0; i < 40; i++) f.entryGate(pred(i * 5L * HOUR, 0.001f * (i % 10)), SP, true, false);
        if (withHuge) {
            for (int j = 0; j < 10; j++) f.entryGate(pred(9L * DAY + j * MIN, 5.0f), SP, true, true);
        }
        return GateRollingRatio.addAndQuery(9L * DAY + 2 * HOUR, 0f);
    }

    /** r cuc tri luc so day: ON => KHONG vao q_t (q = nhu chua tung co); OFF => keo q_t len. */
    @Test
    public void skippedSamplesExcludedFromQuantile() {
        float qOnHuge = qAfter(true, true);
        float qNoHuge = qAfter(false, false);
        float qOffHuge = qAfter(false, true);
        assertEquals(qNoHuge, qOnHuge, 0f);
        assertTrue("OFF phai nap r cuc tri: " + qOffHuge + " vs " + qOnHuge, qOffHuge > qOnHuge);
    }

    /** Dieu kien so day = managerBudget null dung o U = U_MAX (cung ham, khong chep cong thuc). */
    @Test
    public void bookFullBoundaryIsManagerBudgetNull() {
        float eq = 35000f;
        assertNull(TradeUtils.managerBudget(null, eq * Configs.U_MAX, eq, MarketLevelChange.PREDICT_SYMBOL_TRADE));
        assertNotNull(TradeUtils.managerBudget(null, eq * Configs.U_MAX * 0.99f, eq, MarketLevelChange.PREDICT_SYMBOL_TRADE));
        assertNull(TradeUtils.managerBudget(null, 0f, 0f, MarketLevelChange.PREDICT_SYMBOL_TRADE));
    }
}
