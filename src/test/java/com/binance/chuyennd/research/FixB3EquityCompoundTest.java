package com.binance.chuyennd.research;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

/**
 * BUG B3 (docs/plan/QUEUE.md muc BUGS, docs/experiment/T2B_FULLFLOW.md muc 1.2) — goc sizing la HANG SO
 * balanceBasic = Configs.capitalStart() = 35000, khong doan nao trong duong sim ghi lai no
 * => size KHONG compound theo equity, fitness khong phan anh he compound.
 */
public class FixB3EquityCompoundTest {

    private final boolean scalar0 = Configs.DCA_GRID_SCALAR;
    private final float[] w0 = Configs.DCA_GRID_WEIGHTS;
    private final float scale0 = Configs.DCA_GRID_SCALE;
    private final boolean fixB2_0 = Configs.FIX_B2;

    @Before
    public void setUp() {
        // Configs.properties duoc nap luc runtime; trong surefire no co the con rong =>
        // capitalStart() NPE khi BudgetManagerSimple khoi tao field. Dat san gia tri THAT.
        Configs.properties.putIfAbsent("CAPITAL_START", "35000");
        BudgetManagerSimple.resetInstance();
    }

    @After
    public void restore() {
        Configs.DCA_GRID_SCALAR = scalar0;
        Configs.DCA_GRID_WEIGHTS = w0;
        Configs.DCA_GRID_SCALE = scale0;
        Configs.FIX_B2 = fixB2_0;
        BudgetManagerSimple.resetInstance();
    }

    /** Chua chay gi: equity = von goc => C3 khoi dong y het C2b. */
    @Test
    public void equityStartsAtCapital() {
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        assertEquals(bm.balanceBasic, bm.equityNow(), 1e-3f);
    }

    /** equity = balanceCurrent (von + realized) + unProfit (unrealized) — anh chup NHAT QUAN. */
    @Test
    public void equityIsRealizedPlusUnrealized() {
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        bm.balanceCurrent = 70000f;
        bm.unProfit = 5000f;
        assertEquals(75000f, bm.equityNow(), 1e-3f);

        bm.unProfit = -8000f;
        assertEquals(62000f, bm.equityNow(), 1e-3f);
    }

    /** Guard: unrealized am hon ca von => KHONG tra so <= 0 (managerBudget se chan lenh moi). */
    @Test
    public void nonPositiveEquityFallsBack() {
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        bm.balanceCurrent = 1000f;
        bm.unProfit = -2000f;
        assertEquals(1000f, bm.equityNow(), 1e-3f);
    }

    /**
     * COMPOUND: size TUYEN TINH theo equity. Va TRAN margin/leg la HE QUA cua cong thuc
     * (equity x F_BASE x DCA_GRID_SCALE = 4.5% equity), khong phai hang so 1575 rieng —
     * 1575 chi la gia tri cua no tai equity 35000.
     */
    @Test
    public void sizingScalesLinearlyWithEquity() {
        Configs.DCA_GRID_SCALAR = false;
        Configs.DCA_GRID_WEIGHTS = new float[]{1f, 0f, 0f, 0f};
        Configs.DCA_GRID_SCALE = 1.5f;
        Configs.FIX_B2 = true;

        float ratio = DcaUtils.gridLegWeightRatio(0);
        float at35k = TradeUtils.managerBudget(700f, 0f, 35000f, null) * ratio;
        float at70k = TradeUtils.managerBudget(700f, 0f, 70000f, null) * ratio;

        assertEquals("cap = 4.5% equity, o 35000 = 1575", 1575f, at35k, 0.5f);
        assertEquals("cap = 4.5% equity, o 70000 = 3150", 3150f, at70k, 0.5f);
        assertEquals("size compound tuyen tinh theo equity", 2f, at70k / at35k, 1e-3f);
        assertEquals("cap luon = 4.5% equity", 0.045f, at70k / 70000f, 1e-4f);
    }

    /** U_MAX cung do tren CUNG mot goc: u = marginRunning/equity => throttle nhat quan. */
    @Test
    public void throttleUsesSameEquityBase() {
        Configs.DCA_GRID_SCALAR = false;
        Configs.DCA_GRID_WEIGHTS = new float[]{1f, 0f, 0f, 0f};
        Configs.DCA_GRID_SCALE = 1.5f;
        Configs.FIX_B2 = true;

        // marginRunning = 30% equity => u = 0.5 x U_MAX(0.6) => throttle = 0.5
        float b = TradeUtils.managerBudget(700f, 21000f, 70000f, null);
        assertEquals(70000f * Configs.F_BASE * 0.5f, b, 0.5f);
        // u >= U_MAX => chan lenh moi
        org.junit.Assert.assertNull(TradeUtils.managerBudget(700f, 42000f, 70000f, null));
    }
}
