package com.binance.chuyennd.c3live.rate;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.RateLimitSpec;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.Assert.*;

/**
 * [V12 C13] Tieu chi: dot gia lap 24 leg + 80 vi the doi stop <= 50 % gioi han san o MOI cua so truot.
 * Kiem DOC LAP: tu ghi (t, weight, orders) moi call da duoc cho phep roi tu tinh cua so truot, khong dung bo dem cua RateGuard.
 */
public class RateGuardTest {

    static final class FakeClock implements RateGuard.Clock {
        long now = 1_761_400_000_000L;
        long slept;
        @Override public long nowMs() { return now; }
        @Override public void sleepMs(long ms) { now += ms; slept += ms; }
    }

    /** Ghi lai thoi diem duoc phep cua tung call. */
    static final class Recorder {
        final List<long[]> ev = new ArrayList<>();
        final FakeClock c;
        final RateGuard g;
        Recorder(FakeClock c, RateGuard g) { this.c = c; this.g = g; }
        void call(int weight, int orders) {
            g.acquire(weight, orders);
            ev.add(new long[]{c.now, weight, orders});
            c.now += 20; // latency gia lap 20 ms
        }
        long maxWindow(long windowMs, int idx) {
            long best = 0;
            for (int i = 0; i < ev.size(); i++) {
                long s = 0;
                for (int j = i; j < ev.size() && ev.get(j)[0] < ev.get(i)[0] + windowMs; j++) s += ev.get(j)[idx];
                best = Math.max(best, s);
            }
            return best;
        }
    }

    @Test
    public void burst24LegsPlus80StopMovesStaysUnderHalfLimits() {
        FakeClock c = new FakeClock();
        RateGuard.Limits lim = RateGuard.Limits.binanceDefault(); // 2400 / 300 / 1200
        RateGuard g = new RateGuard(lim, 0.5, 30_000L, c);
        Recorder r = new Recorder(c, g);
        long t0 = c.now;
        // 24 leg: MARKET (w1,o1) + query order (w1) + dat STOP (w1,o1)
        for (int i = 0; i < 24; i++) { r.call(1, 1); r.call(1, 0); r.call(1, 1); }
        // 80 vi the doi stop: openStops(sym) w1 + positionRisk w5 + STOP moi (w1,o1) + huy STOP cu (w1, tinh la lenh: bao thu)
        for (int i = 0; i < 80; i++) { r.call(1, 0); r.call(5, 0); r.call(1, 1); r.call(1, 1); }
        long w60 = r.maxWindow(60_000L, 1), o10 = r.maxWindow(10_000L, 2), o60 = r.maxWindow(60_000L, 2);
        assertEquals(24 * 3 + 80 * 4, r.ev.size());
        assertTrue("weight/1m " + w60, w60 <= lim.weight1m / 2);
        assertTrue("orders/10s " + o10, o10 <= lim.orders10s / 2);
        assertTrue("orders/1m " + o60, o60 <= lim.orders1m / 2);
        // tong 208 lenh > 150/10s -> bat buoc phai gian ra nhung xong trong han (khong RATE_LIMIT)
        assertEquals(208, r.ev.stream().mapToLong(e -> e[2]).sum());
        assertTrue("phai co cho", c.slept > 0);
        assertTrue("xong < 30 s gia lap: " + (c.now - t0), c.now - t0 < 30_000L);
        assertEquals(0, g.rejects());
        assertTrue(g.peakOrders10s() <= 150);
    }

    @Test
    public void exhaustedBudgetBeyondMaxWaitThrowsRateLimitWithoutRecording() {
        FakeClock c = new FakeClock();
        RateGuard g = new RateGuard(new RateGuard.Limits(100, 10, 100, true), 0.5, 1_000L, c); // budget w50 o5 o50
        for (int i = 0; i < 5; i++) g.acquire(1, 1);
        try {
            g.acquire(1, 1);
            fail();
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
            assertTrue(e.isDefinitelyNotExecuted());
            assertTrue(e.getRetryAfterMs() > 1_000L);
        }
        assertEquals(5, g.usedOrders10s());
        c.now += 10_001L;
        g.acquire(1, 1);
        assertEquals(1, g.usedOrders10s());
    }

