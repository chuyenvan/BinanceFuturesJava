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

/**
 * Test đối kháng của A1 (A1_QF_REPORT e93febb6, a1_wt) — tích hợp chính thức ở QF2, giữ kịch bản, đổi theo API lane mới:
 * kline = lane KLINE với thời gian chờ production ({@link RestBudget#maxWaitMs}, = 0), giá = lane PRICE, OI = lane FDATA.
 * Ngưỡng A1-T1 siết từ 15 s xuống 5 s (MASTER QF2).
 */
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

    /** Mô phỏng 1 pass KlineIngestCore.fetchAll: pool 30, mỗi symbol 2 lần thử (lane KLINE, chờ như production), timeout 15 s. */
    static int pass(RestBudget b, int n, long timeoutMs) {
        ExecutorService pool = Executors.newFixedThreadPool(30);
        AtomicInteger ok = new AtomicInteger();
        List<Future<?>> fs = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            fs.add(pool.submit(() -> {
                for (int a = 0; a < 2; a++) {
                    if (b.acquire(1, RestBudget.Lane.KLINE, RestBudget.maxWaitMs(RestBudget.Lane.KLINE))) {
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
     * A1-T1: WS chết toàn phần 1 phút. Nền 60 s trước: lane LOW đầy (repair/OI cũ). Rest-Price-Loop: PRICE mỗi 3 s.
     * +4 s pass 752 symbol; +26 s suspects 752 + sample 25. Yêu cầu QF2: không khoảng giá nào > 5 000 ms.
     */
    @Test(timeout = 150_000)
    public void t1_wsTotalLoss_priceRealtimeStarved() throws Exception {
        RestBudget b = new RestBudget(300, 1600, 2000, 150, () -> System.currentTimeMillis() + off.get());
        int low = 0;
        for (int k = 0; k < 400; k++) {
            off.set(-59_000L + k * 140L);
            if (b.tryAcquire(1, RestBudget.Lane.LOW) == 0) low++;
        }
        off.set(0);
        assertEquals("LOW day toi tran (han muc rieng 40)", 40, low);
        final long t0 = System.currentTimeMillis();
        final List<Long> priceOk = Collections.synchronizedList(new ArrayList<>());
        final AtomicBoolean stop = new AtomicBoolean();
        final AtomicLong oiOk = new AtomicLong(), priceDenied = new AtomicLong();
        Thread price = new Thread(() -> {
            while (!stop.get()) {
                if (b.acquire(2, RestBudget.Lane.PRICE, RestBudget.maxWaitMs(RestBudget.Lane.PRICE))) priceOk.add(System.currentTimeMillis());
                else priceDenied.incrementAndGet();
                try { Thread.sleep(3000); } catch (InterruptedException e) { return; }
            }
        }, "sim-price");
        Thread oi = new Thread(() -> {
            while (!stop.get()) {
                if (b.acquire(1, RestBudget.Lane.FDATA, RestBudget.maxWaitMs(RestBudget.Lane.FDATA))) oiOk.incrementAndGet();
                try { Thread.sleep(250); } catch (InterruptedException e) { return; }
            }
        }, "sim-oi");
        price.start();
        oi.start();
        Thread.sleep(300);
        long ts = System.currentTimeMillis();
        int early = pass(b, 752, 15_000L);
        long earlyMs = System.currentTimeMillis() - ts;
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
        long maxGap = 0, prev = t0;
        for (long t : p) { maxGap = Math.max(maxGap, t - prev); prev = t; }
        String rep = String.format("A1-T1(QF2) early_ok=%d/752 (%d ms) suspects_ok=%d/752 sample_ok=%d/25 price_ok=%d price_denied=%d oi_ok=%d price_max_gap_ms=%d denied_total=%d peak_weight<=%d",
                early, earlyMs, sus, smp, priceOk.size(), priceDenied.get(), oiOk.get(), maxGap, b.denied.get(), b.usedNow());
        System.out.println(rep);
        assertTrue("price_realtime dung qua 5 s khi WS chet toan phan: " + rep, maxGap <= 5_000L);
        assertEquals("gia khong bao gio bi tu choi", 0, priceDenied.get());
        assertTrue(oiOk.get() > 100);
    }

    /** A1-T2: HTTP 418 giữa chừng khi 30 luồng đang lấy ngân sách: sau 418 không cấp thêm call nào, không luồng nào bị chặn quá maxWait. */
    @Test(timeout = 60_000)
    public void t2_http418MidFlight() throws Exception {
        RestBudget b = new RestBudget(300, 1600, 2000, 150, System::currentTimeMillis);
        AtomicLong grantedAfter = new AtomicLong(), maxBlock = new AtomicLong(), banAt = new AtomicLong(Long.MAX_VALUE);
        ExecutorService pool = Executors.newFixedThreadPool(30);
        List<Future<?>> fs = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            final RestBudget.Lane lane = i % 3 == 0 ? RestBudget.Lane.PRICE : i % 3 == 1 ? RestBudget.Lane.LOW : RestBudget.Lane.FDATA;
            fs.add(pool.submit(() -> {
                long stopAt = System.currentTimeMillis() + 9_000L;
                while (System.currentTimeMillis() < stopAt) {
                    long s = System.currentTimeMillis();
                    boolean ok = b.acquire(1, lane, 5_000L);
                    maxBlock.accumulateAndGet(System.currentTimeMillis() - s, Math::max);
                    if (ok && s > banAt.get()) grantedAfter.incrementAndGet();
                    try { Thread.sleep(100); } catch (InterruptedException e) { return; }
                }
            }));
        }
        Thread.sleep(250);
        banAt.set(System.currentTimeMillis());
        b.observe(418, "2500", "3", null);   // Retry-After 3 s (+10 s SAFETY) => cooldown ~13 s
        for (Future<?> f : fs) f.get(30, TimeUnit.SECONDS);
        pool.shutdownNow();
        System.out.println("A1-T2 grantedAfter=" + grantedAfter.get() + " maxBlockMs=" + maxBlock.get() + " " + b.statsLine());
        assertEquals("khong duoc cap call nao trong cooldown 418", 0, grantedAfter.get());
        assertTrue("acquire bi chan qua maxWait: " + maxBlock.get(), maxBlock.get() <= 5_000L + 700L);
        assertTrue(BinanceRestGuard.isBanned());
    }

    /** A1-T2b: thiếu header weight / Retry-After rác ⇒ không chặn, cooldown mặc định. */
    @Test
    public void t2b_missingHeaders() {
        RestBudget b = new RestBudget(300, 1600, 2000, 150, System::currentTimeMillis);
        b.observe(200, null, null, null);
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        b.observe(200, "abc", null, "not a date");
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        long t = System.currentTimeMillis();
        b.observe(429, null, "xyz", null);
        assertTrue(BinanceRestGuard.BANNED_UNTIL_MS.get() >= t + 60_000L);
    }
}
