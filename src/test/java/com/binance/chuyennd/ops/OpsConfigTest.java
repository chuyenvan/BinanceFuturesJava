package com.binance.chuyennd.ops;

import com.binance.chuyennd.utils.Utils;
import org.junit.Assume;
import org.junit.Test;

import static org.junit.Assert.*;

/** [V11D OPS] LIVE_PERIODIC_RESET_HOURS (0/12/bien) + parse co bat/tat. */
public class OpsConfigTest {

    @Test
    public void resetHoursDefaultIs12() {
        assertEquals(12, OpsConfig.parseResetHours(null));
        assertEquals(12, OpsConfig.parseResetHours(""));
        assertEquals(12, OpsConfig.parseResetHours("   "));
        assertEquals(12, OpsConfig.parseResetHours("12"));
    }

    @Test
    public void resetHoursZeroDisables() {
        assertEquals(0, OpsConfig.parseResetHours("0"));
        assertEquals(0, OpsConfig.parseResetHours(" 0 "));
        assertEquals(0L, OpsConfig.resetPeriodMs(0));
    }

    @Test
    public void resetHoursInvalidFallsBackTo12() {
        assertEquals(12, OpsConfig.parseResetHours("-1"));
        assertEquals(12, OpsConfig.parseResetHours("abc"));
        assertEquals(12, OpsConfig.parseResetHours("1.5"));
        assertEquals(12, OpsConfig.parseResetHours(String.valueOf(OpsConfig.MAX_RESET_HOURS + 1)));
        assertEquals(OpsConfig.MAX_RESET_HOURS, OpsConfig.parseResetHours(String.valueOf(OpsConfig.MAX_RESET_HOURS)));
        assertEquals(6, OpsConfig.parseResetHours("6"));
        assertFalse(OpsConfig.isValidResetHours("-1"));
        assertTrue(OpsConfig.isValidResetHours("0"));
    }

    /** Mac dinh PHAI bang dung hang so v11c: Thread.sleep(Utils.TIME_HOUR * 12). */
    @Test
    public void defaultPeriodEqualsV11cConstant() {
        assertEquals(Utils.TIME_HOUR * 12, OpsConfig.resetPeriodMs(12));
        assertEquals(43_200_000L, OpsConfig.resetPeriodMs(OpsConfig.DEFAULT_RESET_HOURS));
        assertEquals(6 * Utils.TIME_HOUR, OpsConfig.resetPeriodMs(6));
    }

    /** JVM test khong dat env => gia tri hieu luc = 12h. */
    @Test
    public void runtimeDefaultWhenEnvUnset() {
        Assume.assumeTrue(System.getenv(OpsConfig.KEY_RESET_HOURS) == null);
        assertEquals(12, OpsConfig.periodicResetHours());
        assertEquals(Utils.TIME_HOUR * 12, OpsConfig.periodicResetMs());
    }

    @Test
    public void parseOn() {
        assertTrue(OpsConfig.parseOn("1"));
        assertTrue(OpsConfig.parseOn("true"));
        assertTrue(OpsConfig.parseOn(" TRUE "));
        assertFalse(OpsConfig.parseOn(null));
        assertFalse(OpsConfig.parseOn("0"));
        assertFalse(OpsConfig.parseOn("yes"));
        assertFalse(OpsConfig.parseOn(""));
    }
}
