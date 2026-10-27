package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/**
 * [V12 3] Kich ban G-CANARY K0–K8, K6b, K7b tren MockExchangeGateway (dong ho gia, websocket gia) qua DUNG cac lop c3_live,
 * + guard cung (tran lo, symbol ngoai, vi the ngoai, MO-5 chi 1 lan).
 */
public class CanaryEngineTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_793_000_000_000L;
    static final String MAIN = "C00USDT";
    static final String AUX = "C01USDT";

    MockExchangeGateway mock;
    final AtomicLong now = new AtomicLong(T0);
    File dir;
    final List<String> telegram = Collections.synchronizedList(new ArrayList<>());
    volatile Consumer<Long> hook = t -> { };

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

    /** websocket gia: noi wsSink cua mock vao listener. */
    UserStream.Connector fakeWs() {
        return (url, l) -> {
            Consumer<String> sink = l::onText;
            mock.wsSink = sink;
            l.onOpen();
            return () -> {
                if (mock.wsSink == sink) mock.wsSink = null;
            };
        };
    }

    CanaryEngine engine(CanaryEngine.Config cfg) throws Exception {
        CanaryEngine.Deps d = new CanaryEngine.Deps();
        d.raw = mock;
        d.dir = dir;
        d.clock = now::get;
        d.sleeper = ms -> {
            long t = now.addAndGet(ms);
            mock.now = t;
            hook.accept(t);
        };
        d.connector = fakeWs();
        d.wsUrls = UserStream.parseUrls(UserStream.DEFAULT_URLS);
        d.alert = telegram::add;
        d.legacy = s -> false;
        d.usedWeight1m = () -> 7;
        d.journalName = "j_" + now.get() + "_" + System.nanoTime() + ".jsonl";
        return new CanaryEngine(d, cfg);
    }

    static CanaryEngine.Config cfg() {
        CanaryEngine.Config c = new CanaryEngine.Config();
        c.expectTmb = 10_000d;
        return c;
    }

    private static void ok(CanaryEngine.Result r) {
        assertEquals(r.line() + " data=" + r.data, CanaryEngine.DAT, r.verdict);
    }

    private int writes() {
        return mock.calls("newMarketOrder") + mock.calls("newStopMarket") + mock.calls("cancelStop") + mock.calls("cancelOrder")
                + mock.calls("setLeverage") + mock.calls("setMarginType") + mock.calls("setDualSidePosition");
    }

    private CanaryEngine.Result run(String step) throws Exception {
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = e.step(step);
        e.close();
        return r;
    }

    private void preflight() throws Exception {
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = e.preflight();
        e.close();
        ok(r);
    }

    // ------------------------------------------------------------------ toan bo phien
    @Test
    public void fullSessionK0toK8() throws Exception {
        // K0: chi doc, chon 2 symbol theo luat (quoteVolume giam dan), 65' websocket + keepAlive x2
        CanaryEngine e0 = engine(cfg());
        CanaryEngine.Result k0 = e0.preflight();
        e0.close();
        ok(k0);
        assertEquals(MAIN, e0.state().symMain);
        assertEquals(AUX, e0.state().symAux);
        assertEquals("K0 chi doc: 0 lenh ghi", 0, writes());
        assertTrue(((Number) k0.data.get("ws.keepAliveOk")).intValue() >= 2);
        assertEquals(10_000d, e0.state().tmb0, 1e-9);

        // K1 + MO-5: san nhan lenh, client mat response => queryOrder(cid), 0 gui lai
        CanaryEngine.Config c1 = cfg();
        c1.injectTimeout = true;
        CanaryEngine e1 = engine(c1);
        CanaryEngine.Result k1 = e1.step("K1");
        e1.close();
        ok(k1);
        assertEquals(1, mock.calls("newMarketOrder"));
        assertTrue("query-by-cid", mock.calls("queryOrder") >= 1);
        assertTrue(e1.state().injectTimeoutUsed);
        assertEquals(0, new BigDecimal("20").compareTo(mock.position(MAIN)));
        assertProtect(MAIN, CanaryLimits.MAX_STOP_DIST);   // [3c MAJ-C1] K1 KHONG de vi the tran qua ranh gioi JVM

        // K2: stop -20 % -> -19 % -> closePosition thu 2 (-4130) -> -18 % (qty+reduceOnly)
        mock.rejectSecondClosePosition = true;
        CanaryEngine.Result k2 = run("K2");
        ok(k2);
        // san -4130 ngay o lan doi (b) => trailing chuyen qty+reduceOnly (khong khoang trong); (c) closePosition thu 2 duoc nhan
        // (B la stop qty) roi guard huy (stop active B dang mo)
        assertTrue(String.valueOf(k2.data.get("trail.stats")), String.valueOf(k2.data.get("trail.stats")).contains("fallbackQty=1"));
        assertEquals(Boolean.TRUE, k2.data.get("b.qtyMode"));
        assertEquals("CANCELLED", k2.data.get("c.cancel"));
        assertEquals(1, mock.openStops(MAIN).size());
        mock.rejectSecondClosePosition = false;

        // K3: stop tren mark => -2021 => dong MARKET reduce-only (TRAILING_IMMEDIATE)
        mock.rejectWouldTrigger = true;
        CanaryEngine.Result k3 = run("K3");
        ok(k3);
        assertEquals(0, mock.position(MAIN).signum());
        assertTrue(mock.openStops(null).isEmpty());
        mock.rejectWouldTrigger = false;

        // K4: stop mark -0,15 %, san kich sau ~2'
        final long k4Start = now.get();
        final boolean[] fired = {false};
        hook = t -> {
            if (!fired[0] && t - k4Start > 120_000L && !mock.openStops(MAIN).isEmpty()) {
                fired[0] = true;
                mock.triggerStops(MAIN, new BigDecimal("0.998"));
            }
        };
        CanaryEngine.Result k4 = run("K4");
        hook = t -> { };
        ok(k4);
        assertTrue(fired[0]);
        assertTrue(String.valueOf(k4.data.get("ledger")), String.valueOf(k4.data.get("ledger")).contains("TRAILING_STOP"));
        assertTrue(mock.openStops(null).isEmpty());

        // K5: time-stop
        CanaryEngine.Result k5 = run("K5");
        ok(k5);
        assertEquals(0, mock.position(MAIN).signum());

        // K6: mo + arm, "kill", JVM moi
        ok(run("K6_OPEN"));
        assertProtect(MAIN, CanaryLimits.MAX_STOP_DIST);
        int ord = mock.calls("newMarketOrder");
        int stp = mock.calls("newStopMarket");
        CanaryEngine.Result k6 = run("K6_RESTART");
        ok(k6);
        assertEquals("K6", k6.command);
        assertEquals("0 lenh moi sau restart", ord, mock.calls("newMarketOrder"));
        assertEquals("0 stop trung", stp, mock.calls("newStopMarket"));

        // K6b: so mat => stop VAN CON, UNKNOWN (A); roi flatten
        ok(run("K6B_OPEN"));
        File book = new File(dir, CanaryEngine.BOOK_NAME);
        assertTrue(book.renameTo(new File(dir, CanaryEngine.BOOK_NAME + ".lost")));
        int cancels = mock.calls("cancelStop");
        CanaryEngine.Result k6b = run("K6B_RESTART");
        ok(k6b);
        assertEquals("K6b", k6b.command);
        assertEquals("0 huy stop khi so mat", cancels, mock.calls("cancelStop"));
        assertEquals(1, mock.openStops(MAIN).size());
        CanaryEngine ef = engine(cfg());
        ok(ef.flatten());
        ef.close();
        assertEquals(0, mock.position(MAIN).signum());
        assertTrue(mock.openStops(null).isEmpty());

        // K7: cat websocket 330 s
        CanaryEngine.Result k7 = run("K7");
        ok(k7);
        assertTrue(((Number) k7.data.get("detectMs")).longValue() <= 15_000L);
        assertEquals(Boolean.TRUE, k7.data.get("telegramDown"));

        // K7b: symbol phu vao duoc trong luc symbol chinh o (B)
        CanaryEngine.Result k7b = run("K7B");
        ok(k7b);
        assertEquals("K7b", k7b.command);
        assertNull("khong len (A) duoi 10'", k7b.data.get("A.firstSeenAfterCloseMs"));
        assertTrue(mock.openStops(null).isEmpty());
        assertEquals(0, mock.position(AUX).signum());

        // K8: doi chieu cuoi phien
        CanaryEngine.Result k8 = run("K8");
        ok(k8);
        assertTrue(((Number) k8.data.get("diffFrac")).doubleValue() < 1e-6);

        CanaryEngine ec = engine(cfg());
        ok(ec.cleanupCheck());
        ec.close();
        CanaryState st = CanaryState.load(dir);
        for (String k : new String[]{"K0", "K1", "K2", "K3", "K4", "K5", "K6", "K6b", "K7", "K7b", "K8"}) {
            assertNotNull("thieu ket qua " + k, st.steps.get(k));
            assertEquals(k, CanaryEngine.DAT, st.steps.get(k).result);
        }
        assertTrue("phi da ghi", st.cumFeeStable > 0d);
        assertTrue("0 lenh ngoai 2 symbol", mock.callLog().stream().noneMatch(x -> x.contains("C02USDT") || x.contains("C05USDT")));
    }

    /** 1 stop c3s- closePosition, stop / gia vao = 1 - dist (+- dung sai lam tron). */
    private void assertProtect(String sym, double dist) {
        List<com.binance.chuyennd.c3live.api.OrderInfo> s = mock.openStops(sym);
        assertEquals("so stop " + sym, 1, s.size());
        assertTrue(s.get(0).isClosePosition());
        double r = s.get(0).getStopPrice().doubleValue() / entry(sym);
        assertTrue("stop/entry=" + r, r >= 1d - dist - CanaryLimits.STOP_ROUND_TOL && r <= 1d - dist + CanaryLimits.STOP_ROUND_TOL);
    }

    private double entry(String sym) {
        for (com.binance.chuyennd.c3live.api.PositionInfo p : mock.positions()) {
            if (sym.equals(p.getSymbol()) && p.getPositionAmt() != null && p.getPositionAmt().signum() != 0) {
                return p.getEntryPrice().doubleValue();
            }
        }
        fail("khong co vi the " + sym);
        return 0d;
    }

    // ------------------------------------------------------------------ [3c MAJ-C1] stop bao ve (prereg §ADD-2)
    @Test
    public void protectiveStopTightensWhenLossBudgetShrinks() throws Exception {
        preflight();
        mock.deposit(new BigDecimal("-1.5"));   // tmb0 - tmb = 1,5 => ngan sach (2 - 0,1 - 1,5) / 20 ~ 2 %
        ok(run("K1"));
        List<com.binance.chuyennd.c3live.api.OrderInfo> s = mock.openStops(MAIN);
        assertEquals(1, s.size());
        double r = s.get(0).getStopPrice().doubleValue() / entry(MAIN);
        assertTrue("stop/entry=" + r, r > 0.975d && r < 0.985d);
    }

    @Test
    public void noOpenWhenLossBudgetTooSmall() throws Exception {
        preflight();
        mock.deposit(new BigDecimal("-1.85"));   // ngan sach 0,05 USDT => stop 0,25 % < 1 %
        CanaryEngine.Result r = run("K1");
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("ngan sach"));
        assertEquals("khong gui lenh mo", 0, mock.calls("newMarketOrder"));
    }

    @Test
    public void protectFailureClosesPositionImmediately() throws Exception {
        preflight();
        mock.rejectAllStops = true;
        for (String k : new String[]{"K1", "K6_OPEN"}) {
            CanaryEngine.Result r = run(k);
            assertEquals(k + " " + r.line(), CanaryEngine.TRUOT, r.verdict);
            assertTrue(r.line(), r.line().contains("stop bao ve"));
            assertEquals(k + ": vi the da dong ngay", 0, mock.position(MAIN).signum());
            assertTrue(mock.openStops(null).isEmpty());
        }
    }

    // ------------------------------------------------------------------ guard cung
    @Test
    public void mo5InjectionOnlyOncePerSession() throws Exception {
        preflight();
        CanaryEngine.Config c = cfg();
        c.injectTimeout = true;
        CanaryEngine e1 = engine(c);
        ok(e1.step("K1"));
        e1.close();
        CanaryEngine ef = engine(cfg());
        ok(ef.flatten());
        ef.close();
        CanaryEngine e2 = engine(c);
        CanaryEngine.Result r = e2.step("K1");
        e2.close();
        assertEquals(r.line(), CanaryEngine.TU_CHOI, r.verdict);
        assertTrue(r.line(), r.line().contains("MO-5"));
        assertEquals("1 lenh mo + 1 lenh dong (flatten), khong gui lai", 2, mock.calls("newMarketOrder"));
    }

    @Test
    public void lossCapFlattensAndStopsSession() throws Exception {
        preflight();
        ok(run("K1"));
        mock.deposit(new BigDecimal("-2.5"));   // tmb giam 2,5 USDT (lo/phi) => cham tran 2 USDT
        CanaryEngine.Result r = run("K2");
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("tran lo"));
        assertEquals("da flatten", 0, mock.position(MAIN).signum());
        assertTrue(mock.openStops(null).isEmpty());
        CanaryState st = CanaryState.load(dir);
        assertNotNull(st.aborted);
        int n = mock.calls("newMarketOrder");
        CanaryEngine.Result r2 = run("K1");
        assertEquals(r2.line(), CanaryEngine.TU_CHOI, r2.verdict);
        assertEquals("phien dung: 0 lenh moi", n, mock.calls("newMarketOrder"));
        CanaryEngine ef = engine(cfg());
        ok(ef.flatten());   // flatten van chay khi phien dung
        ef.close();
    }

    @Test
    public void foreignPositionRefusesWithoutTouchingIt() throws Exception {
        preflight();
        mock.setPosition("C05USDT", new BigDecimal("10"), BigDecimal.ONE);
        int w0 = writes();
        CanaryEngine.Result r = run("K1");
        assertEquals(r.line(), CanaryEngine.TU_CHOI, r.verdict);
        assertTrue(r.line(), r.line().contains("C05USDT"));
        assertEquals(w0, writes());
        CanaryEngine ef = engine(cfg());
        CanaryEngine.Result f = ef.flatten();
        ef.close();
        ok(f);
        assertEquals("flatten KHONG cham symbol ngoai", 0, new BigDecimal("10").compareTo(mock.position("C05USDT")));
    }

    @Test
    public void stepsRefusedBeforePreflight() throws Exception {
        CanaryEngine.Result r = run("K1");
        assertEquals(CanaryEngine.TU_CHOI, r.verdict);
        assertEquals(0, writes());
    }

    @Test
    public void k1RefusedWhenNotFlat() throws Exception {
        preflight();
        ok(run("K1"));
        CanaryEngine.Result r = run("K1");
        assertEquals(r.line(), CanaryEngine.TU_CHOI, r.verdict);
        assertEquals(1, mock.calls("newMarketOrder"));
    }

    @Test
    public void k0FailsWithoutExpectedTmbOrWrongMarginMode() throws Exception {
        CanaryEngine.Config c = new CanaryEngine.Config();
        CanaryEngine e = engine(c);
        CanaryEngine.Result r = e.preflight();
        e.close();
        assertEquals(CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("CANARY_EXPECT_TMB"));
        assertNull("khong co moc tmb", CanaryState.load(dir).tmb0);
        mock.setSymbolConfig(MAIN, "ISOLATED", 3);
        CanaryEngine e2 = engine(cfg());
        CanaryEngine.Result r2 = e2.preflight();
        e2.close();
        assertEquals(CanaryEngine.TRUOT, r2.verdict);
        assertTrue(r2.line(), r2.line().contains("SETUP"));
        assertEquals(0, writes());
        CanaryEngine e3 = engine(cfg());
        ok(e3.setup());
        e3.close();
        assertEquals("CROSSED", mock.symbolConfig(MAIN).getMarginType());
        assertEquals(1, mock.symbolConfig(MAIN).getLeverage());
    }

    @Test
    public void k6bFailsIfBookNotRenamed() throws Exception {
        preflight();
        ok(run("K6B_OPEN"));
        CanaryEngine.Result r = run("K6B_RESTART");
        assertEquals(CanaryEngine.TU_CHOI, r.verdict);
    }

    @Test
    public void journalHasNoListenKeyOrSecrets() throws Exception {
        preflight();
        ok(run("K1"));
        for (File f : dir.listFiles()) {
            if (!f.getName().endsWith(".jsonl")) continue;
            String s = new String(java.nio.file.Files.readAllBytes(f.toPath()), java.nio.charset.StandardCharsets.UTF_8);
            assertFalse(f.getName(), s.contains("mockListenKey"));
            assertFalse(s.contains("signature"));
        }
        assertEquals("{\"listenKey\":\"***\"}", CanaryJournal.mask("{\"listenKey\":\"abcdef123\"}"));
    }
}
