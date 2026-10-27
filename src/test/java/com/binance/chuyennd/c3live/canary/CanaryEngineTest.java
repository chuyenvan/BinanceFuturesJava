package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.rate.RateGuard;
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
    volatile String[] jarIdVal = {"jarA", String.valueOf(T0 - 3_600_000L)};

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
        d.jarId = () -> jarIdVal;
        d.legacySize = legacySizeVal;
        return new CanaryEngine(d, cfg);
    }

    /** [3g MIN-8] so dong legacy_symbols.csv cho engine() (-1 = khong ap dung). */
    int legacySizeVal = -1;

    static CanaryEngine.Config cfg() {
        CanaryEngine.Config c = new CanaryEngine.Config();
        c.expectTmb = 10_000d;
        c.priorLossUsdt = 0d;   // [3g MIN-3] lo cong don cac phien truoc (script truyen CANARY_PRIOR_LOSS_USDT)
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

    // ------------------------------------------------------------------ [3d §ADD-3] K0 dung lai keepAlive
    private CanaryEngine.Result k0(boolean reuse) throws Exception {
        CanaryEngine.Config c = cfg();
        c.reuseKeepAlive = reuse;
        CanaryEngine e = engine(c);
        CanaryEngine.Result r = e.preflight();
        e.close();
        ok(r);
        return r;
    }

    @Test
    public void k0ReusesKeepAliveOnlyFromRealK0SameJarWithin24h() throws Exception {
        CanaryEngine.Result r0 = k0(false);   // K0 that: 65' + keepAlive >= 2
        assertEquals("jarA", r0.data.get("jar.md5"));
        long t1 = now.get();
        CanaryEngine.Result r1 = k0(true);
        assertTrue(String.valueOf(r1.data), String.valueOf(r1.data.get("ws.keepAliveSkipped")).contains("md5 jar trung jarA"));
        assertTrue("khong chay lai 65'", now.get() - t1 < 10 * 60_000L);
        long t2 = now.get();
        CanaryEngine.Result r2 = k0(true);   // K0 truoc la ban dung lai => khong noi tiep
        assertNull(r2.data.get("ws.keepAliveSkipped"));
        assertTrue(String.valueOf(r2.data.get("ws.keepAliveReuse")).contains("noi tiep"));
        assertTrue(now.get() - t2 >= 65 * 60_000L);
        jarIdVal = new String[]{"jarB", String.valueOf(T0)};
        long t3 = now.get();
        CanaryEngine.Result r3 = k0(true);   // jar khac
        assertTrue(String.valueOf(r3.data.get("ws.keepAliveReuse")).contains("jar khac"));
        assertTrue(now.get() - t3 >= 65 * 60_000L);
        now.addAndGet(25L * 3_600_000L);
        mock.now = now.get();
        long t4 = now.get();
        CanaryEngine.Result r4 = k0(true);   // > 24 h
        assertTrue(String.valueOf(r4.data.get("ws.keepAliveReuse")).contains("> 24 h"));
        assertTrue(now.get() - t4 >= 65 * 60_000L);
        long t5 = now.get();
        CanaryEngine.Result r5 = k0(false);   // khong bat co => luon chay du, khong ghi reuse
        assertNull(r5.data.get("ws.keepAliveReuse"));
        assertNull(r5.data.get("ws.keepAliveSkipped"));
        assertTrue(now.get() - t5 >= 65 * 60_000L);
    }

    @Test
    public void k0LegacyRecordWithoutJarMd5ReusesOnlyIfJarUnchangedSince() throws Exception {
        jarIdVal = new String[]{null, null};
        k0(false);                                                       // K0 cu: khong ghi md5 jar
        jarIdVal = new String[]{"jarA", String.valueOf(T0 - 3_600_000L)};   // jar co tu truoc K0 do
        CanaryEngine.Result r1 = k0(true);
        assertTrue(String.valueOf(r1.data), String.valueOf(r1.data.get("ws.keepAliveSkipped")).contains("khong doi tu luc do"));
        jarIdVal = new String[]{null, null};
        k0(false);
        jarIdVal = new String[]{"jarA", String.valueOf(now.get() + 60_000L)};   // jar thay SAU K0 do
        CanaryEngine.Result r2 = k0(true);
        assertTrue(String.valueOf(r2.data.get("ws.keepAliveReuse")).contains("jar da doi sau K0 do"));
    }

    // ------------------------------------------------------------------ [3c MAJ-C1] stop bao ve (prereg §ADD-2)
    @Test
    public void protectiveStopTightensWhenLossBudgetShrinks() throws Exception {
        preflight();
        setRealizedLoss(1.5);   // [3f §ADD-4 G] lo canary da chot 1,5 => ngan sach (2 - 0,1 - 1,5) / 20 ~ 2 %
        ok(run("K1"));
        List<com.binance.chuyennd.c3live.api.OrderInfo> s = mock.openStops(MAIN);
        assertEquals(1, s.size());
        double r = s.get(0).getStopPrice().doubleValue() / entry(MAIN);
        assertTrue("stop/entry=" + r, r > 0.975d && r < 0.985d);
    }

    @Test
    public void noOpenWhenLossBudgetTooSmall() throws Exception {
        preflight();
        setRealizedLoss(1.85);   // [3f] ngan sach 0,05 USDT => stop 0,25 % < 1 %
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
        mock.setPrice(MAIN, new BigDecimal("0.88"));   // [3f §ADD-4 G] lo chua chot canary 20 x 0,12 = 2,4 USDT => cham tran 2
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
        mock.setPosition("C05USDT", new BigDecimal("10"), BigDecimal.ONE);   // [3f §ADD-4] LEGACY symbol khac: binh thuong
        CanaryEngine.Result r = run("K1");
        ok(r);
        assertEquals("LEGACY khong bi cham", 0, new BigDecimal("10").compareTo(mock.position("C05USDT")));
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
        // [3f §ADD-4 H] khong kiem tmb tuyet doi; availableBalance < 50 USDT => TRUOT
        mock.dynamicAccount = false;
        mock.accountSnapshot = new com.binance.chuyennd.c3live.api.AccountSnapshot(new BigDecimal("10000"), new BigDecimal("10000"),
                new BigDecimal("10"), BigDecimal.ZERO, Collections.emptyList(), T0);
        CanaryEngine.Config c = new CanaryEngine.Config();
        CanaryEngine e = engine(c);
        CanaryEngine.Result r = e.preflight();
        e.close();
        assertEquals(CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("availableBalance"));
        assertFalse(r.line(), r.line().contains("CANARY_EXPECT_TMB"));
        assertNull("khong co moc tmb", CanaryState.load(dir).tmb0);
        mock.dynamicAccount = true;
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

    // ------------------------------------------------------------------ [3e]
    /** Dong ho RateGuard = dong ho gia cua test (ngu => tien dong ho chung + mock). */
    RateGuard.Clock rgClock() {
        return new RateGuard.Clock() {
            @Override public long nowMs() { return now.get(); }
            @Override public void sleepMs(long ms) { mock.now = now.addAndGet(ms); }
        };
    }

    /** Gateway "that" gia: moi call qua RateGuard nhu C3LiveClient (weight uoc tinh nhu W_*), roi toi mock. */
    static ExchangeGateway guarded(ExchangeGateway inner, RateGuard rg) {
        return (ExchangeGateway) java.lang.reflect.Proxy.newProxyInstance(ExchangeGateway.class.getClassLoader(),
                new Class<?>[]{ExchangeGateway.class}, (proxy, m, args) -> {
                    String n = m.getName();
                    if (!"name".equals(n) && !"toString".equals(n) && !"hashCode".equals(n) && !"equals".equals(n)) {
                        Object a0 = args != null && args.length > 0 ? args[0] : null;
                        boolean order = n.startsWith("newMarketOrder") || n.startsWith("newStopMarket");
                        rg.acquire(CanaryGateway.estWeight(n, a0 instanceof String ? (String) a0 : null), order ? 1 : 0);
                    }
                    try {
                        return m.invoke(inner, args);
                    } catch (java.lang.reflect.InvocationTargetException e) {
                        throw e.getCause();
                    }
                });
    }

    CanaryEngine engineRaw(CanaryEngine.Config cfg, ExchangeGateway raw, RateGuard rg) throws Exception {
        CanaryEngine.Deps d = new CanaryEngine.Deps();
        d.raw = raw;
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
        d.usedWeight1m = rg::lastServerWeight1m;
        d.rateGuard = rg;
        d.journalName = "j_" + now.get() + "_" + System.nanoTime() + ".jsonl";
        d.jarId = () -> jarIdVal;
        return new CanaryEngine(d, cfg);
    }

    @Test
    public void queryStopBackoffSumsToBound() {
        long s = 0;
        for (long w : CanaryEngine.QUERY_STOP_BACKOFF_MS) s += w;
        assertEquals(CanaryEngine.QUERY_STOP_MAX_WAIT_MS, s);
    }

    @Test
    public void k2QueryStopReadAfterWriteLagRetriedWithinBound() throws Exception {
        preflight();
        ok(run("K1"));
        mock.queryStopLagCalls = 2;   // 2 lan dau moi cid: GET algoOrder chua thay (openStops da thay) — nhu 10-27
        CanaryEngine.Result r = run("K2");
        ok(r);
        for (String l : new String[]{"a", "b", "d"}) {
            assertEquals(l, 3, ((Number) r.data.get(l + ".queryStopAttempts")).intValue());
            assertTrue(l, ((Number) r.data.get(l + ".queryStopMs")).longValue() <= CanaryEngine.QUERY_STOP_MAX_WAIT_MS);
            assertEquals(l, "NEW", r.data.get(l + ".queryStop"));
        }
        assertTrue(((Number) r.data.get("ownWeight1mMax")).intValue() > 0);
    }

    @Test
    public void k2QueryStopStillMissingAfterBoundFails() throws Exception {
        preflight();
        ok(run("K1"));
        mock.queryStopLagCalls = 1_000;   // khong bao gio thay => tieu chi K2 KHONG noi long
        CanaryEngine.Result r = run("K2");
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("queryStop"));
        assertEquals(1 + CanaryEngine.QUERY_STOP_BACKOFF_MS.length, ((Number) r.data.get("a.queryStopAttempts")).intValue());
        assertEquals("KHONG CO", r.data.get("a.queryStop"));
        assertEquals("TRUOT => dong", 0, mock.position(MAIN).signum());
    }

    @Test
    public void emergencyFlattenNotBlockedByOwnRateGuard() throws Exception {
        preflight();
        ok(run("K1"));
        assertTrue(mock.position(MAIN).signum() > 0);
        RateGuard rg = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, rgClock());
        rg.onHeaders(1494, null, null);   // nhu 10-27 22:18:46: IP chung LEGACY 1494 > ngan sach 1200
        ExchangeGateway raw = guarded(mock, rg);
        try {   // doi chung: lan thuong bi chinh guard cua ta tu choi
            raw.positions();
            fail("lan thuong phai bi tu choi");
        } catch (GatewayException e) {
            assertEquals(ErrorKind.RATE_LIMIT, e.getKind());
        }
        CanaryEngine ef = engineRaw(cfg(), raw, rg);
        CanaryEngine.Result f = ef.flatten();
        long rejects = rg.rejects();
        ef.close();
        ok(f);
        assertEquals(0, mock.position(MAIN).signum());
        assertTrue(mock.openStops(null).isEmpty());
        assertEquals("chi lan doi chung bi tu choi", 1L, rejects);
        assertTrue(rg.emergencyCalls() > 0);
        assertTrue("flatten chay khi ngan sach thuong da het", rg.emergencyOverBudget() > 0);
        assertEquals(rg.emergencyCalls(), ((Number) f.data.get("rate.emergencyCalls")).longValue());
    }

    @Test
    public void stepRefusedByRateGuardStillAutoFlattens() throws Exception {
        // [3f §ADD-4 I] call thuong bi guard client tu choi (IP nang) => cho sang phut sau roi thu lai, KHONG TRUOT ngay
        preflight();
        ok(run("K1"));
        RateGuard rg = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, rgClock());
        rg.onHeaders(1494, null, null);
        CanaryEngine e = engineRaw(cfg(), guarded(mock, rg), rg);
        CanaryEngine.Result r = e.step("K2");
        boolean retried = e.journal().entries().stream().anyMatch(x -> "GUARD_WAIT_RETRY".equals(x.get("type")));
        e.close();
        ok(r);
        assertTrue("co GUARD_WAIT_RETRY", retried);
    }

    // ------------------------------------------------------------------ [3f §ADD-4] tai khoan CHINH (LEGACY cung tai khoan)
    private void setRealizedLoss(double v) throws Exception {
        CanaryState s = CanaryState.load(dir);
        s.cumFeeStable = v;
        s.save(dir);
    }

    private CanaryEngine.Result cleanup() throws Exception {
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = e.cleanupCheck();
        e.close();
        return r;
    }

    private CanaryEngine.Result flattenRun() throws Exception {
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = e.flatten();
        e.close();
        return r;
    }

    private boolean noWriteOn(String... syms) {
        return mock.callLog().stream().noneMatch(x -> {
            for (String s : syms) if (x.contains(s)) return true;
            return false;
        });
    }

    @Test
    public void legacyElsewhereUntouchedAndPickExcludesLegacySymbols() throws Exception {
        mock.setPosition("C00USDT", new BigDecimal("5"), BigDecimal.ONE);                               // LEGACY vi the (top 1)
        mock.addRestingOrder("C01USDT", "web_legacy_o1", com.binance.chuyennd.c3live.api.Side.BUY, new BigDecimal("3"));   // top 2
        mock.addRestingStop("C04USDT", "web_legacy_a1", new BigDecimal("2"), new BigDecimal("0.5"));
        CanaryEngine e0 = engine(cfg());
        CanaryEngine.Result k0 = e0.preflight();
        e0.close();
        ok(k0);
        assertEquals("loai symbol LEGACY", "C02USDT", e0.state().symMain);
        assertEquals("C03USDT", e0.state().symAux);
        assertEquals(1, ((Number) k0.data.get("legacy.positions")).intValue());
        assertEquals(1, ((Number) k0.data.get("legacy.orders")).intValue());
        assertEquals(1, ((Number) k0.data.get("legacy.algos")).intValue());
        ok(run("K1"));
        assertTrue(mock.position("C02USDT").signum() > 0);
        ok(flattenRun());
        assertEquals(0, mock.position("C02USDT").signum());
        CanaryEngine.Result c = cleanup();
        ok(c);
        assertEquals(0, ((Number) c.data.get("legacy.callsOutside")).intValue());
        assertEquals(0, ((Number) c.data.get("legacy.canaryOutside")).intValue());
        assertEquals(1, ((Number) c.data.get("legacy.positionsEnd")).intValue());
        assertTrue(String.valueOf(c.data.get("legacy.summary")).startsWith("LEGACY vi the K0=1 cuoi=1"));
        // LEGACY nguyen ven, 0 lenh ghi tren symbol LEGACY, cap tai khoan chi doc
        assertEquals(0, new BigDecimal("5").compareTo(mock.position("C00USDT")));
        assertEquals(1, mock.openOrders("C01USDT").size());
        assertEquals(1, mock.openStops("C04USDT").size());
        assertTrue(mock.callLog().toString(), noWriteOn("C00USDT", "C01USDT", "C04USDT", "C05USDT"));
        assertEquals(0, mock.calls("setDualSidePosition"));
    }

    @Test
    public void legacyFillOnMainBetweenStepsIsRedAndNothingIsClosed() throws Exception {
        preflight();
        ok(run("K1"));
        BigDecimal mine = mock.position(MAIN);
        mock.newMarketOrder(MAIN, com.binance.chuyennd.c3live.api.Side.BUY, new BigDecimal("7"), "web_legacy_9", false);   // one-way cong don
        int mo = mock.calls("newMarketOrder");
        CanaryEngine.Result r = run("K2");
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains(CanaryEngine.TRUOT_DO));
        assertEquals("KHONG dong", 0, mine.add(new BigDecimal("7")).compareTo(mock.position(MAIN)));
        assertEquals("0 lenh dong", mo, mock.calls("newMarketOrder"));
        assertTrue("stop canary da huy (tranh dong ca LEGACY)", mock.openStops(MAIN).isEmpty());
        assertTrue(CanaryState.load(dir).aborted.startsWith(CanaryEngine.TRUOT_DO));
        assertEquals(CanaryEngine.TU_CHOI, run("K3").verdict);
        CanaryEngine.Result f = flattenRun();
        assertEquals(f.line(), CanaryEngine.TRUOT, f.verdict);
        assertTrue(f.line(), f.line().contains(CanaryEngine.TRUOT_DO));
        assertEquals("flatten KHONG dong", 0, mine.add(new BigDecimal("7")).compareTo(mock.position(MAIN)));
        assertEquals(mo, mock.calls("newMarketOrder"));
        assertEquals(CanaryEngine.TRUOT, cleanup().verdict);
    }

    @Test
    public void legacyFillOnMainMidStepIsRedAndNothingIsClosed() throws Exception {
        preflight();
        ok(run("K1"));
        BigDecimal mine = mock.position(MAIN);
        final long t0 = now.get();
        final boolean[] fired = {false};
        hook = t -> {
            if (!fired[0] && t - t0 > 90_000L) {
                fired[0] = true;
                mock.newMarketOrder(MAIN, com.binance.chuyennd.c3live.api.Side.BUY, new BigDecimal("7"), "web_legacy_m", false);
            }
        };
        CanaryEngine.Result r = run("K4");   // stop khong kich (gia dung yen) => K4 dang cho thi LEGACY vao MAIN
        hook = t -> { };
        assertTrue("LEGACY da vao giua buoc", fired[0]);
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains(CanaryEngine.TRUOT_DO));
        assertTrue("phat hien nhanh (< 5')", now.get() - t0 < 5 * 60_000L);
        assertEquals("KHONG dong", 0, mine.add(new BigDecimal("7")).compareTo(mock.position(MAIN)));
        assertTrue(mock.openStops(MAIN).isEmpty());
    }

    @Test
    public void legacyRestingOrderOnCanarySymbolClosesCanaryPartOnly() throws Exception {
        preflight();
        ok(run("K1"));
        mock.addRestingOrder(MAIN, "web_legacy_r", com.binance.chuyennd.c3live.api.Side.BUY, new BigDecimal("3"));
        CanaryEngine.Result r = run("K2");
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("ngoai canary"));
        assertEquals("phan canary da dong reduce-only", 0, mock.position(MAIN).signum());
        assertEquals("lenh LEGACY van nguyen", 1, mock.openOrders(MAIN).size());
        assertTrue(CanaryState.load(dir).aborted.startsWith("SCOPE"));
        assertEquals(CanaryEngine.TU_CHOI, run("K3").verdict);
    }

    @Test
    public void accountLevelSettingsAreOnlyRead() throws Exception {
        mock.dualSide = true;   // hedge: canary KHONG doi (§ADD-4 E)
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result k0 = e.preflight();
        e.close();
        assertEquals(k0.line(), CanaryEngine.TRUOT, k0.verdict);
        assertTrue(k0.line(), k0.line().contains("dualSidePosition"));
        CanaryEngine e2 = engine(cfg());
        CanaryEngine.Result s = e2.setup();
        e2.close();
        assertNotEquals(s.line(), CanaryEngine.DAT, s.verdict);
        assertEquals("khong bao gio goi doi cap tai khoan", 0, mock.calls("setDualSidePosition"));
        assertTrue(mock.dualSide);
    }

    // ------------------------------------------------------------------ [3g] sua FAIL A1 tren 3f
    private CanaryEngine.Result runCfg(String step, CanaryEngine.Config c) throws Exception {
        CanaryEngine e = engine(c);
        CanaryEngine.Result r = e.step(step);
        e.close();
        return r;
    }

    @Test
    public void g3LegacySellFillSeenOnStreamMidStepIsUrgentRedNoClose() throws Exception {
        preflight();
        ok(run("K1"));
        BigDecimal mine = mock.position(MAIN);
        final long t0 = now.get();
        final boolean[] fired = {false};
        hook = t -> {
            if (!fired[0] && t - t0 > 90_000L) {
                fired[0] = true;   // LEGACY SELL (khong reduceOnly) cong don one-way vao vi the long canary
                mock.newMarketOrder(MAIN, com.binance.chuyennd.c3live.api.Side.SELL, new BigDecimal("5"), "web_legacy_sell", false);
            }
        };
        CanaryEngine.Result r = run("K4");
        hook = t -> { };
        assertTrue(fired[0]);
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains(CanaryEngine.TRUOT_DO));
        assertEquals("KHONG dong phan con lai", 0, mine.subtract(new BigDecimal("5")).compareTo(mock.position(MAIN)));
        assertTrue("Telegram KHAN CAP", telegram.stream().anyMatch(m -> m.contains("URGENT") && m.contains(CanaryEngine.TRUOT_DO)));
    }

    @Test
    public void g3StopTriggeredBetweenJvmsShrinksLedgerOnlyWithEvidence() throws Exception {
        preflight();
        ok(run("K1"));
        mock.triggerStops(MAIN, new BigDecimal("0.95"));   // khong co JVM (khong stream): stop canary kich
        assertEquals(0, mock.position(MAIN).signum());
        CanaryEngine.Result r = run("K2");
        assertFalse(r.line(), r.line().contains(CanaryEngine.TRUOT_DO));
        CanaryState s = CanaryState.load(dir);
        assertTrue(String.valueOf(s.red), s.red.isEmpty());
    }

    @Test
    public void g3StopFillWithNonCanaryCidMatchedByActualOrderIdAlgoFirst() throws Exception {
        stopFillCase(false);
    }

    @Test
    public void g3StopFillWithNonCanaryCidMatchedByActualOrderIdFillFirst() throws Exception {
        stopFillCase(true);
    }

    private void stopFillCase(boolean after) throws Exception {
        {
            mock.triggeredFillCidPrefix = "autoclose-algo-";   // lenh thuong cua stop KHONG mang c3s-
            mock.algoUpdateAfterFill = after;                  // ALGO_UPDATE (ai) toi truoc / sau khop
            preflight();
            ok(run("K1"));
            final long t0 = now.get();
            final boolean[] fired = {false};
            hook = t -> {
                if (!fired[0] && t - t0 > 60_000L && !mock.openStops(MAIN).isEmpty()) {
                    fired[0] = true;
                    mock.triggerStops(MAIN, new BigDecimal("0.998"));
                }
            };
            CanaryEngine.Result r = run("K4");
            hook = t -> { };
            assertTrue(fired[0]);
            assertFalse("after=" + after + " " + r.line(), r.line().contains(CanaryEngine.TRUOT_DO));
            assertTrue(CanaryState.load(dir).red.isEmpty());
            assertEquals(0, CanaryEngine.dec(CanaryState.load(dir).canaryQty.get(MAIN)).signum());
        }
    }

    @Test
    public void g3SessionCapIsMinOfTwoAndFourMinusPrior() throws Exception {
        preflight();
        CanaryEngine.Config c = cfg();
        c.priorLossUsdt = Double.NaN;
        CanaryEngine.Result r0 = runCfg("K1", c);
        assertEquals(r0.line(), CanaryEngine.TU_CHOI, r0.verdict);
        assertTrue(r0.line(), r0.line().contains("CANARY_PRIOR_LOSS_USDT"));
        c.priorLossUsdt = 3.95d;   // tran phien 0,05 <= 0,10
        CanaryEngine.Result r1 = runCfg("K1", c);
        assertEquals(r1.line(), CanaryEngine.TU_CHOI, r1.verdict);
        assertTrue(r1.line(), r1.line().contains("tran lo phien"));
        assertEquals("0 lenh", 0, mock.calls("newMarketOrder"));
        c.priorLossUsdt = 3.3d;    // tran phien 0,7 => ngan sach (0,7 - 0,1) / 20 = 3 %
        ok(runCfg("K1", c));
        List<com.binance.chuyennd.c3live.api.OrderInfo> s = mock.openStops(MAIN);
        assertEquals(1, s.size());
        double ratio = s.get(0).getStopPrice().doubleValue() / mock.positions().get(0).getEntryPrice().doubleValue();
        assertTrue("stop/entry=" + ratio, ratio > 0.965d && ratio < 0.975d);
    }

    @Test
    public void g3BnbFeeCountedAtMarkOrRefused() throws Exception {
        preflight();
        ok(run("K1"));
        CanaryState s = CanaryState.load(dir);
        s.feeOther.put("BNB", 0.004d);   // phi BNB 0,004 x 600 = 2,4 USDT => cham tran 2
        s.save(dir);
        mock.setPrice("BNBUSDT", new BigDecimal("600"));
        CanaryEngine.Result r = run("K2");
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("tran lo"));
        assertEquals(0, mock.position(MAIN).signum());
    }

    @Test
    public void g3NonStableFeeWithoutPriceStopsSession() throws Exception {
        preflight();
        ok(run("K1"));
        CanaryState s2 = CanaryState.load(dir);
        s2.feeOther.put("XYZ", 1d);   // khong co gia XYZUSDT => khong quy doi duoc => dung + flatten
        s2.save(dir);
        CanaryEngine.Result r2 = run("K2");
        assertEquals(r2.line(), CanaryEngine.TRUOT, r2.verdict);
        assertTrue(r2.line(), r2.line().contains("KHONG quy doi"));
        assertEquals(0, mock.position(MAIN).signum());
    }

    @Test
    public void g3PreAddFourStateLedgerIsZeroAndNothingIsClosed() throws Exception {
        preflight();
        ok(run("K1"));
        BigDecimal mine = mock.position(MAIN);
        CanaryState s = CanaryState.load(dir);
        s.canaryQty.clear();   // phien truoc 3f (tai khoan cu): khong co ledger => 0, KHONG lay so
        s.save(dir);
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result f = e.flatten();
        e.close();
        assertEquals(f.line(), CanaryEngine.TRUOT, f.verdict);
        assertTrue(f.line(), f.line().contains(CanaryEngine.TRUOT_DO));
        assertEquals("KHONG dong vi the khong chung minh la canary", 0, mine.compareTo(mock.position(MAIN)));
    }

    @Test
    public void g3FlattenDoesNotCloseWhenScopeUnreadable() throws Exception {
        preflight();
        ok(run("K1"));
        BigDecimal mine = mock.position(MAIN);
        final boolean[] fail = {false};
        ExchangeGateway raw = (ExchangeGateway) java.lang.reflect.Proxy.newProxyInstance(ExchangeGateway.class.getClassLoader(),
                new Class<?>[]{ExchangeGateway.class}, (p, m, a) -> {
                    if (fail[0] && "positions".equals(m.getName())) {
                        throw new GatewayException(ErrorKind.OTHER, 500, 0, "positionRisk loi (gia lap)", true, 0L, null);
                    }
                    try {
                        return m.invoke(mock, a);
                    } catch (java.lang.reflect.InvocationTargetException ex) {
                        throw ex.getCause();
                    }
                });
        RateGuard rg = new RateGuard(RateGuard.Limits.binanceDefault(), 0.5, 2_000L, rgClock());
        CanaryEngine e = engineRaw(cfg(), raw, rg);
        int mo = mock.calls("newMarketOrder");
        fail[0] = true;
        CanaryEngine.Result f = e.flatten();
        e.close();
        assertEquals(f.line(), CanaryEngine.TRUOT, f.verdict);
        assertTrue(f.line(), f.line().contains("NOREAD"));
        assertFalse("[3h MAJOR-A] doc loi KHONG phai bang chung lan", f.line().contains(CanaryEngine.TRUOT_DO));
        assertEquals("0 lenh dong", mo, mock.calls("newMarketOrder"));
        assertEquals(0, mine.compareTo(mock.position(MAIN)));
        assertFalse("stop bao ve van giu", mock.openStops(MAIN).isEmpty());
        assertTrue("khong luu red", CanaryState.load(dir).red.isEmpty());
        fail[0] = false;   // doc lai duoc => flatten dong binh thuong
        CanaryEngine e2 = engineRaw(cfg(), raw, rg);
        CanaryEngine.Result f2 = e2.flatten();
        e2.close();
        ok(f2);
        assertEquals(0, mock.position(MAIN).signum());
    }

    @Test
    public void g3RealizedLossCountsOnlyCanaryCidFills() throws Exception {
        preflight();
        CanaryState s0 = CanaryState.load(dir);
        double fee0 = s0.cumFeeStable;
        double rp0 = s0.cumRealized;
        CanaryEngine e = engine(cfg());
        String foreign = "{\"e\":\"ORDER_TRADE_UPDATE\",\"E\":1,\"T\":1,\"o\":{\"s\":\"" + MAIN + "\",\"c\":\"web_x\",\"S\":\"SELL\","
                + "\"o\":\"MARKET\",\"x\":\"TRADE\",\"X\":\"FILLED\",\"i\":777,\"l\":\"5\",\"L\":\"1\",\"z\":\"5\",\"ap\":\"1\","
                + "\"n\":\"1.5\",\"N\":\"USDT\",\"rp\":\"-3\",\"R\":false,\"T\":1,\"t\":91}}";
        String canary = foreign.replace("web_x", "c3x-" + MAIN + "-1-1").replace("777", "778").replace("1.5", "0.01")
                .replace("-3", "-0.02").replace("\"t\":91", "\"t\":92");
        e.onStreamText(foreign);
        e.onStreamText(canary);
        e.close();
        CanaryState s = CanaryState.load(dir);
        assertEquals("chi phi lenh canary", fee0 + 0.01d, s.cumFeeStable, 1e-9);
        assertEquals("chi PnL lenh canary", rp0 - 0.02d, s.cumRealized, 1e-9);
    }

    @Test
    public void g3EmptyLegacyFileRefusesK0OnMainAccount() throws Exception {
        legacySizeVal = 0;
        CanaryEngine e = engine(cfg());
        CanaryEngine.Result r = e.preflight();
        e.close();
        assertEquals(r.line(), CanaryEngine.TRUOT, r.verdict);
        assertTrue(r.line(), r.line().contains("legacy_symbols.csv"));
        assertNull(CanaryState.load(dir).tmb0);
    }
}
