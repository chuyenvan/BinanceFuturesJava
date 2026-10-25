package com.binance.chuyennd.c3live.guard;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.SymbolConfig;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

/** [V12 C5] 4 trang thai sai (multiAssets, dualSide, marginType, leverage) x (sua duoc / van sai) + fail-closed + cache. */
public class AccountModeGuardTest {
    final List<String> alerts = new ArrayList<>();
    long now = 1_000_000L;

    AccountModeGuard guard(MockExchangeGateway m) { return new AccountModeGuard(m, 1, alerts::add, () -> now, 60_000L); }

    @Test
    public void allGood() {
        MockExchangeGateway m = new MockExchangeGateway();
        AccountModeGuard g = guard(m);
        assertTrue(g.checkGlobal().isOk());
        assertTrue(g.checkSymbol("BTCUSDT").isOk());
        assertTrue(g.isSymbolCleared("BTCUSDT"));
        assertEquals(0, m.calls("setDualSidePosition") + m.calls("setMarginType") + m.calls("setLeverage"));
        assertTrue(alerts.isEmpty());
    }

    @Test
    public void multiAssetsOffBlocksEverythingAndIsNeverChangedAutomatically() {
        MockExchangeGateway m = new MockExchangeGateway();
        m.multiAssets = false;
        AccountModeGuard g = guard(m);
        AccountModeGuard.Result r = g.checkGlobal();
        assertFalse(r.isOk());
        assertTrue(g.isGlobalBlocked());
        assertTrue(r.getActions().isEmpty());
        assertFalse(g.checkSymbol("BTCUSDT").isOk());
        assertFalse(g.isSymbolCleared("BTCUSDT"));
        assertFalse(m.multiAssets); // khong tu doi
        assertEquals(2, alerts.size());
        assertTrue(alerts.get(0).contains("multiAssetsMargin=false"));
    }

    @Test
    public void dualSideFixedOnceOrBlocked() {
        MockExchangeGateway m = new MockExchangeGateway();
        m.dualSide = true;
        AccountModeGuard g = guard(m);
        AccountModeGuard.Result r = g.checkGlobal();
        assertTrue(r.toString(), r.isOk());
        assertEquals(1, m.calls("setDualSidePosition"));
        assertFalse(m.dualSide);
        assertTrue(alerts.isEmpty());

        MockExchangeGateway s = new MockExchangeGateway();
        s.dualSide = true;
        s.stickDualSide = true;
        AccountModeGuard g2 = guard(s);
        assertFalse(g2.checkGlobal().isOk());
        assertEquals("dat lai DUNG 1 lan", 1, s.calls("setDualSidePosition"));
        assertTrue(g2.isGlobalBlocked());
        assertEquals(1, alerts.size());
    }

