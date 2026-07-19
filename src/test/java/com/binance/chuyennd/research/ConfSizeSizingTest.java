package com.binance.chuyennd.research;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * FUNCTION-TEST SIZE-BY-CONFIDENCE soft-gate (TASK 2026-07-19). HAM THUAN — khong Aerospike/backtest I/O.
 *
 * Muc tieu: chung minh confFactor(p6) tuyen tinh giua [LO,HI] + clamp [FMIN,FMAX], VA khi CONF_SIZE_MODE=0
 * thi budget-per-order BYTE-IDENTICAL (khong ap confFactor). p6 = 1 - symbolPred, tinh per-order.
 *
 * Tai sao test thuan-so: createOrder can predictions/AIRejectFilter/SimpleSymbolMapper(Aerospike) ->
 * khong chay offline. Configs.CONF_SIZE_* la `final` doc env luc load-class -> khong doi giua cac test
 * trong 1 JVM. Nen test goi TRUC TIEP Configs.confFactor (pure static, default env) + tai lap chuoi tinh
 * budget cua createOrder (tham so hoa mode/factor truc tiep).
 */
public class ConfSizeSizingTest {

    private static final float EPS = 1e-4f;

    /** confFactor: p6=0.68 -> ~0.3 (=FMIN, clamp low) ; p6=0.95 -> ~3.0 (=FMAX, clamp high) ;
     *  p6=0.815 (giua) -> ~1.65 (tuyen tinh). Chi assert khi env unset (dung default). */
    @Test
    public void confFactorLinearAndClamp() {
        // Bo qua neu moi truong da set env (default build/HPO khong set) -> tranh false-fail.
        if (System.getenv("CONF_SIZE_LO") != null || System.getenv("CONF_SIZE_HI") != null
                || System.getenv("CONF_SIZE_FMIN") != null || System.getenv("CONF_SIZE_FMAX") != null) {
            System.out.println("[skip assert] env CONF_SIZE_* da set, chi in gia tri.");
        }

        float fLo = Configs.confFactor(0.68f);   // <= LO -> FMIN
        float fMid = Configs.confFactor(0.815f);  // giua -> 1.65
        float fHi = Configs.confFactor(0.95f);   // >= HI -> FMAX
        float fBelow = Configs.confFactor(0.50f); // duoi LO -> FMIN (clamp)
        float fAbove = Configs.confFactor(0.99f); // tren HI -> FMAX (clamp)

        System.out.println("=== SIZE-BY-CONFIDENCE confFactor (LO=" + Configs.CONF_SIZE_LO
                + " HI=" + Configs.CONF_SIZE_HI + " FMIN=" + Configs.CONF_SIZE_FMIN
                + " FMAX=" + Configs.CONF_SIZE_FMAX + ") ===");
        System.out.println("p6=0.50 -> factor=" + fBelow + " (clamp FMIN)");
        System.out.println("p6=0.68 -> factor=" + fLo + " (LO -> FMIN)");
        System.out.println("p6=0.815-> factor=" + fMid + " (giua -> ~1.65)");
        System.out.println("p6=0.95 -> factor=" + fHi + " (HI -> FMAX)");
        System.out.println("p6=0.99 -> factor=" + fAbove + " (clamp FMAX)");

        if (System.getenv("CONF_SIZE_LO") == null && System.getenv("CONF_SIZE_HI") == null
                && System.getenv("CONF_SIZE_FMIN") == null && System.getenv("CONF_SIZE_FMAX") == null) {
            assertEquals("p6=0.68 -> ~0.3", 0.30f, fLo, EPS);
            assertEquals("p6=0.815 -> ~1.65", 1.65f, fMid, EPS);
            assertEquals("p6=0.95 -> ~3.0", 3.00f, fHi, EPS);
            assertEquals("p6=0.50 (clamp) -> 0.3", 0.30f, fBelow, EPS);
            assertEquals("p6=0.99 (clamp) -> 3.0", 3.00f, fAbove, EPS);

            // Tuyen tinh: midpoint = trung binh cong FMIN,FMAX vi 0.815 la trung diem [0.68,0.95].
            assertEquals("midpoint = (FMIN+FMAX)/2", (0.30f + 3.00f) / 2f, fMid, EPS);
            // Ratio budget p6=0.95 vs p6=0.68 (~10x) — dong von don keo p6 cao.
            float ratio = fHi / fLo;
            System.out.println("budget ratio p6=0.95 vs p6=0.68 = " + ratio + "x (FMAX/FMIN)");
            assertEquals("ratio ~10x", 10.0f, ratio, 1e-3f);
        }
    }

