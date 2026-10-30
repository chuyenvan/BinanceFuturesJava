package com.binance.chuyennd.ops;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

/**
 * [V12 R4h] Theo doi ro NATIVE (heap da do bang GC log — ROUND4G §1.4 khong ro; RSS 2,76 GB chi co 1 anh chup): moi gio log
 * 1 dong {@code [OPS-PROC]} doc {@code /proc/self/status} (VmRSS, VmHWM, Threads) + heap JVM + so thread JVM. Chi LOG, khong
 * doi hanh vi. Khong co /proc (vd macOS) => -1.
 */
public final class OpsProcStat {

    private static final Logger LOG = LoggerFactory.getLogger(OpsProcStat.class);

    private OpsProcStat() {
    }

    /** {rssKb, hwmKb, threads}; thieu => -1. */
    static long[] parseStatus(List<String> lines) {
        long[] out = {-1L, -1L, -1L};
        if (lines == null) return out;
        for (String ln : lines) {
            if (ln.startsWith("VmRSS:")) out[0] = num(ln);
            else if (ln.startsWith("VmHWM:")) out[1] = num(ln);
            else if (ln.startsWith("Threads:")) out[2] = num(ln);
        }
        return out;
    }

    private static long num(String ln) {
        String d = ln.replaceAll("[^0-9]", "");
        if (d.isEmpty()) return -1L;
        try {
            return Long.parseLong(d);
        } catch (NumberFormatException e) {
            return -1L;
        }
    }

    static String line(long[] st, long heapUsed, long heapCommitted, int jvmThreads, long uptimeMs) {
        return String.format("[OPS-PROC] rss_mb=%d hwm_mb=%d threads=%d jvm_threads=%d heap_used_mb=%d heap_committed_mb=%d uptime_h=%.1f",
                st[0] < 0 ? -1 : st[0] / 1024, st[1] < 0 ? -1 : st[1] / 1024, st[2], jvmThreads, heapUsed >> 20, heapCommitted >> 20,
                uptimeMs / 3_600_000d);
    }

    public static String snapshot() {
        long[] st;
        Path p = Paths.get("/proc/self/status");
        try {
            st = Files.isReadable(p) ? parseStatus(Files.readAllLines(p)) : new long[]{-1L, -1L, -1L};
        } catch (Exception e) {
            st = new long[]{-1L, -1L, -1L};
        }
        Runtime rt = Runtime.getRuntime();
        int jt = ManagementFactory.getThreadMXBean().getThreadCount();
        return line(st, rt.totalMemory() - rt.freeMemory(), rt.totalMemory(), jt, ManagementFactory.getRuntimeMXBean().getUptime());
    }

    static void logSafe() {
        try {
            LOG.info("{}", snapshot());
        } catch (Throwable t) {
            LOG.warn("[OPS-PROC] loi doc /proc: {}", t.toString());
        }
    }
}
