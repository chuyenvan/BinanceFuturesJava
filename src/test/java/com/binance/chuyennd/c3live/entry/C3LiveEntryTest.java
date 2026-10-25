package com.binance.chuyennd.c3live.entry;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.Test;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 C1/C4/C5/C8] C3LiveEntry: thu tu cong, sizing U_MAX (throttle 1 - U/U_MAX dung TradeUtils.managerBudget toi 1e-6),
 * tran 4,5 %, DCA grid tren so THAT, guard trung coin, LEGACY, sizing fail => dong SKIP.
 */
public class C3LiveEntryTest {

    static final long NOW = 1_792_900_000_000L;
    static final long BAR = NOW - 60_000L;

    static final class Setup {
        final MockExchangeGateway gw = new MockExchangeGateway();
        final AtomicLong now = new AtomicLong(NOW);
        final LiveBookC3 book = new LiveBookC3(null, 1.0);
        final ExchangeInfo ei;
        final SymbolUniverseLive uni;
        final AccountModeGuard guard;
        final SymbolRules rules;
        final List<String> audit = new ArrayList<>();
        final List<String> fills = new ArrayList<>();
        final C3LiveOrderExecutor ex;
        boolean armed = true;
        boolean allow = true;
        boolean push = true;
        Double capital = 10_000d;
        final Set<String> legacy = new HashSet<>();

        Setup(int n) {
            ei = C3LiveFixtures.info(n);
            gw.exchangeInfo = ei;
            for (int i = 0; i < n; i++) gw.setPrice(C3LiveFixtures.sym(i), BigDecimal.ONE);
            uni = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> ei, m -> { });
            uni.apply(ei, NOW);
            guard = new AccountModeGuard(gw, m -> { });
            rules = new SymbolRules(ei, NOW);
            ex = new C3LiveOrderExecutor(gw, book, null, (s, b, f, r) -> fills.add(s), now::get, ms -> now.addAndGet(ms),
                    10_000L, 3, Runnable::run);
        }

