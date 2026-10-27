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

    // ------------------------------------------------------------------ [3e] lan khan cap (flatten / cleanup)
    static long alignedAt(FakeClock c, long secMs) {
        c.now = (c.now / 60_000L) * 60_000L + secMs;
        return c.now;
    }

    @Test
    public void emergencyLaneRunsWhenServerWeightExceedsBudget() {
        FakeClock c = new FakeClock();
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c);
        alignedAt(c, 46_000L);              // giay :46 nhu flatten 10-27 22:18:46
        g.onHeaders(1494, null, null);      // IP chung LEGACY: 1494 > ngan sach 1200
        try {
            g.acquire(5, 0);
            fail("lan thuong phai bi tu choi (can cho > 2 s)");
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
        }
        long slept0 = c.slept;
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
            assertTrue(RateGuard.inEmergencyLane());
            for (int i = 0; i < 20; i++) g.acquire(5, 0);
            g.acquire(1, 1);
        }
        assertEquals("khan cap: khong cho", slept0, c.slept);
        assertEquals(21, g.emergencyCalls());
        assertEquals(21, g.emergencyOverBudget());
        assertFalse(RateGuard.inEmergencyLane());
        try {
            g.acquire(5, 0);
            fail("ra khoi lan khan cap => lai bi chan");
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
        }
    }

    @Test
    public void emergencyLaneRunsWhenInternalBudgetExhausted() {
        FakeClock c = new FakeClock();
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c);
        for (int i = 0; i < 30; i++) g.acquire(40, 0);   // 1200 = het ngan sach noi bo
        try {
            g.acquire(5, 0);
            fail();
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
        }
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
            g.acquire(5, 0);
            g.acquire(1, 1);
            g.acquire(2_000, 0);   // ca 1 call > ngan sach cung khong bi tu choi trong lan khan cap
        }
        assertEquals(0L, c.slept);
        assertEquals(3, g.emergencyCalls());
    }

    @Test
    public void emergencyLaneStillBacksOffOnExchange429And418() {
        FakeClock c = new FakeClock();
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c);
        g.onRateLimited(429, 5_000L);
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
            g.acquire(5, 0);
        }
        assertTrue("429: van cho het back-off cua san", c.slept >= 5_000L);
        g.onRateLimited(418, 300_000L);
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
            g.acquire(5, 0);
            fail("418 chan 300 s > 125 s => loi san");
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
            assertTrue(e.getMessage(), e.getMessage().contains("429/418"));
        }
        assertEquals(1, g.emergencyBlocked());
    }

    @Test
    public void emergencyLaneWaitsForNextMinuteOnlyAtFullExchangeLimit() {
        FakeClock c = new FakeClock();
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c);
        alignedAt(c, 50_000L);
        g.onHeaders(2398, null, null);      // 2398 + 5 > 2400 (100 % gioi han san) => gui se an 429
        try (RateGuard.Lane lane = RateGuard.emergencyLane()) {
            g.acquire(5, 0);
        }
        assertTrue("cho sang phut moi, khong tu choi: " + c.slept, c.slept > 0 && c.slept <= 10_001L);
        assertEquals(1, g.emergencyCalls());
    }

    @Test
    public void emergencyLaneIsPerThreadAndNested() throws Exception {
        final boolean[] other = new boolean[1];
        try (RateGuard.Lane a = RateGuard.emergencyLane()) {
            try (RateGuard.Lane b = RateGuard.emergencyLane()) {
                assertTrue(RateGuard.inEmergencyLane());
            }
            assertTrue("long nhau: van trong lan", RateGuard.inEmergencyLane());
            Thread t = new Thread(() -> other[0] = RateGuard.inEmergencyLane());
            t.start();
            t.join();
        }
        assertFalse("luong khac khong thua lan khan cap", other[0]);
        assertFalse(RateGuard.inEmergencyLane());
    }

    // ------------------------------------------------------------------ [3i] chinh sach canary (IP chung LEGACY)
    static RateGuard.CanaryPolicy canaryPolicy() {
        return new RateGuard.CanaryPolicy(1800, 600, 27, 40, 41, 2, 61_000L);
    }

    static long atSecond(long t, int sec) {
        return Math.floorDiv(t, 60_000L) * 60_000L + 60_000L + sec * 1000L;
    }

    /** weight cac call cua keycheck (W_* C3LiveClient): serverTime, account, multiAssets, dual, positions, openOrders all, openStops all. */
    static final int[] KEYCHECK_W = {1, 5, 30, 30, 5, 40, 40};

    @Test
    public void i3KeycheckAtSecond30WithIpHeader1494WaitsAndSucceedsNeverAboveCap() {
        // 3h that 05:11:42: header IP 1494 (LEGACY) > ngan sach 50 % = 1200 => keycheck TRUOT "can cho 15660 ms > han 2000 ms"
        FakeClock c0 = new FakeClock();
        c0.now = atSecond(c0.now, 30);
        RateGuard old = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c0);
        old.onHeaders(1494, null, null);
        try {
            old.acquire(1, 0, 2_000L);
            fail("hanh vi 3h: phai bi tu choi");
        } catch (GatewayException e) {
            assertTrue(e.getMessage(), e.getMessage().contains("het ngan sach"));
        }
        // 3i: nguong IP 1800, rieng 600, burst [27, 40] => ngu toi :41 roi gui; KHONG lan gui nao co IP + cost > 1800
        FakeClock c = new FakeClock();
        c.now = atSecond(c.now, 30);
        long minute = Math.floorDiv(c.now, 60_000L);
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c, canaryPolicy());
        int ip = 1494;   // weight IP cua phut nay (LEGACY), san bao qua header
        g.onHeaders(ip, null, null);
        List<long[]> sends = new ArrayList<>();
        for (int w : KEYCHECK_W) {
            g.acquire(w, 0, 2_000L, true);
            sends.add(new long[]{c.now, ip, w});
            ip += w;                                  // san tinh weight cua call vua gui
            g.onHeaders(ip, null, null);
            c.now += 20;
        }
        assertEquals(KEYCHECK_W.length, sends.size());
        assertEquals("cung phut (khong cho sang phut moi)", minute, Math.floorDiv(sends.get(0)[0], 60_000L));
        assertTrue("ngu qua cua so burst toi giay 41", Math.floorMod(sends.get(0)[0], 60_000L) >= 41_000L);
        assertEquals(1, g.burstSleeps());
        for (long[] s : sends) assertTrue("IP " + s[1] + " + " + s[2] + " <= 1800", s[1] + s[2] <= 1800);
        assertEquals(0, g.readWaitsTotal());
        assertEquals(0, g.rejects());
    }

    @Test
    public void i3ReadWithIpHeader2300WaitsAtMostTwiceThenFailsCleanly() {
        final RateGuard[] ref = new RateGuard[1];
        final List<Long> sleeps = new ArrayList<>();
        final long[] t = {atSecond(1_761_400_000_000L, 5)};
        RateGuard.Clock c = new RateGuard.Clock() {
            @Override public long nowMs() { return t[0]; }
            @Override public void sleepMs(long ms) {
                t[0] += ms;
                sleeps.add(ms);
                ref[0].onHeaders(2300, null, null);   // gia lap: IP VAN bao hoa o phut moi (LEGACY)
            }
        };
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c, canaryPolicy());
        ref[0] = g;
        g.onHeaders(2300, null, null);
        try {
            g.acquire(5, 0, 2_000L, true);
            fail("phai loi sau 2 lan cho");
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
            assertTrue(e.isDefinitelyNotExecuted());
            assertEquals("retryAfter 0 => lop tren khong cho them", 0L, e.getRetryAfterMs());
            assertTrue(e.getMessage(), e.getMessage().contains("da cho 2 lan"));
        }
        assertEquals(2, sleeps.size());
        for (long s : sleeps) assertTrue("moi lan cho <= 61 s: " + s, s > 0 && s <= 61_000L);
        assertEquals("khong gui", 0L, g.usedWeight1m());
        assertEquals(2, g.readWaitsTotal());
        // lenh GHI: khong cho trong RateGuard (CanaryGateway kiem lai roi thu lai) — loi ngay kem retryAfter <= 61 s
        sleeps.clear();
        try {
            g.acquire(1, 1, 2_000L, false);
            fail("ghi phai bi tu choi");
        } catch (GatewayException e) {
            assertTrue(e.getRetryAfterMs() > 0 && e.getRetryAfterMs() <= 61_000L);
        }
        assertTrue(sleeps.isEmpty());
    }

    @Test
    public void i3ReadRefusedOnceSucceedsAfterMinuteRolls() {
        FakeClock c = new FakeClock();
        c.now = atSecond(c.now, 50);
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c, canaryPolicy());
        g.onHeaders(1795, null, null);   // 1795 + 40 > 1800
        long m0 = Math.floorDiv(c.now, 60_000L);
        g.acquire(40, 0, 2_000L, true);
        assertEquals("gui o phut sau", m0 + 1, Math.floorDiv(c.now, 60_000L));
        assertTrue(c.slept <= 61_000L);
        assertEquals(1, g.readWaitsTotal());
    }

    @Test
    public void i3OwnWeightCap600() {
        FakeClock c = new FakeClock();
        c.now = atSecond(c.now, 0);
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c, canaryPolicy());
        Recorder r = new Recorder(c, g);
        for (int i = 0; i < 15; i++) r.call(40, 0);   // 600 = tran rieng (header khong co)
        assertEquals(0L, c.slept);
        long t = c.now;
        g.acquire(40, 0, 2_000L, true);             // 640 > 600 => cho call cu nhat het han (doc: <= 61 s)
        assertTrue(c.now - t > 2_000L && c.now - t <= 61_000L);
        assertEquals(1, g.readWaitsTotal());
        try {
            g.acquire(601, 0, 2_000L, true);
            fail("1 call > tran rieng");
        } catch (GatewayException e) {
            assertTrue(e.getMessage().contains("vuot ngan sach"));
        }
    }

    @Test
    public void i3BurstWindowSleepSkippedOnEmergencyLaneAndUrgentAndWrites() {
        FakeClock c = new FakeClock();
        c.now = atSecond(c.now, 30);
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c, canaryPolicy());
        try (RateGuard.Lane l = RateGuard.emergencyLane()) {
            g.acquire(5, 0, 2_000L, true);
            g.acquire(1, 1, 2_000L, false);
        }
        assertEquals("lan khan cap: khong ngu burst", 0L, c.slept);
        assertEquals(2, g.emergencyCalls());
        try (RateGuard.Urgent u = RateGuard.urgent(c.now + 61_000L)) {
            g.acquire(5, 0, 2_000L, true);           // stop bao ve: doc xac nhan
            g.acquire(1, 1, 2_000L, false);          // dat stop
        }
        assertEquals("pham vi KHAN (stop bao ve): khong ngu burst", 0L, c.slept);
        assertFalse(RateGuard.inUrgent());
        g.acquire(1, 1, 2_000L, false);              // lenh ghi thuong: CanaryGateway ngu burst TRUOC kiem (khong ngu o day)
        assertEquals(0L, c.slept);
        g.acquire(5, 0, 2_000L, true);               // doc thuong trong [27, 40] => ngu toi :41
        assertEquals(11_000L, c.slept);
        assertEquals(1, g.burstSleeps());
        c.now = atSecond(c.now, 26);
        long s0 = c.slept;
        g.acquire(5, 0, 2_000L, true);               // giay 26: ngoai cua so
        assertEquals(s0, c.slept);
        assertEquals(0L, RateGuard.burstDelayMs(atSecond(0L, 41), canaryPolicy()));
        assertEquals(1_000L, RateGuard.burstDelayMs(atSecond(0L, 40), canaryPolicy()));
        assertEquals(0L, RateGuard.burstDelayMs(atSecond(0L, 30), null));
    }

    @Test
    public void i3UrgentDeadlineNeverWaitedPast() {
        FakeClock c = new FakeClock();
        c.now = atSecond(c.now, 50);
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c, canaryPolicy());
        g.onHeaders(1799, null, null);   // can cho sang phut moi (~10 s)
        try (RateGuard.Urgent u = RateGuard.urgent(c.now + 5_000L)) {
            g.acquire(5, 0, 2_000L, true);
            fail("doc trong pham vi KHAN khong duoc cho qua han");
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
        }
        assertEquals(0L, c.slept);
    }

    @Test
    public void i3NoPolicyKeepsOldBehaviour() {
        FakeClock c = new FakeClock();
        c.now = atSecond(c.now, 30);
        RateGuard g = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, c);
        g.acquire(5, 0, 2_000L, true);   // khong chinh sach: khong ngu burst
        assertEquals(0L, c.slept);
        assertNull(g.policy());
    }
}
