package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.selector.LiveBookU;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * [SHADOW2 2026-10-05] (a) key ON + so day: r KHONG vao buffer LIVE, bo dem skipFull (nguon n_skipfull cua dong
 * [GATE]) tang; key OFF / leg khong PREDICT => bo dem khong tang.
 */
public class LiveSkipFullCountTest {

    private static final long MIN = 60_000L;
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

    /** LIVE bat + key ON + bookFull: REJECT, buffer LIVE van 0, bo dem +1. */
    @Test
    public void onBookFullLiveBufferUntouchedAndCounted() {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = true;
        LiveGateRollingRatio.configureForTest(0.9f, 90);
        AIRejectFilter f = new AIRejectFilter();
        int c0 = AIRejectFilter.skipFullCount.get();
        AIRejectFilter.FilterResult r = f.entryGate(pred(0L, 5.0f), SP, true, true);
        assertEquals(AIRejectFilter.FilterDecision.REJECT, r.decision);
        assertTrue(r.reason.startsWith("BOOK FULL"));
        assertEquals(0, LiveGateRollingRatio.bufferSizeForTest());
        assertEquals(0, GateRollingRatio.bufferSizeForTest());
        assertEquals(c0 + 1, AIRejectFilter.skipFullCount.get());
    }

    /** Mot "tick" 5 ung vien (3 so day) => hieu so bo dem = 3 => dong [GATE] in n_skipfull=3. */
    @Test
    public void tickDeltaFeedsGateLine() {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = true;
        AIRejectFilter f = new AIRejectFilter();
        int c0 = AIRejectFilter.skipFullCount.get();
        boolean[] full = {true, false, true, true, false};
        int nRej = 0;
        for (int i = 0; i < full.length; i++) {
            AIRejectFilter.FilterResult r = f.entryGate(pred(i * MIN, 0.5f), SP, true, full[i]);
            if (r.decision == AIRejectFilter.FilterDecision.REJECT) nRej++;
        }
        int nSkip = AIRejectFilter.skipFullCount.get() - c0;
        assertEquals(3, nSkip);
        String line = LiveBookU.gateLine(true, "1.5500", 24, "0.00800", "0.01720", "0.02400",
                full.length, nRej, nSkip, 0.61234f);
        assertTrue(line, line.endsWith(" n_skipfull=3 u=0.6123"));
    }

    /** key OFF (bookFull=true) va leg khong PREDICT (key ON) => bo dem KHONG tang. */
    @Test
    public void offOrNonPredictNotCounted() {
        AIRejectFilter f = new AIRejectFilter();
        int c0 = AIRejectFilter.skipFullCount.get();
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = false;
        f.entryGate(pred(0L, 0.5f), SP, true, true);
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = true;
        f.entryGate(pred(MIN, 0.5f), SP, false, true);
        f.entryGate(pred(2 * MIN, 0.5f), null, true, true);
        assertEquals(c0, AIRejectFilter.skipFullCount.get());
    }
}
