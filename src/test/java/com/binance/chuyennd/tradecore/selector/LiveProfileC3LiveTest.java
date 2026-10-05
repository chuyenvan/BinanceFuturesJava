package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.io.File;

import static org.junit.Assert.*;

/**
 * [C3-LIVE 2026-10-03] Cong day lenh that cua profile {@code c3_live}:
 * forceNoPush = NOT(SHADOW_NO_PUSH==false AND LIVE_ENTRY_ENABLED==true) OR kill-switch.
 * 4 case bat buoc + bien. Env trong JVM khong doi duoc => kiem ham thuan {@code decideNoPush}.
 */
public class LiveProfileC3LiveTest {

    /** (1) c3_shadow: LUON no-push, ke ca khi env mo du. */
    @Test
    public void c3ShadowAlwaysNoPush() {
        assertTrue(LiveProfileC3.decideNoPush(false, "false", "true", false));
        assertTrue(LiveProfileC3.decideNoPush(false, null, null, false));
    }

    /** (2) c3_live, thieu env => no-push. */
    @Test
    public void c3LiveMissingEnvNoPush() {
        assertTrue(LiveProfileC3.decideNoPush(true, null, null, false));
        assertTrue("chi SHADOW_NO_PUSH=false, thieu LIVE_ENTRY_ENABLED", LiveProfileC3.decideNoPush(true, "false", null, false));
        assertTrue("chi LIVE_ENTRY_ENABLED=true, SHADOW_NO_PUSH thieu", LiveProfileC3.decideNoPush(true, null, "true", false));
        assertTrue("SHADOW_NO_PUSH=true thang", LiveProfileC3.decideNoPush(true, "true", "true", false));
        assertTrue("gia tri rac", LiveProfileC3.decideNoPush(true, "0", "1", false));
    }

    /** (3) c3_live, du hai env, khong kill-switch => PUSH. */
    @Test
    public void c3LiveBothEnvPush() {
        assertFalse(LiveProfileC3.decideNoPush(true, "false", "true", false));
        assertFalse("khong phan biet hoa thuong / khoang trang", LiveProfileC3.decideNoPush(true, " FALSE ", "True", false));
    }

    /** (4) c3_live, du env NHUNG kill-switch ton tai => no-push. */
    @Test
    public void c3LiveKillSwitchWins() throws Exception {
        assertTrue(LiveProfileC3.decideNoPush(true, "false", "true", true));
        File f = File.createTempFile("KILL_SWITCH", ".flag");
        try {
            assertTrue(LiveProfileC3.killSwitchPresent(f.getAbsolutePath()));
            assertTrue(LiveProfileC3.decideNoPush(true, "false", "true",
                    LiveProfileC3.killSwitchPresent(f.getAbsolutePath())));
        } finally {
            assertTrue(f.delete());
        }
        assertFalse(LiveProfileC3.killSwitchPresent(f.getAbsolutePath()));
        assertFalse(LiveProfileC3.killSwitchPresent(null));
    }

    /** Profile tat (surefire): forceNoPush false (duong cu doc SHADOW_NO_PUSH), khong phai c3_live. */
    @Test
    public void offUnchanged() {
        assertFalse(LiveProfileC3.on());
        assertFalse(LiveProfileC3.isLive());
        assertFalse(LiveProfileC3.forceNoPush());
        assertEquals("c3_live", LiveProfileC3.PROFILE_LIVE);
        assertEquals("run/KILL_SWITCH", LiveProfileC3.DEFAULT_KILL_FILE);
    }
}
