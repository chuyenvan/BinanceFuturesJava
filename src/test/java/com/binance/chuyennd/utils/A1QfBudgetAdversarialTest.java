package com.binance.chuyennd.utils;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** A1 AUDIT (khong commit vao nhanh implementer): test doi khang RestBudget. */
public class A1QfBudgetAdversarialTest {
    final AtomicLong off = new AtomicLong();

    @Before
    public void setUp() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    @After
    public void tearDown() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        RestBudget.reset(null);
    }

    /** Mo phong 1 pass KlineIngestCore.fetchAll: pool 30, moi symbol 2 lan thu (acquire HIGH 5 s, backoff 300), timeout 15 s. */
    static int pass(RestBudget b, int n, long timeoutMs) {
        ExecutorService pool = Executors.newFixedThreadPool(30);
        AtomicInteger ok = new AtomicInteger();
        List<Future<?>> fs = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            fs.add(pool.submit(() -> {
                for (int a = 0; a < 2; a++) {
                    if (b.acquire(1, RestBudget.Lane.HIGH, 5_000L)) {
                        ok.incrementAndGet();
                        return;
                    }
                    if (Thread.currentThread().isInterrupted()) return;
                    try {
                        Thread.sleep(300);
                    } catch (InterruptedException e) {
                        return;
                    }
                }
            }));
        }
        long deadline = System.currentTimeMillis() + timeoutMs;
        for (Future<?> f : fs) {
            try {
                f.get(Math.max(1, deadline - System.currentTimeMillis()), TimeUnit.MILLISECONDS);
            } catch (Exception ex) {
                f.cancel(true);
            }
        }
        pool.shutdownNow();
        return ok.get();
    }

    /**
     * A1-T1: WS chet toan phan 1 phut (vd moc 24h Binance dong ca 6 conn cung luc, hoac mang 242 chap chon).
     * Nen 60 s truoc: ~190 weight LOW (OI sweep ~4 call/s lap day lane LOW toi cap-100). Rest-Price-Loop: acquire(2,HIGH,5s) moi 3 s.
     * +4 s earlyRest 752 symbol; +30 s suspects 752 + sample 25. Yeu cau prereg Q7/rollback: khong khoang gia nao > 15 000 ms.
     */
    @Test(timeout = 150_000)
    public void t1_wsTotalLoss_priceRealtimeStarved() throws Exception {
        RestBudget b = new RestBudget(300, 1600, 2000, () -> System.currentTimeMillis() + off.get());
        for (int k = 0; k < 190; k++) {
            off.set(-59_000L + k * 300L);
            assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        }
        off.set(0);
        final long t0 = System.currentTimeMillis();
        final List<Long> priceOk = Collections.synchronizedList(new ArrayList<>());
        final AtomicBoolean stop = new AtomicBoolean();
        final AtomicLong oiOk = new AtomicLong(), priceDenied = new AtomicLong();
        Thread price = new Thread(() -> {
            while (!stop.get()) {
                if (b.acquire(2, RestBudget.Lane.HIGH, 5_000L)) priceOk.add(System.currentTimeMillis());
                else priceDenied.incrementAndGet();
                try { Thread.sleep(3000); } catch (InterruptedException e) { return; }
            }
        }, "sim-price");
        Thread oi = new Thread(() -> {
            while (!stop.get()) {
                if (b.acquire(1, RestBudget.Lane.LOW, 30_000L)) oiOk.incrementAndGet();
                try { Thread.sleep(250); } catch (InterruptedException e) { return; }
            }
        }, "sim-oi");
        price.start();
        oi.start();
        Thread.sleep(300);
        int early = pass(b, 752, 15_000L);
        long w = t0 + 26_000L - System.currentTimeMillis();
        if (w > 0) Thread.sleep(w);
        int sus = pass(b, 752, 15_000L);
        int smp = pass(b, 25, 15_000L);
        w = t0 + 62_000L - System.currentTimeMillis();
        if (w > 0) Thread.sleep(w);
        stop.set(true);
        price.interrupt();
        oi.interrupt();
        long end = System.currentTimeMillis();
        List<Long> p = new ArrayList<>(priceOk);
        p.add(end);
        long maxGap = 0, prev = p.get(0);
        for (long t : p) { maxGap = Math.max(maxGap, t - prev); prev = t; }
        String rep = String.format("A1-T1 early_ok=%d/752 suspects_ok=%d/752 sample_ok=%d/25 price_ok=%d price_denied=%d oi_ok=%d price_max_gap_ms=%d denied_total=%d",
                early, sus, smp, priceOk.size(), priceDenied.get(), oiOk.get(), maxGap, b.denied.get());
        System.out.println(rep);
        assertTrue("price_realtime dung qua 15 s khi WS chet toan phan: " + rep, maxGap <= 15_000L);
    }

    /** A1-T2: HTTP 418 giua chung khi 30 luong dang lay ngan sach: sau 418 khong cap them call nao, khong luong nao bi chan qua maxWait. */
    @Test(timeout = 60_000)
    public void t2_http418MidFlight() throws Exception {
        RestBudget b = new RestBudget(300, 1600, 2000, System::currentTimeMillis);
        AtomicLong grantedAfter = new AtomicLong(), maxBlock = new AtomicLong(), banAt = new AtomicLong(Long.MAX_VALUE);
        ExecutorService pool = Executors.newFixedThreadPool(30);
        List<Future<?>> fs = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            fs.add(pool.submit(() -> {
                long stopAt = System.currentTimeMillis() + 9_000L;
                while (System.currentTimeMillis() < stopAt) {
                    long s = System.currentTimeMillis();
                    boolean ok = b.acquire(1, RestBudget.Lane.HIGH, 5_000L);
                    maxBlock.accumulateAndGet(System.currentTimeMillis() - s, Math::max);
                    if (ok && s > banAt.get()) grantedAfter.incrementAndGet();
                    try { Thread.sleep(100); } catch (InterruptedException e) { return; }
                }
            }));
        }
        Thread.sleep(250);
        banAt.set(System.currentTimeMillis());
        b.observe(418, "2500", "3");   // Retry-After 3 s (+10 s SAFETY) => cooldown ~13 s
        for (Future<?> f : fs) f.get(30, TimeUnit.SECONDS);
        pool.shutdownNow();
        System.out.println("A1-T2 grantedAfter=" + grantedAfter.get() + " maxBlockMs=" + maxBlock.get() + " " + b.statsLine());
        assertEquals("khong duoc cap call nao trong cooldown 418", 0, grantedAfter.get());
        assertTrue("acquire bi chan qua maxWait: " + maxBlock.get(), maxBlock.get() <= 5_000L + 700L);
        assertTrue(BinanceRestGuard.isBanned());
    }

    /** A1-T2b: thieu header weight / Retry-After rac => khong chan, cooldown mac dinh. */
    @Test
    public void t2b_missingHeaders() {
        RestBudget b = new RestBudget(300, 1600, 2000, System::currentTimeMillis);
        b.observe(200, null, null);
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        b.observe(200, "abc", null);
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        long t = System.currentTimeMillis();
        b.observe(429, null, "xyz");
        assertTrue(BinanceRestGuard.BANNED_UNTIL_MS.get() >= t + 60_000L);
    }
}
