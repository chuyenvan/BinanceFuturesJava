package com.binance.chuyennd.c3live.entry;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Method;
import java.math.BigDecimal;
import java.util.Random;

import static org.junit.Assert.*;

/**
 * [R1 T2c 2026-11-10] Thuoc tinh tren trang thai ngau nhien: size leg c3 that ({@link C3LiveEntry}, chuoi
 * managerBudget -> LiveGridSizing.legBudget(apply=true) -> tran 4,5 % -> min 5 -> x tier) == size leg sim
 * ({@code SimulatorMarketLevelTicker1MStopLoss.createOrder}: managerBudget x tier x gridLegWeightRatio(gridLegCount)),
 * va DCA due live ({@code gridDue = DcaUtils.shouldDcaGrid(firstEntryPrice, refPx, legCount)}) == sim
 * ({@code DcaProcessor.getDCA} nhanh grid) tren cung (first, px, legCount). Cau hinh = profile B0 (F_BASE 0,015,
 * luoi 1,1,1,1, SCALE 6, FIX_B2, TIER_FLAT=1); tier khac 1 chi de kiem thu tu phep nhan.
 */
public class C3SimSizingPropertyTest {

    private static final Logger LOG = LoggerFactory.getLogger(C3SimSizingPropertyTest.class);
    private float fBase0, scale0;
    private float[] w0;
    private boolean fix0, grid0;

    @Before
    public void setUp() {
        fBase0 = Configs.F_BASE; scale0 = Configs.DCA_GRID_SCALE; w0 = Configs.DCA_GRID_WEIGHTS;
        fix0 = Configs.FIX_B2; grid0 = Configs.DCA_GRID_ENABLED;
        Configs.F_BASE = 0.015f;
        Configs.DCA_GRID_SCALE = 6.0f;
        Configs.DCA_GRID_WEIGHTS = new float[]{1f, 1f, 1f, 1f};
        Configs.FIX_B2 = true;
        Configs.DCA_GRID_ENABLED = true;
    }

    @After
    public void restore() {
        Configs.F_BASE = fBase0; Configs.DCA_GRID_SCALE = scale0; Configs.DCA_GRID_WEIGHTS = w0;
        Configs.FIX_B2 = fix0; Configs.DCA_GRID_ENABLED = grid0;
    }

    static Float legBudgetApply(Float b, int idx) {
        try {
            Method m = Class.forName("com.binance.chuyennd.tradecore.selector.LiveGridSizing")
                    .getDeclaredMethod("legBudget", Float.class, int.class, boolean.class);
            m.setAccessible(true);
            return (Float) m.invoke(null, b, idx, true);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException(e);
        }
    }

    /** sim createOrder: budget = managerBudget; budget *= tier; budget *= gridLegWeightRatio(legIdx). */
    static float simBudget(double marginRunning, double equity, float tier, int legIdx) {
        Float b = TradeUtils.managerBudget(null, (float) marginRunning, (float) equity, null);
        if (b == null) return Float.NaN;
        b *= tier;
        float ratio = DcaUtils.gridLegWeightRatio(legIdx);
        if (ratio <= 0f) return 0f;
        b *= ratio;
        return b;
    }

