package com.binance.chuyennd.utils;

import org.junit.Test;

import static org.junit.Assert.*;

/** A1 re-audit QF2: cua truy cap package-private + A1-T7 LoopSupervisor (chi a1_wt2, KHONG commit). */
public class A1Qf2Access {
    public static long tryAcquire(RestBudget b, int w, RestBudget.Lane lane) {
        return b.tryAcquire(w, lane);
    }

    /** A1-T7: than loop luon nem Error => supervisor dung lai VO HAN, khong co nguong leo thang (chi log + dem). */
    @Test
    public void t7_supervisorRestartsForeverWithoutEscalation() throws Exception {
        long min0 = LoopSupervisor.minBackoffMs, max0 = LoopSupervisor.maxBackoffMs;
        LoopSupervisor.minBackoffMs = 1;
        LoopSupervisor.maxBackoffMs = 4;
        long r0 = LoopSupervisor.RESTARTS.get();
        try {
            Thread t = LoopSupervisor.start("a1-t7", () -> {
                throw new OutOfMemoryError("gia lap");
            }, true);
            Thread.sleep(500);
            t.interrupt();
            t.join(2000);
            long n = LoopSupervisor.RESTARTS.get() - r0;
            System.out.println("A1-T7 restarts_in_500ms=" + n + " (khong dung, khong leo thang)");
            assertTrue(n > 50);
        } finally {
            LoopSupervisor.minBackoffMs = min0;
            LoopSupervisor.maxBackoffMs = max0;
        }
    }
}
