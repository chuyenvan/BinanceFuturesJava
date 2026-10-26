package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.tradecore.EntryGate;
import org.junit.Test;

import static org.junit.Assert.*;

/** [NUP-TIER2] Unit test cho dieu kien phan vi (q2) va tinh "khong doi buffer/quota". */
public class NupTier2GateTest {

    private static long H = 3600_000L;
    private static long D = 86_400_000L;

    /** Nap 1000 mau r=0..999 trai qua 8 ngay (qua warm-up 7 ngay). */
    private static long seedBuffer() {
        GateRollingRatio.configureForTest(0.99f, 90);
        GateRollingRatio.configureTier2ForTest(true, 0.50f);
        long t0 = 1_600_000_000_000L;
        for (int i = 0; i < 1000; i++) {
            long ts = t0 + (long) i * (8L * D / 1000L);
            GateRollingRatio.addAndQuery(ts, i);
        }
        return t0 + 999L * (8L * D / 1000L) + 3_600_000L;  // gio ke tiep -> buoc tinh q1/q2
    }

    @Test
    public void q2PassesWhenQ1Fails() {
        long ts = seedBuffer();
        // dua candidate vao cung gio qua CHINH threshold() (nap r + tinh q1/q2 mot lan/gio)
        float factor = Math.max(EntryGate.DYN_MIN, (0.15f / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        float p15 = 700f * factor * EntryGate.GATE_DYN_SCALE;
        GateRollingRatio.threshold(ts, p15, 0.15f);
        // q1 ~ 989 => 700 < q1 => gate chinh REJECT; q2 ~ 499 => tier2 PASS
        assertTrue("tier2 phai pass khi q1 reject", GateRollingRatio.tier2Pass(ts, p15, 0.15f));
    }

    @Test
    public void q2FailsWhenBelowTier2Quantile() {
        long ts = seedBuffer();
        float factor = Math.max(EntryGate.DYN_MIN, (0.15f / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        GateRollingRatio.threshold(ts, 100f * factor * EntryGate.GATE_DYN_SCALE, 0.15f);
        assertFalse("r=100 duoi q2 0.50", GateRollingRatio.tier2Pass(ts, 100f * factor * EntryGate.GATE_DYN_SCALE, 0.15f));
    }

    @Test
    public void tier2OffAlwaysFalse() {
        long ts = seedBuffer();
        float factor = Math.max(EntryGate.DYN_MIN, (0.15f / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        GateRollingRatio.threshold(ts, 700f * factor * EntryGate.GATE_DYN_SCALE, 0.15f);
        GateRollingRatio.configureTier2ForTest(false, 0.50f);
        assertFalse(GateRollingRatio.tier2Pass(ts, 700f * factor * EntryGate.GATE_DYN_SCALE, 0.15f));
    }

    @Test
    public void tier2DoesNotChangeBufferOrQuota() {
        long ts = seedBuffer();
        float factor = Math.max(EntryGate.DYN_MIN, (0.15f / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        GateRollingRatio.threshold(ts, 700f * factor * EntryGate.GATE_DYN_SCALE, 0.15f);
        int m0 = GateRollingRatio.bufferSizeForTest();
        long pass0 = GateRollingRatio.passForTest();
        long seen0 = GateRollingRatio.seenForTest();
        long skip0 = GateRollingRatio.skipFullForTest();
        for (int i = 0; i < 5; i++) GateRollingRatio.tier2Pass(ts, 700f * factor * EntryGate.GATE_DYN_SCALE, 0.15f);
        assertEquals("buffer khong doi", m0, GateRollingRatio.bufferSizeForTest());
        assertEquals("pass counter khong doi", pass0, GateRollingRatio.passForTest());
        assertEquals("seen counter khong doi", seen0, GateRollingRatio.seenForTest());
        assertEquals("skipFull counter khong doi", skip0, GateRollingRatio.skipFullForTest());
    }
}
