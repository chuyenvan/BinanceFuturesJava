package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.tradecore.EntryGate;
import org.junit.Test;

import static org.junit.Assert.*;

/**
 * [NUP3-SLEEVE] q2 sleeve = phan vi tren CUNG buffer r (co che q2/gio TIER2): ung vien sleeve chi DOC q2,
 * KHONG nap r, KHONG doi pass/quota cua gate nen; q2 cache theo gio (nhan qua).
 */
public class Nup3SleeveGateTest {

    private static final long D = 86_400_000L;

    /** 1000 mau r = 0..999 trai qua 8 ngay; gate nen pct 0.99, q2 = 0.50. Tra ve moc gio ke tiep. */
    private static long seed() {
        GateRollingRatio.configureForTest(0.99f, 90);
        GateRollingRatio.configureTier2ForTest(true, 0.50f);
        long t0 = 1_600_000_000_000L;
        for (int i = 0; i < 1000; i++) GateRollingRatio.addAndQuery(t0 + (long) i * (8L * D / 1000L), i);
        return t0 + 999L * (8L * D / 1000L) + 3_600_000L;
    }

    private static float p15For(float r, float sp) {
        float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
        return r * factor * EntryGate.GATE_DYN_SCALE;
    }

    @Test
    public void candidateRejectedByBaseGatePassesQ2WithoutTouchingBufferOrQuota() {
        long ts = seed();
        float p15 = p15For(700f, 0.15f);
        float q1 = GateRollingRatio.threshold(ts, p15, 0.15f);       // nen: nap r + tinh q1/q2 mot lan/gio
        assertFalse("gate nen REJECT", EntryGate.pass(p15, q1, 0.15f));
        int m0 = GateRollingRatio.bufferSizeForTest();
        long pass0 = GateRollingRatio.passForTest();
        float q2 = GateRollingRatio.tier2QForTest();
        for (int i = 0; i < 50; i++) assertTrue(GateRollingRatio.tier2Pass(ts, p15, 0.15f));
        assertEquals("khong nap r", m0, GateRollingRatio.bufferSizeForTest());
        assertEquals("khong doi pass/quota", pass0, GateRollingRatio.passForTest());
        assertEquals("q2 khong doi", q2, GateRollingRatio.tier2QForTest(), 0f);
    }

    @Test
    public void belowQ2IsNotACandidate() {
        long ts = seed();
        float p15 = p15For(100f, 0.15f);
        GateRollingRatio.threshold(ts, p15, 0.15f);
        assertFalse(GateRollingRatio.tier2Pass(ts, p15, 0.15f));
    }

    @Test
    public void q2IsHourlyCachedAndCausal() {
        long ts = seed();
        GateRollingRatio.threshold(ts, p15For(700f, 0.15f), 0.15f);
        float q2a = GateRollingRatio.tier2QForTest();
        for (int i = 1; i <= 2000; i++) GateRollingRatio.threshold(ts + i, p15For(1e6f, 0.15f), 0.15f);
        assertEquals("cung gio => q2 khong tinh lai", q2a, GateRollingRatio.tier2QForTest(), 0f);
        GateRollingRatio.threshold(ts + 3_600_000L, p15For(1f, 0.15f), 0.15f);
        assertTrue("gio moi => q2 tinh lai tren cua so truoc-add", GateRollingRatio.tier2QForTest() > q2a);
    }

    @Test
    public void q2OffMeansNoCandidate() {
        long ts = seed();
        float p15 = p15For(700f, 0.15f);
        GateRollingRatio.threshold(ts, p15, 0.15f);
        GateRollingRatio.configureTier2ForTest(false, 0.50f);
        assertFalse(GateRollingRatio.tier2Pass(ts, p15, 0.15f));
        assertFalse(GateRollingRatio.sleeveQ2On());
    }
}
