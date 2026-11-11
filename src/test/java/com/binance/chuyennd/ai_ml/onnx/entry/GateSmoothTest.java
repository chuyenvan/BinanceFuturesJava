package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.junit.After;
import org.junit.Test;

import java.util.TreeMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/** [R3B SMOOTH] prereg 3ea5df40: p~ = mean causal (gom t), phu >= minCov, khong lookahead, thieu phu => NaN. */
public class GateSmoothTest {
    private static final long M = 60_000L;

    @After
    public void off() {
        GateRollingRatio.disableSmoothForTest();
        GateRollingRatio.disableMtfForTest();
    }

    @Test
    public void smoothCausalCoverageNoLookahead() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.configureSmoothForTest(4, 3);
        TreeMap<Long, AiPredictionData> m = new TreeMap<>();
        for (int i = 0; i < 6; i++) m.put(i * M, new AiPredictionData(i * M, i + 1f, 0f));
        GateRollingRatio.setP15Source(m);
        assertEquals((2f + 3f + 4f + 5f) / 4f, GateRollingRatio.smoothP15ForGate(4 * M), 0f);
        m.put(5 * M, new AiPredictionData(5 * M, 1000f, 0f));                       // tuong lai khong anh huong
        assertEquals((2f + 3f + 4f + 5f) / 4f, GateRollingRatio.smoothP15ForGate(4 * M), 0f);
        m.remove(2 * M); m.remove(3 * M);                                            // con 2 < minCov 3
        assertTrue(Float.isNaN(GateRollingRatio.smoothP15ForGate(4 * M)));
    }
}
