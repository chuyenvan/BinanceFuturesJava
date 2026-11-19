package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.api.PositionInfo;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.risk.C3MainEquityTestAccess;
import com.binance.chuyennd.ops.KillSwitchEngineTestAccess;
import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.management.ThreadMXBean;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.Assert.*;

/**
 * [W3B HANG-1119] Tai hien treo 19/11 (4 lan, adapter=live): khoa C3MainEquity (EQ) va KillSwitchEngine (KS) nguoc thu tu.
 * B = C3LIVE-OPS: c3Equity() [EQ] -> positions() REST (o day: chan cho toi khi A da vao KS; production = ngu burst
 * canary toi giay 41 + REST) -> api.onApiResult -> ks.onApiResult [KS].
 * A = OpsKillSwitch: ks.periodic() [KS cu] -> equitySource.totalMarginBalance() = c3Equity() [EQ].
 * C = pool-1: ks.onTickStart() [KS] (nan nhan; production = heartbeat dung => watchdog kill sau 600 s).
 * Rig dung dung day noi production: api -> ks.onApiResult, ks.attachEquitySource(eq).
 */
public class KsEquityDeadlockHang1119Test {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @After
    public void restore() {
        KillSwitchEngineTestAccess.setEqPollUnlocked(true);
        C3MainEquityTestAccess.setRestUnlocked(true);
    }

    /** positions() cua luong "B": bao da vao (dang giu EQ) roi cho tin hieu (mo phong REST dang cho/ngu burst). */
    static final class SlowPositions extends MockExchangeGateway {
        final AtomicBoolean armed = new AtomicBoolean();
        final CountDownLatch entered = new CountDownLatch(1);
        final CountDownLatch release = new CountDownLatch(1);