    @Test
    public void randomStatesLiveSizeAndDcaDueEqualSim() {
        Random rnd = new Random(42);
        float[] tiers = {1f, 1f, 1f, 0.5f, 1.5f, 2f};
        int legs = 0, eq = 0, capped = 0, small = 0, umax = 0, dueChecks = 0, notDueChecks = 0;
        double maxRel = 0d;
        for (int trial = 0; trial < 1500; trial++) {
            C3LiveEntryTest.Setup s = new C3LiveEntryTest.Setup(8);
            double equity = Math.exp(Math.log(300d) + rnd.nextDouble() * (Math.log(300_000d) - Math.log(300d)));
            s.capital = equity;
            C3LiveEntry e = s.builder().legBudgetFn(C3SimSizingPropertyTest::legBudgetApply)
                    .gridDue((f, p, n) -> DcaUtils.shouldDcaGrid(f, p, n)).sizeCapOfEquity(0.045f).build();
            int nFill = rnd.nextInt(8);
            for (int k = 1; k <= nFill; k++) {   // leg lap day U ngau nhien
                e.onLeg(new C3LiveEntry.LegInput(C3LiveFixtures.sym(k), "PREDICT_SYMBOL_TRADE", false,
                        C3LiveEntryTest.BAR, 1.0, 1.0, 1f, false), C3LiveEntryTest.NOW);
            }
            String sym = C3LiveFixtures.sym(0);
            float tier = tiers[rnd.nextInt(tiers.length)];
            double first = 1.0;
            for (int legIdx = 0; legIdx <= Configs.dcaGridLegs(); legIdx++) {
                double px = 1.0;
                boolean dca = legIdx > 0;
                if (dca) {
                    float lvl = Configs.dcaGridLevel(legIdx - 1);
                    if (!(lvl < 0f)) break;
                    double thr = first * (1d + lvl);
                    // DCA chua toi bac: live DCA_NOT_DUE <=> sim shouldDcaGrid false
                    double above = thr * (1d + 0.02 + 0.05 * rnd.nextDouble());
                    s.gw.setPrice(sym, BigDecimal.valueOf(above));
                    C3LiveEntry.Result r0 = e.onLeg(new C3LiveEntry.LegInput(sym, "DCA_LEVEL1", true, C3LiveEntryTest.BAR,
                            above, above, tier, false), C3LiveEntryTest.NOW);
                    boolean simDue = DcaUtils.shouldDcaGrid((float) first, (float) above, legIdx);
                    assertEquals(r0.toString(), simDue, r0.outcome != C3LiveEntry.Outcome.DCA_NOT_DUE);
                    notDueChecks++;
                    px = thr * (1d - 0.05 * rnd.nextDouble());
                    s.gw.setPrice(sym, BigDecimal.valueOf(px));
                    assertTrue(DcaUtils.shouldDcaGrid((float) first, (float) px, legIdx));
                    dueChecks++;
                } else {
                    s.gw.setPrice(sym, BigDecimal.ONE);
                }
                C3LiveEntry.Result r = e.onLeg(new C3LiveEntry.LegInput(sym, dca ? "DCA_LEVEL1" : "PREDICT_SYMBOL_TRADE",
                        dca, C3LiveEntryTest.BAR, px, px, tier, false), C3LiveEntryTest.NOW);
                if (dca) assertNotEquals(r.toString(), C3LiveEntry.Outcome.DCA_NOT_DUE, r.outcome);
                float sim = simBudget(r.marginBefore, equity, tier, legIdx);
                Float mb = TradeUtils.managerBudget(null, (float) r.marginBefore, (float) equity, null);
                if (r.outcome == C3LiveEntry.Outcome.U_MAX) {
                    assertTrue(Float.isNaN(sim));
                    umax++;
                    break;
                }
                if (r.outcome == C3LiveEntry.Outcome.BUDGET_SMALL) {   // D9: live min 5 USDT (truoc tier); sim khong co
                    small++;
                    break;
                }
                if (r.outcome != C3LiveEntry.Outcome.SUBMITTED) break;   // SIZING (minNotional/step) — D9
                legs++;
                boolean cap = mb * DcaUtils.gridLegWeightRatio(legIdx) > 0.045f * (float) equity;
                if (cap) {
                    capped++;
                } else {
                    double rel = Math.abs(r.budget - sim) / sim;
                    maxRel = Math.max(maxRel, rel);
                    assertTrue("legIdx=" + legIdx + " live=" + r.budget + " sim=" + sim, rel <= 1e-6);
                    if (tier == 1f) assertEquals(sim, r.budget, 0d);   // tier 1: trung BIT
                    eq++;
                }
                if (legIdx == 0) first = s.book.cluster(sym).get().firstEntryPrice;
            }
        }
        LOG.info("[R1-T2C] legs={} eq={} capped={} budgetSmall={} umax={} dueChecks={} notDueChecks={} maxRel={}",
                legs, eq, capped, small, umax, dueChecks, notDueChecks, maxRel);
        System.out.println("[R1-T2C] legs=" + legs + " eq=" + eq + " capped=" + capped + " budgetSmall=" + small
                + " umax=" + umax + " dueChecks=" + dueChecks + " notDueChecks=" + notDueChecks + " maxRel=" + maxRel);
        assertTrue(legs > 1000);
        assertTrue(dueChecks > 500);
    }
}