    @Test
    public void marginTypeIsolatedFixedOnceOrBlocksOnlyThatSymbol() {
        MockExchangeGateway m = new MockExchangeGateway();
        m.setSymbolConfig("ETHUSDT", SymbolConfig.ISOLATED, 1);
        AccountModeGuard g = guard(m);
        g.checkGlobal();
        AccountModeGuard.Result r = g.checkSymbol("ETHUSDT");
        assertTrue(r.toString(), r.isOk());
        assertEquals(1, m.calls("setMarginType"));
        assertEquals(1, r.getActions().size());

        MockExchangeGateway s = new MockExchangeGateway();
        s.setSymbolConfig("ETHUSDT", SymbolConfig.ISOLATED, 1);
        s.stickMarginType = true;
        AccountModeGuard g2 = guard(s);
        g2.checkGlobal();
        assertFalse(g2.checkSymbol("ETHUSDT").isOk());
        assertEquals(1, s.calls("setMarginType"));
        assertTrue(g2.checkSymbol("BTCUSDT").isOk());
        assertFalse(g2.isGlobalBlocked());
        assertFalse(g2.isSymbolCleared("ETHUSDT"));
        assertTrue(g2.isSymbolCleared("BTCUSDT"));
        assertTrue(g2.blockedSymbols().contains("ETHUSDT"));
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).contains("ETHUSDT") && alerts.get(0).contains("CROSSED"));
    }

    @Test
    public void leverageNotOneFixedOnceOrBlocked() {
        MockExchangeGateway m = new MockExchangeGateway();
        m.setSymbolConfig("SOLUSDT", SymbolConfig.CROSSED, 5);
        AccountModeGuard g = guard(m);
        g.checkGlobal();
        assertTrue(g.checkSymbol("SOLUSDT").isOk());
        assertEquals(1, m.calls("setLeverage"));
        assertEquals(1, m.symbolConfig("SOLUSDT").getLeverage());

        MockExchangeGateway s = new MockExchangeGateway();
        s.setSymbolConfig("SOLUSDT", SymbolConfig.CROSSED, 5);
        s.stickLeverage = true;
        AccountModeGuard g2 = guard(s);
        g2.checkGlobal();
        AccountModeGuard.Result r = g2.checkSymbol("SOLUSDT");
        assertFalse(r.isOk());
        assertEquals(1, s.calls("setLeverage"));
        assertTrue(r.getProblems().get(0).contains("leverage=5"));
    }

    @Test
    public void readErrorsFailClosed() {
        MockExchangeGateway m = new MockExchangeGateway();
        m.failNext("multiAssetsMargin", new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, "t", false));
        AccountModeGuard g = guard(m);
        assertFalse(g.checkGlobal().isOk());
        assertTrue(g.isGlobalBlocked());
        m.failNext("symbolConfig", new GatewayException(ErrorKind.RATE_LIMIT, "r", true));
        now += 61_000L;
        AccountModeGuard.Result r = g.checkSymbol("BTCUSDT"); // global kiem lai -> OK, symbolConfig loi -> BLOCKED
        assertFalse(r.isOk());
        assertFalse(g.isGlobalBlocked());
        assertTrue(g.checkSymbol("BTCUSDT").isOk());
    }

    @Test
    public void clearedSymbolCachedAndGlobalRecheckedAfterTtl() {
        MockExchangeGateway m = new MockExchangeGateway();
        AccountModeGuard g = guard(m);
        g.checkGlobal();
        for (int i = 0; i < 24; i++) assertTrue(g.checkSymbol("S" + i + "USDT").isOk());
        assertEquals("dot 24 leg: 1 lan kiem toan cuc", 1, m.calls("multiAssetsMargin"));
        int before = m.totalCalls();
        assertTrue(g.checkSymbol("S0USDT").isOk());
        assertEquals("symbol da qua: khong goi san", before, m.totalCalls());
        now += 61_000L;
        m.multiAssets = false; // ai do tat Multi-Assets
        assertFalse(g.checkSymbol("S0USDT").isOk());
        assertTrue(g.isGlobalBlocked());
        g.resetSymbol("S1USDT");
        assertFalse(g.isSymbolCleared("S1USDT"));
    }

    // ------------------------------------------------------------------ [2c MIN-5] nap san symbolConfig toan universe

    private static java.util.Set<String> universe(int n) {
        java.util.Set<String> u = new java.util.TreeSet<>();
        for (int i = 0; i < n; i++) u.add(com.binance.chuyennd.c3live.entry.C3LiveFixtures.sym(i));
        return u;
    }

    @Test
    public void prefetchMakesBurstOf24LegsCallNoPerSymbolRest() {
        MockExchangeGateway m = new MockExchangeGateway();
        m.exchangeInfo = com.binance.chuyennd.c3live.entry.C3LiveFixtures.info(30);
        AccountModeGuard g = guard(m);
        g.checkGlobal();
        assertEquals(30, g.prefetch(universe(30)));
        assertEquals(1, m.calls("symbolConfigs"));
        for (int i = 0; i < 24; i++) assertTrue(g.checkSymbol(com.binance.chuyennd.c3live.entry.C3LiveFixtures.sym(i)).isOk());
        assertEquals("dot 24 leg: 0 REST symbolConfig tung symbol", 0, m.calls("symbolConfig"));
        // het TTL toan cuc (60 s): 1 lan kiem toan cuc, van 0 REST symbolConfig nho cache nap san (<= 1h)
        now += 61_000L;
        assertTrue(g.checkSymbol(com.binance.chuyennd.c3live.entry.C3LiveFixtures.sym(25)).isOk());
        assertEquals(0, m.calls("symbolConfig"));
        // nap lai moi gio
        assertEquals(-1, g.prefetchIfDue(universe(30)));
        now += 3_600_000L;
        assertEquals(30, g.prefetchIfDue(universe(30)));
        assertEquals(2, m.calls("symbolConfigs"));
    }

    @Test
    public void prefetchedWrongConfigStillFixedAtFirstLegAndErrorsFallBack() {
        MockExchangeGateway m = new MockExchangeGateway();
        m.exchangeInfo = com.binance.chuyennd.c3live.entry.C3LiveFixtures.info(5);
        m.setSymbolConfig("C02USDT", SymbolConfig.ISOLATED, 3);
        AccountModeGuard g = guard(m);
        g.checkGlobal();
        assertEquals(4, g.prefetch(universe(5)));
        AccountModeGuard.Result r = g.checkSymbol("C02USDT");   // khong nam trong cache OK => kiem + sua nhu cu
        assertTrue(r.toString(), r.isOk());
        assertEquals(1, m.calls("setMarginType"));
        assertEquals(1, m.calls("setLeverage"));
        // nap san loi => giu cache cu, thu lai sau 5'
        m.failNext("symbolConfigs", new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, "t", false));
        now += 3_600_000L;
        assertEquals(-1, g.prefetchIfDue(universe(5)));
        assertEquals(-1, g.prefetchIfDue(universe(5)));   // chua toi 5'
        now += 300_000L;
        assertEquals(5, g.prefetchIfDue(universe(5)));
    }
}
