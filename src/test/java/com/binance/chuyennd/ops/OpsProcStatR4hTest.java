package com.binance.chuyennd.ops;

import org.junit.Test;

import java.util.Arrays;

import static org.junit.Assert.*;

/** [V12 R4h] OPS-PROC: doc /proc/self/status (VmRSS/VmHWM/Threads). */
public class OpsProcStatR4hTest {

    @Test
    public void parseStatus() {
        long[] s = OpsProcStat.parseStatus(Arrays.asList("Name:\tjava", "VmHWM:\t 3140160 kB", "VmRSS:\t 2759664 kB", "Threads:\t51"));
        assertArrayEquals(new long[]{2759664L, 3140160L, 51L}, s);
        assertArrayEquals(new long[]{-1L, -1L, -1L}, OpsProcStat.parseStatus(null));
        String ln = OpsProcStat.line(s, 600L << 20, 2000L << 20, 49, 3 * 3_600_000L);
        assertTrue(ln, ln.startsWith("[OPS-PROC] rss_mb=2694 hwm_mb=3066 threads=51 jvm_threads=49 heap_used_mb=600 heap_committed_mb=2000 uptime_h=3.0"));
    }

    @Test
    public void snapshotWorks() {
        String s = OpsProcStat.snapshot();
        assertTrue(s, s.startsWith("[OPS-PROC] rss_mb="));
    }

    @Test
    public void procMinutes() {
        assertEquals(60, InPlaceRefresh.parseMinutes(null, InPlaceRefresh.DEFAULT_PROC_STAT_MIN));
        assertEquals(0, InPlaceRefresh.parseMinutes("0", InPlaceRefresh.DEFAULT_PROC_STAT_MIN));
    }
}
