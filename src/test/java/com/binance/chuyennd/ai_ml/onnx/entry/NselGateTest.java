package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * NSEL J-A (docs/prereg/PREREG_NSEL.md §3): gate 2 tang — buffer LOI/THEM tach rieng, quyet dinh LOI y nen K24,
 * THEM chi xet khi LOI fail, F1 chi ap tang THEM, causal q_add, queryOnly (CORE_ADD / would) khong doi LOI,
 * fail-fast cau hinh xung dot, live khong ho tro.
 */
public class NselGateTest {

    private static final long MIN = 60_000L;
    private static final long HOUR = 3600_000L;
    private static final float SP = 0.1f;
    private static final float NAN = Float.NaN;
    private boolean savedSkip;

    @Before
    public void setUp() {
        savedSkip = Configs.GATE_QUOTA_SKIP_WHEN_FULL;
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = true;
        LiveGateRollingRatio.resetForTest();
        GateRollingRatio.configureForTest(0.9f, 90);
        NselGate.configureForTest(0.5f, 90, 24, 32, NAN);
    }

    @After
    public void tearDown() {
        Configs.GATE_QUOTA_SKIP_WHEN_FULL = savedSkip;
        NselGate.disableForTest();
    }

    private static AiPredictionData pred(long ts, float p15) {
        return new AiPredictionData(ts, p15, 0f);
    }

    /** p15 tat dinh, trai deu ca vung pass/fail cua q (sau warm-up 7 ngay). */
    private static float p15(int i, int rank) {
        return (((i * 37 + rank * 11) % 100)) / 1000f;
    }

    @Test
    public void defaultsAreOff() {
        assertFalse(Configs.NSEL_ADD_ENABLED);
        assertFalse(Configs.NSEL_CORE_ADD);
        assertTrue(Float.isNaN(Configs.NSEL_ADD_F1_MIN_BARRET));
        assertEquals(32, Configs.NSEL_ADD_TOPK);
        assertEquals(1, Configs.NSEL_CORE_ADD_MAX_PER_CLUSTER);
        assertEquals(0f, Configs.CRASH_ENTRY_PENALTY, 0f);
        NselGate.disableForTest();
        assertFalse(NselGate.isOn());
    }

    /** Buffer LOI nhan dung r hang <= 24, buffer THEM nhan r MOI hang <= 32 (ke ca hang da qua LOI). */
    @Test
    public void bufferPopulationsByRank() {
        AIRejectFilter f = new AIRejectFilter();
        for (int rank = 1; rank <= 32; rank++) f.entryGateNsel(pred(0L, 0.05f), SP, false, rank, 0f);
        assertEquals(24, GateRollingRatio.bufferSizeForTest());
        assertEquals(24L, GateRollingRatio.seenForTest());
        assertEquals(32, NselGate.addBufferSize());
    }

    /** Hang 25..32: KHONG cham LOI (khong nap, khong noteCandidate), chi buffer THEM. */
    @Test
    public void deepRanksDoNotTouchCoreBuffer() {
        AIRejectFilter f = new AIRejectFilter();
        for (int rank = 25; rank <= 32; rank++) f.entryGateNsel(pred(0L, 0.05f), SP, false, rank, 0f);
        assertEquals(0, GateRollingRatio.bufferSizeForTest());
        assertEquals(0L, GateRollingRatio.seenForTest());
        assertEquals(8, NselGate.addBufferSize());
    }

    /** So day (skipFull bat): KHONG nap ca 2 buffer, ca 2 tang REJECT. */
    @Test
    public void bookFullFeedsNeitherBuffer() {
        AIRejectFilter f = new AIRejectFilter();
        for (int rank = 1; rank <= 32; rank++) {
            AIRejectFilter.FilterResult r = f.entryGateNsel(pred(0L, 5.0f), SP, true, rank, 0f);
            assertEquals("rank=" + rank, AIRejectFilter.FilterDecision.REJECT, r.decision);
        }
        assertEquals(0, GateRollingRatio.bufferSizeForTest());
        assertEquals(0, NselGate.addBufferSize());
        assertEquals(32L, NselGate.addBookFull);
        assertEquals(0L, NselGate.addSeen);
    }