        @Override
        public List<PositionInfo> positions() {
            if ("SIM-C3LIVE-OPS".equals(Thread.currentThread().getName()) && armed.compareAndSet(true, false)) {
                entered.countDown();
                try {
                    release.await(5, TimeUnit.SECONDS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
            return super.positions();
        }
    }

    static final class Run {
        Thread a, b, c;
        boolean deadlock;
        String dump = "";
    }

    private Run scenario() throws Exception {
        SlowPositions mock = new SlowPositions();
        MainAccountRig r = new MainAccountRig(tmp.newFolder(), mock, 2_000d);
        r.setAccount("1000000", "600000");
        long t = r.now.addAndGet(60_000L);
        r.ks.periodic(t);   // khoi dong binh thuong (khong treo)
        mock.armed.set(true);
        Run run = new Run();
        run.b = new Thread(() -> r.eq.c3Equity(), "SIM-C3LIVE-OPS");
        run.a = new Thread(() -> r.ks.periodic(r.now.get()), "SIM-OpsKillSwitch");
        run.c = new Thread(() -> r.ks.onTickStart(r.now.get()), "SIM-pool-1");
        for (Thread th : new Thread[]{run.a, run.b, run.c}) th.setDaemon(true);
        run.b.start();
        assertTrue("B phai vao REST (giu EQ)", mock.entered.await(5, TimeUnit.SECONDS));
        run.a.start();
        waitBlockedOrDone(run.a, 3_000L);   // A: cu = giu KS, cho EQ; moi = khong giu KS
        mock.release.countDown();            // REST xong -> B goi onApiResult (can KS)
        run.b.join(3_000L);
        run.a.join(3_000L);
        run.c.start();
        run.c.join(2_000L);
        ThreadMXBean mx = ManagementFactory.getThreadMXBean();
        long[] all = mx.findMonitorDeadlockedThreads();
        // chi tinh thread CUA LUOT NAY (test khac cung JVM co the con thread deadlock cu)
        java.util.List<Long> mine = new java.util.ArrayList<>();
        if (all != null) {
            for (long id : all) {
                if (id == run.a.getId() || id == run.b.getId() || id == run.c.getId()) mine.add(id);
            }
        }
        run.deadlock = !mine.isEmpty();
        if (run.deadlock) {
            long[] ids = new long[mine.size()];
            for (int i = 0; i < ids.length; i++) ids[i] = mine.get(i);
            StringBuilder sb = new StringBuilder();
            for (ThreadInfo ti : mx.getThreadInfo(ids, true, false)) {
                sb.append(ti.getThreadName()).append(" BLOCKED on ").append(ti.getLockName()).append(" held by ")
                        .append(ti.getLockOwnerName()).append('\n');
            }
            run.dump = sb.toString();
        }
        return run;
    }

    private static void waitBlockedOrDone(Thread th, long maxMs) throws InterruptedException {
        long end = System.currentTimeMillis() + maxMs;
        while (System.currentTimeMillis() < end) {
            Thread.State s = th.getState();
            if (s == Thread.State.BLOCKED || s == Thread.State.TERMINATED) return;
            Thread.sleep(10L);
        }
    }

    @Test
    public void oldBehavior_reproducesDeadlock_andTickThreadStuck() throws Exception {
        KillSwitchEngineTestAccess.setEqPollUnlocked(false);
        C3MainEquityTestAccess.setRestUnlocked(false);   // [W3B muc 2] ca 2 co ve hanh vi cu
        Run run = scenario();
        assertTrue("phai tai hien DEADLOCK KS<->EQ (hanh vi cu)", run.deadlock);
        assertTrue(run.dump, run.dump.contains("SIM-OpsKillSwitch") && run.dump.contains("SIM-C3LIVE-OPS"));
        assertTrue("A treo", run.a.isAlive());
        assertTrue("B treo", run.b.isAlive());
        assertTrue("pool-1 onTickStart treo theo (heartbeat dung)", run.c.isAlive());
        assertEquals(Thread.State.BLOCKED, run.c.getState());
    }

    @Test
    public void fixed_noDeadlock_allThreadsFinish() throws Exception {
        KillSwitchEngineTestAccess.setEqPollUnlocked(true);
        Run run = scenario();
        assertFalse("khong duoc deadlock: " + run.dump, run.deadlock);
        assertFalse("A xong", run.a.isAlive());
        assertFalse("B xong", run.b.isAlive());
        assertFalse("pool-1 xong", run.c.isAlive());
    }

    /** [W3B muc 2] chi tat co KS (KILLSW_EQ_POLL_UNLOCKED=false), EQ REST ngoai khoa => KHONG deadlock. */
    @Test
    public void ksOld_eqRestUnlocked_noDeadlock() throws Exception {
        KillSwitchEngineTestAccess.setEqPollUnlocked(false);
        C3MainEquityTestAccess.setRestUnlocked(true);
        Run run = scenario();
        assertFalse("khong duoc deadlock: " + run.dump, run.deadlock);
        assertFalse(run.a.isAlive());
        assertFalse(run.b.isAlive());
        assertFalse(run.c.isAlive());
    }

    /** [W3B muc 2] chi tat co EQ (C3_EQ_REST_UNLOCKED=false), KS poll ngoai khoa => KHONG deadlock. */
    @Test
    public void eqOld_ksUnlocked_noDeadlock() throws Exception {
        KillSwitchEngineTestAccess.setEqPollUnlocked(true);
        C3MainEquityTestAccess.setRestUnlocked(false);
        Run run = scenario();
        assertFalse("khong duoc deadlock: " + run.dump, run.deadlock);
        assertFalse(run.a.isAlive());
        assertFalse(run.b.isAlive());
        assertFalse(run.c.isAlive());
    }

    @Test
    public void envParsing_defaultOnRollbackOff() {
        assertTrue(KillSwitchEngineTestAccess.parse(null));
        assertTrue(KillSwitchEngineTestAccess.parse("1"));
        assertTrue(KillSwitchEngineTestAccess.parse(" true "));
        assertFalse(KillSwitchEngineTestAccess.parse("0"));
        assertFalse(KillSwitchEngineTestAccess.parse("FALSE"));
    }
}
