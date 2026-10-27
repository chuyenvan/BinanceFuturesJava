package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/** A1 3c: mat ssh / Oracle chet SAU buoc (khong JVM nao canh) => stop tren san gioi han lo <= ~2 USDT. */
public class ProofC3 {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();
    static final long T0 = 1_793_000_000_000L;
    static final String MAIN = "C00USDT";
    MockExchangeGateway mock;
    final AtomicLong now = new AtomicLong(T0);
    File dir;
    double tmb0;

    @Before
    public void setUp() throws Exception {
        mock = new MockExchangeGateway();
        mock.exchangeInfo = C3LiveFixtures.info(6);
        mock.dynamicAccount = true;
        mock.feeRate = new BigDecimal("0.0005");
        mock.now = T0;
        for (int i = 0; i < 6; i++) {
            mock.setPrice(C3LiveFixtures.sym(i), BigDecimal.ONE);
            mock.quoteVolumes.put(C3LiveFixtures.sym(i), new BigDecimal(1000 - i * 100));
        }
        dir = tmp.newFolder("run", "canary");
    }

    UserStream.Connector fakeWs() {
        return (url, l) -> {
            Consumer<String> sink = l::onText;
            mock.wsSink = sink;
            l.onOpen();
            return () -> { if (mock.wsSink == sink) mock.wsSink = null; };
        };
    }

    CanaryEngine engine() throws Exception {
        CanaryEngine.Deps d = new CanaryEngine.Deps();
        d.raw = mock; d.dir = dir; d.clock = now::get;
        d.sleeper = ms -> { long t = now.addAndGet(ms); mock.now = t; };
        d.connector = fakeWs(); d.wsUrls = UserStream.parseUrls(UserStream.DEFAULT_URLS);
        d.alert = m -> { }; d.legacy = s -> false; d.usedWeight1m = () -> 7;
        d.journalName = "j_" + now.get() + "_" + System.nanoTime() + ".jsonl";
        CanaryEngine.Config c = new CanaryEngine.Config();
        c.expectTmb = 10_000d;
        return new CanaryEngine(d, c);
    }

    CanaryEngine.Result run(String k) throws Exception {
        CanaryEngine e = engine();
        CanaryEngine.Result r = k == null ? e.preflight() : e.step(k);
        e.close();   // "JVM ket thuc" — sau day KHONG con gi canh (mat ssh / Oracle chet)
        return r;
    }

    double tmb() { return mock.account().getTotalMarginBalance().doubleValue(); }

    /** Sau buoc: crash gia (khong JVM) => chi stop tren san bao ve. Tra lo = tmb0 - tmb. */
    double crashAfter(String sym, double crashPx) {
        List<OrderInfo> s = mock.openStops(sym);
        assertEquals("phai co dung 1 stop bao ve tren san", 1, s.size());
        assertTrue(s.get(0).isClosePosition());
        double stop = s.get(0).getStopPrice().doubleValue();
        int n = mock.triggerStops(sym, new BigDecimal(String.valueOf(Math.min(crashPx, stop))));
        assertEquals("stop kich", 1, n);
        assertEquals("vi the da dong boi stop", 0, mock.position(sym).signum());
        double loss = tmb0 - tmb();
        System.out.println("PROOF stop=" + stop + " trigger@" + Math.min(crashPx, stop) + " loss=" + String.format(Locale.ROOT, "%.4f", loss));
        return loss;
    }

    void k0() throws Exception {
        CanaryEngine.Result r = run(null);
        assertEquals(r.line(), "DAT", r.verdict);
        tmb0 = tmb();
    }

    @Test public void r1_sshLostAfterK1() throws Exception {
        k0();
        CanaryEngine.Result r = run("K1");
        assertEquals(r.line(), "DAT", r.verdict);
        double loss = crashAfter(MAIN, 0.954);   // trigger at stop price (mock fills at given price)
        assertTrue("lo " + loss + " <= 2", loss <= 2.0);
    }

    @Test public void r2_sshLostAfterK2() throws Exception {
        k0();
        assertEquals("DAT", run("K1").verdict);
        CanaryEngine.Result r = run("K2");
        assertEquals(r.line(), "DAT", r.verdict);
        double loss = crashAfter(MAIN, 0.96);
        assertTrue("lo " + loss, loss <= 2.0);
    }

    @Test public void r3_budgetUsedThenSshLost() throws Exception {
        k0();
        mock.deposit(new BigDecimal("-1.5"));   // da lo 1,5 USDT
        CanaryEngine.Result r = run("K1");
        assertEquals(r.line(), "DAT", r.verdict);
        double loss = crashAfter(MAIN, Double.parseDouble(System.getProperty("px", "0.9805")));
        assertTrue("tong lo " + loss + " <= 2.0", loss <= 2.0);
    }

    @Test public void r4_sshLostAfterK6Open() throws Exception {
        k0();
        CanaryEngine.Result r = run("K6_OPEN");
        assertEquals(r.line(), "DAT", r.verdict);
        double loss = crashAfter(MAIN, 0.95);
        assertTrue("lo " + loss, loss <= 2.0);
    }

    @Test public void r5_gapThroughStop_mockFillsAtCrashPrice() throws Exception {
        k0();
        assertEquals("DAT", run("K1").verdict);
        List<OrderInfo> s = mock.openStops(MAIN);
        mock.triggerStops(MAIN, new BigDecimal("0.80"));   // gap -20 % qua stop
        System.out.println("PROOF gap: stop=" + s.get(0).getStopPrice() + " loss=" + String.format(Locale.ROOT, "%.4f", tmb0 - tmb()));
    }

    @Test public void r6_gatewayBackstopWhenNoPositionVisible() {
        CanaryJournal j = new CanaryJournal(new File(dir, "g.jsonl"), now::get);
        CanaryGateway gw = new CanaryGateway(mock, new LinkedHashSet<>(Collections.singletonList(MAIN)), j, () -> -1, () -> false);
        // khong co vi the tren san => entry null => gateway KHONG chan stop xa (chi engine chan)
        boolean accepted;
        try {
            gw.newStopMarket(MAIN, Side.SELL, null, new BigDecimal("0.50"), "c3s-C00USDT-1-9", true);
            accepted = true;
        } catch (CanaryGateway.GuardException e) {
            accepted = false;
        }
        System.out.println("PROOF backstop entry=null far stop accepted=" + accepted + " mockCalls=" + mock.calls("newStopMarket"));
    }

    @Test public void r7_k1ThenK2RefusedLeavesProtectedPosition() throws Exception {
        k0();
        assertEquals("DAT", run("K1").verdict);
        mock.setPosition("C05USDT", new BigDecimal("3"), BigDecimal.ONE);   // vi the ngoai canary => K2 TU CHOI (khong flatten trong JVM)
        CanaryEngine.Result r = run("K2");
        System.out.println("PROOF K2 with foreign: " + r.line());
        assertEquals(1, mock.openStops(MAIN).size());
    }
}
