package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.rate.ProductionRatePolicy;
import com.binance.chuyennd.c3live.rate.RateGuard;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 R4 R5] (f) rate production = chinh sach canary 3i: header IP 1494 o giay :30 => call doc thuong cho toi :41 roi THANH
 * CONG; stop bao ve duoi tai IP nang van dat duoc &lt;= 61 s (guard tu choi => cho sang phut moi trong han Urgent), hoac qua han
 * => dong qty c3 qua lan khan cap (khong bi guard cua ta chan).
 */
public class C3ProdRateTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final class FakeClock implements RateGuard.Clock {
        final AtomicLong t;
        final List<Long> sleeps = new ArrayList<>();

        FakeClock(long t0) {
            t = new AtomicLong(t0);
        }

        @Override
        public long nowMs() {
            return t.get();
        }

        @Override
        public void sleepMs(long ms) {
            sleeps.add(ms);
            t.addAndGet(ms);
        }
    }

    @Test
    public void policyIsCanary3iFromEnv() {
        RateGuard.CanaryPolicy p = ProductionRatePolicy.policy(k -> null);
        assertEquals(1800, p.ipAdmitCap);
        assertEquals(600, p.ownCap);
        assertEquals(27, p.burstFromSec);
        assertEquals(40, p.burstToSec);
        assertEquals(41, p.burstResumeSec);
        assertEquals(2, p.readMaxWaits);
        assertEquals(61_000L, p.readWaitMaxMs);
        assertEquals(1600, ProductionRatePolicy.policy(k -> "1600").ipAdmitCap);
        assertEquals(1920, ProductionRatePolicy.policy(k -> "5000").ipAdmitCap);
        assertEquals(1800, ProductionRatePolicy.policy(k -> "abc").ipAdmitCap);
    }

    @Test
    public void ipHeader1494AtSecond30ReadsWaitAndSucceed() {
        long minute = 1_792_900_020_000L - Math.floorMod(1_792_900_020_000L, 60_000L);
        FakeClock c = new FakeClock(minute + 30_000L);
        RateGuard g = ProductionRatePolicy.guard(k -> null, c);
        g.onHeaders(1494, null, null);
        // 7 call doc (positionRisk 5, openOrders 40, openAlgo 40, account 5 ...) — khong call nao bi tu choi
        int[] w = {5, 40, 40, 5, 1, 1, 5};
        for (int x : w) {
            g.acquire(x, 0, 2_000L, true);
            g.onHeaders(Math.min(2399, 1494 + x), null, null);
        }
        assertFalse(c.sleeps.isEmpty());
        assertEquals("ngu toi giay 41", 11_000L, (long) c.sleeps.get(0));
        assertEquals(0L, g.rejects());
        assertTrue(Math.floorMod(c.nowMs(), 60_000L) >= 41_000L);
    }

    @Test
    public void ipHeaderSaturatedReadsWaitNextMinuteThenSucceed() {
        long minute = 1_792_900_020_000L - Math.floorMod(1_792_900_020_000L, 60_000L);
        FakeClock c = new FakeClock(minute + 45_000L);
        RateGuard g = ProductionRatePolicy.guard(k -> null, c);
        g.onHeaders(2300, null, null);
        g.acquire(5, 0, 2_000L, true);
        assertEquals(1, c.sleeps.size());
        assertTrue(c.sleeps.get(0) <= 61_000L);
        assertTrue(c.nowMs() >= minute + 60_000L);
        // lan khan cap: khong bi nguong IP 1800 / rieng 600 chan (chi 100 % gioi han san)
        g.onHeaders(2300, null, null);
        int n = c.sleeps.size();
        try (RateGuard.Lane l = RateGuard.emergencyLane()) {
            g.acquire(1, 1, 2_000L, false);
        }
        assertEquals(n, c.sleeps.size());
    }

    /** Mock: guard client tu choi (chua gui) moi lenh ghi THUONG cho toi {@code busyUntil}; lan khan cap luon qua. */
    static final class BusyIpMock extends MockExchangeGateway {
        volatile long busyUntil;
        final List<String> log = new java.util.concurrent.CopyOnWriteArrayList<>();

        private void gate(String what) {
            if (RateGuard.inEmergencyLane()) {
                log.add(what + ":emerg");
                return;
            }
            long left = busyUntil - now;
            if (left > 0) {
                log.add(what + ":refused(" + left + ")");
                throw new GatewayException(ErrorKind.RATE_LIMIT, 0, 0, "rate guard: het ngan sach (IP nang)", true, left, null);
            }
            log.add(what + ":ok:urgent=" + RateGuard.inUrgent());
        }

        @Override
        public synchronized OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String cid,
                                                    boolean reduceOnly) {
            gate("STOP");
            return super.newStopMarket(symbol, side, qty, stopPrice, cid, reduceOnly);
        }

        @Override
        public OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean reduceOnly) {
            if (cid != null && cid.startsWith("c3x-")) gate("CLOSE");
            return super.newMarketOrder(symbol, side, qty, cid, reduceOnly);
        }
    }

    @Test
    public void protectiveStopUnderHeavyIpLandsWithin61s() throws Exception {
        BusyIpMock m = new BusyIpMock();
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), m, 10_000d);
        String s = C3LiveFixtures.sym(0);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.tick(s, "1.10");
        String cid = r.book.cluster(s).get().stopClientAlgoId;
        long t0 = r.now.get();
        m.busyUntil = t0 + 40_000L;   // IP nang 40 s
        r.mock.exchangeEndStop(cid, "EXPIRED");
        r.protector.check();
        String c2 = r.book.cluster(s).get().stopClientAlgoId;
        assertNotNull("stop dat lai sau khi cho guard (trong han)", c2);
        assertTrue("<= 61 s: " + (r.now.get() - t0), r.now.get() - t0 <= 61_000L);
        assertTrue(m.log.toString(), m.log.toString().contains("refused"));
        assertTrue(m.log.get(m.log.size() - 1), m.log.get(m.log.size() - 1).startsWith("STOP:ok:urgent=true"));
        assertTrue(r.book.isHolding(s));
    }

    @Test
    public void protectiveStopBlockedPastDeadlineFlattensViaEmergencyLane() throws Exception {
        BusyIpMock m = new BusyIpMock();
        MainAccountRig r = new MainAccountRig(tmp.getRoot(), m, 10_000d);
        String s = C3LiveFixtures.sym(0);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.tick(s, "1.10");
        String cid = r.book.cluster(s).get().stopClientAlgoId;
        long t0 = r.now.get();
        m.busyUntil = t0 + 600_000L;   // IP bao hoa 10'
        r.mock.exchangeEndStop(cid, "EXPIRED");
        r.protector.check();
        assertNull(r.book.cluster(s).get().stopClientAlgoId);
        assertTrue("khong cho qua han Urgent", r.now.get() - t0 <= 61_000L);
        r.now.set(t0 + 62_000L);
        r.sync();
        r.protector.check();
        assertTrue(m.log.toString(), m.log.toString().contains("CLOSE:emerg"));
        assertEquals(0, r.mock.position(s).signum());
        for (int i = 0; i < MainAccountRig.LEGACY_N; i++) {
            String lg = MainAccountRig.legacySym(i);
            assertEquals(0, r.legacyExpected.get(lg).compareTo(r.mock.position(lg)));
        }
    }
}
