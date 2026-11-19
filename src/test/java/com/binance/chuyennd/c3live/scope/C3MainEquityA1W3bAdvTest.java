package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.AccountSnapshot;
import com.binance.chuyennd.c3live.api.IncomeRecord;
import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
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
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

/** [W3B v2] Test doi khang A1_W3B muc 2 (a1_w3b/A1W3bEqAdvTest) dua vao bo chinh, y nguyen. */
public class C3MainEquityA1W3bAdvTest {
    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final String S = C3LiveFixtures.sym(0);

    @After
    public void restore() {
        C3MainEquityTestAccess.setRestUnlocked(true);
        KillSwitchEngineTestAccess.setEqPollUnlocked(true);
    }

    /** gateway: positions/account cham theo co, co the nem 1 lan, co the tien dong ho trong REST. */
    static final class G extends MockExchangeGateway {
        final AtomicBoolean slowPos = new AtomicBoolean();
        final AtomicBoolean slowAcc = new AtomicBoolean();
        final AtomicReference<Throwable> throwPosOnce = new AtomicReference<>();
        volatile AtomicLong clock;
        volatile long advanceInRest = 0L;
        final CountDownLatch entered = new CountDownLatch(1);
        final CountDownLatch release = new CountDownLatch(1);

        private void block(AtomicBoolean f) {
            if (f.get() && Thread.currentThread().getName().startsWith("A1SLOW")) {
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
            block(slowPos);
            if (clock != null && advanceInRest > 0) clock.addAndGet(advanceInRest);
            Throwable t = throwPosOnce.getAndSet(null);
            if (t instanceof RuntimeException) throw (RuntimeException) t;
            if (t instanceof Error) throw (Error) t;
            return super.positions();
        }

        @Override
        public AccountSnapshot account() {
            block(slowAcc);
            return super.account();
        }
    }

    private C3MainEquity eq60(MainAccountRig r, String name, List<String> api) {
        return new C3MainEquity(r.sgw, r.book, r.scope, 10_000d, new File(r.root, "run/" + name + ".json"), "mock", 60_000L,
                r.now::get, (a, ok) -> api.add(a + ":" + ok), x -> { });
    }

    /** E1: dong ho tien 14 s TRONG REST (burst sleep): gia tri + thoi diem lam moi cache = ban e65c010e. */
    @Test
    public void e1_clockAdvanceInRest_sameAsRef() throws Exception {
        G g1 = new G();
        G g2 = new G();
        MainAccountRig r1 = new MainAccountRig(tmp.newFolder(), g1, 10_000d);
        MainAccountRig r2 = new MainAccountRig(tmp.newFolder(), g2, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r1, S, "100", "1.0");
        C3MainEquityKillSwitchTest.c3Position(r2, S, "100", "1.0");
        g1.clock = r1.now;
        g2.clock = r2.now;
        g1.advanceInRest = 14_000L;
        g2.advanceInRest = 14_000L;
        C3MainEquity n = eq60(r1, "n", new ArrayList<>());
        C3MainEquityRefE65 o = new C3MainEquityRefE65(r2.sgw, r2.book, r2.scope, 10_000d, new File(r2.root, "run/o.json"),
                "mock", 60_000L, r2.now::get, (a, ok) -> { }, x -> { });
        for (int i = 0; i < 40; i++) {
            BigDecimal px = new BigDecimal(1 + (i % 7) * 0.01).setScale(4, BigDecimal.ROUND_HALF_UP);
            g1.setPrice(S, px);
            g2.setPrice(S, px);
            Double vn = i % 2 == 0 ? n.c3Equity() : n.capital();
            Double vo = i % 2 == 0 ? o.c3Equity() : o.capital();
            assertEquals("buoc " + i, vo, vn);
            assertEquals("clock buoc " + i, r2.now.get(), r1.now.get());
            assertEquals("positions calls " + i, g2.calls("positions"), g1.calls("positions"));
            r1.now.addAndGet(9_000L);
            r2.now.addAndGet(9_000L);
        }
    }

    /** E2: REST cua thread A loi trong khi B cho => B tu REST, co gia tri; chuoi onApiResult false roi true. */
    @Test
    public void e2_restFailWhileWaiter_waiterRetries() throws Exception {
        G g = new G();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), g, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        List<String> api = new CopyOnWriteArrayList<>();
        C3MainEquity e = eq60(r, "e2", api);
        g.slowPos.set(true);
        g.throwPosOnce.set(new RuntimeException("gia lap"));
        AtomicReference<Double> ra = new AtomicReference<>(1d);
        AtomicReference<Double> rb = new AtomicReference<>();
        Thread a = new Thread(() -> ra.set(e.c3Equity()), "A1SLOW-A");
        a.start();
        assertTrue(g.entered.await(5, TimeUnit.SECONDS));
        Thread b = new Thread(() -> rb.set(e.c3Equity()), "A1-B");
        b.start();
        Thread.sleep(200L);
        assertTrue("B phai cho posFlight", b.isAlive());
        g.release.countDown();
        a.join(5_000L);
        b.join(5_000L);
        assertFalse(a.isAlive());
        assertFalse(b.isAlive());
        assertNull(ra.get());
        assertNotNull(rb.get());
        assertEquals("[positions:false, positions:true]", api.toString());
    }