    private static AIRejectFilter.FilterDecision[][] runBaseK24() {
        GateRollingRatio.configureForTest(0.9f, 90);
        AIRejectFilter f = new AIRejectFilter();
        AIRejectFilter.FilterDecision[][] out = new AIRejectFilter.FilterDecision[960][24];
        for (int i = 0; i < 960; i++) {
            for (int rank = 1; rank <= 24; rank++) {
                out[i][rank - 1] = f.entryGate(pred(i * 15L * MIN, p15(i, rank)), SP, true, false, rank).decision;
            }
        }
        return out;
    }

    /**
     * Quyet dinh LOI cho hang <= 24 TRUNG gate K24 nen (10 ngay, qua warm-up), buffer LOI cung kich thuoc;
     * THEM chi duoc xet khi LOI fail (hoac hang > 24) — dem addSeen khop.
     */
    @Test
    public void coreDecisionEqualsK24AndAddOnlyWhenCoreFails() {
        AIRejectFilter.FilterDecision[][] base = runBaseK24();
        int bufBase = GateRollingRatio.bufferSizeForTest();
        long passBase = GateRollingRatio.passForTest();
        GateRollingRatio.configureForTest(0.9f, 90);
        NselGate.configureForTest(0.5f, 90, 24, 32, NAN);
        AIRejectFilter f = new AIRejectFilter();
        long coreFail = 0, nCore = 0, nAdd = 0;
        for (int i = 0; i < 960; i++) {
            for (int rank = 1; rank <= 32; rank++) {
                AIRejectFilter.FilterResult r = f.entryGateNsel(pred(i * 15L * MIN, p15(i, rank)), SP, false, rank, 0f);
                boolean pass = r.decision == AIRejectFilter.FilterDecision.PASS;
                if (rank <= 24) {
                    boolean corePass = base[i][rank - 1] == AIRejectFilter.FilterDecision.PASS;
                    if (corePass) {
                        assertTrue("i=" + i + " rank=" + rank, pass);
                        assertEquals(NselGate.TIER_CORE, r.nselTier);
                        nCore++;
                    } else {
                        coreFail++;
                        if (pass) assertEquals(NselGate.TIER_ADD, r.nselTier);
                    }
                } else {
                    coreFail++;
                    if (pass) assertEquals(NselGate.TIER_ADD, r.nselTier);
                }
                if (pass && r.nselTier == NselGate.TIER_ADD) nAdd++;
            }
        }
        assertEquals(bufBase, GateRollingRatio.bufferSizeForTest());
        assertEquals(passBase, GateRollingRatio.passForTest());
        assertEquals(coreFail, NselGate.addSeen);
        assertEquals(nCore, NselGate.corePass);
        assertEquals(nAdd, NselGate.addPass);
        assertEquals(960 * 32, NselGate.addBufferSize());
        assertTrue("phai co ca 2 tang trong chuoi test: core=" + nCore + " add=" + nAdd, nCore > 0 && nAdd > 0);
    }

    /**
     * corePeekPass (queryOnly — dung cho CORE_ADD va counter would, chay ca khi NSEL OFF) xen giua cac lan goi gate
     * LOI, ke ca la lan goi DAU TIEN cua gio moi => quyet dinh, buffer, pass, seen cua LOI KHONG doi (gate J-B).
     */
    @Test
    public void corePeekDoesNotChangeCoreDecisions() {
        AIRejectFilter.FilterDecision[][] base = runBaseK24();
        int bufBase = GateRollingRatio.bufferSizeForTest();
        long passBase = GateRollingRatio.passForTest();
        long seenBase = GateRollingRatio.seenForTest();
        GateRollingRatio.configureForTest(0.9f, 90);
        AIRejectFilter f = new AIRejectFilter();
        int nPeekPass = 0;
        for (int i = 0; i < 960; i++) {
            long ts = i * 15L * MIN;
            for (int rank = 1; rank <= 24; rank++) {
                if ((i + rank) % 3 == 0 && f.corePeekPass(pred(ts, p15(i + 5, rank)), SP)) nPeekPass++;
                assertEquals("i=" + i + " rank=" + rank, base[i][rank - 1],
                        f.entryGate(pred(ts, p15(i, rank)), SP, true, false, rank).decision);
            }
        }
        assertEquals(bufBase, GateRollingRatio.bufferSizeForTest());
        assertEquals(passBase, GateRollingRatio.passForTest());
        assertEquals(seenBase, GateRollingRatio.seenForTest());
        assertTrue(nPeekPass > 0);
    }