        C3LiveEntry.Builder builder() {
            return C3LiveEntry.builder().book(book)
                    .killSwitch(new C3LiveEntry.KillSwitchView() {
                        public boolean armed() { return armed; }
                        public boolean allowNewEntry(String s) { return allow; }
                    })
                    .universe(uni).modeGuard(guard).rules(() -> rules).capital(() -> capital).legacy(legacy::contains)
                    .budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null))
                    .legBudgetFn((b, i) -> b)
                    .gridDue((f, p, n) -> n == 1 && p <= f * 0.5f)
                    .executor(ex).audit(new OrderAuditLog(OrderAuditLog.LIVE_TAG, audit::add))
                    .pushAllowed(() -> push).dcaGridEnabled(true).sizeCapOfEquity(0.045f);
        }
    }

    static C3LiveEntry.LegInput leg(String sym, boolean dca, double px) {
        return new C3LiveEntry.LegInput(sym, dca ? "DCA_LEVEL1" : "BIG_DOWN", dca, BAR, px, px, 1f, false);
    }

    @Test
    public void twentyFourCandidatesThrottleMatchesManagerBudgetAndUmax() {
        float fb = Configs.F_BASE;
        try {
            Configs.F_BASE = 0.2f;   // ep throttle tien sat U_MAX trong 24 leg
            Setup s = new Setup(24);
            C3LiveEntry e = s.builder().sizeCapOfEquity(1.0f).build();   // tran 4,5 % khong rang buoc: do throttle thuan
            double equity = 10_000d;
            double ladder = Configs.dcaGridTotalWeight() > 0f ? Configs.dcaGridTotalWeight() : 1d;
            double sum = 0d;
            int submitted = 0;
            for (int k = 0; k < 24; k++) {
                C3LiveEntry.Result r = e.onLeg(leg(C3LiveFixtures.sym(k), false, 1.0), NOW);
                if (r.outcome != C3LiveEntry.Outcome.SUBMITTED) {
                    assertTrue(r.toString(), r.outcome == C3LiveEntry.Outcome.U_MAX
                            || r.outcome == C3LiveEntry.Outcome.BUDGET_SMALL);
                    continue;
                }
                submitted++;
                // U truoc leg k = margin (pending+confirmed) cac leg truoc / equity (doc lap: tong notional da giu)
                assertEquals(sum, r.marginBefore, 1e-6);
                double expectedThrottle = 1d - (sum / equity) / Configs.U_MAX;
                double actualThrottle = r.budget / (equity * Configs.F_BASE / ladder);
                assertEquals("throttle leg " + k, expectedThrottle, actualThrottle, 1e-6);
                double notional = r.qty.doubleValue() * 1.0;
                assertTrue(notional <= r.budget + 1e-9);
                assertTrue(r.budget - notional < 0.1 + 1e-9);   // round down 1 step (0.1 x gia 1)
                sum += notional;
            }
            assertTrue(submitted >= 20);
            assertEquals(sum, s.book.marginUsed(), 1e-6);
            assertTrue("tong margin " + sum + " > U_MAX*equity", sum <= Configs.U_MAX * equity + 1e-9);
            assertEquals(submitted, s.gw.calls("newMarketOrder"));
        } finally {
            Configs.F_BASE = fb;
        }
    }

    @Test
    public void defaultConfigCapsAt45PctAndSumBelowUmax() {
        Setup s = new Setup(24);
        C3LiveEntry e = s.builder().build();
        double sum = 0d;
        for (int k = 0; k < 24; k++) {
            C3LiveEntry.Result r = e.onLeg(leg(C3LiveFixtures.sym(k), false, 1.0), NOW);
            assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.outcome);
            assertTrue(r.budget <= 0.045 * 10_000 + 1e-6);
            sum += r.qty.doubleValue();
        }
        assertTrue(sum <= 6_000d);
        assertEquals(24, s.book.openCount());
        assertEquals(24, s.fills.size());
    }

    @Test
    public void capitalIsMinPilotAndEquity() {
        Setup s = new Setup(2);
        s.capital = 5_000d;   // = min(pilot 10 000, tmb 5 000) do C3LiveEquity tinh
        C3LiveEntry.Result r = s.builder().sizeCapOfEquity(1f).build().onLeg(leg(C3LiveFixtures.sym(0), false, 1.0), NOW);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.outcome);
        double ladder = Configs.dcaGridTotalWeight() > 0f ? Configs.dcaGridTotalWeight() : 1d;
        assertEquals(5_000d * Configs.F_BASE / ladder, r.budget, 1e-3);
    }

    @Test
    public void gateOrderKillSwitchUniverseModeGuard() {
        Setup s = new Setup(4);
        C3LiveEntry e = s.builder().build();
        s.push = false;
        assertEquals(C3LiveEntry.Outcome.PUSH_OFF, e.onLeg(leg(C3LiveFixtures.sym(0), false, 1), NOW).outcome);
        s.push = true;
        s.armed = false;
        assertEquals(C3LiveEntry.Outcome.KS_NOT_ARMED, e.onLeg(leg(C3LiveFixtures.sym(0), false, 1), NOW).outcome);
        s.armed = true;
        s.allow = false;
        // latch chan ca symbol TradFi (kill-switch kiem TRUOC universe)
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, e.onLeg(leg("TSLAUSDT", false, 1), NOW).outcome);
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, e.onLeg(leg(C3LiveFixtures.sym(0), true, 1), NOW).outcome);
        s.allow = true;
        // TradFi / khong niem yet => NOT_BUYABLE, KHONG goi REST mode guard
        s.gw.multiAssets = false;
        assertEquals(C3LiveEntry.Outcome.NOT_BUYABLE, e.onLeg(leg("TSLAUSDT", false, 100), NOW).outcome);
        assertEquals(C3LiveEntry.Outcome.NOT_BUYABLE, e.onLeg(leg("NOPEUSDT", false, 1), NOW).outcome);
        assertEquals(0, s.gw.calls("multiAssetsMargin"));
        // multiAssets=false => AccountModeGuard chan (khong tu doi)
        assertEquals(C3LiveEntry.Outcome.MODE_GUARD, e.onLeg(leg(C3LiveFixtures.sym(0), false, 1), NOW).outcome);
        assertEquals(0, s.gw.calls("newMarketOrder"));
        s.gw.multiAssets = true;
        AccountModeGuard fresh = new AccountModeGuard(s.gw, m -> { });
        C3LiveEntry e2 = s.builder().modeGuard(fresh).build();
        s.legacy.add(C3LiveFixtures.sym(1));
        assertEquals(C3LiveEntry.Outcome.LEGACY, e2.onLeg(leg(C3LiveFixtures.sym(1), false, 1), NOW).outcome);
        s.capital = null;
        assertEquals(C3LiveEntry.Outcome.NO_EQUITY, e2.onLeg(leg(C3LiveFixtures.sym(0), false, 1), NOW).outcome);
        s.capital = 10_000d;
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, e2.onLeg(leg(C3LiveFixtures.sym(0), false, 1), NOW).outcome);
        // guard trung coin thay vi the THAT
        assertEquals(C3LiveEntry.Outcome.HOLDING, e2.onLeg(leg(C3LiveFixtures.sym(0), false, 1), NOW).outcome);
        assertEquals(1, s.gw.calls("newMarketOrder"));
        assertTrue(e2.counts().get(C3LiveEntry.Outcome.SUBMITTED) == 1L);
    }

    @Test
    public void dcaGridOnRealBook() {
        Setup s = new Setup(3);
        C3LiveEntry e = s.builder().build();
        String a = C3LiveFixtures.sym(0);
        assertEquals(C3LiveEntry.Outcome.DCA_NOT_HOLDING, e.onLeg(leg(a, true, 0.4), NOW).outcome);
        C3LiveEntry.Result r0 = e.onLeg(leg(a, false, 1.0), NOW);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r0.outcome);
        assertTrue(r0.cid.endsWith("-0"));
        assertEquals(C3LiveEntry.Outcome.DCA_NOT_DUE, e.onLeg(leg(a, true, 0.8), NOW).outcome);
        C3LiveEntry.LegInput t3 = new C3LiveEntry.LegInput(a, "DCA_LEVEL1", true, BAR, 0.4, 0.4, 0.5f, true);
        assertEquals(C3LiveEntry.Outcome.TIER3_DCA, e.onLeg(t3, NOW).outcome);
        C3LiveEntry.Result r1 = e.onLeg(leg(a, true, 0.4), NOW + 60_000L);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r1.outcome);
        assertTrue(r1.cid, r1.cid.endsWith("-1"));
        assertEquals(2, s.book.legCount(a));
        // bac 2 khong den (gridDue chi bac 1) va cid moi khac cid cu
        assertEquals(C3LiveEntry.Outcome.DCA_NOT_DUE, e.onLeg(leg(a, true, 0.1), NOW + 120_000L).outcome);
        assertNotEquals(r0.cid, r1.cid);
        // DCA tat => DCA_OFF
        C3LiveEntry off = s.builder().dcaGridEnabled(false).build();
        assertEquals(C3LiveEntry.Outcome.DCA_OFF, off.onLeg(leg(a, true, 0.4), NOW).outcome);
    }

    @Test
    public void sizingFailureSkipsLegWithAuditLine() {
        Setup s = new Setup(2);
        C3LiveEntry e = s.builder().build();
        // gia 1e-6 => qty > maxQty => BO leg (khong cat nho, khong noi budget)
        C3LiveEntry.Result r = e.onLeg(leg(C3LiveFixtures.sym(0), false, 0.000001), NOW);
        assertEquals(C3LiveEntry.Outcome.SIZING, r.outcome);
        assertFalse(s.book.isHolding(C3LiveFixtures.sym(0)));
        assertEquals(1, s.audit.size());
        assertTrue(s.audit.get(0), s.audit.get(0).startsWith("[C3-LIVE-ORDER]"));
        assertTrue(s.audit.get(0), s.audit.get(0).contains("status=SKIP"));
        assertTrue(s.audit.get(0), s.audit.get(0).contains("reason=sizing:ABOVE_MAX_QTY"));
        assertEquals(0, s.gw.calls("newMarketOrder"));
    }
}
