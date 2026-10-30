package com.binance.chuyennd.utils;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** [INGEST-QF] Ngân sách REST cứng: bảng weight, lane, cửa sổ trượt, header, 429/418. */
public class RestBudgetTest {
    final AtomicLong off = new AtomicLong();
    RestBudget b;

    @Before
    public void setUp() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        b = new RestBudget(300, 1600, 2000, () -> System.currentTimeMillis() + off.get());
    }

    @After
    public void tearDown() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        RestBudget.reset(null);
    }

    static final String F = "https://fapi.binance.com";

    @Test
    public void weightTable() {
        assertEquals(1, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=3"));
        assertEquals(1, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=99"));
        assertEquals(2, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=100"));
        assertEquals(5, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m"));   // mac dinh limit 500 => 5
    }

    @Test
    public void weightTableOthers() {
        assertEquals(5, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=X&interval=1m&limit=500"));
        assertEquals(10, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=X&interval=1m&limit=1500"));
        assertEquals(2, RestBudget.weightOf(F + "/fapi/v1/ticker/price"));
        assertEquals(1, RestBudget.weightOf(F + "/fapi/v1/ticker/price?symbol=BTCUSDT"));
        assertEquals(40, RestBudget.weightOf(F + "/fapi/v1/ticker/24hr"));
        assertEquals(10, RestBudget.weightOf(F + "/fapi/v1/premiumIndex"));
        assertEquals(1, RestBudget.weightOf(F + "/futures/data/openInterestHist?symbol=X&period=5m&limit=8"));
        assertEquals(5, RestBudget.weightOf(F + "/fapi/v9/unknown"));
        assertEquals(RestBudget.Lane.HIGH, RestBudget.laneOf(F + "/fapi/v1/klines?symbol=X&limit=2"));
        assertEquals(RestBudget.Lane.HIGH, RestBudget.laneOf(F + "/fapi/v1/ticker/price"));
        assertEquals(RestBudget.Lane.LOW, RestBudget.laneOf(F + "/fapi/v1/premiumIndex"));
        assertEquals(RestBudget.Lane.LOW, RestBudget.laneOf(F + "/futures/data/takerlongshortRatio?symbol=X"));
    }

    @Test
    public void disabledOrNonFapiPassesThrough() {
        RestBudget.reset(null);
        assertTrue(RestBudget.beforeRequest(F + "/fapi/v1/ticker/24hr"));
        RestBudget.reset(b);
        assertTrue(RestBudget.beforeRequest("https://api.telegram.org/botX/sendMessage"));
        assertEquals(0, b.usedNow());
    }

    @Test
    public void capAndLowReserve() {
        for (int i = 0; i < 200; i++) assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        assertTrue("LOW dung o cap-100", b.tryAcquire(1, RestBudget.Lane.LOW) > 0);
        for (int i = 0; i < 100; i++) assertEquals(0, b.tryAcquire(1, RestBudget.Lane.HIGH));
        assertTrue("HIGH dung o cap", b.tryAcquire(1, RestBudget.Lane.HIGH) > 0);
        assertEquals(300, b.usedNow());
        assertFalse("het han cho => false", b.acquire(1, RestBudget.Lane.HIGH, 30));
        assertEquals(1, b.denied.get());
        off.addAndGet(60_001L);   // cua so truot het han
        assertEquals(0, b.usedNow());
        assertEquals(0, b.tryAcquire(300, RestBudget.Lane.HIGH));
    }

    @Test
    public void capClampedTo300() {
        RestBudget big = new RestBudget(5000, 1600, 2000, System::currentTimeMillis);
        assertEquals(300, big.cap);
    }

    @Test
    public void headerSoftBlocksLowHardBlocksAll() {
        b.observe(200, "1700", null);
        assertTrue(b.tryAcquire(1, RestBudget.Lane.LOW) > 0);
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.HIGH));
        b.observe(200, "2100", null);
        assertTrue(b.tryAcquire(1, RestBudget.Lane.HIGH) > 0);
        off.addAndGet(61_000L);   // sang phut moi => header cu het hieu luc
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        assertTrue(b.statsLine().contains("hdr_max=2100"));
    }

    @Test
    public void http429SetsGlobalCooldownFromRetryAfter() {
        long before = System.currentTimeMillis();
        b.observe(429, "2400", "7");
        assertTrue(BinanceRestGuard.isBanned());
        long until = BinanceRestGuard.BANNED_UNTIL_MS.get();
        assertTrue(until >= before + 7_000L);
        assertTrue(b.tryAcquire(1, RestBudget.Lane.HIGH) > 0);   // dang cooldown => khong cap
        assertEquals(1, b.http429.get());
        b.observe(418, null, null);
        assertTrue(BinanceRestGuard.BANNED_UNTIL_MS.get() >= before + 120_000L);
        assertTrue(b.statsLine().contains("http418=1"));
    }
}
