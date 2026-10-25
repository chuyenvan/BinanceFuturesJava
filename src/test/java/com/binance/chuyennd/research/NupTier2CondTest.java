package com.binance.chuyennd.research;

import com.binance.chuyennd.tradecore.Configs;
import org.junit.Test;

import static org.junit.Assert.*;

/** [NUP-TIER2] Unit test tung dieu kien U / nen khong sap / size, va mac dinh TAT. */
public class NupTier2CondTest {

    @Test
    public void uCondition() {
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.tier2UOk(19f, 100f, 0.20f));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.tier2UOk(20f, 100f, 0.20f));   // bien phai la <
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.tier2UOk(25f, 100f, 0.20f));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.tier2UOk(0f, 0f, 0.20f));
    }

    @Test
    public void crashCandleCondition() {
        // -0.5% > -1% => OK; -1.0% khong > -1% => FAIL; -3% => FAIL
        assertTrue(SimulatorMarketLevelTicker1MStopLoss.tier2CrashOk(100f, 99.5f, -0.01f));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.tier2CrashOk(100f, 98.9f, -0.01f));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.tier2CrashOk(100f, 97.0f, -0.01f));
        assertFalse(SimulatorMarketLevelTicker1MStopLoss.tier2CrashOk(0f, 99f, -0.01f));
    }

    @Test
    public void sizeMultiplier() {
        assertEquals(500f, SimulatorMarketLevelTicker1MStopLoss.tier2Size(1000f, 0.5f), 1e-6);
    }

    @Test
    public void defaultOffAndThresholds() {
        assertFalse("cờ phải mặc định TẮT", Configs.GATE_TIER2_ENABLED);
        assertEquals(0.20f, Configs.GATE_TIER2_U_MAX, 1e-6);
        assertEquals(-0.01f, Configs.GATE_TIER2_CRASH_RET, 1e-6);
        assertEquals(0.5f, Configs.GATE_TIER2_SIZE_MULT, 1e-6);
    }
}
