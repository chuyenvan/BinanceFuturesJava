package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.api.Ticker24h;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.runtime.C3LiveAccountLock;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.Assert.*;

/** [V12 3] Guard CUNG cua CanaryGateway + luat chon symbol + lock tai khoan con. */
public class CanaryGuardTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    MockExchangeGateway mock;
    CanaryGateway gw;
    final AtomicBoolean lossHit = new AtomicBoolean(false);

    @Before
    public void setUp() throws Exception {
        mock = new MockExchangeGateway();
        mock.exchangeInfo = C3LiveFixtures.info(6);
        for (int i = 0; i < 6; i++) mock.setPrice(C3LiveFixtures.sym(i), BigDecimal.ONE);
        CanaryJournal j = new CanaryJournal(new File(tmp.getRoot(), "j.jsonl"), System::currentTimeMillis);
        gw = new CanaryGateway(mock, new LinkedHashSet<>(Arrays.asList("C00USDT", "C01USDT")), j, () -> 5, lossHit::get);
    }

    private void refused(Runnable r) {
        int n = mock.calls("newMarketOrder") + mock.calls("newStopMarket") + mock.calls("cancelStop") + mock.calls("setLeverage")
                + mock.calls("setMarginType") + mock.calls("cancelOrder") + mock.calls("setDualSidePosition");
        try {
            r.run();
            fail("phai bi TU CHOI");
        } catch (CanaryGateway.GuardException e) {
            assertTrue(e.isDefinitelyNotExecuted());
        }
        int n2 = mock.calls("newMarketOrder") + mock.calls("newStopMarket") + mock.calls("cancelStop") + mock.calls("setLeverage")
                + mock.calls("setMarginType") + mock.calls("cancelOrder") + mock.calls("setDualSidePosition");
        assertEquals("khong goi san", n, n2);
    }

    @Test
    public void notionalAboveCapRefused() {
        refused(() -> gw.newMarketOrder("C00USDT", Side.BUY, new BigDecimal("25.1"), "c3-C00USDT-1-0", false));
        gw.newMarketOrder("C00USDT", Side.BUY, new BigDecimal("25"), "c3-C00USDT-2-0", false);   // dung tran 25
        assertEquals(1, mock.calls("newMarketOrder"));
        mock.setPrice("C01USDT", new BigDecimal("2"));
        refused(() -> gw.newMarketOrder("C01USDT", Side.BUY, new BigDecimal("13"), "c3-C01USDT-3-0", false));   // 26 USDT
    }

    @Test
    public void openTotalAboveCapRefused() {
        gw.newMarketOrder("C00USDT", Side.BUY, new BigDecimal("20"), "c3-C00USDT-1-0", false);
        gw.newMarketOrder("C01USDT", Side.BUY, new BigDecimal("20"), "c3-C01USDT-1-0", false);   // tong 40 = tran
        refused(() -> gw.newMarketOrder("C01USDT", Side.BUY, new BigDecimal("0.1"), "c3-C01USDT-2-0", false));
        // dong (reduce-only) luon duoc
        gw.newMarketOrder("C01USDT", Side.SELL, new BigDecimal("20"), "c3x-C01USDT-1-1", true);
        assertEquals(0, mock.position("C01USDT").signum());
    }

    @Test
    public void otherSymbolsAndForbiddenActionsRefused() {
        refused(() -> gw.newMarketOrder("C05USDT", Side.BUY, BigDecimal.ONE, "c3-C05USDT-1-0", false));
        refused(() -> gw.newMarketOrder("C05USDT", Side.SELL, BigDecimal.ONE, "c3x-C05USDT-1-1", true));
        refused(() -> gw.newStopMarket("C05USDT", Side.SELL, null, BigDecimal.ONE, "c3s-C05USDT-1-1", true));
        refused(() -> gw.cancelStop("C05USDT", "c3s-C05USDT-1-1"));
        refused(() -> gw.cancelOrder("C05USDT", "x"));
        refused(() -> gw.setLeverage("C05USDT", 1));
        refused(() -> gw.setLeverage("C00USDT", 2));
        refused(() -> gw.setMarginType("C00USDT", "ISOLATED"));
        refused(() -> gw.setDualSidePosition(true));
        refused(() -> gw.newMarketOrder("C00USDT", Side.SELL, BigDecimal.ONE, "c3x-C00USDT-1-1", false));   // mo short
        refused(() -> gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3-C00USDT-1-0", true));
        refused(() -> gw.newStopMarket("C00USDT", Side.BUY, null, BigDecimal.ONE, "c3s-C00USDT-1-1", true));
        refused(() -> gw.newStopMarket("C00USDT", Side.SELL, BigDecimal.ONE, BigDecimal.ONE, "c3s-C00USDT-1-1", false));
        assertEquals(13, gw.refusedCalls());
    }

    /** [3c MAJ-C1] stop SELL khong bao gio xa hon -4,5 % so gia vao (dung sai lam tron 2 bp). */
    @Test
    public void stopFartherThanMaxDistFromEntryRefused() {
        gw.newMarketOrder("C00USDT", Side.BUY, new BigDecimal("20"), "c3-C00USDT-1-0", false);   // entry 1
        refused(() -> gw.newStopMarket("C00USDT", Side.SELL, null, new BigDecimal("0.80"), "c3s-C00USDT-1-1", true));
        refused(() -> gw.newStopMarket("C00USDT", Side.SELL, null, new BigDecimal("0.9547"), "c3s-C00USDT-1-2", true));
        refused(() -> gw.newStopMarket("C00USDT", Side.SELL, new BigDecimal("20"), new BigDecimal("0.9"), "c3s-C00USDT-1-3", true));
        gw.newStopMarket("C00USDT", Side.SELL, null, new BigDecimal("0.9550"), "c3s-C00USDT-1-4", true);   // dung -4,5 %
        gw.newStopMarket("C00USDT", Side.SELL, new BigDecimal("20"), new BigDecimal("0.99"), "c3s-C00USDT-1-5", true);
        assertEquals(2, mock.calls("newStopMarket"));
        assertEquals(3, gw.refusedCalls());
    }

    @Test
    public void foreignPositionBlocksOpen() {
        // [3f §ADD-4] LEGACY tren symbol khac: binh thuong; vi the / lenh ngoai canary TREN symbol canary => tu choi
        mock.setPosition("C05USDT", new BigDecimal("3"), BigDecimal.ONE);
        gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3-C00USDT-1-0", false);
        gw.canaryQty = s -> "C00USDT".equals(s) ? BigDecimal.ONE : BigDecimal.ZERO;
        mock.setPosition("C01USDT", new BigDecimal("2"), BigDecimal.ONE);
        refused(() -> gw.newMarketOrder("C01USDT", Side.BUY, BigDecimal.ONE, "c3-C01USDT-1-0", false));
        refused(() -> gw.setLeverage("C01USDT", 1));
        mock.setPosition("C01USDT", BigDecimal.ZERO, BigDecimal.ONE);
        mock.addRestingOrder("C01USDT", "web_1", Side.BUY, BigDecimal.ONE);
        refused(() -> gw.newMarketOrder("C01USDT", Side.BUY, BigDecimal.ONE, "c3-C01USDT-2-0", false));
        refused(() -> gw.setMarginType("C01USDT", "CROSSED"));
        assertEquals(0, new BigDecimal("3").compareTo(mock.position("C05USDT")));
    }

    @Test
    public void nonCanaryCidAndAccountLevelWritesRefused() {
        refused(() -> gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "web_x", false));
        refused(() -> gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3x-C00USDT-1-1", false));
        refused(() -> gw.newMarketOrder("C00USDT", Side.SELL, BigDecimal.ONE, "c3-C00USDT-1-0", true));
        refused(() -> gw.newStopMarket("C00USDT", Side.SELL, null, BigDecimal.ONE, "web_s", true));
        refused(() -> gw.cancelStop("C00USDT", "web_s"));
        refused(() -> gw.cancelOrder("C00USDT", "web_o"));
        refused(() -> gw.setDualSidePosition(false));
        assertEquals(0, mock.calls("setDualSidePosition"));
    }

    @Test
    public void readViewIsScopedToCanarySymbols() {
        mock.setPosition("C05USDT", new BigDecimal("3"), BigDecimal.ONE);
        mock.addRestingOrder("C04USDT", "web_1", Side.BUY, BigDecimal.ONE);
        mock.addRestingStop("C04USDT", "web_2", BigDecimal.ONE, new BigDecimal("0.5"));
        assertTrue(gw.positions().isEmpty());
        assertTrue(gw.openOrders(null).isEmpty());
        assertTrue(gw.openStops(null).isEmpty());
        assertTrue(gw.openOrders("C04USDT").isEmpty());
        assertEquals(1, gw.positionsAll().size());
        assertEquals(1, gw.openOrdersAll().size());
        assertEquals(1, gw.openStopsAll().size());
        for (com.binance.chuyennd.c3live.api.PositionInfo p : gw.account().getPositions()) assertNotEquals("C05USDT", p.getSymbol());
    }

    @Test
    public void lossCapRefusesOpenButAllowsClose() {
        gw.newMarketOrder("C00USDT", Side.BUY, new BigDecimal("10"), "c3-C00USDT-1-0", false);
        lossHit.set(true);
        refused(() -> gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3-C00USDT-2-0", false));
        gw.newMarketOrder("C00USDT", Side.SELL, new BigDecimal("10"), "c3x-C00USDT-1-1", true);
        assertEquals(0, mock.position("C00USDT").signum());
    }

    @Test
    public void readFailureForPriceOrPositionsRefusesOpen() {
        mock.failNext("tickers24h", new GatewayException(com.binance.chuyennd.c3live.api.ErrorKind.OTHER, "x", true));
        refused(() -> gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3-C00USDT-1-0", false));
        mock.failNext("positions", new GatewayException(com.binance.chuyennd.c3live.api.ErrorKind.OTHER, "x", true));
        refused(() -> gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3-C00USDT-2-0", false));
    }

    @Test
    public void injectionsAreClientSideOnly() {
        gw.failPositions = true;
        int p0 = mock.calls("positions");
        try {
            gw.positions();
            fail();
        } catch (GatewayException e) {
            assertTrue(e.getMessage().contains("TIEM"));
        }
        assertEquals("khong goi san", p0, mock.calls("positions"));
        gw.failPositions = false;
        gw.armTimeoutAfterNextOpen();
        try {
            gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3-C00USDT-1-0", false);
            fail();
        } catch (GatewayException e) {
            assertFalse("trang thai khong ro", e.isDefinitelyNotExecuted());
        }
        assertEquals("san DA nhan lenh", 1, mock.calls("newMarketOrder"));
        assertEquals(0, BigDecimal.ONE.compareTo(mock.position("C00USDT")));
        assertFalse("chi 1 lan", gw.timeoutArmed());
        gw.newMarketOrder("C00USDT", Side.BUY, BigDecimal.ONE, "c3-C00USDT-2-0", false);
    }

    @Test(expected = IllegalArgumentException.class)
    public void moreThanTwoSymbolsRejected() {
        new CanaryGateway(mock, new LinkedHashSet<>(Arrays.asList("A", "B", "C")), null, null, null);
    }

    // ------------------------------------------------------------------ luat chon symbol
    @Test
    public void symbolRuleRanksByQuoteVolumeAndFilters() {
        List<SymbolMeta> l = new ArrayList<>();
        l.add(C3LiveFixtures.crypto("AAAUSDT"));
        l.add(C3LiveFixtures.crypto("BBBUSDT"));
        l.add(C3LiveFixtures.crypto("CCCUSDT"));
        l.add(C3LiveFixtures.crypto("DDDUSDT"));
        l.add(C3LiveFixtures.crypto("LEGUSDT"));
        l.add(SymbolMeta.builder("BIGUSDT").pair("BIGUSDT").status("TRADING").contractType("PERPETUAL").baseAsset("BIG")
                .quoteAsset("USDT").marginAsset("USDT").underlyingType("COIN").underlyingSubType(Collections.emptyList())
                .onboardDate(1L).deliveryDate(4_133_404_800_000L).tickSize(new BigDecimal("0.0001")).minPrice(new BigDecimal("0.0001"))
                .maxPrice(new BigDecimal("1000")).stepSize(new BigDecimal("0.1")).minQty(new BigDecimal("0.1"))
                .maxQty(new BigDecimal("1000")).marketStepSize(new BigDecimal("0.1")).marketMinQty(new BigDecimal("0.1"))
                .marketMaxQty(new BigDecimal("1000")).minNotional(new BigDecimal("20")).build());   // MIN_NOTIONAL > 10
        l.add(C3LiveFixtures.tradfi("TSLAUSDT"));
        ExchangeInfo ei = new ExchangeInfo(0L, Collections.emptyList(), l);
        Map<String, BigDecimal> vol = new HashMap<>();
        vol.put("AAAUSDT", new BigDecimal("500"));
        vol.put("BBBUSDT", new BigDecimal("900"));
        vol.put("CCCUSDT", new BigDecimal("500"));
        vol.put("DDDUSDT", new BigDecimal("2000"));   // tick/gia qua lon (gia 0.5 => tick 0,02 %)
        vol.put("LEGUSDT", new BigDecimal("5000"));   // LEGACY
        vol.put("BIGUSDT", new BigDecimal("9000"));
        vol.put("TSLAUSDT", new BigDecimal("99999"));
        List<Ticker24h> t = new ArrayList<>();
        for (Map.Entry<String, BigDecimal> e : vol.entrySet()) {
            t.add(new Ticker24h(e.getKey(), "DDDUSDT".equals(e.getKey()) ? new BigDecimal("0.5") : BigDecimal.ONE, e.getValue(), 0L));
        }
        long now = 1_793_000_000_000L;
        SymbolPicker.Pick p = SymbolPicker.pick(ei, t, "LEGUSDT"::equals, now);
        assertEquals("BBBUSDT", p.main);
        assertEquals("hoa quoteVolume => theo ten", "AAAUSDT", p.aux);
        assertEquals(3, p.eligible);
        assertEquals("CCCUSDT", p.top.get(2).symbol);
        assertTrue(p.rejectCounts.toString(), p.rejectCounts.containsKey("LEGACY"));
        assertTrue(p.rejectCounts.containsKey("MIN_NOTIONAL_GT_10"));
        assertTrue(p.rejectCounts.containsKey("TICK_GT_0.01PCT"));
        assertTrue(p.rejectCounts.containsKey("UNIVERSE_TRADFI"));
        assertTrue(SymbolPicker.whyNot("LEGUSDT", ei, t, "LEGUSDT"::equals, now).isPresent());
        assertFalse(SymbolPicker.whyNot("BBBUSDT", ei, t, s -> false, now).isPresent());
    }

    // ------------------------------------------------------------------ lock tai khoan con
    @Test
    public void accountLockIsExclusiveAndCanaryRefusesWhileRuntimeHoldsIt() throws Exception {
        File f = new File(tmp.getRoot(), "run/c3live_account.lock");
        C3LiveAccountLock runtime = C3LiveAccountLock.tryAcquire(f, "c3live-runtime");
        assertNotNull(runtime);
        assertNull("canary khong lay duoc khi runtime giu", C3LiveAccountLock.tryAcquire(f, "c3live-canary"));
        Map<String, String> env = new HashMap<>();
        env.put(C3LiveAccountLock.KEY_FILE, f.getPath());
        env.put("CANARY_DIR", new File(tmp.getRoot(), "run/canary").getPath());
        env.put("LIVE_C3_KEYS_FILE", new File(tmp.getRoot(), "khong_co_keys.env").getPath());
        int code = C3LiveCanary.run(new String[]{"preflight"}, env::get);
        assertEquals(2, code);
        assertTrue(C3LiveCanary.lastLine, C3LiveCanary.lastLine.contains("lock tai khoan con dang bi giu"));
        runtime.release();
        int code2 = C3LiveCanary.run(new String[]{"preflight"}, env::get);
        assertEquals(2, code2);
        assertTrue("sau khi nha lock: qua buoc lock, dung o key", C3LiveCanary.lastLine.contains("khong tao duoc client"));
        C3LiveAccountLock again = C3LiveAccountLock.tryAcquire(f, "x");
        assertNotNull("lenh canary ket thuc => da nha lock", again);
        again.release();
    }

    // ------------------------------------------------------------------ [V12 3b] env sach (khong Aerospike/symbol_mapper/Redis)
    @Test
    public void canaryRefusesUncleanEnvBeforeLockOrClient() throws Exception {
        File f = new File(tmp.getRoot(), "run/c3live_account.lock");
        for (String k : C3LiveCanary.FORBIDDEN_ENV) {
            Map<String, String> env = new HashMap<>();
            env.put(C3LiveAccountLock.KEY_FILE, f.getPath());
            env.put("CANARY_DIR", new File(tmp.getRoot(), "run/canary").getPath());
            env.put(k, "LIVE_TS_MKT_EXT".equals(k) ? "1" : "c3_shadow");
            for (String cmd : new String[]{"preflight", "status", "flatten"}) {
                int code = C3LiveCanary.run(new String[]{cmd}, env::get);
                assertEquals(k + " " + cmd, 2, code);
                assertTrue(C3LiveCanary.lastLine, C3LiveCanary.lastLine.contains("env khong sach: " + k));
            }
        }
        assertFalse("env bi tu choi TRUOC lock: chua tao file lock", f.exists());
        assertFalse("khong tao thu muc canary", new File(tmp.getRoot(), "run/canary").exists());
        Map<String, String> clean = new HashMap<>();
        clean.put("LIVE_PROFILE", "  ");   // rong = sach
        assertNull(C3LiveCanary.isolationProblem(clean::get));
    }
}
