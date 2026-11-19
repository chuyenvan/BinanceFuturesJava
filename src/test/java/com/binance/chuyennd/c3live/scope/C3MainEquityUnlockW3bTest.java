package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.risk.C3MainEquity;
import com.binance.chuyennd.c3live.risk.C3MainEquityRefE65;
import com.binance.chuyennd.c3live.risk.C3MainEquityTestAccess;
import com.binance.chuyennd.ops.KillSwitchEngineTestAccess;
import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.lang.management.ManagementFactory;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Random;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/**
 * [W3B muc 2] C3MainEquity: REST (positions/account/income) + onApiResult NGOAI khoa. (1) single-flight: N thread => 1 REST
 * (bang so lan cua ban cu); (2) gateway cham khong chan capital()/status() cua thread khac; (3) so hoc + so lan goi API + chuoi
 * onApiResult trung ban e65c010e (C3MainEquityRefE65) tren kich ban ngau nhien co dinh; (4) stress khong deadlock voi KS ke ca
 * khi tat KILLSW_EQ_POLL_UNLOCKED.
 */
public class C3MainEquityUnlockW3bTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @After
    public void restore() {
        C3MainEquityTestAccess.setRestUnlocked(true);
        KillSwitchEngineTestAccess.setEqPollUnlocked(true);
    }

    /** Gateway cham co dieu khien: thread ten "W3B-SLOW*" cho latch trong positions/account/income. */
    static final class Slow extends MockExchangeGateway {
        final AtomicBoolean slowPos = new AtomicBoolean();
        final AtomicBoolean slowAcc = new AtomicBoolean();
        final AtomicBoolean slowInc = new AtomicBoolean();
        final CountDownLatch entered = new CountDownLatch(1);
        volatile CountDownLatch release = new CountDownLatch(1);

        private void maybeBlock(AtomicBoolean f) {
            if (f.get() && Thread.currentThread().getName().startsWith("W3B-SLOW")) {
                entered.countDown();
                try {
                    release.await(10, TimeUnit.SECONDS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        }

        @Override
        public List<PositionInfo> positions() {
            maybeBlock(slowPos);
            return super.positions();
        }

        @Override
        public AccountSnapshot account() {
            maybeBlock(slowAcc);
            return super.account();
        }

        @Override
        public List<IncomeRecord> income(String t, long s, int l) {
            maybeBlock(slowInc);
            return super.income(t, s, l);
        }
    }

    static final String S = C3LiveFixtures.sym(0);
    static final String S2 = C3LiveFixtures.sym(1);

    private C3MainEquity eq60(MainAccountRig r, String name, List<String> api) {
        C3LiveOrderExecutor.ApiObserver o = (a, ok) -> api.add(a + ":" + ok);
        return new C3MainEquity(r.sgw, r.book, r.scope, 10_000d, new File(r.root, "run/" + name + ".json"), "mock", 60_000L,
                r.now::get, o, x -> { });
    }

    private static void waitParked(List<Thread> ts, long maxMs) throws InterruptedException {
        long end = System.currentTimeMillis() + maxMs;
        while (System.currentTimeMillis() < end) {
            boolean all = true;
            for (Thread t : ts) {
                Thread.State s = t.getState();
                if (s != Thread.State.BLOCKED && s != Thread.State.WAITING && s != Thread.State.TIMED_WAITING
                        && s != Thread.State.TERMINATED) all = false;
            }
            if (all) return;
            Thread.sleep(5L);
        }
    }

    /** N thread capital() dong thoi khi cache het han => dung 1 positions + 1 account, ca 2 mode (so lan goi khong doi). */
    private int[] singleFlight(boolean unlocked) throws Exception {
        C3MainEquityTestAccess.setRestUnlocked(unlocked);
        Slow m = new Slow();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), m, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        List<String> api = new CopyOnWriteArrayList<>();
        C3MainEquity e = eq60(r, "eqsf", api);
        int p0 = m.calls("positions");
        int a0 = m.calls("account");
        m.slowPos.set(true);
        List<Thread> ts = new ArrayList<>();
        List<Double> out = new CopyOnWriteArrayList<>();
        for (int i = 0; i < 8; i++) {
            Thread t = new Thread(() -> out.add(e.capital()), "W3B-SLOW-" + i);
            t.setDaemon(true);
            ts.add(t);
        }
        for (Thread t : ts) t.start();
        assertTrue(m.entered.await(5, TimeUnit.SECONDS));
        waitParked(ts, 2_000L);
        m.release.countDown();
        for (Thread t : ts) t.join(5_000L);
        for (Thread t : ts) assertFalse(t.isAlive());
        assertEquals(8, out.size());
        for (Double d : out) assertEquals(out.get(0), d);
        assertNotNull(out.get(0));
        return new int[]{m.calls("positions") - p0, m.calls("account") - a0, api.size()};
    }

    @Test
    public void singleFlight_nThread_motRest_bangBanCu() throws Exception {
        int[] neu = singleFlight(true);
        int[] old = singleFlight(false);
        assertEquals("positions moi", 1, neu[0]);
        assertEquals("account moi", 1, neu[1]);
        assertArrayEquals("so lan goi API + so onApiResult = ban cu", old, neu);
    }

    /** income cham (pollFunding) giu ~1,5 s: capital() (cache con han) + status() cua thread khac khong bi chan > 300 ms. */
    private long blockedMs(boolean unlocked, String what) throws Exception {
        C3MainEquityTestAccess.setRestUnlocked(unlocked);
        Slow m = new Slow();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), m, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        C3MainEquity e = eq60(r, "eqbl", new CopyOnWriteArrayList<>());
        assertNotNull(e.capital());   // nap cache
        long t0 = r.now.get();
        Thread a;
        if ("income".equals(what)) {
            m.slowInc.set(true);
            a = new Thread(() -> e.pollFunding(t0 + 1_000L), "W3B-SLOW-A");
        } else {
            m.slowPos.set(true);
            r.now.addAndGet(61_000L);   // het han => A REST positions
            a = new Thread(e::c3Equity, "W3B-SLOW-A");
        }
        a.setDaemon(true);
        a.start();
        assertTrue(m.entered.await(5, TimeUnit.SECONDS));
        Thread releaser = new Thread(() -> {
            try {
                Thread.sleep(1_500L);
            } catch (InterruptedException ignore) {
                Thread.currentThread().interrupt();
            }
            m.release.countDown();
        });
        releaser.setDaemon(true);
        releaser.start();
        long s = System.nanoTime();
        if ("income".equals(what)) assertNotNull(e.capital());
        else e.status();
        long ms = (System.nanoTime() - s) / 1_000_000L;
        a.join(5_000L);
        assertFalse(a.isAlive());
        return ms;
    }

    @Test
    public void gatewayCham_khongChanThreadKhac() throws Exception {
        assertTrue("capital() khi income cham", blockedMs(true, "income") < 300L);
        assertTrue("status() khi positions cham", blockedMs(true, "positions") < 300L);
        assertTrue("doi chung ban cu: capital() bi chan", blockedMs(false, "income") >= 1_000L);
        assertTrue("doi chung ban cu: status() bi chan", blockedMs(false, "positions") >= 1_000L);
    }

    /** So hoc + so lan goi API + chuoi onApiResult + alert trung ban cu tren 400 buoc ngau nhien co dinh (1 thread). */
    @Test
    public void soHoc_trungBanCu_kichBanGhiSan() throws Exception {
        MockExchangeGateway m = new MockExchangeGateway();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), m, 10_000d);
        r.setAccount("1000000", "900000");
        List<String> apiN = new ArrayList<>();
        List<String> apiR = new ArrayList<>();
        List<String> alN = new ArrayList<>();
        List<String> alR = new ArrayList<>();
        C3MainEquity n = new C3MainEquity(r.sgw, r.book, r.scope, 10_000d, new File(r.root, "run/eqN.json"), "mock", 60_000L,
                r.now::get, (a, ok) -> apiN.add(a + ":" + ok), alN::add);
        C3MainEquityRefE65 o = new C3MainEquityRefE65(r.sgw, r.book, r.scope, 10_000d, new File(r.root, "run/eqR.json"), "mock",
                60_000L, r.now::get, (a, ok) -> apiR.add(a + ":" + ok), alR::add);
        Random rnd = new Random(7);
        int opened = 0;
        int nCalls = 0;
        String[] methods = {"positions", "account", "income"};
        for (int step = 0; step < 400; step++) {
            long t = r.now.addAndGet(1_000L + rnd.nextInt(90_000));
            m.now = t;
            int ev = rnd.nextInt(10);
            if (ev == 0 && opened < 2) {
                C3MainEquityKillSwitchTest.c3Position(r, opened == 0 ? S : S2, "100", "1.0");
                opened++;
            } else if (ev <= 3) {
                String sym = rnd.nextBoolean() ? S : S2;
                String px = new BigDecimal(0.5 + rnd.nextDouble()).setScale(4, BigDecimal.ROUND_HALF_UP).toPlainString();
                m.setPrice(sym, new BigDecimal(px));
            } else if (ev == 4) {
                m.incomes.add(new IncomeRecord(rnd.nextBoolean() ? S : S2, "FUNDING_FEE",
                        new BigDecimal(rnd.nextInt(200) - 100).movePointLeft(2), "USDT", t - rnd.nextInt(600_000), "i" + step));
            } else if (ev == 5 && opened > 0) {
                r.book.addFillCosts(S, 0.01d * rnd.nextInt(10), rnd.nextInt(50) - 25, t);
            } else if (ev == 6) {
                r.setAccount("1000000", rnd.nextInt(4) == 0 ? "1" : "900000");
            } else if (ev == 7) {
                String mt = methods[rnd.nextInt(3)];
                m.failNext(mt, new GatewayException(ErrorKind.RATE_LIMIT, "gia lap " + step, true));
                m.failNext(mt, new GatewayException(ErrorKind.RATE_LIMIT, "gia lap " + step, true));
            }
            int op = rnd.nextInt(3);
            int[] c0 = {m.calls("positions"), m.calls("account"), m.calls("income")};
            Object vn = op == 0 ? n.c3Equity() : op == 1 ? n.capital() : (Object) n.pollFunding(t);
            int[] c1 = {m.calls("positions"), m.calls("account"), m.calls("income")};
            Object vo = op == 0 ? o.c3Equity() : op == 1 ? o.capital() : (Object) o.pollFunding(t);
            int[] c2 = {m.calls("positions"), m.calls("account"), m.calls("income")};
            String at = "buoc " + step + " op " + op;
            assertEquals(at, vo, vn);
            for (int k = 0; k < 3; k++) assertEquals(at + " API " + methods[k], c2[k] - c1[k], c1[k] - c0[k]);
            nCalls += c1[0] - c0[0] + c1[1] - c0[1] + c1[2] - c0[2];
            assertEquals(at, apiR, apiN);
            assertEquals(at, alR, alN);
            assertTrue(at, Objects.equals(o.status(), n.status()));
            assertEquals(at, o.fundingCum(), n.fundingCum(), 0d);
        }
        assertTrue("kich ban phai co goi API: " + nCalls, nCalls > 50);
        assertTrue("kich ban phai co loi API", apiN.toString().contains(":false"));
        assertTrue("kich ban phai co funding", n.fundingCum() != 0d);
    }

    /** Stress 1,5 s: KS (ca 2 gia tri co KS) + c3Equity/capital/pollFunding/onTickStart dong thoi => khong deadlock, xong het. */
    @Test
    public void stress_khongDeadlock_voiKs_keCaTatCoKs() throws Exception {
        for (boolean ksUnlocked : new boolean[]{false, true}) {
            KillSwitchEngineTestAccess.setEqPollUnlocked(ksUnlocked);
            C3MainEquityTestAccess.setRestUnlocked(true);
            MainAccountRig r = new MainAccountRig(tmp.newFolder(), new MockExchangeGateway(), 2_000d);
            r.setAccount("1000000", "600000");
            C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
            final long end = System.currentTimeMillis() + 1_500L;
            AtomicInteger ops = new AtomicInteger();
            List<Thread> ts = new ArrayList<>();
            Runnable[] jobs = {
                    () -> r.ks.periodic(r.now.get()),
                    () -> r.eq.c3Equity(),
                    () -> r.eq.capital(),
                    () -> r.eq.pollFunding(r.now.addAndGet(700_000L)),
                    () -> r.ks.onTickStart(r.now.get()),
                    () -> r.ks.onApiResult(r.now.get(), "x", true)};
            for (int i = 0; i < jobs.length; i++) {
                final Runnable j = jobs[i];
                Thread t = new Thread(() -> {
                    while (System.currentTimeMillis() < end) {
                        j.run();
                        ops.incrementAndGet();
                    }
                }, "W3B-STRESS-" + i);
                t.setDaemon(true);
                ts.add(t);
            }
            for (Thread t : ts) t.start();
            for (Thread t : ts) t.join(10_000L);
            long[] dl = ManagementFactory.getThreadMXBean().findMonitorDeadlockedThreads();
            List<String> mine = new ArrayList<>();
            if (dl != null) for (long id : dl) for (Thread t : ts) if (t.getId() == id) mine.add(t.getName());
            assertTrue("deadlock ksUnlocked=" + ksUnlocked + ": " + mine, mine.isEmpty());
            for (Thread t : ts) assertFalse(t.getName() + " ksUnlocked=" + ksUnlocked, t.isAlive());
            assertTrue(ops.get() > 100);
        }
    }

    @Test
    public void envParsing() {
        assertTrue(C3MainEquityTestAccess.parse(null));
        assertTrue(C3MainEquityTestAccess.parse("1"));
        assertTrue(C3MainEquityTestAccess.parse(" true "));
        assertFalse(C3MainEquityTestAccess.parse("0"));
        assertFalse(C3MainEquityTestAccess.parse("False"));
        // [W3B v2] A1 e7: cam to hop tat CA 2 co (deadlock 19/11) => ep REST ngoai khoa
        assertTrue(C3MainEquityTestAccess.effective(null, null));
        assertFalse(C3MainEquityTestAccess.effective("false", null));
        assertTrue(C3MainEquityTestAccess.effective(null, "false"));
        assertTrue("to hop cam", C3MainEquityTestAccess.effective("false", "0"));
        assertTrue("to hop cam", C3MainEquityTestAccess.effective("0", "FALSE"));
    }
}
