package com.binance.chuyennd.c3live.exec;

import com.binance.chuyennd.c3live.api.ClientOrderIds;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderKind;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 C3] Idempotency: timeout SAU KHI san da nhan => queryOrder theo cid truoc khi gui lai => 0 lenh trung tren 1 000
 * luot ngau nhien (ca crash/restart giua chung). San gia lap KHONG tu chan cid trung (dem so lan khop moi cid) de
 * kiem chinh logic cua executor, khong dua vao san.
 */
public class C3LiveOrderExecutorTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    /** Crash JVM gia lap (khong phai RuntimeException => thoat khoi place nhu tien trinh chet). */
    static final class Crash extends Error {
        Crash() {
            super("crash");
        }
    }

    static final class FlakyGw extends MockExchangeGateway {
        final Random rnd;
        final Map<String, Integer> execCount = new HashMap<>();
        final Map<String, OrderInfo> exec = new HashMap<>();
        double pReject = 0.05, pPreTimeout = 0.15, pAckTimeout = 0.25, pCrashAfter = 0.05, pCrashBefore = 0.03,
                pQueryErr = 0.25;
        long seq = 1;

        FlakyGw(long seed) {
            rnd = new Random(seed);
        }

        @Override
        public synchronized OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean ro) {
            assertTrue(ClientOrderIds.isValid(cid));
            double r = rnd.nextDouble();
            double a = pReject;
            if (r < a) throw new GatewayException(ErrorKind.INSUFFICIENT_MARGIN, 400, -2019, "margin", true, 0L, null);
            a += pPreTimeout;
            if (r < a) throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0, "timeout(truoc)", false, 0L, null);
            a += pCrashBefore;
            if (r < a) throw new Crash();
            execCount.merge(cid, 1, Integer::sum);
            OrderInfo o = OrderInfo.builder().kind(OrderKind.REGULAR).symbol(symbol).orderId(seq++).clientOrderId(cid)
                    .side(side).type("MARKET").status(OrderStatus.FILLED).rawStatus("FILLED").origQty(qty).executedQty(qty)
                    .avgPrice(new BigDecimal("1.01")).reduceOnly(ro).updateTimeMs(0L).build();
            exec.put(cid, o);
            a += pAckTimeout;
            if (r < a) throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0, "timeout(sau)", false, 0L, null);
            a += pCrashAfter;
            if (r < a) throw new Crash();
            return o;
        }

        @Override
        public synchronized Optional<OrderInfo> queryOrder(String symbol, String cid) {
            if (rnd.nextDouble() < pQueryErr) {
                throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0, "query timeout", false, 0L, null);
            }
            if (!exec.containsKey(cid) && rnd.nextBoolean()) {
                throw new GatewayException(ErrorKind.UNKNOWN_ORDER, 400, -2013, "Order does not exist", true, 0L, null);
            }
            return Optional.ofNullable(exec.get(cid));
        }
    }

    private static C3LiveOrderExecutor exec(FlakyGw gw, LiveBookC3 book, AtomicLong now, List<String> fills) {
        return new C3LiveOrderExecutor(gw, book, null, (s, b, f, r) -> fills.add(s + "@" + f + "/" + r), now::get,
                ms -> now.addAndGet(ms), 10_000L, 3, Runnable::run);
    }

    @Test
    public void thousandRandomTrialsZeroDuplicates() {
        FlakyGw gw = new FlakyGw(20261025L);
        AtomicLong now = new AtomicLong(1_792_900_000_000L);
        File f = new File(tmp.getRoot(), "run/c3live_book.json");
        List<String> fills = new ArrayList<>();
        int restarts = 0, confirmed = 0, cancelled = 0, resent = 0;
        List<String> cids = new ArrayList<>();
        for (int i = 0; i < 1000; i++) {
            if (f.exists()) assertTrue(f.delete());
            LiveBookC3 book = new LiveBookC3(f, 1.0);
            C3LiveOrderExecutor ex = exec(gw, book, now, fills);
            String sym = "S" + (i % 37) + "USDT";
            String cid = C3LiveCids.entry(sym, 29_880_000L + i, i % 4);
            cids.add(cid);
            assertTrue(book.reserve(sym, cid, i % 4, 29_880_000L + i, "BIG_DOWN", 1.0, new BigDecimal("12"), 12.0, now.get()));
            boolean crashed = false;
            try {
                ex.place(cid);
            } catch (Crash c) {
                crashed = true;
            }
            int guard = 0;
            if (crashed) {
                // restart: so nap tu file, executor moi, KHONG gui lai — chi tra san
                restarts++;
                book = new LiveBookC3(f, 1.0);
                ex = exec(gw, book, now, fills);
                now.addAndGet(15_000L);
                while (ex.resolveUnresolved(true) > 0 && guard++ < 200) now.addAndGet(5_000L);
            } else {
                while (ex.resolveUnresolved(false) > 0 && guard++ < 200) now.addAndGet(5_000L);
            }
            assertEquals("leg treo sau giai quyet trial " + i, 0, book.unresolvedLegs().size());
            int n = gw.execCount.getOrDefault(cid, 0);
            assertTrue("LENH TRUNG cid=" + cid + " n=" + n, n <= 1);
            boolean holding = book.isHolding(sym);
            assertEquals("so lech san trial " + i + " n=" + n, n == 1, holding);
            if (holding) {
                confirmed++;
                assertEquals(LiveBookC3.LegState.CONFIRMED, book.leg(cid).get().state);
            } else {
                cancelled++;
            }
            now.addAndGet(60_000L);
        }
        int dup = 0;
        for (String c : cids) if (gw.execCount.getOrDefault(c, 0) > 1) dup++;
        assertEquals(0, dup);
        assertTrue("phai co restart trong kich ban", restarts > 20);
        assertTrue(confirmed > 500);
        assertTrue(cancelled > 50);
        assertEquals(confirmed, fills.size());
    }

    @Test
    public void ackThenTimeoutQueriesBeforeRetryNoDuplicate() {
        FlakyGw gw = new FlakyGw(1L);
        gw.pReject = 0;
        gw.pPreTimeout = 0;
        gw.pCrashBefore = 0;
        gw.pAckTimeout = 1.0;   // luon: san nhan roi timeout
        gw.pCrashAfter = 0;
        gw.pQueryErr = 0;
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        List<String> fills = new ArrayList<>();
        C3LiveOrderExecutor ex = exec(gw, book, now, fills);
        assertTrue(book.reserve("AUSDT", "c3-AUSDT-1-0", 0, 1, "X", 1.0, BigDecimal.TEN, 10.0, now.get()));
        long t0 = now.get();
        ex.submit("c3-AUSDT-1-0");
        assertEquals(1, (int) gw.execCount.get("c3-AUSDT-1-0"));
        assertEquals(LiveBookC3.LegState.CONFIRMED, book.leg("c3-AUSDT-1-0").get().state);
        assertEquals(1, book.leg("c3-AUSDT-1-0").get().attempts);
        assertTrue("phai cho het cua so an toan truoc khi tra", now.get() - t0 >= 10_000L);
        assertEquals(1, fills.size());
    }

    @Test
    public void absentAfterTimeoutResendsSameCidThenGivesUp() {
        FlakyGw gw = new FlakyGw(2L);
        gw.pReject = 0;
        gw.pPreTimeout = 1.0;   // luon timeout TRUOC khi san nhan
        gw.pQueryErr = 0;
        AtomicLong now = new AtomicLong(1_000_000L);
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        C3LiveOrderExecutor ex = exec(gw, book, now, new ArrayList<>());
        book.reserve("AUSDT", "c3-AUSDT-1-0", 0, 1, "X", 1.0, BigDecimal.TEN, 10.0, now.get());
        ex.submit("c3-AUSDT-1-0");
        assertFalse(book.isHolding("AUSDT"));
        assertEquals(0, gw.execCount.getOrDefault("c3-AUSDT-1-0", 0).intValue());
    }

    @Test
    public void definitelyNotExecutedCancelsWithoutQuery() {
        MockExchangeGateway gw = new MockExchangeGateway();
        gw.failNext("newMarketOrder", new GatewayException(ErrorKind.FILTER, 400, -4164, "notional", true, 0L, null));
        AtomicLong now = new AtomicLong(1_000L);
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(gw, book, null, null, now::get, ms -> now.addAndGet(ms), 10_000L, 3,
                Runnable::run);
        book.reserve("AUSDT", "c3-AUSDT-1-0", 0, 1, "X", 1.0, BigDecimal.TEN, 10.0, now.get());
        ex.submit("c3-AUSDT-1-0");
        assertFalse(book.isHolding("AUSDT"));
        assertEquals(0, gw.calls("queryOrder"));
    }

    @Test
    public void restartPendingNeverSentIsCancelledNotSent() {
        MockExchangeGateway gw = new MockExchangeGateway();
        File f = new File(tmp.getRoot(), "b.json");
        LiveBookC3 book = new LiveBookC3(f, 1.0);
        book.reserve("AUSDT", "c3-AUSDT-1-0", 0, 1, "X", 1.0, BigDecimal.TEN, 10.0, 1_000L);
        LiveBookC3 r = new LiveBookC3(f, 1.0);
        AtomicLong now = new AtomicLong(100_000L);
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(gw, r, null, null, now::get, ms -> now.addAndGet(ms), 10_000L, 3,
                Runnable::run);
        assertEquals(0, ex.resolveUnresolved(true));
        assertFalse(r.isHolding("AUSDT"));
        assertEquals(0, gw.calls("newMarketOrder"));
    }

    @Test
    public void cidFormatAndLimits() {
        assertEquals("c3-BTCUSDT-29880000-0", C3LiveCids.entry("BTCUSDT", 29_880_000L, 0));
        assertEquals("c3x-BTCUSDT-29880001-2", C3LiveCids.close("BTCUSDT", 29_880_001L, 2));
        assertEquals(29_880_000L, C3LiveCids.barMin(29_880_000L * 60_000L + 59_999L));
        String nonAscii = C3LiveCids.entry("币安人生USDT", 29_880_000L, 3);
        assertTrue(ClientOrderIds.isValid(nonAscii));
        assertTrue(nonAscii.startsWith("c3-x"));
        String longSym = C3LiveCids.entry("ABCDEFGHIJKLMNOPQRSTUVWXYZ1000USDT", 29_880_000L, 5);
        assertTrue(ClientOrderIds.isValid(longSym));
        assertTrue(longSym.length() <= 36);
        assertNotEquals(C3LiveCids.entry("AUSDT", 1, 0), C3LiveCids.entry("AUSDT", 1, 1));
        assertNotEquals(C3LiveCids.entry("AUSDT", 1, 0), C3LiveCids.entry("AUSDT", 2, 0));
    }
}
