package com.binance.chuyennd.research;

import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.EntryCost;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import java.util.function.Function;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * [ENTRY-COST-BUCKET 2026-10-12] docs/result/EXEC_RESULT.md §6(a): SIM_ENTRY_COST_MODE=bucket — phan bucket dung
 * bien -1/-2/-4% (khop isCrashBar), OFF = cong thuc cu, bucket voi cost=SLIPPAGE_RATE ~ path off, fail-fast.
 */
public class EntryCostBucketTest {

    private final float crash0 = Configs.CRASH_ENTRY_PENALTY;
    private final float slip0 = Configs.SLIPPAGE_RATE;
    private final boolean applySlip0 = Configs.APPLY_SLIPPAGE;
    private final boolean fund0 = Configs.APPLY_FUNDING_FEE;

    @Before
    public void setUp() {
        EntryCost.reset();
        Configs.APPLY_SLIPPAGE = true;
        Configs.APPLY_FUNDING_FEE = false;
    }

    @After
    public void restore() {
        EntryCost.reset();
        Configs.CRASH_ENTRY_PENALTY = crash0;
        Configs.SLIPPAGE_RATE = slip0;
        Configs.APPLY_SLIPPAGE = applySlip0;
        Configs.APPLY_FUNDING_FEE = fund0;
    }

    private static Function<String, String> cfg(String... kv) {
        Map<String, String> m = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put(kv[i], kv[i + 1]);
        return m::get;
    }

    private static Function<String, String> bucketCfg(String nc, String c1, String c2, String c4) {
        return cfg("SIM_ENTRY_COST_MODE", "bucket", "SIM_ENTRY_COST_NC", nc, "SIM_ENTRY_COST_C1", c1,
                "SIM_ENTRY_COST_C2", c2, "SIM_ENTRY_COST_C4", c4);
    }

