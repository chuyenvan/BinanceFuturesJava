package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.junit.After;
import org.junit.Test;

import java.util.TreeMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/** [R3-G3 MTF-OR] docs/prereg/PREREG_R3_GATE_FAMILY.md (b901016e) §6: mean causal, phu >= minCov, khong lookahead, pct_w float32, OR. */
public class GateMtfOrTest {
    private static final long M = 60_000L;

    @After
    public void off() {
        GateRollingRatio.disableMtfForTest();
    }

    private static TreeMap<Long, AiPredictionData> series(long t0, float... v) {
        TreeMap<Long, AiPredictionData> m = new TreeMap<>();
        for (int i = 0; i < v.length; i++) m.put(t0 + i * M, new AiPredictionData(t0 + i * M, v[i], 0f));
        return m;
    }

    @Test
    public void pctWMatchesFloat32Formula() {
        GateRollingRatio.configureForTest(Float.parseFloat("0.999950829"), 90);
        GateRollingRatio.configureMtfForTest(15, 12, 0.5f);
        float want = (float) (1.0 - 0.5 * (1.0 - (double) Float.parseFloat("0.999950829")));
        assertEquals(want, GateRollingRatio.mtfPctForTest(), 0f);
    }

    @Test
    public void meanIsCausalAndIncludesT() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.configureMtfForTest(3, 3, 0.5f);
        TreeMap<Long, AiPredictionData> m = series(0L, 1f, 2f, 3f, 100f);
        GateRollingRatio.setP15Source(m);
        assertEquals(2f, GateRollingRatio.smoothedP15(2 * M), 0f);      // (1+2+3)/3, KHONG dung phut 3 (=100)
        m.put(3 * M, new AiPredictionData(3 * M, -999f, 0f));            // doi tuong lai => mean tai t=2' khong doi
        assertEquals(2f, GateRollingRatio.smoothedP15(2 * M), 0f);
    }

    @Test
    public void coverageRuleFailClosed() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.configureMtfForTest(3, 3, 0.5f);
        TreeMap<Long, AiPredictionData> m = series(0L, 1f, 2f, 3f);
        m.remove(1 * M);                                                 // thieu 1 phut => 2 < minCov 3 => NaN
        GateRollingRatio.setP15Source(m);
        assertTrue(Float.isNaN(GateRollingRatio.smoothedP15(2 * M)));
        GateRollingRatio.configureMtfForTest(3, 2, 0.5f);
        assertEquals(2f, GateRollingRatio.smoothedP15(2 * M), 0f);      // (1+3)/2
    }

    @Test
    public void warmupBothFramesFallBackToBaseAndOr() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.configureMtfForTest(3, 1, 0.5f);
        GateRollingRatio.setP15Source(series(0L, 0.001f, 0.001f, 0.5f));
        // warm-up => q = base 0.008; thr = 0.008*fac*gs. p15 diem 0.5 qua; khung mean (0.1673) cung qua.
        assertTrue(GateRollingRatio.mtfPass(2 * M, 0.5f, 0.0001f));
        // p15 diem rat nho, mean cung nho => truot ca hai
        GateRollingRatio.configureMtfForTest(3, 1, 0.5f);
        GateRollingRatio.setP15Source(series(0L, 0.0f, 0.0f, 0.0f));
        assertFalse(GateRollingRatio.mtfPass(2 * M, 0.0f, 0.0001f));
    }
}
