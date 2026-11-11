package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import org.junit.After;
import org.junit.Test;

import java.util.*;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/** [R5P2] prereg PREREG_R5P2_MAX15_GATE: q theo phut = phan tu k cua cua so [t-days, t) (brute force); MAX causal. */
public class GateQMinuteMaxTest {
    private static final long M = 60_000L, D = 86_400_000L;

    @After
    public void off() {
        GateRollingRatio.configureForTest(0.5f, 30);   // tat che do phut
        GateRollingRatio.disableSmoothForTest();
        GateRollingRatio.configureMaxForTest(false);
    }

    @Test
    public void minuteQuantileEqualsBruteForce() {
        float pct = 0.97f;
        int days = 2;
        GateRollingRatio.configureForTest(pct, days);
        GateRollingRatio.configureQMinuteForTest();
        Random rnd = new Random(20261111L);
        List<long[]> tsL = new ArrayList<>();
        List<Float> rL = new ArrayList<>();
        long t0 = 1_700_000_000_000L / M * M;
        int checked = 0;
        for (long t = t0; t < t0 + 12 * D; t += M * (1 + rnd.nextInt(3))) {
            int n = 1 + rnd.nextInt(5);
            float q = Float.NaN;
            for (int i = 0; i < n; i++) {
                float r = (float) Math.abs(rnd.nextGaussian()) * (rnd.nextInt(50) == 0 ? 5f : 1f);
                if (rnd.nextInt(10) == 0 && !rL.isEmpty()) r = rL.get(rnd.nextInt(rL.size()));   // trung gia tri
                float qi = GateRollingRatio.addAndQuery(t + i, r);
                if (i == 0) q = qi; else assertEquals(q, qi, 0f);          // co dinh trong phut
                tsL.add(new long[]{t + i});
                rL.add(r);
            }
            // brute force: o cua phut TRUOC t trong [t - days, t)
            List<Float> w = new ArrayList<>();
            long first = tsL.get(0)[0];
            for (int j = 0; j < tsL.size() - n; j++) {
                long ts = tsL.get(j)[0];
                if (ts >= t - days * D && ts < t) w.add(rL.get(j));
            }
            float want;
            if (w.isEmpty() || (t - first) < 7 * D) want = Configs.MIN_MOMENTUM_15M;
            else {
                Collections.sort(w);
                int m = w.size();
                int k = Math.min(m - 1, Math.max(0, (int) Math.floor((double) pct * (m - 1))));
                want = w.get(k);
            }
            assertEquals("t=" + t, want, q, 0f);
            checked++;
        }
        assertTrue(checked > 3000);
    }

    @Test
    public void maxCausalCoverage() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.configureSmoothForTest(3, 3);
        GateRollingRatio.configureMaxForTest(true);
        TreeMap<Long, AiPredictionData> m = new TreeMap<>();
        float[] v = {1f, 5f, 2f, 3f, 100f};
        for (int i = 0; i < v.length; i++) m.put(i * M, new AiPredictionData(i * M, v[i], 0f));
        GateRollingRatio.setP15Source(m);
        assertEquals(5f, GateRollingRatio.smoothP15ForGate(2 * M), 0f);   // max(1,5,2), khong dung phut 3,4
        assertEquals(5f, GateRollingRatio.smoothP15ForGate(3 * M), 0f);   // cua so [1,3] = (5,2,3) => 5
        m.remove(2 * M);
        assertTrue(Float.isNaN(GateRollingRatio.smoothP15ForGate(3 * M)));   // con 2 < minCov 3
    }
}
