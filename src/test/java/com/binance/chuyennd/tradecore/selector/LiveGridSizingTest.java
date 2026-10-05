package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import static org.junit.Assert.*;

/**
 * [LIVE-SIZING 2026-10-03] E2 parity: budget leg live = managerBudget x gridLegWeightRatio(legIdx)
 * khi {@code LIVE_APPLY_GRID_RATIO=true}; co TAT => dung managerBudget (HEAD).
 * Bo so B0: equity 35000, U=0, F_BASE 0.015, DCA_GRID_SCALE 6, luoi 1,1,1,1, FIX_B2 => leg0 787.5 / OFF 131.25.
 */
public class LiveGridSizingTest {

    private float fBase0, uMax0, scale0;
    private float[] w0, lv0;
    private boolean fix0, scalar0;

    @Before
    public void setUp() {
        fBase0 = Configs.F_BASE;
        uMax0 = Configs.U_MAX;
        scale0 = Configs.DCA_GRID_SCALE;
        w0 = Configs.DCA_GRID_WEIGHTS;
        lv0 = Configs.DCA_GRID_LEVELS;
        fix0 = Configs.FIX_B2;
        scalar0 = Configs.DCA_GRID_SCALAR;
        Configs.F_BASE = 0.015f;
        Configs.U_MAX = 0.60f;
        Configs.DCA_GRID_SCALE = 6.0f;
        Configs.DCA_GRID_WEIGHTS = new float[]{1f, 1f, 1f, 1f};
        Configs.DCA_GRID_LEVELS = new float[]{-0.50f, -0.75f, -0.90f};
        Configs.FIX_B2 = true;
        Configs.DCA_GRID_SCALAR = false;
    }

    @After
    public void restore() {
        Configs.F_BASE = fBase0;
        Configs.U_MAX = uMax0;
        Configs.DCA_GRID_SCALE = scale0;
        Configs.DCA_GRID_WEIGHTS = w0;
        Configs.DCA_GRID_LEVELS = lv0;
        Configs.FIX_B2 = fix0;
        Configs.DCA_GRID_SCALAR = scalar0;
    }

    private static Float mb35000() {
        return TradeUtils.managerBudget(null, 0f, 35000f, null);
    }

    /** Co mac dinh TAT trong surefire (khong ai dat LIVE_APPLY_GRID_RATIO). */
    @Test
    public void flagOffByDefault() {
        assertFalse(LiveGridSizing.on());
        Float mb = mb35000();
        assertSame("co TAT => tra DUNG tham chieu managerBudget", mb, LiveGridSizing.legBudget(mb, 0));
    }

    /** OFF => 131.25 (= 35000 x 0.015 / 4). */
    @Test
    public void offLeg0Is131_25() {
        Float b = LiveGridSizing.legBudget(mb35000(), 0, false);
        assertEquals(131.25f, b, 0.01f);
    }

    /** ON => 787.5 (= 131.25 x 1 x 6) va trung bit voi cong thuc sim managerBudget * gridLegWeightRatio(0). */
    @Test
    public void onLeg0Is787_5_sameAsSim() {
        Float b = LiveGridSizing.legBudget(mb35000(), 0, true);
        assertEquals(787.5f, b, 0.01f);
        Float sim = mb35000();
        sim *= DcaUtils.gridLegWeightRatio(0);   // y het SimulatorMarketLevelTicker1MStopLoss:1439-1444
        assertEquals(Float.floatToIntBits(sim), Float.floatToIntBits(b));
    }

    /** Leg 1..3 cung ratio 6 (luoi phang); het bac (leg 4 > dcaGridLegs=3) => 0 (bi chan o budget<5). */
    @Test
    public void ladderAndExhaustion() {
        Float mb = mb35000();
        for (int i = 1; i <= 3; i++) {
            assertEquals(787.5f, LiveGridSizing.legBudget(mb, i, true), 0.01f);
        }
        assertEquals(0f, LiveGridSizing.legBudget(mb, 4, true), 0f);
    }

    /** Leg DCA vi the that (legIdx<0) va budget null: KHONG doi. */
    @Test
    public void unknownLegAndNullUntouched() {
        Float mb = mb35000();
        assertSame(mb, LiveGridSizing.legBudget(mb, -1, true));
        assertNull(LiveGridSizing.legBudget(null, 0, true));
    }

    /** Throttle U van ap truoc ratio: U=0.3 => throttle 0.5 => 393.75. */
    @Test
    public void throttleThenRatio() {
        Float mb = TradeUtils.managerBudget(null, 10500f, 35000f, MarketLevelChange.DCA_LEVEL1);
        assertEquals(393.75f, LiveGridSizing.legBudget(mb, 0, true), 0.01f);
    }
}
