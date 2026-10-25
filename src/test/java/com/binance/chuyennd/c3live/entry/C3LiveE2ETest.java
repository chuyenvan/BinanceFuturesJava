package com.binance.chuyennd.c3live.entry;

import com.binance.chuyennd.c3live.adapter.DryGateway;
import com.binance.chuyennd.c3live.api.ClientOrderIds;
import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
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
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 C12 tich hop] 1 tick sap 24 ung vien end-to-end tren MockExchangeGateway: kill-switch ACT that
 * ({@link KillSwitchEngine}), universe (TradFi bi loai), AccountModeGuard, equity {@link C3LiveEquity} (min(pilot, tmb)),
 * sizing {@code TradeUtils.managerBudget} (U_MAX), {@link SymbolRules}, giu cho {@link LiveBookC3} (persist),
 * executor idempotent (1 leg bi timeout SAU khi san nhan => 0 lenh trung), latch C3 => tick sau 0 lenh moi, A40 =>
 * FLATTEN reduce-only chia lo + huy stop + Telegram. Them bien the DryGateway: 1 dong [LIVE-DRY] / leg, 0 dong live.
 */
public class C3LiveE2ETest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_020_000L;

    static final class ListSink implements KillSwitchEngine.Sink {
        final List<String> lines = new ArrayList<>();
        public void info(String m) { lines.add("I " + m); }
        public void warn(String m) { lines.add("W " + m); }
    }

    /** Mock: cid chi dinh bi timeout SAU KHI san da khop (lan dau). */
    static final class AckTimeoutGw extends MockExchangeGateway {
        final Set<String> ackTimeoutOnce = new HashSet<>();
        final Map<String, Integer> sends = new ConcurrentHashMap<>();

        @Override
        public synchronized OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String cid, boolean ro) {
            sends.merge(cid, 1, Integer::sum);
            OrderInfo o = super.newMarketOrder(symbol, side, qty, cid, ro);
            if (ackTimeoutOnce.remove(cid)) {
                throw new GatewayException(ErrorKind.TIMEOUT_UNKNOWN_STATE, 0, 0, "read timeout", false, 0L, null);
            }
            return o;
        }
    }

    private KillSwitchEngine ks(ListSink sink, AtomicLong now, List<String> alerts) {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.c2Signed = true;
        p.latchFile = new File(tmp.getRoot(), "run/killsw_latch.json");
        p.resetFile = new File(tmp.getRoot(), "run/killsw_reset.req");
        p.autoReleaseMs = 30 * 60_000L;
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", sink, null, () -> 10_000d,
                () -> Configs.U_MAX, now.get(), p);
        e.setAlert(alerts::add);
        return e;
    }

    private C3LiveEntry entry(ExchangeGateway gw, ExchangeInfo ei, LiveBookC3 book, KillSwitchEngine ks, AtomicLong now,
                              OrderAuditLog audit, Map<String, BigDecimal> refs) {
        SymbolUniverseLive uni = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults(), () -> ei, m -> { });
        uni.apply(ei, now.get());
        C3LiveOrderExecutor.ApiObserver api = (a, ok) -> ks.onApiResult(now.get(), a, ok);
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(gw, book, api,
                (s, b, f, r) -> ks.onFill(now.get(), s, b, f, r), now::get, ms -> now.addAndGet(ms), 10_000L, 3,
                Runnable::run);
        C3LiveEquity eq = new C3LiveEquity(gw, 10_000d, 60_000L, now::get, api);
        ks.attachEquitySource(eq);
        return C3LiveEntry.builder().book(book)
                .killSwitch(new C3LiveEntry.KillSwitchView() {
                    public boolean armed() { return ks.mode() == KillSwitchEngine.Mode.ACT; }
                    public boolean allowNewEntry(String s) { return ks.allowNewEntry(s); }
                })
                .universe(uni).modeGuard(new AccountModeGuard(gw, m -> { })).rules(() -> new SymbolRules(ei, now.get()))
                .capital(eq::capital).legacy(s -> false)
                .budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null)).legBudgetFn((b, i) -> b)
                .gridDue((f, p, n) -> false).executor(ex).audit(audit)
                .refSink((s, p) -> refs.put(s, BigDecimal.valueOf(p))).pushAllowed(() -> true).dcaGridEnabled(true)
                .sizeCapOfEquity(0.045f).build();
    }

    @Test
    public void oneCrashTick24CandidatesEndToEnd() {
        AtomicLong now = new AtomicLong(T0);
        ExchangeInfo ei = C3LiveFixtures.info(48);
        AckTimeoutGw gw = new AckTimeoutGw();
        gw.exchangeInfo = ei;
        for (int i = 0; i < 48; i++) gw.setPrice(C3LiveFixtures.sym(i), new BigDecimal("2"));
        ListSink sink = new ListSink();
        List<String> alerts = new ArrayList<>();
        KillSwitchEngine ks = ks(sink, now, alerts);
        File bookFile = new File(tmp.getRoot(), "run/c3live_book.json");
        LiveBookC3 book = new LiveBookC3(bookFile, 1.0);
        List<String> audit = new ArrayList<>();
        C3LiveEntry e = entry(gw, ei, book, ks, now, new OrderAuditLog(OrderAuditLog.LIVE_TAG, audit::add),
                new ConcurrentHashMap<>());
        long bar = T0 - 60_000L;
        String slow = "c3-" + C3LiveFixtures.sym(7) + "-" + Math.floorDiv(bar, 60_000L) + "-0";
        gw.ackTimeoutOnce.add(slow);

        // --- tick 1: 24 ung vien + 1 TradFi
        assertEquals(C3LiveEntry.Outcome.NOT_BUYABLE,
                e.onLeg(new C3LiveEntry.LegInput("TSLAUSDT", "BIG_DOWN", false, bar, 300, 300, 1f, false), now.get()).outcome);
        double sum = 0d;
        for (int k = 0; k < 24; k++) {
            C3LiveEntry.Result r = e.onLeg(new C3LiveEntry.LegInput(C3LiveFixtures.sym(k), "BIG_DOWN", false, bar, 2.0, 2.0,
                    1f, false), now.get());
            assertEquals(r.toString(), C3LiveEntry.Outcome.SUBMITTED, r.outcome);
            assertTrue(ClientOrderIds.isValid(r.cid));
            assertTrue(r.budget <= 0.045 * 10_000 + 1e-6);
            sum += r.qty.doubleValue() * 2.0;
        }
        assertEquals(24, book.openCount());
        assertEquals(0, book.unresolvedLegs().size());
        assertTrue(sum <= Configs.U_MAX * 10_000d);
        assertEquals(sum, book.marginUsed(), 1e-6);
        // idempotency: leg bi timeout sau khi san nhan => tra san, KHONG gui lai
        assertEquals(1, (int) gw.sends.get(slow));
        for (Integer n : gw.sends.values()) assertEquals(1, n.intValue());
        assertEquals(24, gw.calls("newMarketOrder"));
        assertTrue(gw.calls("queryOrder") >= 1);
        assertEquals(LiveBookC3.LegState.CONFIRMED, book.leg(slow).get().state);
        // so persist == so RAM
        assertEquals(book.marginUsed(), new LiveBookC3(bookFile, 1.0).marginUsed(), 1e-9);
        assertEquals(KillSwitchEngine.Action.NONE, ks.requiredAction());

        // --- latch C3 (5 loi API lien tiep) => tick 2: 0 lenh moi, ke ca DCA
        for (int i = 0; i < 5; i++) ks.onApiResult(now.get(), "positions", false);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, ks.requiredAction());
        now.addAndGet(60_000L);
        for (int k = 24; k < 48; k++) {
            C3LiveEntry.Result r = e.onLeg(new C3LiveEntry.LegInput(C3LiveFixtures.sym(k), "BIG_DOWN", false, bar + 60_000L,
                    2.0, 2.0, 1f, false), now.get());
            assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, r.outcome);
        }
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, e.onLeg(new C3LiveEntry.LegInput(C3LiveFixtures.sym(0), "DCA_LEVEL1",
                true, bar + 60_000L, 0.5, 0.5, 1f, false), now.get()).outcome);
        assertEquals(24, gw.calls("newMarketOrder"));
        // C3 KHONG tu go sau 30' sach (chi C1/C5)
        for (int i = 0; i < 40; i++) {
            now.addAndGet(60_000L);
            ks.onTickStart(now.get());
            ks.onApiResult(now.get(), "positions", true);
            ks.periodic(now.get());
        }
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, ks.requiredAction());

        // --- A40: equity that -41 % => FLATTEN: dong reduce-only <= 5 lenh/10 s, huy stop, Telegram
        for (int k = 0; k < 2; k++) {
            String sym = C3LiveFixtures.sym(k);
            gw.newStopMarket(sym, Side.SELL, new BigDecimal("1.5"), "c3s-" + sym + "-1", true);
            book.setStop(sym, 1.5, "c3s-" + sym + "-1", now.get());
        }
        ks.onAccountEquity(now.get(), 10_000d);
        ks.onAccountEquity(now.get(), 5_900d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, ks.requiredAction());
        C3LiveFlattener fl = new C3LiveFlattener(gw, book, ks::requiredAction, alerts::add,
                (a, ok) -> ks.onApiResult(now.get(), a, ok), now::get, 5, 10_000L, 10_000L);
        int rounds = 0;
        int maxPerWindow = 0;
        while (book.openCount() > 0 && rounds++ < 100) {
            int sent = fl.step();
            maxPerWindow = Math.max(maxPerWindow, sent);
            now.addAndGet(10_001L);
        }
        fl.step();
        assertEquals(0, book.openCount());
        assertTrue(maxPerWindow <= 5);
        assertTrue("phai can >= 5 luot cho 24 cum", rounds >= 5);
        assertEquals(0, gw.openStops(null).size());
        assertEquals(0, gw.positions().size());
        assertEquals(24 + 24, gw.calls("newMarketOrder"));
        assertTrue(alerts.stream().anyMatch(m -> m.contains("FLATTEN: dong 24 cum")));
        assertTrue(alerts.stream().anyMatch(m -> m.contains("FLATTEN xong")));
        assertTrue(alerts.stream().anyMatch(m -> m.contains("LATCH action=FLATTEN")));
        // van chan mo moi
        assertEquals(C3LiveEntry.Outcome.KS_BLOCKED, e.onLeg(new C3LiveEntry.LegInput(C3LiveFixtures.sym(30), "BIG_DOWN",
                false, bar + 120_000L, 2.0, 2.0, 1f, false), now.get()).outcome);
    }

    @Test
    public void dryAdapterOneLiveDryLinePerLegNoLiveLines() {
        AtomicLong now = new AtomicLong(T0);
        ExchangeInfo ei = C3LiveFixtures.info(24);
        List<String> audit = new ArrayList<>();
        OrderAuditLog dryLog = new OrderAuditLog(OrderAuditLog.DRY_TAG, audit::add);
        Map<String, BigDecimal> refs = new ConcurrentHashMap<>();
        DryGateway gw = new DryGateway(() -> ei, refs::get, new BigDecimal("10000"), dryLog, now::get);
        ListSink sink = new ListSink();
        KillSwitchEngine ks = ks(sink, now, new ArrayList<>());
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        C3LiveEntry e = entry(gw, ei, book, ks, now, dryLog, refs);
        long bar = T0 - 60_000L;
        List<String> cids = new ArrayList<>();
        for (int k = 0; k < 24; k++) {
            C3LiveEntry.Result r = e.onLeg(new C3LiveEntry.LegInput(C3LiveFixtures.sym(k), "BIG_DOWN", false, bar, 0.5 + k,
                    0.5 + k, 1f, false), now.get());
            assertEquals(r.toString(), C3LiveEntry.Outcome.SUBMITTED, r.outcome);
            cids.add(r.cid);
            LiveBookC3.ClusterView c = book.cluster(C3LiveFixtures.sym(k)).get();
            assertEquals(0.5 + k, c.avgPrice, 1e-9);   // khop o gia ref (close 1m)
        }
        assertEquals(24, audit.size());
        for (int k = 0; k < 24; k++) {
            String line = audit.get(k);
            assertTrue(line, line.startsWith("[LIVE-DRY] "));
            assertTrue(line, line.contains("cid=" + cids.get(k) + " "));
            assertTrue(line, line.contains("status=FILLED"));
            assertEquals("12 cot", 12, line.split(" ").length - 1);
            assertFalse(line.contains("[C3-LIVE-ORDER]"));
        }
        // tmb dry = von + PnL (gia ref khong doi => 10 000)
        assertEquals(10_000d, gw.account().getTotalMarginBalance().doubleValue(), 1e-6);
    }
}
