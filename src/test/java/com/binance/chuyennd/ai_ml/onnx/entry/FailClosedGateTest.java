package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.lang.reflect.Field;
import java.lang.reflect.Method;

import static org.junit.Assert.*;

/**
 * [V12 SAFE C10] patch audD failclosed: LIVE gate bat => p15/thr NaN/±Inf => REJECT (FAIL-CLOSED), r khong huu han
 * KHONG vao buffer/persist; LIVE gate tat (sim) => hanh vi cu (NaN < thr = false => PASS) va bo dem khong tang.
 */
public class FailClosedGateTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    private static final long MIN = 60_000L;
    private static final float SP = 0.1f;

    @Before
    public void setUp() {
        LiveGateRollingRatio.resetForTest();
    }

    @After
    public void tearDown() {
        LiveGateRollingRatio.resetForTest();
    }

    private void liveOn() {
        LiveGateRollingRatio.configureForTest(0.9f, 90);
        LiveGateRollingRatio.setPersistFileForTest(new File(tmp.getRoot(), "gate_ratio_live.bin").getPath());
    }

    private static AiPredictionData pred(long ts, float p15) {
        return new AiPredictionData(ts, p15, 0f);
    }

    private static int pending() throws Exception {
        Field f = LiveGateRollingRatio.class.getDeclaredField("pendingCount");
        f.setAccessible(true);
        return f.getInt(null);
    }

    private static AIRejectFilter.FilterResult evaluate(float p, float thr) throws Exception {
        Method m = AIRejectFilter.class.getDeclaredMethod("evaluate", float.class, float.class);
        m.setAccessible(true);
        return (AIRejectFilter.FilterResult) m.invoke(new AIRejectFilter(), p, thr);
    }

    @Test
    public void liveOnNonFiniteP15RejectsAndBufferUntouched() throws Exception {
        liveOn();
        AIRejectFilter f = new AIRejectFilter();
        float[] bad = {Float.NaN, Float.POSITIVE_INFINITY, Float.NEGATIVE_INFINITY};
        int c0 = AIRejectFilter.nonFiniteRejectCount.get();
        for (int i = 0; i < bad.length; i++) {
            AIRejectFilter.FilterResult r = f.entryGate(pred(i * MIN, bad[i]), SP, true);
            assertEquals("p15=" + bad[i], AIRejectFilter.FilterDecision.REJECT, r.decision);
            assertTrue(r.reason, r.reason.startsWith("FAIL-CLOSED"));
        }
        assertEquals(3, AIRejectFilter.nonFiniteRejectCount.get() - c0);
        assertEquals(0, LiveGateRollingRatio.bufferSizeForTest());
        assertEquals(0, pending());
    }

    @Test
    public void liveOnNonFiniteSymbolPredRejects() throws Exception {
        liveOn();
        AIRejectFilter f = new AIRejectFilter();
        AIRejectFilter.FilterResult r = f.entryGate(pred(0L, 5.0f), Float.NaN, true);
        assertEquals(AIRejectFilter.FilterDecision.REJECT, r.decision);
        assertEquals(0, LiveGateRollingRatio.bufferSizeForTest());
        assertEquals(0, pending());
    }

    @Test
    public void liveOnThresholdNonFiniteReturnsNaNWithoutLoading() throws Exception {
        liveOn();
        assertTrue(Float.isNaN(LiveGateRollingRatio.threshold(0L, Float.NaN, SP)));
        assertTrue(Float.isNaN(LiveGateRollingRatio.threshold(MIN, Float.POSITIVE_INFINITY, SP)));
        assertTrue(Float.isNaN(LiveGateRollingRatio.threshold(2 * MIN, Float.NEGATIVE_INFINITY, SP)));
        assertEquals(0, LiveGateRollingRatio.bufferSizeForTest());
        assertEquals(0, pending());
        // r huu han: nap + persist pending nhu cu
        float q = LiveGateRollingRatio.threshold(3 * MIN, 0.05f, SP);
        assertTrue(Float.isFinite(q));
        assertEquals(1, LiveGateRollingRatio.bufferSizeForTest());
        assertEquals(1, pending());
    }

    @Test
    public void liveOnFiniteUnchanged() throws Exception {
        liveOn();
        AIRejectFilter f = new AIRejectFilter();
        int c0 = AIRejectFilter.nonFiniteRejectCount.get();
        AIRejectFilter.FilterResult r = f.entryGate(pred(0L, 5.0f), SP, true);   // warm-up => base
        assertEquals(AIRejectFilter.FilterDecision.PASS, r.decision);
        assertEquals(1, LiveGateRollingRatio.bufferSizeForTest());
        assertEquals(0, AIRejectFilter.nonFiniteRejectCount.get() - c0);
    }

    @Test
    public void liveOnEvaluateThresholdNonFinite() throws Exception {
        liveOn();
        assertEquals(AIRejectFilter.FilterDecision.REJECT, evaluate(1f, Float.NaN).decision);
        assertEquals(AIRejectFilter.FilterDecision.REJECT, evaluate(1f, Float.NEGATIVE_INFINITY).decision);
        assertTrue(evaluate(1f, Float.NEGATIVE_INFINITY).reason.startsWith("FAIL-CLOSED"));
        // +Inf thr: REJECT qua nhanh cu (BAD MOMENTUM)
        AIRejectFilter.FilterResult r = evaluate(1f, Float.POSITIVE_INFINITY);
        assertEquals(AIRejectFilter.FilterDecision.REJECT, r.decision);
        assertTrue(r.reason.startsWith("BAD MOMENTUM"));
        assertEquals(AIRejectFilter.FilterDecision.PASS, evaluate(0.05f, 0.01f).decision);
    }

    /** Key LIVE tat (sim / backtest): hanh vi cu y nguyen — NaN PASS, bo dem fail-closed khong tang. */
    @Test
    public void liveOffKeepsOldBehaviour() throws Exception {
        assertFalse(LiveGateRollingRatio.isOn());
        int c0 = AIRejectFilter.nonFiniteRejectCount.get();
        assertEquals(AIRejectFilter.FilterDecision.PASS, evaluate(Float.NaN, 0.01f).decision);
        assertEquals(AIRejectFilter.FilterDecision.PASS, evaluate(1f, Float.NaN).decision);
        assertEquals(AIRejectFilter.FilterDecision.PASS, evaluate(Float.POSITIVE_INFINITY, 0.01f).decision);
        assertEquals(AIRejectFilter.FilterDecision.REJECT, evaluate(Float.NEGATIVE_INFINITY, 0.01f).decision);
        AIRejectFilter.FilterResult r = new AIRejectFilter().entryGate(pred(0L, Float.NaN), null, false);
        assertEquals(AIRejectFilter.FilterDecision.PASS, r.decision);
        assertEquals(0, AIRejectFilter.nonFiniteRejectCount.get() - c0);
    }
}