    // Tai lap chuoi tinh budget trong createOrder (tham so hoa confMode/symbolPred truc tiep).
    private static float budgetForConf(float balanceBasic, int numberOrderBudget, float marginRunning,
                                       MarketLevelChange level, float tierMultiplier, int confMode, Float symbolPred) {
        Float budget = balanceBasic / (float) numberOrderBudget;              // BudgetManagerSimple.getBudget()
        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, level); // guard THAT
        assertTrue("managerBudget khong duoc null trong kich ban test", budget != null);
        budget *= tierMultiplier;                                             // tier
        // (SIZE_MULT bo qua trong test nay — mac dinh 1.0)
        if (confMode == 1 && symbolPred != null) {                            // <-- SIZE-BY-CONFIDENCE (nhu code)
            float p6 = 1f - symbolPred;
            budget *= Configs.confFactor(p6);
        }
        return budget;
    }

    /** CONF_SIZE_MODE=0 (default) -> budget BYTE-IDENTICAL voi baseline khong ap confFactor. */
    @Test
    public void modeOffIsByteIdentical() {
        float balanceBasic = 35000f;
        int numberOrderBudget = 50;
        MarketLevelChange level = MarketLevelChange.PREDICT_SYMBOL_TRADE;
        Float symbolPred = 0.05f; // p6=0.95 (keo tot) — neu mode=1 se x3, mode=0 KHONG duoc cham

        // Baseline: KHONG co buoc conf (mo phong code truoc khi them soft-gate).
        Float baseline = balanceBasic / (float) numberOrderBudget;
        baseline = TradeUtils.managerBudget(baseline, 0f, balanceBasic, level);
        baseline *= 1.0f; // tier

        float modeOff = budgetForConf(balanceBasic, numberOrderBudget, 0f, level, 1.0f, 0, symbolPred);

        System.out.println("mode=0 (OFF): baseline budget=" + baseline + " withGate budget=" + modeOff);
        assertEquals("mode=0 phai byte-identical (raw bits)",
                Float.floatToRawIntBits(baseline), Float.floatToRawIntBits(modeOff));

        if (System.getenv("CONF_SIZE_MODE") == null) {
            assertEquals("CONF_SIZE_MODE default = 0", 0, Configs.CONF_SIZE_MODE);
        }
    }

    /** CONF_SIZE_MODE=1: budget p6=0.95 vs p6=0.68 ~10x (von don keo p6 cao, GIU tan suat). */
    @Test
    public void modeOnScalesBudgetByConfidence() {
        float balanceBasic = 35000f;
        int numberOrderBudget = 50;
        MarketLevelChange level = MarketLevelChange.PREDICT_SYMBOL_TRADE;

        // Bo qua assert neu env CONF_SIZE_* bi set (doi curve) — chi in.
        boolean defaults = System.getenv("CONF_SIZE_LO") == null && System.getenv("CONF_SIZE_HI") == null
                && System.getenv("CONF_SIZE_FMIN") == null && System.getenv("CONF_SIZE_FMAX") == null;

        // p6=0.68 -> symbolPred=0.32 ; p6=0.815 -> 0.185 ; p6=0.95 -> 0.05
        float bLo = budgetForConf(balanceBasic, numberOrderBudget, 0f, level, 1.0f, 1, 0.32f);
        float bMid = budgetForConf(balanceBasic, numberOrderBudget, 0f, level, 1.0f, 1, 0.185f);
        float bHi = budgetForConf(balanceBasic, numberOrderBudget, 0f, level, 1.0f, 1, 0.05f);

        System.out.println("mode=1: budget p6=0.68=" + bLo + " p6=0.815=" + bMid + " p6=0.95=" + bHi);
        System.out.println("budget ratio p6=0.95 / p6=0.68 = " + (bHi / bLo) + "x");

        if (defaults) {
            assertEquals("budget ratio hi/lo ~10x", 10.0f, bHi / bLo, 1e-2f);
            assertTrue("budget p6 cao > budget p6 marginal", bHi > bMid && bMid > bLo);
        }
    }
}
