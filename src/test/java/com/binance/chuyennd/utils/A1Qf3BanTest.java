package com.binance.chuyennd.utils;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.Assert.*;

/** A1 re-audit QF3 (chi a1_wt3, KHONG commit): ban ben qua restart + Q11. */
public class A1Qf3BanTest {
    Path dir, f;

    @Before
    public void setUp() throws Exception {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        dir = Files.createTempDirectory("a1qf3");
        f = dir.resolve("rest_ban_until.ms");
    }

    @After
    public void tearDown() {
        BinanceRestGuard.disablePersistence();
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        RestBudget.reset(null);
    }

    static void newJvm() {   // mo phong JVM moi: RAM sach
        BinanceRestGuard.disablePersistence();
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    @Test
    public void b1_roundTrip418ThenRestart() {
        BinanceRestGuard.enablePersistence(f);
        RestBudget b = RestBudget.create(300, 1600, 2000, 150, System::currentTimeMillis);
        b.observe(418, null, "120", null);
        assertTrue(Files.exists(f));
        long until = BinanceRestGuard.BANNED_UNTIL_MS.get();
        newJvm();
        assertFalse(BinanceRestGuard.isBanned());
        BinanceRestGuard.enablePersistence(f);
        assertTrue("JVM moi phai biet dang ban", BinanceRestGuard.isBanned());
        assertEquals(until, BinanceRestGuard.BANNED_UNTIL_MS.get());
    }

    @Test
    public void b2_corruptOrMissingFileFailsOpen() throws Exception {
        Files.write(f, "abc".getBytes(StandardCharsets.US_ASCII));
        assertEquals(0L, BinanceRestGuard.enablePersistence(f));
        assertFalse(BinanceRestGuard.isBanned());
        newJvm();
        Files.delete(f);
        assertEquals(0L, BinanceRestGuard.enablePersistence(f));
        Files.write(f, new byte[0]);
        newJvm();
        assertEquals(0L, BinanceRestGuard.enablePersistence(f));
        System.out.println("A1-B2 file hong/mat/rong => fail-open (khong ban) — ghi nhan");
    }

    @Test
    public void b3_shorterBanNeverShrinksFile() throws Exception {
        BinanceRestGuard.enablePersistence(f);
        long now = System.currentTimeMillis();
        BinanceRestGuard.cooldownUntil(now + 3 * 86_400_000L, "test 3 ngay");
        long big = BinanceRestGuard.readPersisted(f);
        BinanceRestGuard.cooldownUntil(now + 60_000L, "test ngan");
        assertEquals("ban ngan sau khong duoc rut ngan moc", big, BinanceRestGuard.readPersisted(f));
        newJvm();
        BinanceRestGuard.enablePersistence(f);
        assertTrue(BinanceRestGuard.BANNED_UNTIL_MS.get() >= now + 3 * 86_400_000L);
    }

    @Test
    public void b4_q11NoCallDuringBan() {
        RestBudget b = RestBudget.create(300, 1600, 2000, 150, System::currentTimeMillis);
        RestBudget.reset(b);
        BinanceRestGuard.BANNED_UNTIL_MS.set(System.currentTimeMillis() + 60_000L);
        long t = System.currentTimeMillis();
        assertFalse(RestBudget.beforeRequest("https://fapi.binance.com/fapi/v1/klines?symbol=X&interval=1m&limit=3"));
        assertFalse(RestBudget.beforeRequest("https://fapi.binance.com/fapi/v1/ticker/price"));
        long waited = System.currentTimeMillis() - t;
        assertEquals(0, b.sentBanned.get());
        assertTrue(b.statsLine().contains("sent_banned_total=0"));
        assertTrue("PRICE cho toi da 5 s: " + waited, waited <= 5_700L);
    }
}