    private static OrderTargetInfoTest leg(float entry, float qty, float tp) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, qty,
                Configs.LEVERAGE_ORDER, null, 1_600_000_000_000L, 1_600_000_000_000L, OrderSide.BUY);
        o.priceTP = tp;
        return o;
    }

    /** Ban sao NGUYEN VAN calTp cua module (5abf6a0f) — path off phai trung tung bit. */
    private static float oldCalTp(float q, float e, float tp) {
        Float r = q * (tp - e) - q * e * Configs.RATE_FEE;
        if (Configs.APPLY_SLIPPAGE) {
            float slip = q * e * Configs.SLIPPAGE_RATE * 2f;
            r = r - slip;
        }
        r = r - 0f;
        return r;
    }

    // ---------- (a) phan bucket ----------
    @Test
    public void bucketBoundariesMatchSpecAndIsCrashBar() {
        float o = 100f;
        assertEquals(EntryCost.NC, EntryCost.bucketOf(101f, o));
        assertEquals(EntryCost.NC, EntryCost.bucketOf(100f, o));
        assertEquals(EntryCost.NC, EntryCost.bucketOf(Math.nextUp(99f), o));   // bar_ret ngay tren -1%
        assertEquals(EntryCost.C1, EntryCost.bucketOf(99f, o));                // bar_ret = -1% (<= -1% => C1)
        assertEquals(EntryCost.C1, EntryCost.bucketOf(Math.nextDown(99f), o));
        assertEquals(EntryCost.C1, EntryCost.bucketOf(Math.nextUp(98f), o));   // ngay tren -2%
        assertEquals(EntryCost.C2, EntryCost.bucketOf(98f, o));                // = -2% => C2
        assertEquals(EntryCost.C2, EntryCost.bucketOf(Math.nextDown(98f), o));
        assertEquals(EntryCost.C2, EntryCost.bucketOf(Math.nextUp(96f), o));   // ngay tren -4%
        assertEquals(EntryCost.C4, EntryCost.bucketOf(96f, o));                // = -4% => C4
        assertEquals(EntryCost.C4, EntryCost.bucketOf(Math.nextDown(96f), o));
        assertEquals(EntryCost.C4, EntryCost.bucketOf(50f, o));
        assertEquals(EntryCost.NC, EntryCost.bucketOf(Float.NaN, o));          // isCrashBar(NaN)=false => NC
        float[][] pts = {{101f, o}, {100f, o}, {Math.nextUp(99f), o}, {99f, o}, {Math.nextDown(99f), o},
                {98f, o}, {96f, o}, {Float.NaN, o}};
        for (float[] p : pts) {
            assertEquals("NC <=> !isCrashBar tai " + p[0], SimulatorMarketLevelTicker1MStopLoss.isCrashBar(p[0], p[1]),
                    EntryCost.bucketOf(p[0], p[1]) != EntryCost.NC);
        }
    }

    @Test
    public void bucketSweepConsistentWithIsCrashBarAndBarRet() {
        Random r = new Random(42);
        for (int i = 0; i < 200_000; i++) {
            float open = (float) Math.exp(r.nextGaussian() * 4.0);           // gia 1e-5..1e5
            float ret = (float) ((r.nextDouble() - 0.7) * 0.12);           // ~[-8.4%, +3.6%]
            float close = open * (1f + ret);
            if (i % 4 == 0) close = Math.nextUp(close);
            int b = EntryCost.bucketOf(close, open);
            assertEquals(SimulatorMarketLevelTicker1MStopLoss.isCrashBar(close, open), b != EntryCost.NC);
            float br = (close - open) / open;
            int exp = br > -0.01f ? EntryCost.NC : br > -0.02f ? EntryCost.C1 : br > -0.04f ? EntryCost.C2 : EntryCost.C4;
            assertEquals(exp, b);
        }
    }

    // ---------- (b) mode off ----------
    @Test
    public void offIsDefaultAndCalTpBitIdenticalToOldFormula() {
        EntryCost.configure(Cfg::get, Configs.CRASH_ENTRY_PENALTY);   // env test JVM: khong khai key => off
        assertFalse(EntryCost.isBucket());
        for (Function<String, String> g : java.util.Arrays.asList(cfg(), cfg("SIM_ENTRY_COST_MODE", "off"),
                cfg("SIM_ENTRY_COST_MODE", " OFF "), cfg("SIM_ENTRY_COST_MODE", ""))) {
            EntryCost.configure(g, 0.0069f);   // off + penalty cu: hop le
            assertFalse(EntryCost.isBucket());
            assertTrue(EntryCost.dumpRows().isEmpty());                // CONFIG_HASH khong doi
            for (int b = 0; b < 4; b++) assertEquals(0f, EntryCost.cost(b), 0f);
        }
        Random r = new Random(7);
        for (int i = 0; i < 10_000; i++) {
            float q = (float) (r.nextDouble() * 1000), e = (float) Math.exp(r.nextGaussian() * 3);
            float tp = e * (float) (1 + (r.nextDouble() - 0.5) * 0.2);
            assertEquals(Float.floatToIntBits(oldCalTp(q, e, tp)), Float.floatToIntBits(leg(e, q, tp).calTp()));
        }
    }

    // ---------- (c) bucket voi moi cost = SLIPPAGE_RATE ----------
    @Test
    public void bucketWithAllCostsEqualSlippageMatchesOffPath() {
        float s = Configs.SLIPPAGE_RATE;
        String v = Float.toString(s);
        Random r = new Random(11);
        for (int i = 0; i < 10_000; i++) {
            float open = (float) Math.exp(r.nextGaussian() * 3);
            float close = open * (1f + (float) ((r.nextDouble() - 0.5) * 0.004));   // chan KHONG sap
            float q = (float) (1 + r.nextDouble() * 1000);
            float tp = close * (float) (1 + (r.nextDouble() - 0.5) * 0.2);
            EntryCost.reset();
            float pnlOff = leg(close, q, tp).calTp();
            EntryCost.configure(bucketCfg(v, v, v, v), 0f);
            int b = EntryCost.bucketOf(close, open);
            assertEquals(EntryCost.NC, b);
            float e = EntryCost.applyEntry(close, b);
            // gia vao: cung cong thuc voi crash penalty => bang TUYET DOI
            assertEquals(Float.floatToIntBits(close * (1f + s)), Float.floatToIntBits(e));
            // calTp bucket: 1 chan slip (phia RA) — bang tung bit voi cong thuc tuong minh
            float pnlB = leg(e, q, tp).calTp();
            Float exp = q * (tp - e) - q * e * Configs.RATE_FEE;
            exp = exp - q * e * s;
            exp = exp - 0f;
            assertEquals(Float.floatToIntBits(exp), Float.floatToIntBits(pnlB));
            // TONG chi phi bucket = off toi bac 1; chenh = bac 2 q*close*s*(fee+s) (do slip/fee tinh tren entry da cong)
            double d2 = (double) q * close * s * (Configs.RATE_FEE + s);
            double tol = 1e-5 * Math.abs((double) q * close) + 1e-4;
            assertEquals(pnlOff - d2, pnlB, tol);
        }
    }

    @Test
    public void bucketRealCostsPerBucketAndDumpRows() {
        EntryCost.configure(bucketCfg("0.0007", "0.0018", "0.0019", "0.0032"), 0f);
        assertTrue(EntryCost.isBucket());
        assertEquals(0.0007f, EntryCost.cost(EntryCost.NC), 0f);
        assertEquals(0.0032f, EntryCost.cost(EntryCost.C4), 0f);
        assertEquals(Float.floatToIntBits(99f * (1f + 0.0018f)), Float.floatToIntBits(EntryCost.applyEntry(99f, EntryCost.C1)));
        assertEquals(Float.floatToIntBits(96f * (1f + 0.0032f)), Float.floatToIntBits(EntryCost.applyEntry(96f, EntryCost.C4)));
        assertEquals(5, EntryCost.dumpRows().size());
    }

    // ---------- (d2) duong chua ho tro bucket: fail-fast ----------
    @Test
    public void unsupportedPathsFailFastOnlyInBucket() {
        EntryCost.requireOff("x");   // off: no-op
        assertEquals("ZERO_TRADES", com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4
                .evaluateDetailed(new java.util.TreeMap<>(), 30).note);
        EntryCost.configure(bucketCfg("0.0007", "0.0018", "0.0019", "0.0032"), 0f);
        try {
            com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4.evaluateDetailed(new java.util.TreeMap<>(), 30);
            fail("bucket phai fail-fast o HPOFitnessCalculatorV4");
        } catch (IllegalStateException expected) {
            assertTrue(expected.getMessage().contains("HPOFitnessCalculatorV4"));
        }
    }

    // ---------- (d) fail-fast ----------
    private static void expectFail(Function<String, String> g, float pen) {
        try {
            EntryCost.configure(g, pen);
            fail("phai fail-fast");
        } catch (IllegalStateException expected) {
            assertFalse("trang thai khong doi khi fail", EntryCost.isBucket());
        }
    }

    @Test
    public void failFastOnMissingBadOrConflictingKeys() {
        String[] k = EntryCost.K_COST;
        for (int miss = 0; miss < 4; miss++) {
            Map<String, String> m = new HashMap<>();
            m.put(EntryCost.K_MODE, "bucket");
            for (int i = 0; i < 4; i++) if (i != miss) m.put(k[i], "0.001");
            expectFail(m::get, 0f);
            m.put(k[miss], "  ");
            expectFail(m::get, 0f);
        }
        expectFail(cfg(EntryCost.K_MODE, "buckets"), 0f);
        expectFail(bucketCfg("0.0007", "abc", "0.0019", "0.0032"), 0f);
        expectFail(bucketCfg("0.0007", "0.18", "0.0019", "0.0032"), 0f);        // % thay vi FRACTION
        expectFail(bucketCfg("0.0007", "NaN", "0.0019", "0.0032"), 0f);
        expectFail(bucketCfg("0.0007", "0.0018", "0.0019", "0.0032"), 0.0069f); // xung dot crash penalty
        expectFail(cfg(k[0], "0.0007"), 0f);                                     // off ma khai cost => mo ho
        expectFail(cfg(EntryCost.K_MODE, "off", k[3], "0.0032"), 0f);
        EntryCost.configure(bucketCfg("0.0007", "0.0018", "0.0019", "0.0032"), 0f);  // penalty=0 => hop le
        assertTrue(EntryCost.isBucket());
    }
}
