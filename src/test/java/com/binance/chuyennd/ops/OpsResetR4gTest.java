package com.binance.chuyennd.ops;

import org.junit.Test;

import static org.junit.Assert.*;

/** [V12 R4g] reset dinh ky: mac dinh TAT cho c3_live/c3_shadow, khai tuong minh thang; ingestor khong doc key nay. */
public class OpsResetR4gTest {

    @Test
    public void c3ProfilesDefaultOff() {
        assertEquals(0, OpsConfig.resolveResetHours(null, "c3_live"));
        assertEquals(0, OpsConfig.resolveResetHours("", "c3_shadow"));
        assertEquals(0, OpsConfig.resolveResetHours("  ", " C3_LIVE "));
    }

    @Test
    public void otherProfilesKeepLegacy12() {
        assertEquals(12, OpsConfig.resolveResetHours(null, null));
        assertEquals(12, OpsConfig.resolveResetHours(null, ""));
        assertEquals(12, OpsConfig.resolveResetHours(null, "head"));
        assertEquals(12, OpsConfig.resolveResetHours("abc", null));
    }

    @Test
    public void explicitValidValueWins() {
        assertEquals(12, OpsConfig.resolveResetHours("12", "c3_live"));
        assertEquals(4, OpsConfig.resolveResetHours("4", "c3_shadow"));
        assertEquals(0, OpsConfig.resolveResetHours("0", null));
    }

    @Test
    public void explicitInvalidFallsBackToProfileDefault() {
        assertEquals(0, OpsConfig.resolveResetHours("-1", "c3_live"));
        assertEquals(0, OpsConfig.resolveResetHours("99999", "c3_shadow"));
        assertEquals(12, OpsConfig.resolveResetHours("-1", "x"));
    }

    @Test
    public void isC3Profile() {
        assertTrue(OpsConfig.isC3Profile("c3_live"));
        assertTrue(OpsConfig.isC3Profile("C3_Shadow"));
        assertFalse(OpsConfig.isC3Profile(null));
        assertFalse(OpsConfig.isC3Profile("c3"));
    }

    @Test
    public void mapperRefreshMinutes() {
        assertEquals(10, InPlaceRefresh.parseMinutes(null));
        assertEquals(10, InPlaceRefresh.parseMinutes("x"));
        assertEquals(10, InPlaceRefresh.parseMinutes("-3"));
        assertEquals(0, InPlaceRefresh.parseMinutes("0"));
        assertEquals(5, InPlaceRefresh.parseMinutes(" 5 "));
        assertEquals(1440, InPlaceRefresh.parseMinutes("99999"));
    }
}