    /** corePeekPass = cung quyet dinh voi entryGate tai cung thoi diem (nhung khong nap). */
    @Test
    public void corePeekMatchesGateDecision() {
        AIRejectFilter f = new AIRejectFilter();
        for (int i = 0; i < 960; i++) {
            long ts = i * 15L * MIN;
            boolean peek = f.corePeekPass(pred(ts, p15(i, 3)), SP);
            int before = GateRollingRatio.bufferSizeForTest();
            boolean gate = f.entryGate(pred(ts, p15(i, 3)), SP, true, false, 3).decision
                    == AIRejectFilter.FilterDecision.PASS;
            assertEquals("i=" + i, gate, peek);
            assertEquals(before + 1, GateRollingRatio.bufferSizeForTest());
        }
    }

    /** F1 chi ap tang THEM; bien -1% = REJECT (float32 (c-o)/o, cung bieu thuc penalty). */
    @Test
    public void f1OnlyOnAddTierWithBoundary() {
        NselGate.configureForTest(0.5f, 90, 24, 32, -0.01f);
        long ts = 0L;   // warm-up => q_add = base, p15=5 qua chac chan
        assertEquals(NselGate.TIER_ADD, NselGate.decide(ts, 5f, SP, false, 30, false, (99.01f - 100f) / 100f));
        assertEquals(NselGate.TIER_REJECT, NselGate.decide(ts, 5f, SP, false, 30, false, (99f - 100f) / 100f));
        assertEquals(NselGate.TIER_REJECT, NselGate.decide(ts, 5f, SP, false, 30, false, -0.05f));
        assertEquals(2L, NselGate.addRejF1);
        // LOI pass tren nen sap: F1 KHONG ap
        assertEquals(NselGate.TIER_CORE, NselGate.decide(ts, 5f, SP, false, 5, true, -0.5f));
        // F1 tat (NaN): nen sap van vao tang THEM
        NselGate.configureForTest(0.5f, 90, 24, 32, NAN);
        assertEquals(NselGate.TIER_ADD, NselGate.decide(ts, 5f, SP, false, 30, false, -0.5f));
        assertTrue(NselGate.f1Pass(-0.9f));
    }

    /** Causal q_add: r cua gio h KHONG vao q_h; cung thuat toan (bit-identical) voi buffer LOI. */
    @Test
    public void addQuantileCausalAndSameAlgorithmAsCore() {
        NselGate.configureForTest(0.5f, 30, 24, 32, NAN);
        GateRollingRatio.configureForTest(0.5f, 30);
        for (int i = 0; i < 400; i++) {
            long ts = i * 20L * MIN;
            float p = p15(i, 7);
            float qa = NselGate.addThreshold(ts, p, SP);
            float qc = GateRollingRatio.addAndQuery(ts, GateRollingRatio.ratio(p, SP));
            assertEquals("i=" + i, Float.floatToIntBits(qc), Float.floatToIntBits(qa));
        }
        NselGate.configureForTest(0.5f, 30, 24, 32, NAN);
        float r1 = GateRollingRatio.ratio(0.01f, SP), r2 = GateRollingRatio.ratio(0.02f, SP), r3 = GateRollingRatio.ratio(0.03f, SP);
        NselGate.addThreshold(0L, 0.01f, SP);
        NselGate.addThreshold(1L, 0.02f, SP);
        NselGate.addThreshold(2L, 0.03f, SP);
        float q = NselGate.addThreshold(200L * HOUR, 9f, SP);
        assertEquals(r2, q, 0f);
        assertTrue(r1 < r2 && r2 < r3);
    }

