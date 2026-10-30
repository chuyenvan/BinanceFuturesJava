package com.binance.chuyennd.utils;

import org.junit.Test;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/** [INGEST-QF2] Supervisor dựng lại loop chết vì Error/RuntimeException; interrupt thì dừng hẳn. */
public class LoopSupervisorTest {

    @Test(timeout = 20_000)
    public void loopDiesWithErrorThenRestarts() throws Exception {
        LoopSupervisor.minBackoffMs = 10L;
        AtomicInteger runs = new AtomicInteger();
        CountDownLatch healthy = new CountDownLatch(1);
        long before = LoopSupervisor.RESTARTS.get();
        Thread t = LoopSupervisor.start("test-loop", () -> {
            int n = runs.incrementAndGet();
            if (n == 1) throw new OutOfMemoryError("gia lap OOM trong loop");
            if (n == 2) throw new IllegalStateException("gia lap RuntimeException lot");
            healthy.countDown();
            while (true) {
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }, true);
        assertTrue("loop phai duoc dung lai sau 2 lan chet", healthy.await(10, TimeUnit.SECONDS));
        assertEquals(3, runs.get());
        assertTrue(LoopSupervisor.RESTARTS.get() - before >= 2);
        t.interrupt();
        t.join(5_000);
        assertFalse("interrupt => dung han", t.isAlive());
        LoopSupervisor.minBackoffMs = 1_000L;
    }
}
