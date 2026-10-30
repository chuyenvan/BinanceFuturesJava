package com.binance.chuyennd.c3live.scope;

import com.binance.chuyennd.c3live.adapter.DryGateway;
import com.binance.chuyennd.c3live.adapter.GatewayFactory;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.risk.C3MainEquity;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 R4 R9] (i) dry tren tai khoan chinh: CUNG view / pham vi / von ao (C3MainEquity) / loc stream; 0 lenh that (DryGateway
 * khong mang, khong key; GatewayFactory DRY khong tao C3LiveClient, khong RateGuard).
 */
public class C3DryMainAccountTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void dryModeSendsZeroRealOrdersAndUsesSameScope() throws Exception {
        long t0 = 1_792_900_020_000L;
        AtomicLong now = new AtomicLong(t0);
        // GatewayFactory DRY: khong doc key, khong client that, khong rate guard
        Map<String, String> env = new HashMap<>();
        env.put("LIVE_C3_KEYS_FILE", new File(tmp.getRoot(), "khong_ton_tai.env").getPath());
        GatewayFactory.Result gr = GatewayFactory.create(GatewayFactory.Mode.DRY, env::get, s -> BigDecimal.ONE, new BigDecimal("10000"),
                now::get, OrderAuditLog.dry());
        assertTrue(gr.gateway instanceof DryGateway);
        assertNull(gr.rateGuard);

        ExchangeInfo ei = C3LiveFixtures.info(10);
        List<String> audit = new ArrayList<>();
        OrderAuditLog log = new OrderAuditLog(OrderAuditLog.DRY_TAG, audit::add);
        Map<String, BigDecimal> refs = new HashMap<>();
        for (int i = 0; i < 10; i++) refs.put(C3LiveFixtures.sym(i), BigDecimal.ONE);
        DryGateway dry = new DryGateway(() -> ei, refs::get, new BigDecimal("10000"), log, now::get);
        LiveBookC3 book = new LiveBookC3(new File(tmp.getRoot(), "run/c3live_book.json"), 1.0);
        C3Scope scope = new C3Scope(book, now::get, new File(tmp.getRoot(), "run/merged.txt"));
        C3ScopedGateway sgw = new C3ScopedGateway(dry, scope, now::get, null);
        sgw.setBook(book);
        FillAccounting acct = new FillAccounting(book, sgw, log, null, x -> { }, null, now::get, null);
        C3StreamScope ss = new C3StreamScope(scope, book, now::get);
        dry.setEventSink(txt -> {
            String f = ss.filter(txt);
            if (f != null) acct.dispatch(UserStreamEvents.parse(f));
        });
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(sgw, book, null, null, now::get, ms -> now.addAndGet(ms), 10_000L, 3,
                Runnable::run);
        C3MainEquity eq = new C3MainEquity(sgw, book, scope, 10_000d, new File(tmp.getRoot(), "run/eq.json"), "dry", 0L, now::get,
                null, x -> { });
        C3LegacyRefresher ref = new C3LegacyRefresher(sgw, scope, null, null, x -> { }, now::get);
        assertTrue(ref.refreshNow());
        assertEquals(0, scope.legacyPositionCount());
        SymbolUniverseLive uni = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> ei, x -> { });
        uni.apply(ei, now.get());
        C3LiveEntry entry = C3LiveEntry.builder().book(book)
                .killSwitch(new C3LiveEntry.KillSwitchView() {
                    public boolean armed() { return true; }
                    public boolean allowNewEntry(String s) { return true; }
                })
                .universe(uni).modeGuard(new AccountModeGuard(sgw, x -> { }).globalPolicy(false, false))
                .rules(() -> new SymbolRules(ei, t0)).capital(eq::capital).legacy(s -> scope.entryBlocked(s, now.get()))
                .budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null)).legBudgetFn((b, i) -> b)
                .gridDue((f, px, n) -> false).executor(ex).audit(log).pushAllowed(() -> true).dcaGridEnabled(true)
                .sizeCapOfEquity(0.045f).build();
        String s = C3LiveFixtures.sym(1);
        C3LiveEntry.Result r = entry.onLeg(new C3LiveEntry.LegInput(s, "BIG_DOWN", false, t0, 1.0, 1.0, 1f, false, 0.5f, 1),
                now.get());
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.outcome);
        assertEquals("von ao = C3_CAPITAL", 10_000d, r.capital, 1e-6);
        assertTrue(book.cluster(s).isPresent());
        assertTrue(book.cluster(s).get().confirmedQty.signum() > 0);
        assertEquals("view pham vi c3 tren dry", 1, sgw.positions().size());
        assertFalse(audit.isEmpty());
        for (String line : audit) assertTrue(line, line.startsWith(OrderAuditLog.DRY_TAG));
        try {
            sgw.setDualSidePosition(false);
            fail();
        } catch (C3ScopedGateway.ScopeRefusal e) {
            assertTrue(e.isDefinitelyNotExecuted());
        }
        assertTrue(eq.c3Equity() > 9_000d);
        assertEquals("dry", dry.name());
    }
}