    /** ratio() = dung r ma threshold() nap vao buffer LOI. */
    @Test
    public void ratioMatchesCoreThresholdSample() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.threshold(0L, 0.037f, SP);
        float q = GateRollingRatio.addAndQuery(200L * HOUR, 0f);
        assertEquals(Float.floatToIntBits(GateRollingRatio.ratio(0.037f, SP)), Float.floatToIntBits(q));
    }

    private static void expectFail(Runnable r, String what) {
        try {
            r.run();
            fail("phai fail-fast: " + what);
        } catch (IllegalStateException expected) {
            // ok
        }
    }

    /** Fail-fast cau hinh xung dot (PREREG_NSEL §2, P0B K5). */
    @Test
    public void validateFailFast() {
        // OFF hoan toan: khong nem
        NselGate.validate(false, false, false, NAN, 24, 32, 1, true, false, null, null);
        NselGate.validate(false, false, true, NAN, -1, 32, 1, false, false, null, null);
        // cau hinh M1/M2 hop le
        NselGate.validate(true, true, false, -0.01f, 24, 32, 1, true, false, null, 0.999915f);
        expectFail(() -> NselGate.validate(false, false, false, NAN, 24, 32, 1, true, false, "-1", null), "GATE_BUFFER_TOPK con khai");
        expectFail(() -> NselGate.validate(false, true, false, NAN, 24, 32, 1, true, false, null, null), "CORE_ADD khong co THEM");
        expectFail(() -> NselGate.validate(true, true, true, NAN, 24, 32, 1, true, false, null, 0.999915f), "CORE_ADD + DCA_SIGNAL_GATE");
        expectFail(() -> NselGate.validate(true, true, false, NAN, 24, 32, 0, true, false, null, 0.999915f), "max/cum < 1");
        expectFail(() -> NselGate.validate(false, false, false, -0.01f, 24, 32, 1, true, false, null, null), "F1 khong co THEM");
        expectFail(() -> NselGate.validate(true, false, false, NAN, 24, 32, 1, false, false, null, 0.999915f), "LOI khong o mode ratio");
        expectFail(() -> NselGate.validate(true, false, false, NAN, 24, 32, 1, true, true, null, 0.999915f), "LIVE ratio bat");
        expectFail(() -> NselGate.validate(true, false, false, NAN, -1, 32, 1, true, false, null, 0.999915f), "khong rank-mode");
        expectFail(() -> NselGate.validate(true, false, false, NAN, 24, 16, 1, true, false, null, 0.999915f), "K_THEM < K_LOI");
        expectFail(() -> NselGate.validate(true, false, false, NAN, 24, 32, 1, true, false, null, null), "thieu pct THEM");
        expectFail(() -> NselGate.validate(true, false, false, NAN, 24, 32, 1, true, false, null, 1.0f), "pct THEM ngoai (0,1)");
    }

    /** LIVE: chua ho tro NSEL — moi key NSEL / LIVE_NSEL_* / GATE_BUFFER_TOPK => fail-fast; profile sach => no-op. */
    @Test
    public void liveFailFast() {
        NselGate.failIfLive(false, false, NAN, Arrays.asList("LIVE_GATE_ROLLING_PCT", "SELECTOR_RANK_TOPK"), null);
        NselGate.failIfLive(false, false, NAN, Collections.<String>emptyList(), null);
        expectFail(() -> NselGate.failIfLive(false, false, NAN, Arrays.asList("LIVE_NSEL_ADD_ROLLING_PCT"), null), "LIVE_NSEL_*");
        expectFail(() -> NselGate.failIfLive(true, false, NAN, Collections.<String>emptyList(), null), "NSEL_ADD_ENABLED o live");
        expectFail(() -> NselGate.failIfLive(false, true, NAN, Collections.<String>emptyList(), null), "SIM_NSEL_CORE_ADD o live");
        expectFail(() -> NselGate.failIfLive(false, false, -0.01f, Collections.<String>emptyList(), null), "F1 o live");
        expectFail(() -> NselGate.failIfLive(false, false, NAN, Collections.<String>emptyList(), "32"), "GATE_BUFFER_TOPK o live");
    }
}
