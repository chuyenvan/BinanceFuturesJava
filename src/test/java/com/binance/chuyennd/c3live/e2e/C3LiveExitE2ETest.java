package com.binance.chuyennd.c3live.e2e;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.exit.TrailingStopManager;
import com.binance.chuyennd.c3live.fill.FillAccounting;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.binance.chuyennd.c3live.recon.Reconciler;
import com.binance.chuyennd.c3live.risk.C3LiveEquity;
import com.binance.chuyennd.c3live.risk.C3LiveFlattener;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 C12 vong 2b] Mock e2e DAY DU (chay CI): mo -> DCA -> arm -> doi stop xN -> stop khop; mo -> time-stop; mo -> X14 gia
 * han -> dong; restart giua chung; kill-switch C2/C3/C4/A40; mat user stream (fallback REST). Thanh phan THAT:
 * KillSwitchEngine (ACT + C4 cong suat + C3 tu go), C3LiveEntry, executor idempotent, LiveBookC3 (persist), C3LiveFlattener,
 * TrailingStopManager, FillAccounting (su kien san dang user stream), Reconciler. San = MockExchangeGateway.
 */
public class C3LiveExitE2ETest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_020_000L;
    static final long MIN = 60_000L;
    static final long H = 3_600_000L;

    final class Rig {
        final AtomicLong now = new AtomicLong(T0);
        final MockExchangeGateway gw = new MockExchangeGateway();
        final ExchangeInfo ei = C3LiveFixtures.info(30);
        final List<String> alerts = new ArrayList<>();
        final List<String> ksLines = new ArrayList<>();
        final AtomicBoolean defer = new AtomicBoolean(false);
        final File bookFile = new File(tmp.getRoot(), "run/c3live_book.json");
        KillSwitchEngine ks;
        LiveBookC3 book;
        FillAccounting acct;
        Reconciler rec;
        C3LiveOrderExecutor ex;
        C3LiveEntry entry;
        C3LiveFlattener flat;
        TrailingStopManager mgr;
        C3LiveEquity eq;
        int bar;

        Rig() {
            gw.exchangeInfo = ei;
            gw.dynamicAccount = true;
            for (int i = 0; i < 30; i++) gw.setPrice(C3LiveFixtures.sym(i), new BigDecimal("1"));
            KillSwitchEngine.Params p = new KillSwitchEngine.Params();
            p.c2Signed = true;
            p.latchFile = new File(tmp.getRoot(), "run/killsw_latch.json");
            p.resetFile = new File(tmp.getRoot(), "run/killsw_reset.req");
            p.autoReleaseMs = 30 * MIN;
            p.autoReleaseCodes.add("C3");
            p.c4Capacity = true;
            ks = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", new KillSwitchEngine.Sink() {
                public void info(String m) { ksLines.add(m); }
                public void warn(String m) { ksLines.add(m); }
            }, null, () -> 10_000d, () -> Configs.U_MAX, T0, p);
            ks.setAlert(alerts::add);
            boot();
        }

        /** (Re)khoi dong cac thanh phan JVM tren CUNG file so (restart). */
        void boot() {
            C3LiveOrderExecutor.ApiObserver api = (a, ok) -> ks.onApiResult(now.get(), a, ok);
            book = new LiveBookC3(bookFile, 1.0);
            C3LiveOrderExecutor.FillObserver fill = (s, b, f, r) -> ks.onFill(now.get(), s, b, f, r);
            acct = new FillAccounting(book, gw, new OrderAuditLog(OrderAuditLog.LIVE_TAG, s -> { }), fill, alerts::add, api,
                    now::get, null);
            rec = new Reconciler(gw, book, acct, () -> new SymbolRules(ei, T0), alerts::add, api, now::get, 0.01, 2, null);
            acct.setUnknownPositionSink(rec::onUnknownPosition);
            gw.wsSink = txt -> acct.dispatch(UserStreamEvents.parse(txt));
            ex = new C3LiveOrderExecutor(gw, book, api, fill, now::get, ms -> now.addAndGet(ms), 10_000L, 3, Runnable::run);
            eq = new C3LiveEquity(gw, 10_000d, 60_000L, now::get, api);
            ks.attachEquitySource(eq);
            SymbolUniverseLive uni = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> ei, m -> { });
            uni.apply(ei, now.get());
            entry = C3LiveEntry.builder().book(book)
                    .killSwitch(new C3LiveEntry.KillSwitchView() {
                        public boolean armed() { return true; }
                        public boolean allowNewEntry(String s) { return ks.allowNewEntry(s); }
                        public boolean allowDca(String s) { return ks.allowDca(s); }
                    })
                    .universe(uni).modeGuard(new AccountModeGuard(gw, m -> { })).rules(() -> new SymbolRules(ei, T0))
                    .capital(eq::capital).legacy(s -> false)
                    .budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null)).legBudgetFn((b, i) -> b)
                    .gridDue((f, px, n) -> n == 1 && px <= f * 0.5f).executor(ex)
                    .audit(new OrderAuditLog(OrderAuditLog.LIVE_TAG, s -> { })).pushAllowed(() -> true).dcaGridEnabled(true)
                    .sizeCapOfEquity(0.045f).reconAllows(rec::allowsEntry).build();
            flat = new C3LiveFlattener(gw, book, ks::requiredAction, alerts::add, api, now::get, 5, 10_000L, 10_000L);
            mgr = TrailingStopManager.builder().gateway(gw).book(book).rules(() -> new SymbolRules(ei, T0))
                    .closer(flat::closeCluster).defer((s, t, n) -> defer.get()).armHook((s, t, n) -> { })
                    .action(ks::requiredAction).api(api).clock(now::get).safeRetryMs(10_000L).build();
            ex.resolveUnresolved(true);
            rec.startup();
        }

        C3LiveEntry.Result buy(String sym, float ref, boolean dca) {
            bar++;
            return entry.onLeg(new C3LiveEntry.LegInput(sym, dca ? "DCA_LEVEL1" : "BIG_DOWN", dca, T0 + bar * MIN, ref, ref, 1f,
                    false, 0.5f, 1), now.get());
        }

        /** 1 nhip: san kich stop o gia => nhip exit => FLATTEN. */
        void tick(String sym, String px) {
            now.addAndGet(10_000L);
            BigDecimal p = new BigDecimal(px);
            gw.triggerStops(sym, p);
            Map<String, Float> m = new HashMap<>();
            for (String s : book.ownedSymbols()) {
                BigDecimal x = gw.price(s);
                if (x != null) m.put(s, x.floatValue());
            }
            m.put(sym, p.floatValue());
            mgr.step(m);
            flat.step();
        }

        String lastLedger() throws Exception {
            List<String> l = Files.readAllLines(new File(tmp.getRoot(), "run/" + LiveBookC3.LEDGER_NAME).toPath());
            return l.get(l.size() - 1);
        }
    }


    /** periodic sau 1 tick + 1 cua so du lieu BTC tuoi (C1/C5 sach) — nhu luong that. */
    static void periodicHealthy(KillSwitchEngine e, long t) {
        e.onTickStart(t);
        java.util.Map<String, java.util.List<com.binance.chuyennd.object.sw.KlineObjectSimple>> w = new java.util.HashMap<>();
        com.binance.chuyennd.object.sw.KlineObjectSimple k = new com.binance.chuyennd.object.sw.KlineObjectSimple();
        k.startTime = t - 60_000L;
        k.priceOpen = 1f;
        k.priceClose = 1f;
        k.maxPrice = 1f;
        k.minPrice = 1f;
        w.put("BTCUSDT", java.util.Collections.singletonList(k));
        e.onMarketData(t, w);
        e.periodic(t);
    }

    @Test
    public void openDcaArmMoveStopNTimesThenStopFills() throws Exception {
        Rig r = new Rig();
        String s = C3LiveFixtures.sym(0);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.tick(s, "0.7");
        r.gw.setPrice(s, new BigDecimal("0.5"));
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 0.5f, true).outcome);
        LiveBookC3.ClusterView c = r.book.cluster(s).get();
        assertEquals(2, c.legCount);
        float avg = c.avgEntryF;
        assertTrue(avg > 0.5f && avg < 1.0f);
        r.tick(s, "0.6");
        assertFalse(r.book.cluster(s).get().trailArmed());
        int moves = 0;
        String prevStop = null;
        double prevPx = 0;
        for (int i = 0; i <= 12; i++) {
            double px = avg * (1.08 + 0.04 * i);
            r.tick(s, String.format(java.util.Locale.ROOT, "%.4f", px));
            LiveBookC3.ClusterView cv = r.book.cluster(s).get();
            assertTrue(cv.trailArmed());
            assertEquals("luon dung 1 stop mo tren san", 1, r.gw.openStops(s).size());
            if (prevStop != null && !prevStop.equals(cv.stopClientAlgoId)) {
                moves++;
                assertTrue("stop chi dich LEN", cv.stopPrice > prevPx);
            }
            prevStop = cv.stopClientAlgoId;
            prevPx = cv.stopPrice;
        }
        assertTrue("doi stop >= 5 lan (" + moves + ")", moves >= 5);
        double stopPx = r.book.cluster(s).get().stopPrice;
        r.tick(s, String.format(java.util.Locale.ROOT, "%.4f", stopPx * 0.995));
        assertFalse("stop khop => so cap nhat", r.book.isHolding(s));
        assertEquals(0, r.gw.position(s).signum());
        assertTrue(r.gw.openStops(s).isEmpty());
        String led = r.lastLedger();
        assertTrue(led, led.contains(FillAccounting.REASON_TRAILING));
        assertTrue("lai > 0", r.book.account().realized > 0d);
        assertEquals(KillSwitchEngine.Action.NONE, r.ks.requiredAction());
    }

    @Test
    public void openThenTimeStop168h() throws Exception {
        Rig r = new Rig();
        String s = C3LiveFixtures.sym(1);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.tick(s, "1.01");
        r.now.addAndGet(168 * H);
        r.tick(s, "1.02");
        assertFalse(r.book.isHolding(s));
        assertEquals(0, r.gw.position(s).signum());
        assertTrue(r.lastLedger().contains(TrailingStopManager.REASON_TIME_STOP));
        assertTrue(r.gw.callLog().stream().anyMatch(x -> x.startsWith("newMarketOrder:" + s + ":c3x-")));
    }

    @Test
    public void openThenX14ExtendsThenCloses() throws Exception {
        Rig r = new Rig();
        String s = C3LiveFixtures.sym(2);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.defer.set(true);
        r.now.addAndGet(200 * H);
        r.tick(s, "0.98");
        assertTrue("X14 hoan: van giu", r.book.isHolding(s));
        r.now.addAndGet(100 * H);
        r.tick(s, "0.97");
        assertTrue(r.book.isHolding(s));
        r.defer.set(false);
        r.tick(s, "0.97");
        assertFalse(r.book.isHolding(s));
        assertTrue(r.lastLedger().contains(TrailingStopManager.REASON_TIME_STOP));
    }

    @Test
    public void restartMidwayKeepsStateAndSingleStop() {
        Rig r = new Rig();
        String s = C3LiveFixtures.sym(3);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.tick(s, "1.10");
        r.tick(s, "1.20");
        LiveBookC3.ClusterView before = r.book.cluster(s).get();
        int placed = r.gw.calls("newStopMarket");
        r.boot();   // restart JVM: so nap tu file, reconcile khoi dong
        LiveBookC3.ClusterView after = r.book.cluster(s).get();
        assertEquals(before.tsFirstLeg, after.tsFirstLeg);
        assertEquals(before.legCount, after.legCount);
        assertEquals(Float.floatToIntBits(before.peakRate), Float.floatToIntBits(after.peakRate));
        assertEquals(Float.floatToIntBits(before.priceSL), Float.floatToIntBits(after.priceSL));
        assertEquals(before.stopClientAlgoId, after.stopClientAlgoId);
        r.tick(s, "1.19");
        assertEquals("khong dat lai stop trung", placed, r.gw.calls("newStopMarket"));
        r.tick(s, "1.40");
        assertEquals(1, r.gw.openStops(s).size());
        assertTrue(r.gw.calls("newStopMarket") > placed);
    }

    @Test
    public void killSwitchC2BlocksEntryAndDcaButStopsStillManaged() {
        Rig r = new Rig();
        for (int i = 4; i < 7; i++) {
            r.gw.setPrice(C3LiveFixtures.sym(i), new BigDecimal("1.03"));   // khop 3 % bat loi so voi ref 1.0
            assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(C3LiveFixtures.sym(i), 1.0f, false).outcome);
        }
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, r.ks.requiredAction());
        assertTrue(r.ks.latchCodes().contains("C2"));
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, r.buy(C3LiveFixtures.sym(8), 1.0f, false).outcome);
        r.gw.setPrice(C3LiveFixtures.sym(4), new BigDecimal("0.5"));
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, r.buy(C3LiveFixtures.sym(4), 0.5f, true).outcome);
        r.tick(C3LiveFixtures.sym(5), "1.20");
        assertTrue("van quan ly vi the (arm + stop)", r.book.cluster(C3LiveFixtures.sym(5)).get().stopClientAlgoId != null);
        periodicHealthy(r.ks, r.now.get() + 5 * H);
        assertTrue("C2 khong tu go", r.ks.latchCodes().contains("C2"));
    }

    @Test
    public void killSwitchC3LatchesThenAutoReleases() {
        Rig r = new Rig();
        for (int i = 0; i < 5; i++) {
            r.gw.failNext("newMarketOrder", new GatewayException(ErrorKind.OTHER, 400, -1000, "loi", true, 0L, null));
            r.buy(C3LiveFixtures.sym(10 + i), 1.0f, false);
        }
        assertTrue(r.ks.latchCodes().contains("C3"));
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, r.buy(C3LiveFixtures.sym(20), 1.0f, false).outcome);
        r.rec.checkPositions();   // call OK => C3 het dat
        periodicHealthy(r.ks, r.now.get());
        r.now.addAndGet(31 * MIN);
        r.rec.checkPositions();
        r.rec.checkPositions();
        periodicHealthy(r.ks, r.now.get());
        assertFalse("30' sach + 3 OK => tu go", r.ks.latchCodes().contains("C3"));
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(C3LiveFixtures.sym(20), 1.0f, false).outcome);
    }

    @Test
    public void killSwitchC4CapacityBlocksNewClusterButAllowsDca() {
        Rig r = new Rig();
        String s = C3LiveFixtures.sym(0);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.ks.onPaper(r.now.get(), 91, 100f, 10_000f);   // = onBook tu so that: > 90 vi the
        C3LiveEntry.Result nr = r.buy(C3LiveFixtures.sym(1), 1.0f, false);
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, nr.outcome);
        r.gw.setPrice(s, new BigDecimal("0.5"));
        assertEquals("DCA cum dang co van chay", C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 0.5f, true).outcome);
        assertEquals(KillSwitchEngine.Action.NONE, r.ks.requiredAction());
        r.ks.onPaper(r.now.get(), 2, 100f, 10_000f);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(C3LiveFixtures.sym(1), 1.0f, false).outcome);
    }

    @Test
    public void killSwitchA40FlattensAllAndCancelsStops() {
        Rig r = new Rig();
        for (int i = 0; i < 6; i++) assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(C3LiveFixtures.sym(i), 1.0f, false).outcome);
        r.tick(C3LiveFixtures.sym(0), "1.15");
        assertNotNull(r.book.cluster(C3LiveFixtures.sym(0)).get().stopClientAlgoId);
        periodicHealthy(r.ks, r.now.get());   // dinh equity tai khoan con (tu luc bat)
        r.gw.deposit(new BigDecimal("-5000"));   // equity tai khoan con giam > 40 %
        r.now.addAndGet(2 * MIN);
        periodicHealthy(r.ks, r.now.get());
        assertEquals(KillSwitchEngine.Action.FLATTEN, r.ks.requiredAction());
        for (int k = 0; k < 6 && r.book.openCount() > 0; k++) {
            r.now.addAndGet(11_000L);
            r.flat.step();
        }
        assertEquals(0, r.book.openCount());
        for (int i = 0; i < 6; i++) assertEquals(0, r.gw.position(C3LiveFixtures.sym(i)).signum());
        assertTrue(r.gw.openStops(null).isEmpty());
        assertEquals(0, r.mgr.step(Collections.singletonMap(C3LiveFixtures.sym(0), 2f)));
        assertTrue(r.alerts.stream().anyMatch(a -> a.contains("FLATTEN")));
    }

    @Test
    public void userStreamLossFallbackRestUpdatesBook() {
        Rig r = new Rig();
        String s = C3LiveFixtures.sym(7);
        assertEquals(C3LiveEntry.Outcome.SUBMITTED, r.buy(s, 1.0f, false).outcome);
        r.tick(s, "1.15");
        r.gw.wsSink = null;   // mat user stream
        r.gw.triggerStops(s, new BigDecimal("1.05"));
        assertTrue("chua biet (khong co stream)", r.book.isHolding(s));
        AtomicLong clk = new AtomicLong(0L);
        UserStream us = new UserStream(r.gw, (url, l) -> {
            l.onClosed("failure");
            return () -> { };
        }, UserStream.parseUrls("wss://x/{key}"), r.acct, () -> {
            r.ex.resolveUnresolved(false);
            r.rec.checkPositions();
        }, r.alerts::add, null, clk::get, 5_000L, 10_000L, 60_000L, 0L);
        for (int i = 0; i < 5; i++) {
            us.tick(clk.get());
            clk.addAndGet(1_000L);
        }
        assertFalse("fallback REST => so cap nhat", r.book.isHolding(s));
        assertTrue(r.alerts.stream().anyMatch(a -> a.contains("mat user stream")));
    }
}
