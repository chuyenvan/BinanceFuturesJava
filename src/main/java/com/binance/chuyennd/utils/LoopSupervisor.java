package com.binance.chuyennd.utils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.atomic.AtomicLong;

/**
 * [INGEST-QF2 2026-10-31] Giám sát loop chính trong JVM (thay "restart JVM" làm đường tự cứu, MAJ-1 A1_QF_REPORT):
 * thân loop thoát vì {@link Throwable} (Error/OOM/RuntimeException lọt) hoặc tự return ⇒ log ERROR, đếm, ngủ backoff
 * (1 s → 30 s, reset sau 10′ chạy ổn) rồi chạy LẠI thân loop trên CÙNG thread. Thread bị interrupt ⇒ dừng hẳn.
 */
public final class LoopSupervisor {
    private static final Logger LOG = LoggerFactory.getLogger(LoopSupervisor.class);
    /** Tổng số lần dựng lại loop từ khi JVM start (metric loop_restarts, prereg Q10). */
    public static final AtomicLong RESTARTS = new AtomicLong();
    static volatile long minBackoffMs = 1_000L, maxBackoffMs = 30_000L;

    private LoopSupervisor() {
    }

    /** Bọc thân loop: dùng {@code new Thread(LoopSupervisor.wrap("ten", () -> {...}))}. */
    public static Runnable wrap(String name, Runnable body) {
        return () -> {
            long backoff = minBackoffMs;
            while (!Thread.currentThread().isInterrupted()) {
                long t0 = System.currentTimeMillis();
                String why;
                try {
                    body.run();
                    why = "thoat binh thuong (khong mong doi)";
                } catch (Throwable t) {
                    why = t.toString();
                    LOG.error("[SUPERVISOR] loop {} chet: {}", name, why, t);
                }
                if (Thread.currentThread().isInterrupted()) return;
                if (System.currentTimeMillis() - t0 > 600_000L) backoff = minBackoffMs;
                long n = RESTARTS.incrementAndGet();
                LOG.error("[SUPERVISOR] dung lai loop {} sau {} ms (lan thu {} toan JVM): {}", name, backoff, n, why);
                try {
                    Thread.sleep(backoff);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                }
                backoff = Math.min(maxBackoffMs, backoff * 2);
            }
        };
    }

    /** Tạo + start thread được giám sát. */
    public static Thread start(String name, Runnable body, boolean daemon) {
        Thread t = new Thread(wrap(name, body), name);
        t.setDaemon(daemon);
        t.start();
        return t;
    }
}
