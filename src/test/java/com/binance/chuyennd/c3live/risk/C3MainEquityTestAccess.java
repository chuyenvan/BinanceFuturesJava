package com.binance.chuyennd.c3live.risk;

/** [W3B muc 2] cua test cho co C3_EQ_REST_UNLOCKED. */
public final class C3MainEquityTestAccess {
    private C3MainEquityTestAccess() {
    }

    public static void setRestUnlocked(boolean v) {
        C3MainEquity.restUnlocked = v;
    }

    public static boolean effective(String eqRaw, String ksRaw) {
        return C3MainEquity.effectiveRestUnlocked(eqRaw, ksRaw);
    }

    public static boolean parse(String raw) {
        return C3MainEquity.restUnlockedFrom(raw);
    }
}
