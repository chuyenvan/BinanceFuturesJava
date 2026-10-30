package com.binance.chuyennd.ai_ml.features.export.entry;

import org.junit.Test;

import static org.junit.Assert.*;

/** [V12 R4g] LIVE_FEAT_DUMP theo ngay UTC khi reset dinh ky TAT (bai hoc 10-25: ngan sach tong tu tat sau 50 h). */
public class LiveFeatureDumpDailyR4gTest {

    @Test
    public void parseDaily() {
        assertTrue(LiveFeatureDump.parseDaily(null, true));
        assertFalse(LiveFeatureDump.parseDaily("", false));
        assertTrue(LiveFeatureDump.parseDaily("1", false));
        assertTrue(LiveFeatureDump.parseDaily(" TRUE ", false));
        assertFalse(LiveFeatureDump.parseDaily("0", true));
    }

    @Test
    public void reopenOnlyOnNewUtcDay_notAfterShutdown() {
        long d = 20_391L;
        assertTrue(LiveFeatureDump.reopenOnNewDay(true, d, d + 1, false));
        assertFalse("cung ngay", LiveFeatureDump.reopenOnNewDay(true, d, d, false));
        assertFalse("che do tong (reset bat) => nhu cu", LiveFeatureDump.reopenOnNewDay(false, d, d + 1, false));
        assertFalse("JVM dang tat", LiveFeatureDump.reopenOnNewDay(true, d, d + 1, true));
        assertFalse("chua ghi lan nao", LiveFeatureDump.reopenOnNewDay(true, Long.MIN_VALUE, d, false));
    }
}
