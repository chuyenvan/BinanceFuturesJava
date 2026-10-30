package com.binance.chuyennd.utils;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

/** [INGEST-QF3] Ban bền qua restart JVM (MAJ-A, ADD2/Q11) + leo thang supervisor (MIN-C). */
public class Qf3UtilsTest {
    Path dir;

    @Before
    public void setUp() throws Exception {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        dir = Files.createTempDirectory("qf3ban");
    }

    @After
    public void tearDown() throws Exception {
        BinanceRestGuard.disablePersistence();
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        LoopSupervisor.setAlertSink(null);
    }

    @Test
    public void banPersistsAcrossJvmRestartAndBlocksAllFapiLanes() throws Exception {
        Path f = dir.resolve("rest_ban_until.ms");
        BinanceRestGuard.enablePersistence(f);
        long now = System.currentTimeMillis();
        BinanceRestGuard.cooldownUntil(now + 120_000L, "HTTP 418 Retry-After=120");
        long saved = Long.parseLong(new String(Files.readAllBytes(f)).trim());
        assertTrue("moc ban duoc ghi file", saved >= now + 120_000L);
        // "JVM moi": RAM trang, nap lai tu file TRUOC moi call
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        BinanceRestGuard.disablePersistence();
        long loaded = BinanceRestGuard.enablePersistence(f);
        assertEquals(saved, loaded);
        assertTrue(BinanceRestGuard.isBanned());
        RestBudget b = RestBudget.create(300, 1600, 2000, 150, System::currentTimeMillis);
        for (RestBudget.Lane l : RestBudget.Lane.values()) {
            assertTrue("lane " + l + " phai bi chan toi moc ban", b.tryAcquire(1, l) > 0);
            assertEquals(0, b.available(l));
        }
        assertEquals("khong call fapi nao trong luc ban (Q11)", 0, b.calls.get() + b.fcalls.get());
    }

    @Test
    public void reportBanBodyAlsoPersisted() throws Exception {
        Path f = dir.resolve("b2.ms");
        BinanceRestGuard.enablePersistence(f);
        long until = System.currentTimeMillis() + 300_000L;
        BinanceRestGuard.reportBan("{\"code\":-1003,\"msg\":\"Way too many requests; IP banned until " + until + ".\"}");
        assertTrue(Long.parseLong(new String(Files.readAllBytes(f)).trim()) >= until);
    }

    @Test
    public void expiredBanFileIgnoredAndMissingFileOk() {
        Path f = dir.resolve("none.ms");
        assertEquals(0L, BinanceRestGuard.enablePersistence(f));
        assertFalse(BinanceRestGuard.isBanned());
    }

    @Test
    public void supervisorEscalatesAfter10DeathsPerHourWithAntiSpam() {
        List<String> sent = new ArrayList<>();
        LoopSupervisor.setAlertSink(sent::add);
        long t = 5_000_000_000L;
        String name = "qf3-esc-" + System.nanoTime();
        for (int i = 0; i < 10; i++) assertFalse(LoopSupervisor.recordDeath(name, "Error", t + i * 1000L));
        assertTrue("lan thu 11 trong 1h => leo thang", LoopSupervisor.recordDeath(name, "Error", t + 11_000L));
        assertEquals(1, sent.size());
        assertTrue(sent.get(0).startsWith("KHAN"));
        for (int i = 0; i < 20; i++) assertFalse("chong spam 30'", LoopSupervisor.recordDeath(name, "Error", t + 12_000L + i * 1000L));
        assertEquals(1, sent.size());
        assertTrue("sau 30' van con chet nhieu => bao lai", LoopSupervisor.recordDeath(name, "Error", t + 31 * 60_000L));
        assertEquals(2, sent.size());
        String other = name + "-b";
        assertFalse("dem theo tung loop", LoopSupervisor.recordDeath(other, "Error", t));
    }
}
