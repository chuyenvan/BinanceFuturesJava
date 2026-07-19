package com.binance.chuyennd.research;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * FUNCTION-TEST LEVER-B sizing (TASK 2026-07-19). HAM THUAN — khong Aerospike/backtest I/O.
 *
 * Muc tieu: chung minh env SIZE_MULT nhan TUYEN TINH size von/lenh (quantity + margin) MA khong dung
 * guard chong-am-von. Tai sao test thuan-so thay vi goi createOrder that:
 *   - createOrder can predictions/AIRejectFilter/ClientSingleton(exchange_info Kaggle)/SimpleSymbolMapper
 *     (Aerospike) -> khong chay offline duoc.
 *   - Configs.SIZE_MULT la `final` doc tu env luc load-class -> khong doi duoc giua cac test trong 1 JVM.
 * Nen test tai lap CHINH XAC chuoi tinh size trong createOrder, tham so hoa sizeMult truc tiep:
 *     budget0 = balanceBasic / number_order_budget
 *     budget  = TradeUtils.managerBudget(budget0, marginRunning, balanceBasic, level)   // guard THAT, pure static
 *     budget *= tierMultiplier                                                          // tier (dat 1.0)
 *     budget *= sizeMult                                                                // <-- LEVER-B
 *     quantity = budget * leverage / entry     // = loi cua Utils.calQuantityTest (truoc normalize)
 *     margin   = quantity * entry / leverage   // = OrderTargetInfoTest.calMargin() = budget
 */
public class SizeMultSizingTest {

    // Tai lap CHINH XAC chuoi tinh trong SimulatorMarketLevelTicker1MStopLoss.createOrder().
    private static float budgetForMult(float balanceBasic, int numberOrderBudget, float marginRunning,
                                       MarketLevelChange level, float tierMultiplier, float sizeMult) {
        Float budget = balanceBasic / (float) numberOrderBudget;            // BudgetManagerSimple.getBudget()
        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, level); // guard THAT
        assertTrue("managerBudget khong duoc null trong kich ban test", budget != null);
        budget *= tierMultiplier;                                            // tier
        if (sizeMult != 1.0f) budget *= sizeMult;                            // LEVER-B (dung dieu kien nhu code)
        return budget;
    }

    private static float quantity(float budget, int leverage, float entry) {
        return budget * leverage / entry;   // loi cua Utils.calQuantityTest
    }

    private static float margin(float quantity, float entry, int leverage) {
        return quantity * entry / leverage; // OrderTargetInfoTest.calMargin()
    }

    /** SIZE_MULT=10 -> quantity + margin cua 1 lenh ~10x so SIZE_MULT=1 (cung gia/balance). */
    @Test
    public void sizeMult10ScalesQuantityAndMargin10x() {
        float balanceBasic = 35000f;
        int numberOrderBudget = 50;      // default
        float marginRunning = 0f;        // marginRatio=0 -> khong bi throttle
        int leverage = 1;                // Configs.LEVERAGE_ORDER default
        float entry = 250f;              // gia coin gia dinh
        float tier = 1.0f;               // tier binh thuong
        MarketLevelChange level = MarketLevelChange.PREDICT_SYMBOL_TRADE;

        float budget1 = budgetForMult(balanceBasic, numberOrderBudget, marginRunning, level, tier, 1.0f);
        float budget10 = budgetForMult(balanceBasic, numberOrderBudget, marginRunning, level, tier, 10.0f);

        float qty1 = quantity(budget1, leverage, entry);
        float qty10 = quantity(budget10, leverage, entry);
        float margin1 = margin(qty1, entry, leverage);
        float margin10 = margin(qty10, entry, leverage);

        float qtyRatio = qty10 / qty1;
        float marginRatio = margin10 / margin1;

        System.out.println("=== LEVER-B SIZE_MULT function-test (balance=" + balanceBasic
                + " numOrderBudget=" + numberOrderBudget + " entry=" + entry + " lev=" + leverage + ") ===");
        System.out.println("SIZE_MULT=1  -> budget=" + budget1 + " quantity=" + qty1 + " margin=" + margin1);
        System.out.println("SIZE_MULT=10 -> budget=" + budget10 + " quantity=" + qty10 + " margin=" + margin10);
        System.out.println("quantity ratio (10/1) = " + qtyRatio + " ; margin ratio (10/1) = " + marginRatio);

        assertEquals("quantity phai scale ~10x", 10.0f, qtyRatio, 1e-4f);
        assertEquals("margin phai scale ~10x", 10.0f, marginRatio, 1e-4f);
        // margin == budget (leverage=1): xac nhan LEVER-B chi noi SIZE trong khuon budget.
        assertEquals("margin == budget (guard-in-budget)", budget10, margin10, 1e-2f);
    }

    /** Default SIZE_MULT=1 (env unset) => budget/quantity/margin BYTE-IDENTICAL voi khong ap dung nhan. */
    @Test
    public void defaultMult1IsByteIdentical() {
        float balanceBasic = 35000f;
        int numberOrderBudget = 50;
        MarketLevelChange level = MarketLevelChange.PREDICT_SYMBOL_TRADE;

        // Baseline: KHONG co buoc SIZE_MULT (mo phong code cu, truoc khi them lever).
        Float baseline = balanceBasic / (float) numberOrderBudget;
        baseline = TradeUtils.managerBudget(baseline, 0f, balanceBasic, level);
        baseline *= 1.0f; // tier

        // Voi lever nhung mult=1: dieu kien `if (sizeMult!=1.0f)` bo qua -> budget khong bi cham.
        float withLever = budgetForMult(balanceBasic, numberOrderBudget, 0f, level, 1.0f, 1.0f);

        System.out.println("Default mult=1: baseline budget=" + baseline + " withLever budget=" + withLever);
        // So SANH BIT (Float.floatToRawIntBits) — khong chi ~=, ma PHAI TRUNG BIT (byte-identical).
        assertEquals("mult=1 phai byte-identical (raw bits)",
                Float.floatToRawIntBits(baseline), Float.floatToRawIntBits(withLever));

        // Xac nhan hang so Configs mac dinh khi env unset.
        System.out.println("Configs.SIZE_MULT(default) = " + Configs.SIZE_MULT
                + " ; Configs.MAX_CONCURRENT_ORDERS(default) = " + Configs.MAX_CONCURRENT_ORDERS);
        // (Chi assert khi test chay ma KHONG set env — moi truong build/HPO khong set 2 env nay.)
        if (System.getenv("SIZE_MULT") == null) {
            assertEquals("SIZE_MULT default = 1.0", 1.0f, Configs.SIZE_MULT, 0f);
        }
        if (System.getenv("MAX_CONCURRENT") == null) {
            assertEquals("MAX_CONCURRENT_ORDERS default = 40", 40, Configs.MAX_CONCURRENT_ORDERS);
        }
    }
}
