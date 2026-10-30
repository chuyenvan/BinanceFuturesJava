package com.binance.chuyennd.utils;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** [INGEST-QF2] Ngân sách REST: bảng weight, lane PRICE/KLINE/LOW/FDATA, dành riêng giá, header theo giờ sàn, 429/418. */
public class RestBudgetTest {
    final AtomicLong off = new AtomicLong();
    RestBudget b;
    static final String F = "https://fapi.binance.com";

    @Before
    public void setUp() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        b = new RestBudget(300, 1600, 2000, 150, () -> System.currentTimeMillis() + off.get());
    }

    @After
    public void tearDown() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        RestBudget.reset(null);
    }

    @Test
    public void weightTable() {
        assertEquals(1, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=3"));
        assertEquals(1, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=99"));
        assertEquals(2, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=100"));
        assertEquals(5, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=BTCUSDT&interval=1m"));   // mac dinh limit 500
        assertEquals(10, RestBudget.weightOf(F + "/fapi/v1/klines?symbol=X&interval=1m&limit=1500"));
        assertEquals(2, RestBudget.weightOf(F + "/fapi/v1/ticker/price"));
        assertEquals(40, RestBudget.weightOf(F + "/fapi/v1/ticker/24hr"));
        assertEquals(10, RestBudget.weightOf(F + "/fapi/v1/premiumIndex"));
        assertEquals(5, RestBudget.weightOf(F + "/fapi/v9/unknown"));
    }

    @Test
    public void lanes() {
        assertEquals(RestBudget.Lane.KLINE, RestBudget.laneOf(F + "/fapi/v1/klines?symbol=X&interval=1m&limit=2"));
        assertEquals("repair limit 500 => LOW", RestBudget.Lane.LOW, RestBudget.laneOf(F + "/fapi/v1/klines?symbol=X&interval=1m&limit=500&startTime=1"));
        assertEquals(RestBudget.Lane.PRICE, RestBudget.laneOf(F + "/fapi/v1/ticker/price"));
        assertEquals(RestBudget.Lane.LOW, RestBudget.laneOf(F + "/fapi/v1/premiumIndex"));
        assertEquals(RestBudget.Lane.FDATA, RestBudget.laneOf(F + "/futures/data/takerlongshortRatio?symbol=X"));
        assertEquals(0L, RestBudget.maxWaitMs(RestBudget.Lane.KLINE));
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
    public void priceReserveNeverTakenByKlineOrLow() {
        for (int i = 0; i < 40; i++) assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        assertTrue("LOW dung o 40", b.tryAcquire(1, RestBudget.Lane.LOW) > 0);
        assertEquals("LOW day khong an cua KLINE", 200, b.available(RestBudget.Lane.KLINE));
        for (int i = 0; i < 200; i++) assertEquals(0, b.tryAcquire(1, RestBudget.Lane.KLINE));
        assertTrue("KLINE dung o 200", b.tryAcquire(1, RestBudget.Lane.KLINE) > 0);
        assertEquals(0, b.available(RestBudget.Lane.KLINE));
        assertFalse("KLINE khong cho", b.acquire(1, RestBudget.Lane.KLINE, RestBudget.maxWaitMs(RestBudget.Lane.KLINE)));
        for (int i = 0; i < 30; i++) assertEquals("gia luon con 60 weight rieng", 0, b.tryAcquire(2, RestBudget.Lane.PRICE));
        assertTrue(b.tryAcquire(1, RestBudget.Lane.PRICE) > 0);
        assertEquals(300, b.usedNow());
        off.addAndGet(60_001L);
        assertEquals(0, b.usedNow());
    }

    @Test
    public void fdataSeparateBucket() {
        for (int i = 0; i < 150; i++) assertEquals(0, b.tryAcquire(1, RestBudget.Lane.FDATA));
        assertTrue(b.tryAcquire(1, RestBudget.Lane.FDATA) > 0);
        assertEquals("futures/data khong an weight IP", 0, b.usedNow());
        assertEquals(40, b.available(RestBudget.Lane.LOW));
        assertEquals(150, b.fdataNow());
    }

    @Test
    public void capClamped() {
        assertEquals(300, new RestBudget(5000, 1600, 2000, 150, System::currentTimeMillis).cap);
        assertEquals(190, new RestBudget(5000, 1600, 2000, 999, System::currentTimeMillis).fdataCap);
    }

    static String httpDate(long ms) {
        return DateTimeFormatter.RFC_1123_DATE_TIME.format(ZonedDateTime.ofInstant(java.time.Instant.ofEpochMilli(ms), ZoneOffset.UTC));
    }

    /** Đặt đồng hồ test vào giữa phút (tránh test chạy sát ranh phút). */
    long midMinute() {
        off.set(30_000L - (System.currentTimeMillis() % 60_000L));
        return System.currentTimeMillis() + off.get();
    }

    @Test
    public void headerByServerMinute() {
        long now = midMinute();
        b.observe(200, "1700", null, httpDate(now));
        assertTrue(b.tryAcquire(1, RestBudget.Lane.LOW) > 0);
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.KLINE));
        assertEquals(0, b.tryAcquire(2, RestBudget.Lane.PRICE));
        b.observe(200, "2100", null, httpDate(now));
        assertTrue(b.tryAcquire(1, RestBudget.Lane.KLINE) > 0);
        assertEquals("gia chi dung khi >=2300", 0, b.tryAcquire(2, RestBudget.Lane.PRICE));
        b.observe(200, "2350", null, httpDate(now));
        assertTrue(b.tryAcquire(2, RestBudget.Lane.PRICE) > 0);
        assertEquals("FDATA khong theo header IP", 0, b.tryAcquire(1, RestBudget.Lane.FDATA));
        off.addAndGet(61_000L);
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.LOW));
        assertTrue(b.statsLine().contains("hdr_max=2350"));
    }

    @Test
    public void serverClockAheadMovesMinute() {
        long now = midMinute();
        // dong ho san nhanh 40 s (local giua phut L, san da o phut L+1): header gan theo phut SAN va van chan dung phut do
        b.observe(200, "2100", null, httpDate(now + 40_000L));
        assertTrue("header phut san hien tai => chan KLINE", b.tryAcquire(1, RestBudget.Lane.KLINE) > 0);
        assertTrue(b.statsLine().matches(".*skew_ms=(39|40)[0-9]{3} .*"));
        off.addAndGet(55_000L);   // local L+85 s (phut L+1) nhung san L+125 s = phut L+2 => header cu het hieu luc
        assertEquals(0, b.tryAcquire(1, RestBudget.Lane.KLINE));
        assertTrue(RestBudget.parseHttpDate("garbage") < 0);
    }

    @Test
    public void http429SetsGlobalCooldownFromRetryAfter() {
        long before = System.currentTimeMillis();
        b.observe(429, "2400", "7", null);
        assertTrue(BinanceRestGuard.isBanned());
        assertTrue(BinanceRestGuard.BANNED_UNTIL_MS.get() >= before + 7_000L);
        assertTrue(b.tryAcquire(2, RestBudget.Lane.PRICE) > 0);
        assertTrue(b.tryAcquire(1, RestBudget.Lane.FDATA) > 0);
        assertEquals(0, b.available(RestBudget.Lane.KLINE));
        b.observe(418, null, null, null);
        assertTrue(BinanceRestGuard.BANNED_UNTIL_MS.get() >= before + 120_000L);
        assertTrue(b.statsLine().contains("http418=1"));
    }
}
