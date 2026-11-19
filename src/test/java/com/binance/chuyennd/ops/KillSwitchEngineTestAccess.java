package com.binance.chuyennd.ops;

/** [W3B HANG-1119] cua test (package ops) cho co KILLSW_EQ_POLL_UNLOCKED. */
public final class KillSwitchEngineTestAccess {
    private KillSwitchEngineTestAccess() {
    }

    public static void setEqPollUnlocked(boolean v) {
        KillSwitchEngine.eqPollUnlocked = v;
    }

    public static boolean parse(String raw) {
        return KillSwitchEngine.eqPollUnlockedFrom(raw);
    }
}