    /** E3: Error (khong phai RuntimeException) trong REST => khoa duoc tha, lan sau van chay. */
    @Test
    public void e3_errorInRest_releasesLocks() throws Exception {
        G g = new G();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), g, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        C3MainEquity e = eq60(r, "e3", new ArrayList<>());
        g.throwPosOnce.set(new AssertionError("gia lap"));
        try {
            e.c3Equity();
            fail("phai nem");
        } catch (AssertionError expected) {
            // ok
        }
        AtomicReference<Double> v = new AtomicReference<>();
        Thread t = new Thread(() -> v.set(e.c3Equity()), "A1-E3");
        t.start();
        t.join(2_000L);
        assertFalse("bi treo sau Error", t.isAlive());
        assertNotNull(v.get());
    }

    /** E4: positions cham (giu posFlight) => KS onTickStart/onApiResult/requiredAction + status() khong bi chan. */
    @Test
    public void e4_slowRest_doesNotBlockKsOrStatus() throws Exception {
        G g = new G();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), g, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        C3MainEquity e = eq60(r, "e4", new ArrayList<>());
        r.ks.attachEquitySource(e);
        g.slowPos.set(true);
        Thread a = new Thread(e::c3Equity, "A1SLOW-OPS");
        a.setDaemon(true);
        a.start();
        assertTrue(g.entered.await(5, TimeUnit.SECONDS));
        Thread ksP = new Thread(() -> r.ks.periodic(r.now.get()), "A1-KS-PERIODIC");
        ksP.setDaemon(true);
        ksP.start();
        Thread.sleep(100L);
        long s = System.nanoTime();
        r.ks.onTickStart(r.now.get());
        r.ks.onApiResult(r.now.get(), "x", true);
        r.ks.requiredAction();
        e.status();
        long ms = (System.nanoTime() - s) / 1_000_000L;
        g.release.countDown();
        a.join(5_000L);
        ksP.join(5_000L);
        assertFalse(ksP.isAlive());
        assertTrue("KS/status bi chan " + ms + " ms", ms < 300L);
    }

    /** E5: available() (account) cham => c3Equity() voi cache con han tra ngay. */
    @Test
    public void e5_slowAccount_doesNotBlockCachedEquity() throws Exception {
        G g = new G();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), g, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        C3MainEquity e = eq60(r, "e5", new ArrayList<>());
        assertNotNull(e.c3Equity());
        r.now.addAndGet(1_000L);
        g.slowAcc.set(true);
        Thread a = new Thread(e::capital, "A1SLOW-CAP");
        a.setDaemon(true);
        r.now.addAndGet(0L);
        // account cache chua co => capital() REST account (cham)
        a.start();
        assertTrue(g.entered.await(5, TimeUnit.SECONDS));
        long s = System.nanoTime();
        assertNotNull(e.c3Equity());
        long ms = (System.nanoTime() - s) / 1_000_000L;
        g.release.countDown();
        a.join(5_000L);
        assertTrue("c3Equity bi chan " + ms, ms < 300L);
    }

    /** E6: funding duoc cong trong luc REST positions dang bay => ket qua cuoi (cache) = tinh lai tu dau. */
    @Test
    public void e6_fundingDuringRest_consistent() throws Exception {
        G g = new G();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), g, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        C3MainEquity e = eq60(r, "e6", new ArrayList<>());
        long t1 = r.now.addAndGet(120_000L);
        g.now = t1;
        g.incomes.add(new IncomeRecord(S, "FUNDING_FEE", new BigDecimal("-3.5"), "USDT", t1 - 60_000L, "f1"));
        g.slowPos.set(true);
        AtomicReference<Double> ra = new AtomicReference<>();
        Thread a = new Thread(() -> ra.set(e.c3Equity()), "A1SLOW-A");
        a.start();
        assertTrue(g.entered.await(5, TimeUnit.SECONDS));
        int n = e.pollFunding(t1);
        g.release.countDown();
        a.join(5_000L);
        assertEquals(1, n);
        assertEquals(-3.5d, e.fundingCum(), 1e-9);
        Double cached = e.c3Equity();
        r.now.addAndGet(61_000L);
        Double fresh = e.c3Equity();
        assertEquals(fresh, cached, 1e-9);
        assertEquals(fresh, ra.get(), 1e-9);
    }

    /** E7: KS co tat (KILLSW_EQ_POLL_UNLOCKED=false) + REST cham => tick thread (onTickStart) bi chan suot REST (do tre). */
    @Test
    public void e7_ksFlagOff_tickBlockedDuringRest_measured() throws Exception {
        KillSwitchEngineTestAccess.setEqPollUnlocked(false);
        G g = new G();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), g, 10_000d);
        C3MainEquityKillSwitchTest.c3Position(r, S, "100", "1.0");
        C3MainEquity e = eq60(r, "e7", new ArrayList<>());
        r.ks.attachEquitySource(e);
        g.slowPos.set(true);
        r.now.addAndGet(120_000L);
        Thread ksP = new Thread(() -> r.ks.periodic(r.now.get()), "A1SLOW-KS");
        ksP.setDaemon(true);
        ksP.start();
        assertTrue(g.entered.await(5, TimeUnit.SECONDS));
        Thread rel = new Thread(() -> {
            try { Thread.sleep(800L); } catch (InterruptedException ignore) { }
            g.release.countDown();
        });
        rel.start();
        long s = System.nanoTime();
        r.ks.onTickStart(r.now.get());
        long ms = (System.nanoTime() - s) / 1_000_000L;
        ksP.join(5_000L);
        assertFalse(ksP.isAlive());
        assertTrue("ghi nhan: tick bi chan " + ms + " ms khi tat co KS", ms >= 500L);
    }
}