    @Test
    public void fractionClampedToHalf() {
        RateGuard g = new RateGuard(new RateGuard.Limits(2400, 300, 1200, true), 0.9, 0L, new FakeClock());
        assertEquals(1200, g.budgetWeight1m());
        assertEquals(150, g.budgetOrders10s());
        assertEquals(600, g.budgetOrders1m());
        RateGuard g2 = new RateGuard(new RateGuard.Limits(2400, 300, 1200, true), 0.25, 0L, new FakeClock());
        assertEquals(600, g2.budgetWeight1m());
    }

    @Test
    public void limitsFromExchangeInfo() {
        ExchangeInfo ei = new ExchangeInfo(0L, Arrays.asList(new RateLimitSpec("REQUEST_WEIGHT", "MINUTE", 1, 6000),
                new RateLimitSpec("ORDERS", "SECOND", 10, 100), new RateLimitSpec("ORDERS", "MINUTE", 1, 400)), Collections.emptyList());
        RateGuard.Limits l = RateGuard.Limits.fromExchangeInfo(ei);
        assertEquals(6000, l.weight1m);
        assertEquals(100, l.orders10s);
        assertEquals(400, l.orders1m);
        assertTrue(l.fromExchange);
        RateGuard.Limits d = RateGuard.Limits.fromExchangeInfo(new ExchangeInfo(0L, null, null));
        assertEquals(2400, d.weight1m);
        assertFalse(d.fromExchange);
    }

    @Test
    public void serverHeaderWeightAboveBudgetWaitsForNextMinute() {
        FakeClock c = new FakeClock();
        c.now = 1_761_400_040_000L; // giay 20 cua phut (1_761_400_020_000 la dau phut)
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 60_000L, c);
        g.onHeaders(1_195, null, null); // LEGACY cung IP da dung 1195
        long before = c.now;
        g.acquire(10, 0);
        assertTrue("phai cho sang phut moi", c.now / 60_000L > before / 60_000L);
        // han ngan -> RATE_LIMIT
        FakeClock c2 = new FakeClock();
        c2.now = 1_761_400_020_000L;
        RateGuard g2 = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 1_000L, c2);
        g2.onHeaders(1_199, null, null);
        try { g2.acquire(5, 0); fail(); } catch (GatewayException e) { assertEquals(ErrorKind.RATE_LIMIT, e.getKind()); }
    }

    @Test
    public void http429BacksOffAnd418HonoursRetryAfter() {
        FakeClock c = new FakeClock();
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 0L, c);
        long until = g.onRateLimited(429, 0L);
        assertEquals(c.now + 2_000L, until);
        try { g.acquire(1, 0); fail(); } catch (GatewayException e) { assertEquals(ErrorKind.RATE_LIMIT, e.getKind()); }
        long until2 = g.onRateLimited(429, 0L);
        assertEquals(c.now + 4_000L, until2); // 2^n
        c.now += 4_001L;
        g.acquire(1, 0);
        g.onSuccess();
        long ban = g.onRateLimited(418, 120_000L);
        assertEquals(c.now + 120_000L, ban);
        RateGuard g3 = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 0L, c);
        assertEquals(c.now + RateGuard.BAN_418_DEFAULT_MS, g3.onRateLimited(418, 0L));
    }

    @Test
    public void singleRequestBiggerThanBudgetRejected() {
        RateGuard g = new RateGuard(new RateGuard.Limits(20, 300, 1200, true), 0.5, 5_000L, new FakeClock());
        try { g.acquire(11, 0); fail(); } catch (GatewayException e) { assertEquals(ErrorKind.RATE_LIMIT, e.getKind()); }
    }
}
